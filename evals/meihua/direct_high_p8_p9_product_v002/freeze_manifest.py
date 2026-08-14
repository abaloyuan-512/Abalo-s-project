from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "evals/meihua/direct_high_p8_p9_product_v002"
OUTPUT = STAGE / "candidate_manifest.json"

CANDIDATE_FILES = (
    "evals/meihua/direct_high_p8_p9_product_v002/acceptance_contract.json",
    "evals/meihua/direct_high_p8_p9_product_v002/scope_lock.json",
    "evals/meihua/direct_high_p8_p9_product_v002/decision_log.md",
    "evals/meihua/direct_high_p8_p9_product_v002/build_offline_evidence.py",
    "evals/meihua/direct_high_p8_p9_product_v002/route_boundary_probe.mjs",
    "evals/meihua/direct_high_p8_p9_product_v002/test_evidence.py",
    "evals/meihua/direct_high_p8_p9_product_v002/offline_ledger.json",
    "evals/meihua/direct_high_p8_p9_product_v002/verification_result.json",
    "evals/meihua/direct_high_p8_p9_product_v002/freeze_manifest.py",
)

AUTHORITY_FILES = (
    # V001 frozen candidate and its final FAIL evidence.
    "evals/meihua/direct_high_p8_p9_product_v001/candidate_manifest.json",
    "evals/meihua/direct_high_p8_p9_product_v001/offline_ledger.json",
    "evals/meihua/direct_high_p8_p9_product_v001/verification_result.json",
    "evals/meihua/direct_high_p8_p9_product_v001/independent_acceptance_result.json",
    "evals/meihua/direct_high_p8_p9_product_v001/final_outcome.json",
    # Historical FAIL/STOP chain.
    "outputs/v007_s1_stage_summary.json",
    "evals/meihua/direct_reading_v2_stability_v008/canary_outcome.json",
    "evals/meihua/direct_reading_v2_stability_v010/final_outcome.json",
    "evals/meihua/direct_reading_v2_stability_v010/independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_conditional_router_v012/final_outcome.json",
    "evals/meihua/direct_reading_v2_conditional_router_v012/independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_conditional_router_v013/design_stop.json",
    "evals/meihua/direct_reading_v2_parse_exception_v019/final_outcome.json",
    "evals/meihua/direct_reading_v2_parse_exception_v019/independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_parse_exception_v020/final_outcome.json",
    "evals/meihua/direct_reading_v2_parse_exception_v020/independent_acceptance_result.json",
    "outputs/v022_classified_router_only_live_ledger.json",
    "evals/meihua/direct_reading_v2_parse_exception_v021/v022_final_outcome.json",
    "evals/meihua/direct_reading_v2_parse_exception_v021/v022_independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_sdk_runtime_diagnostic_v023/candidate_manifest.json",
    "evals/meihua/direct_reading_v2_sdk_runtime_diagnostic_v023/final_outcome.json",
    "evals/meihua/direct_reading_v2_sdk_runtime_diagnostic_v023/independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_sdk_authoritative_origin_v024/design_stop.json",
    # Positive Direct Reading anchors.
    "outputs/v009_canary_real_result.json",
    "evals/meihua/direct_reading_v2_stability_v009/candidate_manifest.json",
    "evals/meihua/direct_reading_v2_stability_v009/final_outcome.json",
    "outputs/v011_stability_run_ledger.json",
    "evals/meihua/direct_reading_v2_stability_v011/candidate_manifest.json",
    "evals/meihua/direct_reading_v2_stability_v011/independent_acceptance_result.json",
    "evals/meihua/direct_reading_v2_stability_v011/live_final_outcome.json",
    "evals/meihua/direct_reading_v2_stability_v011/live_independent_acceptance_result.json",
    # Frozen service, rules, legacy entries, and V001 product/API/UI bytes.
    "src/abalo_iching/application/sites_direct_reading_v2.py",
    "src/abalo_iching/application/sites_direct_high_product_v1.py",
    "scripts/run_hosted_api.py",
    "sites/hosted-app/package.json",
    "sites/hosted-app/app/api/direct-reading/v2/route.ts",
    "sites/hosted-app/app/direct-reading-v2-preview/page.tsx",
    "sites/hosted-app/app/direct-reading-v2-preview/page.module.css",
    "sites/hosted-app/app/direct-reading-v2-preview/ProductPresentation.tsx",
    "docs/specs/MEIHUA_RULE_SPEC_V1.md",
    "docs/specs/MEIHUA_DATA_CONTRACT_V1.md",
    "docs/specs/MEIHUA_INTERPRETATION_SPEC_V1.md",
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


def verify_v001_candidate() -> int:
    path = ROOT / "evals/meihua/direct_high_p8_p9_product_v001/candidate_manifest.json"
    if sha256(path) != "3A8B644C2D685F208EA815DE60A15E3785B1EB07C8F10FC4FCD42DE8DE498B4D":
        raise RuntimeError("V001_MANIFEST_DRIFT")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for entry in manifest["candidate_files"]:
        if sha256(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"V001_CANDIDATE_DRIFT:{entry['path']}")
    return len(manifest["candidate_files"])


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("CANDIDATE_MANIFEST_ALREADY_EXISTS")
    v001_matches = verify_v001_candidate()
    manifest = {
        "stage_id": "DIRECT_HIGH_P8_P9_PRODUCT_V002_EVIDENCE",
        "contract_id": "DRV2-P8-P9-DIRECT-HIGH-V002-EVIDENCE-COMPLETENESS-OFFLINE-ACCEPTANCE-V1",
        "status": "FROZEN_OFFLINE_EVIDENCE_CANDIDATE_AWAITING_INDEPENDENT_QA",
        "candidate_files": entries(CANDIDATE_FILES),
        "authority_files": entries(AUTHORITY_FILES),
        "offline_ledger_sha256": sha256(STAGE / "offline_ledger.json"),
        "v001_candidate_hashes": {"matched": v001_matches, "denominator": v001_matches, "mismatched": 0},
        "verification": {
            "v002_specialty": "4 passed",
            "v002_plus_direct_reading_inherited_focused": "148 passed + 1 isolated environmental rerun passed",
            "sites_build": "PASS",
            "sites_tests": "49 passed",
            "full_pytest": "1459 passed",
        },
        "router_calls": 0,
        "live_calls": 0,
        "deployment": False,
        "production": False,
        "default_replacement": False,
        "p9_artwork": False,
    }
    OUTPUT.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(sha256(OUTPUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
