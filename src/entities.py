"""
Gameplay Entities for K-Pop Demon Hunters: Arcade Beat 'Em Up.
Includes:
- HeroPlayer (Rumi, Zoey, Mira, Bobby with 4-hit combos, jump kicks, throws, Hunmoon Specials, and optional AI companion logic)
- EnemyFighter (Faceless Demons with Hive-Mind Merge, Dokkaebi Tricksters & Brutes, Mulguishin Water Demons, Rogue Half-Demons)
- BossFighter (Mystery, Romance, Abby, Baby, Jinu with Soul Empowerment, and Final Boss Gwi-Ma)
- Projectiles, HazardZones, BreakableProps, Pickups, HitSparks, and FloatingText
"""

import math
import random
import pygame
from src.config import (
    BOSSES,
    CHARACTERS,
    COLOR_BLACK,
    COLOR_DEMON_PURPLE,
    COLOR_GWIMA_FIRE,
    COLOR_HP_GREEN,
    COLOR_HP_RED,
    COLOR_HUNMOON_BLUE,
    COLOR_HUNMOON_GOLD,
    COLOR_NEON_CYAN,
    COLOR_NEON_PINK,
    COLOR_WARNING,
    COLOR_WHITE,
    ENEMIES,
    GRAVITY,
    LANE_BOTTOM,
    LANE_TOP,
    PICKUPS,
    get_stage_z_bounds,
)
from src.sprites import (
    draw_boss_sprite,
    draw_enemy_sprite,
    draw_hero_sprite,
    draw_outlined_circle,
    draw_shadow,
)


