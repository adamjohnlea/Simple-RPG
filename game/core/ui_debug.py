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
        self.notifications = []  # list of {text:str, t0:int}
        events.subscribe("ui.debug.toggle", self._toggle)
        events.subscribe("ui.minimap.toggle", self._toggle_minimap)
        events.subscribe("ui.inventory.toggle", self._toggle_inventory)
        events.subscribe("ui.journal.toggle", self._toggle_journal)
        events.subscribe("ui.character.toggle", self._toggle_character)
        events.subscribe("ui.notify", self._on_notify)
        self.font = None
        self._mini_font = None
        self._hud_font = None
        self._inv_font = None

    def _toggle(self, _):
        self.visible = not self.visible

    def _toggle_minimap(self, _):
        self.minimap_visible = not self.minimap_visible

    def _toggle_inventory(self, _):
        self.inventory_visible = not self.inventory_visible

    def _toggle_journal(self, _):
        self.journal_visible = not self.journal_visible

    def _toggle_character(self, _):
        self.character_visible = not self.character_visible

    def _on_notify(self, payload):
        # payload: {text: str}
        try:
            text = str(payload.get("text", "")).strip()
            if text:
                self.notifications.append({"text": text, "t0": pygame.time.get_ticks()})
        except Exception:
            pass

    def draw(self, screen: pygame.Surface, dt: float, scene_manager):
        # Always draw HUD elements (coins, notifications, inventory panel)
        self._draw_coin_hud(screen)
        self._draw_notifications(screen)
        if self.inventory_visible:
            self._draw_inventory(screen)
        if self.journal_visible:
            self._draw_journal(screen)
        if self.character_visible:
            self._draw_character(screen)

        # Debug overlay (toggle with F1)
        if not self.visible:
            # Still allow minimap when debug overlay is hidden
            curr = scene_manager.current
            if self.minimap_visible and curr:
                self._draw_minimap(screen, curr)
            return

        if self.font is None:
            self.font = pygame.font.SysFont("consolas", 16)
        curr = scene_manager.current
        # Build help line dynamically; show farming keys only when farming is available
        base_help = "F1: Toggle Debug  |  F5: +8h  |  F6: +100c  |  M: Minimap  |  I: Inventory  |  J: Journal  |  C: Character  |  P: Pause"
        if curr and getattr(curr, 'plots', None) is not None:
            base_help += "  |  E: Till  |  F: Plant"
        base_help += "  |  Q: Quit"
        lines = [
            f"FPS: {int(1000/max(1, dt))}",
            f"Scene: {curr.name if curr else 'None'}",
            base_help,
        ]
        if curr and curr.player:
            pr = curr.player["rect"]
            lines.append(f"Player: x={pr.x} y={pr.y}")
        # GameState info (coins/quest flags)
        try:
            from game.util.state import GameState
            lines.append(f"Coins: {GameState.coins}")
            lines.append(
                f"Player: {GameState.player_name} ({GameState.player_race})  "
                f"Lvl {GameState.level}  XP {GameState.xp}/{GameState._xp_required_for_next()}"
            )
            lines.append(
                f"Stats: HP {GameState.stats.get('HP',0)}  ATK {GameState.stats.get('ATK',0)}  "
                f"DEF {GameState.stats.get('DEF',0)}  SPD {GameState.stats.get('SPD',0)}"
            )
            lines.append(f"Quest: started={GameState.flags.get('quest_started', False)} completed={GameState.flags.get('quest_completed', False)}")
            lines.append(f"Boots: {GameState.upgrades.get('boots', False)}")
        except Exception:
            pass
        y = 5
        for line in lines:
            surf = self.font.render(line, True, Config.COLORS.get("debug_text", (255,255,255))) 
            screen.blit(surf, (5, y))
            y += 18

        # Optional: draw colliders/triggers
        if curr and Config.DRAW_DEBUG_SHAPES:
            for r in curr.world_colliders:
                pygame.draw.rect(screen, Config.COLORS.get("collider", (0,255,0)), curr.camera.apply(r), 1)
            for t in curr.triggers:
                pygame.draw.rect(screen, Config.COLORS.get("trigger", (255,0,0)), curr.camera.apply(t["rect"]), 1)

        # Minimap overlay
        if self.minimap_visible and curr:
            self._draw_minimap(screen, curr)

    def _draw_coin_hud(self, screen: pygame.Surface):
        # Always show coins at top-left
        if self._hud_font is None:
            self._hud_font = pygame.font.SysFont("arial", 18)
        try:
            from game.util.state import GameState
            coins = int(getattr(GameState, 'coins', 0))
        except Exception:
            coins = 0
        text = f"Coins: {coins}"
        color = (255, 255, 255)
        shadow = (0, 0, 0)
        surf = self._hud_font.render(text, True, color)
        sh = self._hud_font.render(text, True, shadow)
        screen.blit(sh, (11, 11))
        screen.blit(surf, (10, 10))
        # Optional: show Level/HP line under coins
        try:
            from game.util.state import GameState
            info = f"LV {GameState.level}  HP {GameState.hp_current}/{GameState.stats.get('HP', GameState.hp_current)}"
            info_surf = self._hud_font.render(info, True, (255, 255, 255))
            info_shadow = self._hud_font.render(info, True, (0, 0, 0))
            screen.blit(info_shadow, (11, 30))
            screen.blit(info_surf, (10, 29))
        except Exception:
            pass

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
        y = 38
        for n in self.notifications[-4:]:  # show up to last 4
            msg = str(n.get("text", ""))
            txt = self._hud_font.render(msg, True, (255, 255, 180))
            sh = self._hud_font.render(msg, True, (0, 0, 0))
            x = (screen.get_width() - txt.get_width()) // 2
            screen.blit(sh, (x + 1, y + 1))
            screen.blit(txt, (x, y))
            y += txt.get_height() + 4

    def _draw_inventory(self, screen: pygame.Surface):
        # Simple panel on right side listing inventory id: count
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        panel_w = 240
        panel_h = min(300, screen.get_height() - 40)
        x = screen.get_width() - panel_w - 10
        y = 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        screen.blit(panel, (x, y))
        title = self._inv_font.render("Inventory", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 8))
        try:
            from game.util.state import GameState
            items = getattr(GameState, 'inventory', {}) or {}
        except Exception:
            items = {}
        y_text = y + 8 + title.get_height() + 6
        if not items:
            empty = self._inv_font.render("(empty)", True, (220, 220, 220))
            screen.blit(empty, (x + 10, y_text))
        else:
            for k, v in items.items():
                line = f"{k}: {v}"
                ln = self._inv_font.render(line, True, (220, 220, 220))
                screen.blit(ln, (x + 10, y_text))
                y_text += ln.get_height() + 4

    def _draw_journal(self, screen: pygame.Surface):
        # Panel on left side showing simple quest log (with word wrapping)
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        panel_w = 280
        panel_h = min(260, screen.get_height() - 40)
        x = 10
        y = 60
        # margins
        margin_x = 10
        margin_y = 8
        text_color = (220, 220, 220)
        header_color = (255, 235, 180)

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
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
        # Character panel on right side, below Inventory panel if open
        if self._inv_font is None:
            self._inv_font = pygame.font.SysFont("consolas", 16)
        panel_w = 240
        panel_h = min(260, screen.get_height() - 40)
        x = screen.get_width() - panel_w - 10
        # Try to avoid overlapping with inventory panel (which uses y=10 and up to 300px)
        inv_top = 10 if self.inventory_visible else 0
        inv_h = min(300, screen.get_height() - 40) if self.inventory_visible else 0
        y = (inv_top + inv_h + 10) if self.inventory_visible else 60
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        screen.blit(panel, (x, y))
        title = self._inv_font.render("Character", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 8))
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
        except Exception:
            name = 'Hero'; race = 'Human'; lvl = 1; xp = 0; xp_next = 50
            hp_cur = 20; hp_max = 20; atk = 5; dfn = 3; spd = 10; boots = False
        y_text = y + 8 + title.get_height() + 6
        lines = [
            f"Name: {name}",
            f"Race: {race}",
            f"Level: {lvl}",
            f"XP: {xp}/{xp_next}",
            f"HP: {hp_cur}/{hp_max}",
            f"ATK: {atk}   DEF: {dfn}   SPD: {spd}",
            f"Boots: {'Yes' if boots else 'No'}",
        ]
        for line in lines:
            ln = self._inv_font.render(line, True, (220, 220, 220))
            screen.blit(ln, (x + 10, y_text))
            y_text += ln.get_height() + 4

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
