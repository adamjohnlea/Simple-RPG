import pygame
from typing import Dict, Any

from game.config import Config
from game.core.scene import BaseScene
from game.scripts_common import spawn_player_from_json
from game.systems.movement import move_player
from game.systems.interaction import handle_interaction
from game.systems.render import draw_world, draw_prompt, draw_day_night_tint, draw_clock
from game.util.serialization import load_json


class HomeInteriorScene(BaseScene):
    def __init__(self, manager):
        super().__init__(manager)
        self.data = None
        self.furniture = []
        # Sleep sequence state
        self._sleep_phase = None  # None|'fade_in'|'hold'|'fade_out'
        self._sleep_timer = 0.0
        self._sleep_alpha = 0
        self._sleep_saved = False
        self._font = None

    def load(self):
        self.data = load_json(f"{Config.SCENES_DIR}/home_interior.json")
        b = self.data["bounds"]
        self.bounds = pygame.Rect(*b)
        self.camera.set_bounds(self.bounds)
        # Colliders (e.g., walls/furniture)
        self.world_colliders = [pygame.Rect(*c["rect"]) for c in self.data.get("colliders", [])]
        self.furniture = [pygame.Rect(*c["rect"]) for c in self.data.get("colliders", [])]
        # Interactables (door back)
        self.interactables = [{**i, "rect": pygame.Rect(*i["rect"])} for i in self.data.get("interactables", [])]
        # Triggers (not needed beyond door)
        self.triggers = [{**t, "rect": pygame.Rect(*t["rect"])} for t in self.data.get("triggers", [])]

    def enter(self, payload: Dict[str, Any] | None = None):
        spawns = self.data.get("spawns", {})
        spawn_name = (payload or {}).get("spawn") or "door_in"
        self.player = spawn_player_from_json(spawns, spawn_name)

    def _start_sleep(self):
        if self._sleep_phase is None:
            self._sleep_phase = 'fade_in'
            self._sleep_timer = 0.0
            self._sleep_alpha = 0
            self._sleep_saved = False

    def update(self, dt: float, input_sys):
        # If sleeping, run sequence and block movement/interactions
        if self._sleep_phase is not None:
            ms = dt
            if self._sleep_phase == 'fade_in':
                self._sleep_timer += ms
                # 500 ms fade in
                t = min(1.0, self._sleep_timer / 500.0)
                self._sleep_alpha = int(t * 200)
                if t >= 1.0:
                    # set morning and save once, then hold
                    if not self._sleep_saved:
                        try:
                            from game.util.time_of_day import TimeOfDay
                            from game.util.save import write_save
                            TimeOfDay.set_morning()
                            write_save({
                                "scene": self.data.get("name", "home_interior"),
                                "spawn": "door_in",
                                "player_pos": None,
                                "time_minutes": TimeOfDay.minutes,
                            })
                        except Exception:
                            pass
                        self._sleep_saved = True
                    self._sleep_phase = 'hold'
                    self._sleep_timer = 0.0
            elif self._sleep_phase == 'hold':
                # show message for 800 ms
                self._sleep_timer += ms
                self._sleep_alpha = 200
                if self._sleep_timer >= 800.0:
                    self._sleep_phase = 'fade_out'
                    self._sleep_timer = 0.0
            elif self._sleep_phase == 'fade_out':
                self._sleep_timer += ms
                # 500 ms fade out
                t = min(1.0, self._sleep_timer / 500.0)
                self._sleep_alpha = int((1.0 - t) * 200)
                if t >= 1.0:
                    self._sleep_phase = None
                    self._sleep_timer = 0.0
                    self._sleep_alpha = 0
            # keep camera stable
            self.camera.follow(self.player["rect"])
            input_sys.end_frame()
            return

        # Normal movement
        move_player(self.player, input_sys, dt, self.world_colliders)

        # Interaction system default (doors)
        self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)

        # Bed interaction: if Space near a bed, start sleep
        if input_sys.was_pressed("INTERACT"):
            pr = self.player["rect"]
            closest = None
            best_d2 = (48 + 1) ** 2
            for it in self.interactables:
                if str(it.get("tag", "")) != "bed.sleep":
                    continue
                ir = it["rect"]
                dx = ir.centerx - pr.centerx
                dy = ir.centery - pr.centery
                d2 = dx*dx + dy*dy
                if d2 < best_d2:
                    best_d2 = d2
                    closest = it
            if closest is not None:
                self._start_sleep()

        # Camera follow
        self.camera.follow(self.player["rect"])

        input_sys.end_frame()

    def draw(self, surface: pygame.Surface):
        draw_world(surface, self.camera, Config.COLORS["ground_home"], [], self.furniture, [], self.player)
        # Draw visual exit door and bed inside the home
        door_color = Config.COLORS.get("door", (200, 80, 40))
        bed_color = Config.COLORS.get("bed", (180, 60, 180))
        for it in self.interactables:
            tag = it.get("tag")
            if tag == "door.exit":
                pygame.draw.rect(surface, door_color, self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)
            if tag == "bed.sleep":
                pygame.draw.rect(surface, bed_color, self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)
        draw_prompt(surface, self.prompt_text)
        draw_day_night_tint(surface)
        draw_clock(surface)

        # Sleep overlay and message
        if self._sleep_phase is not None:
            overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, max(0, min(255, self._sleep_alpha))))
            surface.blit(overlay, (0, 0))
            if self._sleep_phase in ("hold",):
                if self._font is None:
                    self._font = pygame.font.SysFont("arial", 22)
                msg = self._font.render("A new day! Progress saved.", True, (255, 255, 255))
                surface.blit(msg, ((surface.get_width() - msg.get_width()) // 2, (surface.get_height() - msg.get_height()) // 2))
