"""
Core configuration, constants, character rosters, enemy stats, and stage definitions
for K-Pop Demon Hunters: Arcade Beat 'Em Up.
"""

import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, "backgrounds")

# Display & Arcade Canvas Settings
GAME_TITLE = "K-POP DEMON HUNTERS: THE ARCADE GAME"
INTERNAL_WIDTH = 960
INTERNAL_HEIGHT = 540
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 720
FPS = 60

# 2.5D Walkable Lane Depth Bounds (Z maps to screen Y when grounded)
LANE_TOP = 372
LANE_BOTTOM = 484
GRAVITY = 1550.0


def world_x_to_bg_img_x(world_x: float) -> float:
    """Map world X to local X (0..INTERNAL_WIDTH) inside the mirror-tiled 960x540 stage background."""
    tile_idx = int(world_x // INTERNAL_WIDTH)
    rem_x = world_x - tile_idx * INTERNAL_WIDTH
    if tile_idx % 2 == 1:
        return float(INTERNAL_WIDTH) - rem_x
    return rem_x


def get_stage_z_bounds(stage_id: str, world_x: float) -> tuple[float, float]:
    """
    Return the exact walkable floor depth bounds (z_min, z_max) at `world_x`
    for `stage_id`, matching the painted walls, counters, stage ledges, and train rails
    so characters and enemies can never walk on walls or off platform drop-offs.
    """
    img_x = world_x_to_bg_img_x(world_x)

    if stage_id == "plane":
        # Left fuselage wall & exit door (0..342), marble bar counter (342..560),
        # VIP purple sofas (560..790), rear door alcove (790..892), right counter (892..960)
        if img_x < 342.0:
            z_min = 394.0 - (img_x / 342.0) * 10.0
        elif img_x < 560.0:
            z_min = 384.0
        elif img_x < 790.0:
            t = (img_x - 560.0) / 230.0
            z_min = 376.0 - t * 16.0
        elif img_x < 892.0:
            z_min = 358.0
        else:
            z_min = 384.0
        return z_min, 512.0

    if stage_id in ("concert", "saja_concert", "gwima_lair"):
        # Neon stage platform top border (y=366, angled at outer corners) & front drop-off ledge (y=484)
        if stage_id == "saja_concert":
            # saja_concert.jpg is horizontally flipped relative to concert.jpg
            img_x = float(INTERNAL_WIDTH) - img_x
        if img_x < 118.0:
            z_min = 388.0 - (img_x / 118.0) * 14.0
        elif img_x > 875.0:
            z_min = 374.0 + ((img_x - 875.0) / 85.0) * 14.0
        else:
            z_min = 374.0
        return z_min, 478.0

    if stage_id == "bathhouse":
        # Between the cedar shoji wall / recessed wall baths (y=378) and front stone curb (y=488)
        return 384.0, 482.0

    if stage_id == "train":
        # Between top cyan roof safety rail (y=362, plus painted AC unit at 820..960)
        # and bottom cyan safety rail (y=478, plus painted relay box at 630..740)
        z_min = 396.0 if img_x >= 820.0 else 370.0
        z_max = 454.0 if (630.0 <= img_x <= 740.0) else 472.0
        return z_min, z_max

    return float(LANE_TOP), float(LANE_BOTTOM)

# Color Palette (Vibrant K-Pop Neon + Korean Mythic Arcade)
COLOR_BG_DARK = (14, 10, 26)
COLOR_NEON_PINK = (255, 65, 165)
COLOR_NEON_CYAN = (45, 235, 255)
COLOR_HUNMOON_BLUE = (60, 180, 255)
COLOR_HUNMOON_GOLD = (255, 215, 70)
COLOR_DEMON_PURPLE = (155, 50, 220)
COLOR_GWIMA_FIRE = (255, 90, 25)
COLOR_WHITE = (250, 250, 255)
COLOR_BLACK = (10, 8, 16)
COLOR_HP_GREEN = (60, 235, 110)
COLOR_HP_RED = (225, 45, 65)
COLOR_WARNING = (255, 55, 55)

# Playable Characters (4-Player Roster)
CHARACTER_ORDER = ["rumi", "zoey", "mira", "bobby"]

CHARACTERS = {
    "rumi": {
        "id": "rumi",
        "name": "RUMI",
        "title": "Lead Singer & Leader",
        "weapon_name": "Sain-geom (Hunmoon Light Sword)",
        "color_primary": (110, 175, 255),     # Electric Hunmoon Blue
        "color_secondary": (255, 215, 85),    # Golden trim
        "hair_color": (135, 75, 235),         # Iconic purple braided hair
        "skin_pattern_color": (65, 225, 255), # Glowing Half-Demon blue patterns
        "max_hp": 140,
        "speed": 215.0,
        "z_speed": 150.0,
        "jump_power": 540.0,
        "attack_damage": [14, 16, 20, 32],
        "attack_reach": 84,
        "attack_speed": 1.05,
        "special_name": "Half-Demon Resonance",
        "special_desc": "Blue demon patterns ignite! 360° Sain-geom light wave + mind-control immunity.",
    },
    "zoey": {
        "id": "zoey",
        "name": "ZOEY",
        "title": "Lead Rapper",
        "weapon_name": "Shin-kal (Spirit Daggers)",
        "color_primary": (255, 85, 175),      # Hyper Neon Pink
        "color_secondary": (80, 250, 220),    # Mint/Cyan accents
        "hair_color": (30, 30, 48),           # Dark twin buns / space buns
        "skin_pattern_color": (255, 140, 220),
        "max_hp": 125,
        "speed": 250.0,
        "z_speed": 175.0,
        "jump_power": 575.0,
        "attack_damage": [11, 12, 14, 24],
        "attack_reach": 68,
        "attack_speed": 1.35,
        "special_name": "Spitfire Spirit Barrage",
        "special_desc": "Acrobatic spin unleashing a fan of piercing Shin-kal spirit daggers!",
    },
    "mira": {
        "id": "mira",
        "name": "MIRA",
        "title": "Lead Dancer & Choreographer",
        "weapon_name": "Gok-Do (Curved Moon Polearm)",
        "color_primary": (245, 60, 95),       # Fierce Crimson/Magenta
        "color_secondary": (255, 200, 60),    # Gold Crescent Blade
        "hair_color": (215, 45, 105),         # Sleek long pink/red hair
        "skin_pattern_color": (255, 190, 70),
        "max_hp": 155,
        "speed": 195.0,
        "z_speed": 140.0,
        "jump_power": 520.0,
        "attack_damage": [18, 22, 26, 40],
        "attack_reach": 102,
        "attack_speed": 0.90,
        "special_name": "Crescent Moon Cleave",
        "special_desc": "Leaping Gok-Do ground slam that sends a lunar shockwave across the stage!",
    },
    "bobby": {
        "id": "bobby",
        "name": "BOBBY",
        "title": "Group Manager",
        "weapon_name": "VIP Cell Phones & Clipboard",
        "color_primary": (70, 205, 135),      # Manager Mint/Emerald Suit
        "color_secondary": (255, 230, 100),   # VIP Gold Lanyard
        "hair_color": (45, 32, 24),           # Neat parted brown hair
        "skin_pattern_color": (120, 245, 170),
        "max_hp": 150,
        "speed": 205.0,
        "z_speed": 148.0,
        "jump_power": 510.0,
        "attack_damage": [13, 15, 18, 28],
        "attack_reach": 95,
        "attack_speed": 1.0,
        "special_name": "Hold Please! VIP Drop",
        "special_desc": "Calls in falling stage spotlights on enemies and tosses healing Boba to the team!",
    },
}

# Enemy Types
ENEMIES = {
    "faceless": {
        "name": "Faceless Demon",
        "max_hp": 42,
        "speed": 125.0,
        "damage": 7,
        "reach": 42,
        "score": 100,
        "color": (135, 55, 185),
        "scale": 0.85,
        "can_merge": True,
    },
    "faceless_amalgam": {
        "name": "Hive-Mind Amalgam",
        "max_hp": 145,
        "speed": 95.0,
        "damage": 16,
        "reach": 66,
        "score": 350,
        "color": (185, 40, 230),
        "scale": 1.35,
        "super_armor": True,
    },
    "dokkaebi_trickster": {
        "name": "Dokkaebi Trickster",
        "max_hp": 70,
        "speed": 140.0,
        "damage": 10,
        "reach": 58,
        "score": 200,
        "color": (210, 75, 65),
        "scale": 0.98,
    },
    "dokkaebi_brute": {
        "name": "Dokkaebi Brute",
        "max_hp": 165,
        "speed": 90.0,
        "damage": 18,
        "reach": 76,
        "score": 400,
        "color": (175, 45, 45),
        "scale": 1.38,
        "super_armor": True,
    },
    "mulguishin": {
        "name": "Mulguishin (Water Demon)",
        "max_hp": 85,
        "speed": 135.0,
        "damage": 12,
        "reach": 72,
        "score": 250,
        "color": (45, 145, 155),
        "scale": 1.02,
        "can_grab": True,
    },
    "half_demon_rogue": {
        "name": "Corrupted Half-Demon",
        "max_hp": 120,
        "speed": 175.0,
        "damage": 14,
        "reach": 64,
        "score": 350,
        "color": (75, 110, 210),
        "scale": 1.05,
    },
}

# Boss Roster (Saja Boys + Gwi-Ma)
BOSSES = {
    "mystery": {
        "name": "MYSTERY (Saja Boys)",
        "subtitle": "Phantom Illusionist",
        "max_hp": 480,
        "speed": 165.0,
        "damage": 16,
        "color_primary": (140, 70, 235),
        "color_secondary": (65, 225, 255),
        "hair_color": (195, 180, 240),
        "score": 2500,
    },
    "romance": {
        "name": "ROMANCE (Saja Boys)",
        "subtitle": "Heartbreaker Idol",
        "max_hp": 580,
        "speed": 155.0,
        "damage": 18,
        "color_primary": (255, 75, 165),
        "color_secondary": (255, 215, 95),
        "hair_color": (255, 145, 195),
        "score": 3000,
    },
    "abby": {
        "name": "ABBY (Saja Boys)",
        "subtitle": "Heavyweight Enforcer",
        "max_hp": 720,
        "speed": 135.0,
        "damage": 22,
        "color_primary": (45, 195, 220),
        "color_secondary": (255, 140, 55),
        "hair_color": (40, 80, 140),
        "score": 3500,
    },
    "baby": {
        "name": "BABY (Saja Boys)",
        "subtitle": "Supersonic Maknae",
        "max_hp": 650,
        "speed": 225.0,
        "damage": 18,
        "color_primary": (85, 245, 155),
        "color_secondary": (255, 235, 75),
        "hair_color": (255, 220, 95),
        "score": 4000,
    },
    "jinu": {
        "name": "JINU (Leader of the Saja Boys)",
        "subtitle": "Tormented Demon Prince",
        "max_hp": 850,
        "speed": 190.0,
        "damage": 22,
        "color_primary": (195, 35, 85),
        "color_secondary": (90, 200, 255),
        "hair_color": (25, 20, 35),
        "score": 5000,
    },
    "gwima": {
        "name": "GWI-MA, LORD OF LIVING FIRE",
        "subtitle": "Supreme Monarch of Demons",
        "max_hp": 1400,
        "speed": 110.0,
        "damage": 26,
        "color_primary": (255, 80, 20),
        "color_secondary": (255, 215, 50),
        "hair_color": (255, 140, 0),
        "score": 10000,
    },
}

# Pickups (Korean Street Food & Concert Items)
PICKUPS = {
    "boba": {"name": "Brown Sugar Boba", "heal": 40, "meter": 15, "score": 150, "color": (210, 155, 105)},
    "tteokbokki": {"name": "Spicy Tteokbokki", "heal": 75, "meter": 20, "score": 250, "color": (245, 65, 55)},
    "corndog": {"name": "K-Cheese Corn Dog", "heal": 65, "meter": 15, "score": 200, "color": (245, 185, 60)},
    "lightstick": {"name": "Huntr/x Golden Lightstick", "heal": 20, "meter": 100, "score": 300, "color": (255, 220, 70)},
    "kbbq": {"name": "Deluxe K-BBQ Feast", "heal": 999, "meter": 50, "score": 500, "color": (255, 110, 80), "team_heal": True},
}

# 6-Stage Story Campaign & Song Mapping
STAGES = [
    {
        "number": 1,
        "id": "plane",
        "name": "STAGE 1: MILE-HIGH AMBUSH",
        "location": "Aboard the Huntr/x Private Jet",
        "song_title": "How It's Done",
        "song_artist": "HUNTR/X (EJAE, Audrey Nuna, Rei Ami)",
        "song_file_stem": "stage1_how_its_done",
        "song_keywords": ["how_its_done", "how it's done", "howitsdone", "stage1"],
        "bpm": 128,
        "length": 2500,
        "boss": "mystery",
        "theme_color": (95, 55, 185),
        "hazard": "turbulence",
        "intro_text": "Demons have breached the Huntr/x jet! Clear the cabin before the engines fail!",
        "outro_text": "MYSTERY IS DEFEATED! The engines are burning—JUMP OUT OF THE PLANE!",
        "waves": [
            {"x": 450, "enemies": [("faceless", 4), ("dokkaebi_trickster", 2)]},
            {"x": 1050, "enemies": [("dokkaebi_trickster", 3), ("faceless", 4)]},
            {"x": 1680, "enemies": [("dokkaebi_brute", 1), ("dokkaebi_trickster", 2), ("faceless", 4)]},
            {"x": 2250, "boss": "mystery", "minions": [("faceless", 3)]},
        ],
    },
    {
        "number": 2,
        "id": "concert",
        "name": "STAGE 2: CRASH THE CONCERT",
        "location": "Seoul Neon Dome — Crowd & Main Stage",
        "song_title": "Golden",
        "song_artist": "HUNTR/X",
        "song_file_stem": "stage2_golden",
        "song_keywords": ["golden", "stage2"],
        "bpm": 124,
        "length": 2600,
        "boss": "romance",
        "theme_color": (225, 165, 35),
        "hazard": "spotlights",
        "intro_text": "Skydiving straight into the arena! Fight through the demon-possessed crowd to the stage!",
        "outro_text": "ROMANCE'S SPELL IS BROKEN! The fans are safe—head to the bathhouse hideout!",
        "waves": [
            {"x": 480, "enemies": [("dokkaebi_trickster", 3), ("faceless", 4)]},
            {"x": 1100, "enemies": [("dokkaebi_brute", 1), ("dokkaebi_trickster", 3), ("faceless", 3)]},
            {"x": 1750, "enemies": [("dokkaebi_brute", 2), ("half_demon_rogue", 1), ("faceless", 4)]},
            {"x": 2350, "boss": "romance", "minions": [("dokkaebi_trickster", 2)]},
        ],
    },
    {
        "number": 3,
        "id": "bathhouse",
        "name": "STAGE 3: STEAM & SHADOWS",
        "location": "Old Seoul Traditional Bathhouse",
        "song_title": "Free",
        "song_artist": "HUNTR/X",
        "song_file_stem": "stage3_free",
        "song_keywords": ["free", "stage3"],
        "bpm": 118,
        "length": 2600,
        "boss": "abby",
        "theme_color": (35, 165, 185),
        "hazard": "hottubs",
        "intro_text": "Watch the bubbling hot tubs! Mulguishin water demons are lurking beneath the steam!",
        "outro_text": "ABBY IS WASHED UP! Hurry—the Saja Boys are boarding the midnight bullet train!",
        "waves": [
            {"x": 480, "enemies": [("mulguishin", 3), ("faceless", 3)]},
            {"x": 1120, "enemies": [("mulguishin", 3), ("dokkaebi_brute", 1), ("dokkaebi_trickster", 2)]},
            {"x": 1760, "enemies": [("mulguishin", 4), ("dokkaebi_brute", 2)]},
            {"x": 2350, "boss": "abby", "minions": [("mulguishin", 2)]},
        ],
    },
    {
        "number": 4,
        "id": "train",
        "name": "STAGE 4: RUNAWAY BULLET TRAIN",
        "location": "KTX High-Speed Express Rooftop",
        "song_title": "Takedown",
        "song_artist": "HUNTR/X",
        "song_file_stem": "stage4_takedown",
        "song_keywords": ["takedown", "take_down", "stage4"],
        "bpm": 138,
        "length": 2700,
        "boss": "baby",
        "theme_color": (45, 200, 125),
        "hazard": "train_signs",
        "intro_text": "High-speed rooftop battle! Watch out for low tunnel signs and Baby's supersonic kicks!",
        "outro_text": "BABY IS DERAILED! The train arrives at the Saja Boys' dark stadium...",
        "waves": [
            {"x": 500, "enemies": [("half_demon_rogue", 2), ("dokkaebi_trickster", 3)]},
            {"x": 1180, "enemies": [("dokkaebi_brute", 2), ("faceless", 5)]},
            {"x": 1820, "enemies": [("half_demon_rogue", 2), ("dokkaebi_brute", 2), ("faceless", 4)]},
            {"x": 2450, "boss": "baby", "minions": [("half_demon_rogue", 1), ("faceless", 2)]},
        ],
    },
    {
        "number": 5,
        "id": "saja_concert",
        "name": "STAGE 5: THE DARK ENCORE",
        "location": "Demonic Saja Boys Stadium Altar",
        "song_title": "Your Idol",
        "song_artist": "Saja Boys",
        "song_file_stem": "stage5_your_idol",
        "song_keywords": ["your_idol", "your idol", "youridol", "stage5"],
        "bpm": 132,
        "length": 2800,
        "boss": "jinu",
        "theme_color": (195, 30, 85),
        "hazard": "dark_pillars",
        "intro_text": "The Saja Boys are draining the crowd's souls! Fight through the demon horde to reach Jinu!",
        "outro_text": "JINU BREAKS FREE! 'Take my soul energy, Rumi... Finish Gwi-Ma together!'",
        "waves": [
            {"x": 500, "enemies": [("faceless", 6), ("dokkaebi_trickster", 3)]},
            {"x": 1150, "enemies": [("mulguishin", 3), ("dokkaebi_brute", 2), ("faceless", 4)]},
            {"x": 1850, "enemies": [("half_demon_rogue", 3), ("dokkaebi_brute", 2), ("faceless", 5)]},
            {"x": 2550, "boss": "jinu", "minions": [("half_demon_rogue", 2)]},
        ],
    },
    {
        "number": 6,
        "id": "gwima_lair",
        "name": "FINAL STAGE: HEART OF THE INFERNO",
        "location": "The Hunmoon Abyss — Throne of Gwi-Ma",
        "song_title": "What It Sounds Like",
        "song_artist": "HUNTR/X",
        "song_file_stem": "stage6_what_it_sounds_like",
        "song_keywords": ["what_it_sounds_like", "what it sounds like", "whatitsoundslike", "stage6"],
        "bpm": 130,
        "length": 1500,
        "boss": "gwima",
        "theme_color": (255, 80, 20),
        "hazard": "fire_waves",
        "soul_empowered": True,
        "intro_text": "SOUL EMPOWERED BY JINU! Dodge Gwi-Ma's inferno lanes and strike his molten hands & core!",
        "outro_text": "GWI-MA IS VANQUISHED! The Hunmoon shines golden once more!",
        "waves": [
            {"x": 550, "enemies": [("dokkaebi_brute", 2), ("half_demon_rogue", 2), ("faceless", 5)]},
            {"x": 1220, "boss": "gwima", "minions": [("faceless", 4)]},
        ],
    },
]
