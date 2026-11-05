from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send committed fixtures to the running API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--input-dir", type=Path, default=Path("examples/inputs"))
    parser.add_argument("--output-dir", type=Path, default=Path("examples/outputs"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    endpoint = args.base_url.rstrip("/") + "/api/v1/product-cards/generate"
    failed = False
    for source in sorted(args.input_dir.glob("*.json")):
        payload = source.read_bytes()
        request = urllib.request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            failed = True
            print(f"{source.name}: HTTP {exc.code}", file=sys.stderr)
            continue
        except OSError as exc:
            failed = True
            print(f"{source.name}: {exc}", file=sys.stderr)
            continue

        target = args.output_dir / source.name
        target.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"{source.name}: {result['status']} -> {target}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

