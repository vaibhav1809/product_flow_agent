from __future__ import annotations

import shutil


def is_available() -> bool:
    return shutil.which("ffmpeg") is not None
