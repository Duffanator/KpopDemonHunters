"""
High-Resolution Multi-Frame Illustrated 2D Arcade Sprite Renderer (`src/sprites.py`).
Uses `src/animator.py` to compile 45+ skeletal-mesh-animated frames per hero
and 20+ frames per enemy and boss (Idle, 8-frame Walk, 8-frame Run, 16-frame 4-Hit
Attack Combos, 4-frame Jump/Air-Kick, and Hurt recoil sequences).
"""

import math
import os
from PIL import Image
import pygame
from src.animator import (
    build_attack_combo_frames,
    build_hurt_frames,
    build_idle_frames,
    build_jump_frames,
    build_walk_frames,
    pil_to_pygame,
)
from src.config import (
    CHARACTERS,
    COLOR_BLACK,
    COLOR_DEMON_PURPLE,
    COLOR_GWIMA_FIRE,
    COLOR_HUNMOON_BLUE,
    COLOR_HUNMOON_GOLD,
    COLOR_NEON_CYAN,
    COLOR_NEON_PINK,
    COLOR_WHITE,
    SPRITES_DIR,
)

# Padding used by warp_sprite_mesh (pad_x=24, pad_y=20)
MESH_PAD_Y = 20


def _make_hurt_surface(surf: pygame.Surface) -> pygame.Surface:
    """Create a bright white-tinted arcade hit-flash copy of a transparent sprite."""
    flash = surf.copy()
    flash.fill((175, 175, 175, 0), special_flags=pygame.BLEND_RGB_ADD)
    return flash


def _make_afterimage_surface(surf: pygame.Surface, tint_rgb: tuple[int, int, int]) -> pygame.Surface:
    """Create a semi-transparent colored motion-blur afterimage for dashes & specials."""
    ghost = surf.copy()
    ghost.fill((*tint_rgb, 115), special_flags=pygame.BLEND_RGBA_MULT)
    return ghost


def _convert_pil_sequence(pil_frames: list[Image.Image], native_facing: int) -> dict[int, list[pygame.Surface]]:
    """Convert a list of PIL frames into right-facing (+1) and left-facing (-1) Pygame Surface lists."""
    right_list: list[pygame.Surface] = []
    left_list: list[pygame.Surface] = []
    for p_img in pil_frames:
        surf = pil_to_pygame(p_img)
        flipped = pygame.transform.flip(surf, True, False)
        if native_facing == 1:
            right_list.append(surf)
            left_list.append(flipped)
        else:
            left_list.append(surf)
            right_list.append(flipped)
    return {1: right_list, -1: left_list}


def _scale_pil_to_height(img: Image.Image, scale: float, max_h: int) -> Image.Image:
    sw = max(16, int(img.width * scale))
    sh = max(16, int(img.height * scale))
    if sh > max_h:
        adj = max_h / sh
        sw = max(16, int(sw * adj))
        sh = max(16, int(sh * adj))
    return img.resize((sw, sh), Image.Resampling.LANCZOS)


def _tint_pil(img: Image.Image, r_mult: float, g_mult: float, b_mult: float) -> Image.Image:
    out = img.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0:
                px[x, y] = (
                    min(255, int(r * r_mult + 25)),
                    min(255, int(g * g_mult + 10)),
                    min(255, int(b * b_mult + 35)),
                    a,
                )
    return out


