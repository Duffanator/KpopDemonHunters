"""
Sprite Sheet Background Remover & Connected-Component Pose Extractor (`tools/process_sprites.py`).
Extracts full-body illustrated 2D arcade sprites from white-background sheets into
tightly cropped, halo-free transparent RGBA PNGs.
"""

from collections import deque
import math
import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES_DIR = os.path.join(BASE_DIR, "assets", "sprites")
RAW_DIR = os.path.join(SPRITES_DIR, "raw")


def remove_white_background(img: Image.Image) -> Image.Image:
    """
    Flood-fill pure white background (#FFFFFF) into RGBA transparency,
    clear enclosed white gaps (like between legs/weapons), and de-fringe
    both dark ink outlines and colored weapon glows against white.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    pixels = rgba.load()

    def is_white_bg(r: int, g: int, b: int, strict: bool = False) -> bool:
        sat = max(r, g, b) - min(r, g, b)
        if strict:
            return min(r, g, b) > 242 and sat < 12
        return min(r, g, b) > 228 and sat < 20

    visited = bytearray(w * h)
    bg_mask = bytearray(w * h)
    q = deque()

    # 1. Seed flood-fill from all 4 outer borders
    for x in range(w):
        for y in (0, h - 1):
            idx = y * w + x
            r, g, b, _ = pixels[x, y]
            if not visited[idx] and is_white_bg(r, g, b):
                visited[idx] = 1
                bg_mask[idx] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            idx = y * w + x
            r, g, b, _ = pixels[x, y]
            if not visited[idx] and is_white_bg(r, g, b):
                visited[idx] = 1
                bg_mask[idx] = 1
                q.append((x, y))

    while q:
        cx, cy = q.popleft()
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                nidx = ny * w + nx
                if not visited[nidx]:
                    r, g, b, _ = pixels[nx, ny]
                    if is_white_bg(r, g, b):
                        visited[nidx] = 1
                        bg_mask[nidx] = 1
                        q.append((nx, ny))

    # 2. Detect enclosed pure-white background holes (e.g. between legs, arms, or weapon shafts)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            idx = y * w + x
            if not visited[idx]:
                r, g, b, _ = pixels[x, y]
                if is_white_bg(r, g, b, strict=True):
                    comp = []
                    cq = deque([(x, y)])
                    visited[idx] = 1
                    while cq:
                        px, py = cq.popleft()
                        comp.append((px, py))
                        for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                            if 0 <= nx < w and 0 <= ny < h:
                                nidx = ny * w + nx
                                if not visited[nidx]:
                                    nr, ng, nb, _ = pixels[nx, ny]
                                    if is_white_bg(nr, ng, nb, strict=False):
                                        visited[nidx] = 1
                                        cq.append((nx, ny))
                    # Enclosed background gaps are larger than small eye highlights/collar triangles
                    if len(comp) > 320:
                        for px, py in comp:
                            bg_mask[py * w + px] = 1

    # 3. Apply transparency & de-fringe edge pixels bordering the background
    for y in range(h):
        row_off = y * w
        for x in range(w):
            idx = row_off + x
            if bg_mask[idx]:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                near_bg = False
                for nx, ny in (
                    (x - 1, y),
                    (x + 1, y),
                    (x, y - 1),
                    (x, y + 1),
                    (x - 1, y - 1),
                    (x + 1, y - 1),
                    (x - 1, y + 1),
                    (x + 1, y + 1),
                ):
                    if 0 <= nx < w and 0 <= ny < h and bg_mask[ny * w + nx]:
                        near_bg = True
                        break
                if near_bg:
                    r, g, b, _ = pixels[x, y]
                    min_c = min(r, g, b)
                    max_c = max(r, g, b)
                    sat = max_c - min_c
                    if min_c > 165:
                        if sat < 24:
                            # Anti-aliased black outline pixel against white -> darken & feather alpha
                            lum = (r + g + b) / 3.0
                            new_a = max(0, min(255, int((248 - lum) * 3.0)))
                            pixels[x, y] = (int(r * 0.35), int(g * 0.35), int(b * 0.35), new_a)
                        else:
                            # Colored weapon/magic glow edge against white -> un-multiply white
                            new_a = max(0, min(255, int((252 - min_c) * 3.4)))
                            a_norm = max(0.2, new_a / 255.0)
                            nr = max(0, min(255, int((r - 255 * (1.0 - a_norm)) / a_norm)))
                            ng = max(0, min(255, int((g - 255 * (1.0 - a_norm)) / a_norm)))
                            nb = max(0, min(255, int((b - 255 * (1.0 - a_norm)) / a_norm)))
                            pixels[x, y] = (nr, ng, nb, new_a)

    return rgba


def extract_character_sprites(rgba: Image.Image, num_sprites: int) -> list[Image.Image]:
    """
    Use 8-connected component labeling to isolate `num_sprites` full-body characters
    arranged left-to-right, without clipping diagonal weapons or capes.
    """
    w, h = rgba.size
    pixels = rgba.load()
    labels = [0] * (w * h)
    components: list[dict] = []

    comp_id = 0
    for y in range(h):
        for x in range(w):
            idx = y * w + x
            if labels[idx] == 0 and pixels[x, y][3] > 20:
                comp_id += 1
                q = deque([(x, y)])
                labels[idx] = comp_id
                pts = []
                sum_x = 0
                sum_y = 0
                min_x, max_x = x, x
                min_y, max_y = y, y

                while q:
                    cx, cy = q.popleft()
                    pts.append((cx, cy))
                    sum_x += cx
                    sum_y += cy
                    if cx < min_x:
                        min_x = cx
                    if cx > max_x:
                        max_x = cx
                    if cy < min_y:
                        min_y = cy
                    if cy > max_y:
                        max_y = cy

                    # 8-connected neighborhood with 2px bridge to keep thin slash trails connected
                    for dy in (-2, -1, 0, 1, 2):
                        ny = cy + dy
                        if 0 <= ny < h:
                            row_o = ny * w
                            for dx in (-2, -1, 0, 1, 2):
                                nx = cx + dx
                                if 0 <= nx < w:
                                    nidx = row_o + nx
                                    if labels[nidx] == 0 and pixels[nx, ny][3] > 20:
                                        labels[nidx] = comp_id
                                        q.append((nx, ny))

                if len(pts) >= 20:
                    components.append(
                        {
                            "id": comp_id,
                            "pts": pts,
                            "area": len(pts),
                            "cx": sum_x / len(pts),
                            "cy": sum_y / len(pts),
                            "bbox": (min_x, min_y, max_x + 1, max_y + 1),
                        }
                    )

    if len(components) < num_sprites:
        # Fallback if two poses touched slightly: split evenly
        step = w // num_sprites
        return [rgba.crop((i * step, 0, (i + 1) * step, h)) for i in range(num_sprites)]

    # Top `num_sprites` largest components are the main character bodies
    components.sort(key=lambda c: c["area"], reverse=True)
    main_groups = components[:num_sprites]
    extra_components = components[num_sprites:]

    # Sort main characters Left-to-Right by centroid X
    main_groups.sort(key=lambda c: c["cx"])
    for g in main_groups:
        g["all_pts"] = list(g["pts"])

    # Assign any secondary floating components (e.g., Mystery's floating orbs, Bobby's thrown phone)
    # to the nearest main character
    for ext in extra_components:
        best_group = min(
            main_groups,
            key=lambda g: math.hypot((ext["cx"] - g["cx"]) * 0.8, (ext["cy"] - g["cy"]) * 0.5),
        )
        best_group["all_pts"].extend(ext["pts"])

    # Render each character group onto its own tightly cropped transparent image
    sprites: list[Image.Image] = []
    for g in main_groups:
        pts = g["all_pts"]
        min_x = min(p[0] for p in pts)
        max_x = max(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_y = max(p[1] for p in pts)

        cw = max_x - min_x + 1
        ch = max_y - min_y + 1
        out_img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        out_px = out_img.load()
        for px, py in pts:
            out_px[px - min_x, py - min_y] = pixels[px, py]
        sprites.append(out_img)

    return sprites


def process_all_sheets():
    tasks = [
        ("rumi_sheet.jpg", 3, ["rumi_idle", "rumi_walk", "rumi_attack"], "chars"),
        ("zoey_sheet.jpg", 3, ["zoey_idle", "zoey_walk", "zoey_attack"], "chars"),
        ("mira_sheet.jpg", 3, ["mira_idle", "mira_walk", "mira_attack"], "chars"),
        ("bobby_sheet.jpg", 3, ["bobby_idle", "bobby_walk", "bobby_attack"], "chars"),
        ("enemies_sheet.jpg", 4, ["faceless", "dokkaebi_trickster", "dokkaebi_brute", "mulguishin"], "enemies"),
        ("saja_boys_sheet.jpg", 4, ["mystery", "romance", "abby", "baby"], "bosses"),
        ("final_bosses_sheet.jpg", 2, ["jinu", "gwima"], "bosses"),
    ]

    for raw_name, count, out_names, subdir in tasks:
        src_path = os.path.join(RAW_DIR, raw_name)
        if not os.path.isfile(src_path):
            print(f"[WARN] Missing {src_path}")
            continue
        out_dir = os.path.join(SPRITES_DIR, subdir)
        os.makedirs(out_dir, exist_ok=True)
        print(f"Processing {raw_name} -> {count} sprites...")
        img = Image.open(src_path)
        rgba = remove_white_background(img)
        sprites = extract_character_sprites(rgba, count)
        for name, sp in zip(out_names, sprites):
            dest = os.path.join(out_dir, f"{name}.png")
            sp.save(dest, "PNG")
            print(f"  [OK] {subdir}/{name}.png ({sp.size[0]}x{sp.size[1]})")


def generate_derived_stage_backgrounds():
    """
    Create high-res illustrated backgrounds for Stage 3 (bathhouse.jpg),
    Stage 5 (saja_concert.jpg), and Stage 6 (gwima_lair.jpg) from our
    illustrated base backgrounds using Pillow color-grading & atmospheric compositing.
    """
    from PIL import ImageDraw, ImageEnhance, ImageFilter

    bg_dir = os.path.join( BASE_DIR, "assets", "backgrounds")
    os.makedirs(bg_dir, exist_ok=True)

    concert_path = os.path.join(bg_dir, "concert.jpg")
    plane_path = os.path.join(bg_dir, "plane.jpg")

    if os.path.isfile(concert_path):
        base_concert = Image.open(concert_path).convert("RGB")
        w, h = base_concert.size

        # 1. Stage 5: Demonic Saja Boys Stadium (`saja_concert.jpg`)
        # Flip horizontally for fresh stage geometry & apply crimson/purple dark-idol color grade
        saja = base_concert.transpose(Image.FLIP_LEFT_RIGHT).copy()
        px = saja.load()
        for y in range(h):
            for x in range(w):
                r, g, b = px[x, y]
                # Shift cyan/gold into hypnotic crimson, magenta & dark violet
                nr = min(255, int(r * 1.15 + g * 0.45))
                ng = int(g * 0.25)
                nb = min(255, int(b * 0.95 + r * 0.25))
                px[x, y] = (nr, ng, nb)
        saja = ImageEnhance.Contrast(saja).enhance(1.15)
        saja.save(os.path.join(bg_dir, "saja_concert.jpg"), "JPEG", quality=92)
        print("  [OK] backgrounds/saja_concert.jpg")

        # 2. Stage 6: Heart of the Inferno — Throne of Gwi-Ma (`gwima_lair.jpg`)
        gwima_bg = base_concert.copy()
        gpx = gwima_bg.load()
        for y in range(h):
            for x in range(w):
                r, g, b = gpx[x, y]
                lum = (r + g + b) / 3.0
                if y < int(h * 0.62):
                    # Volcanic orange/gold/purple living fire sky
                    nr = min(255, int(lum * 1.45 + 35))
                    ng = min(255, int(lum * 0.65))
                    nb = min(255, int(b * 0.45))
                else:
                    # Dark obsidian arena floor with molten fiery reflections
                    nr = min(255, int(r * 0.95 + 20))
                    ng = min(255, int(g * 0.38))
                    nb = min(255, int(b * 0.35))
                gpx[x, y] = (nr, ng, nb)
        gwima_bg = ImageEnhance.Contrast(gwima_bg).enhance(1.2)
        gwima_bg.save(os.path.join(bg_dir, "gwima_lair.jpg"), "JPEG", quality=92)
        print("  [OK] backgrounds/gwima_lair.jpg")

    # 3. Stage 3: Steam & Shadows Bathhouse (`bathhouse.jpg`)
    # Render a dedicated high-res illustrated Korean Traditional Bathhouse (cedar shoji screens,
    # glowing lanterns, recessed stone hot-tub alcoves, wet ceramic tile floor, and front stone curb)
    bw, bh = 960, 540
    bath_img = Image.new("RGBA", (bw, bh), (16, 28, 38, 255))
    bdraw = ImageDraw.Draw(bath_img)

    # Ceiling & upper timber rafters (y = 0 .. 82)
    bdraw.rectangle((0, 0, bw, 82), fill=(22, 16, 14, 255))
    for rx in range(0, bw + 80, 80):
        bdraw.polygon([(rx - 18, 0), (rx + 18, 0), (rx + 8, 82), (rx - 8, 82)], fill=(48, 32, 22, 255))
    bdraw.rectangle((0, 74, bw, 86), fill=(68, 44, 28, 255))
    bdraw.line((0, 86, bw, 86), fill=(18, 12, 8, 255), width=3)

    # Back Wall: Cedar Timber Framing & Warm Backlit Hanji Shoji Screens (y = 86 .. 374)
    bdraw.rectangle((0, 86, bw, 374), fill=(52, 34, 24, 255))
    for sx in range(24, bw - 20, 188):
        # Outer cedar frame
        bdraw.rectangle((sx, 98, sx + 156, 336), fill=(38, 24, 16, 255), outline=(18, 10, 6, 255), width=3)
        # Warm glowing shoji paper interior
        for py in range(106, 330):
            t_grad = (py - 106) / 224.0
            r_c = int(245 - t_grad * 55)
            g_c = int(205 - t_grad * 65)
            b_c = int(135 - t_grad * 45)
            bdraw.line((sx + 8, py, sx + 148, py), fill=(r_c, g_c, b_c, 255))
        # Traditional Korean lattice grid
        for gx in range(sx + 8, sx + 150, 28):
            bdraw.line((gx, 106, gx, 328), fill=(58, 36, 22, 255), width=3)
        for gy in range(106, 330, 32):
            bdraw.line((sx + 8, gy, sx + 148, gy), fill=(58, 36, 22, 255), width=3)

        # Hanging warm lantern between shoji panels
        lx = sx + 172
        if lx < bw - 12:
            bdraw.line((lx, 86, lx, 124), fill=(20, 14, 10, 255), width=3)
            bdraw.rounded_rectangle((lx - 14, 124, lx + 14, 168), radius=6, fill=(255, 195, 95, 255), outline=(45, 25, 12, 255), width=2)
            bdraw.line((lx - 10, 138, lx + 10, 138), fill=(185, 95, 35, 255), width=2)
            bdraw.line((lx - 10, 154, lx + 10, 154), fill=(185, 95, 35, 255), width=2)

    # Stone Dado Wall Base & Recessed Hot-Tub Alcoves along the back wall (y = 328 .. 378)
    bdraw.rectangle((0, 328, bw, 378), fill=(44, 58, 66, 255))
    bdraw.line((0, 328, bw, 328), fill=(90, 115, 125, 255), width=3)
    for tx in (70, 520):
        # Carved granite hot tub basin along back wall
        bdraw.rounded_rectangle((tx, 334, tx + 340, 380), radius=10, fill=(68, 84, 94, 255), outline=(22, 30, 36, 255), width=3)
        bdraw.rounded_rectangle((tx + 12, 342, tx + 328, 372), radius=6, fill=(28, 195, 210, 255), outline=(145, 245, 255, 255), width=2)

    # Walkable Wet Ceramic Tile Floor (y = 378 .. 488)
    for fy in range(378, 488):
        t_f = (fy - 378) / 110.0
        r_f = int(26 + t_f * 14)
        g_f = int(68 + t_f * 24)
        b_f = int(82 + t_f * 28)
        bdraw.line((0, fy, bw, fy), fill=(r_f, g_f, b_f, 255))

    # Perspective tile grout lines on the walkable floor
    for ty in range(378, 490, 22):
        bdraw.line((0, ty, bw, ty), fill=(20, 50, 62, 255), width=2)
    for gx in range(-120, bw + 160, 64):
        dx_persp = int((gx - bw * 0.5) * 0.28)
        bdraw.line((gx, 378, gx + dx_persp, 488), fill=(20, 50, 62, 255), width=2)

    # Top & Bottom Neon/Stone Floor Trim Borders (clearly marking walkable floor y = 378 .. 488)
    bdraw.line((0, 378, bw, 378), fill=(65, 225, 240, 255), width=3)
    bdraw.line((0, 488, bw, 488), fill=(65, 225, 240, 255), width=4)

    # Front Raised Stone Curb / Drainage Wall (y = 488 .. 540)
    bdraw.rectangle((0, 490, bw, bh), fill=(24, 34, 42, 255))
    for cx in range(0, bw, 96):
        bdraw.rectangle((cx + 4, 496, cx + 88, 534), fill=(32, 46, 56, 255), outline=(16, 22, 28, 255), width=2)

    # Soft Steam Glow & Lantern Bloom Overlay
    mist = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(mist)
    mdraw.rectangle((0, 325, bw, 410), fill=(155, 240, 250, 52))
    for sx in range(24, bw - 20, 188):
        lx = sx + 172
        if lx < bw - 12:
            mdraw.ellipse((lx - 65, 95, lx + 65, 215), fill=(255, 190, 85, 65))
    mist = mist.filter(ImageFilter.GaussianBlur(radius=22))
    bath_rgba = Image.alpha_composite(bath_img, mist).convert("RGB")
    bath_rgba.save(os.path.join(bg_dir, "bathhouse.jpg"), "JPEG", quality=92)
    print("  [OK] backgrounds/bathhouse.jpg")


if __name__ == "__main__":
    process_all_sheets()
    generate_derived_stage_backgrounds()
