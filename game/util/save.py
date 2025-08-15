import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List


# Project root (../../.. from this file)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SAVE_FILE = os.path.join(PROJECT_ROOT, "save_game.json")  # legacy single-slot autosave
SAVE_DIR = os.path.join(PROJECT_ROOT, "saves")


def _ensure_save_dir():
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
    except Exception:
        pass


def load_save() -> Optional[Dict[str, Any]]:
    """
    Legacy single-slot loader (autosave). Kept for backwards compatibility.
    """
    try:
        if not os.path.exists(SAVE_FILE):
            return None
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # Corrupt or unreadable save — ignore for MVP
        return None


def write_save(data: Dict[str, Any]) -> None:
    """
    Legacy single-slot writer (autosave). Kept for backwards compatibility.
    """
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        # Non-fatal for MVP
        pass


def delete_save() -> None:
    """
    Delete the legacy autosave file only. Named saves are not affected.
    """
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
    except Exception:
        # Non-fatal
        pass


def _slugify(name: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    slug = ''.join(ch if ch in allowed else '-' for ch in name.strip())
    # Collapse multiple dashes
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-') or 'save'


def write_named_save(name: str, data: Dict[str, Any]) -> Optional[str]:
    """
    Write a new named save file under SAVE_DIR. The file includes metadata
    fields 'name' and 'created_at' (ISO). Returns the path or None on error.
    """
    try:
        _ensure_save_dir()
        now = datetime.now()
        iso = now.isoformat(timespec='seconds')
        payload = dict(data)
        payload["name"] = str(name or "Save")
        payload["created_at"] = iso
        # Unique filename prefix with timestamp
        fname = f"{now.strftime('%Y%m%d-%H%M%S')}_{_slugify(payload['name'])}.json"
        fpath = os.path.join(SAVE_DIR, fname)
        with open(fpath, 'w') as f:
            json.dump(payload, f)
        return fpath
    except Exception:
        return None


def load_save_file(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def list_save_slots() -> List[Dict[str, Any]]:
    """
    Returns a list of save descriptors sorted by most recent first.
    Each descriptor: { 'path', 'name', 'created_at', 'mtime', 'is_autosave' }
    Includes legacy autosave if present.
    """
    items: List[Dict[str, Any]] = []
    try:
        _ensure_save_dir()
        # Named saves
        for fname in sorted(os.listdir(SAVE_DIR)):
            if not fname.lower().endswith('.json'):
                continue
            path = os.path.join(SAVE_DIR, fname)
            try:
                data = load_save_file(path) or {}
                name = str(data.get('name') or os.path.splitext(fname)[0])
                created_at = str(data.get('created_at') or '')
                mtime = os.path.getmtime(path)
                items.append({
                    'path': path,
                    'name': name,
                    'created_at': created_at,
                    'mtime': mtime,
                    'is_autosave': False,
                })
            except Exception:
                continue
        # Legacy autosave as a slot
        if os.path.exists(SAVE_FILE):
            try:
                data = load_save() or {}
                name = str(data.get('name') or 'Autosave')
                created_at = str(data.get('created_at') or '')
                mtime = os.path.getmtime(SAVE_FILE)
                items.append({
                    'path': SAVE_FILE,
                    'name': name,
                    'created_at': created_at,
                    'mtime': mtime,
                    'is_autosave': True,
                })
            except Exception:
                pass
        # Sort by mtime (descending)
        items.sort(key=lambda it: it.get('mtime', 0), reverse=True)
    except Exception:
        pass
    return items


def has_any_saves() -> bool:
    try:
        return len(list_save_slots()) > 0
    except Exception:
        return False
