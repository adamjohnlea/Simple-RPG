import json
import pygame
from typing import Dict, Callable, Optional, Any, List, Tuple

from game.core.camera import Camera
from game.config import Config
from game.util.serialization import load_json


class BaseScene:
    def __init__(self, manager: "SceneManager"):
        self.manager = manager
        self.events = manager.events
        self.camera = Camera(viewport=(Config.WIDTH, Config.HEIGHT))
        self.name = self.__class__.__name__
        self.bounds = pygame.Rect(0, 0, Config.WIDTH, Config.HEIGHT)
        self.entities: List[Dict[str, Any]] = []
        self.world_colliders: List[pygame.Rect] = []
        self.interactables: List[Dict[str, Any]] = []
        self.triggers: List[Dict[str, Any]] = []
        self.player: Optional[Dict[str, Any]] = None
        self.prompt_text: Optional[str] = None

    def load(self):
        raise NotImplementedError

    def enter(self, payload: Optional[Dict[str, Any]] = None):
        raise NotImplementedError

    def update(self, dt: float, input_sys):
        raise NotImplementedError

    def draw(self, surface: pygame.Surface):
        raise NotImplementedError

    def unload(self):
        pass


class SceneManager:
    def __init__(self, events: "EventBus"):
        self.events = events
        self._registry: Dict[str, Callable[["SceneManager"], BaseScene]] = {}
        self._stack: List[BaseScene] = []
        self.events.subscribe("scene.change", self._on_scene_change)

    def register(self, name: str, scene_cls: Callable[["SceneManager"], BaseScene]):
        self._registry[name] = scene_cls

    def push(self, name: str, payload: Optional[Dict[str, Any]] = None):
        scene = self._create_scene(name)
        scene.load()
        scene.enter(payload)
        self._stack.append(scene)

    def replace(self, name: str, payload: Optional[Dict[str, Any]] = None):
        if self._stack:
            old = self._stack.pop()
            old.unload()
        self.push(name, payload)

    def pop(self):
        if self._stack:
            old = self._stack.pop()
            old.unload()

    def _create_scene(self, name: str) -> BaseScene:
        if name not in self._registry:
            raise KeyError(f"Scene '{name}' not registered")
        return self._registry[name](self)

    def _on_scene_change(self, payload: Dict[str, Any]):
        target = payload.get("target")
        self.replace(target, payload={"spawn": payload.get("spawn")})

    def update(self, dt: float, input_sys):
        if self._stack:
            self._stack[-1].update(dt, input_sys)

    def draw(self, surface: pygame.Surface):
        if self._stack:
            self._stack[-1].draw(surface)

    @property
    def current(self) -> Optional[BaseScene]:
        return self._stack[-1] if self._stack else None
