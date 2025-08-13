import pygame
from typing import Optional

from game.config import Config


class DebugUI:
    def __init__(self, events):
        self.visible = Config.DEBUG_OVERLAY
        events.subscribe("ui.debug.toggle", self._toggle)
        self.font = None

    def _toggle(self, _):
        self.visible = not self.visible

    def draw(self, screen: pygame.Surface, dt: float, scene_manager):
        if not self.visible:
            return
        if self.font is None:
            self.font = pygame.font.SysFont("consolas", 16)
        curr = scene_manager.current
        lines = [
            f"FPS: {int(1000/max(1, dt))}",
            f"Scene: {curr.name if curr else 'None'}",
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
