import pygame
from typing import Optional

from game.config import Config


class DebugUI:
    def __init__(self, events):
        self.visible = Config.DEBUG_OVERLAY
        self.minimap_visible = False
        self.inventory_visible = False
        self.journal_visible = False
        self.character_visible = False
        self.help_visible = False
        self.notifications = []  # list of {text:str, t0:int}
        events.subscribe("ui.debug.toggle", self._toggle)
        events.subscribe("ui.minimap.toggle", self._toggle_minimap)
        events.subscribe("ui.inventory.toggle", self._toggle_inventory)
        events.subscribe("ui.journal.toggle", self._toggle_journal)
        events.subscribe("ui.character.toggle", self._toggle_character)
        events.subscribe("ui.help.toggle", self._toggle_help)
        events.subscribe("ui.notify", self._on_notify)
        self.font = None
        self._mini_font = None
        self._hud_font = None
        self._inv_font = None
        # Inventory navigation state
        self._inv_selection = 0
        # Subscribe to simple navigation events (published by Input)
        events.subscribe("ui.nav.up", self._on_nav_up)
        events.subscribe("ui.nav.down", self._on_nav_down)
        events.subscribe("ui.nav.confirm", self._on_nav_confirm)
        events.subscribe("ui.nav.alt", self._on_nav_alt)
        self._events = events

    def _toggle(self, _):
        self.visible = not self.visible
        if self.visible:
            # make panels mutually exclusive
            self.inventory_visible = False
            self.journal_visible = False
            self.character_visible = False
            self.help_visible = False

    def _toggle_minimap(self, _):
        self.minimap_visible = not self.minimap_visible

    def _toggle_inventory(self, _):
        self.inventory_visible = not self.inventory_visible
        if self.inventory_visible:
            # make panels mutually exclusive
            self.journal_visible = False
            self.character_visible = False
            self.help_visible = False
            self.visible = False
            self._inv_selection = 0

    def _toggle_journal(self, _):
        self.journal_visible = not self.journal_visible
        if self.journal_visible:
            self.inventory_visible = False
            self.character_visible = False
            self.help_visible = False
            self.visible = False

    def _toggle_character(self, _):
        self.character_visible = not self.character_visible
        if self.character_visible:
            self.inventory_visible = False
            self.journal_visible = False
            self.help_visible = False
            self.visible = False

    def _toggle_help(self, _):
        self.help_visible = not self.help_visible
        if self.help_visible:
            self.inventory_visible = False
            self.journal_visible = False
            self.character_visible = False
            self.visible = False

    def _on_notify(self, payload):
        # payload: {text: str}
        try:
            text = str(payload.get("text", "")).strip()
            if text:
                self.notifications.append({"text": text, "t0": pygame.time.get_ticks()})
        except Exception:
            pass

    def draw(self, screen: pygame.Surface, dt: float, scene_manager):
        # Always draw HUD elements (top bar, notifications, panels)
        self._draw_top_bar(screen)
        self._draw_notifications(screen)
        if self.inventory_visible:
            self._draw_inventory(screen)
        if self.journal_visible:
            self._draw_journal(screen)
        if self.character_visible:
            self._draw_character(screen)
        if self.help_visible:
            self._draw_help_controls(screen)
        
        # Debug overlay (toggle with F1)
        if not self.visible:
            # Still allow minimap when debug overlay is hidden
            curr = scene_manager.current
            if self.minimap_visible and curr:
                self._draw_minimap(screen, curr)
            return
        
        curr = scene_manager.current
        self._draw_debug_panel(screen, dt, curr)
        
        # Optional: draw colliders/triggers
        if curr and Config.DRAW_DEBUG_SHAPES:
            for r in curr.world_colliders:
                pygame.draw.rect(screen, Config.COLORS.get("collider", (0,255,0)), curr.camera.apply(r), 1)
            for t in curr.triggers:
                pygame.draw.rect(screen, Config.COLORS.get("trigger", (255,0,0)), curr.camera.apply(t["rect"]), 1)
        
        # Minimap overlay
        if self.minimap_visible and curr:
            self._draw_minimap(screen, curr)

    def _inventory_entries(self):
        try:
            from game.util.state import GameState
            items = dict(getattr(GameState, 'inventory', {}) or {})
            upgrades = getattr(GameState, 'upgrades', {}) or {}
            equipment = getattr(GameState, 'equipment', {}) or {}
            db = getattr(GameState, 'EQUIPMENT_DB', {}) or {}
        except Exception:
            items = {}
            upgrades = {}
            equipment = {}
            db = {}
        # Build entries: items (with pretty name), then Upgrades header lines, then Unequip entries if occupied
        entries = []
        # Items
        for k, v in sorted(items.items()):
            label = db.get(k, {}).get('name') or k.replace('_', ' ').title()
            entries.append(("item", k, int(v), label))
        # Upgrades (owned): read-only lines
        owned_upgrades = [k for k, v in upgrades.items() if v]
        for up in owned_upgrades:
            name = up.replace('_', ' ').title()
            entries.append(("upgrade", name))
        # Unequip entries for each occupied slot
        # Determine label from DB name
        for slot in ("weapon", "armor", "accessory"):
            cur = equipment.get(slot)
            if cur:
                label = db.get(cur, {}).get('name') or cur.replace('_', ' ').title()
                entries.append(("unequip", slot, label))
        return entries

    def _on_nav_up(self, _):
        if not self.inventory_visible:
            return
        self._inv_selection = max(0, self._inv_selection - 1)

    def _on_nav_down(self, _):
        if not self.inventory_visible:
            return
        self._inv_selection += 1

    def _current_inventory_hint(self, entries):
        if not self.inventory_visible or not entries:
            return ""
        ent = entries[max(0, min(self._inv_selection, len(entries)-1))]
        etype = ent[0]
        try:
            from game.util.state import GameState
            equipment = getattr(GameState, 'equipment', {}) or {}
            db = getattr(GameState, 'EQUIPMENT_DB', {}) or {}
        except Exception:
            equipment = {}
            db = {}
        if etype == 'item':
            _, item_id, count, label = ent
            if item_id in db:
                # Determine if currently equipped in its slot
                slot = db[item_id]['slot']
                if equipment.get(slot) == item_id:
                    return f"Enter: Unequip {label}  |  Esc: Close"
                else:
                    return f"Enter: Equip {label}  |  Esc: Close"
            else:
                return "(Not equippable)  |  Esc: Close"
        elif etype == 'unequip':
            _, slot, label = ent
            return f"Enter: Unequip {label}  |  Esc: Close"
        else:
            return "Esc: Close"

    def _on_nav_confirm(self, _):
        if not self.inventory_visible:
            return
        entries = self._inventory_entries()
        if not entries:
            return
        idx = max(0, min(self._inv_selection, len(entries)-1))
        ent = entries[idx]
        etype = ent[0]
        try:
            from game.util.state import GameState
        except Exception:
            return
        if etype == 'item':
            _, item_id, count, label = ent
            if GameState.is_equippable(item_id):
                # If already equipped in that slot, unequip; else equip
                slot = GameState.EQUIPMENT_DB[item_id]['slot']
                if GameState.equipment.get(slot) == item_id:
                    if GameState.unequip_slot(slot):
                        self._events.publish("ui.notify", {"text": f"Unequipped {label}"})
                else:
                    if GameState.equip_item(item_id):
                        # Get bonus summary
                        bon = GameState.EQUIPMENT_DB[item_id].get('bonuses', {}) or {}
                        if bon:
                            btxt = ", ".join([f"+{v} {k}" for k, v in bon.items()])
                            self._events.publish("ui.notify", {"text": f"Equipped {label} ({btxt})"})
                        else:
                            self._events.publish("ui.notify", {"text": f"Equipped {label}"})
        elif etype == 'unequip':
            _, slot, label = ent
            if GameState.unequip_slot(slot):
                self._events.publish("ui.notify", {"text": f"Unequipped {label}"})

    def _on_nav_alt(self, _):
        # Reserved for future (e.g., Split stack / Drop). No-op for now in Inventory.
        return


    def _draw_top_bar(self, screen: pygame.Surface):
        # Permanent top bar that sits above the game scene
        if self._hud_font is None:
            self._hud_font = pygame.font.SysFont("arial", 18)
        bar_h = 44
        # Background bar
        panel = pygame.Surface((screen.get_width(), bar_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        screen.blit(panel, (0, 0))
        # Left: Coins
        try:
            from game.util.state import GameState
            coins = int(getattr(GameState, 'coins', 0))
            lvl = int(getattr(GameState, 'level', 1))
        except Exception:
            coins = 0
            lvl = 1
        # Get day number
        try:
            from game.util.time_of_day import TimeOfDay as TOD
            day_num = int(getattr(TOD, 'day', 1))
        except Exception:
            day_num = 1
        left_text = f"Day {day_num}   Coins: {coins}"
        left_surf = self._hud_font.render(left_text, True, (255, 255, 255))
        left_shadow = self._hud_font.render(left_text, True, (0, 0, 0))
        screen.blit(left_shadow, (11, 13))
        screen.blit(left_surf, (10, 12))
        # Center: Time
        try:
            from game.util.time_of_day import TimeOfDay
            time_txt = TimeOfDay.clock_text()
        except Exception:
            time_txt = ""
        if time_txt:
            t_surf = self._hud_font.render(time_txt, True, (255, 255, 255))
            t_shadow = self._hud_font.render(time_txt, True, (0, 0, 0))
            x = (screen.get_width() - t_surf.get_width()) // 2
            y = (bar_h - t_surf.get_height()) // 2 + 1
            screen.blit(t_shadow, (x + 1, y + 1))
            screen.blit(t_surf, (x, y))
        # Right: Level
        right_text = f"LV {lvl}"
        r_surf = self._hud_font.render(right_text, True, (255, 255, 255))
        r_shadow = self._hud_font.render(right_text, True, (0, 0, 0))
        rx = screen.get_width() - r_surf.get_width() - 12
        ry = (bar_h - r_surf.get_height()) // 2 + 1
        screen.blit(r_shadow, (rx + 1, ry + 1))
        screen.blit(r_surf, (rx, ry))

    def _draw_notifications(self, screen: pygame.Surface):
        # Draw recent notifications at top-center stacking downward
        now = pygame.time.get_ticks()
        duration_ms = 2000
        # prune expired
        self.notifications = [n for n in self.notifications if now - n.get('t0', 0) <= duration_ms]
        if not self.notifications:
            return
        if self._hud_font is None:
            self._hud_font = pygame.font.SysFont("arial", 18)
        y = 50
        for n in self.notifications[-4:]:  # show up to last 4
            msg = str(n.get("text", ""))
            txt = self._hud_font.render(msg, True, (255, 255, 180))
            sh = self._hud_font.render(msg, True, (0, 0, 0))
            x = (screen.get_width() - txt.get_width()) // 2
            screen.blit(sh, (x + 1, y + 1))
            screen.blit(txt, (x, y))
            y += txt.get_height() + 4

    def _draw_inventory(self, screen: pygame.Surface):
        # Centered large panel with selectable items and equip/unequip actions
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        # Backdrop
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        # Panel geometry (70% of screen, centered)
        panel_w = int(screen.get_width() * 0.7)
        panel_h = int(screen.get_height() * 0.7)
        x = (screen.get_width() - panel_w) // 2
        y = (screen.get_height() - panel_h) // 2
        margin_x = 16
        margin_y = 12
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        screen.blit(panel, (x, y))
        title = self._inv_font.render("Inventory", True, (255, 255, 255))
        screen.blit(title, (x + margin_x, y + margin_y))
        # Build entries
        entries = self._inventory_entries()
        # clamp selection
        if entries:
            self._inv_selection = max(0, min(self._inv_selection, len(entries) - 1))
        else:
            self._inv_selection = 0
        y_text = y + margin_y + title.get_height() + 10
        if not entries:
            empty = self._inv_font.render("(empty)", True, (220, 220, 220))
            screen.blit(empty, (x + margin_x, y_text))
        else:
            # draw entries with selection
            for i, ent in enumerate(entries):
                etype = ent[0]
                color = (255, 255, 0) if i == self._inv_selection else (220, 220, 220)
                if etype == "item":
                    _, item_id, count, label = ent
                    ln = self._inv_font.render(f"{label}: {count}", True, color)
                elif etype == "upgrade":
                    _, name = ent
                    ln = self._inv_font.render(f"- {name}", True, color)
                elif etype == "unequip":
                    _, slot, label = ent
                    ln = self._inv_font.render(f"[Unequip {label}]", True, color)
                else:
                    ln = self._inv_font.render("?", True, color)
                screen.blit(ln, (x + margin_x, y_text))
                y_text += ln.get_height() + 6
        # Hint area
        hint_y = y + panel_h - 28
        hint_text = self._current_inventory_hint(entries)
        if hint_text:
            hint = self._inv_font.render(hint_text, True, (200, 200, 200))
            screen.blit(hint, (x + margin_x, hint_y))

    def _draw_journal(self, screen: pygame.Surface):
        # Centered large panel showing simple quest log (with word wrapping)
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        # Backdrop
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        # Centered panel geometry
        panel_w = int(screen.get_width() * 0.7)
        panel_h = int(screen.get_height() * 0.7)
        x = (screen.get_width() - panel_w) // 2
        y = (screen.get_height() - panel_h) // 2
        # margins
        margin_x = 16
        margin_y = 12
        text_color = (220, 220, 220)
        header_color = (255, 235, 180)

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        screen.blit(panel, (x, y))

        # Title
        title = self._inv_font.render("Journal", True, (255, 255, 255))
        screen.blit(title, (x + margin_x, y + margin_y))

        # Fetch quest state
        try:
            from game.util.state import GameState
            started = bool(GameState.flags.get("quest_started", False))
            completed = bool(GameState.flags.get("quest_completed", False))
        except Exception:
            started = False
            completed = False

        # Word-wrap helper
        def wrap_text(text: str, font: pygame.font.Font, max_width: int):
            words = text.split(" ")
            lines = []
            cur = ""
            for w in words:
                trial = w if not cur else cur + " " + w
                if font.size(trial)[0] <= max_width:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    # If a single word is too long, hard-cut it
                    while font.size(w)[0] > max_width:
                        # find max substring that fits
                        lo, hi = 1, len(w)
                        best = 1
                        while lo <= hi:
                            mid = (lo + hi) // 2
                            if font.size(w[:mid])[0] <= max_width:
                                best = mid
                                lo = mid + 1
                            else:
                                hi = mid - 1
                        lines.append(w[:best])
                        w = w[best:]
                    cur = w
            if cur:
                lines.append(cur)
            return lines

        y_text = y + margin_y + title.get_height() + 6

        # Header
        header = self._inv_font.render("Farmer's Request", True, header_color)
        screen.blit(header, (x + margin_x, y_text))
        y_text += header.get_height() + 4

        # Content lines based on quest state
        if not started:
            base_lines = [
                "- Talk to the Farmer in town.",
                "- He needs a bag of seeds from the shop.",
            ]
            status = "Status: Not started"
        elif not completed:
            base_lines = [
                "- Bring 1x seeds to the Farmer.",
                "- Reward: Boots, 5 coins, 50 XP",
            ]
            status = "Status: In progress"
        else:
            base_lines = [
                "- Quest completed.",
            ]
            status = "Status: Completed ✓"

        # Available vertical space before the status area (keep 26px for status/margin)
        max_text_y = y + panel_h - 26
        max_width = panel_w - margin_x * 2
        for src in base_lines:
            for wrapped in wrap_text(src, self._inv_font, max_width):
                if y_text + self._inv_font.get_height() > max_text_y:
                    break
                ln = self._inv_font.render(wrapped, True, text_color)
                screen.blit(ln, (x + margin_x, y_text))
                y_text += ln.get_height() + 2

        # Status at the bottom (wrap if needed)
        status_lines = wrap_text(status, self._inv_font, max_width)
        total_h = sum(self._inv_font.size(s)[1] + 2 for s in status_lines) - 2
        y_status = y + panel_h - total_h - 10
        for s in status_lines:
            st = self._inv_font.render(s, True, (180, 220, 180) if completed else text_color)
            screen.blit(st, (x + margin_x, y_status))
            y_status += st.get_height() + 2

    def _draw_character(self, screen: pygame.Surface):
        # Centered large character panel
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        # Backdrop
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        # Panel geometry
        panel_w = int(screen.get_width() * 0.7)
        panel_h = int(screen.get_height() * 0.7)
        x = (screen.get_width() - panel_w) // 2
        y = (screen.get_height() - panel_h) // 2
        margin_x = 16
        margin_y = 12
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        screen.blit(panel, (x, y))
        title = self._inv_font.render("Character", True, (255, 255, 255))
        screen.blit(title, (x + margin_x, y + margin_y))
        try:
            from game.util.state import GameState
            name = getattr(GameState, 'player_name', 'Hero')
            race = getattr(GameState, 'player_race', 'Human')
            lvl = getattr(GameState, 'level', 1)
            xp = getattr(GameState, 'xp', 0)
            try:
                xp_next = GameState._xp_required_for_next()
            except Exception:
                xp_next = 50
            hp_max = int(GameState.stats.get('HP', 0)) if getattr(GameState, 'stats', None) else 0
            hp_cur = int(getattr(GameState, 'hp_current', hp_max))
            atk = int(GameState.stats.get('ATK', 0)) if getattr(GameState, 'stats', None) else 0
            dfn = int(GameState.stats.get('DEF', 0)) if getattr(GameState, 'stats', None) else 0
            spd = int(GameState.stats.get('SPD', 0)) if getattr(GameState, 'stats', None) else 0
            boots = bool(GameState.upgrades.get('boots', False)) if getattr(GameState, 'upgrades', None) else False
            equipment = getattr(GameState, 'equipment', {}) or {}
            db = getattr(GameState, 'EQUIPMENT_DB', {}) or {}
            def slot_label(slot):
                cur = equipment.get(slot)
                return (db.get(cur, {}).get('name') if cur else None) or "(none)"
        except Exception:
            name = 'Hero'; race = 'Human'; lvl = 1; xp = 0; xp_next = 50
            hp_cur = 20; hp_max = 20; atk = 5; dfn = 3; spd = 10; boots = False
            equipment = {"weapon": None, "armor": None, "accessory": None}
            def slot_label(slot):
                return "(none)"
        y_text = y + margin_y + title.get_height() + 10
        lines = [
            f"Name: {name}",
            f"Race: {race}",
            f"Level: {lvl}",
            f"XP: {xp}/{xp_next}",
            f"HP: {hp_cur}/{hp_max}",
            f"ATK: {atk}   DEF: {dfn}   SPD: {spd}",
            f"Boots: {'Yes' if boots else 'No'}",
            f"Weapon: {slot_label('weapon')}",
            f"Armor: {slot_label('armor')}",
            f"Accessory: {slot_label('accessory')}",
        ]
        for line in lines:
            ln = self._inv_font.render(line, True, (220, 220, 220))
            screen.blit(ln, (x + margin_x, y_text))
            y_text += ln.get_height() + 6

    def _draw_help_controls(self, screen: pygame.Surface):
        # Centered Controls/Help panel listing keybindings with word-wrapping so text fits
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        # Backdrop
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        # Panel geometry (slightly wider to give text more room)
        panel_w = int(screen.get_width() * 0.8)
        panel_h = int(screen.get_height() * 0.7)
        x = (screen.get_width() - panel_w) // 2
        y = (screen.get_height() - panel_h) // 2
        margin_x = 16
        margin_y = 12
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        screen.blit(panel, (x, y))
        title = self._inv_font.render("Controls", True, (255, 255, 255))
        screen.blit(title, (x + margin_x, y + margin_y))

        # Small word-wrap helper
        def wrap_text(text: str, font: pygame.font.Font, max_width: int):
            words = str(text).split(" ")
            lines = []
            cur = ""
            for w in words:
                trial = w if not cur else cur + " " + w
                if font.size(trial)[0] <= max_width:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    # Hard wrap extremely long words
                    while font.size(w)[0] > max_width and w:
                        lo, hi = 1, len(w)
                        best = 1
                        while lo <= hi:
                            mid = (lo + hi) // 2
                            if font.size(w[:mid])[0] <= max_width:
                                best = mid
                                lo = mid + 1
                            else:
                                hi = mid - 1
                        lines.append(w[:best])
                        w = w[best:]
                    cur = w
            if cur:
                lines.append(cur)
            return lines

        # Build the list of controls
        entries = [
            "Movement: WASD / Arrow Keys",
            "Interact/Confirm: Space",
            "Confirm (Alt): A",
            "Run: Shift (requires Boots)",
            "Cancel/Back: Esc",
            "Minimap: M",
            "Inventory: I",
            "Journal: J",
            "Character: C",
            "Help (this): H",
            "Pause: P",
            "Quit Prompt: Q",
            "Farming — Till: E",
            "Farming — Plant: F (need 1 Seeds on Tilled soil)",
            "Debug — Toggle Overlay: F1",
            "Debug — Time Skip +8h: F5",
            "Debug — +100 Coins: F6",
            "Debug — Give Wooden Sword: F9",
        ]

        y_text = y + margin_y + title.get_height() + 10
        available_w = panel_w - margin_x * 2

        # Render in two columns if wide enough, wrapping per-column
        columnize = screen.get_width() >= 1280
        if columnize:
            col_gap = 24
            col_width = (available_w - col_gap) // 2
            left_x = x + margin_x
            right_x = left_x + col_width + col_gap
            left_y = y_text
            right_y = y_text
            half = (len(entries) + 1) // 2
            left_entries = entries[:half]
            right_entries = entries[half:]
            # Left column
            for line in left_entries:
                for wrapped in wrap_text(line, self._inv_font, col_width):
                    ln = self._inv_font.render(wrapped, True, (220, 220, 220))
                    screen.blit(ln, (left_x, left_y))
                    left_y += ln.get_height() + 6
            # Right column
            for line in right_entries:
                for wrapped in wrap_text(line, self._inv_font, col_width):
                    ln = self._inv_font.render(wrapped, True, (220, 220, 220))
                    screen.blit(ln, (right_x, right_y))
                    right_y += ln.get_height() + 6
        else:
            # Single column wrapped
            for line in entries:
                for wrapped in wrap_text(line, self._inv_font, available_w):
                    ln = self._inv_font.render(wrapped, True, (220, 220, 220))
                    screen.blit(ln, (x + margin_x, y_text))
                    y_text += ln.get_height() + 6

    def _draw_debug_panel(self, screen: pygame.Surface, dt: float, curr: Optional[object]):
        # Centered large debug panel (replacing legacy corner overlay)
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        # Backdrop
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        # Panel geometry (80% width, 70% height)
        panel_w = int(screen.get_width() * 0.8)
        panel_h = int(screen.get_height() * 0.7)
        x = (screen.get_width() - panel_w) // 2
        y = (screen.get_height() - panel_h) // 2
        margin_x = 16
        margin_y = 12
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        screen.blit(panel, (x, y))
        title = self._inv_font.render("Debug", True, (255, 255, 255))
        screen.blit(title, (x + margin_x, y + margin_y))
        # Small word-wrap helper
        def wrap_text(text: str, font: pygame.font.Font, max_width: int):
            words = str(text).split(" ")
            lines = []
            cur = ""
            for w in words:
                trial = w if not cur else cur + " " + w
                if font.size(trial)[0] <= max_width:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    # Hard wrap very long words
                    while font.size(w)[0] > max_width and w:
                        lo, hi = 1, len(w)
                        best = 1
                        while lo <= hi:
                            mid = (lo + hi) // 2
                            if font.size(w[:mid])[0] <= max_width:
                                best = mid
                                lo = mid + 1
                            else:
                                hi = mid - 1
                        lines.append(w[:best])
                        w = w[best:]
                    cur = w
            if cur:
                lines.append(cur)
            return lines
        # Build content strings similar to old overlay
        fps = f"FPS: {int(1000/max(1, dt))}"
        scene_name = f"Scene: {curr.name if curr else 'None'}"
        base_help = "F1: Toggle Debug  |  F5: +8h  |  F6: +100c  |  F9: +Sword  |  M: Minimap  |  I: Inventory  |  J: Journal  |  C: Character  |  H: Help  |  P: Pause"
        try:
            if curr and getattr(curr, 'plots', None) is not None:
                base_help += "  |  E: Till  |  F: Plant"
        except Exception:
            pass
        base_help += "  |  Q: Quit"
        lines = [fps, scene_name, base_help]
        if curr and getattr(curr, 'player', None):
            try:
                pr = curr.player["rect"]
                lines.append(f"Player: x={pr.x} y={pr.y}")
            except Exception:
                pass
        try:
            from game.util.state import GameState
            lines.append(f"Coins: {GameState.coins}")
            lines.append(
                f"Player: {GameState.player_name} ({GameState.player_race})  Lvl {GameState.level}  XP {GameState.xp}/{GameState._xp_required_for_next()}"
            )
            lines.append(
                f"Stats: HP {GameState.stats.get('HP',0)}  ATK {GameState.stats.get('ATK',0)}  DEF {GameState.stats.get('DEF',0)}  SPD {GameState.stats.get('SPD',0)}"
            )
            lines.append(
                f"Quest: started={GameState.flags.get('quest_started', False)} completed={GameState.flags.get('quest_completed', False)}"
            )
            lines.append(f"Boots: {GameState.upgrades.get('boots', False)}")
        except Exception:
            pass
        # Render with wrapping inside panel
        available_w = panel_w - margin_x * 2
        y_text = y + margin_y + title.get_height() + 10
        for src in lines:
            for wrapped in wrap_text(src, self._inv_font, available_w):
                ln = self._inv_font.render(wrapped, True, (220, 220, 220))
                screen.blit(ln, (x + margin_x, y_text))
                y_text += ln.get_height() + 6

    def _draw_minimap(self, screen: pygame.Surface, curr):
        # Config
        mini_w = 180
        # keep aspect ratio of world bounds
        bounds = curr.bounds
        if bounds.width <= 0 or bounds.height <= 0:
            return
        aspect = bounds.height / max(1, bounds.width)
        mini_h = int(mini_w * aspect)
        mini_h = max(90, min(mini_h, 140))
        margin = 8
        x0 = margin
        y0 = screen.get_height() - mini_h - margin

        # Background panel
        panel = pygame.Surface((mini_w, mini_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))
        screen.blit(panel, (x0, y0))

        # Scale factors
        sx = mini_w / float(bounds.width)
        sy = mini_h / float(bounds.height)

        def world_to_mini_rect(rect: pygame.Rect) -> pygame.Rect:
            # map world-space rect to minimap local space
            mx = int((rect.x - bounds.x) * sx)
            my = int((rect.y - bounds.y) * sy)
            mw = max(1, int(rect.width * sx))
            mh = max(1, int(rect.height * sy))
            return pygame.Rect(x0 + mx, y0 + my, mw, mh)

        # Draw roads (if any)
        roads = getattr(curr, 'roads', []) or []
        for r in roads:
            pygame.draw.rect(screen, (160, 160, 160), world_to_mini_rect(r))
        # Draw buildings (if any)
        buildings = getattr(curr, 'buildings', []) or curr.world_colliders
        for b in buildings:
            pygame.draw.rect(screen, (120, 120, 180), world_to_mini_rect(b))
        # Farmland plots (distinct color) if present on scene
        plots = getattr(curr, 'plots', None)
        if plots:
            for p in plots:
                rect = p.get('rect') if isinstance(p, dict) else None
                if rect is None:
                    continue
                pygame.draw.rect(screen, (180, 140, 60), world_to_mini_rect(rect))
                pygame.draw.rect(screen, (50, 35, 15), world_to_mini_rect(rect), 1)
        # Player dot
        if curr.player:
            pr: pygame.Rect = curr.player["rect"]
            pdot = pygame.Rect(pr.centerx - 2, pr.centery - 2, 4, 4)
            pygame.draw.rect(screen, (255, 235, 120), world_to_mini_rect(pdot))

        # Quest waypoint marker (MVP): Farmer quest guidance in Town
        try:
            from game.util.state import GameState
            # Decide current target tag
            target_tag = None
            if not GameState.flags.get("quest_completed", False):
                if not GameState.flags.get("quest_started", False):
                    target_tag = "npc.farmer"
                else:
                    # Quest started
                    if GameState.has_item("seeds", 1):
                        target_tag = "npc.farmer"
                    else:
                        target_tag = "door.shop"
            if target_tag:
                # Find matching interactable on current scene
                tgt_rect = None
                for it in getattr(curr, 'interactables', []) or []:
                    if str(it.get('tag', '')) == target_tag:
                        tgt_rect = it.get('rect')
                        break
                if isinstance(tgt_rect, pygame.Rect):
                    # Draw a small red marker centered on target
                    cx, cy = tgt_rect.centerx, tgt_rect.centery
                    marker_world = pygame.Rect(cx - 3, cy - 3, 6, 6)
                    mr = world_to_mini_rect(marker_world)
                    pygame.draw.rect(screen, (255, 80, 80), mr)
                    pygame.draw.rect(screen, (0, 0, 0), mr, 1)
        except Exception:
            pass

        # Optional label
        if self._mini_font is None:
            self._mini_font = pygame.font.SysFont("consolas", 12)
        name = getattr(curr, 'data', {}).get('name') if getattr(curr, 'data', None) else curr.name.lower()
        label = self._mini_font.render(str(name), True, (220, 220, 220))
        screen.blit(label, (x0 + 4, y0 + 4))
