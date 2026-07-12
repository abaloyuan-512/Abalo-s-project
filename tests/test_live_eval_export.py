import json
from pathlib import Path
from scripts.export_meihua_live_eval_review import export
def test_export_stays_outside_repo_and_has_manifest(tmp_path):
    out=tmp_path/"results";out.mkdir();(out/"attempts.jsonl").write_text("",encoding="utf-8");(out/"summary.json").write_text("{}",encoding="utf-8")
    z=tmp_path/"bundle.zip"; info=export(out,z); assert z.is_file() and info["bytes"]>0
    import zipfile
    with zipfile.ZipFile(z) as a: assert "MANIFEST.txt" in a.namelist()
def test_git_and_security_reports_are_explainable(tmp_path):
    from scripts.export_meihua_live_eval_review import write_audit_reports
    write_audit_reports(tmp_path)
    assert "System.Object[]" not in (tmp_path/"git_status.txt").read_text("utf-8")
    assert "REAL_SECRET_MATCHES=0" in (tmp_path/"security_scan.txt").read_text("utf-8")
