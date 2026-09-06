from __future__ import annotations

import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from abalo_iching.application.sites_direct_reading_speed_v1 import (
    PROMPT_SUFFIX,
    prepare_concise_reading,
)
from abalo_iching.application.sites_direct_reading_v3 import (
    DirectReadingPreparedRequest,
    prepare_direct_reading_v2_request,
    process_prepared_direct_reading_v2_request,
)
from tests.test_sites_direct_reading_v2 import _complete_text
from tests.test_sites_direct_reading_v3_p9 import FINALE, Provider
from abalo_iching.application.sites_direct_high_product_v1 import build_direct_high_product_presentation


@pytest.mark.parametrize("context", [None, {"discernment_note": "我担心收入不稳定。"}])
def test_concise_profile_preserves_chart_and_untrusted_context(context: dict | None) -> None:
    payload = {"question_text": "我要不要考虑换工作这件事？", "numbers": [5, 6, 3]}
    if context:
        payload["optional_context"] = context
    base = prepare_direct_reading_v2_request(
        payload, clock=lambda: datetime(2026, 9, 6, 12, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    assert isinstance(base, DirectReadingPreparedRequest)
    snapshot = base.model_dump()
    candidate = prepare_concise_reading(base)
    assert base.model_dump() == snapshot
    changed = {key for key in snapshot if getattr(candidate, key) != getattr(base, key)}
    assert changed == {"system_prompt", "prompt_sha256", "prompt_version"}
    assert candidate.prompt_version == base.prompt_version + PROMPT_SUFFIX
    assert "1000至1400" in candidate.system_prompt
    assert "1800至2600" in base.system_prompt
    serialized = json.dumps([candidate.system_prompt, candidate.user_prompt], ensure_ascii=False,
                            sort_keys=True, separators=(",", ":"))
    assert candidate.prompt_sha256 == hashlib.sha256(serialized.encode()).hexdigest().upper()
    assert prepare_concise_reading(candidate) == candidate


@pytest.mark.parametrize("text,expected", [(_complete_text().replace("## 六三", "## 动爻：六三") + FINALE, "SUCCESS"),
                                          (_complete_text(), "BLOCKED_OUTPUT"),
                                          ("## 判断\n太短。" + FINALE, "BLOCKED_OUTPUT")],
                         ids=["valid-mapped", "missing-finale", "too-short"])
def test_same_release_gates_and_single_model_call(text: str, expected: str) -> None:
    base = prepare_direct_reading_v2_request({
        "question_text": "我要不要考虑换工作这件事？", "numbers": [5, 6, 3],
    })
    assert isinstance(base, DirectReadingPreparedRequest)
    candidate = prepare_concise_reading(base)
    provider = Provider(text)
    response = process_prepared_direct_reading_v2_request(candidate, provider=provider)
    assert response["status"] == expected
    assert provider.calls == 1
    assert response["audit"]["prompt_version"] == candidate.prompt_version
    if expected == "SUCCESS":
        build_direct_high_product_presentation(candidate, response)
    else:
        assert response["direct_reading"] is None


def test_unknown_baseline_fails_closed() -> None:
    base = prepare_direct_reading_v2_request({
        "question_text": "我要不要考虑换工作这件事？", "numbers": [5, 6, 3],
    })
    assert isinstance(base, DirectReadingPreparedRequest)
    with pytest.raises(ValueError, match="baseline prompt changed"):
        prepare_concise_reading(base.model_copy(update={"system_prompt": "unknown"}))
