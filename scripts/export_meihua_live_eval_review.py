"""Export non-secret live-eval reports and SHA-256 acceptance ZIP."""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_audit_reports(output_dir:Path):
    branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
    status=subprocess.run(["git","status","--short"],cwd=ROOT,text=True,capture_output=True,check=True).stdout
    (output_dir/"git_status.txt").write_text(f"BRANCH={branch}\nHEAD={head}\nSTATUS_SHORT:\n{status}",encoding="utf-8")
    hits=[]
    pattern=re.compile(r"sk-[A-Za-z0-9_-]{12,}")
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(x in p.parts for x in (".git",".venv","node_modules","dist","__pycache__",".pytest_cache")) or p.suffix in {".xlsx",".zip",".pyc"}: continue
        try: text=p.read_text("utf-8")
        except UnicodeDecodeError: continue
        if pattern.search(text): hits.append(p.relative_to(ROOT).as_posix())
    real=[x for x in hits if "fixture" not in x.lower() and "test" not in x.lower() and "red_team" not in x.lower()]
    if real: raise ValueError(f"REAL_SECRET_LIKE_MATCHES={real}")
    lines=["REAL_SECRET_MATCHES=0"]+[f"TEST_FIXTURE_FALSE_POSITIVE={x}" for x in hits]
    (output_dir/"security_scan.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
def export(output_dir:Path,zip_path:Path):
    if ROOT.resolve() in output_dir.resolve().parents or output_dir.resolve()==ROOT.resolve(): raise ValueError("results must be outside repo")
    write_audit_reports(output_dir)
    with tempfile.TemporaryDirectory() as td:
        stage=Path(td)/"bundle"; stage.mkdir()
        for rel in ["evals/meihua/live_eval_v001","scripts/build_meihua_live_eval_v001.py","scripts/build_meihua_live_eval_final_preflight_artifacts.py","scripts/run_meihua_live_eval_v001.py","scripts/validate_meihua_live_eval_v001.py","scripts/export_meihua_live_eval_review.py","tests/fixtures/live_eval_v001_expected.json","tests/test_live_eval_dataset_v001.py","tests/test_live_eval_budget_guard.py","tests/test_live_eval_runner_mocked.py","tests/test_live_eval_export.py"]:
            src=ROOT/rel; dst=stage/rel
            if src.is_dir(): shutil.copytree(src,dst)
            else: dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        for p in output_dir.rglob("*"):
            if p.is_file() and p.name not in {".env","secrets.toml"} and not p.name.endswith(".inspect.ndjson"):
                target=stage/"results"/p.relative_to(output_dir); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,target)
        manifest=stage/"MANIFEST.txt"; files=sorted(x for x in stage.rglob("*") if x.is_file())
        manifest.write_text("\n".join(f"{x.relative_to(stage).as_posix()}|{x.stat().st_size}|{sha(x)}" for x in files)+"\n",encoding="utf-8")
        zip_path.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
            for x in sorted(stage.rglob("*")):
                if x.is_file(): z.write(x,x.relative_to(stage).as_posix())
    return {"path":str(zip_path.resolve()),"bytes":zip_path.stat().st_size,"sha256":sha(zip_path)}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--zip",type=Path,required=True);a=p.parse_args();print(json.dumps(export(a.output_dir,a.zip),ensure_ascii=False))
