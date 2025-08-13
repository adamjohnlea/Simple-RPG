import pygame
from typing import List, Dict, Any, Tuple

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


def draw_day_night_tint(surface: pygame.Surface):
    # Import lazily to avoid cycles
    try:
        from game.util.time_of_day import TimeOfDay
    except Exception:
        return
    # Choose tint based on time
    if TimeOfDay.is_night():
        color = (0, 0, 40, 140)
    elif TimeOfDay.is_evening():
        color = (20, 10, 0, 80)
    else:
        return
    overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
    overlay.fill(color)
    surface.blit(overlay, (0, 0))


def draw_clock(surface: pygame.Surface):
    try:
        from game.util.time_of_day import TimeOfDay
    except Exception:
        return
    font = pygame.font.SysFont("consolas", 18)
    txt = TimeOfDay.clock_text()
    label = font.render(txt, True, (255, 255, 255))
    bg = pygame.Surface((label.get_width() + 10, label.get_height() + 8), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 160))
    x = surface.get_width() - bg.get_width() - 8
    y = 8
    surface.blit(bg, (x, y))
    surface.blit(label, (x + 5, y + 4))
