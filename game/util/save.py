import json
import os
from typing import Optional, Dict, Any


SAVE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "save_game.json")


def load_save() -> Optional[Dict[str, Any]]:
    try:
        if not os.path.exists(SAVE_FILE):
            return None
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # Corrupt or unreadable save — ignore for MVP
        return None


def write_save(data: Dict[str, Any]) -> None:
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        # Non-fatal for MVP
        pass
