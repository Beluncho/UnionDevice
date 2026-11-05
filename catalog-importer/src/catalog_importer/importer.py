from __future__ import annotations

import html
import io
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path
from typing import Any, BinaryIO

import httpx
from bs4 import BeautifulSoup

DEFAULT_FEED_URL = "https://www.souz-pribor.ru/yml/any/feed.xml"
DEFAULT_OFFER_IDS = ("58444", "64423")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/141.0 Safari/537.36"
)


class ImporterError(RuntimeError):
    pass


class CatalogImporter:
    def __init__(self, *, timeout: float = 45.0, proxy: str | None = None) -> None:
        self._client = httpx.Client(
            timeout=timeout,
            proxy=proxy,
            follow_redirects=True,
            trust_env=False,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CatalogImporter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def index(
        self,
        *,
        output: Path,
        feed_url: str = DEFAULT_FEED_URL,
        feed_file: Path | None = None,
    ) -> int:
        output.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with (
            self._feed_stream(feed_url=feed_url, feed_file=feed_file) as stream,
            output.open("w", encoding="utf-8", newline="\n") as target,
        ):
            for offer in iter_offers(stream):
                target.write(json.dumps(offer, ensure_ascii=False) + "\n")
                count += 1
        return count

    def enrich(
        self,
        *,
        offer_ids: Iterable[str],
        output_dir: Path,
        feed_url: str = DEFAULT_FEED_URL,
        feed_file: Path | None = None,
    ) -> list[Path]:
        selected_ids = tuple(dict.fromkeys(str(item) for item in offer_ids))
        if not selected_ids:
            raise ImporterError("At least one offer ID is required for enrichment")

        with self._feed_stream(feed_url=feed_url, feed_file=feed_file) as stream:
            offers = find_offers(stream, set(selected_ids))
        missing = [item for item in selected_ids if item not in offers]
        if missing:
            raise ImporterError("Offer IDs not found: " + ", ".join(missing))

        output_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for offer_id in selected_ids:
            offer = offers[offer_id]
            source_url = offer.get("url")
            if not source_url:
                raise ImporterError(f"Offer {offer_id} has no product URL")
            page = self._get_text(source_url, accept="text/html")
            product = parse_product_page(page, offer)
            filename = slug_for_offer(offer) + ".json"
            destination = output_dir / filename
            write_json(destination, product)
            paths.append(destination)
        return paths

    def prepare_examples(
        self,
        *,
        output_dir: Path,
        feed_url: str = DEFAULT_FEED_URL,
        feed_file: Path | None = None,
    ) -> list[Path]:
        paths = self.enrich(
            offer_ids=DEFAULT_OFFER_IDS,
            output_dir=output_dir,
            feed_url=feed_url,
            feed_file=feed_file,
        )
        complete = output_dir / "testo-510.json"
        if complete not in paths:
            raise ImporterError("Expected testo-510.json was not produced")
        data = json.loads(complete.read_text(encoding="utf-8"))
        specs = data.get("specs") or {}
        preferred_keys = (
            "Тип прибора",
            "Диапазон измерений",
            "Погрешность",
            "Класс защиты",
        )
        partial_specs = {key: specs[key] for key in preferred_keys if key in specs}
        if not partial_specs:
            raise ImporterError("testo 510 does not contain specifications")
        partial = {
            "name": data["name"],
            "manufacturer": data.get("manufacturer"),
            "specs": partial_specs,
            "description": None,
        }
        partial_path = output_dir / "testo-510.partial.json"
        write_json(partial_path, partial)
        return [*paths, partial_path]

    def _feed_stream(
        self,
        *,
        feed_url: str,
        feed_file: Path | None,
    ):
        if feed_file is not None:
            if not feed_file.is_file():
                raise ImporterError(f"Feed file not found: {feed_file}")
            return feed_file.open("rb")

        response = self._client.get(feed_url)
        if response.is_error:
            raise ImporterError(f"Feed request failed with HTTP {response.status_code}")
        return io.BytesIO(response.content)

    def _get_text(self, url: str, *, accept: str) -> str:
        try:
            response = self._client.get(url, headers={"Accept": accept})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ImporterError(f"Product page request failed: {url}") from exc
        return response.text


def iter_offers(stream: BinaryIO):
    for _, element in ET.iterparse(stream, events=("end",)):
        if element.tag != "offer":
            continue
        fields: dict[str, Any] = {
            "offer_id": element.attrib.get("id", ""),
            "available": element.attrib.get("available") == "true",
        }
        params: dict[str, str] = {}
        for child in element:
            value = (child.text or "").strip()
            if child.tag == "param":
                name = (child.attrib.get("name") or "").strip()
                if name and value:
                    params[name] = value
            elif child.tag in {
                "name",
                "typePrefix",
                "url",
                "categoryId",
                "vendor",
                "vendorCode",
            }:
                fields[child.tag] = value
        fields["params"] = params
        yield fields
        element.clear()


def find_offers(stream: BinaryIO, offer_ids: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for offer in iter_offers(stream):
        offer_id = offer["offer_id"]
        if offer_id in offer_ids:
            found[offer_id] = offer
            if len(found) == len(offer_ids):
                break
    return found


def parse_product_page(page: str, offer: dict[str, Any]) -> dict[str, Any]:
    soup = BeautifulSoup(page, "html.parser")
    description = _parse_description(soup)
    specs = _parse_specs(soup)
    type_prefix = (offer.get("typePrefix") or "").strip()
    if type_prefix:
        specs = {"Тип прибора": type_prefix, **specs}
    if not description:
        description = _json_ld_description(soup)
    if not specs:
        raise ImporterError(f"No specifications found for offer {offer['offer_id']}")

    return {
        "name": offer.get("name") or _json_ld_name(soup),
        "manufacturer": offer.get("vendor") or _json_ld_brand(soup),
        "specs": specs,
        "description": description or None,
    }


def _parse_description(soup: BeautifulSoup) -> str:
    root = soup.select_one("#description .product-description") or soup.select_one("#description")
    if root is None:
        return ""
    return " ".join(root.stripped_strings)


def _parse_specs(soup: BeautifulSoup) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in soup.select("#specifications table tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) != 2:
            continue
        key = " ".join(cells[0].stripped_strings)
        value = " ".join(cells[1].stripped_strings)
        if key and value:
            result[key] = value
    return result


def _product_json_ld(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(html.unescape(script.get_text(strip=True)))
        except (TypeError, ValueError):
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
    return {}


def _json_ld_description(soup: BeautifulSoup) -> str:
    value = _product_json_ld(soup).get("description")
    return value.strip() if isinstance(value, str) else ""


def _json_ld_name(soup: BeautifulSoup) -> str:
    value = _product_json_ld(soup).get("name")
    return value.strip() if isinstance(value, str) else ""


def _json_ld_brand(soup: BeautifulSoup) -> str | None:
    brand = _product_json_ld(soup).get("brand")
    if isinstance(brand, dict) and isinstance(brand.get("name"), str):
        return brand["name"].strip()
    return None


def slug_for_offer(offer: dict[str, Any]) -> str:
    name = (offer.get("name") or offer["offer_id"]).strip().lower()
    slug = "".join(char if char.isalnum() else "-" for char in name)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def search_index(index_path: Path, query: str, limit: int = 20) -> list[dict[str, Any]]:
    if not index_path.is_file():
        raise ImporterError(f"Catalog index not found: {index_path}")
    terms = [term.casefold() for term in query.split() if term.strip()]
    if not terms:
        raise ImporterError("Search query must not be blank")
    if limit < 1 or limit > 100:
        raise ImporterError("Search limit must be between 1 and 100")

    matches: list[dict[str, Any]] = []
    with index_path.open("r", encoding="utf-8") as source:
        for line in source:
            item = json.loads(line)
            haystack = " ".join(
                str(item.get(field, ""))
                for field in ("offer_id", "name", "typePrefix", "vendor", "vendorCode")
            ).casefold()
            if all(term in haystack for term in terms):
                matches.append(item)
                if len(matches) == limit:
                    break
    return matches

