"""
2D Skeletal Mesh Deformation & Multi-Frame Animation Generator (`src/animator.py`).
Uses Pillow's C-accelerated `Image.Transform.MESH` to generate smooth multi-frame
animation sequences from high-res illustrated character, enemy, and boss sprites:
- 6-frame Idle breathing & hair/flame ripple cycle
- 8-frame Walk stride cycle (alternating left/right leg stepping, knee lift, arm counter-swing, head bob)
- 8-frame Run sprint cycle (forward lean, high knee drive, fast stride)
- 16-frame 4-Hit Attack Combo (4 frames per combo step: Windup -> Launch -> Peak Impact -> Follow-through,
  with distinct upward, horizontal, downward, and lunging finisher arcs)
- 4-frame Jump & Air Kick sequence (Takeoff -> Rising Tuck -> Apex Kick/Slash -> Landing)
- 3-frame Hurt / Knockback recoil sequence
"""

import math
import os
from PIL import Image
import pygame


def pil_to_pygame(pil_img: Image.Image) -> pygame.Surface:
    """Convert an RGBA PIL Image directly to a hardware-friendly Pygame alpha Surface."""
    raw_bytes = pil_img.tobytes()
    return pygame.image.fromstring(raw_bytes, pil_img.size, "RGBA").convert_alpha()


def pygame_to_pil(surf: pygame.Surface) -> Image.Image:
    """Convert a Pygame RGBA Surface to a PIL Image."""
    raw_bytes = pygame.image.tostring(surf, "RGBA")
    return Image.frombytes("RGBA", surf.get_size(), raw_bytes)


def warp_sprite_mesh(
    src_img: Image.Image,
    native_facing: int,
    dx_dy_fn,
    pad_x: int = 24,
    pad_y: int = 20,
    grid_cols: int = 12,
    grid_rows: int = 14,
) -> Image.Image:
    """
    Apply a continuous, tear-free 2D skeletal UV mesh deformation to `src_img`
    using Pillow's C-accelerated `Image.Transform.MESH`.
    `dx_dy_fn(u_fwd, v)` takes:
      - `u_fwd`: horizontal coordinate in [-1.0 (back), +1.0 (front)]
      - `v`: vertical coordinate in [0.0 (top of head), 1.0 (bottom of feet)]
    and returns `(dx_pixels, dy_pixels)` displacement in the output image.
    """
    sw, sh = src_img.size
    ow = sw + pad_x * 2
    oh = sh + pad_y * 2

    padded = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
    padded.paste(src_img, (pad_x, pad_y))

    cx = pad_x + sw * 0.5
    top_y = float(pad_y)
    half_w = max(1.0, sw * 0.5)
    body_h = max(1.0, float(sh))

    # Precompute inverse source coordinates at every grid vertex (cols+1 x rows+1)
    verts_sx = [[0.0] * (grid_cols + 1) for _ in range(grid_rows + 1)]
    verts_sy = [[0.0] * (grid_cols + 1) for _ in range(grid_rows + 1)]

    for r in range(grid_rows + 1):
        oy = (r * oh) / grid_rows
        v = max(-0.15, min(1.15, (oy - top_y) / body_h))
        for c in range(grid_cols + 1):
            ox = (c * ow) / grid_cols
            u = max(-1.25, min(1.25, (ox - cx) / half_w))
            u_fwd = u * native_facing
            dx, dy = dx_dy_fn(u_fwd, v)
            verts_sx[r][c] = ox - dx
            verts_sy[r][c] = oy - dy

    mesh_data = []
    for r in range(grid_rows):
        y0 = int(round((r * oh) / grid_rows))
        y1 = int(round(((r + 1) * oh) / grid_rows))
        if y1 <= y0:
            continue
        for c in range(grid_cols):
            x0 = int(round((c * ow) / grid_cols))
            x1 = int(round(((c + 1) * ow) / grid_cols))
            if x1 <= x0:
                continue
            target_box = (x0, y0, x1, y1)
            # Counter-clockwise source quad: UL, LL, LR, UR
            quad = (
                verts_sx[r][c],
                verts_sy[r][c],
                verts_sx[r + 1][c],
                verts_sy[r + 1][c],
                verts_sx[r + 1][c + 1],
                verts_sy[r + 1][c + 1],
                verts_sx[r][c + 1],
                verts_sy[r][c + 1],
            )
            mesh_data.append((target_box, quad))

    return padded.transform((ow, oh), Image.Transform.MESH, mesh_data, Image.Resampling.BILINEAR)


