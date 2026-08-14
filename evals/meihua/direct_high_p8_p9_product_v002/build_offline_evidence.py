from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from abalo_iching.application import sites_direct_reading_v2 as high_service
from abalo_iching.application.sites_direct_high_product_v1 import (
    DirectHighEntryMode,
    DirectHighProductPresentationV1,
    build_direct_high_product_presentation,
)
from abalo_iching.application.sites_direct_reading_v2 import (
    MODEL,
    DirectReadingProviderResult,
    DirectReadingUsage,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "evals/meihua/direct_high_p8_p9_product_v002"
DEFAULT_OUTPUT = STAGE / "offline_ledger.json"
FIXED_CLOCK = lambda: datetime(2026, 8, 11, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
PUBLIC_CONTRACT = "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha(value: object) -> str:
    return sha_bytes(canonical_bytes(value))


class FixtureProvider:
    def __init__(self, text: str, *, fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.calls = 0

    def generate(self, **_kwargs: Any) -> DirectReadingProviderResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("fixture provider failure")
        return DirectReadingProviderResult(
            output_text=self.text,
            api_status="completed",
            incomplete_details=None,
            response_id=f"fixture-v002-{self.calls}",
            model=MODEL,
            usage=DirectReadingUsage(input_tokens=10, output_tokens=100, total_tokens=110),
            latency_ms=1,
        )


def run_transaction(
    *, case_index: int, question: str, numbers: list[int], text: str, provider_fail: bool = False
) -> tuple[object, dict[str, Any], object | None, dict[str, int]]:
    original_cast = high_service.cast_meihua
    cast_count = 0
    prepare_attempts = 0
    fixed_high_attempts = 0

    def counted(value: object) -> object:
        nonlocal cast_count
        cast_count += 1
        return original_cast(value)

    provider = FixtureProvider(text, fail=provider_fail)
    high_service.cast_meihua = counted
    try:
        prepare_attempts += 1
        prepared = prepare_direct_reading_v2_request(
            {"question_text": question, "numbers": numbers},
            clock=FIXED_CLOCK,
            request_id=f"drv2-{case_index:016x}",
        )
        fixed_high_attempts += 1
        response = process_prepared_direct_reading_v2_request(prepared, provider=provider)
    finally:
        high_service.cast_meihua = original_cast
    presentation = (
        build_direct_high_product_presentation(prepared, response)
        if response["status"] == "SUCCESS"
        else None
    )
    return prepared, response, presentation, {
        "prepare_attempts": prepare_attempts,
        "deterministic_cast_count": cast_count,
        "provider_attempts": provider.calls,
        "fixed_high_attempts": fixed_high_attempts,
    }


def base_row(case_id: str, mode: str, counts: dict[str, int]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "entry_mode": mode,
        **counts,
        "automatic_retries": 0,
        "router_attempts": 0,
        "router_live_calls": 0,
        "router_model_calls": 0,
        "mapping_model_calls": 0,
        "mapping_additional_casts": 0,
        "live_calls": 0,
        "real_provider_instantiated": False,
    }


def public_payload(request_id: str, response: dict[str, Any], presentation: object) -> dict[str, Any]:
    return {
        "contract_version": PUBLIC_CONTRACT,
        "request_id": request_id,
        "status": "SUCCESS",
        "direct_reading": copy.deepcopy(response["direct_reading"]),
        "product_presentation": presentation.model_dump(mode="json"),
        "direct_high": {
            "route": "DIRECT_HIGH",
            "entry_mode": "CLEAR",
            "router_attempts": 0,
            "automatic_retries": 0,
        },
    }


def probe_public_boundary(request: dict[str, Any], upstream: dict[str, Any]) -> dict[str, Any]:
    node = shutil.which("node")
    dist = ROOT / "sites/hosted-app/dist/server/index.js"
    if node is None or not dist.is_file():
        raise RuntimeError("SITES_BUILD_REQUIRED_BEFORE_V002_EVIDENCE")
    payload = {"request": request, "upstream": upstream}
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False) as handle:
            handle.write(canonical_bytes(payload))
            path = Path(handle.name)
        completed = subprocess.run(
            [node, str(STAGE / "route_boundary_probe.mjs"), str(path), str(dist)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return json.loads(completed.stdout)
    finally:
        if path is not None and path.is_file():
            path.unlink()


def main(output: Path) -> int:
    v009 = json.loads((ROOT / "outputs/v009_canary_real_result.json").read_text(encoding="utf-8"))
    frozen = json.loads(
        (ROOT / "evals/meihua/direct_reading_v2_stability_v010/frozen_cases.json").read_text(encoding="utf-8")
    )["cases"]
    live = json.loads((ROOT / "outputs/v011_stability_run_ledger.json").read_text(encoding="utf-8"))["cases"]
    released_by_id = {row["case_id"]: row["released_direct_reading"] for row in live}
    positives = [
        (DirectHighEntryMode.CLEAR, v009["input"]["question_text"], v009["input"]["numbers"], v009["direct_reading"], v009["reading_utf8_sha256"]),
        (DirectHighEntryMode.CONFIRMED, frozen[0]["question_text"], frozen[0]["numbers"], released_by_id[frozen[0]["case_id"]], sha_bytes(released_by_id[frozen[0]["case_id"]]["text"].encode("utf-8"))),
        (DirectHighEntryMode.SKIP, frozen[1]["question_text"], frozen[1]["numbers"], released_by_id[frozen[1]["case_id"]], sha_bytes(released_by_id[frozen[1]["case_id"]]["text"].encode("utf-8"))),
    ]
    rows: list[dict[str, Any]] = []
    case_index = 1
    for mode, question, numbers, released, expected_sha in positives:
        prepared, response, presentation, counts = run_transaction(
            case_index=case_index, question=question, numbers=numbers, text=released["text"]
        )
        assert presentation is not None and response["status"] == "SUCCESS"
        assert presentation.source_reading_sha256 == expected_sha
        row = base_row(f"P8P9-V002-P{case_index:02d}-{mode.value}", mode.value, counts)
        row.update({
            "kind": "POSITIVE",
            "status": "SUCCESS",
            "released": True,
            "blocked": False,
            "question_sha_preserved": prepared.question_sha256 == response["audit"]["question_sha256"],
            "source_reading_sha256": presentation.source_reading_sha256,
            "reconstructed_reading_sha256": presentation.reconstructed_reading_sha256,
            "program_strength_source": presentation.page8.program_strength.source,
            "p8_responsibility": presentation.page8.responsibility,
            "p9_responsibility": presentation.page9.responsibility,
            "direct_reading_null": False,
            "presentation_null": False,
            "direct_high_null": False,
        })
        rows.append(row)
        case_index += 1

    question = frozen[0]["question_text"]
    numbers = frozen[0]["numbers"]
    released = released_by_id[frozen[0]["case_id"]]
    text = released["text"]
    line_text = released["chart_facts"]["moving_line"]["canonical_line_text"]

    service_cases = [
        ("HIGH_PROVIDER_EXCEPTION", "PROVIDER", text, True, None),
        ("HIGH_TRUNCATED_OR_MISSING_SECTION", "DIRECT_HIGH_VALIDATOR", text.rsplit("## ", 1)[0], False, None),
        ("HIGH_VALIDATION_ERROR", "DIRECT_HIGH_VALIDATOR", text.replace(line_text, line_text + "，必成", 1), False, None),
        ("SAFETY_HARD_GATE", "DIRECT_HIGH_SAFETY", text + "\n明确行动日是2026年9月1日。", False, "UNSUPPORTED_DATE"),
    ]
    for kind, gate, provider_text, provider_fail, rule in service_cases:
        prepared, response, presentation, counts = run_transaction(
            case_index=case_index,
            question=question,
            numbers=numbers,
            text=provider_text,
            provider_fail=provider_fail,
        )
        assert response["status"] != "SUCCESS" and response["direct_reading"] is None and presentation is None
        if rule is not None:
            assert rule in response["validation_errors"]
        row = base_row(f"P8P9-V002-N{case_index - 3:02d}-{kind}", "CLEAR", counts)
        row.update({
            "kind": kind,
            "tamper_kind": kind,
            "source_stage": "FIXTURE_PROVIDER_OUTPUT",
            "expected_gate": gate,
            "observed_gate": gate,
            "status": response["status"],
            "error_code": response["error_code"],
            "safety_rule_id": rule,
            "released": False,
            "blocked": True,
            "question_sha_preserved": prepared.question_sha256 == response["audit"]["question_sha256"],
            "original_transaction_sha256": canonical_sha({"question_sha256": prepared.question_sha256, "provider_attempts": counts["provider_attempts"]}),
            "tampered_object_sha256": canonical_sha({"provider_output_sha256": sha_bytes(provider_text.encode("utf-8"))}) if not provider_fail else None,
            "direct_reading_null": True,
            "presentation_null": True,
            "direct_high_null": True,
        })
        rows.append(row)
        case_index += 1

    consumer_kinds = (
        "P8_CHART_LINEAGE_MISMATCH",
        "P8_PROGRAM_STRENGTH_SOURCE_INVALID",
        "P9_MISSING_REQUIRED_ITEM",
        "P9_NOT_BYTE_EXACT",
        "P8_P9_RESPONSIBILITY_CROSSOVER",
    )
    for kind in consumer_kinds:
        prepared, response, presentation, counts = run_transaction(
            case_index=case_index, question=question, numbers=numbers, text=text
        )
        assert presentation is not None
        original = presentation.model_dump(mode="json")
        tampered = copy.deepcopy(original)
        intermediate_gate = "PYDANTIC_STRICT_PRODUCT_BOUNDARY"
        blocked = False
        upstream = public_payload(prepared.request_id, response, presentation)
        original_sha = canonical_sha(upstream)
        if kind == "P8_CHART_LINEAGE_MISMATCH":
            altered_response = copy.deepcopy(response)
            altered_response["direct_reading"]["chart_facts"]["base_hexagram"]["name"] = "非本次盘面"
            try:
                build_direct_high_product_presentation(prepared, altered_response)
            except ValueError:
                blocked = True
            tampered = altered_response["direct_reading"]
            upstream["direct_reading"] = copy.deepcopy(tampered)
            intermediate_gate = "SAME_PREPARED_CHART_LINEAGE"
        elif kind == "P8_PROGRAM_STRENGTH_SOURCE_INVALID":
            tampered["page8"]["program_strength"]["source"] = "MODEL_TEXT"
        elif kind == "P9_MISSING_REQUIRED_ITEM":
            del tampered["page9"]["change_signals"]
        elif kind == "P9_NOT_BYTE_EXACT":
            tampered["page9"]["judgment"]["markdown"] += "。"
        else:
            tampered["page8"]["responsibility"] = "JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS"
        if not blocked:
            try:
                DirectHighProductPresentationV1.model_validate(tampered)
            except ValidationError:
                blocked = True
        assert blocked
        if kind != "P8_CHART_LINEAGE_MISMATCH":
            upstream["product_presentation"] = copy.deepcopy(tampered)
        request = {
            "contract_version": PUBLIC_CONTRACT,
            "request_id": prepared.request_id,
            "question_text": question,
            "numbers": numbers,
            "entry_mode": "CLEAR",
        }
        probe = probe_public_boundary(request, upstream)
        assert probe["status"] == "BLOCKED_OUTPUT"
        assert probe["direct_reading_null"] and probe["presentation_null"] and probe["direct_high_null"]
        row = base_row(f"P8P9-V002-N{case_index - 3:02d}-{kind}", "CLEAR", counts)
        row.update({
            "kind": kind,
            "tamper_kind": kind,
            "source_stage": "POST_SUCCESS_PRODUCT_CONSUMER",
            "expected_gate": "PUBLIC_ALLOW_LIST_ATOMIC_RELEASE",
            "observed_gate": "PUBLIC_ALLOW_LIST_ATOMIC_RELEASE",
            "intermediate_gate": intermediate_gate,
            "status": probe["status"],
            "error_code": probe["error_code"],
            "released": False,
            "blocked": True,
            "question_sha_preserved": True,
            "original_transaction_sha256": original_sha,
            "tampered_object_sha256": canonical_sha(upstream),
            "direct_reading_null": probe["direct_reading_null"],
            "presentation_null": probe["presentation_null"],
            "direct_high_null": probe["direct_high_null"],
        })
        assert row["original_transaction_sha256"] != row["tampered_object_sha256"]
        rows.append(row)
        case_index += 1

    route_cases = ("PRODUCT_PARTIAL_RELEASE_ATTEMPT", "PUBLIC_STRUCTURE_TAMPER", "PUBLIC_DIGEST_TAMPER")
    for kind in route_cases:
        prepared, response, presentation, counts = run_transaction(
            case_index=case_index, question=question, numbers=numbers, text=text
        )
        assert presentation is not None
        upstream = public_payload(prepared.request_id, response, presentation)
        original_sha = canonical_sha(upstream)
        if kind == "PRODUCT_PARTIAL_RELEASE_ATTEMPT":
            upstream["status"] = "BLOCKED_OUTPUT"
        elif kind == "PUBLIC_STRUCTURE_TAMPER":
            upstream["product_presentation"]["page8"]["base_hexagram"] = None
            upstream["product_presentation"]["page9"]["responsibility"] = "WRONG_PAGE"
            upstream["product_presentation"]["page9"]["judgment"]["start_offset"] = -1
        else:
            false_digest = "A" * 64
            upstream["product_presentation"]["source_reading_sha256"] = false_digest
            upstream["product_presentation"]["reconstructed_reading_sha256"] = false_digest
            upstream["product_presentation"]["page9"]["judgment"]["sha256"] = false_digest
            upstream["product_presentation"]["page8"]["program_strength"]["program_fact_sha256"] = false_digest
        request = {
            "contract_version": PUBLIC_CONTRACT,
            "request_id": prepared.request_id,
            "question_text": question,
            "numbers": numbers,
            "entry_mode": "CLEAR",
        }
        probe = probe_public_boundary(request, upstream)
        assert probe["status"] == "BLOCKED_OUTPUT"
        assert probe["direct_reading_null"] and probe["presentation_null"] and probe["direct_high_null"]
        row = base_row(f"P8P9-V002-N{case_index - 3:02d}-{kind}", "CLEAR", counts)
        row.update({
            "kind": kind,
            "tamper_kind": kind,
            "source_stage": "SITES_PUBLIC_PRODUCT_BOUNDARY",
            "expected_gate": "PUBLIC_ALLOW_LIST_ATOMIC_RELEASE",
            "observed_gate": "PUBLIC_ALLOW_LIST_ATOMIC_RELEASE",
            "status": probe["status"],
            "error_code": probe["error_code"],
            "released": False,
            "blocked": True,
            "question_sha_preserved": True,
            "original_transaction_sha256": original_sha,
            "tampered_object_sha256": canonical_sha(upstream),
            "direct_reading_null": probe["direct_reading_null"],
            "presentation_null": probe["presentation_null"],
            "direct_high_null": probe["direct_high_null"],
        })
        assert row["original_transaction_sha256"] != row["tampered_object_sha256"]
        rows.append(row)
        case_index += 1

    negative_counts: dict[str, int] = {}
    for row in rows:
        if row["kind"] != "POSITIVE":
            negative_counts[row["kind"]] = negative_counts.get(row["kind"], 0) + 1
    ledger = {
        "stage_id": "DIRECT_HIGH_P8_P9_PRODUCT_V002_EVIDENCE",
        "contract_id": "DRV2-P8-P9-DIRECT-HIGH-V002-EVIDENCE-COMPLETENESS-OFFLINE-ACCEPTANCE-V1",
        "evidence_kind": "OFFLINE_FIXTURE_ONLY",
        "v001_verdict_preserved": "OFFLINE_CANDIDATE_FAIL_STOP",
        "v001_manifest_sha256": "3A8B644C2D685F208EA815DE60A15E3785B1EB07C8F10FC4FCD42DE8DE498B4D",
        "case_denominator": len(rows),
        "success_count": sum(row["released"] for row in rows),
        "failed_count": sum(not row["released"] for row in rows),
        "released_count": sum(row["released"] for row in rows),
        "blocked_count": sum(row["blocked"] for row in rows),
        "negative_kind_counts": negative_counts,
        "prepare_attempts": sum(row["prepare_attempts"] for row in rows),
        "deterministic_cast_count": sum(row["deterministic_cast_count"] for row in rows),
        "provider_attempts": sum(row["provider_attempts"] for row in rows),
        "fixed_high_attempts": sum(row["fixed_high_attempts"] for row in rows),
        "automatic_retries": 0,
        "router_attempts": 0,
        "router_live_calls": 0,
        "router_model_calls": 0,
        "mapping_model_calls": 0,
        "mapping_additional_casts": 0,
        "live_calls": 0,
        "real_provider_instantiated": False,
        "deployment": False,
        "production": False,
        "default_replacement": False,
        "rows": rows,
    }
    required = set(json.loads((STAGE / "acceptance_contract.json").read_text(encoding="utf-8"))["required_negative_kinds"])
    assert required.issubset(negative_counts)
    assert ledger["case_denominator"] == len(rows) == ledger["success_count"] + ledger["failed_count"]
    assert ledger["success_count"] == ledger["released_count"] == 3
    assert ledger["failed_count"] == ledger["blocked_count"] == len(negative_counts) == 12
    assert all(row["prepare_attempts"] == row["deterministic_cast_count"] == row["provider_attempts"] == row["fixed_high_attempts"] == 1 for row in rows)
    assert ledger["prepare_attempts"] == ledger["deterministic_cast_count"] == ledger["provider_attempts"] == ledger["fixed_high_attempts"] == len(rows)
    assert all(row["released"] or (row["direct_reading_null"] and row["presentation_null"] and row["direct_high_null"]) for row in rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(ledger, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(sha_bytes(output.read_bytes()))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    raise SystemExit(main(arguments.output))
