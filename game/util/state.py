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

    # NEW: Player profile and progression
    player_name: str = "Hero"
    player_race: str = "Human"  # Human|Elf|Dwarf|Orc
    stats: Dict[str, int] = {  # base/max stats; SPD affects move speed
        "HP": 20,
        "ATK": 5,
        "DEF": 3,
        "SPD": 10,  # 10 => 1.0x speed
    }
    hp_current: int = 20
    level: int = 1
    xp: int = 0
    unspent_points: int = 0  # reserved for future manual alloc UI

    # Equipment (MVP): three slots and a small item DB for bonuses
    equipment: Dict[str, str | None] = {
        "weapon": None,
        "armor": None,
        "accessory": None,
    }
    EQUIPMENT_DB: Dict[str, Dict] = {
        # id: {slot, name, bonuses}
        "wooden_sword": {"slot": "weapon", "name": "Wooden Sword", "bonuses": {"ATK": 2}},
    }

    # Race base stats
    RACES: Dict[str, Dict[str, int]] = {
        "Human": {"HP": 20, "ATK": 5,  "DEF": 5,  "SPD": 10},
        "Elf":   {"HP": 16, "ATK": 6,  "DEF": 4,  "SPD": 12},
        "Dwarf": {"HP": 24, "ATK": 5,  "DEF": 7,  "SPD": 8},
        "Orc":   {"HP": 22, "ATK": 7,  "DEF": 4,  "SPD": 9},
    }

    @classmethod
    def _xp_required_for_next(cls) -> int:
        # Simple curve: next level requirement = 50 * current level
        return 50 * max(1, cls.level)

    @classmethod
    def add_xp(cls, amount: int):
        if amount <= 0:
            return
        cls.xp += int(amount)
        leveled = False
        # Process multiple levels if big XP
        while cls.xp >= cls._xp_required_for_next():
            cls.xp -= cls._xp_required_for_next()
            cls.level += 1
            leveled = True
            # MVP: auto stat gains
            cls.stats["HP"] += 2
            cls.stats["ATK"] += 1
            cls.stats["DEF"] += 1
            if cls.level % 2 == 0:
                cls.stats["SPD"] += 1
            cls.hp_current = cls.stats["HP"]  # refill on level-up (MVP)
        # UI notifications are published by scenes after calling add_xp

    @classmethod
    def apply_race(cls, race: str):
        r = (race or "Human").strip()
        if r not in cls.RACES:
            r = "Human"
        cls.player_race = r
        base = cls.RACES[r]
        cls.stats = dict(base)
        cls.hp_current = cls.stats["HP"]

    @classmethod
    def to_dict(cls) -> Dict:
        return {
            "coins": int(cls.coins),
            "inventory": dict(cls.inventory or {}),
            "flags": dict(cls.flags or {}),
            "upgrades": dict(cls.upgrades or {}),
            "farming_plots": dict(cls.farming_plots or {}),
            # NEW fields
            "player_name": cls.player_name,
            "player_race": cls.player_race,
            "stats": dict(cls.stats or {}),
            "hp_current": int(cls.hp_current),
            "level": int(cls.level),
            "xp": int(cls.xp),
            "unspent_points": int(cls.unspent_points),
            # Equipment
            "equipment": {
                "weapon": cls.equipment.get("weapon"),
                "armor": cls.equipment.get("armor"),
                "accessory": cls.equipment.get("accessory"),
            },
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
        # NEW defaults for old saves
        cls.player_name = str(data.get("player_name", "Hero"))
        cls.player_race = str(data.get("player_race", "Human"))
        cls.stats = dict(data.get("stats", cls.RACES.get(cls.player_race, cls.RACES["Human"])))
        cls.hp_current = int(data.get("hp_current", cls.stats.get("HP", 20)))
        cls.level = int(data.get("level", 1))
        cls.xp = int(data.get("xp", 0))
        cls.unspent_points = int(data.get("unspent_points", 0))
        # Equipment
        eq = data.get("equipment") or {}
        cls.equipment = {
            "weapon": eq.get("weapon"),
            "armor": eq.get("armor"),
            "accessory": eq.get("accessory"),
        }

    @classmethod
    def reset_defaults(cls):
        cls.coins = 10
        cls.inventory = {"seeds": 0}
        cls.flags = {"quest_started": False, "quest_completed": False}
        cls.upgrades = {"boots": False}
        cls.farming_plots = {}
        cls.player_name = "Hero"
        cls.apply_race("Human")
        cls.level = 1
        cls.xp = 0
        cls.unspent_points = 0
        cls.equipment = {"weapon": None, "armor": None, "accessory": None}

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

    # --- Equipment helpers (MVP) ---
    @classmethod
    def _apply_bonuses(cls, bonuses: Dict[str, int], sign: int = 1):
        if not bonuses:
            return
        for k, v in bonuses.items():
            try:
                cls.stats[k] = int(cls.stats.get(k, 0)) + int(sign) * int(v)
                if k == "HP":
                    # If max HP changed, clamp current HP to new max
                    cls.hp_current = min(cls.hp_current, int(cls.stats.get("HP", cls.hp_current)))
            except Exception:
                pass

    @classmethod
    def is_equippable(cls, item_id: str) -> bool:
        it = cls.EQUIPMENT_DB.get(item_id)
        return bool(it and it.get("slot"))

    @classmethod
    def equip_item(cls, item_id: str) -> bool:
        """
        Equip an item from inventory. If the slot is occupied, unequip existing first.
        Returns True on success.
        """
        it = cls.EQUIPMENT_DB.get(item_id)
        if not it:
            return False
        slot = str(it.get("slot"))
        if not slot:
            return False
        # Ensure we have the item
        if not cls.has_item(item_id, 1):
            return False
        # Unequip existing in slot first
        curr = cls.equipment.get(slot)
        if curr == item_id:
            # already equipped; treat as success
            return True
        if curr:
            cls.unequip_slot(slot)
        # Consume one from inventory and equip
        if not cls.remove_item(item_id, 1):
            return False
        cls.equipment[slot] = item_id
        bonuses = (it.get("bonuses") or {})
        cls._apply_bonuses(bonuses, +1)
        return True

    @classmethod
    def unequip_slot(cls, slot: str) -> bool:
        slot = str(slot or "").lower()
        curr = cls.equipment.get(slot)
        if not curr:
            return False
        it = cls.EQUIPMENT_DB.get(curr)
        if it and it.get("bonuses"):
            cls._apply_bonuses(it.get("bonuses") or {}, -1)
        # return item to inventory
        cls.add_item(curr, 1)
        cls.equipment[slot] = None
        return True