def build_idle_frames(base_pil: Image.Image, native_facing: int, num_frames: int = 6, is_flame: bool = False) -> list[Image.Image]:
    """Generate a smooth 6-frame breathing, weapon poise, and hair/flame ripple idle cycle."""
    frames = []
    for i in range(num_frames):
        theta = (i * 2.0 * math.pi) / num_frames
        breath = math.sin(theta)
        wave = math.cos(theta)

        def deform(u_fwd: float, v: float, b=breath, wv=wave):
            # Feet stay planted at v = 1.0
            anchor = max(0.0, 1.0 - v)
            # Chest & shoulder breathing expansion + vertical poise bob
            dy = -2.8 * b * (anchor ** 1.1)
            dx = native_facing * (1.6 * b * u_fwd * max(0.0, 1.0 - abs(v - 0.38) * 2.2))

            # Hair / cape / living flame ripple
            if is_flame:
                dx += 5.5 * math.sin(theta + v * 5.0) * anchor
                dy += 3.0 * math.cos(theta + u_fwd * 3.0) * anchor
            elif u_fwd < 0.0 or v < 0.35:
                dx += 2.6 * math.sin(theta - v * 4.0) * anchor

            # Weapon hand subtle poise oscillation (front side)
            if u_fwd > 0.25 and 0.15 < v < 0.68:
                dy += 3.2 * wv * ((u_fwd - 0.25) / 0.75)

            return dx, dy

        frames.append(warp_sprite_mesh(base_pil, native_facing, deform))
    return frames


def build_walk_frames(
    idle_pil: Image.Image,
    walk_pil: Image.Image | None,
    native_facing: int,
    num_frames: int = 8,
    stride_px: float = 11.5,
    lift_px: float = 8.5,
    bob_px: float = 4.5,
    lean_px: float = 4.0,
) -> list[Image.Image]:
    """
    Generate an 8-frame articulated walk or run cycle:
    - Alternating left/right leg stride & knee lift
    - Counter-swinging shoulders & weapon arm
    - Double-time vertical stride bounce & forward lean
    """
    if walk_pil is None:
        walk_pil = idle_pil

    frames = []
    for i in range(num_frames):
        theta = (i * 2.0 * math.pi) / num_frames
        # Use `idle_pil` on the passing steps (frames 3 and 7) and `walk_pil` on extended stride steps
        use_idle_base = (i in (3, 7)) and (walk_pil is not idle_pil)
        src = idle_pil if use_idle_base else walk_pil
        # Scale down mesh leg swing slightly when using the already-striding hero `walk_pil`
        leg_scale = 0.72 if (walk_pil is not idle_pil and not use_idle_base) else 1.0

        def deform(u_fwd: float, v: float, th=theta, l_sc=leg_scale):
            dx = 0.0
            dy = 0.0

            # 1. Forward torso lean (strongest at head/shoulders, 0 at feet)
            anchor = max(0.0, 1.0 - v)
            dx += native_facing * lean_px * anchor

            # 2. Double-frequency vertical stride bounce (2 bounces per 8-frame cycle)
            dy -= bob_px * abs(math.cos(th)) * (0.35 + 0.65 * anchor)

            # 3. Articulated Left & Right Leg Scissoring Stride + Foot Lift (v > 0.50)
            if v > 0.50:
                w_leg = ((v - 0.50) / 0.50) ** 1.25
                leg_side = math.tanh(u_fwd * 3.0)  # +1 for front leg, -1 for back leg
                # Horizontal scissor swing
                dx += native_facing * (stride_px * l_sc) * w_leg * leg_side * math.sin(th)
                # Vertical knee/foot lift on the forward-swinging leg
                lift_front = max(0.0, math.cos(th))
                lift_back = max(0.0, -math.cos(th))
                w_front = 0.5 * (1.0 + leg_side)
                w_back = 0.5 * (1.0 - leg_side)
                dy -= lift_px * w_leg * (w_front * lift_front + w_back * lift_back)

            # 4. Counter-swinging Arms & Shoulders (0.18 < v < 0.60)
            if 0.16 < v < 0.62:
                w_arm = math.exp(-((v - 0.38) / 0.18) ** 2) * min(1.0, abs(u_fwd) / 0.55)
                dx -= native_facing * (stride_px * 0.48) * w_arm * math.sin(th)
                dy += (lift_px * 0.42) * w_arm * math.sin(th) * math.copysign(1.0, u_fwd)

            # 5. Flowing Hair / Braid / Coat Tails
            if u_fwd < -0.1 or v < 0.30:
                dx += 3.5 * math.sin(th - v * 4.5) * anchor

            return dx, dy

        frames.append(warp_sprite_mesh(src, native_facing, deform))
    return frames


