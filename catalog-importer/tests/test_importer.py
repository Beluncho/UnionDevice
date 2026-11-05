from __future__ import annotations

import json
from pathlib import Path

import pytest
from catalog_importer.importer import (
    CatalogImporter,
    ImporterError,
    find_offers,
    iter_offers,
    parse_product_page,
    search_index,
)

FIXTURES = Path(__file__).with_name("fixtures")


def test_iter_offers_reads_basic_catalog() -> None:
    with (FIXTURES / "feed.xml").open("rb") as stream:
        offers = list(iter_offers(stream))
    assert len(offers) == 2
    assert offers[0]["offer_id"] == "58444"
    assert offers[0]["params"] == {"Артикул": "0563 0510"}


def test_find_offers_returns_only_selected() -> None:
    with (FIXTURES / "feed.xml").open("rb") as stream:
        result = find_offers(stream, {"64423"})
    assert list(result) == ["64423"]


def test_parse_product_page_extracts_normalized_input() -> None:
    page = (FIXTURES / "product.html").read_text(encoding="utf-8")
    offer = {
        "offer_id": "58444",
        "name": "testo 510",
        "vendor": "Testo",
        "typePrefix": "дифференциальный манометр",
    }
    product = parse_product_page(page, offer)
    assert product == {
        "name": "testo 510",
        "manufacturer": "Testo",
        "specs": {
            "Тип прибора": "дифференциальный манометр",
            "Диапазон измерений": "0 ... 100 гПа",
            "Класс защиты": "IP40",
        },
        "description": "Полное описание прибора. Вторая часть.",
    }


def test_enrich_requires_offer_ids(tmp_path: Path) -> None:
    with CatalogImporter() as importer, pytest.raises(ImporterError, match="At least one"):
        importer.enrich(offer_ids=[], output_dir=tmp_path)


def test_index_writes_jsonl_from_local_feed(tmp_path: Path) -> None:
    output = tmp_path / "catalog.jsonl"
    with CatalogImporter() as importer:
        count = importer.index(output=output, feed_file=FIXTURES / "feed.xml")
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert count == 2
    assert rows[1]["name"] == "testo 830-T1"


def test_search_index_finds_products_by_type_and_vendor(tmp_path: Path) -> None:
    output = tmp_path / "catalog.jsonl"
    with CatalogImporter() as importer:
        importer.index(output=output, feed_file=FIXTURES / "feed.xml")
    matches = search_index(output, "Testo манометр")
    assert [item["offer_id"] for item in matches] == ["58444"]