class ArcadeAssetBank:
    """Loads illustrated sprites and compiles multi-frame skeletal animation banks."""

    def __init__(self):
        self.marquee_surface: pygame.Surface | None = None
        self.portraits_hud: dict[str, pygame.Surface] = {}
        self.portraits_select: dict[str, pygame.Surface] = {}

        # Multi-frame animation banks:
        # hero_anims[cid] = {
        #   "idle": {1: [6 surfs], -1: [6 surfs]},
        #   "walk": {1: [8 surfs], -1: [8 surfs]},
        #   "run":  {1: [8 surfs], -1: [8 surfs]},
        #   "jump": {1: [4 surfs], -1: [4 surfs]},
        #   "hurt": {1: [3 surfs], -1: [3 surfs]},
        #   "combos": [ {1: [4 surfs], -1: [4 surfs]} x 4 ],
        # }
        self.hero_anims: dict[str, dict] = {}
        self.enemy_anims: dict[str, dict] = {}
        self.boss_anims: dict[str, dict] = {}

        self._loaded = False

    def ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True

        # 1. Load Marquee
        marquee_path = os.path.join(SPRITES_DIR, "marquee.jpg")
        if os.path.isfile(marquee_path):
            try:
                img = pygame.image.load(marquee_path).convert()
                self.marquee_surface = pygame.transform.smoothscale(img, (960, 540))
            except pygame.error:
                self.marquee_surface = None

        # 2. Load 2x2 Portrait Grid
        grid_path = os.path.join(SPRITES_DIR, "portraits_grid.jpg")
        if os.path.isfile(grid_path):
            try:
                grid = pygame.image.load(grid_path).convert()
                gw, gh = grid.get_size()
                crops = {
                    "rumi": pygame.Rect(int(gw * 0.055), int(gh * 0.055), int(gw * 0.415), int(gh * 0.415)),
                    "zoey": pygame.Rect(int(gw * 0.530), int(gh * 0.055), int(gw * 0.415), int(gh * 0.415)),
                    "mira": pygame.Rect(int(gw * 0.055), int(gh * 0.530), int(gw * 0.415), int(gh * 0.415)),
                    "bobby": pygame.Rect(int(gw * 0.530), int(gh * 0.530), int(gw * 0.415), int(gh * 0.415)),
                }
                for cid, rect in crops.items():
                    sub = grid.subsurface(rect).copy()
                    self.portraits_hud[cid] = pygame.transform.smoothscale(sub, (46, 46))
                    self.portraits_select[cid] = pygame.transform.smoothscale(sub, (136, 136))
            except (pygame.error, ValueError):
                pass

        # 3. Compile 45-Frame Hero Animation Banks (drawn facing RIGHT = +1)
        target_hero_heights = {"rumi": 144, "zoey": 136, "mira": 148, "bobby": 148}
        for cid, target_h in target_hero_heights.items():
            idle_p = os.path.join(SPRITES_DIR, "chars", f"{cid}_idle.png")
            walk_p = os.path.join(SPRITES_DIR, "chars", f"{cid}_walk.png")
            atk_p = os.path.join(SPRITES_DIR, "chars", f"{cid}_attack.png")
            if not os.path.isfile(idle_p):
                continue

            raw_idle = Image.open(idle_p).convert("RGBA")
            scale = target_h / max(1, raw_idle.height)
            max_h = int(target_h * 1.20)

            idle_pil = _scale_pil_to_height(raw_idle, scale, max_h)
            walk_pil = _scale_pil_to_height(Image.open(walk_p).convert("RGBA"), scale, max_h) if os.path.isfile(walk_p) else idle_pil
            atk_pil = _scale_pil_to_height(Image.open(atk_p).convert("RGBA"), scale, max_h) if os.path.isfile(atk_p) else walk_pil

            idle_seq = _convert_pil_sequence(build_idle_frames(idle_pil, 1, num_frames=6), 1)
            walk_seq = _convert_pil_sequence(
                build_walk_frames(idle_pil, walk_pil, 1, num_frames=8, stride_px=12.0, lift_px=9.0, bob_px=4.5, lean_px=3.5),
                1,
            )
            run_seq = _convert_pil_sequence(
                build_walk_frames(idle_pil, walk_pil, 1, num_frames=8, stride_px=16.5, lift_px=12.5, bob_px=6.5, lean_px=9.5),
                1,
            )
            jump_seq = _convert_pil_sequence(build_jump_frames(idle_pil, walk_pil, atk_pil, 1), 1)
            hurt_pil_frames = build_hurt_frames(idle_pil, 1)
            hurt_seq = _convert_pil_sequence(hurt_pil_frames, 1)
            hurt_flash_seq = {
                1: [_make_hurt_surface(s) for s in hurt_seq[1]],
                -1: [_make_hurt_surface(s) for s in hurt_seq[-1]],
            }

            combo_pil_lists = build_attack_combo_frames(idle_pil, walk_pil, atk_pil, 1)
            combo_seqs = [_convert_pil_sequence(c_list, 1) for c_list in combo_pil_lists]

            self.hero_anims[cid] = {
                "idle": idle_seq,
                "walk": walk_seq,
                "run": run_seq,
                "jump": jump_seq,
                "hurt": hurt_seq,
                "hurt_flash": hurt_flash_seq,
                "combos": combo_seqs,
            }

        # 4. Compile 20-Frame Enemy Animation Banks (drawn facing LEFT = -1)
        enemy_specs = {
            "faceless": ("faceless.png", 118),
            "dokkaebi_trickster": ("dokkaebi_trickster.png", 136),
            "dokkaebi_brute": ("dokkaebi_brute.png", 184),
            "mulguishin": ("mulguishin.png", 142),
        }
        raw_enemy_pils: dict[str, Image.Image] = {}
        for etype, (fname, target_h) in enemy_specs.items():
            epath = os.path.join(SPRITES_DIR, "enemies", fname)
            if os.path.isfile(epath):
                raw = Image.open(epath).convert("RGBA")
                scale = target_h / max(1, raw.height)
                epil = _scale_pil_to_height(raw, scale, int(target_h * 1.15))
                raw_enemy_pils[etype] = epil
                self.enemy_anims[etype] = self._compile_npc_anim_bank(epil, native_facing=-1)

        if "faceless" in raw_enemy_pils:
            base_f = raw_enemy_pils["faceless"]
            am_pil = _tint_pil(
                base_f.resize((int(base_f.width * 1.45), int(base_f.height * 1.45)), Image.Resampling.LANCZOS),
                1.35,
                0.75,
                1.45,
            )
            self.enemy_anims["faceless_amalgam"] = self._compile_npc_anim_bank(am_pil, native_facing=-1)

        # 5. Compile 22-Frame Boss Animation Banks (drawn facing LEFT = -1)
        boss_specs = {
            "mystery": ("mystery.png", 160),
            "romance": ("romance.png", 162),
            "abby": ("abby.png", 174),
            "baby": ("baby.png", 154),
            "jinu": ("jinu.png", 176),
            "gwima": ("gwima.png", 268),
        }
        raw_boss_pils: dict[str, Image.Image] = {}
        for bid, (fname, target_h) in boss_specs.items():
            bpath = os.path.join(SPRITES_DIR, "bosses", fname)
            if os.path.isfile(bpath):
                raw = Image.open(bpath).convert("RGBA")
                scale = target_h / max(1, raw.height)
                bpil = _scale_pil_to_height(raw, scale, int(target_h * 1.15))
                raw_boss_pils[bid] = bpil
                self.boss_anims[bid] = self._compile_npc_anim_bank(
                    bpil, native_facing=-1, is_flame=(bid == "gwima")
                )

        if "baby" in raw_boss_pils:
            base_b = raw_boss_pils["baby"]
            rogue_pil = _tint_pil(
                base_b.resize((int(base_b.width * 0.90), int(base_b.height * 0.90)), Image.Resampling.LANCZOS),
                0.75,
                0.95,
                1.45,
            )
            self.enemy_anims["half_demon_rogue"] = self._compile_npc_anim_bank(rogue_pil, native_facing=-1)

    def _compile_npc_anim_bank(self, base_pil: Image.Image, native_facing: int = -1, is_flame: bool = False) -> dict:
        """Compile Idle (4f), Walk (8f), Attack (6f), and Hurt (2f) sequences for an enemy or boss."""
        idle_seq = _convert_pil_sequence(
            build_idle_frames(base_pil, native_facing, num_frames=4 if not is_flame else 6, is_flame=is_flame),
            native_facing,
        )
        walk_seq = _convert_pil_sequence(
            build_walk_frames(
                base_pil,
                None,
                native_facing,
                num_frames=8,
                stride_px=13.5 if not is_flame else 9.0,
                lift_px=9.5 if not is_flame else 5.0,
                bob_px=5.0,
                lean_px=4.5,
            ),
            native_facing,
        )
        # 6-frame enemy/boss attack: 2 windup frames -> 2 fierce strike frames -> 2 recovery frames
        combo_lists = build_attack_combo_frames(base_pil, None, None, native_facing)
        atk_pil_6 = [
            combo_lists[2][0],  # High windup 1
            combo_lists[0][0],  # Coil back 2
            combo_lists[0][1],  # Strike launch 3
            combo_lists[3][2],  # Full lunge impact 4
            combo_lists[2][2],  # Heavy follow-through 5
            combo_lists[0][3],  # Recovery 6
        ]
        atk_seq = _convert_pil_sequence(atk_pil_6, native_facing)

        hurt_pils = build_hurt_frames(base_pil, native_facing)
        hurt_seq = _convert_pil_sequence(hurt_pils, native_facing)
        hurt_flash_seq = {
            1: [_make_hurt_surface(s) for s in hurt_seq[1]],
            -1: [_make_hurt_surface(s) for s in hurt_seq[-1]],
        }
        return {
            "idle": idle_seq,
            "walk": walk_seq,
            "attack": atk_seq,
            "hurt": hurt_seq,
            "hurt_flash": hurt_flash_seq,
        }


