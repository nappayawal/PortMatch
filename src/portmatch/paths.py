from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """
    Returns the folder that contains ships.json and the sqlite DB.
    - In dev: project root (…/PortMatch_Lite_v2_0)
    - In exe: folder where the exe sits
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    # …/PortMatch_Lite_v2_0/src/portmatch/paths.py -> parents[2] is project root
    return Path(__file__).resolve().parents[2]


def ships_json_path() -> Path:
    return app_root() / "ships.json"


def db_path() -> Path:
    return app_root() / "portmatch_lite.db"