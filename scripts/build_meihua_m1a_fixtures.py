"""Build deterministic M1-A Batch 3 fixture and audit assets without model calls."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abalo_iching.interpretation.m1a_batch3 import write_batch3_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "evals" / "meihua" / "m1a_v001",
    )
    args = parser.parse_args()
    bundle = write_batch3_bundle(args.output_dir)
    manifest = bundle["manifest"]
    print(
        f"candidates={manifest['candidate_count']} fixtures={manifest['fixture_count']} "
        f"sentinels={manifest['sentinel_count']} "
        f"pressure_cases={manifest['pressure_case_count']} output={args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
