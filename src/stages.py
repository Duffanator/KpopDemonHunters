"""
Stage Background Renderer, Parallax Environment & Wave Progression Manager
for all 6 story stages of K-Pop Demon Hunters.
"""

import math
import os
import random
import pygame
from src.config import (
    BACKGROUNDS_DIR,
    COLOR_BLACK,
    COLOR_DEMON_PURPLE,
    COLOR_GWIMA_FIRE,
    COLOR_HUNMOON_BLUE,
    COLOR_HUNMOON_GOLD,
    COLOR_NEON_CYAN,
    COLOR_NEON_PINK,
    COLOR_WHITE,
    INTERNAL_HEIGHT,
    INTERNAL_WIDTH,
    LANE_BOTTOM,
    LANE_TOP,
    STAGES,
    get_stage_z_bounds,
)
from src.entities import BossFighter, BreakableProp, EnemyFighter, FloatingText, HazardZone, PickupItem

_STAGE_BG_CACHE: dict[str, tuple[pygame.Surface, pygame.Surface]] = {}


def _get_stage_bg_pair(stage_id: str) -> tuple[pygame.Surface, pygame.Surface] | None:
    if stage_id in _STAGE_BG_CACHE:
        return _STAGE_BG_CACHE[stage_id]
    bg_path = os.path.join(BACKGROUNDS_DIR, f"{stage_id}.jpg")
    if os.path.isfile(bg_path):
        try:
            raw = pygame.image.load(bg_path).convert()
            tile_a = pygame.transform.smoothscale(raw, (INTERNAL_WIDTH, INTERNAL_HEIGHT))
            tile_b = pygame.transform.flip(tile_a, True, False)
            _STAGE_BG_CACHE[stage_id] = (tile_a, tile_b)
            return _STAGE_BG_CACHE[stage_id]
        except pygame.error:
            return None
    return None


