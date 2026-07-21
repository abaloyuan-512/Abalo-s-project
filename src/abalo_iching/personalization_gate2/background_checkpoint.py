from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .models import CASE_ID_PATTERN, ExperimentArm, Gate2BackgroundCheckpoint


CHECKPOINT_VERSION = "personalization_gate2_background_checkpoint_v1"


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"拒绝覆盖阶段 C.1后台检查点：{path}")
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"拒绝覆盖阶段 C.1临时检查点：{temporary}")
    temporary.write_bytes(data)
    os.replace(temporary, path)


class Gate2BackgroundCheckpointWriter:
    """把响应ID和轮询状态逐条写入仓库外不可覆盖文件。"""

    def __init__(
        self,
        *,
        repository_root: Path,
        output_root: Path,
        case_id: str,
        arm: ExperimentArm,
    ) -> None:
        repository = repository_root.resolve()
        output = output_root.resolve()
        if output == repository or repository in output.parents:
            raise ValueError("阶段 C.1后台检查点必须位于Git仓库之外")
        if re.fullmatch(CASE_ID_PATTERN, case_id) is None:
            raise ValueError("阶段 C.1后台检查点case_id不安全")
        self.directory = (
            output / "background_checkpoints" / case_id / arm.value
        ).resolve()
        if output not in self.directory.parents:
            raise ValueError("阶段 C.1后台检查点路径不得逃逸输出目录")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.case_id = case_id
        self.arm = arm
        existing_sequences = [
            int(path.stem.removeprefix("checkpoint_"))
            for path in self.directory.glob("checkpoint_*.json")
            if path.stem.removeprefix("checkpoint_").isdigit()
        ]
        self._sequence = max(existing_sequences, default=-1) + 1

    def write(self, checkpoint: Gate2BackgroundCheckpoint) -> Path:
        path = self.directory / f"checkpoint_{self._sequence:04d}.json"
        payload = {
            "checkpoint_version": CHECKPOINT_VERSION,
            "case_id": self.case_id,
            "arm": self.arm.value,
            "checkpoint": checkpoint.model_dump(mode="json"),
        }
        data = _json_bytes(payload)
        _write_new(path, data)
        digest = hashlib.sha256(data).hexdigest()
        _write_new(
            path.with_suffix(".sha256"),
            f"{digest}  {path.name}\n".encode("ascii"),
        )
        self._sequence += 1
        return path

    def latest(self) -> Gate2BackgroundCheckpoint | None:
        paths = sorted(self.directory.glob("checkpoint_*.json"))
        if not paths:
            return None
        response_ids: set[str] = set()
        latest: Gate2BackgroundCheckpoint | None = None
        for path in paths:
            hash_path = path.with_suffix(".sha256")
            if not hash_path.exists():
                raise ValueError(f"后台检查点缺少SHA-256文件：{path.name}")
            expected = hash_path.read_text(encoding="ascii").split()[0]
            data = path.read_bytes()
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected:
                raise ValueError(f"后台检查点SHA-256不匹配：{path.name}")
            payload = json.loads(data.decode("utf-8"))
            if payload.get("checkpoint_version") != CHECKPOINT_VERSION:
                raise ValueError("后台检查点版本不匹配")
            if payload.get("case_id") != self.case_id:
                raise ValueError("后台检查点case_id不匹配")
            if payload.get("arm") != self.arm.value:
                raise ValueError("后台检查点arm不匹配")
            latest = Gate2BackgroundCheckpoint.model_validate(payload["checkpoint"])
            response_ids.add(latest.response_id)
        if len(response_ids) != 1:
            raise ValueError("同一后台检查点目录出现多个响应ID")
        return latest
