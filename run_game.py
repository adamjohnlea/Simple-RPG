import os
import sys
import pygame

# Ensure local package import
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from game.config import Config
from game.core.scene import SceneManager
from game.core.events import EventBus
from game.core.input import Input
from game.core.ui_debug import DebugUI
from game.core.timings import Clock
from game.util.save import load_save, write_save

# Register scenes
from game.scenes.town import TownScene
from game.scenes.home_interior import HomeInteriorScene
from game.scenes.farmland import FarmlandScene
from game.scenes.shop_interior import ShopInteriorScene


def main():
    pygame.init()
    pygame.display.set_caption("Simple RPG")
    screen = pygame.display.set_mode((Config.WIDTH, Config.HEIGHT))

    clock = Clock(target_fps=Config.TARGET_FPS)
    events = EventBus()
    input_sys = Input()
    scene_manager = SceneManager(events)
    debug_ui = DebugUI(events)

    scene_manager.register("town", TownScene)
    scene_manager.register("home_interior", HomeInteriorScene)
    scene_manager.register("farmland", FarmlandScene)
    scene_manager.register("shop_interior", ShopInteriorScene)

    # Persist saves on scene change (MVP)
    def _on_scene_change_save(payload):
        write_save({
            "scene": payload.get("target", "town"),
            "spawn": payload.get("spawn", "start"),
            "player_pos": None
        })
    events.subscribe("scene.change", _on_scene_change_save)

    # Start scene using save if available
    save = load_save()
    if save and save.get("scene"):
        scene_manager.replace(save["scene"], payload={"spawn": save.get("spawn", "start")})
    else:
        scene_manager.replace("town", payload={"spawn": "start"})

    running = True
    while running:
        dt = clock.tick()
        for pg_event in pygame.event.get():
            if pg_event.type == pygame.QUIT:
                running = False
            input_sys.process_pygame_event(pg_event, events)

        # Update scene
        scene_manager.update(dt, input_sys)

        # Draw
        screen.fill(Config.COLORS["bg"])  # default bg
        scene_manager.draw(screen)
        debug_ui.draw(screen, dt, scene_manager)

        pygame.display.flip()

    # On exit, write a last-known position if possible
    curr = scene_manager.current
    if curr and curr.player:
        pr = curr.player["rect"]
        write_save({
            "scene": curr.data.get("name", curr.name.lower()) if hasattr(curr, "data") and curr.data else curr.name.lower(),
            "spawn": None,
            "player_pos": [pr.x, pr.y]
        })

    pygame.quit()


if __name__ == "__main__":
    main()
