from __future__ import annotations

import json
from pathlib import Path

from build_v007_s1_outputs import _render_case


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    evidence = json.loads(
        (ROOT / "outputs" / "v009_canary_real_result.json").read_text(encoding="utf-8")
    )
    if evidence["status"] != "SUCCESS" or evidence["validation_errors"]:
        raise RuntimeError("V009_CANARY_NOT_RELEASABLE")
    provenance = _render_case("V009-CANARY-01", evidence)
    generated_page = ROOT / provenance["page_path"]
    generated_provenance = ROOT / "outputs" / "v007_v009_canary_01_provenance.json"
    target_page = ROOT / "outputs" / "v009_canary_page8_page9.md"
    target_provenance = ROOT / "outputs" / "v009_canary_provenance.json"
    generated_page.replace(target_page)
    provenance["page_path"] = "outputs/v009_canary_page8_page9.md"
    target_provenance.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    generated_provenance.unlink(missing_ok=True)
    print(json.dumps({"case_id": provenance["case_id"], "status": "SUCCESS"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

