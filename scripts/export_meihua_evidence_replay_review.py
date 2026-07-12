"""Export non-secret uncommitted Evidence-ref replay review materials."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_meihua_live_eval_review import write_audit_reports

PROMPT_RESOURCE = "src/abalo_iching/interpretation/prompts/meihua_interpretation_v1.txt"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_paths() -> list[str]:
    lines = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.splitlines()
    return sorted({line[3:].replace("\\", "/") for line in lines if line[3:]})


def export(replay_dir: Path, zip_path: Path) -> dict[str, object]:
    if ROOT.resolve() in replay_dir.resolve().parents or replay_dir.resolve() == ROOT.resolve():
        raise ValueError("replay results must be outside repository")
    if zip_path.exists():
        raise FileExistsError("REVIEW_ZIP_ALREADY_EXISTS")
    write_audit_reports(replay_dir)
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp) / "bundle"
        stage.mkdir()
        for rel in changed_paths():
            src = ROOT / rel
            if not src.is_file() or rel == PROMPT_RESOURCE:
                continue
            dst = stage / "uncommitted_source" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        prompt_diff = subprocess.run(
            ["git", "diff", "--", PROMPT_RESOURCE], cwd=ROOT, text=True, capture_output=True, check=True
        ).stdout
        (stage / "prompt_v5_change.patch").write_text(prompt_diff, encoding="utf-8")
        for rel in (
            "evals/meihua/live_eval_v001/dataset.json",
            "evals/meihua/live_eval_v001/rubric.md",
            "evals/meihua/live_eval_v001/expected_constraints.json",
        ):
            src = ROOT / rel
            dst = stage / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        for src in replay_dir.rglob("*"):
            if src.is_file() and src.name not in {".env", "secrets.toml"} and not src.name.endswith(".inspect.ndjson"):
                dst = stage / "replay_results" / src.relative_to(replay_dir)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        metadata = {
            "prompt_version": "MEIHUA_INTERPRETATION_PROMPT_V5",
            "repair_prompt_version": "MEIHUA_REPAIR_PROMPT_V4",
            "provider_schema_version": "MEIHUA_AI_NARRATIVE_DRAFT_SCHEMA_V3",
            "narrative_assembly_version": "MEIHUA_NARRATIVE_ASSEMBLY_V1",
            "evidence_catalog_version": "MEIHUA_EVIDENCE_REFERENCE_CATALOG_V1",
            "legacy_resolver_version": "MEIHUA_LEGACY_EVIDENCE_RESOLVER_V1",
            "legacy_deduplicator_version": "MEIHUA_LEGACY_EVIDENCE_DEDUPLICATOR_V1",
            "api_calls_added": 0,
            "original_responses_included": False,
        }
        (stage / "VERSION_AUDIT.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest = stage / "MANIFEST.txt"
        files = sorted(path for path in stage.rglob("*") if path.is_file())
        manifest.write_text(
            "\n".join(
                f"{path.relative_to(stage).as_posix()}|{path.stat().st_size}|{sha256(path)}" for path in files
            ) + "\n",
            encoding="utf-8",
        )
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
    return {"path": str(zip_path.resolve()), "bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-dir", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.replay_dir, args.zip), ensure_ascii=False))
