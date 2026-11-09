"""Bridge to the FLOW_SKILL task engine (`flow-task` CLI). Optional: absent engine = clear error, never a crash."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def find() -> Optional[str]:
    """Locate flow-task: $FLOW_TASK_BIN, next to this interpreter (shared venv), then PATH."""
    exe = "flow-task.exe" if sys.platform == "win32" else "flow-task"
    for cand in (os.environ.get("FLOW_TASK_BIN"), Path(sys.executable).parent / exe, shutil.which("flow-task")):
        if cand and Path(cand).is_file():
            return str(cand)
    return None


def run(*args: str, timeout: int = 60) -> str:
    exe = find()
    if not exe:
        return "error: flow-task not installed (install FLOW_SKILL, or set FLOW_TASK_BIN)"
    p = subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout)
    return (p.stdout + p.stderr).strip()