ASSET_BANK = ArcadeAssetBank()


def draw_outlined_circle(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    center: tuple[float, float],
    radius: float,
    outline_width: int = 2,
):
    ix, iy = int(center[0]), int(center[1])
    ir = max(1, int(radius))
    pygame.draw.circle(surface, COLOR_BLACK, (ix, iy), ir + outline_width)
    pygame.draw.circle(surface, color, (ix, iy), ir)


def draw_shadow(surface: pygame.Surface, x: float, z: float, width: float = 56, height: float = 16):
    shadow_rect = pygame.Rect(int(x - width // 2), int(z - height // 2), int(width), int(height))
    shadow_surf = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 125), (0, 0, int(width), int(height)))
    surface.blit(shadow_surf, shadow_rect.topleft)


def _draw_slash_arc(
    surface: pygame.Surface,
    cx: float,
    cy: float,
    facing: int,
    radius: float,
    color_outer: tuple[int, int, int],
    color_inner: tuple[int, int, int],
    combo_step: int,
):
    r = int(radius)
    arc_surf = pygame.Surface((r * 2 + 16, r * 2 + 16), pygame.SRCALPHA)
    center = r + 8
    pts = []
    start_a = -0.85 if combo_step % 2 == 0 else -0.65
    end_a = 0.85 if combo_step % 2 == 0 else 0.95
    steps = 10
    for i in range(steps + 1):
        a = start_a + (end_a - start_a) * (i / steps)
        px = center + facing * math.cos(a) * r
        py = center + math.sin(a) * r * 0.72
        pts.append((px, py))
    for i in range(steps, -1, -1):
        a = start_a + (end_a - start_a) * (i / steps)
        px = center + facing * math.cos(a) * (r * 0.58)
        py = center + math.sin(a) * (r * 0.45)
        pts.append((px, py))

    pygame.draw.polygon(arc_surf, (*color_outer, 165), pts)
    pygame.draw.polygon(arc_surf, (*color_inner, 220), pts, 2)
    surface.blit(arc_surf, (int(cx - center), int(cy - center)))