class StageManager:
    """Manages stage backgrounds, camera locking, enemy waves, environmental hazards, and boss spawns."""

    def __init__(self, stage_index: int = 0):
        self.stage_index = stage_index % len(STAGES)
        self.cfg = STAGES[self.stage_index]
        self.camera_x = 0.0
        self.camera_locked = False
        self.current_wave_idx = 0
        self.wave_spawned = False
        self.stage_cleared = False
        self.clear_timer = 0.0
        self.anim_timer = 0.0
        self.hazard_cooldown = 5.5
        self.go_arrow_timer = 0.0
        self.boss_warning_timer = 0.0

    def setup_stage_props(self) -> list[BreakableProp]:
        """
        Populate the stage with both solid background-aligned furniture/structures
        and interactive destructible/triggerable floor objects!
        """
        props: list[BreakableProp] = []
        drop_cycle = ["boba", "tteokbokki", "corndog", "lightstick", "boba", "kbbq"]
        length = self.cfg["length"]
        sid = self.cfg["id"]
        num_tiles = (length // INTERNAL_WIDTH) + 1

        def tile_wx(t_idx: int, img_x: float) -> float:
            if t_idx % 2 == 1:
                return float(t_idx * INTERNAL_WIDTH + (INTERNAL_WIDTH - img_x))
            return float(t_idx * INTERNAL_WIDTH + img_x)

        # 1. Register Background-Aligned Solid & Interactive Structures per 960px tile
        if sid == "plane":
            for t_idx in range(num_tiles):
                # Marble Bar Counter (342..558 in tile_a; front base at z=384, top slab 78px high at y=306)
                props.append(BreakableProp(tile_wx(t_idx, 450.0), 384.0, "bar_counter", "boba"))
                # Purple VIP Velvet Sofas & Side Table (560..790 in tile_a; front base at z=368, cushions 48px high)
                props.append(BreakableProp(tile_wx(t_idx, 675.0), 368.0, "vip_sofa", None))
                # Right Marble Counter (894..960 in tile_a; front base at z=384, top slab 78px high)
                props.append(BreakableProp(tile_wx(t_idx, 926.0), 384.0, "side_counter", "lightstick"))

        elif sid == "train":
            for t_idx in range(num_tiles):
                # Top-right Rooftop AC & High-Voltage Ventilation Unit (820..960 in tile_a; base at z=396, 58px high)
                props.append(BreakableProp(tile_wx(t_idx, 890.0), 396.0, "train_ac", None))
                # Bottom-right Electrical Relay Box (630..740 in tile_a; base at z=472, 44px high)
                props.append(BreakableProp(tile_wx(t_idx, 685.0), 472.0, "train_relay", None))

        # 2. Populate Interactive Floor Objects & Destructible Props
        idx = 0
        for px in range(340, length - 260, 390):
            zl, zh = get_stage_z_bounds(sid, float(px))
            drop_item = drop_cycle[idx % len(drop_cycle)]

            if sid == "plane":
                # Alternate between VIP Rolling Beverage Carts and Huntr/x Tour Road Cases
                ptype = "bev_cart" if (idx % 2 == 0) else "crate"
                pz = zl + 34.0 if (idx % 2 == 0) else zh - 26.0
                props.append(BreakableProp(float(px), pz, ptype, drop_item))

            elif sid == "concert":
                # Interactive Stage Pyro Pods along the upper deck + Sonic Speaker Stacks
                if idx % 2 == 0:
                    props.append(BreakableProp(float(px - 70), zl + 14.0, "pyro_pod", None))
                pz = zh - 24.0 if (idx % 2 == 0) else zl + 28.0
                props.append(BreakableProp(float(px), pz, "speaker", drop_item))

            elif sid == "bathhouse":
                # Solid Steaming Jade Stone Hot Tubs + Cedar Bath Barrels
                if idx % 2 == 0:
                    props.append(BreakableProp(float(px - 80), zl + 24.0, "hottub", None))
                pz = zh - 22.0 if (idx % 2 == 0) else zl + 26.0
                props.append(BreakableProp(float(px + 40), pz, "bath_barrel", drop_item))

            elif sid == "train":
                # Armored KTX Cargo Crates positioned in the center-left of the roof deck
                pz = (zl + zh) * 0.5 + (-16.0 if idx % 2 == 0 else 16.0)
                props.append(BreakableProp(float(px), pz, "crate", drop_item))

            elif sid == "saja_concert":
                # Demonic Soul Obelisks + Dark Idol Speaker Stacks + Pyro Pods
                ptype = "soul_pillar" if (idx % 2 == 0) else "speaker"
                pz = zl + 26.0 if (idx % 2 == 0) else zh - 24.0
                props.append(BreakableProp(float(px), pz, ptype, drop_item))
                if idx % 3 == 1:
                    props.append(BreakableProp(float(px + 95), zl + 14.0, "pyro_pod", None))

            else:
                # Stage 6 (Gwi-Ma's Inferno): Molten Obsidian Braziers & Hunmoon Soul Crystals
                ptype = "soul_crystal" if (idx % 2 == 0) else "lava_brazier"
                pz = zl + 24.0 if (idx % 2 == 0) else zh - 24.0
                props.append(BreakableProp(float(px), pz, ptype, drop_item))

            idx += 1

        return props

    def update(
        self,
        dt: float,
        players: list,
        enemies: list[EnemyFighter],
        boss_ref: list,  # single-element list [BossFighter | None]
        hazards: list[HazardZone],
        pickups: list[PickupItem],
        texts: list[FloatingText],
        audio,
    ):
        self.anim_timer += dt
        if self.go_arrow_timer > 0:
            self.go_arrow_timer -= dt
        if self.boss_warning_timer > 0:
            self.boss_warning_timer -= dt

        living_players = [p for p in players if p.active and p.state != "ko"]
        if not living_players:
            return

        # Camera follows the leading player when not locked by an active wave
        if not self.camera_locked:
            avg_x = max(p.x for p in living_players)
            target_cam = max(self.camera_x, avg_x - 380.0)
            max_cam = max(0.0, float(self.cfg["length"] - INTERNAL_WIDTH))
            self.camera_x = min(max_cam, self.camera_x + (target_cam - self.camera_x) * min(1.0, dt * 6.0))

        # Check wave triggers
        waves = self.cfg["waves"]
        if self.current_wave_idx < len(waves):
            wave = waves[self.current_wave_idx]
            trigger_x = wave["x"] - 420.0
            if not self.wave_spawned and (self.camera_x >= trigger_x or max(p.x for p in living_players) >= wave["x"] - 120):
                self.wave_spawned = True
                self.camera_locked = True
                self._spawn_wave(wave, len(living_players), enemies, boss_ref, texts, audio)
            elif self.wave_spawned:
                # Check if all enemies and boss in this wave are defeated
                active_enemies = [e for e in enemies if e.hp > 0]
                active_boss = boss_ref[0] if (boss_ref[0] is not None and boss_ref[0].hp > 0) else None
                if not active_enemies and active_boss is None:
                    self.camera_locked = False
                    self.wave_spawned = False
                    self.current_wave_idx += 1
                    if self.current_wave_idx >= len(waves):
                        self.stage_cleared = True
                        self.clear_timer = 4.2
                        audio.play_sfx("stage_clear")
                    else:
                        self.go_arrow_timer = 2.6

        # Periodic stage environmental hazards
        self.hazard_cooldown -= dt
        if self.hazard_cooldown <= 0 and not self.stage_cleared:
            self.hazard_cooldown = random.uniform(5.0, 7.5)
            h_type = self.cfg.get("hazard")
            if h_type == "hottubs":
                # Bathhouse steam vent eruption
                target_p = random.choice(living_players)
                hazards.append(
                    HazardZone(
                        x=target_p.x,
                        z=target_p.z,
                        width=96,
                        depth=54,
                        warning_time=1.0,
                        active_time=0.5,
                        damage=12,
                        owner_team="enemy",
                        hazard_type="steam",
                    )
                )
            elif h_type == "train_signs":
                # Bullet train low tunnel sign sweeping across top lane!
                texts.append(
                    FloatingText(self.camera_x + 480, LANE_TOP + 25, 60, "WARNING: LOW TUNNEL SIGN!", COLOR_HUNMOON_GOLD)
                )
                hazards.append(
                    HazardZone(
                        x=self.camera_x + 480,
                        z=LANE_TOP + 30,
                        width=880,
                        depth=52,
                        warning_time=1.1,
                        active_time=0.45,
                        damage=16,
                        owner_team="enemy",
                        hazard_type="train_sign",
                    )
                )

    def _spawn_wave(
        self,
        wave: dict,
        player_count: int,
        enemies: list[EnemyFighter],
        boss_ref: list,
        texts: list[FloatingText],
        audio,
    ):
        sid = self.cfg["id"]
        if "enemies" in wave:
            for e_type, count in wave["enemies"]:
                for i in range(count):
                    side = -1 if i % 2 == 0 else 1
                    spawn_x = self.camera_x + (INTERNAL_WIDTH + 45 + i * 35 if side > 0 else -45 - i * 35)
                    zl, zh = get_stage_z_bounds(sid, spawn_x)
                    spawn_z = random.uniform(zl + 14.0, zh - 14.0)
                    enemies.append(EnemyFighter(e_type, spawn_x, spawn_z))

        if "boss" in wave:
            b_id = wave["boss"]
            spawn_x = self.camera_x + INTERNAL_WIDTH - 140
            zl, zh = get_stage_z_bounds(sid, spawn_x)
            spawn_z = (zl + zh) * 0.5
            boss_ref[0] = BossFighter(b_id, spawn_x, spawn_z, player_count=player_count)
            self.boss_warning_timer = 2.8
            audio.play_sfx("boss_warning")
            texts.append(
                FloatingText(spawn_x - 80, spawn_z, 95, f"BOSS: {boss_ref[0].cfg['name']}!", COLOR_HUNMOON_GOLD)
            )
            for m_type, m_count in wave.get("minions", []):
                for i in range(m_count):
                    mx = self.camera_x + INTERNAL_WIDTH + 30 + i * 35
                    mzl, mzh = get_stage_z_bounds(sid, mx)
                    enemies.append(
                        EnemyFighter(
                            m_type,
                            mx,
                            random.uniform(mzl + 14.0, mzh - 14.0),
                        )
                    )

    def draw_background(self, surface: pygame.Surface):
        """Render high-res illustrated scrolling 2.5D stage backgrounds with animated atmosphere."""
        sid = self.cfg["id"]
        cam = self.camera_x
        t = self.anim_timer

        bg_pair = _get_stage_bg_pair(sid)
        if bg_pair is not None:
            tile_a, tile_b = bg_pair
            # 1:1 world-locked tile scrolling so background walls, counters, and rooftop units match colliders!
            eff_cam = int(cam)
            first_tile_idx = eff_cam // INTERNAL_WIDTH
            offset_x = -(eff_cam % INTERNAL_WIDTH)

            for i in range(2):
                t_idx = first_tile_idx + i
                tile = tile_a if (t_idx % 2 == 0) else tile_b
                surface.blit(tile, (offset_x + i * INTERNAL_WIDTH, 0))

            # Animated atmospheric overlays per stage
            if sid == "train":
                # High-speed rushing wind streaks on bullet train rooftop
                for i in range(7):
                    lx = int(INTERNAL_WIDTH - ((t * 1050 + i * 173) % (INTERNAL_WIDTH + 180)))
                    ly = 75 + i * 24
                    pygame.draw.line(surface, (165, 240, 255), (lx, ly), (lx + 90, ly), 2)
            elif sid == "bathhouse":
                # Rising steam bubbles
                for i in range(8):
                    bx = int((i * 137 - cam * 0.5) % INTERNAL_WIDTH)
                    by = int(LANE_TOP + 20 - ((t * 28 + i * 19) % 120))
                    pygame.draw.circle(surface, (205, 250, 255), (bx, by), 4, 1)
            elif sid == "gwima_lair":
                # Rising embers in Gwi-Ma's inferno arena
                for i in range(12):
                    ex = int((i * 97 + math.sin(t * 3 + i) * 25) % INTERNAL_WIDTH)
                    ey = int(INTERNAL_HEIGHT - ((t * 65 + i * 47) % INTERNAL_HEIGHT))
                    pygame.draw.circle(surface, COLOR_HUNMOON_GOLD if i % 2 == 0 else COLOR_GWIMA_FIRE, (ex, ey), 3)
            return

        # Sky / upper backdrop (y = 0 .. LANE_TOP)
        if sid == "plane":
            # Stage 1: Inside the Luxury Huntr/x Private Jet
            surface.fill((24, 16, 46))
            # Fuselage ceiling & purple neon strips
            pygame.draw.rect(surface, (42, 30, 76), (0, 0, INTERNAL_WIDTH, LANE_TOP))
            pygame.draw.line(surface, COLOR_NEON_PINK, (0, 72), (INTERNAL_WIDTH, 72), 4)
            pygame.draw.line(surface, COLOR_NEON_CYAN, (0, 78), (INTERNAL_WIDTH, 78), 2)

            # Scrolling cabin windows showing night clouds & city lights below
            for wx in range(-int(cam * 0.5) % 140 - 140, INTERNAL_WIDTH + 140, 140):
                win_rect = pygame.Rect(wx, 102, 74, 96)
                pygame.draw.rect(surface, (10, 14, 34), win_rect, border_radius=18)
                # Scrolling cloud streak inside window
                cloud_x = win_rect.x + int((t * 90 + wx) % 50)
                pygame.draw.ellipse(surface, (90, 120, 195), (cloud_x, win_rect.y + 52, 36, 14))
                pygame.draw.rect(surface, COLOR_HUNMOON_GOLD, win_rect, 3, border_radius=18)

                # Luxury VIP Idol Seats along the cabin wall
                seat_rect = pygame.Rect(wx + 12, 206, 52, 56)
                pygame.draw.rect(surface, (125, 40, 145), seat_rect, border_radius=8)
                pygame.draw.rect(surface, COLOR_BLACK, seat_rect, 2, border_radius=8)

            # Cabin Carpet Floor (y = LANE_TOP .. INTERNAL_HEIGHT)
            pygame.draw.rect(surface, (52, 24, 72), (0, LANE_TOP, INTERNAL_WIDTH, INTERNAL_HEIGHT - LANE_TOP))
            # Gold aisle runner stripes
            pygame.draw.line(surface, COLOR_HUNMOON_GOLD, (0, LANE_TOP + 22), (INTERNAL_WIDTH, LANE_TOP + 22), 3)
            pygame.draw.line(surface, COLOR_HUNMOON_GOLD, (0, LANE_BOTTOM - 16), (INTERNAL_WIDTH, LANE_BOTTOM - 16), 3)

        elif sid == "concert":
            # Stage 2: Seoul Neon Dome — Crowd & Main Stage
            surface.fill((18, 12, 38))
            # Sweeping concert laser beams
            for i in range(5):
                lx = 120 + i * 185
                end_x = lx + int(math.sin(t * 2.2 + i) * 180)
                col = COLOR_NEON_PINK if i % 2 == 0 else COLOR_NEON_CYAN
                pygame.draw.line(surface, col, (lx, 0), (end_x, LANE_TOP), 3)

            # Cheering crowd waving golden Huntr/x lightsticks in background
            for cx in range(-int(cam * 0.35) % 36, INTERNAL_WIDTH + 36, 36):
                bob = int(math.sin(t * 8.0 + cx * 0.1) * 5)
                pygame.draw.circle(surface, (28, 22, 48), (cx, LANE_TOP - 28 + bob), 14)
                # Glowing lightstick
                pygame.draw.circle(surface, COLOR_HUNMOON_GOLD, (cx + 10, LANE_TOP - 46 + bob), 4)

            # Main Stage Floor
            pygame.draw.rect(surface, (36, 28, 64), (0, LANE_TOP, INTERNAL_WIDTH, INTERNAL_HEIGHT - LANE_TOP))
            for gx in range(-int(cam) % 120, INTERNAL_WIDTH + 120, 120):
                pygame.draw.line(surface, (65, 52, 110), (gx, LANE_TOP), (gx - 40, INTERNAL_HEIGHT), 2)
            pygame.draw.line(surface, COLOR_NEON_PINK, (0, LANE_TOP + 4), (INTERNAL_WIDTH, LANE_TOP + 4), 4)

        elif sid == "bathhouse":
            # Stage 3: Traditional Korean Bathhouse with Hot Tubs
            surface.fill((20, 42, 54))
            # Wooden shoji/lattice panels & warm lanterns
            for bx in range(-int(cam * 0.45) % 160 - 160, INTERNAL_WIDTH + 160, 160):
                panel = pygame.Rect(bx, 68, 140, LANE_TOP - 72)
                pygame.draw.rect(surface, (78, 52, 38), panel, 4)
                # Bubbling turquoise Hot Tubs along top wall!
                tub = pygame.Rect(bx + 14, LANE_TOP - 54, 112, 52)
                pygame.draw.ellipse(surface, (28, 185, 205), tub)
                pygame.draw.ellipse(surface, (95, 65, 45), tub, 5)
                # Bubbles
                b_off = int((t * 30 + bx) % 70)
                pygame.draw.circle(surface, (195, 250, 255), (bx + 32 + b_off, LANE_TOP - 30), 5, 1)

            # Wet Ceramic Tile Floor
            pygame.draw.rect(surface, (38, 76, 88), (0, LANE_TOP, INTERNAL_WIDTH, INTERNAL_HEIGHT - LANE_TOP))
            for tx in range(-int(cam) % 80, INTERNAL_WIDTH + 80, 80):
                pygame.draw.line(surface, (52, 98, 112), (tx, LANE_TOP), (tx, INTERNAL_HEIGHT), 2)
            for ty in range(LANE_TOP, INTERNAL_HEIGHT, 48):
                pygame.draw.line(surface, (52, 98, 112), (0, ty), (INTERNAL_WIDTH, ty), 2)

        elif sid == "train":
            # Stage 4: Runaway High-Speed KTX Bullet Train Rooftop
            surface.fill((12, 16, 36))
            # High-speed scrolling Seoul skyline silhouette
            for sx in range(-int((cam + t * 420) * 0.35) % 110 - 110, INTERNAL_WIDTH + 110, 110):
                bh = 90 + (abs(sx * 17) % 85)
                pygame.draw.rect(surface, (26, 34, 68), (sx, LANE_TOP - bh, 82, bh))
                pygame.draw.line(surface, COLOR_NEON_CYAN, (sx + 10, LANE_TOP - bh + 12), (sx + 70, LANE_TOP - bh + 12), 2)

            # Rushing wind speed lines
            for i in range(8):
                lx = int((INTERNAL_WIDTH - ((t * 950 + i * 173) % (INTERNAL_WIDTH + 200))))
                ly = 80 + (i * 22)
                pygame.draw.line(surface, (160, 235, 255), (lx, ly), (lx + 95, ly), 2)

            # Metallic Bullet Train Roof Panels
            pygame.draw.rect(surface, (62, 72, 92), (0, LANE_TOP, INTERNAL_WIDTH, INTERNAL_HEIGHT - LANE_TOP))
            pygame.draw.line(surface, COLOR_NEON_CYAN, (0, LANE_TOP + 8), (INTERNAL_WIDTH, LANE_TOP + 8), 4)
            pygame.draw.line(surface, COLOR_NEON_CYAN, (0, LANE_BOTTOM - 8), (INTERNAL_WIDTH, LANE_BOTTOM - 8), 4)
            for rx in range(-int(cam) % 180, INTERNAL_WIDTH + 180, 180):
                pygame.draw.rect(surface, (48, 56, 74), (rx, LANE_TOP + 20, 150, LANE_BOTTOM - LANE_TOP - 40), 2)

        elif sid == "saja_concert":
            # Stage 5: Demonic Saja Boys Stadium ("Your Idol")
            surface.fill((28, 8, 26))
            # Dark crimson & violet hypnotic spotlight pillars
            for px in range(-int(cam * 0.4) % 180 - 180, INTERNAL_WIDTH + 180, 180):
                pygame.draw.rect(surface, (75, 18, 58), (px, 50, 44, LANE_TOP - 50))
                pygame.draw.line(surface, (255, 45, 115), (px + 22, 50), (px + 22, LANE_TOP), 4)
            pygame.draw.rect(surface, (46, 16, 48), (0, LANE_TOP, INTERNAL_WIDTH, INTERNAL_HEIGHT - LANE_TOP))
            pygame.draw.line(surface, (255, 50, 115), (0, LANE_TOP + 4), (INTERNAL_WIDTH, LANE_TOP + 4), 4)

        else:
            # Stage 6: Heart of the Inferno — Throne of Gwi-Ma ("What It Sounds Like")
            surface.fill((36, 10, 18))
            # Living flame pillars in the background
            for fx in range(60, INTERNAL_WIDTH, 150):
                fh = 120 + int(math.sin(t * 7.0 + fx) * 28)
                pts = [(fx - 35, LANE_TOP), (fx, LANE_TOP - fh), (fx + 35, LANE_TOP)]
                pygame.draw.polygon(surface, (215, 55, 20), pts)
                pts_inner = [(fx - 18, LANE_TOP), (fx, LANE_TOP - fh + 30), (fx + 18, LANE_TOP)]
                pygame.draw.polygon(surface, COLOR_HUNMOON_GOLD, pts_inner)

            # Obsidian Arena Floor with Golden-Blue Hunmoon Soul Cracks
            pygame.draw.rect(surface, (34, 20, 38), (0, LANE_TOP, INTERNAL_WIDTH, INTERNAL_HEIGHT - LANE_TOP))
            pygame.draw.line(surface, COLOR_NEON_CYAN, (0, LANE_TOP + 10), (INTERNAL_WIDTH, LANE_TOP + 10), 3)
            pygame.draw.line(surface, COLOR_HUNMOON_GOLD, (0, LANE_BOTTOM - 10), (INTERNAL_WIDTH, LANE_BOTTOM - 10), 3)
