"""Run M1-A Batch 3 fixtures through the repository's offline service path only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abalo_iching.interpretation.m1a_eval_runner import (  # noqa: E402
    FixedReplayProvider,
    M1AEvalConfig,
    load_fixtures,
    run_m1a_eval,
    write_eval_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "evals" / "meihua" / "m1a_v001" / "fixtures.json",
    )
    parser.add_argument("--fixture-id", action="append", default=[])
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--provider-kind", choices=("FAKE", "MOCK"), default="MOCK")
    parser.add_argument("--invalid-first-attempt", action="store_true")
    parser.add_argument("--max-cases", type=int, required=True)
    parser.add_argument("--max-provider-attempts", type=int, required=True)
    parser.add_argument("--max-repairs", type=int, required=True)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--jsonl-output", type=Path, required=True)
    args = parser.parse_args()
    fixtures = load_fixtures(args.fixtures)
    provider = FixedReplayProvider(
        provider_kind=args.provider_kind,
        invalid_first_attempt=args.invalid_first_attempt,
    )
    config = M1AEvalConfig(
        batch_id=args.batch_id,
        max_cases=args.max_cases,
        max_provider_attempts=args.max_provider_attempts,
        max_repairs=args.max_repairs,
        fixture_ids=tuple(args.fixture_id),
    )
    output = run_m1a_eval(fixtures, config, provider, resume_path=args.resume)
    write_eval_outputs(output, args.json_output, args.jsonl_output)
    print(
        f"results={len(output['results'])} attempts={output['budgets']['provider_attempts_used']} "
        f"repairs={output['budgets']['repairs_used']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
