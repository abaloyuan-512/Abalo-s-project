"""Run the Sites Phase 3A deterministic local loop without external services."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from abalo_iching.application import process_sites_meihua_request  # noqa: E402
from scripts.render_sites_phase3a_preview import render_response_html  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if ROOT.resolve() == args.output.resolve() or ROOT.resolve() in args.output.resolve().parents:
        raise ValueError("output must be outside the Git repository")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    response = process_sites_meihua_request(payload)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "sites_meihua_response.json").write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "sites_meihua_preview.html").write_text(render_response_html(response), encoding="utf-8")
    print(json.dumps({"status": response["status"], "request_id": response["request_id"], "output_files": ["sites_meihua_response.json", "sites_meihua_preview.html"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
