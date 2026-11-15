"""
4-Player Arcade Input, Batocera SDL/PadToKey & Custom Control Mapper (`src/input_manager.py`).
Supports:
1. Batocera `.keys` (evmapy padtokey) 4-player non-overlapping keyboard mappings
2. Batocera `SDL_GAMECONTROLLERCONFIG` automatic environment variable parsing
3. Direct SDL2 USB Arcade Encoders (Zero Delay / DragonRise / Brooks / XInput / DInput)
4. Customizable `controls.json` + In-Game Interactive Arcade Control Mapper (`F2`)
"""

import json
import os
import pygame
from src.config import BASE_DIR

CONTROLS_JSON_PATH = os.path.join(BASE_DIR, "controls.json")

DEFAULT_JOY_MAP = {
    "attack_buttons": [0, 2],
    "jump_buttons": [1],
    "special_buttons": [2, 5],
    "synergy_buttons": [3, 4],
    "coin_buttons": [6, 8, 10],
    "start_buttons": [7, 9, 11],
    "axis_x": 0,
    "axis_y": 1,
    "invert_x": False,
    "invert_y": False,
}


class PlayerInputState:
    """Snapshot of a single player's arcade controls for the current frame."""

    def __init__(self, player_index: int):
        self.player_index = player_index
        self.dx = 0.0
        self.dz = 0.0
        self.attack_down = False
        self.jump_down = False
        self.special_down = False
        self.synergy_down = False
        self.start_down = False
        self.coin_down = False

        # Edge-triggered events (True only on the frame the button was pressed)
        self.attack_pressed = False
        self.jump_pressed = False
        self.special_pressed = False
        self.synergy_pressed = False
        self.start_pressed = False
        self.coin_pressed = False

        # Double-tap dash detection
        self.dash_triggered = 0  # -1 for left dash, +1 for right dash, 0 for none
        self._last_dir_x = 0
        self._last_tap_dir = 0
        self._last_tap_time = -1.0


def _parse_sdl_gamecontrollerconfig() -> list[dict]:
    """
    Parse Batocera's `SDL_GAMECONTROLLERCONFIG` environment variable if present
    so physical arcade cabinet button bindings configured in EmulationStation work automatically.
    """
    raw = os.environ.get("SDL_GAMECONTROLLERCONFIG", "")
    parsed_configs: list[dict] = []
    if not raw:
        return parsed_configs

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if len(parts) < 3:
            continue
        guid = parts[0].lower()
        name = parts[1].lower()
        mapping: dict[str, str] = {"guid": guid, "name": name}
        for field in parts[2:]:
            if ":" in field:
                k, v = field.split(":", 1)
                mapping[k.strip()] = v.strip()
        parsed_configs.append(mapping)
    return parsed_configs


def _extract_btn_index(val: str | None) -> int | None:
    if not val:
        return None
    if val.startswith("b") and val[1:].isdigit():
        return int(val[1:])
    return None


