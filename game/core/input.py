import pygame
from typing import Dict


class Input:
    def __init__(self):
        self.actions: Dict[str, bool] = {
            "MOVE_UP": False,
            "MOVE_DOWN": False,
            "MOVE_LEFT": False,
            "MOVE_RIGHT": False,
            "INTERACT": False,
            "DEBUG_TOGGLE": False,
            "RUN": False,
            "CANCEL": False,
        }
        self._pressed_frame: Dict[str, bool] = {k: False for k in self.actions}

    def process_pygame_event(self, event: pygame.event.Event, events_bus):
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            down = event.type == pygame.KEYDOWN
            if event.key in (pygame.K_w, pygame.K_UP):
                self.actions["MOVE_UP"] = down
            if event.key in (pygame.K_s, pygame.K_DOWN):
                self.actions["MOVE_DOWN"] = down
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.actions["MOVE_LEFT"] = down
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.actions["MOVE_RIGHT"] = down
            if event.key == pygame.K_SPACE:
                self.actions["INTERACT"] = down
                if down:
                    self._pressed_frame["INTERACT"] = True
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.actions["RUN"] = down
            if event.key == pygame.K_ESCAPE:
                self.actions["CANCEL"] = down
                if down:
                    self._pressed_frame["CANCEL"] = True
            if event.key == pygame.K_F1 and down:
                events_bus.publish("ui.debug.toggle", {})

    def was_pressed(self, action: str) -> bool:
        return self._pressed_frame.get(action, False)

    def end_frame(self):
        for k in self._pressed_frame:
            self._pressed_frame[k] = False
