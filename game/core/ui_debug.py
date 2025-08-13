import pygame
from typing import Optional

from game.config import Config


class DebugUI:
    def __init__(self, events):
        self.visible = Config.DEBUG_OVERLAY
        self.minimap_visible = False
        events.subscribe("ui.debug.toggle", self._toggle)
        events.subscribe("ui.minimap.toggle", self._toggle_minimap)
        self.font = None
        self._mini_font = None

    def _toggle(self, _):
        self.visible = not self.visible

    def _toggle_minimap(self, _):
        self.minimap_visible = not self.minimap_visible

    def draw(self, screen: pygame.Surface, dt: float, scene_manager):
        if not self.visible:
            return
        if self.font is None:
            self.font = pygame.font.SysFont("consolas", 16)
        curr = scene_manager.current
        lines = [
            f"FPS: {int(1000/max(1, dt))}",
            f"Scene: {curr.name if curr else 'None'}",
            "F1: Toggle Debug  |  F5: +8h  |  M: Minimap",
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
            surf = self.font.render(line, True, Config.COLORS["debug_text"]) 
            screen.blit(surf, (5, y))
            y += 18

        # Optional: draw colliders/triggers
        if curr and Config.DRAW_DEBUG_SHAPES:
            for r in curr.world_colliders:
                pygame.draw.rect(screen, Config.COLORS["collider"], curr.camera.apply(r), 1)
            for t in curr.triggers:
                pygame.draw.rect(screen, Config.COLORS["trigger"], curr.camera.apply(t["rect"]), 1)

        # Minimap overlay
        if self.minimap_visible and curr:
            self._draw_minimap(screen, curr)

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