class ArcadeInputManager:
    """Manages 4-player arcade cabinet inputs, credits, `controls.json`, and controller hot-plugging."""

    def __init__(self, initial_credits: int = 4):
        pygame.joystick.init()
        self.credits = initial_credits
        self.joysticks: dict[int, pygame.joystick.JoystickType] = {}
        self.states = [PlayerInputState(i) for i in range(4)]
        self._prev_buttons = [
            {"attack": False, "jump": False, "special": False, "synergy": False, "start": False, "coin": False}
            for _ in range(4)
        ]
        self._prev_global_coin = False
        self.sdl_configs = _parse_sdl_gamecontrollerconfig()
        self.custom_joy_maps: dict[int, dict] = {i: dict(DEFAULT_JOY_MAP) for i in range(4)}
        self.load_controls_config()
        self.refresh_joysticks()

    def load_controls_config(self):
        """Load per-player joystick button overrides from `controls.json` if present."""
        if os.path.isfile(CONTROLS_JSON_PATH):
            try:
                with open(CONTROLS_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                players_cfg = data.get("players", {})
                for idx in range(4):
                    p_key = f"player_{idx + 1}"
                    if p_key in players_cfg and isinstance(players_cfg[p_key], dict):
                        merged = dict(DEFAULT_JOY_MAP)
                        merged.update(players_cfg[p_key])
                        self.custom_joy_maps[idx] = merged
            except (OSError, json.JSONDecodeError):
                pass
        else:
            self.save_controls_config()

    def save_controls_config(self):
        """Save `controls.json` so users can also edit button indices manually or via the F2 mapper."""
        payload = {
            "_comment": "Arcade Joystick Button Mapping for K-Pop Demon Hunters. Press F2 on the Title Screen to map interactively, or edit button numbers below.",
            "players": {
                f"player_{idx + 1}": self.custom_joy_maps[idx] for idx in range(4)
            },
        }
        try:
            with open(CONTROLS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError:
            pass

    def _apply_sdl_config_for_joystick(self, idx: int, joy: pygame.joystick.JoystickType):
        """If Batocera exported SDL_GAMECONTROLLERCONFIG, adapt button indices for this stick unless overridden."""
        if not self.sdl_configs:
            return
        joy_name = (joy.get_name() or "").lower()
        joy_guid = (joy.get_guid() if hasattr(joy, "get_guid") else "").lower()

        matched = None
        for cfg in self.sdl_configs:
            if (joy_guid and cfg.get("guid") == joy_guid) or (joy_name and cfg.get("name") == joy_name):
                matched = cfg
                break
        if matched is None:
            matched = self.sdl_configs[min(idx, len(self.sdl_configs) - 1)]

        # In SDL GameController: 'a' is South (B in Batocera), 'b' is East (A in Batocera),
        # 'x' is West (Y in Batocera), 'y' is North (X in Batocera)
        btn_south = _extract_btn_index(matched.get("a"))
        btn_east = _extract_btn_index(matched.get("b"))
        btn_west = _extract_btn_index(matched.get("x"))
        btn_north = _extract_btn_index(matched.get("y"))
        btn_l1 = _extract_btn_index(matched.get("leftshoulder"))
        btn_r1 = _extract_btn_index(matched.get("rightshoulder"))
        btn_back = _extract_btn_index(matched.get("back"))
        btn_start = _extract_btn_index(matched.get("start"))

        jmap = self.custom_joy_maps[idx]
        if btn_south is not None:
            jmap["attack_buttons"] = list({btn_south, *(jmap.get("attack_buttons", []))})
        if btn_east is not None:
            jmap["jump_buttons"] = list({btn_east, *(jmap.get("jump_buttons", []))})
        if btn_west is not None or btn_r1 is not None:
            sp = list(jmap.get("special_buttons", []))
            if btn_west is not None and btn_west not in sp:
                sp.insert(0, btn_west)
            if btn_r1 is not None and btn_r1 not in sp:
                sp.append(btn_r1)
            jmap["special_buttons"] = sp
        if btn_north is not None or btn_l1 is not None:
            sy = list(jmap.get("synergy_buttons", []))
            if btn_north is not None and btn_north not in sy:
                sy.insert(0, btn_north)
            if btn_l1 is not None and btn_l1 not in sy:
                sy.append(btn_l1)
            jmap["synergy_buttons"] = sy
        if btn_back is not None and btn_back not in jmap["coin_buttons"]:
            jmap["coin_buttons"].insert(0, btn_back)
        if btn_start is not None and btn_start not in jmap["start_buttons"]:
            jmap["start_buttons"].insert(0, btn_start)

    def refresh_joysticks(self):
        """Scan connected SDL2 gamepads / arcade encoders."""
        self.joysticks.clear()
        count = pygame.joystick.get_count()
        for idx in range(min(4, count)):
            try:
                joy = pygame.joystick.Joystick(idx)
                joy.init()
                self.joysticks[idx] = joy
                self._apply_sdl_config_for_joystick(idx, joy)
            except pygame.error:
                pass

    def add_credit(self, amount: int = 1) -> int:
        self.credits = min(99, self.credits + amount)
        return self.credits

    def use_credit(self) -> bool:
        if self.credits > 0:
            self.credits -= 1
            return True
        return False

    def get_live_diagnostic_text(self) -> str:
        """Return a live readout of connected joysticks and currently pressed buttons/axes."""
        parts = []
        for idx, joy in self.joysticks.items():
            try:
                pressed = [str(b) for b in range(joy.get_numbuttons()) if joy.get_button(b)]
                axes = [f"A{a}:{joy.get_axis(a):+.1f}" for a in range(min(4, joy.get_numaxes())) if abs(joy.get_axis(a)) > 0.25]
                hats = [f"H:{joy.get_hat(0)}" for h in range(min(1, joy.get_numhats())) if joy.get_hat(0) != (0, 0)]
                info = " ".join(
                    ([f"Btn[{','.join(pressed)}]"] if pressed else [])
                    + axes
                    + hats
                )
                parts.append(f"P{idx + 1} Joy ({joy.get_name()[:18]}): {info or 'Idle'}")
            except pygame.error:
                pass
        if not parts:
            return "No USB Joysticks detected (Using Keyboard / Batocera PadToKey / IPAC)"
        return " | ".join(parts)

    def update(self, current_time: float) -> bool:
        """
        Poll keyboard (including Batocera PadToKey 4-player keys & IPAC) and up to 4 joysticks.
        Returns True if any coin was inserted this frame.
        """
        keys = pygame.key.get_pressed()
        coin_inserted = False

        # Global coin keys (5, 6, 7, 8 on MAME/IPAC/Batocera padtokey cabinets, plus Tab / Backspace)
        global_coin_now = bool(
            keys[pygame.K_5]
            or keys[pygame.K_6]
            or keys[pygame.K_7]
            or keys[pygame.K_8]
            or keys[pygame.K_TAB]
            or keys[pygame.K_BACKSPACE]
        )
        if global_coin_now and not self._prev_global_coin:
            self.add_credit(1)
            coin_inserted = True
        self._prev_global_coin = global_coin_now

        for p_idx in range(4):
            state = self.states[p_idx]
            prev = self._prev_buttons[p_idx]

            dx = 0.0
            dz = 0.0
            attack = False
            jump = False
            special = False
            synergy = False
            start = False
            coin = False

            # --- Keyboard / Batocera PadToKey (.keys) / IPAC 4-Player Mappings ---
            if p_idx == 0:
                # Player 1: Arrow keys OR WASD
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    dx -= 1.0
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    dx += 1.0
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    dz -= 1.0
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    dz += 1.0

                attack = bool(keys[pygame.K_z] or keys[pygame.K_LCTRL])
                jump = bool(keys[pygame.K_x] or keys[pygame.K_LALT])
                special = bool(keys[pygame.K_c] or keys[pygame.K_SPACE])
                synergy = bool(keys[pygame.K_v] or keys[pygame.K_LSHIFT])
                start = bool(keys[pygame.K_1] or keys[pygame.K_RETURN])
                coin = bool(keys[pygame.K_5] or keys[pygame.K_TAB])

            elif p_idx == 1:
                # Player 2: T/G/F/H (Batocera PadToKey P2 & IPAC)
                if keys[pygame.K_f]:
                    dx -= 1.0
                if keys[pygame.K_h]:
                    dx += 1.0
                if keys[pygame.K_t]:
                    dz -= 1.0
                if keys[pygame.K_g]:
                    dz += 1.0

                attack = bool(keys[pygame.K_u] or keys[pygame.K_RCTRL])
                jump = bool(keys[pygame.K_o] or keys[pygame.K_RSHIFT])
                special = bool(keys[pygame.K_p])
                synergy = bool(keys[pygame.K_y])
                start = bool(keys[pygame.K_2] or keys[pygame.K_KP_ENTER])
                coin = bool(keys[pygame.K_6])

            elif p_idx == 2:
                # Player 3: I/K/J/L + N/M/Comma/Period (Batocera PadToKey P3)
                if keys[pygame.K_j]:
                    dx -= 1.0
                if keys[pygame.K_l]:
                    dx += 1.0
                if keys[pygame.K_i]:
                    dz -= 1.0
                if keys[pygame.K_k]:
                    dz += 1.0

                attack = bool(keys[pygame.K_n])
                jump = bool(keys[pygame.K_m])
                special = bool(keys[pygame.K_COMMA])
                synergy = bool(keys[pygame.K_PERIOD])
                start = bool(keys[pygame.K_3])
                coin = bool(keys[pygame.K_7])

            elif p_idx == 3:
                # Player 4: Numpad 8/2/4/6 + Numpad 1/0/3/7 (Batocera PadToKey P4)
                if keys[pygame.K_KP4]:
                    dx -= 1.0
                if keys[pygame.K_KP6]:
                    dx += 1.0
                if keys[pygame.K_KP8]:
                    dz -= 1.0
                if keys[pygame.K_KP2] or keys[pygame.K_KP5]:
                    dz += 1.0

                attack = bool(keys[pygame.K_KP1])
                jump = bool(keys[pygame.K_KP0])
                special = bool(keys[pygame.K_KP3] or keys[pygame.K_KP_PERIOD])
                synergy = bool(keys[pygame.K_KP7])
                start = bool(keys[pygame.K_4])
                coin = bool(keys[pygame.K_8])

            # --- SDL2 Joystick / Arcade Stick Mapping ---
            joy = self.joysticks.get(p_idx)
            if joy is not None:
                jmap = self.custom_joy_maps[p_idx]
                try:
                    num_axes = joy.get_numaxes()
                    ax_x_idx = jmap.get("axis_x", 0)
                    ax_y_idx = jmap.get("axis_y", 1)
                    if num_axes > max(ax_x_idx, ax_y_idx):
                        ax_x = joy.get_axis(ax_x_idx) * (-1.0 if jmap.get("invert_x") else 1.0)
                        ax_y = joy.get_axis(ax_y_idx) * (-1.0 if jmap.get("invert_y") else 1.0)
                        if abs(ax_x) > 0.3:
                            dx = -1.0 if ax_x < 0 else 1.0
                        if abs(ax_y) > 0.3:
                            dz = -1.0 if ax_y < 0 else 1.0

                    if joy.get_numhats() > 0:
                        hat_x, hat_y = joy.get_hat(0)
                        if hat_x != 0:
                            dx = float(hat_x)
                        if hat_y != 0:
                            dz = float(-hat_y)  # SDL hat Y is +1 up, -1 down

                    num_btns = joy.get_numbuttons()
                    for b in jmap.get("attack_buttons", [0]):
                        if 0 <= b < num_btns and joy.get_button(b):
                            attack = True
                    for b in jmap.get("jump_buttons", [1]):
                        if 0 <= b < num_btns and joy.get_button(b):
                            jump = True
                    for b in jmap.get("special_buttons", [2, 5]):
                        if 0 <= b < num_btns and joy.get_button(b):
                            special = True
                    for b in jmap.get("synergy_buttons", [3, 4]):
                        if 0 <= b < num_btns and joy.get_button(b):
                            synergy = True
                    for b in jmap.get("coin_buttons", [6, 8, 10]):
                        if 0 <= b < num_btns and joy.get_button(b):
                            coin = True
                    for b in jmap.get("start_buttons", [7, 9, 11]):
                        if 0 <= b < num_btns and joy.get_button(b):
                            start = True
                except pygame.error:
                    pass

            # Normalize diagonal movement slightly while keeping snappy 8-way feel
            state.dx = max(-1.0, min(1.0, dx))
            state.dz = max(-1.0, min(1.0, dz))

            state.attack_down = attack
            state.jump_down = jump
            state.special_down = special
            state.synergy_down = synergy
            state.start_down = start
            state.coin_down = coin

            state.attack_pressed = attack and not prev["attack"]
            state.jump_pressed = jump and not prev["jump"]
            state.special_pressed = special and not prev["special"]
            state.synergy_pressed = synergy and not prev["synergy"]
            state.start_pressed = start and not prev["start"]
            state.coin_pressed = coin and not prev["coin"]

            if state.coin_pressed and not global_coin_now:
                self.add_credit(1)
                coin_inserted = True

            # Double-tap Left/Right dash detection
            state.dash_triggered = 0
            cur_dir_x = -1 if state.dx < -0.5 else (1 if state.dx > 0.5 else 0)
            if cur_dir_x != 0 and state._last_dir_x == 0:
                if cur_dir_x == state._last_tap_dir and (current_time - state._last_tap_time) <= 0.26:
                    state.dash_triggered = cur_dir_x
                    state._last_tap_dir = 0
                else:
                    state._last_tap_dir = cur_dir_x
                    state._last_tap_time = current_time
            state._last_dir_x = cur_dir_x

            prev["attack"] = attack
            prev["jump"] = jump
            prev["special"] = special
            prev["synergy"] = synergy
            prev["start"] = start
            prev["coin"] = coin

        return coin_inserted
