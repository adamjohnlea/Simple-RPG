import pygame
from typing import Tuple


class Camera:
    def __init__(self, viewport: Tuple[int, int]):
        self.viewport_w, self.viewport_h = viewport
        self.rect = pygame.Rect(0, 0, self.viewport_w, self.viewport_h)
        self.world_bounds = pygame.Rect(0, 0, self.viewport_w, self.viewport_h)

    def set_bounds(self, bounds: pygame.Rect):
        self.world_bounds = bounds.copy()

    def follow(self, target_rect: pygame.Rect):
        # center camera on target
        cx = target_rect.centerx - self.viewport_w // 2
        cy = target_rect.centery - self.viewport_h // 2
        self.rect.topleft = (cx, cy)
        self.clamp_to_bounds()

    def clamp_to_bounds(self):
        # If world smaller than viewport, center; else clamp
        if self.world_bounds.width <= self.viewport_w:
            self.rect.x = self.world_bounds.centerx - self.viewport_w // 2
        else:
            self.rect.x = max(self.world_bounds.left, min(self.rect.x, self.world_bounds.right - self.viewport_w))

        if self.world_bounds.height <= self.viewport_h:
            self.rect.y = self.world_bounds.centery - self.viewport_h // 2
        else:
            self.rect.y = max(self.world_bounds.top, min(self.rect.y, self.world_bounds.bottom - self.viewport_h))

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        return rect.move(-self.rect.x, -self.rect.y)