class FloatingText:
    """Arcade pop-up text for damage numbers, 'COMBO!', 'HEAL!', 'MERGED!', etc."""

    def __init__(self, x: float, z: float, y: float, text: str, color: tuple[int, int, int], size: int = 18):
        self.x = x
        self.z = z
        self.y = y
        self.text = text
        self.color = color
        self.size = size
        self.timer = 0.85
        self.max_timer = 0.85

    def update(self, dt: float) -> bool:
        self.timer -= dt
        self.y += 38.0 * dt
        return self.timer > 0

    def draw(self, surface: pygame.Surface, camera_x: float, font: pygame.font.Font):
        sx = int(self.x - camera_x)
        sy = int(self.z - self.y)
        txt_outline = font.render(self.text, True, COLOR_BLACK)
        txt_fg = font.render(self.text, True, self.color)
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surface.blit(txt_outline, (sx - txt_fg.get_width() // 2 + ox, sy + oy))
        surface.blit(txt_fg, (sx - txt_fg.get_width() // 2, sy))


class HitSpark:
    """Crisp arcade starburst impact effect when punches/weapons connect."""

    def __init__(self, x: float, z: float, y: float, color: tuple[int, int, int], radius: float = 24.0):
        self.x = x
        self.z = z
        self.y = y
        self.color = color
        self.max_radius = radius
        self.timer = 0.18
        self.max_timer = 0.18

    def update(self, dt: float) -> bool:
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface: pygame.Surface, camera_x: float):
        progress = 1.0 - (self.timer / self.max_timer)
        sx = self.x - camera_x
        sy = self.z - self.y
        r = self.max_radius * (0.5 + 0.7 * progress)
        pts = []
        spikes = 8
        for i in range(spikes * 2):
            ang = (i * math.pi) / spikes + progress * 0.8
            rad = r if i % 2 == 0 else r * 0.38
            pts.append((int(sx + math.cos(ang) * rad), int(sy + math.sin(ang) * rad)))
        pygame.draw.polygon(surface, COLOR_WHITE, pts)
        pygame.draw.polygon(surface, self.color, pts, 2)


class Projectile:
    """Projectiles fired by Heroes (Bobby's phones, Zoey's daggers, Mira/Rumi waves) or Bosses."""

    def __init__(
        self,
        x: float,
        z: float,
        y: float,
        vx: float,
        vz: float,
        damage: int,
        owner_team: str,
        proj_type: str,
        color: tuple[int, int, int],
        radius: float = 16.0,
        pierce: bool = False,
        lifetime: float = 1.6,
    ):
        self.x = x
        self.z = z
        self.y = y
        self.vx = vx
        self.vz = vz
        self.damage = damage
        self.owner_team = owner_team  # "hero" or "enemy"
        self.proj_type = proj_type    # "phone", "shinkal", "moon_wave", "light_wave", "charm_heart", "fireball"
        self.color = color
        self.radius = radius
        self.pierce = pierce
        self.lifetime = lifetime
        self.anim_timer = 0.0
        self.hit_ids: set[int] = set()

    def update(self, dt: float) -> bool:
        self.anim_timer += dt
        self.lifetime -= dt
        self.x += self.vx * dt
        self.z = max(LANE_TOP, min(LANE_BOTTOM, self.z + self.vz * dt))
        return self.lifetime > 0

    def draw(self, surface: pygame.Surface, camera_x: float):
        sx = self.x - camera_x
        sy = self.z - self.y
        draw_shadow(surface, sx, self.z, width=self.radius * 1.4, height=8)

        if self.proj_type == "phone":
            # Spinning glowing smartphone with ring waves
            ang = self.anim_timer * 16.0
            dx = math.cos(ang) * 9
            dy = math.sin(ang) * 9
            pts = [
                (sx - dx - dy * 0.5, sy - dy + dx * 0.5),
                (sx + dx - dy * 0.5, sy + dy + dx * 0.5),
                (sx + dx + dy * 0.5, sy + dy - dx * 0.5),
                (sx - dx + dy * 0.5, sy - dy - dx * 0.5),
            ]
            pygame.draw.polygon(surface, COLOR_BLACK, [(int(px), int(py)) for px, py in pts])
            pygame.draw.polygon(surface, COLOR_NEON_CYAN, [(int(px), int(py)) for px, py in pts], 0)
            pygame.draw.circle(surface, COLOR_HUNMOON_GOLD, (int(sx), int(sy)), int(self.radius), 1)
        elif self.proj_type == "charm_heart":
            # Romance's pink hypnotic heart projectile
            r = int(self.radius * 0.65)
            pygame.draw.circle(surface, COLOR_NEON_PINK, (int(sx - r * 0.5), int(sy - r * 0.3)), r)
            pygame.draw.circle(surface, COLOR_NEON_PINK, (int(sx + r * 0.5), int(sy - r * 0.3)), r)
            pygame.draw.polygon(
                surface,
                COLOR_NEON_PINK,
                [(int(sx - r * 1.1), int(sy - r * 0.1)), (int(sx + r * 1.1), int(sy - r * 0.1)), (int(sx), int(sy + r * 1.2))],
            )
        elif self.proj_type in ("moon_wave", "light_wave"):
            # Crescent energy wave
            w = int(self.radius * 1.4)
            h = int(self.radius * 2.2)
            rect = pygame.Rect(int(sx - w // 2), int(sy - h // 2), w, h)
            pygame.draw.ellipse(surface, self.color, rect)
            pygame.draw.ellipse(surface, COLOR_WHITE, rect.inflate(-6, -6), 2)
        else:
            draw_outlined_circle(surface, self.color, (sx, sy), self.radius * 0.65)
            pygame.draw.circle(surface, COLOR_WHITE, (int(sx), int(sy)), int(self.radius * 0.35))


class HazardZone:
    """
    Telegraphed stage or boss hazard (e.g., Gwi-Ma's sweeping flamethrower lane,
    Bobby's VIP spotlight drop, bathhouse steam eruption, or bullet train tunnel sign).
    """

    def __init__(
        self,
        x: float,
        z: float,
        width: float,
        depth: float,
        warning_time: float,
        active_time: float,
        damage: int,
        owner_team: str,
        hazard_type: str,
    ):
        self.x = x
        self.z = z
        self.width = width
        self.depth = depth
        self.warning_time = warning_time
        self.active_time = active_time
        self.damage = damage
        self.owner_team = owner_team  # "hero" (Bobby spotlight) or "enemy" (stage/Gwi-Ma hazard)
        self.hazard_type = hazard_type
        self.timer = 0.0
        self.hit_ids: set[int] = set()

    @property
    def is_active_damage(self) -> bool:
        return self.warning_time <= self.timer <= (self.warning_time + self.active_time)

    def update(self, dt: float) -> bool:
        self.timer += dt
        return self.timer < (self.warning_time + self.active_time)

    def draw(self, surface: pygame.Surface, camera_x: float):
        sx = int(self.x - camera_x - self.width // 2)
        sy = int(self.z - self.depth // 2)
        rect = pygame.Rect(sx, sy, int(self.width), int(self.depth))

        if self.timer < self.warning_time:
            # Flashing telegraph warning zone on floor
            blink = int(self.timer * 14) % 2 == 0
            col = COLOR_HUNMOON_GOLD if self.owner_team == "hero" else (COLOR_WARNING if blink else (255, 160, 40))
            warn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(warn_surf, (*col, 75), (0, 0, rect.width, rect.height), border_radius=8)
            pygame.draw.rect(warn_surf, (*col, 210), (0, 0, rect.width, rect.height), 2, border_radius=8)
            surface.blit(warn_surf, rect.topleft)
        else:
            # Active eruption (Flame wave, Spotlight beam, Steam geyser, or Train warning)
            act_surf = pygame.Surface((rect.width, rect.height + 120), pygame.SRCALPHA)
            if self.hazard_type == "gwima_flame":
                pygame.draw.rect(act_surf, (255, 75, 20, 185), (0, 80, rect.width, rect.height), border_radius=10)
                pygame.draw.rect(act_surf, (255, 220, 65, 220), (8, 86, max(4, rect.width - 16), max(4, rect.height - 12)), border_radius=8)
            elif self.hazard_type == "spotlight":
                # Vertical concert spotlight beam crashing down
                pygame.draw.polygon(
                    act_surf,
                    (255, 240, 120, 165),
                    [(rect.width // 2 - 12, 0), (rect.width // 2 + 12, 0), (rect.width, 120), (0, 120)],
                )
                pygame.draw.ellipse(act_surf, (255, 255, 200, 220), (0, 100, rect.width, rect.height))
            elif self.hazard_type == "steam":
                pygame.draw.ellipse(act_surf, (190, 245, 255, 180), (0, 30, rect.width, rect.height + 70))
            else:
                pygame.draw.rect(act_surf, (255, 65, 95, 190), (0, 80, rect.width, rect.height), border_radius=6)
            surface.blit(act_surf, (sx, sy - 100))


class PickupItem:
    """Korean Street Food & Concert Pickups (Boba, Tteokbokki, Corn Dog, Lightstick, K-BBQ)."""

    def __init__(self, x: float, z: float, pickup_type: str):
        self.x = x
        self.z = z
        self.pickup_type = pickup_type
        self.cfg = PICKUPS[pickup_type]
        self.anim_timer = random.uniform(0.0, 3.0)
        self.collected = False

    def update(self, dt: float):
        self.anim_timer += dt

    def draw(self, surface: pygame.Surface, camera_x: float, font: pygame.font.Font):
        sx = self.x - camera_x
        bob = math.sin(self.anim_timer * 5.0) * 4.0
        sy = self.z - 14 - bob
        draw_shadow(surface, sx, self.z, width=28, height=10)

        col = self.cfg["color"]
        if self.pickup_type == "boba":
            # Boba cup + purple straw + tapioca pearls
            rect = pygame.Rect(int(sx - 8), int(sy - 10), 16, 20)
            pygame.draw.rect(surface, COLOR_BLACK, rect.inflate(4, 4), border_radius=4)
            pygame.draw.rect(surface, col, rect, border_radius=3)
            pygame.draw.line(surface, (165, 85, 235), (int(sx + 2), int(sy - 18)), (int(sx), int(sy - 6)), 3)
            for px_off in (-4, 0, 4):
                pygame.draw.circle(surface, (45, 25, 15), (int(sx + px_off), int(sy + 6)), 2)
        elif self.pickup_type == "lightstick":
            # Glowing Golden Huntr/x Lightstick
            pygame.draw.line(surface, COLOR_BLACK, (int(sx), int(sy + 12)), (int(sx), int(sy - 4)), 6)
            pygame.draw.line(surface, COLOR_WHITE, (int(sx), int(sy + 12)), (int(sx), int(sy - 4)), 3)
            draw_outlined_circle(surface, COLOR_HUNMOON_GOLD, (sx, sy - 8), 9)
        else:
            # Plate / snack bowl
            pygame.draw.ellipse(surface, COLOR_WHITE, pygame.Rect(int(sx - 14), int(sy - 4), 28, 14))
            pygame.draw.ellipse(surface, COLOR_BLACK, pygame.Rect(int(sx - 14), int(sy - 4), 28, 14), 2)
            draw_outlined_circle(surface, col, (sx, sy - 2), 8)


class BreakableProp:
    """
    Solid 2.5D Stage Obstacle & Interactive Level/Background Object.
    Stops grounded characters and enemies from walking through it (and allows jumping on top of crates/counters/AC boxes).
    Supports both destructible floor props (crates, rolling beverage carts, speaker stacks, bath barrels, soul pillars,
    lava braziers, soul crystals) and permanent background structures (marble bar counters, VIP sofas, steaming hot tubs,
    concert pyro pods, rooftop AC/relay boxes) with stage-themed interactive reactions when struck!
    """

    PROP_SPECS = {
        "crate": {"half_w": 22.0, "half_d": 7.5, "height": 38.0, "hp": 36, "indestructible": False, "bg_fixture": False},
        "bev_cart": {"half_w": 24.0, "half_d": 7.5, "height": 38.0, "hp": 36, "indestructible": False, "bg_fixture": False},
        "bar_counter": {"half_w": 104.0, "half_d": 12.0, "height": 78.0, "hp": 999, "indestructible": True, "charges": 2, "bg_fixture": True},
        "vip_sofa": {"half_w": 110.0, "half_d": 12.0, "height": 48.0, "hp": 999, "indestructible": True, "charges": 2, "bg_fixture": True},
        "side_counter": {"half_w": 33.0, "half_d": 12.0, "height": 78.0, "hp": 999, "indestructible": True, "charges": 1, "bg_fixture": True},
        "speaker": {"half_w": 24.0, "half_d": 8.0, "height": 52.0, "hp": 45, "indestructible": False, "bg_fixture": False},
        "pyro_pod": {"half_w": 20.0, "half_d": 6.5, "height": 22.0, "hp": 999, "indestructible": True, "charges": 99, "bg_fixture": False},
        "hottub": {"half_w": 48.0, "half_d": 12.0, "height": 30.0, "hp": 999, "indestructible": True, "charges": 99, "bg_fixture": False},
        "bath_barrel": {"half_w": 20.0, "half_d": 7.5, "height": 38.0, "hp": 34, "indestructible": False, "bg_fixture": False},
        "train_ac": {"half_w": 66.0, "half_d": 12.0, "height": 58.0, "hp": 999, "indestructible": True, "charges": 99, "bg_fixture": True},
        "train_relay": {"half_w": 52.0, "half_d": 10.0, "height": 44.0, "hp": 999, "indestructible": True, "charges": 99, "bg_fixture": True},
        "soul_pillar": {"half_w": 21.0, "half_d": 8.0, "height": 56.0, "hp": 45, "indestructible": False, "bg_fixture": False},
        "lava_brazier": {"half_w": 21.0, "half_d": 8.0, "height": 44.0, "hp": 48, "indestructible": False, "bg_fixture": False},
        "soul_crystal": {"half_w": 21.0, "half_d": 8.0, "height": 46.0, "hp": 36, "indestructible": False, "bg_fixture": False},
    }

    def __init__(self, x: float, z: float, prop_type: str, drop_type: str | None = None):
        self.x = x
        self.z = z
        self.prop_type = prop_type
        self.drop_type = drop_type
        spec = self.PROP_SPECS.get(prop_type, self.PROP_SPECS["crate"])
        self.half_w: float = spec["half_w"]
        self.half_d: float = spec["half_d"]
        self.height: float = spec["height"]
        self.hp: int = spec["hp"]
        self.indestructible: bool = spec["indestructible"]
        self.bg_fixture: bool = spec.get("bg_fixture", False)
        self.charges: int = spec.get("charges", 1)

        self.hurt_timer = 0.0
        self.interact_cooldown = 0.0
        self.aura_timer = random.uniform(0.0, 2.0)
        self.anim_timer = random.uniform(0.0, 4.0)
        self.vx = 0.0  # Used when a rolling beverage cart is launched across the cabin!
        self.cart_hit_ids: set[int] = set()

    def take_damage(self, amount: int) -> bool:
        self.hurt_timer = 0.14
        if self.indestructible:
            return False
        self.hp -= amount
        return self.hp <= 0

    def trigger_interaction(
        self,
        hit_dir: int,
        enemies: list,
        boss,
        players: list,
        hazards: list[HazardZone],
        pickups: list[PickupItem],
        sparks: list[HitSpark],
        texts: list[FloatingText],
        audio,
    ) -> bool:
        """
        Execute stage-themed interactive behavior when struck by a player attack or enemy slam.
        Returns True if this destructible prop was destroyed and should be removed.
        """
        if self.interact_cooldown > 0:
            return False
        self.interact_cooldown = 0.35
        self.hurt_timer = 0.16

        targets = [e for e in enemies if e.hp > 0]
        if boss is not None and boss.hp > 0:
            targets.append(boss)

        if self.prop_type == "bev_cart":
            # Launch the VIP Beverage Cart rolling down the cabin aisle to bowl over enemies!
            if abs(self.vx) < 20.0:
                self.vx = (1 if hit_dir >= 0 else -1) * 410.0
                self.cart_hit_ids.clear()
                audio.play_sfx("hit")
                sparks.append(HitSpark(self.x, self.z, 26, COLOR_NEON_CYAN, radius=24))
                texts.append(FloatingText(self.x, self.z, 54, "RUNAWAY VIP CART!", COLOR_HUNMOON_GOLD))
                self.hp -= 18
                return False

        elif self.prop_type in ("bar_counter", "side_counter"):
            # Shatter crystal bottles & glowing ice bucket on top of the background marble counter!
            if self.charges > 0:
                self.charges -= 1
                audio.play_sfx("hit")
                sparks.append(HitSpark(self.x, self.z, 46, COLOR_NEON_CYAN, radius=32))
                texts.append(FloatingText(self.x, self.z, 68, "BARWARE SHATTER! ICE SPLASH!", COLOR_NEON_CYAN))
                for t in targets:
                    if abs(t.x - self.x) <= self.half_w + 55 and abs(t.z - self.z) <= self.half_d + 48:
                        t.take_damage(22, (32.0 if t.x >= self.x else -32.0), is_heavy=True)
                        sparks.append(HitSpark(t.x, t.z, 34, COLOR_NEON_CYAN))
                if self.drop_type:
                    pickups.append(PickupItem(self.x, self.z + self.half_d + 16, self.drop_type))
                    self.drop_type = None
            return False

        elif self.prop_type == "vip_sofa":
            sparks.append(HitSpark(self.x, self.z, 30, COLOR_DEMON_PURPLE, radius=20))
            return False

        elif self.prop_type == "speaker":
            # Concert Speaker Stack pulses a Sonic Bass Shockwave every time it's struck!
            audio.play_sfx("slash_heavy")
            sparks.append(HitSpark(self.x, self.z, 36, COLOR_NEON_PINK, radius=34))
            texts.append(FloatingText(self.x, self.z, 64, "SONIC BASS SHOCKWAVE!", COLOR_NEON_PINK))
            for t in targets:
                if abs(t.x - self.x) <= 135 and abs(t.z - self.z) <= 52:
                    t.take_damage(18, (38.0 if t.x >= self.x else -38.0), is_heavy=True)
                    sparks.append(HitSpark(t.x, t.z, 32, COLOR_NEON_CYAN))

        elif self.prop_type == "pyro_pod":
            # Concert Pyro Pod erupts in a vertical flame/spotlight pillar!
            self.interact_cooldown = 1.6
            audio.play_sfx("special_hunmoon")
            texts.append(FloatingText(self.x, self.z, 68, "STAGE PYRO ERUPTION!", COLOR_HUNMOON_GOLD))
            hazards.append(
                HazardZone(
                    x=self.x,
                    z=self.z + 10,
                    width=110,
                    depth=58,
                    warning_time=0.05,
                    active_time=0.50,
                    damage=32,
                    owner_team="hero",
                    hazard_type="gwima_flame",
                )
            )
            return False

        elif self.prop_type == "hottub":
            # Bathhouse Steaming Hot Tub erupts a scalding water/steam splash that damages nearby demons!
            self.interact_cooldown = 1.4
            audio.play_sfx("hit")
            sparks.append(HitSpark(self.x, self.z, 32, COLOR_NEON_CYAN, radius=34))
            texts.append(FloatingText(self.x, self.z, 66, "HOT TUB GEYSER SPLASH!", COLOR_NEON_CYAN))
            hazards.append(
                HazardZone(
                    x=self.x,
                    z=self.z,
                    width=135,
                    depth=68,
                    warning_time=0.05,
                    active_time=0.45,
                    damage=26,
                    owner_team="hero",
                    hazard_type="steam",
                )
            )
            return False

        elif self.prop_type in ("train_ac", "train_relay"):
            # High-Voltage Bullet Train AC / Relay Box discharges an electric shock arc!
            self.interact_cooldown = 1.5
            audio.play_sfx("hit")
            sparks.append(HitSpark(self.x, self.z, 38, COLOR_NEON_CYAN, radius=34))
            texts.append(FloatingText(self.x, self.z, 66, "HIGH-VOLTAGE ARC!", COLOR_NEON_CYAN))
            for t in targets:
                if abs(t.x - self.x) <= self.half_w + 75 and abs(t.z - self.z) <= self.half_d + 48:
                    t.take_damage(26, (36.0 if t.x >= self.x else -36.0), is_heavy=True)
                    sparks.append(HitSpark(t.x, t.z, 34, COLOR_HUNMOON_GOLD))
            return False

        elif self.prop_type == "soul_pillar":
            # Demonic Soul Obelisk pulses dark energy on hit and bursts with Purified Soul Meter when broken!
            sparks.append(HitSpark(self.x, self.z, 40, COLOR_NEON_PINK, radius=28))

        elif self.prop_type == "lava_brazier":
            # Molten Obsidian Brazier splashes liquid fire on nearby enemies when hit!
            sparks.append(HitSpark(self.x, self.z, 38, COLOR_GWIMA_FIRE, radius=30))
            texts.append(FloatingText(self.x, self.z, 64, "MOLTEN SPLASH!", COLOR_GWIMA_FIRE))
            for t in targets:
                if abs(t.x - self.x) <= 125 and abs(t.z - self.z) <= 48:
                    t.take_damage(22, (32.0 if t.x >= self.x else -32.0), is_heavy=True)

        destroyed = self.take_damage(18)
        if destroyed:
            audio.play_sfx("hit")
            sparks.append(HitSpark(self.x, self.z, 28, COLOR_HUNMOON_GOLD, radius=32))
            if self.prop_type == "soul_pillar":
                texts.append(FloatingText(self.x, self.z, 72, "SOUL PILLAR SHATTERED! +20 METER!", COLOR_NEON_CYAN))
                for p in players:
                    if p.active and p.state != "ko":
                        p.add_meter(20.0)
                for t in targets:
                    if abs(t.x - self.x) <= 145 and abs(t.z - self.z) <= 55:
                        t.take_damage(30, (42.0 if t.x >= self.x else -42.0), is_heavy=True)
            elif self.prop_type == "soul_crystal":
                texts.append(FloatingText(self.x, self.z, 72, "HUNMOON CRYSTAL NOVA! +20 HP / +30 METER!", COLOR_HUNMOON_GOLD))
                for p in players:
                    if p.active and p.state != "ko":
                        p.heal(20)
                        p.add_meter(30.0)
                for t in targets:
                    if abs(t.x - self.x) <= 155 and abs(t.z - self.z) <= 60:
                        t.take_damage(32, (42.0 if t.x >= self.x else -42.0), is_heavy=True)
            if self.drop_type:
                pickups.append(PickupItem(self.x, self.z, self.drop_type))
            return True
        return False

    def update(
        self,
        dt: float,
        stage_width: float = 2600.0,
        enemies: list | None = None,
        boss=None,
        players: list | None = None,
        pickups: list[PickupItem] | None = None,
        sparks: list[HitSpark] | None = None,
        texts: list[FloatingText] | None = None,
        audio=None,
    ) -> bool:
        """Update timers, hot-tub soothing steam aura, and rolling beverage cart physics. Returns False if destroyed."""
        self.anim_timer += dt
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
        if self.interact_cooldown > 0:
            self.interact_cooldown -= dt

        # Stage 3 Hot Tub Soothing Steam Aura: gently warms nearby players for +3 HP every 2.4s
        if self.prop_type == "hottub" and players:
            self.aura_timer += dt
            if self.aura_timer >= 2.4:
                self.aura_timer = 0.0
                for p in players:
                    if p.active and p.state != "ko" and p.hp < p.max_hp:
                        if abs(p.x - self.x) <= self.half_w + 48 and abs(p.z - self.z) <= self.half_d + 36:
                            p.heal(3)
                            if texts is not None:
                                texts.append(FloatingText(p.x, p.z, 54, "+3 WARM STEAM", COLOR_NEON_CYAN))

        # Stage 1 Rolling VIP Beverage Cart bowling through enemies!
        if abs(self.vx) > 5.0:
            self.x += self.vx * dt
            self.vx *= max(0.0, 1.0 - dt * 1.4)
            targets = list(enemies or [])
            if boss is not None and boss.hp > 0:
                targets.append(boss)
            for t in targets:
                if t.hp > 0 and id(t) not in self.cart_hit_ids:
                    if abs(t.x - self.x) <= self.half_w + 26 and abs(t.z - self.z) <= self.half_d + 22:
                        self.cart_hit_ids.add(id(t))
                        kb = 45.0 if self.vx >= 0 else -45.0
                        t.take_damage(28, kb, is_heavy=True)
                        if sparks is not None:
                            sparks.append(HitSpark(t.x, t.z, 30, COLOR_HUNMOON_GOLD, radius=28))
                        if texts is not None:
                            texts.append(FloatingText(t.x, t.z, 58, "BOWLED OVER! 28!", COLOR_HUNMOON_GOLD))
                        if audio is not None:
                            audio.play_sfx("hit")
            if abs(self.vx) < 35.0 or self.x < 40 or self.x > stage_width - 40:
                self.vx = 0.0
                if self.hp <= 18:
                    if self.drop_type and pickups is not None:
                        pickups.append(PickupItem(self.x, self.z, self.drop_type))
                    if sparks is not None:
                        sparks.append(HitSpark(self.x, self.z, 26, COLOR_HUNMOON_GOLD))
                    return False

        return True

    def draw(self, surface: pygame.Surface, camera_x: float):
        sx = int(self.x - camera_x)
        sy = int(self.z)
        if sx < -160 or sx > 1120:
            return

        flash = self.hurt_timer > 0

        # Background-painted structures already have high-res artwork in the stage background!
        if self.prop_type in ("bar_counter", "side_counter", "vip_sofa"):
            return

        if self.prop_type in ("train_ac", "train_relay"):
            # Subtle high-voltage electric arc flash on the rooftop AC/Relay boxes
            if int(self.anim_timer * 8) % 4 == 0 or flash:
                top_y = sy - int(self.height) + 8
                pygame.draw.line(surface, COLOR_HUNMOON_GOLD, (sx - 14, top_y), (sx, top_y - 5), 2)
                pygame.draw.line(surface, COLOR_NEON_CYAN, (sx, top_y - 5), (sx + 14, top_y), 2)
            return

        draw_shadow(surface, sx, sy - int(self.half_d * 0.5), width=int(self.half_w * 2.1), height=int(self.half_d * 1.6))

        if self.prop_type == "hottub":
            # Carved Granite Bathhouse Hot Tub with Bubbling Turquoise Water & Steam
            w, d, h = int(self.half_w * 2), int(self.half_d * 2), int(self.height)
            base_rect = pygame.Rect(sx - w // 2, sy - h, w, h)
            rim_rect = pygame.Rect(sx - w // 2 - 4, sy - h - d // 2, w + 8, d)
            water_rect = rim_rect.inflate(-14, -8)
            stone_col = COLOR_WHITE if flash else (68, 84, 96)
            pygame.draw.rect(surface, (42, 54, 64), base_rect, border_radius=8)
            pygame.draw.rect(surface, COLOR_BLACK, base_rect, 2, border_radius=8)
            pygame.draw.ellipse(surface, stone_col, rim_rect)
            pygame.draw.ellipse(surface, COLOR_BLACK, rim_rect, 2)
            pygame.draw.ellipse(surface, (32, 205, 220), water_rect)
            pygame.draw.ellipse(surface, (165, 250, 255), water_rect, 2)
            # Animated steam bubbles
            for i in range(3):
                bx = sx - 26 + i * 26 + int(math.sin(self.anim_timer * 3.5 + i) * 6)
                by = water_rect.centery - int((self.anim_timer * 18 + i * 9) % 18)
                pygame.draw.circle(surface, (215, 252, 255), (bx, by), 4, 1)
            return

        if self.prop_type == "pyro_pod":
            # Concert Stage Pyrotechnic Emitter Pod
            w, h = int(self.half_w * 2), int(self.height)
            rect = pygame.Rect(sx - w // 2, sy - h, w, h)
            pygame.draw.rect(surface, COLOR_WHITE if flash else (44, 38, 68), rect, border_radius=5)
            pygame.draw.rect(surface, COLOR_HUNMOON_GOLD, rect, 2, border_radius=5)
            # Glowing flame nozzle
            nozzle_col = COLOR_GWIMA_FIRE if int(self.anim_timer * 6) % 2 == 0 else COLOR_HUNMOON_GOLD
            pygame.draw.ellipse(surface, nozzle_col, (sx - 12, sy - h - 5, 24, 10))
            return

        if self.prop_type == "bev_cart":
            # VIP Stainless-Steel & Gold Airline Beverage Service Cart
            w, h = int(self.half_w * 2), int(self.height)
            rect = pygame.Rect(sx - w // 2, sy - h, w, h - 6)
            pygame.draw.rect(surface, COLOR_WHITE if flash else (65, 58, 96), rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_HUNMOON_GOLD, rect, 2, border_radius=4)
            # Push handle & wheels
            pygame.draw.line(surface, COLOR_HUNMOON_GOLD, (rect.left - 5, rect.top + 4), (rect.left, rect.top + 4), 3)
            pygame.draw.circle(surface, COLOR_BLACK, (rect.left + 8, sy - 3), 5)
            pygame.draw.circle(surface, COLOR_BLACK, (rect.right - 8, sy - 3), 5)
            # Boba cups on top tray
            pygame.draw.rect(surface, (210, 155, 105), (sx - 12, rect.top - 10, 8, 10), border_radius=2)
            pygame.draw.rect(surface, COLOR_NEON_PINK, (sx + 4, rect.top - 10, 8, 10), border_radius=2)
            return

        if self.prop_type == "bath_barrel":
            # Traditional Hinoki Cedar Bath Barrel with Brass Hoops
            w, h = int(self.half_w * 2), int(self.height)
            rect = pygame.Rect(sx - w // 2, sy - h, w, h)
            pygame.draw.rect(surface, COLOR_WHITE if flash else (145, 92, 52), rect, border_radius=7)
            pygame.draw.rect(surface, COLOR_BLACK, rect, 2, border_radius=7)
            pygame.draw.line(surface, COLOR_HUNMOON_GOLD, (rect.left + 2, rect.top + 10), (rect.right - 2, rect.top + 10), 3)
            pygame.draw.line(surface, COLOR_HUNMOON_GOLD, (rect.left + 2, rect.bottom - 10), (rect.right - 2, rect.bottom - 10), 3)
            pygame.draw.ellipse(surface, (38, 195, 210), (rect.left + 4, rect.top - 5, w - 8, 10))
            return

        if self.prop_type in ("soul_pillar", "soul_crystal", "lava_brazier"):
            w, h = int(self.half_w * 2), int(self.height)
            if self.prop_type == "lava_brazier":
                rect = pygame.Rect(sx - w // 2, sy - h + 12, w, h - 12)
                pygame.draw.rect(surface, COLOR_WHITE if flash else (45, 26, 32), rect, border_radius=6)
                pygame.draw.rect(surface, COLOR_HUNMOON_GOLD, rect, 2, border_radius=6)
                flame_h = 16 + int(math.sin(self.anim_timer * 9.0) * 5)
                pts = [(sx - 16, rect.top), (sx, rect.top - flame_h), (sx + 16, rect.top)]
                pygame.draw.polygon(surface, COLOR_GWIMA_FIRE, pts)
                pygame.draw.polygon(surface, COLOR_HUNMOON_GOLD, [(sx - 8, rect.top), (sx, rect.top - flame_h + 6), (sx + 8, rect.top)])
            else:
                col = COLOR_HUNMOON_GOLD if self.prop_type == "soul_crystal" else COLOR_DEMON_PURPLE
                edge_col = COLOR_NEON_CYAN if self.prop_type == "soul_crystal" else COLOR_NEON_PINK
                pts = [(sx - w // 2, sy), (sx - w // 3, sy - h + 10), (sx, sy - h - 6), (sx + w // 3, sy - h + 10), (sx + w // 2, sy)]
                pygame.draw.polygon(surface, COLOR_WHITE if flash else col, pts)
                pygame.draw.polygon(surface, edge_col, pts, 2)
            return

        # Default 2.5D isometric-style K-Pop Tour Road Case / Concert Speaker Stack
        body_col = (255, 255, 255) if flash else (36, 32, 58)
        trim_col = COLOR_NEON_CYAN if self.prop_type == "speaker" else COLOR_HUNMOON_GOLD
        accent_col = COLOR_NEON_PINK if self.prop_type == "speaker" else COLOR_NEON_CYAN

        w, h = int(self.half_w * 2), int(self.height)
        rect = pygame.Rect(sx - w // 2, sy - h, w, h)
        top_lid = [
            (sx - w // 2, sy - h),
            (sx - w // 2 + 8, sy - h - 10),
            (sx + w // 2 + 8, sy - h - 10),
            (sx + w // 2, sy - h),
        ]
        side_panel = [
            (sx + w // 2, sy - h),
            (sx + w // 2 + 8, sy - h - 10),
            (sx + w // 2 + 8, sy - 10),
            (sx + w // 2, sy),
        ]
        pygame.draw.polygon(surface, (58, 52, 88) if not flash else COLOR_WHITE, top_lid)
        pygame.draw.polygon(surface, COLOR_BLACK, top_lid, 2)
        pygame.draw.polygon(surface, (24, 20, 40) if not flash else COLOR_WHITE, side_panel)
        pygame.draw.polygon(surface, COLOR_BLACK, side_panel, 2)

        pygame.draw.rect(surface, COLOR_BLACK, rect.inflate(4, 4), border_radius=4)
        pygame.draw.rect(surface, body_col, rect, border_radius=3)
        pygame.draw.rect(surface, trim_col, rect, 2, border_radius=3)

        if self.prop_type == "speaker":
            # Dual subwoofer speaker cones pulsing to the beat
            pulse = int(abs(math.sin(self.anim_timer * 8.0)) * 2)
            pygame.draw.circle(surface, COLOR_BLACK, (sx, sy - h // 3), 9 + pulse)
            pygame.draw.circle(surface, accent_col, (sx, sy - h // 3), 9 + pulse, 2)
            pygame.draw.circle(surface, COLOR_BLACK, (sx, sy - (h * 2) // 3), 8 + pulse)
            pygame.draw.circle(surface, trim_col, (sx, sy - (h * 2) // 3), 8 + pulse, 2)
        else:
            # Corner metal brackets & glowing Huntr/x diamond emblem
            pygame.draw.line(surface, trim_col, (rect.left + 4, rect.centery), (rect.right - 4, rect.centery), 2)
            diamond = [
                (sx, sy - h // 2 - 8),
                (sx + 8, sy - h // 2),
                (sx, sy - h // 2 + 8),
                (sx - 8, sy - h // 2),
            ]
            pygame.draw.polygon(surface, accent_col, diamond)
            pygame.draw.polygon(surface, COLOR_BLACK, diamond, 1)


def compute_prop_ground_height(
    x: float, z: float, current_y: float, props: list[BreakableProp]
) -> tuple[float, BreakableProp | None]:
    """
    Return `(ground_y, support_prop)` if an entity at `(x, z)` is high enough to stand/land on top of
    a solid stage prop (marble bar counters, VIP sofas, road cases, beverage carts, speaker stacks,
    hot tub rims, rooftop AC units).
    """
    ground_y = 0.0
    support_prop: BreakableProp | None = None
    for prop in props:
        if prop.bg_fixture:
            # Background fixtures (bar_counter, vip_sofa, side_counter, train_ac, train_relay) have their
            # front base at `prop.z` and their visual top surface at `prop.z - prop.height`.
            if abs(x - prop.x) <= prop.half_w - 6.0 and (prop.z - 12.0 <= z <= prop.z + 12.0):
                if current_y >= prop.height - 12.0 and prop.height > ground_y:
                    ground_y = prop.height
                    support_prop = prop
        else:
            # 2.5D floor props have their floor footprint centered at `prop_cz = prop.z - prop.half_d`
            prop_cz = prop.z - prop.half_d
            if abs(x - prop.x) <= prop.half_w - 2.0 and abs(z - prop_cz) <= prop.half_d + 7.5:
                if current_y >= prop.height - 12.0 and prop.height > ground_y:
                    ground_y = prop.height
                    support_prop = prop
    return ground_y, support_prop


def resolve_stage_and_prop_collisions(
    entity,
    stage_id: str,
    props: list[BreakableProp],
    ent_half_w: float = 13.0,
    ent_half_d: float = 4.5,
    is_enemy: bool = False,
    enemies: list | None = None,
    boss=None,
    players: list | None = None,
    hazards: list[HazardZone] | None = None,
    pickups: list[PickupItem] | None = None,
    sparks: list[HitSpark] | None = None,
    texts: list[FloatingText] | None = None,
    audio=None,
    prev_x: float | None = None,
):
    """
    Enforce pixel-accurate 2.5D stage wall/ledge bounds and solid obstacle foot-base collisions:
    - Stops horizontal X movement when walking sideways into a wall/counter step (e.g., bar counter or AC unit side).
    - Stops depth Z movement at the exact floor base line of walls, counters, stage ledges, and train rails.
    - Uses each floor prop's actual 2.5D base footprint (`z` in `[prop.z - 2*half_d, prop.z]`) so characters'
      shoes stop right at the visual edge of crates, carts, speaker stacks, hot tubs, and barrels with zero gap!
    """
    ent_y = getattr(entity, "y", 0.0)
    hit_wall = False
    if prev_x is not None and abs(entity.x - prev_x) > 0.01 and ent_y < 60.0:
        z_min_prev, z_max_prev = get_stage_z_bounds(stage_id, prev_x)
        z_min_cur, z_max_cur = get_stage_z_bounds(stage_id, entity.x)
        # If walking sideways into a vertical step in the wall/counter contour, block X movement!
        if z_min_cur > z_min_prev + 4.0 and entity.z < z_min_cur:
            entity.x = prev_x
            hit_wall = True
        elif z_max_cur < z_max_prev - 4.0 and entity.z > z_max_cur:
            entity.x = prev_x
            hit_wall = True

    z_min, z_max = get_stage_z_bounds(stage_id, entity.x)
    if entity.z < z_min:
        entity.z = z_min
        hit_wall = True
    elif entity.z > z_max:
        entity.z = z_max
        hit_wall = True

    is_hurt_enemy = is_enemy and getattr(entity, "hurt_timer", 0.0) > 0

    if hit_wall and is_hurt_enemy and not getattr(entity, "slammed_this_hit", False):
        entity.slammed_this_hit = True
        entity.hp = max(0, entity.hp - 10)
        if sparks is not None:
            sparks.append(HitSpark(entity.x, entity.z, 32, COLOR_HUNMOON_GOLD, radius=26))
        if texts is not None:
            texts.append(FloatingText(entity.x, entity.z, 62, "WALL SLAM! +10", COLOR_HUNMOON_GOLD))

    # Solid 2.5D Floor Object Collision (aligned to the prop's actual floor base [prop.z - 2*half_d, prop.z])
    for prop in list(props):
        if prop.bg_fixture:
            # Background fixtures (bar counters, sofas, train AC) use the exact stage wall contour above
            continue
        if ent_y >= prop.height - 4.0:
            # High mid-air jump / escape vault passes cleanly over floor props
            continue

        # Visual 2.5D props are drawn upward from `sy = prop.z`, so their floor footprint center is `prop.z - prop.half_d`
        prop_cz = prop.z - prop.half_d
        dx = entity.x - prop.x
        dz = entity.z - prop_cz
        req_x = prop.half_w + ent_half_w
        req_z = prop.half_d + ent_half_d

        if abs(dx) < req_x and abs(dz) < req_z:
            overlap_x = req_x - abs(dx)
            overlap_z = req_z - abs(dz)

            push_z_dir = 1.0 if dz >= 0 else -1.0
            cand_z = prop_cz + push_z_dir * req_z
            z_low, z_high = get_stage_z_bounds(stage_id, entity.x)
            z_valid = (z_low <= cand_z <= z_high)

            if overlap_z <= overlap_x and z_valid:
                entity.z = cand_z
            else:
                push_x_dir = 1.0 if dx >= 0 else -1.0
                entity.x = prop.x + push_x_dir * req_x

            # If a knocked-back enemy slams into a solid object, deal bonus crash damage & trigger interaction!
            if is_hurt_enemy and not getattr(entity, "slammed_this_hit", False):
                entity.slammed_this_hit = True
                entity.hp = max(0, entity.hp - 10)
                if sparks is not None:
                    sparks.append(HitSpark(entity.x, entity.z, 32, COLOR_NEON_CYAN, radius=28))
                if texts is not None:
                    texts.append(FloatingText(entity.x, entity.z, 64, "OBJECT CRASH! +10", COLOR_NEON_CYAN))
                if enemies is not None and hazards is not None and pickups is not None and sparks is not None and texts is not None and audio is not None:
                    destroyed = prop.trigger_interaction(
                        hit_dir=(-1 if dx >= 0 else 1),
                        enemies=enemies,
                        boss=boss,
                        players=players or [],
                        hazards=hazards,
                        pickups=pickups,
                        sparks=sparks,
                        texts=texts,
                        audio=audio,
                    )
                    if destroyed and prop in props:
                        props.remove(prop)

    # Final safety clamp to walkable floor contour at resolved X
    z_min_f, z_max_f = get_stage_z_bounds(stage_id, entity.x)
    entity.z = max(z_min_f, min(z_max_f, entity.z))


class HeroPlayer:
    """Playable Character (Rumi, Zoey, Mira, or Bobby) supporting 4-player arcade input or AI companion."""

    def __init__(self, player_index: int, char_id: str, x: float, z: float, active: bool = False, is_ai: bool = False):
        self.player_index = player_index
        self.char_id = char_id
        self.cfg = CHARACTERS[char_id]
        self.active = active
        self.is_ai = is_ai

        self.x = x
        self.z = z
        self.y = 0.0
        self.ground_y = 0.0
        self.vy = 0.0
        self.facing = 1

        self.max_hp = self.cfg["max_hp"]
        self.hp = self.max_hp
        self.lives = 3
        self.score = 0
        self.hunmoon_meter = 100.0  # Starts full so players can immediately try their signature special!
        self.max_meter = 100.0

        self.state = "idle"  # idle, walk, run, jump, attack, hurt, ko
        self.anim_timer = 0.0
        self.is_running = False
        self.jumps_used = 0
        self.is_double_jumping = False
        self.air_vx = 0.0
        self.flip_angle = 0.0

        # Combat timers
        self.combo_step = 0
        self.combo_window = 0.0
        self.attack_timer = 0.0
        self.attack_duration = 0.32
        self.attack_has_hit = False
        self.special_timer = 0.0
        self.hurt_timer = 0.0
        self.invuln_timer = 1.5
        self.charm_timer = 0.0      # Romance's reversed-controls debuff
        self.grabbed_timer = 0.0    # Mulguishin water grab
        self.continue_timer = 10.0  # 10-second arcade continue countdown when KO'd
        self.soul_empowered = False # Activated in Stage 5/6 after Jinu transfers his soul!

    def spawn_or_continue(self, char_id: str, x: float, z: float, is_ai: bool = False):
        self.char_id = char_id
        self.cfg = CHARACTERS[char_id]
        self.max_hp = self.cfg["max_hp"]
        self.hp = self.max_hp
        self.lives = 3
        self.hunmoon_meter = 100.0
        self.x = x
        self.z = z
        self.y = 140.0  # Drop in dramatically from top of screen!
        self.vy = 0.0
        self.state = "jump"
        self.active = True
        self.is_ai = is_ai
        self.invuln_timer = 2.2
        self.continue_timer = 10.0
        self.charm_timer = 0.0
        self.grabbed_timer = 0.0

    def add_meter(self, amount: float):
        self.hunmoon_meter = min(self.max_meter, self.hunmoon_meter + amount)

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + amount)

    def take_damage(self, amount: int, knockback_dir: int = 0) -> bool:
        if not self.active or self.state == "ko" or self.invuln_timer > 0 or self.special_timer > 0:
            return False

        self.hp -= amount
        self.hurt_timer = 0.28
        self.invuln_timer = 0.55
        self.state = "hurt"
        self.x += knockback_dir * 18.0
        if self.hp <= 0:
            self.lives -= 1
            if self.lives > 0:
                self.hp = self.max_hp
                self.y = 110.0
                self.vy = 0.0
                self.invuln_timer = 2.5
                self.state = "jump"
            else:
                self.hp = 0
                self.state = "ko"
                self.continue_timer = 9.9
        return True

    def update(
        self,
        dt: float,
        inp,
        camera_x: float,
        stage_width: float,
        enemies: list,
        boss,
        projectiles: list[Projectile],
        hazards: list[HazardZone],
        sparks: list[HitSpark],
        texts: list[FloatingText],
        all_players: list["HeroPlayer"],
        audio,
        stage_id: str = "plane",
        props: list[BreakableProp] | None = None,
    ):
        if not self.active:
            return

        active_props = props if props is not None else []
        prev_x = self.x
        ground_y, support_prop = compute_prop_ground_height(self.x, self.z, self.y, active_props)
        self.ground_y = ground_y
        on_ground = self.y <= ground_y + 0.5

        self.anim_timer += dt

        if self.state == "ko":
            if self.is_ai:
                self.active = False
                return
            self.continue_timer -= dt
            if self.continue_timer <= 0:
                self.active = False
            return

        if self.invuln_timer > 0:
            self.invuln_timer -= dt
        if self.charm_timer > 0:
            # Rumi's half-demon bloodline or Jinu's Soul Empowerment clears Gwi-Ma/Romance mind control faster
            decay = 2.5 if (self.char_id == "rumi" or self.soul_empowered) else 1.0
            self.charm_timer = max(0.0, self.charm_timer - dt * decay)
        if self.grabbed_timer > 0:
            self.grabbed_timer = max(0.0, self.grabbed_timer - dt)

        if self.soul_empowered:
            self.add_meter(dt * 14.0)

        # Combo window decay
        if self.combo_window > 0:
            self.combo_window -= dt
            if self.combo_window <= 0:
                self.combo_step = 0

        # Special attack active state
        if self.special_timer > 0:
            self.special_timer -= dt
            if self.special_timer <= 0 and on_ground:
                self.state = "idle"

        # Hurt recovery (still enforce wall/object bounds during knockback!)
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
            resolve_stage_and_prop_collisions(self, stage_id, active_props, ent_half_w=13.0, ent_half_d=4.5, prev_x=prev_x)
            if self.hurt_timer <= 0:
                self.state = "idle" if on_ground else "jump"
            return

        # Obtain controls from either human PlayerInputState or AI Companion Brain
        if self.is_ai:
            dx, dz, atk_press, jmp_press, spc_press, syn_press, dash_dir = self._compute_ai_inputs(enemies, boss)
        else:
            dx = inp.dx
            dz = inp.dz
            if self.charm_timer > 0:
                dx = -dx
                dz = -dz
            atk_press = inp.attack_pressed
            jmp_press = inp.jump_pressed
            spc_press = inp.special_pressed
            syn_press = inp.synergy_pressed
            dash_dir = inp.dash_triggered

        if dash_dir != 0 and on_ground:
            self.is_running = True
            self.facing = dash_dir

        # Trigger Hunmoon Special Attack (Button 3)
        if spc_press and self.special_timer <= 0:
            can_meter = self.hunmoon_meter >= 50.0
            can_desperation = self.hp > 22
            if can_meter or can_desperation:
                if can_meter:
                    self.hunmoon_meter -= 50.0
                else:
                    self.hp -= 12
                self._trigger_hunmoon_special(
                    enemies, boss, projectiles, hazards, sparks, texts, all_players, audio
                )
                return

        # Trigger Team Synergy / Dodge Roll (Button 4)
        if syn_press and self.attack_timer <= 0 and self.special_timer <= 0:
            # Check if another active hero is within 90px for a Duo K-Pop Harmony Blast!
            partner = None
            for other in all_players:
                if other is not self and other.active and other.state != "ko":
                    if math.hypot(other.x - self.x, other.z - self.z) < 95 and self.hunmoon_meter >= 35:
                        partner = other
                        break
            if partner is not None:
                self.hunmoon_meter = max(0.0, self.hunmoon_meter - 35.0)
                self.invuln_timer = 1.4
                partner.invuln_timer = 1.4
                audio.play_sfx("special_hunmoon")
                texts.append(
                    FloatingText(self.x, self.z, 70, f"{self.cfg['name']} x {partner.cfg['name']} HARMONY!", COLOR_HUNMOON_GOLD)
                )
                self._damage_area(165, 55, 42, enemies, boss, sparks, texts, audio)
                return
            else:
                # Evasive Dodge Roll (stopped by solid walls & obstacles)
                self.invuln_timer = 0.42
                self.x += self.facing * 65.0
                resolve_stage_and_prop_collisions(self, stage_id, active_props, ent_half_w=13.0, ent_half_d=4.5, prev_x=prev_x)
                texts.append(FloatingText(self.x, self.z, 45, "DODGE!", COLOR_NEON_CYAN))

        # Trigger Attack (Button 1)
        if atk_press and self.attack_timer <= 0 and self.special_timer <= 0:
            if self.grabbed_timer > 0:
                self.grabbed_timer = max(0.0, self.grabbed_timer - 0.45)
            self._start_attack(projectiles, enemies, boss, sparks, texts, audio)

        # Trigger Jump or Double-Jump Escape Vault (Button 2)
        if jmp_press and self.special_timer <= 0:
            if on_ground and self.attack_timer <= 0:
                if self.grabbed_timer > 0:
                    self.grabbed_timer = 0.0
                self.vy = self.cfg["jump_power"]
                self.y = ground_y + 1.0
                on_ground = False
                self.jumps_used = 1
                self.is_double_jumping = False
                self.air_vx = 0.0
                self.flip_angle = 0.0
                self.state = "jump"
            elif not on_ground and self.jumps_used < 2:
                # Double-Jump Escape Vault across the screen!
                self.jumps_used = 2
                self.is_double_jumping = True
                self.attack_timer = 0.0
                self.grabbed_timer = 0.0
                if abs(dx) > 0.15:
                    escape_dir = 1 if dx > 0 else -1
                else:
                    # Vault toward whichever side of the screen has more open room
                    screen_center_x = camera_x + 480.0
                    escape_dir = 1 if self.x < screen_center_x else -1
                self.facing = escape_dir
                self.vy = self.cfg["jump_power"] * 0.88
                self.air_vx = escape_dir * 520.0
                self.flip_angle = 0.0
                self.invuln_timer = max(self.invuln_timer, 0.58)
                self.state = "jump"
                audio.play_sfx("slash_light")
                texts.append(FloatingText(self.x, self.z, self.y + 55, "ESCAPE VAULT!", COLOR_NEON_CYAN))

        # Attack timer progression
        if self.attack_timer > 0:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.state = "jump" if not on_ground else "idle"

        # Movement (can move freely when not locked in grounded attack swing, or can drift in air)
        if (self.attack_timer <= 0 or not on_ground) and self.special_timer <= 0 and self.grabbed_timer <= 0:
            if self.is_double_jumping and not on_ground:
                # Rapid horizontal vault across screen + slight directional steering
                self.x += (self.air_vx + dx * 90.0) * dt
                self.z += dz * self.cfg["z_speed"] * dt
                self.air_vx *= max(0.0, 1.0 - dt * 1.35)
                self.flip_angle += 760.0 * dt
            elif abs(dx) < 0.1 and abs(dz) < 0.1:
                self.is_running = False
                if on_ground and self.attack_timer <= 0:
                    self.state = "idle"
            else:
                if dx < -0.1:
                    self.facing = -1
                elif dx > 0.1:
                    self.facing = 1

                spd_mult = 1.48 if self.is_running else 1.0
                if self.soul_empowered:
                    spd_mult *= 1.15
                self.x += dx * self.cfg["speed"] * spd_mult * dt
                self.z += dz * self.cfg["z_speed"] * dt
                if on_ground and self.attack_timer <= 0:
                    self.state = "run" if self.is_running else "walk"

        # Clamp within camera viewport and resolve stage walls + solid level/background objects!
        min_x = max(36.0, camera_x + 34.0)
        max_x = min(stage_width - 36.0, camera_x + 960.0 - 34.0)
        self.x = max(min_x, min(max_x, self.x))
        resolve_stage_and_prop_collisions(self, stage_id, active_props, ent_half_w=13.0, ent_half_d=4.5, prev_x=prev_x)
        self.x = max(min_x, min(max_x, self.x))

        # Recompute ground_y after horizontal/depth movement in case player jumped onto or walked off an object!
        ground_y, support_prop = compute_prop_ground_height(self.x, self.z, self.y, active_props)
        self.ground_y = ground_y

        # Vertical jump gravity & landing on the floor (y = 0.0) or on top of an object (y = ground_y)
        if self.y > ground_y or self.vy != 0.0:
            self.y += self.vy * dt
            self.vy -= GRAVITY * dt
            ground_y, support_prop = compute_prop_ground_height(self.x, self.z, self.y, active_props)
            self.ground_y = ground_y
            if self.y <= ground_y and self.vy <= 0.0:
                self.y = ground_y
                self.vy = 0.0
                self.jumps_used = 0
                self.is_double_jumping = False
                self.air_vx = 0.0
                self.flip_angle = 0.0
                if self.state == "jump":
                    self.state = "idle"
                # Gently center depth on the top surface when landing on an object unless stepping off
                if support_prop is not None and abs(dz) < 0.2:
                    if support_prop.bg_fixture:
                        self.z = support_prop.z
                    else:
                        self.z = support_prop.z - support_prop.half_d

    def _compute_ai_inputs(self, enemies: list, boss) -> tuple[float, float, bool, bool, bool, bool, int]:
        """Smart arcade teammate AI so solo or 2-player kids can play with the whole Huntr/x group!"""
        targets = [e for e in enemies if e.hp > 0]
        if boss is not None and boss.hp > 0:
            targets.append(boss)
        if not targets:
            return 0.0, 0.0, False, False, False, False, 0

        nearest = min(targets, key=lambda t: math.hypot(t.x - self.x, t.z - self.z))
        dist_x = nearest.x - self.x
        dist_z = nearest.z - self.z

        dx = 0.0
        dz = 0.0
        reach = self.cfg["attack_reach"] * 0.82
        if abs(dist_x) > reach:
            dx = 1.0 if dist_x > 0 else -1.0
        if abs(dist_z) > 18.0:
            dz = 1.0 if dist_z > 0 else -1.0

        atk = abs(dist_x) <= reach + 12 and abs(dist_z) <= 28 and random.random() < 0.22
        jmp = random.random() < 0.008
        spc = self.hunmoon_meter >= 85.0 and abs(dist_x) < 120 and random.random() < 0.04
        return dx, dz, atk, jmp, spc, False, 0

    def _start_attack(
        self,
        projectiles: list[Projectile],
        enemies: list,
        boss,
        sparks: list[HitSpark],
        texts: list[FloatingText],
        audio,
    ):
        self.state = "attack"
        base_dur = 0.34 / self.cfg["attack_speed"]
        self.attack_duration = base_dur
        self.attack_timer = base_dur
        self.combo_window = 0.65

        dmg_list = self.cfg["attack_damage"]
        dmg = dmg_list[self.combo_step % len(dmg_list)]
        if self.y > 0:
            # Jump Kick bonus damage!
            dmg = int(dmg * 1.25)
        if self.soul_empowered:
            dmg = int(dmg * 1.35)

        is_finisher = (self.combo_step % 4) == 3 or self.is_running
        self.is_running = False

        # Audio feedback
        if self.char_id == "bobby":
            audio.play_sfx("phone_throw")
        elif is_finisher or self.char_id == "mira":
            audio.play_sfx("slash_heavy")
        else:
            audio.play_sfx("slash_light")

        # Bobby's Ranged Cell Phone Combos!
        if self.char_id == "bobby" and (self.combo_step % 4 in (1, 2, 3)):
            count = 1 if (self.combo_step % 4) == 1 else (2 if (self.combo_step % 4) == 2 else 3)
            for i in range(count):
                vz = (i - (count - 1) / 2.0) * 65.0
                projectiles.append(
                    Projectile(
                        x=self.x + self.facing * 24,
                        z=self.z,
                        y=32,
                        vx=self.facing * 430.0,
                        vz=vz,
                        damage=dmg,
                        owner_team="hero",
                        proj_type="phone",
                        color=COLOR_NEON_CYAN,
                        radius=15.0,
                        pierce=is_finisher,
                    )
                )

        # Zoey's Finisher throws a piercing Shin-kal Spirit Dagger!
        if self.char_id == "zoey" and is_finisher:
            projectiles.append(
                Projectile(
                    x=self.x + self.facing * 24,
                    z=self.z,
                    y=30,
                    vx=self.facing * 520.0,
                    vz=0.0,
                    damage=dmg,
                    owner_team="hero",
                    proj_type="shinkal",
                    color=COLOR_NEON_PINK,
                    radius=14.0,
                    pierce=True,
                )
            )

        # Rumi's Soul-Empowered Sword sends a Hunmoon Light Wave on finishers!
        if self.char_id == "rumi" and (self.soul_empowered or is_finisher):
            projectiles.append(
                Projectile(
                    x=self.x + self.facing * 28,
                    z=self.z,
                    y=32,
                    vx=self.facing * 460.0,
                    vz=0.0,
                    damage=int(dmg * 0.85),
                    owner_team="hero",
                    proj_type="light_wave",
                    color=COLOR_NEON_CYAN,
                    radius=22.0,
                    pierce=True,
                )
            )

        # Melee Hitbox Check
        reach = self.cfg["attack_reach"] * (1.2 if self.soul_empowered else 1.0)
        z_tol = 36.0 if self.char_id == "mira" else 28.0
        hit_any = False

        targets = list(enemies)
        if boss is not None and boss.hp > 0:
            targets.append(boss)

        for target in targets:
            if target.hp <= 0:
                continue
            dx = (target.x - self.x) * self.facing
            dz = abs(target.z - self.z)
            # Hit enemies in front (or slightly behind on Mira's wide polearm sweep)
            min_dx = -24.0 if self.char_id == "mira" else -10.0
            if min_dx <= dx <= reach and dz <= z_tol:
                knockback = self.facing * (38.0 if is_finisher else 14.0)
                target.take_damage(dmg, knockback, is_heavy=is_finisher)
                hit_any = True
                self.score += 25
                self.add_meter(6.5)
                sparks.append(
                    HitSpark(
                        target.x,
                        target.z,
                        34,
                        self.cfg["color_primary"],
                        radius=30.0 if is_finisher else 20.0,
                    )
                )
                texts.append(
                    FloatingText(
                        target.x + random.uniform(-10, 10),
                        target.z,
                        52,
                        f"{dmg}{'!' if is_finisher else ''}",
                        COLOR_HUNMOON_GOLD if is_finisher else COLOR_WHITE,
                    )
                )

        if hit_any:
            audio.play_sfx("hit")

        self.combo_step = (self.combo_step + 1) % 4

    def _trigger_hunmoon_special(
        self,
        enemies: list,
        boss,
        projectiles: list[Projectile],
        hazards: list[HazardZone],
        sparks: list[HitSpark],
        texts: list[FloatingText],
        all_players: list["HeroPlayer"],
        audio,
    ):
        self.special_timer = 0.65
        self.invuln_timer = 1.6
        self.charm_timer = 0.0
        self.grabbed_timer = 0.0
        self.state = "attack"
        audio.play_sfx("special_hunmoon")

        texts.append(
            FloatingText(self.x, self.z, 76, f"{self.cfg['special_name'].upper()}!", self.cfg["color_secondary"])
        )

        if self.char_id == "rumi":
            # Half-Demon Resonance: 360° Sain-geom Shockwave + Cures all teammates' debuffs + 2 Light Beams!
            for ally in all_players:
                if ally.active:
                    ally.charm_timer = 0.0
                    ally.grabbed_timer = 0.0
                    ally.invuln_timer = max(ally.invuln_timer, 1.2)
            self._damage_area(175, 65, 48, enemies, boss, sparks, texts, audio)
            for dir_sign in (-1, 1):
                projectiles.append(
                    Projectile(
                        x=self.x + dir_sign * 20,
                        z=self.z,
                        y=32,
                        vx=dir_sign * 500.0,
                        vz=0.0,
                        damage=36,
                        owner_team="hero",
                        proj_type="light_wave",
                        color=COLOR_NEON_CYAN,
                        radius=28.0,
                        pierce=True,
                    )
                )

        elif self.char_id == "zoey":
            # Spitfire Spirit Barrage: 8-way fan of piercing Shin-kal Spirit Daggers!
            self._damage_area(125, 50, 32, enemies, boss, sparks, texts, audio)
            for dir_sign in (-1, 1):
                for vz in (-130.0, -45.0, 45.0, 130.0):
                    projectiles.append(
                        Projectile(
                            x=self.x + dir_sign * 16,
                            z=self.z,
                            y=30,
                            vx=dir_sign * 520.0,
                            vz=vz,
                            damage=28,
                            owner_team="hero",
                            proj_type="shinkal",
                            color=COLOR_NEON_PINK,
                            radius=16.0,
                            pierce=True,
                        )
                    )

        elif self.char_id == "mira":
            # Crescent Moon Cleave: Massive ground slam + Twin Golden Lunar Shockwaves!
            self.y = 48.0
            self.vy = -120.0
            self._damage_area(195, 75, 56, enemies, boss, sparks, texts, audio)
            for dir_sign in (-1, 1):
                projectiles.append(
                    Projectile(
                        x=self.x + dir_sign * 24,
                        z=self.z,
                        y=28,
                        vx=dir_sign * 420.0,
                        vz=0.0,
                        damage=42,
                        owner_team="hero",
                        proj_type="moon_wave",
                        color=COLOR_HUNMOON_GOLD,
                        radius=32.0,
                        pierce=True,
                    )
                )

        elif self.char_id == "bobby":
            # "Hold Please!" VIP Call: Drops 3 crashing stage spotlights on enemies + heals the team!
            self._damage_area(140, 55, 35, enemies, boss, sparks, texts, audio)
            for ally in all_players:
                if ally.active and ally.state != "ko":
                    ally.heal(25)
            texts.append(FloatingText(self.x, self.z, 94, "VIP BOBA SERVICE! +25 HP!", COLOR_HP_GREEN))
            for offset_x in (-130, 0, 130):
                hazards.append(
                    HazardZone(
                        x=self.x + offset_x + self.facing * 60,
                        z=self.z,
                        width=95,
                        depth=58,
                        warning_time=0.22,
                        active_time=0.45,
                        damage=45,
                        owner_team="hero",
                        hazard_type="spotlight",
                    )
                )

    def _damage_area(
        self,
        radius_x: float,
        radius_z: float,
        damage: int,
        enemies: list,
        boss,
        sparks: list[HitSpark],
        texts: list[FloatingText],
        audio,
    ):
        targets = list(enemies)
        if boss is not None and boss.hp > 0:
            targets.append(boss)
        for t in targets:
            if t.hp <= 0:
                continue
            if abs(t.x - self.x) <= radius_x and abs(t.z - self.z) <= radius_z:
                kb = 45.0 if t.x >= self.x else -45.0
                t.take_damage(damage, kb, is_heavy=True)
                self.score += 40
                sparks.append(HitSpark(t.x, t.z, 36, COLOR_HUNMOON_GOLD, radius=34.0))
                texts.append(FloatingText(t.x, t.z, 58, f"{damage}!", COLOR_HUNMOON_GOLD))

    def draw(self, surface: pygame.Surface, camera_x: float, font_small: pygame.font.Font):
        if not self.active or self.state == "ko":
            return
        sx = self.x - camera_x
        atk_prog = -1.0
        if self.attack_timer > 0 and self.attack_duration > 0:
            atk_prog = max(0.0, min(0.999, 1.0 - (self.attack_timer / self.attack_duration)))
        draw_hero_sprite(
            surface=surface,
            char_id=self.char_id,
            screen_x=sx,
            screen_z=self.z,
            y_offset=self.y,
            facing=self.facing,
            state=self.state,
            anim_timer=self.anim_timer,
            combo_step=self.combo_step,
            special_active=(self.special_timer > 0),
            soul_empowered=self.soul_empowered,
            hurt_flash=(self.hurt_timer > 0.14),
            invuln_blink=(self.invuln_timer > 0 and self.special_timer <= 0 and self.hurt_timer <= 0),
            attack_progress=atk_prog,
            is_double_jumping=self.is_double_jumping,
            flip_angle=self.flip_angle,
            ground_y=self.ground_y,
        )

        # Player indicator tag above head (P1, P2, P3, P4 / AI)
        tag_colors = [COLOR_NEON_CYAN, COLOR_NEON_PINK, COLOR_HUNMOON_GOLD, COLOR_HP_GREEN]
        tag_col = tag_colors[self.player_index % 4]
        label = f"P{self.player_index + 1}" if not self.is_ai else f"AI"
        if self.charm_timer > 0:
            label = "CHARMED!"
            tag_col = COLOR_NEON_PINK
        elif self.grabbed_timer > 0:
            label = "GRABBED!"
            tag_col = COLOR_WARNING

        tag_surf = font_small.render(label, True, tag_col)
        surface.blit(tag_surf, (int(sx - tag_surf.get_width() // 2), int(self.z - self.y - 152)))


class EnemyFighter:
    """
    Enemy Demon AI with Arcade Attack-Token & Formation Ring Fairness:
    - Only 2 enemies may engage a player in melee slots (1 left, 1 right) at a time,
      and only 1 enemy per player may swing at once!
    - Remaining enemies wait in an outer formation ring (165px–260px away), pacing
      until an attack token opens up.
    - Attacks have a fair 0.26s telegraphed wind-up that can be interrupted or dodged,
      followed by a brief post-attack step-back retreat.
    """

    def __init__(self, enemy_type: str, x: float, z: float):
        self.enemy_type = enemy_type
        self.cfg = ENEMIES[enemy_type]
        self.x = x
        self.z = z
        self.y = 0.0
        self.vy = 0.0
        self.facing = -1

        self.max_hp = self.cfg["max_hp"]
        self.hp = self.max_hp
        self.state = "walk"
        self.anim_timer = random.uniform(0.0, 5.0)
        self.hurt_timer = 0.0
        self.attack_cooldown = random.uniform(0.7, 1.6)
        self.attack_anim_timer = 0.0
        self.attack_damage_dealt = False
        self.retreat_timer = 0.0
        self.merge_timer = 0.0

        # Token & formation slot assignments (updated each frame by assign_enemy_tokens_and_slots)
        self.target_player: HeroPlayer | None = None
        self.has_attack_token: bool = False
        self.can_start_swing: bool = False
        self.slot_x: float = x
        self.slot_z: float = z
        self.slammed_this_hit: bool = False

    def take_damage(self, amount: int, knockback: float = 0.0, is_heavy: bool = False):
        self.hp -= amount
        self.hurt_timer = 0.30 if not self.cfg.get("super_armor") or is_heavy else 0.10
        self.merge_timer = 0.0
        self.slammed_this_hit = False
        if not self.cfg.get("super_armor") or is_heavy:
            # Interrupt enemy wind-up if hit before strike lands!
            self.attack_anim_timer = 0.0
            self.attack_damage_dealt = False
            self.x += knockback
            self.state = "hurt"
            if is_heavy:
                self.y = 6.0
                self.vy = 210.0

    def update(
        self,
        dt: float,
        players: list[HeroPlayer],
        other_enemies: list["EnemyFighter"],
        texts: list[FloatingText],
        audio,
        stage_id: str = "plane",
        props: list[BreakableProp] | None = None,
        boss=None,
        hazards: list[HazardZone] | None = None,
        pickups: list[PickupItem] | None = None,
        sparks: list[HitSpark] | None = None,
    ):
        if self.hp <= 0:
            return

        active_props = props if props is not None else []
        prev_x = self.x
        self.anim_timer += dt

        if self.y > 0 or self.vy != 0:
            self.y += self.vy * dt
            self.vy -= GRAVITY * dt
            if self.y <= 0:
                self.y = 0.0
                self.vy = 0.0

        if self.hurt_timer > 0:
            self.hurt_timer -= dt
            resolve_stage_and_prop_collisions(
                entity=self,
                stage_id=stage_id,
                props=active_props,
                ent_half_w=13.0,
                ent_half_d=4.5,
                is_enemy=True,
                enemies=other_enemies,
                boss=boss,
                players=players,
                hazards=hazards,
                pickups=pickups,
                sparks=sparks,
                texts=texts,
                audio=audio,
                prev_x=prev_x,
            )
            if self.hurt_timer <= 0:
                self.state = "walk"
                self.slammed_this_hit = False
            return

        if self.retreat_timer > 0:
            self.retreat_timer -= dt

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        # --- Active Telegraphed Attack Swing Progression ---
        if self.attack_anim_timer > 0:
            self.attack_anim_timer -= dt
            self.state = "attack"
            # Strike lands halfway through the 0.50s animation (after a fair 0.26s wind-up!)
            if not self.attack_damage_dealt and self.attack_anim_timer <= 0.24:
                self.attack_damage_dealt = True
                target = self.target_player
                if target is not None and target.active and target.state != "ko" and target.y < 38:
                    dx_hit = (target.x - self.x) * self.facing
                    dz_hit = abs(target.z - self.z)
                    if -10 <= dx_hit <= self.cfg["reach"] + 12 and dz_hit <= 28.0:
                        if target.take_damage(self.cfg["damage"], knockback_dir=self.facing):
                            audio.play_sfx("hit")
                            if self.cfg.get("can_grab") and target.grabbed_timer <= 0:
                                target.grabbed_timer = 1.0
                                texts.append(FloatingText(target.x, target.z, 64, "WATER GRAB!", COLOR_NEON_CYAN))
            if self.attack_anim_timer <= 0:
                self.state = "walk"
                self.retreat_timer = random.uniform(0.85, 1.35)
                self.attack_cooldown = random.uniform(1.3, 2.2)
            return

        # --- Faceless Demon Hive-Mind Merge Mechanic ---
        if self.cfg.get("can_merge") and self.enemy_type == "faceless":
            nearby_faceless = [
                e
                for e in other_enemies
                if e is not self
                and e.hp > 0
                and e.enemy_type == "faceless"
                and math.hypot(e.x - self.x, e.z - self.z) < 85.0
            ]
            if len(nearby_faceless) >= 2:
                self.merge_timer += dt
                if self.merge_timer >= 4.5:
                    nearby_faceless[0].hp = 0
                    nearby_faceless[1].hp = 0
                    self.enemy_type = "faceless_amalgam"
                    self.cfg = ENEMIES["faceless_amalgam"]
                    self.max_hp = self.cfg["max_hp"]
                    self.hp = self.max_hp
                    self.merge_timer = 0.0
                    texts.append(FloatingText(self.x, self.z, 72, "HIVE-MIND MERGE!", COLOR_DEMON_PURPLE))
                    return
            else:
                self.merge_timer = max(0.0, self.merge_timer - dt * 0.5)

        target = self.target_player
        if target is None or not target.active or target.state == "ko":
            self.state = "idle"
            return

        # Face the target player
        self.facing = 1 if (target.x >= self.x) else -1

        # Move toward assigned slot (either Flanking Attack Slot if holding token, or Outer Waiting Ring Post)
        dx_slot = self.slot_x - self.x
        dz_slot = self.slot_z - self.z
        spd = self.cfg["speed"] * (0.95 if self.has_attack_token else 0.65)

        moved = False
        if abs(dx_slot) > 10.0:
            step_x = math.copysign(min(abs(dx_slot), spd * dt), dx_slot)
            self.x += step_x
            moved = True
        if abs(dz_slot) > 8.0:
            step_z = math.copysign(min(abs(dz_slot), spd * 0.72 * dt), dz_slot)
            self.z += step_z
            moved = True

        # Enemy-to-enemy personal space repulsion (prevents stacking into a mass on top of each other)
        for other in other_enemies:
            if other is self or other.hp <= 0:
                continue
            ox = self.x - other.x
            oz = self.z - other.z
            if abs(ox) < 52.0 and abs(oz) < 30.0:
                push_x = (52.0 - abs(ox)) * (1.0 if ox >= 0 else -1.0) * 1.8 * dt
                push_z = (30.0 - abs(oz)) * (1.0 if oz >= 0 else -1.0) * 1.8 * dt
                self.x += push_x
                self.z += push_z

        resolve_stage_and_prop_collisions(
            entity=self,
            stage_id=stage_id,
            props=active_props,
            ent_half_w=13.0,
            ent_half_d=4.5,
            is_enemy=False,
            prev_x=prev_x,
        )
        self.state = "walk" if moved else "idle"

        # Only enemies holding an Attack Token AND swing permission may initiate an attack!
        if self.has_attack_token and self.can_start_swing and self.attack_cooldown <= 0 and self.retreat_timer <= 0:
            dist_x = abs(target.x - self.x)
            dist_z = abs(target.z - self.z)
            reach = self.cfg["reach"]
            if dist_x <= reach + 8 and dist_z <= 24.0:
                self.state = "attack"
                self.attack_anim_timer = 0.50
                self.attack_damage_dealt = False

    def draw(self, surface: pygame.Surface, camera_x: float):
        if self.hp <= 0:
            return
        sx = self.x - camera_x
        atk_prog = -1.0
        if self.attack_anim_timer > 0:
            atk_prog = max(0.0, min(0.999, 1.0 - (self.attack_anim_timer / 0.50)))
        draw_enemy_sprite(
            surface=surface,
            enemy_type=self.enemy_type,
            screen_x=sx,
            screen_z=self.z,
            y_offset=self.y,
            facing=self.facing,
            state=self.state,
            anim_timer=self.anim_timer,
            hurt_flash=(self.hurt_timer > 0.10),
            merge_progress=min(1.0, self.merge_timer / 4.2),
            attack_progress=atk_prog,
        )
        # Compact HP bar above enemy head
        if self.hp < self.max_hp:
            bw = 42
            bx = int(sx - bw // 2)
            by = int(self.z - self.y - 126 * self.cfg.get("scale", 1.0))
            pygame.draw.rect(surface, COLOR_BLACK, (bx - 1, by - 1, bw + 2, 6))
            pygame.draw.rect(surface, COLOR_HP_RED, (bx, by, bw, 4))
            fill_w = max(1, int(bw * (self.hp / self.max_hp)))
            pygame.draw.rect(surface, COLOR_HP_GREEN, (bx, by, fill_w, 4))


def assign_enemy_tokens_and_slots(
    enemies: list[EnemyFighter],
    players: list[HeroPlayer],
    anim_time: float,
    stage_id: str = "plane",
    props: list[BreakableProp] | None = None,
):
    """
    Arcade Beat-'Em-Up Crowd Coordinator:
    - Assigns each enemy to the nearest living player.
    - Grants at most 2 Attack Tokens per player (1 Left flanker, 1 Right flanker).
    - Allows at most 1 enemy per player to be actively swinging at any time.
    - Places all other enemies into a spaced-out Outer Waiting Ring (165px–260px away)
      clamped to the stage's walkable floor bounds and outside solid obstacles!
    """
    living_players = [p for p in players if p.active and p.state != "ko"]
    living_enemies = [e for e in enemies if e.hp > 0]
    if not living_players or not living_enemies:
        return

    by_player: dict[int, list[EnemyFighter]] = {id(p): [] for p in living_players}
    for e in living_enemies:
        nearest_p = min(living_players, key=lambda p: math.hypot(p.x - e.x, (p.z - e.z) * 1.4))
        e.target_player = nearest_p
        e.has_attack_token = False
        e.can_start_swing = False
        by_player[id(nearest_p)].append(e)

    for p in living_players:
        group = by_player[id(p)]
        if not group:
            continue

        # Sort eligible attackers (not retreating, not hurt) by proximity to player
        eligible = [e for e in group if e.retreat_timer <= 0 and e.hurt_timer <= 0]
        eligible.sort(key=lambda e: (0 if e.attack_anim_timer > 0 else 1, math.hypot(e.x - p.x, e.z - p.z)))

        left_holder: EnemyFighter | None = None
        right_holder: EnemyFighter | None = None

        for e in eligible:
            if left_holder is not None and right_holder is not None:
                break
            prefer_left = e.x <= p.x
            if prefer_left:
                if left_holder is None:
                    left_holder = e
                elif right_holder is None:
                    right_holder = e
            else:
                if right_holder is None:
                    right_holder = e
                elif left_holder is None:
                    left_holder = e

        token_holders: list[EnemyFighter] = []
        if left_holder is not None:
            left_holder.has_attack_token = True
            left_holder.slot_x = p.x - (left_holder.cfg["reach"] - 6)
            zl, zh = get_stage_z_bounds(stage_id, left_holder.slot_x)
            left_holder.slot_z = max(zl, min(zh, p.z - 6))
            token_holders.append(left_holder)

        if right_holder is not None:
            right_holder.has_attack_token = True
            right_holder.slot_x = p.x + (right_holder.cfg["reach"] - 6)
            zl, zh = get_stage_z_bounds(stage_id, right_holder.slot_x)
            right_holder.slot_z = max(zl, min(zh, p.z + 6))
            token_holders.append(right_holder)

        # Only 1 token holder per player may swing at a time!
        already_swinging = any(th.attack_anim_timer > 0 for th in token_holders)
        if not already_swinging and token_holders:
            # Give swing permission to whichever token holder is closest to its flanking slot
            ready_holder = min(token_holders, key=lambda th: abs(th.x - th.slot_x) + abs(th.z - th.slot_z))
            ready_holder.can_start_swing = True

        # Assign all non-token enemies to a spaced-out Outer Waiting Ring
        waiters = [e for e in group if not e.has_attack_token]
        waiters.sort(key=lambda e: e.x)
        for idx, w_enemy in enumerate(waiters):
            side = -1 if (w_enemy.x < p.x or (idx % 2 == 0 and w_enemy.x == p.x)) else 1
            ring_tier = idx // 2
            weave = math.sin(anim_time * 2.2 + idx * 1.3) * 14.0
            sx = p.x + side * (168.0 + ring_tier * 52.0) + weave
            zl, zh = get_stage_z_bounds(stage_id, sx)
            band = (idx % 4) / 3.0
            sz = zl + 12.0 + band * max(10.0, (zh - zl - 24.0))
            w_enemy.slot_x = sx
            w_enemy.slot_z = max(zl, min(zh, sz))


class BossFighter:
    """
    Stage Bosses:
    1. Mystery (Stage 1 - Plane): Shadow teleports + Phantom Orbs + spawns Illusion Decoy
    2. Romance (Stage 2 - Concert): Charmed Heart projectiles (reverses controls!) + Spin sweep
    3. Abby (Stage 3 - Bathhouse): Tidal wave hot-tub eruption + Super-armor charge
    4. Baby (Stage 4 - Bullet Train): Supersonic wall-bounce tornado kicks + Wind cutters
    5. Jinu (Stage 5 - Saja Concert): Dark Soul slashes -> Yields & empowers Huntr/x with Soul Energy!
    6. Gwi-Ma (Stage 6 - Final Boss): Colossal Flame Monarch with sweeping lane flamethrowers & molten fist slams!
    """

    def __init__(self, boss_id: str, x: float, z: float, player_count: int = 1):
        self.boss_id = boss_id
        self.cfg = BOSSES[boss_id]
        self.x = x
        self.z = z
        self.y = 0.0
        self.facing = -1

        # Scale boss HP smoothly with active player count
        hp_scale = 1.0 + 0.22 * max(0, player_count - 1)
        self.max_hp = int(self.cfg["max_hp"] * hp_scale)
        self.hp = self.max_hp

        self.state = "walk"
        self.anim_timer = 0.0
        self.hurt_timer = 0.0
        self.action_timer = 1.6
        self.special_cooldown = 3.2
        self.jinu_empowered_triggered = False

    def take_damage(self, amount: int, knockback: float = 0.0, is_heavy: bool = False):
        self.hp = max(0, self.hp - amount)
        self.hurt_timer = 0.14
        if self.boss_id != "gwima" and is_heavy:
            self.x += knockback * 0.35

    def update(
        self,
        dt: float,
        camera_x: float,
        players: list[HeroPlayer],
        enemies: list[EnemyFighter],
        projectiles: list[Projectile],
        hazards: list[HazardZone],
        texts: list[FloatingText],
        audio,
        stage_id: str = "plane",
        props: list[BreakableProp] | None = None,
    ):
        if self.hp <= 0:
            return

        active_props = props if props is not None else []
        self.anim_timer += dt
        if self.hurt_timer > 0:
            self.hurt_timer -= dt

        # Stage 5 Story Moment: Jinu yields at <=12% HP and empowers the team with his Soul Energy!
        if self.boss_id == "jinu" and not self.jinu_empowered_triggered and self.hp <= self.max_hp * 0.12:
            self.jinu_empowered_triggered = True
            self.hp = 0
            audio.play_sfx("stage_clear")
            for p in players:
                p.soul_empowered = True
                p.heal(999)
                p.hunmoon_meter = 100.0
            texts.append(
                FloatingText(
                    self.x,
                    self.z,
                    90,
                    "JINU: 'TAKE MY SOUL ENERGY, RUMI!'",
                    COLOR_NEON_CYAN,
                )
            )
            return

        living_players = [p for p in players if p.active and p.state != "ko"]
        if not living_players:
            return

        target = min(living_players, key=lambda p: math.hypot(p.x - self.x, p.z - self.z))
        dist_x = target.x - self.x
        dist_z = target.z - self.z
        self.facing = 1 if dist_x >= 0 else -1

        self.action_timer -= dt
        self.special_cooldown -= dt

        if self.boss_id == "gwima":
            # Gwi-Ma stays anchored on the right side of the inferno arena and unleashes massive attacks
            desired_x = camera_x + 790.0
            self.x += (desired_x - self.x) * min(1.0, dt * 3.0)
            self.z += (target.z - self.z) * min(1.0, dt * 1.4)
            zl, zh = get_stage_z_bounds(stage_id, self.x)
            self.z = max(zl + 14, min(zh - 14, self.z))

            if self.special_cooldown <= 0:
                self.special_cooldown = 2.6
                self.state = "attack"
                pattern = random.choice(["flame_lanes", "fist_slam", "fire_fan"])
                if pattern == "flame_lanes":
                    # Sweeping Flamethrower Breath across 2 lanes!
                    texts.append(FloatingText(self.x - 140, self.z, 110, "GWI-MA INFERNO BREATH!", COLOR_GWIMA_FIRE))
                    chosen_lanes = random.sample([zl + 22, (zl + zh) / 2, zh - 22], 2)
                    for lz in chosen_lanes:
                        hazards.append(
                            HazardZone(
                                x=camera_x + 440,
                                z=lz,
                                width=780,
                                depth=56,
                                warning_time=0.95,
                                active_time=0.70,
                                damage=24,
                                owner_team="enemy",
                                hazard_type="gwima_flame",
                            )
                        )
                elif pattern == "fist_slam":
                    # Colossal Molten Fist Slams on player positions!
                    texts.append(FloatingText(self.x - 120, self.z, 110, "MOLTEN FIST SLAM!", COLOR_HUNMOON_GOLD))
                    for p in living_players:
                        hazards.append(
                            HazardZone(
                                x=p.x,
                                z=p.z,
                                width=120,
                                depth=64,
                                warning_time=0.80,
                                active_time=0.45,
                                damage=26,
                                owner_team="enemy",
                                hazard_type="gwima_flame",
                            )
                        )
                else:
                    # 5-Way Fireball Barrage
                    for vz in (-140, -70, 0, 70, 140):
                        projectiles.append(
                            Projectile(
                                x=self.x - 60,
                                z=self.z,
                                y=45,
                                vx=-360.0,
                                vz=vz,
                                damage=18,
                                owner_team="enemy",
                                proj_type="fireball",
                                color=COLOR_GWIMA_FIRE,
                                radius=18.0,
                            )
                        )
            return

        # Standard Saja Boys Boss Movement & Signature Skills
        if abs(dist_x) > 68:
            self.x += self.facing * self.cfg["speed"] * dt
            self.state = "walk"
        if abs(dist_z) > 18:
            self.z += (1 if dist_z > 0 else -1) * (self.cfg["speed"] * 0.72) * dt

        self.x = max(camera_x + 50, min(camera_x + 910, self.x))
        resolve_stage_and_prop_collisions(self, stage_id, active_props, ent_half_w=20.0, ent_half_d=12.0)

        # Close-range combo strike
        if abs(dist_x) <= 74 and abs(dist_z) <= 28 and self.action_timer <= 0:
            self.state = "attack"
            self.action_timer = 1.05
            if target.take_damage(self.cfg["damage"], knockback_dir=self.facing):
                audio.play_sfx("hit")

        # Signature Saja Boys Special Moves
        if self.special_cooldown <= 0:
            self.special_cooldown = 3.6
            self.state = "attack"

            if self.boss_id == "mystery":
                # Teleport across cabin + fire phantom orbs
                self.x = camera_x + random.choice([180, 480, 780])
                zl, zh = get_stage_z_bounds(stage_id, self.x)
                self.z = random.uniform(zl + 14, zh - 14)
                resolve_stage_and_prop_collisions(self, stage_id, active_props, ent_half_w=20.0, ent_half_d=12.0)
                texts.append(FloatingText(self.x, self.z, 75, "PHANTOM ILLUSION!", COLOR_DEMON_PURPLE))
                for dir_s in (-1, 1):
                    projectiles.append(
                        Projectile(
                            x=self.x,
                            z=self.z,
                            y=32,
                            vx=dir_s * 340.0,
                            vz=0.0,
                            damage=14,
                            owner_team="enemy",
                            proj_type="shadow_orb",
                            color=COLOR_NEON_CYAN,
                            radius=15.0,
                        )
                    )

            elif self.boss_id == "romance":
                # Blows Charmed Hearts that reverse player joystick controls!
                texts.append(FloatingText(self.x, self.z, 75, "HEARTBREAKER CHARM!", COLOR_NEON_PINK))
                for vz in (-85.0, 0.0, 85.0):
                    projectiles.append(
                        Projectile(
                            x=self.x + self.facing * 24,
                            z=self.z,
                            y=34,
                            vx=self.facing * 310.0,
                            vz=vz,
                            damage=12,
                            owner_team="enemy",
                            proj_type="charm_heart",
                            color=COLOR_NEON_PINK,
                            radius=16.0,
                        )
                    )

            elif self.boss_id == "abby":
                # Bathhouse Geyser Slam!
                texts.append(FloatingText(self.x, self.z, 80, "TIDAL WAVE SLAM!", COLOR_NEON_CYAN))
                for p in living_players:
                    hazards.append(
                        HazardZone(
                            x=p.x,
                            z=p.z,
                            width=105,
                            depth=62,
                            warning_time=0.75,
                            active_time=0.45,
                            damage=20,
                            owner_team="enemy",
                            hazard_type="steam",
                        )
                    )

            elif self.boss_id == "baby":
                # Supersonic Tornado Dash + Wind Cutters
                texts.append(FloatingText(self.x, self.z, 75, "SUPERSONIC SPIN!", COLOR_HP_GREEN))
                self.x += self.facing * 160.0
                self.x = max(camera_x + 60, min(camera_x + 900, self.x))
                for dir_s in (-1, 1):
                    projectiles.append(
                        Projectile(
                            x=self.x,
                            z=self.z,
                            y=30,
                            vx=dir_s * 420.0,
                            vz=0.0,
                            damage=16,
                            owner_team="enemy",
                            proj_type="wind_cutter",
                            color=COLOR_HP_GREEN,
                            radius=18.0,
                        )
                    )

            elif self.boss_id == "jinu":
                # Dark Soul Crescent Waves + Demon Pillar Eruption
                texts.append(FloatingText(self.x, self.z, 80, "DARK IDOL SLASH!", (255, 50, 100)))
                for vz in (-60.0, 60.0):
                    projectiles.append(
                        Projectile(
                            x=self.x + self.facing * 28,
                            z=self.z,
                            y=34,
                            vx=self.facing * 390.0,
                            vz=vz,
                            damage=18,
                            owner_team="enemy",
                            proj_type="soul_wave",
                            color=(255, 50, 110),
                            radius=20.0,
                        )
                    )

    def draw(self, surface: pygame.Surface, camera_x: float):
        if self.hp <= 0:
            return
        sx = self.x - camera_x
        draw_boss_sprite(
            surface=surface,
            boss_id=self.boss_id,
            screen_x=sx,
            screen_z=self.z,
            y_offset=self.y,
            facing=self.facing,
            state=self.state,
            anim_timer=self.anim_timer,
            hurt_flash=(self.hurt_timer > 0.05),
        )
