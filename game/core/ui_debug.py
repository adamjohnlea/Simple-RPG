import pygame
from typing import Optional

from game.config import Config


class DebugUI:
    def __init__(self, events):
        self.visible = Config.DEBUG_OVERLAY
        self.minimap_visible = False
        self.inventory_visible = False
        self.notifications = []  # list of {text:str, t0:int}
        events.subscribe("ui.debug.toggle", self._toggle)
        events.subscribe("ui.minimap.toggle", self._toggle_minimap)
        events.subscribe("ui.inventory.toggle", self._toggle_inventory)
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
        lines = [
            f"FPS: {int(1000/max(1, dt))}",
            f"Scene: {curr.name if curr else 'None'}",
            "F1: Toggle Debug  |  F5: +8h  |  M: Minimap  |  I: Inventory  |  E: Till  |  P: Plant",
        ]
        if curr and curr.player:
            pr = curr.player["rect"]
            lines.append(f"Player: x={pr.x} y={pr.y}")
        # GameState info (coins/quest flags)
        try:
            from game.util.state import GameState
            lines.append(f"Coins: {GameState.coins}")
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
        # Player dot
        if curr.player:
            pr: pygame.Rect = curr.player["rect"]
            pdot = pygame.Rect(pr.centerx - 2, pr.centery - 2, 4, 4)
            pygame.draw.rect(screen, (255, 235, 120), world_to_mini_rect(pdot))

        # Optional label
        if self._mini_font is None:
            self._mini_font = pygame.font.SysFont("consolas", 12)
        name = getattr(curr, 'data', {}).get('name') if getattr(curr, 'data', None) else curr.name.lower()
        label = self._mini_font.render(str(name), True, (220, 220, 220))
        screen.blit(label, (x0 + 4, y0 + 4))
