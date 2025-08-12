import pygame
from typing import List, Dict, Any

from game.config import Config


def draw_prompt(screen: pygame.Surface, text: str):
    if not text:
        return
    font = pygame.font.SysFont("arial", 18)
    surf = font.render(text, True, Config.COLORS["prompt_text"]) 
    bg = pygame.Surface((surf.get_width() + 12, surf.get_height() + 8), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 160))
    x = (screen.get_width() - bg.get_width()) // 2
    y = screen.get_height() - bg.get_height() - 12
    screen.blit(bg, (x, y))
    screen.blit(surf, (x + 6, y + 4))


def draw_world(surface: pygame.Surface, camera, ground_color, roads: List[pygame.Rect], buildings: List[pygame.Rect], fences: List[pygame.Rect], player: Dict[str, Any]):
    surface.fill(ground_color)
    # roads/paths first
    for r in roads:
        pygame.draw.rect(surface, Config.COLORS["road"], camera.apply(r))
    # buildings/static props
    for b in buildings:
        pygame.draw.rect(surface, Config.COLORS["building"], camera.apply(b))
    # fences/field props
    for f in fences:
        pygame.draw.rect(surface, Config.COLORS["fence"], camera.apply(f))

    # player
    if player:
        pygame.draw.rect(surface, Config.COLORS["player"], camera.apply(player["rect"]))
