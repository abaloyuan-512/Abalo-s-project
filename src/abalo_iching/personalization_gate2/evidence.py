from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .models import Gate2EvidenceRecord


EVIDENCE_PACKAGE_VERSION = "personalization_gate2_evidence_v1"


def _json_bytes(value: object) -> bytes:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_new_file(path: Path, data: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"证据文件已存在，拒绝覆盖：{path}")
    temp_path = path.with_name(f".{path.name}.tmp")
    if temp_path.exists():
        raise FileExistsError(f"临时证据文件已存在，拒绝覆盖：{temp_path}")
    temp_path.write_bytes(data)
    os.replace(temp_path, path)


class Gate2EvidenceWriter:
    """把 Fake 干跑证据写到仓库外目录；不保存 API Key 或内部 Prompt。"""

    def __init__(self, *, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()

    def write(self, record: Gate2EvidenceRecord, output_root: Path) -> Path:
        resolved_root = output_root.resolve()
        if resolved_root == self.repository_root or self.repository_root in resolved_root.parents:
            raise ValueError("Gate 2 运行证据必须写到 Git 仓库之外")

        run_dir = (resolved_root / record.case_id / record.arm.value).resolve()
        if resolved_root not in run_dir.parents:
            raise ValueError("Gate 2 证据路径不得逃逸输出根目录")
        if run_dir == self.repository_root or self.repository_root in run_dir.parents:
            raise ValueError("Gate 2 运行证据必须写到 Git 仓库之外")
        if run_dir.exists():
            raise FileExistsError(f"证据运行目录已存在，拒绝覆盖：{run_dir}")
        run_dir.mkdir(parents=True, exist_ok=False)

        record_bytes = _json_bytes(record.model_dump(mode="json"))
        record_path = run_dir / "run_record.json"
        _write_new_file(record_path, record_bytes)

        manifest = {
            "package_version": EVIDENCE_PACKAGE_VERSION,
            "case_id": record.case_id,
            "arm": record.arm.value,
            "synthetic_data_confirmed": True,
            "files": {
                "run_record.json": {
                    "sha256": _sha256(record_bytes),
                    "bytes": len(record_bytes),
                    "line_endings": "LF",
                }
            },
        }
        _write_new_file(run_dir / "manifest.json", _json_bytes(manifest))
        return run_dir
