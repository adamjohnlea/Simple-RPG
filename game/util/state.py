from typing import Dict


class GameState:
    """
    Extremely simple global game state for MVP gameplay additions.
    Not persisted yet (kept for current run only).
    """
    coins: int = 10
    inventory: Dict[str, int] = {"seeds": 0}
    flags: Dict[str, bool] = {
        "quest_started": False,
        "quest_completed": False,
    }
    upgrades: Dict[str, bool] = {
        "boots": False,
    }
    # Session-only farming persistence: per-plot state keyed by plot id
    # Example entry: {"plot_1": {"state": "planted", "planted_minutes": 123.0}}
    farming_plots: Dict[str, Dict] = {}

    @classmethod
    def add_item(cls, item_id: str, qty: int = 1):
        cls.inventory[item_id] = cls.inventory.get(item_id, 0) + qty

    @classmethod
    def remove_item(cls, item_id: str, qty: int = 1) -> bool:
        have = cls.inventory.get(item_id, 0)
        if have < qty:
            return False
        new_qty = have - qty
        if new_qty <= 0:
            cls.inventory.pop(item_id, None)
        else:
            cls.inventory[item_id] = new_qty
        return True

    @classmethod
    def has_item(cls, item_id: str, qty: int = 1) -> bool:
        return cls.inventory.get(item_id, 0) >= qty
