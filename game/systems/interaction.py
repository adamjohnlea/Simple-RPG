import pygame
from typing import List, Dict, Any, Optional

from game.config import Config


def get_closest_interactable(player: dict, interactables: List[Dict[str, Any]], max_dist: int = 48) -> Optional[Dict[str, Any]]:
    pr: pygame.Rect = player["rect"]
    closest = None
    best_d2 = (max_dist + 1) ** 2
    for item in interactables:
        ir: pygame.Rect = item["rect"]
        dx = ir.centerx - pr.centerx
        dy = ir.centery - pr.centery
        d2 = dx * dx + dy * dy
        if d2 < best_d2:
            best_d2 = d2
            closest = item
    return closest


def handle_interaction(player: dict, interactables: List[Dict[str, Any]], input_sys, events_bus) -> str:
    prompt = None
    item = get_closest_interactable(player, interactables)
    if item is not None:
        prompt = item.get("prompt")
        if input_sys.was_pressed("INTERACT"):
            action = item.get("action", {})
            if action.get("type") == "scene_change":
                events_bus.publish("scene.change", {
                    "target": action.get("target"),
                    "spawn": action.get("spawn")
                })
    return prompt
