from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import uuid


TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp_test_workspace"


@contextmanager
def workspace_temp_dir(prefix: str):
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TMP_ROOT / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