def draw_hero_sprite(
    surface: pygame.Surface,
    char_id: str,
    screen_x: float,
    screen_z: float,
    y_offset: float,
    facing: int,
    state: str,
    anim_timer: float,
    combo_step: int = 0,
    special_active: bool = False,
    soul_empowered: bool = False,
    hurt_flash: bool = False,
    invuln_blink: bool = False,
    attack_progress: float = -1.0,
    is_double_jumping: bool = False,
    flip_angle: float = 0.0,
    ground_y: float = 0.0,
):
    """Render Rumi, Zoey, Mira, or Bobby using their 45-frame skeletal-animated sprite bank."""
    ASSET_BANK.ensure_loaded()
    cfg = CHARACTERS[char_id]
    shadow_y = screen_z - ground_y
    draw_shadow(surface, screen_x, shadow_y, width=56, height=16)

    bx = screen_x
    by = screen_z - y_offset

    if invuln_blink and int(anim_timer * 16) % 2 == 0:
        pygame.draw.ellipse(
            surface,
            COLOR_NEON_CYAN,
            pygame.Rect(int(bx - 30), int(shadow_y - 10), 60, 20),
            2,
        )

    if soul_empowered or special_active:
        aura_radius = 54 + int(6 * math.sin(anim_timer * 14))
        aura_surf = pygame.Surface((aura_radius * 2 + 8, aura_radius * 2 + 8), pygame.SRCALPHA)
        aura_col = (*COLOR_HUNMOON_BLUE, 85) if not soul_empowered else (*COLOR_HUNMOON_GOLD, 100)
        pygame.draw.circle(aura_surf, aura_col, (aura_radius + 4, aura_radius + 4), aura_radius)
        pygame.draw.circle(aura_surf, (*COLOR_NEON_CYAN, 165), (aura_radius + 4, aura_radius + 4), aura_radius - 5, 2)
        surface.blit(aura_surf, (int(bx - aura_radius - 4), int(by - 56 - aura_radius - 4)))

    bank = ASSET_BANK.hero_anims.get(char_id)
    if not bank:
        return

    dir_key = 1 if facing >= 0 else -1
    sprite_surf: pygame.Surface | None = None

    if hurt_flash:
        seq = bank["hurt_flash"][dir_key]
        sprite_surf = seq[int(anim_timer * 14) % len(seq)]
    elif state == "hurt":
        seq = bank["hurt"][dir_key]
        sprite_surf = seq[int(anim_timer * 12) % len(seq)]
    elif state == "attack" or special_active:
        c_seq = bank["combos"][combo_step % 4][dir_key]
        if 0.0 <= attack_progress <= 1.0:
            f_idx = min(len(c_seq) - 1, int(attack_progress * len(c_seq)))
        else:
            f_idx = int(anim_timer * 18) % len(c_seq)
        sprite_surf = c_seq[f_idx]
    elif state == "jump":
        seq = bank["jump"][dir_key]
        f_idx = min(len(seq) - 1, int(anim_timer * 10) % len(seq))
        sprite_surf = seq[f_idx]
    elif state == "run":
        seq = bank["run"][dir_key]
        f_idx = int(anim_timer * 16) % len(seq)
        sprite_surf = seq[f_idx]
        # Draw speed afterimage trail behind sprinting character!
        prev_surf = seq[(f_idx - 1) % len(seq)]
        sw, sh = prev_surf.get_size()
        ghost = _make_afterimage_surface(prev_surf, cfg["color_primary"])
        surface.blit(ghost, (int(bx - dir_key * 18 - sw // 2), int(by - sh + MESH_PAD_Y + 4)))
    elif state == "walk":
        seq = bank["walk"][dir_key]
        f_idx = int(anim_timer * 12) % len(seq)
        sprite_surf = seq[f_idx]
    else:
        seq = bank["idle"][dir_key]
        f_idx = int(anim_timer * 7) % len(seq)
        sprite_surf = seq[f_idx]

    if sprite_surf is not None:
        if is_double_jumping and y_offset > 12:
            # Draw glowing neon escape vault afterimage + mid-air somersault flip!
            sw0, sh0 = sprite_surf.get_size()
            ghost = _make_afterimage_surface(sprite_surf, COLOR_NEON_CYAN)
            surface.blit(ghost, (int(bx - dir_key * 28 - sw0 // 2), int(by + 12 - sh0 + MESH_PAD_Y + 4)))
            rot_deg = (-dir_key * flip_angle) % 360
            rot_surf = pygame.transform.rotate(sprite_surf, rot_deg)
            rw, rh = rot_surf.get_size()
            surface.blit(rot_surf, (int(bx - rw // 2), int(by - sh0 // 2 - rh // 2 + MESH_PAD_Y + 4)))
        else:
            sw, sh = sprite_surf.get_size()
            draw_x = int(bx - sw // 2)
            draw_y = int(by - sh + MESH_PAD_Y + 4)
            surface.blit(sprite_surf, (draw_x, draw_y))

    if special_active:
        slash_colors = {
            "rumi": (COLOR_NEON_CYAN, COLOR_HUNMOON_GOLD, 76),
            "zoey": (COLOR_NEON_PINK, COLOR_NEON_CYAN, 68),
            "mira": (COLOR_HUNMOON_GOLD, (255, 75, 115), 86),
            "bobby": (COLOR_NEON_CYAN, COLOR_HUNMOON_GOLD, 64),
        }
        c_out, c_in, rad = slash_colors.get(char_id, (COLOR_NEON_CYAN, COLOR_WHITE, 70))
        _draw_slash_arc(
            surface,
            bx + facing * 24,
            by - 68,
            facing,
            rad * (1.2 if soul_empowered else 1.0),
            c_out,
            c_in,
            combo_step,
        )


def draw_enemy_sprite(
    surface: pygame.Surface,
    enemy_type: str,
    screen_x: float,
    screen_z: float,
    y_offset: float,
    facing: int,
    state: str,
    anim_timer: float,
    hurt_flash: bool = False,
    merge_progress: float = 0.0,
    attack_progress: float = -1.0,
):
    """Render enemies using their 20-frame skeletal-animated sprite bank."""
    ASSET_BANK.ensure_loaded()
    is_large = "brute" in enemy_type or "amalgam" in enemy_type
    draw_shadow(surface, screen_x, screen_z, width=68 if is_large else 48, height=18 if is_large else 14)

    bx = screen_x
    by = screen_z - y_offset

    if enemy_type == "mulguishin":
        pygame.draw.ellipse(
            surface,
            (30, 185, 205),
            pygame.Rect(int(bx - 28), int(screen_z - 8), 56, 16),
            2,
        )

    if merge_progress > 0.0:
        r = int(34 + 10 * math.sin(anim_timer * 16))
        pygame.draw.circle(surface, COLOR_NEON_PINK, (int(bx), int(by - 45)), r, 2)

    bank = ASSET_BANK.enemy_anims.get(enemy_type) or ASSET_BANK.enemy_anims.get("faceless")
    if not bank:
        return

    dir_key = 1 if facing >= 0 else -1
    if hurt_flash:
        seq = bank["hurt_flash"][dir_key]
        sprite_surf = seq[int(anim_timer * 14) % len(seq)]
    elif state == "hurt":
        seq = bank["hurt"][dir_key]
        sprite_surf = seq[int(anim_timer * 12) % len(seq)]
    elif state == "attack":
        seq = bank["attack"][dir_key]
        if 0.0 <= attack_progress <= 1.0:
            f_idx = min(len(seq) - 1, int(attack_progress * len(seq)))
        else:
            f_idx = int(anim_timer * 16) % len(seq)
        sprite_surf = seq[f_idx]
    elif state == "walk":
        seq = bank["walk"][dir_key]
        sprite_surf = seq[int(anim_timer * 11) % len(seq)]
    else:
        seq = bank["idle"][dir_key]
        sprite_surf = seq[int(anim_timer * 6) % len(seq)]

    if sprite_surf is not None:
        sw, sh = sprite_surf.get_size()
        draw_x = int(bx - sw // 2)
        draw_y = int(by - sh + MESH_PAD_Y + 4)
        surface.blit(sprite_surf, (draw_x, draw_y))

    if state == "attack":
        _draw_slash_arc(
            surface,
            bx + facing * 18,
            by - 54,
            facing,
            60 if is_large else 44,
            COLOR_DEMON_PURPLE,
            COLOR_HUNMOON_GOLD,
            0,
        )


def draw_boss_sprite(
    surface: pygame.Surface,
    boss_id: str,
    screen_x: float,
    screen_z: float,
    y_offset: float,
    facing: int,
    state: str,
    anim_timer: float,
    hurt_flash: bool = False,
):
    """Render Saja Boys and Gwi-Ma using their 22-frame skeletal-animated sprite bank."""
    ASSET_BANK.ensure_loaded()
    is_gwima = boss_id == "gwima"
    draw_shadow(surface, screen_x, screen_z, width=140 if is_gwima else 68, height=32 if is_gwima else 18)

    bx = screen_x
    by = screen_z - y_offset

    aura_r = (96 if is_gwima else 54) + int(6 * math.sin(anim_timer * 10))
    aura_surf = pygame.Surface((aura_r * 2 + 8, aura_r * 2 + 8), pygame.SRCALPHA)
    aura_colors = {
        "mystery": (145, 65, 245, 85),
        "romance": (255, 70, 175, 85),
        "abby": (45, 200, 235, 85),
        "baby": (80, 245, 155, 85),
        "jinu": (225, 35, 90, 105),
        "gwima": (255, 95, 20, 110),
    }
    pygame.draw.circle(aura_surf, aura_colors.get(boss_id, (180, 40, 220, 85)), (aura_r + 4, aura_r + 4), aura_r)
    surface.blit(aura_surf, (int(bx - aura_r - 4), int(by - (95 if is_gwima else 55) - aura_r)))

    bank = ASSET_BANK.boss_anims.get(boss_id)
    if not bank:
        return

    dir_key = 1 if facing >= 0 else -1
    if hurt_flash:
        seq = bank["hurt_flash"][dir_key]
        sprite_surf = seq[int(anim_timer * 14) % len(seq)]
    elif state == "attack":
        seq = bank["attack"][dir_key]
        sprite_surf = seq[int(anim_timer * 15) % len(seq)]
    elif state == "walk":
        seq = bank["walk"][dir_key]
        sprite_surf = seq[int(anim_timer * 11) % len(seq)]
    else:
        seq = bank["idle"][dir_key]
        sprite_surf = seq[int(anim_timer * 7) % len(seq)]

    if sprite_surf is not None:
        sw, sh = sprite_surf.get_size()
        draw_x = int(bx - sw // 2)
        draw_y = int(by - sh + MESH_PAD_Y + 6)
        surface.blit(sprite_surf, (draw_x, draw_y))

    if state == "attack":
        _draw_slash_arc(
            surface,
            bx + facing * 24,
            by - (85 if is_gwima else 54),
            facing,
            95 if is_gwima else 64,
            COLOR_GWIMA_FIRE if is_gwima else COLOR_NEON_PINK,
            COLOR_HUNMOON_GOLD,
            0,
        )
