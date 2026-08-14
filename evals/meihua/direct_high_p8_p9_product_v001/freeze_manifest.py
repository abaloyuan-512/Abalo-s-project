from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "evals/meihua/direct_high_p8_p9_product_v001"
OUTPUT = STAGE / "candidate_manifest.json"

CANDIDATE_FILES = (
    "evals/meihua/direct_high_p8_p9_product_v001/acceptance_contract.json",
    "evals/meihua/direct_high_p8_p9_product_v001/scope_lock.json",
    "evals/meihua/direct_high_p8_p9_product_v001/build_offline_evidence.py",
    "evals/meihua/direct_high_p8_p9_product_v001/offline_ledger.json",
    "evals/meihua/direct_high_p8_p9_product_v001/verification_result.json",
    "evals/meihua/direct_high_p8_p9_product_v001/freeze_manifest.py",
    "src/abalo_iching/application/sites_direct_high_product_v1.py",
    "scripts/run_hosted_api.py",
    "sites/hosted-app/package.json",
    "sites/hosted-app/app/api/direct-reading/v2/route.ts",
    "sites/hosted-app/app/direct-reading-v2-preview/page.tsx",
    "sites/hosted-app/app/direct-reading-v2-preview/page.module.css",
    "sites/hosted-app/app/direct-reading-v2-preview/ProductPresentation.tsx",
    "sites/hosted-app/tests/direct-reading-v2-route.test.mjs",
    "sites/hosted-app/tests/direct-reading-v2-preview.test.tsx",
    "sites/hosted-app/tests/fixtures/direct-reading-python-server.py",
    "tests/test_sites_direct_high_product_v1.py",
    "tests/test_hosted_api.py",
)

AUTHORITY_FILES = (
    "src/abalo_iching/application/sites_direct_reading_v2.py",
    "src/abalo_iching/application/sites_question_context_v1.py",
    "src/abalo_iching/meihua/calendar_provider.py",
    "src/abalo_iching/meihua/relations.py",
    "src/abalo_iching/meihua/seasonal_strength.py",
    "docs/specs/MEIHUA_RULE_SPEC_V1.md",
    "docs/specs/MEIHUA_DATA_CONTRACT_V1.md",
    "docs/specs/MEIHUA_INTERPRETATION_SPEC_V1.md",
    "outputs/v009_canary_real_result.json",
    "evals/meihua/direct_reading_v2_stability_v009/candidate_manifest.json",
    "evals/meihua/direct_reading_v2_stability_v009/final_outcome.json",
    "outputs/v011_stability_run_ledger.json",
    "evals/meihua/direct_reading_v2_stability_v011/candidate_manifest.json",
    "evals/meihua/direct_reading_v2_stability_v011/independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_stability_v011/live_final_outcome.json",
    "evals/meihua/direct_reading_v2_stability_v011/live_independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_sdk_authoritative_origin_v024/design_stop.json",
    "sites/hosted-app/db/direct-reading-preview-jobs.ts",
    "sites/hosted-app/db/schema.ts",
    "sites/hosted-app/app/direct-reading-v2-preview/SafeDirectReadingMarkdown.tsx",
    "sites/hosted-app/app/direct-reading-v2-preview/pollPolicy.ts",
    "sites/hosted-app/tests/fixtures/run-final-sites-canary.mjs",
    "streamlit_app.py",
    "iching_tools.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def entries(paths: tuple[str, ...]) -> list[dict[str, str]]:
    missing = [path for path in paths if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"MANIFEST_MISSING_FILES:{missing}")
    return [{"path": path, "sha256": sha256(ROOT / path)} for path in paths]


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("CANDIDATE_MANIFEST_ALREADY_EXISTS")
    manifest = {
        "stage_id": "DIRECT_HIGH_P8_P9_PRODUCT_V001",
        "contract_id": "DRV2-P8-P9-DIRECT-HIGH-OFFLINE-PRODUCT-WIRING-ACCEPTANCE-V1",
        "status": "FROZEN_OFFLINE_CANDIDATE_AWAITING_INDEPENDENT_QA",
        "candidate_files": entries(CANDIDATE_FILES),
        "authority_files": entries(AUTHORITY_FILES),
        "offline_ledger_sha256": sha256(STAGE / "offline_ledger.json"),
        "verification": {
            "focused_python": "123 passed",
            "sites_build": "PASS",
            "sites_tests": "49 passed",
            "full_pytest": "1459 passed",
        },
        "router_calls": 0,
        "live_calls": 0,
        "deployment": False,
        "production": False,
        "default_replacement": False,
    }
    OUTPUT.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(sha256(OUTPUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
