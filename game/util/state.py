from typing import Dict


class GameState:
    """
    Extremely simple global game state for MVP gameplay additions.
    Persisted between runs via save/load.
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
    # Farming persistence: per-plot state keyed by plot id
    # Example entry: {"plot_1": {"state": "planted", "planted_minutes": 123.0}}
    farming_plots: Dict[str, Dict] = {}

    @classmethod
    def to_dict(cls) -> Dict:
        return {
            "coins": int(cls.coins),
            "inventory": dict(cls.inventory or {}),
            "flags": dict(cls.flags or {}),
            "upgrades": dict(cls.upgrades or {}),
            "farming_plots": dict(cls.farming_plots or {}),
        }

    @classmethod
    def from_dict(cls, data: Dict):
        if not isinstance(data, dict):
            return
        cls.coins = int(data.get("coins", 10))
        cls.inventory = dict(data.get("inventory", {"seeds": 0}))
        cls.flags = dict(data.get("flags", {"quest_started": False, "quest_completed": False}))
        cls.upgrades = dict(data.get("upgrades", {"boots": False}))
        cls.farming_plots = dict(data.get("farming_plots", {}))

    @classmethod
    def reset_defaults(cls):
        cls.coins = 10
        cls.inventory = {"seeds": 0}
        cls.flags = {"quest_started": False, "quest_completed": False}
        cls.upgrades = {"boots": False}
        cls.farming_plots = {}

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
