from __future__ import annotations

import argparse
from pathlib import Path

from catalog_importer.importer import (
    DEFAULT_FEED_URL,
    CatalogImporter,
    ImporterError,
    search_index,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catalog-importer")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--http-proxy")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index = subparsers.add_parser("index", help="Create a local JSONL index from the YML feed")
    _add_feed_options(index)
    index.add_argument("--output", type=Path, required=True)

    enrich = subparsers.add_parser("enrich", help="Enrich explicitly selected offer IDs")
    _add_feed_options(enrich)
    enrich.add_argument("--offer-id", action="append", required=True)
    enrich.add_argument("--output-dir", type=Path, required=True)

    search = subparsers.add_parser("search", help="Search the local JSONL catalog index")
    search.add_argument("--index", type=Path, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=20)

    examples = subparsers.add_parser("prepare-examples", help="Prepare committed demo fixtures")
    _add_feed_options(examples)
    examples.add_argument("--output-dir", type=Path, default=Path("examples/inputs"))
    return parser


def _add_feed_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--feed-url", default=DEFAULT_FEED_URL)
    parser.add_argument("--feed-file", type=Path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "search":
            for item in search_index(args.index, args.query, args.limit):
                print(
                    "\t".join(
                        str(item.get(field, ""))
                        for field in ("offer_id", "vendor", "name", "typePrefix")
                    )
                )
        else:
            with CatalogImporter(timeout=args.timeout, proxy=args.http_proxy) as importer:
                if args.command == "index":
                    count = importer.index(
                        output=args.output,
                        feed_url=args.feed_url,
                        feed_file=args.feed_file,
                    )
                    print(f"Indexed {count} offers into {args.output}")
                elif args.command == "enrich":
                    paths = importer.enrich(
                        offer_ids=args.offer_id,
                        output_dir=args.output_dir,
                        feed_url=args.feed_url,
                        feed_file=args.feed_file,
                    )
                    for path in paths:
                        print(path)
                else:
                    paths = importer.prepare_examples(
                        output_dir=args.output_dir,
                        feed_url=args.feed_url,
                        feed_file=args.feed_file,
                    )
                    for path in paths:
                        print(path)
    except ImporterError as exc:
        print(f"catalog-importer: {exc}")
        return 1
    return 0

