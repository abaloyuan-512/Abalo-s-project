"""Export a self-contained Phase 2B Batch 001 human-review acceptance bundle."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT.parent / "Abalo-s-project_phase2b_batch001_draft_import_review_bundle.zip"

PROJECT_FILES = (
    "README.md",
    "AGENTS.md",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "streamlit_app.py",
    "iching_tools.py",
    "src/abalo_iching/data/meihua/hexagram_canonical_texts_v1.json",
    "src/abalo_iching/data/meihua/interpretation_knowledge_v1.json",
    "scripts/build_meihua_review_batch.py",
    "scripts/build_canonical_texts.py",
    "scripts/build_interpretation_knowledge.py",
    "scripts/import_meihua_editorial_proposal.py",
    "scripts/update_batch001_review_xlsx.mjs",
    "scripts/validate_meihua_review_batch.py",
    "scripts/export_meihua_review_bundle.py",
    "tests/fixtures/knowledge_review_batch_001_expected.json",
    "tests/test_knowledge_review_batch_001.py",
    "tests/test_knowledge_review_state_protection.py",
    "tests/test_batch001_draft_writeback.py",
    "tests/test_canonical_text_knowledge.py",
    "tests/test_interpretation_knowledge.py",
    "docs/specs/meihua_canonical_corrections_v1.json",
)
PROJECT_DIRS = (
    "docs/knowledge_reviews/batch_001",
    "review_data/meihua/batch_001",
)
AUDIT_FILES = (
    "GIT_STATUS.txt",
    "GIT_DIFF.patch",
    "COMPILEALL_OUTPUT.txt",
    "PYTEST_OUTPUT.txt",
    "PHASE1_PYTEST_OUTPUT.txt",
    "COVERAGE_OUTPUT.txt",
    "INTERPRETATION_COVERAGE_OUTPUT.txt",
    "BATCH_VALIDATION_OUTPUT.txt",
    "RED_TEAM_OUTPUT.txt",
    "PIP_CHECK_OUTPUT.txt",
    "SOURCE_COMPARISON_SUMMARY.txt",
    "FORMAL_KNOWLEDGE_HASH_BEFORE_AFTER.txt",
    "H12_CANONICAL_CORRECTION_AUDIT.txt",
    "DRAFT_SELECTION_OUTPUT.txt",
    "WHEEL_OUTPUT.txt",
    "SECURITY_SCAN.txt",
)
FORBIDDEN_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_file(path: Path) -> bool:
    return not any(part in FORBIDDEN_PARTS or part.endswith(".egg-info") for part in path.parts) and path.name not in {
        ".coverage",
        ".env",
        "secrets.toml",
    }


def _copy_project_content(stage: Path) -> None:
    for relative in PROJECT_FILES:
        source = ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for relative in PROJECT_DIRS:
        source_dir = ROOT / relative
        for source in source_dir.rglob("*"):
            if source.is_file() and _safe_file(source):
                target = stage / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)


def _copy_audit(stage: Path, audit_dir: Path) -> None:
    target_dir = stage / "audit"
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in AUDIT_FILES:
        source = audit_dir / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, target_dir / name)


def _write_manifest(stage: Path) -> int:
    manifest = stage / "audit/BUNDLE_MANIFEST.txt"
    lines = ["# relative_path|bytes|sha256", "# Manifest intentionally excludes itself."]
    files = sorted(path for path in stage.rglob("*") if path.is_file() and path != manifest)
    for path in files:
        relative = path.relative_to(stage).as_posix()
        lines.append(f"{relative}|{path.stat().st_size}|{_sha256(path)}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(files)


def export_bundle(audit_dir: Path, output: Path) -> tuple[int, int, str]:
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Acceptance ZIP must be outside the repository")
    with tempfile.TemporaryDirectory(prefix="abalo-phase2b-bundle-") as temp:
        stage = Path(temp) / "bundle"
        stage.mkdir()
        _copy_project_content(stage)
        _copy_audit(stage, audit_dir.resolve())
        file_count = _write_manifest(stage)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
        with zipfile.ZipFile(output, "r") as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Corrupt ZIP member: {bad}")
    return file_count + 1, output.stat().st_size, _sha256(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count, size, digest = export_bundle(args.audit_dir, args.output)
    print(f"ZIP={args.output.resolve()}")
    print(f"FILES={count}")
    print(f"BYTES={size}")
    print(f"SHA256={digest}")
    print("ZIP_VALIDATION=PASS")


if __name__ == "__main__":
    main()
