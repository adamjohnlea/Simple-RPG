import math
import pygame
from typing import List

from game.config import Config


def _normalize(vx: float, vy: float) -> (float, float):
    mag = math.hypot(vx, vy)
    if mag == 0:
        return 0.0, 0.0
    return vx / mag, vy / mag


def move_player(player: dict, input_sys, dt_ms: float, world_colliders: List[pygame.Rect]):
    dt = dt_ms / 1000.0
    vx = float(input_sys.actions["MOVE_RIGHT"]) - float(input_sys.actions["MOVE_LEFT"]) 
    vy = float(input_sys.actions["MOVE_DOWN"]) - float(input_sys.actions["MOVE_UP"]) 

    vx, vy = _normalize(vx, vy)
    speed = Config.SPEED
    # Scale by SPD stat and then apply RUN multiplier if boots are owned
    try:
        from game.util.state import GameState
        spd = int(GameState.stats.get("SPD", 10)) if getattr(GameState, 'stats', None) else 10
        speed *= max(0.5, spd / 10.0)
        if input_sys.actions.get("RUN") and GameState.upgrades.get("boots", False):
            speed *= Config.RUN_MULTIPLIER
    except Exception:
        pass

    dx = vx * speed * dt
    dy = vy * speed * dt

    rect: pygame.Rect = player["rect"]

    # X movement and collision
    rect.x += int(round(dx))
    for col in world_colliders:
        if rect.colliderect(col):
            if dx > 0:
                rect.right = col.left
            elif dx < 0:
                rect.left = col.right

    # Y movement and collision
    rect.y += int(round(dy))
    for col in world_colliders:
        if rect.colliderect(col):
            if dy > 0:
                rect.bottom = col.top
            elif dy < 0:
                rect.top = col.bottom
