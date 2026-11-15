"""
1-Click Arcade Cabinet Packager for Batocera & RetroPie (`build_arcade_package.py`).
Creates:
- `dist/KpopDemonHunters.pygame/` (Self-contained folder ready to copy to `/userdata/roms/pygame/` on Batocera)
- `dist/KpopDemonHunters.pygame.keys` (Full 4-Player Batocera Pad-to-Key mapping profile for physical arcade controls)
- `dist/KpopDemonHunters.sh` (Ready to copy to `RetroPie/roms/ports/` on RetroPie)
"""

import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
PYGAME_PKG_DIR = os.path.join(DIST_DIR, "KpopDemonHunters.pygame")


def _make_player_padtokey_actions(
    key_up: str,
    key_down: str,
    key_left: str,
    key_right: str,
    key_attack: str,
    key_jump: str,
    key_special: str,
    key_synergy: str,
    key_start: str,
    key_coin: str,
    include_hotkey_exit: bool = False,
) -> list[dict]:
    """
    Build a Batocera `evmapy` / `padtokey` action list for a single arcade player.
    Maps both digital D-Pad (`up/down/left/right`) and analog encoder axes (`joystick1up/down/left/right`),
    plus arcade action buttons (`b`, `a`, `y`, `x`, `pageup`, `pagedown`), `select` (Coin), and `start` (Start).
    """
    actions = [
        {"trigger": "up", "type": "key", "target": key_up, "description": "Move Up"},
        {"trigger": "down", "type": "key", "target": key_down, "description": "Move Down"},
        {"trigger": "left", "type": "key", "target": key_left, "description": "Move Left"},
        {"trigger": "right", "type": "key", "target": key_right, "description": "Move Right"},
        {"trigger": "joystick1up", "type": "key", "target": key_up, "description": "Stick Up"},
        {"trigger": "joystick1down", "type": "key", "target": key_down, "description": "Stick Down"},
        {"trigger": "joystick1left", "type": "key", "target": key_left, "description": "Stick Left"},
        {"trigger": "joystick1right", "type": "key", "target": key_right, "description": "Stick Right"},
        {"trigger": "b", "type": "key", "target": key_attack, "description": "Button 1: Attack / Combo"},
        {"trigger": "a", "type": "key", "target": key_jump, "description": "Button 2: Jump / Double-Jump Escape"},
        {"trigger": "y", "type": "key", "target": key_special, "description": "Button 3: Hunmoon Special"},
        {"trigger": "x", "type": "key", "target": key_synergy, "description": "Button 4: Team Synergy / Dodge"},
        {"trigger": "pagedown", "type": "key", "target": key_special, "description": "R1: Hunmoon Special"},
        {"trigger": "pageup", "type": "key", "target": key_synergy, "description": "L1: Team Synergy / Dodge"},
        {"trigger": "start", "type": "key", "target": key_start, "description": "Start / Join Game"},
        {"trigger": "select", "type": "key", "target": key_coin, "description": "Insert Coin"},
    ]
    if include_hotkey_exit:
        actions.append(
            {
                "trigger": ["hotkey", "start"],
                "type": "key",
                "target": ["KEY_ESC"],
                "description": "Exit to Batocera Menu",
            }
        )
    return actions


def build_package():
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(PYGAME_PKG_DIR, exist_ok=True)

    # Copy main.py, requirements.txt, controls.json, src/, and assets/
    shutil.copy2(os.path.join(BASE_DIR, "main.py"), os.path.join(PYGAME_PKG_DIR, "__main__.py"))
    shutil.copy2(os.path.join(BASE_DIR, "main.py"), os.path.join(PYGAME_PKG_DIR, "main.py"))
    shutil.copy2(os.path.join(BASE_DIR, "requirements.txt"), os.path.join(PYGAME_PKG_DIR, "requirements.txt"))
    controls_path = os.path.join(BASE_DIR, "controls.json")
    if os.path.isfile(controls_path):
        shutil.copy2(controls_path, os.path.join(PYGAME_PKG_DIR, "controls.json"))
    shutil.copytree(os.path.join(BASE_DIR, "src"), os.path.join(PYGAME_PKG_DIR, "src"))
    shutil.copytree(os.path.join(BASE_DIR, "assets"), os.path.join(PYGAME_PKG_DIR, "assets"))

    # Create full 4-Player Batocera padtokey profile (`KpopDemonHunters.pygame.keys`)
    keys_profile = {
        "actions_player1": _make_player_padtokey_actions(
            key_up="KEY_UP",
            key_down="KEY_DOWN",
            key_left="KEY_LEFT",
            key_right="KEY_RIGHT",
            key_attack="KEY_Z",
            key_jump="KEY_X",
            key_special="KEY_C",
            key_synergy="KEY_V",
            key_start="KEY_1",
            key_coin="KEY_5",
            include_hotkey_exit=True,
        ),
        "actions_player2": _make_player_padtokey_actions(
            key_up="KEY_T",
            key_down="KEY_G",
            key_left="KEY_F",
            key_right="KEY_H",
            key_attack="KEY_U",
            key_jump="KEY_O",
            key_special="KEY_P",
            key_synergy="KEY_Y",
            key_start="KEY_2",
            key_coin="KEY_6",
        ),
        "actions_player3": _make_player_padtokey_actions(
            key_up="KEY_I",
            key_down="KEY_K",
            key_left="KEY_J",
            key_right="KEY_L",
            key_attack="KEY_N",
            key_jump="KEY_M",
            key_special="KEY_COMMA",
            key_synergy="KEY_DOT",
            key_start="KEY_3",
            key_coin="KEY_7",
        ),
        "actions_player4": _make_player_padtokey_actions(
            key_up="KEY_KP8",
            key_down="KEY_KP2",
            key_left="KEY_KP4",
            key_right="KEY_KP6",
            key_attack="KEY_KP1",
            key_jump="KEY_KP0",
            key_special="KEY_KP3",
            key_synergy="KEY_KP7",
            key_start="KEY_4",
            key_coin="KEY_8",
        ),
    }

    # Write `KpopDemonHunters.pygame.keys` both next to the `.pygame` folder and inside it
    with open(os.path.join(DIST_DIR, "KpopDemonHunters.pygame.keys"), "w", encoding="utf-8") as f:
        json.dump(keys_profile, f, indent=2)
    with open(os.path.join(PYGAME_PKG_DIR, "KpopDemonHunters.pygame.keys"), "w", encoding="utf-8") as f:
        json.dump(keys_profile, f, indent=2)

    # Create RetroPie / Generic Linux Arcade Cabinet Port Launch Script
    sh_script = """#!/usr/bin/env bash
# RetroPie / Linux Arcade Cabinet Launcher for K-Pop Demon Hunters
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/KpopDemonHunters.pygame"
python3 main.py --fullscreen
"""
    sh_path = os.path.join(DIST_DIR, "KpopDemonHunters.sh")
    with open(sh_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(sh_script)

    print("Arcade cabinet package created in:", DIST_DIR)
    print("  1. For Batocera: Copy `dist/KpopDemonHunters.pygame` and `KpopDemonHunters.pygame.keys` to `/userdata/roms/pygame/`")
    print("  2. For RetroPie: Copy `dist/KpopDemonHunters.pygame` and `KpopDemonHunters.sh` to `~/RetroPie/roms/ports/`")


if __name__ == "__main__":
    build_package()
