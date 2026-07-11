import json
from importlib.resources import files

from abalo_iching.interpretation.knowledge import load_canonical_texts
from abalo_iching.meihua.hexagrams import hexagram_from_number


def test_canonical_texts_cover_64_hexagrams_and_384_lines():
    records = load_canonical_texts()
    assert len(records) == 64
    assert sum(len(item.lines) for item in records) == 384
    assert {item.king_wen_number for item in records} == set(range(1, 65))


def test_every_hexagram_has_exactly_six_unique_line_positions():
    for item in load_canonical_texts():
        assert len(item.lines) == 6
        assert {line.line_position for line in item.lines} == set(range(1, 7))
        assert [line.line_name for line in item.lines] == ["初", "二", "三", "四", "五", "上"]


def test_names_and_sequence_match_frozen_phase1_data():
    assert [(item.king_wen_number, item.hexagram_name) for item in load_canonical_texts()] == [
        (number, hexagram_from_number(number).name_zh) for number in range(1, 65)
    ]


def test_every_canonical_record_has_traceable_public_source_fields():
    for item in load_canonical_texts():
        assert item.canonical_judgment_text
        assert item.source_name
        assert item.source_reference.startswith("https://")
        assert item.source_accessed_at == "2026-07-11"
        assert item.canonical_data_version == "MEIHUA_CANONICAL_TEXTS_V1"
        for line in item.lines:
            assert line.canonical_line_text
            assert line.source_reference == item.source_reference


def test_source_policy_records_primary_hash_and_cross_checks():
    payload = json.loads(files("abalo_iching.data.meihua").joinpath("hexagram_canonical_texts_v1.json").read_text("utf-8"))
    assert payload["source_sha256"] == "193BF6C89170F54C0C64EE21839EBE3B5F8E34E4C5A7BC4BDF55055855DF4DFF"
    assert "ctext.org" in payload["cross_check_sources"][0]
    assert "wikisource.org" in payload["cross_check_sources"][1]
    assert payload["cross_check_status"] == "PENDING_HUMAN_LINE_BY_LINE_REVIEW"
    assert payload["normalization_rules"] == [
        "trim whitespace",
        "無 → 无",
        "punctuation normalization",
        "special source formatting repair for hexagram 8",
    ]


def test_canonical_scope_excludes_commentaries_and_use_nine_six():
    for item in load_canonical_texts():
        assert not item.canonical_judgment_text.startswith(("《彖》", "《象》", "文言"))
        assert all(not line.canonical_line_text.startswith(("《彖》", "《象》", "用九", "用六")) for line in item.lines)