def build_attack_combo_frames(
    idle_pil: Image.Image,
    walk_pil: Image.Image | None,
    attack_pil: Image.Image | None,
    native_facing: int,
) -> list[list[Image.Image]]:
    """
    Generate 4 distinct 4-frame attack animations (16 frames total) for a 4-hit combo:
      - Combo 0: Fast Horizontal Slash (Windup -> Launch -> Peak Extension -> Recovery)
      - Combo 1: Rising Uppercut Slash (Low Coil -> Upward Sweep -> High Peak -> Recovery)
      - Combo 2: Heavy Overhead Cleave (High Raise -> Downward Smash -> Ground Impact -> Recovery)
      - Combo 3: Explosive Lunging Finisher (Deep Coil -> Hyper Lunge -> Wide Finisher -> Settle)
    Each combo step returns 4 sequential frames.
    """
    if walk_pil is None:
        walk_pil = idle_pil
    if attack_pil is None:
        attack_pil = walk_pil

    combos: list[list[Image.Image]] = []

    # Spec for each of the 4 frames within each of the 4 combo steps:
    # (source_img, lean_px, stretch_front, weapon_dy, body_dy)
    combo_specs = [
        # Combo 0: Horizontal Slash
        [
            (walk_pil, -8.0, -4.0, -8.0, 2.0),
            (attack_pil, 5.0, 6.0, -4.0, 0.0),
            (attack_pil, 13.0, 14.0, 2.0, 2.0),
            (walk_pil, 6.0, 4.0, 4.0, 1.0),
        ],
        # Combo 1: Rising Uppercut Slash
        [
            (walk_pil, -6.0, -3.0, 12.0, 5.0),
            (attack_pil, 6.0, 8.0, -6.0, -2.0),
            (attack_pil, 12.0, 15.0, -18.0, -6.0),
            (idle_pil, 4.0, 3.0, -8.0, -2.0),
        ],
        # Combo 2: Heavy Overhead Cleave
        [
            (idle_pil, -10.0, -4.0, -18.0, -5.0),
            (attack_pil, 8.0, 10.0, -2.0, 1.0),
            (attack_pil, 15.0, 16.0, 16.0, 6.0),
            (walk_pil, 7.0, 5.0, 8.0, 3.0),
        ],
        # Combo 3: Explosive Lunging Finisher
        [
            (walk_pil, -14.0, -8.0, -10.0, 4.0),
            (attack_pil, 10.0, 12.0, -4.0, -2.0),
            (attack_pil, 20.0, 22.0, 0.0, 2.0),
            (attack_pil, 14.0, 14.0, 6.0, 3.0),
        ],
    ]

    for step_frames_spec in combo_specs:
        step_frames: list[Image.Image] = []
        for src, lean, stretch_f, wep_dy, b_dy in step_frames_spec:

            def deform(u_fwd: float, v: float, ln=lean, sf=stretch_f, wdy=wep_dy, bdy=b_dy):
                anchor = max(0.0, 1.0 - v)
                # Torso & head lean forward/back
                dx = native_facing * ln * (anchor ** 0.85)
                dy = bdy * anchor

                # Front arm / weapon extension & vertical slash arc
                if u_fwd > 0.05:
                    w_front = ((u_fwd - 0.05) / 0.95) ** 1.1
                    dx += native_facing * sf * w_front * (0.4 + 0.6 * anchor)
                    dy += wdy * w_front * max(0.0, 1.0 - abs(v - 0.42) * 1.4)

                return dx, dy

            step_frames.append(warp_sprite_mesh(src, native_facing, deform))
        combos.append(step_frames)

    return combos


def build_jump_frames(
    idle_pil: Image.Image,
    walk_pil: Image.Image | None,
    attack_pil: Image.Image | None,
    native_facing: int,
) -> list[Image.Image]:
    """Generate 4 jump frames: Launch Stretch, Rising Tuck, Mid-Air Apex Pose, and Jump-Kick/Air-Slash."""
    if walk_pil is None:
        walk_pil = idle_pil
    if attack_pil is None:
        attack_pil = walk_pil

    specs = [
        (walk_pil, 3.0, -6.0, 0.0),    # Frame 0: Rising launch
        (walk_pil, 6.0, -12.0, -8.0),  # Frame 1: Mid-air knee tuck
        (idle_pil, 4.0, -8.0, -4.0),   # Frame 2: Apex hover
        (attack_pil, 12.0, -6.0, 10.0),# Frame 3: Diving Air Slash / Jump Kick!
    ]
    frames = []
    for src, lean, leg_tuck, wep_ext in specs:

        def deform(u_fwd: float, v: float, ln=lean, lt=leg_tuck, we=wep_ext):
            dx = native_facing * ln * (1.0 - v * 0.5)
            dy = 0.0
            if v > 0.50:
                # Tuck legs upward in mid-air
                dy += lt * ((v - 0.50) / 0.50)
                dx += native_facing * (we * 0.5) * ((v - 0.50) / 0.50) * math.tanh(u_fwd * 2.5)
            if u_fwd > 0.15:
                dx += native_facing * we * ((u_fwd - 0.15) / 0.85)
            return dx, dy

        frames.append(warp_sprite_mesh(src, native_facing, deform))
    return frames


def build_hurt_frames(idle_pil: Image.Image, native_facing: int) -> list[Image.Image]:
    """Generate 3 hurt/recoil frames bending backward from impact."""
    frames = []
    for recoil in (-10.0, -16.0, -7.0):

        def deform(u_fwd: float, v: float, rc=recoil):
            anchor = max(0.0, 1.0 - v)
            # Upper body snaps backward and curves on impact
            dx = native_facing * rc * (anchor ** 0.9)
            dy = 4.0 * math.sin(v * math.pi)
            return dx, dy

        frames.append(warp_sprite_mesh(idle_pil, native_facing, deform))
    return frames
