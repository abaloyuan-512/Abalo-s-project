"""Authorized M1-A live-evaluation entrypoint; current frozen auth defaults fail closed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abalo_iching.interpretation.m1a_eval_runner import load_fixtures  # noqa: E402
from abalo_iching.interpretation.m1a_live_eval import (  # noqa: E402
    M1ALiveEvalError,
    M1ALiveStage,
    create_live_provider,
    load_frozen_plan,
    run_live_evaluation,
    write_safe_live_output,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-openai", action="store_true")
    parser.add_argument("--stage", required=True, choices=("sentinel", "full"))
    parser.add_argument(
        "--plan",
        type=Path,
        default=ROOT / "evals" / "meihua" / "m1a_v001" / "live_eval_plan_v1.json",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "evals" / "meihua" / "m1a_v001" / "fixtures.json",
    )
    parser.add_argument(
        "--sentinels",
        type=Path,
        default=ROOT / "evals" / "meihua" / "m1a_v001" / "sentinels.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    stage = M1ALiveStage.SENTINEL if args.stage == "sentinel" else M1ALiveStage.FULL_FIXTURE
    try:
        load_frozen_plan(args.plan)
        provider = create_live_provider(stage, live_openai=args.live_openai)
        fixtures = load_fixtures(args.fixtures)
        if stage is M1ALiveStage.SENTINEL:
            sentinels = json.loads(args.sentinels.read_text(encoding="utf-8"))
            fixture_ids = tuple(item["fixture_id"] for item in sentinels)
        else:
            fixture_ids = tuple(sorted(item["fixture_id"] for item in fixtures))
        output = run_live_evaluation(fixtures, fixture_ids, provider)
        write_safe_live_output(output, args.output)
    except M1ALiveEvalError as exc:
        print(exc.code.value, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
