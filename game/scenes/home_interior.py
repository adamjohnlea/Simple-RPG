import pygame
from typing import Dict, Any

from game.config import Config
from game.core.scene import BaseScene
from game.scripts_common import spawn_player_from_json
from game.systems.movement import move_player
from game.systems.interaction import handle_interaction
from game.systems.render import draw_world, draw_prompt
from game.util.serialization import load_json


class HomeInteriorScene(BaseScene):
    def __init__(self, manager):
        super().__init__(manager)
        self.data = None
        self.furniture = []

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

    def update(self, dt: float, input_sys):
        move_player(self.player, input_sys, dt, self.world_colliders)

        # Interaction
        self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)

        # Camera follow
        self.camera.follow(self.player["rect"])

        input_sys.end_frame()

    def draw(self, surface: pygame.Surface):
        draw_world(surface, self.camera, Config.COLORS["ground_home"], [], self.furniture, [], self.player)
        # Draw visual exit door inside the home (based on interactable tag)
        door_color = Config.COLORS.get("door", (200, 80, 40))
        for it in self.interactables:
            if it.get("tag") == "door.exit":
                pygame.draw.rect(surface, door_color, self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)
                break
        draw_prompt(surface, self.prompt_text)
