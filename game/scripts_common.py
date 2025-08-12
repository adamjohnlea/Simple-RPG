import pygame
from typing import Dict, Any


def spawn_player_from_json(spawns: Dict[str, Any], spawn_name: str) -> dict:
    pos = spawns.get(spawn_name) or list(spawns.values())[0]
    x, y = pos[0], pos[1]
    # Use a small rectangle for player
    rect = pygame.Rect(int(x) - 8, int(y) - 8, 16, 16)
    return {"rect": rect, "components": {"PlayerControl": True}}
