import pygame


class Clock:
    def __init__(self, target_fps: int = 60):
        self.clock = pygame.time.Clock()
        self.target_fps = target_fps

    def tick(self) -> float:
        ms = self.clock.tick(self.target_fps)
        return max(1, ms)  # milliseconds elapsed (avoid zero)
