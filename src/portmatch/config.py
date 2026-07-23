from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .paths import app_dir

@dataclass(frozen=True)
class Ship:
    id: str
    name: str
    brand: str = ""

def load_ships(config_path: Path | None = None) -> List[Ship]:
    """Load ships from ships.json (by default beside the app folder)."""
    if config_path is None:
        config_path = app_dir() / "ships.json"

    data = json.loads(config_path.read_text(encoding="utf-8"))
    ships: List[Ship] = []
    for item in data:
        ships.append(Ship(
            id=item["id"],
            name=item["name"],
            brand=item.get("brand", "")
        ))
    return ships
