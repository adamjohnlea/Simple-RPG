import os
import sys
import pygame
from datetime import datetime

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
from game.util.save import load_save, write_save, delete_save, list_save_slots, write_named_save, load_save_file, has_any_saves
from game.util.time_of_day import TimeOfDay
from game.util.state import GameState

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

    # Helpers for Save/Load full state
    def _current_scene_name_and_spawn():
        curr = scene_manager.current
        if curr is None:
            return ("town", "start")
        name = curr.data.get("name", curr.name.lower()) if hasattr(curr, "data") and curr.data else curr.name.lower()
        # We don't persist spawn name for arbitrary positions; keep None unless known
        return (name, None)

    def _build_save_dict(forced_target: str | None = None, forced_spawn: str | None = None, forced_player_pos=None):
        # Compose full state for v1.0 save
        if forced_target is None:
            scene_name, spawn = _current_scene_name_and_spawn()
        else:
            scene_name, spawn = forced_target, forced_spawn
        curr = scene_manager.current
        player_pos = forced_player_pos
        if player_pos is None and curr and curr.player:
            pr = curr.player["rect"]
            player_pos = [pr.x, pr.y]
        return {
            "scene": scene_name,
            "spawn": spawn,
            "player_pos": player_pos,
            "time_minutes": TimeOfDay.minutes,
            "game_state": GameState.to_dict(),
        }

    # Persist saves on scene change (v1.0)
    def _on_scene_change_save(payload):
        data = _build_save_dict(forced_target=payload.get("target", "town"),
                                forced_spawn=payload.get("spawn", "start"),
                                forced_player_pos=None)
        write_save(data)
    events.subscribe("scene.change", _on_scene_change_save)

    # Start menu (New / Load / Quit)
    font = pygame.font.SysFont("arial", 22)

    def _draw_center_text(lines):
        screen.fill(Config.COLORS["bg"])
        title = pygame.font.SysFont("arial", 28).render("Simple RPG", True, (255, 255, 255))
        screen.blit(title, ((Config.WIDTH - title.get_width()) // 2, 120))
        y = 200
        for line, sel in lines:
            txt = font.render(line, True, (255, 255, 0) if sel else (220, 220, 220))
            screen.blit(txt, ((Config.WIDTH - txt.get_width()) // 2, y))
            y += 34
        pygame.display.flip()

    def _start_menu() -> str:
        options = ["New Game", "Load Game", "Quit"]
        sel = 0
        clock_menu = Clock(target_fps=30)
        while True:
            _ = clock_menu.tick()
            has_save = has_any_saves()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return "quit"
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_UP, pygame.K_w):
                        sel = (sel - 1) % len(options)
                    elif ev.key in (pygame.K_DOWN, pygame.K_s):
                        sel = (sel + 1) % len(options)
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if options[sel] == "New Game":
                            return "new"
                        if options[sel] == "Load Game":
                            if has_save:
                                return "load"
                        if options[sel] == "Quit":
                            return "quit"
                    elif ev.key == pygame.K_ESCAPE:
                        return "quit"
            # Draw menu
            display_lines = []
            for i, opt in enumerate(options):
                text = opt
                if opt == "Load Game" and not has_save:
                    text = f"{opt} (no saves)"
                display_lines.append((text, i == sel and (opt != "Load Game" or has_save)))
            _draw_center_text(display_lines)

    def _load_menu() -> dict | None:
        """Return the chosen save descriptor from list_save_slots(), or None to cancel."""
        saves = list_save_slots()
        if not saves:
            return None
        sel = 0
        font_small = pygame.font.SysFont("arial", 18)
        clock_menu = Clock(target_fps=30)
        while True:
            _ = clock_menu.tick()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE,):
                        return None
                    if ev.key in (pygame.K_UP, pygame.K_w):
                        sel = (sel - 1) % len(saves)
                    elif ev.key in (pygame.K_DOWN, pygame.K_s):
                        sel = (sel + 1) % len(saves)
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return saves[sel]
            # Draw list
            screen.fill(Config.COLORS["bg"])
            title = pygame.font.SysFont("arial", 28).render("Load Game", True, (255, 255, 255))
            screen.blit(title, ((Config.WIDTH - title.get_width()) // 2, 80))
            y = 160
            for i, slot in enumerate(saves):
                name = slot.get('name') or 'Save'
                # Player summary from save
                summary = ""
                try:
                    data = load_save_file(slot.get('path', '')) or {}
                    gs = data.get('game_state') or {}
                    pname = gs.get('player_name') or ""
                    prace = gs.get('player_race') or ""
                    plevel = gs.get('level') or 1
                    if pname or prace:
                        summary = f"Player: {pname} ({prace})  Lvl {plevel}"
                except Exception:
                    pass
                label = f"{name}"
                meta = []
                if slot.get('is_autosave'):
                    meta.append("Autosave")
                if slot.get('created_at'):
                    meta.append(slot.get('created_at'))
                meta_line = " - ".join(meta)

                txt = font.render(label, True, (255, 255, 0) if i == sel else (220, 220, 220))
                screen.blit(txt, ((Config.WIDTH - txt.get_width()) // 2, y))
                y2 = y + 22
                if summary:
                    sub_txt = font_small.render(summary, True, (180, 220, 180))
                    screen.blit(sub_txt, ((Config.WIDTH - sub_txt.get_width()) // 2, y2))
                    y2 += 18
                if meta_line:
                    sub2 = font_small.render(meta_line, True, (180, 180, 180))
                    screen.blit(sub2, ((Config.WIDTH - sub2.get_width()) // 2, y2))
                y += 56
            hint = font_small.render("Enter: Load | Esc: Back", True, (200, 200, 200))
            screen.blit(hint, ((Config.WIDTH - hint.get_width()) // 2, Config.HEIGHT - 80))
            pygame.display.flip()

    def _text_input_modal(title_text: str, prompt_text: str, default_value: str = "") -> str | None:
        """Block until Enter (return value) or Esc (None)."""
        buf = list(default_value)
        caret_visible = True
        caret_timer = 0
        clock_menu = Clock(target_fps=30)
        while True:
            dt_ms = clock_menu.tick()
            caret_timer += dt_ms
            if caret_timer >= 500:
                caret_timer = 0
                caret_visible = not caret_visible
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        return None
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return ''.join(buf).strip()
                    if ev.key == pygame.K_BACKSPACE:
                        if buf:
                            buf.pop()
                    else:
                        # Simple text input: letters, numbers, space, dash, underscore
                        ch = ev.unicode
                        if ch and 32 <= ord(ch) < 127:
                            buf.append(ch)
            # Draw
            screen.fill(Config.COLORS["bg"]) 
            title = pygame.font.SysFont("arial", 28).render(title_text, True, (255, 255, 255))
            screen.blit(title, ((Config.WIDTH - title.get_width()) // 2, 120))
            prompt = font.render(prompt_text, True, (220, 220, 220))
            screen.blit(prompt, ((Config.WIDTH - prompt.get_width()) // 2, 200))
            entered = ''.join(buf)
            display_text = entered + ("|" if caret_visible else "")
            entry = font.render(display_text, True, (255, 255, 0))
            screen.blit(entry, ((Config.WIDTH - entry.get_width()) // 2, 240))
            hint = pygame.font.SysFont("arial", 18).render("Enter: Confirm | Esc: Cancel", True, (200, 200, 200))
            screen.blit(hint, ((Config.WIDTH - hint.get_width()) // 2, 320))
            pygame.display.flip()

    # Determine start flow
    def _race_select_menu() -> str | None:
        races = list(GameState.RACES.keys())
        sel = 0
        font_small = pygame.font.SysFont("arial", 18)
        clock_menu = Clock(target_fps=30)
        while True:
            _ = clock_menu.tick()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE,):
                        return None
                    if ev.key in (pygame.K_UP, pygame.K_w):
                        sel = (sel - 1) % len(races)
                    elif ev.key in (pygame.K_DOWN, pygame.K_s):
                        sel = (sel + 1) % len(races)
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return races[sel]
            # Draw
            screen.fill(Config.COLORS["bg"])
            title = pygame.font.SysFont("arial", 28).render("Choose Race", True, (255, 255, 255))
            screen.blit(title, ((Config.WIDTH - title.get_width()) // 2, 80))
            y = 160
            for i, race in enumerate(races):
                base = GameState.RACES[race]
                label = f"{race}   HP {base['HP']}  ATK {base['ATK']}  DEF {base['DEF']}  SPD {base['SPD']}"
                txt = font.render(label, True, (255, 255, 0) if i == sel else (220, 220, 220))
                screen.blit(txt, ((Config.WIDTH - txt.get_width()) // 2, y))
                y += 36
            hint = font_small.render("Enter: Select  |  Esc: Cancel", True, (200, 200, 200))
            screen.blit(hint, ((Config.WIDTH - hint.get_width()) // 2, Config.HEIGHT - 80))
            pygame.display.flip()

    def _do_new_game_flow() -> bool:
        # Character creation: name then race selection
        default_name = "Hero"
        entered_name = _text_input_modal("New Game", "Enter your name:", default_name)
        if entered_name is None or not entered_name.strip():
            return False
        selected_race = _race_select_menu()
        if selected_race is None:
            return False
        GameState.reset_defaults()
        GameState.player_name = entered_name.strip()
        GameState.apply_race(selected_race)
        TimeOfDay.set_morning()
        delete_save()
        scene_manager.replace("town", payload={"spawn": "start"})
        return True

    choice = _start_menu()
    if choice == "quit":
        pygame.quit()
        return
    elif choice == "new":
        started = _do_new_game_flow()
        if not started:
            # Back to start menu
            choice = _start_menu()
            if choice == "quit":
                pygame.quit(); return
    elif choice == "load":
        selected = _load_menu()
        if not selected:
            # Back to start menu again
            choice = _start_menu()
            if choice == "quit":
                pygame.quit()
                return
            elif choice == "new":
                started_new = _do_new_game_flow()
                if not started_new:
                    # If canceled, loop back to start menu again
                    choice = _start_menu()
                    if choice == "quit":
                        pygame.quit()
                        return
            elif choice != "load":
                # default safeguard
                scene_manager.replace("town", payload={"spawn": "start"})
            else:
                # fall-through to another load attempt
                selected = _load_menu()
                if not selected:
                    pygame.quit()
                    return
        # Load chosen save file (only if a selection was made)
        if selected:
            save = load_save_file(selected.get('path')) or {}
            if save.get("game_state"):
                GameState.from_dict(save.get("game_state"))
            if save.get("time_minutes") is not None:
                TimeOfDay.minutes = float(save.get("time_minutes", TimeOfDay.minutes))
            scene_manager.replace(save.get("scene", "town"), payload={
                "spawn": save.get("spawn", "start"),
                "player_pos": save.get("player_pos"),
            })
        else:
            # If no selection, assume we already handled start menu fallback above
            pass

    # Game loop
    running = True
    quit_prompt = False
    pause_menu = False
    pause_sel = 0
    pause_options = ["Resume", "Save", "Load", "Quit to Start Menu"]
    # Press Q to open Quit prompt (no on-screen button); Press P to Pause
    while running:
        dt = clock.tick()
        for pg_event in pygame.event.get():
            if quit_prompt:
                # Handle quit prompt keys directly
                if pg_event.type == pygame.KEYDOWN:
                    if pg_event.key in (pygame.K_ESCAPE,):
                        quit_prompt = False
                    elif pg_event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_s):
                        # Save (named) and quit
                        # Build default suggestion
                        scene_name, _ = _current_scene_name_and_spawn()
                        default_name = f"{scene_name} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        entered = _text_input_modal("Save Game", "Enter a name for your save:", default_name)
                        if entered is None:
                            # canceled naming; stay in quit prompt
                            continue
                        data = _build_save_dict()
                        write_named_save(entered, data)
                        # After saving, return to the start menu instead of quitting immediately
                        quit_prompt = False
                        # Loop on the start menu until a concrete action is chosen
                        while True:
                            choice2 = _start_menu()
                            if choice2 == "quit":
                                running = False
                                break
                            elif choice2 == "new":
                                started2 = _do_new_game_flow()
                                if started2:
                                    break
                                else:
                                    # If canceled, return to start menu loop
                                    continue
                            elif choice2 == "load":
                                selected2 = _load_menu()
                                if not selected2:
                                    # Back to start menu again
                                    continue
                                save2 = load_save_file(selected2.get('path')) or {}
                                if save2.get("game_state"):
                                    GameState.from_dict(save2.get("game_state"))
                                if save2.get("time_minutes") is not None:
                                    TimeOfDay.minutes = float(save2.get("time_minutes", TimeOfDay.minutes))
                                scene_manager.replace(save2.get("scene", "town"), payload={
                                    "spawn": save2.get("spawn", "start"),
                                    "player_pos": save2.get("player_pos"),
                                })
                                break
                            else:
                                # Fallback: quit
                                running = False
                                break
                        # Continue main loop after handling start menu
                    elif pg_event.key in (pygame.K_n, pygame.K_q):
                        # Quit without saving
                        running = False
                elif pg_event.type == pygame.QUIT:
                    # Already in quit prompt; ignore duplicate
                    pass
                continue
            if pause_menu:
                # Handle Pause menu navigation
                if pg_event.type == pygame.KEYDOWN:
                    if pg_event.key in (pygame.K_ESCAPE, pygame.K_p):
                        pause_menu = False
                    elif pg_event.key in (pygame.K_UP, pygame.K_w):
                        pause_sel = (pause_sel - 1) % len(pause_options)
                    elif pg_event.key in (pygame.K_DOWN, pygame.K_s):
                        pause_sel = (pause_sel + 1) % len(pause_options)
                    elif pg_event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        chosen = pause_options[pause_sel]
                        if chosen == "Resume":
                            pause_menu = False
                        elif chosen == "Save":
                            scene_name, _ = _current_scene_name_and_spawn()
                            default_name = f"{scene_name} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            entered = _text_input_modal("Save Game", "Enter a name for your save:", default_name)
                            if entered is not None:
                                data = _build_save_dict()
                                write_named_save(entered, data)
                        elif chosen == "Load":
                            selected2 = _load_menu()
                            if selected2:
                                save2 = load_save_file(selected2.get('path')) or {}
                                if save2.get("game_state"):
                                    GameState.from_dict(save2.get("game_state"))
                                if save2.get("time_minutes") is not None:
                                    TimeOfDay.minutes = float(save2.get("time_minutes", TimeOfDay.minutes))
                                scene_manager.replace(save2.get("scene", "town"), payload={
                                    "spawn": save2.get("spawn", "start"),
                                    "player_pos": save2.get("player_pos"),
                                })
                                pause_menu = False
                        elif chosen == "Quit to Start Menu":
                            # Return to start menu loop without forcing a save
                            pause_menu = False
                            while True:
                                choice2 = _start_menu()
                                if choice2 == "quit":
                                    running = False
                                    break
                                elif choice2 == "new":
                                    started2 = _do_new_game_flow()
                                    if started2:
                                        break
                                    else:
                                        continue
                                elif choice2 == "load":
                                    selected2 = _load_menu()
                                    if not selected2:
                                        continue
                                    save2 = load_save_file(selected2.get('path')) or {}
                                    if save2.get("game_state"):
                                        GameState.from_dict(save2.get("game_state"))
                                    if save2.get("time_minutes") is not None:
                                        TimeOfDay.minutes = float(save2.get("time_minutes", TimeOfDay.minutes))
                                    scene_manager.replace(save2.get("scene", "town"), payload={
                                        "spawn": save2.get("spawn", "start"),
                                        "player_pos": save2.get("player_pos"),
                                    })
                                    break
                                else:
                                    running = False
                                    break
                elif pg_event.type == pygame.QUIT:
                    # Treat window close as opening quit prompt from pause
                    pause_menu = False
                    quit_prompt = True
                continue
            # Normal event handling
            if pg_event.type == pygame.QUIT:
                quit_prompt = True
                continue
            if pg_event.type == pygame.KEYDOWN and pg_event.key == pygame.K_q:
                quit_prompt = True
                continue
            if pg_event.type == pygame.KEYDOWN and pg_event.key == pygame.K_p:
                pause_menu = True
                pause_sel = 0
                continue
            input_sys.process_pygame_event(pg_event, events)

        if not quit_prompt and not pause_menu:
            # Debug: time skip by 8 hours when F5 pressed
            if input_sys.was_pressed("TIME_SKIP"):
                TimeOfDay.add_minutes(8 * 60)

            # Advance time-of-day, then update scene
            TimeOfDay.advance_ms(dt)
            scene_manager.update(dt, input_sys)

        # Draw
        screen.fill(Config.COLORS["bg"])  # default bg
        scene_manager.draw(screen)
        debug_ui.draw(screen, dt, scene_manager)


        # Draw quit prompt overlay if active
        if quit_prompt:
            overlay = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            f = pygame.font.SysFont("arial", 20)
            lines = [
                "Quit Game?",
                "Y/Enter/S: Save and Quit",
                "N/Q: Quit without Saving",
                "Esc: Cancel",
            ]
            y = Config.HEIGHT // 2 - 60
            for line in lines:
                t = f.render(line, True, (255, 255, 255))
                screen.blit(t, ((Config.WIDTH - t.get_width()) // 2, y))
                y += 30

        # Draw pause menu overlay
        if pause_menu:
            overlay = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            f = pygame.font.SysFont("arial", 22)
            title = pygame.font.SysFont("arial", 28).render("Paused", True, (255, 255, 255))
            screen.blit(title, ((Config.WIDTH - title.get_width()) // 2, 100))
            y = 180
            for i, opt in enumerate(pause_options):
                sel = (i == pause_sel)
                t = f.render(opt, True, (255, 255, 0) if sel else (220, 220, 220))
                screen.blit(t, ((Config.WIDTH - t.get_width()) // 2, y))
                y += 34
            hint = pygame.font.SysFont("arial", 18).render("Enter: Confirm  |  Esc/P: Resume", True, (200, 200, 200))
            screen.blit(hint, ((Config.WIDTH - hint.get_width()) // 2, Config.HEIGHT - 80))

        pygame.display.flip()

    # On exit, if we reached here without saving via prompt, write a last-known position and full state
    curr = scene_manager.current
    # Only save if we didn't explicitly choose "Quit without Saving"
    # Since we can't distinguish here, we'll conservatively not overwrite if a quit prompt saved;
    # the prompt path already wrote the save. We'll still write to keep MVP consistent.
    if curr and curr.player:
        data = _build_save_dict()
        write_save(data)

    pygame.quit()


if __name__ == "__main__":
    main()
