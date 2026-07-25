from datetime import datetime
from zoneinfo import ZoneInfo

from abalo_iching.application.sites_cultural_reading_v1 import _literal_judgment_note
from abalo_iching.application.sites_meihua_service_v2 import process_sites_meihua_v2_request


FIXED_NOW = datetime(2026, 7, 19, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def _response() -> dict[str, object]:
    return process_sites_meihua_v2_request(
        {
            "contract_version": "SITES_MEIHUA_API_CONTRACT_V2",
            "request_id": "cultural-reading-v1",
            "question_domain": "PROJECT_COOPERATION",
            "decision_goal": "PLAN_NEXT_STEP",
            "time_horizon": "NEXT_30_DAYS",
            "numbers": [13, 14, 15],
            "locale": "zh-CN",
            "client_timestamp": "2026-07-19T10:00:00+08:00",
            "user_acknowledgements": {
                "deterministic_only": True,
                "narrative_unverified": True,
                "structured_question_confirmed": True,
            },
        },
        clock=lambda: FIXED_NOW,
        include_cultural_reading=True,
    )


def test_number_path_explains_three_number_casting_roles_in_user_language() -> None:
    response = _response()
    reading = response["deterministic_result"]["cultural_reading"]
    assert reading["template_version"] == "SITES_CULTURAL_READING_V1"
    assert [(item["input_number"], item["role"], item["result_name"]) for item in reading["number_path"]] == [
        (13, "上卦", "巽"),
        (14, "下卦", "坎"),
        (15, "动爻", "六三"),
    ]
    assert all("三数起卦法" in item["explanation"] for item in reading["number_path"])
    assert all("冻结规则" not in item["explanation"] for item in reading["number_path"])


def test_canonical_texts_and_plain_language_terms_are_separated() -> None:
    reading = _response()["deterministic_result"]["cultural_reading"]
    assert [item["role"] for item in reading["hexagrams"]] == ["本卦", "互卦", "变卦"]
    assert all(item["canonical_text"] and item["source_reference"] for item in reading["hexagrams"])
    assert all(item["plain_note"].startswith("字义小注：") for item in reading["hexagrams"])
    assert reading["moving_line"]["canonical_text"]
    assert [item["title"] for item in reading["terms"]] == [
        "动爻（变化发生在哪里）",
        "体用关系（你与这件事的关系）",
        "旺衰（眼下有多少余力）",
    ]
    assert "内部调整的关口" in reading["terms"][0]["current_effect"]
    assert "具体日期" not in reading["terms"][0]["current_effect"]
    assert "规则阶段" not in reading["terms"][0]["current_effect"]
    assert "议题一方" not in str(reading["terms"])
    assert "体方" not in str(reading["terms"])
    assert "比和（双方五行相同" in str(reading["terms"])


def test_classic_counsel_is_versioned_exact_quote_not_generated_copy() -> None:
    counsel = _response()["deterministic_result"]["cultural_reading"]["classic_counsel"]
    assert counsel == {"quote": "穷则变，变则通，通则久。", "source": "《周易·系辞下》"}


def test_literal_note_explains_tong_ren_judgment_without_applying_it_to_the_question() -> None:
    note = _literal_judgment_note("亨。利涉大川，利君子貞。")
    assert "亨：通达" in note
    assert "利涉大川：适合渡过大河" in note
    assert "利君子貞：有利于君子守正而行" in note
