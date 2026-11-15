"""
Arcade HUD, Title / Attract Screen, 4-Player Character Select, Boss Health Bar,
and Story Cutscene Overlays for K-Pop Demon Hunters.
"""

import math
import pygame
from src.config import (
    CHARACTER_ORDER,
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
    INTERNAL_HEIGHT,
    INTERNAL_WIDTH,
)
from src.sprites import ASSET_BANK


class ArcadeHUD:
    """Renders the 4-player TMNT-style top arcade HUD, boss bars, title screen, and character select."""

    def __init__(self):
        pygame.font.init()
        self.font_xs = pygame.font.SysFont("arial", 13, bold=True)
        self.font_sm = pygame.font.SysFont("arial", 16, bold=True)
        self.font_md = pygame.font.SysFont("arial", 22, bold=True)
        self.font_lg = pygame.font.SysFont("arial", 34, bold=True)
        self.font_xl = pygame.font.SysFont("arial", 46, bold=True)

    def draw_text_outlined(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        pos: tuple[int, int],
        center: bool = False,
    ):
        fg = font.render(text, True, color)
        bg = font.render(text, True, COLOR_BLACK)
        x, y = pos
        if center:
            x -= fg.get_width() // 2
            y -= fg.get_height() // 2
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)):
            surface.blit(bg, (x + ox, y + oy))
        surface.blit(fg, (x, y))

    def draw_gameplay_hud(
        self,
        surface: pygame.Surface,
        players: list,
        credits: int,
        stage_mgr,
        boss,
        audio_track_name: str,
        ai_companions_enabled: bool,
        anim_time: float,
    ):
        ASSET_BANK.ensure_loaded()

        # Semi-transparent top arcade HUD bar
        top_bar = pygame.Surface((INTERNAL_WIDTH, 66), pygame.SRCALPHA)
        pygame.draw.rect(top_bar, (10, 8, 22, 215), (0, 0, INTERNAL_WIDTH, 66))
        pygame.draw.line(top_bar, COLOR_HUNMOON_GOLD, (0, 64), (INTERNAL_WIDTH, 64), 2)
        surface.blit(top_bar, (0, 0))

        slot_w = INTERNAL_WIDTH // 4
        blink = int(anim_time * 3.2) % 2 == 0

        for idx in range(4):
            p = players[idx]
            sx = idx * slot_w + 8
            sy = 7

            if p.active and p.state != "ko":
                # Portrait icon
                portrait = ASSET_BANK.portraits_hud.get(p.char_id)
                if portrait is not None:
                    surface.blit(portrait, (sx, sy + 2))
                pygame.draw.rect(surface, p.cfg["color_primary"], (sx, sy + 2, 46, 46), 2)

                # Name, Lives & Score
                tx = sx + 52
                tag = f"P{idx + 1}" if not p.is_ai else "AI"
                self.draw_text_outlined(
                    surface,
                    f"{tag} {p.cfg['name']} x{p.lives}",
                    self.font_xs,
                    p.cfg["color_secondary"],
                    (tx, sy),
                )
                self.draw_text_outlined(
                    surface,
                    f"{p.score:06d}",
                    self.font_xs,
                    COLOR_WHITE,
                    (sx + slot_w - 64, sy),
                )

                # HP Bar
                bar_w = slot_w - 66
                hp_ratio = max(0.0, min(1.0, p.hp / max(1, p.max_hp)))
                pygame.draw.rect(surface, (45, 20, 35), (tx, sy + 18, bar_w, 12), border_radius=3)
                hp_col = COLOR_HP_GREEN if hp_ratio > 0.35 else COLOR_HP_RED
                if hp_ratio > 0:
                    pygame.draw.rect(surface, hp_col, (tx, sy + 18, int(bar_w * hp_ratio), 12), border_radius=3)
                pygame.draw.rect(surface, COLOR_WHITE, (tx, sy + 18, bar_w, 12), 1, border_radius=3)

                # Hunmoon Special Rhythm Meter
                m_ratio = max(0.0, min(1.0, p.hunmoon_meter / p.max_meter))
                pygame.draw.rect(surface, (20, 28, 52), (tx, sy + 34, bar_w, 9), border_radius=3)
                m_col = COLOR_HUNMOON_GOLD if (p.hunmoon_meter >= 50 and blink) else COLOR_NEON_CYAN
                if m_ratio > 0:
                    pygame.draw.rect(surface, m_col, (tx, sy + 34, int(bar_w * m_ratio), 9), border_radius=3)
                pygame.draw.rect(surface, COLOR_HUNMOON_BLUE, (tx, sy + 34, bar_w, 9), 1, border_radius=3)

            elif p.active and p.state == "ko":
                # 10-Second Arcade Continue Countdown!
                sec = max(0, int(math.ceil(p.continue_timer)))
                self.draw_text_outlined(
                    surface,
                    f"P{idx + 1} CONTINUE? {sec}",
                    self.font_sm,
                    COLOR_WARNING if blink else COLOR_HUNMOON_GOLD,
                    (sx + slot_w // 2 - 8, sy + 18),
                    center=True,
                )
                sub_msg = "PRESS START!" if credits > 0 else "INSERT COIN (5/TAB)"
                self.draw_text_outlined(
                    surface,
                    sub_msg,
                    self.font_xs,
                    COLOR_WHITE,
                    (sx + slot_w // 2 - 8, sy + 40),
                    center=True,
                )
            else:
                # Inactive slot: Classic flashing INSERT COIN / PRESS START
                msg = f"P{idx + 1} PRESS START" if credits > 0 else f"P{idx + 1} INSERT COIN"
                col = COLOR_HUNMOON_GOLD if credits > 0 else COLOR_NEON_PINK
                if blink:
                    self.draw_text_outlined(
                        surface,
                        msg,
                        self.font_sm,
                        col,
                        (sx + slot_w // 2 - 8, sy + 24),
                        center=True,
                    )

        # Boss Health Bar at Bottom of Screen
        if boss is not None and boss.hp > 0:
            bw = 540
            bx = (INTERNAL_WIDTH - bw) // 2
            by = INTERNAL_HEIGHT - 56
            pygame.draw.rect(surface, (18, 10, 28), (bx - 6, by - 22, bw + 12, 44), border_radius=6)
            pygame.draw.rect(surface, COLOR_HUNMOON_GOLD, (bx - 6, by - 22, bw + 12, 44), 2, border_radius=6)
            self.draw_text_outlined(
                surface,
                f"{boss.cfg['name']} — {boss.cfg['subtitle']}",
                self.font_xs,
                COLOR_HUNMOON_GOLD,
                (INTERNAL_WIDTH // 2, by - 11),
                center=True,
            )
            ratio = max(0.0, min(1.0, boss.hp / max(1, boss.max_hp)))
            pygame.draw.rect(surface, (60, 15, 25), (bx, by, bw, 14), border_radius=4)
            pygame.draw.rect(surface, boss.cfg["color_primary"], (bx, by, int(bw * ratio), 14), border_radius=4)
            pygame.draw.rect(surface, COLOR_WHITE, (bx, by, bw, 14), 1, border_radius=4)

        # Flashing "GO! >>>" Arrow when a wave is cleared
        if stage_mgr.go_arrow_timer > 0 and blink:
            self.draw_text_outlined(
                surface,
                "GO! >>>",
                self.font_lg,
                COLOR_HUNMOON_GOLD,
                (INTERNAL_WIDTH - 110, 118),
                center=True,
            )

        # Boss Approaching Warning Banner
        if stage_mgr.boss_warning_timer > 0 and blink:
            self.draw_text_outlined(
                surface,
                "WARNING! SAJA CHALLENGER APPROACHING!",
                self.font_md,
                COLOR_WARNING,
                (INTERNAL_WIDTH // 2, 112),
                center=True,
            )

        # Bottom Arcade Status Strip (Song Title + Credits + Shortcuts)
        bot_y = INTERNAL_HEIGHT - 16
        self.draw_text_outlined(
            surface,
            f"♪ {audio_track_name}",
            self.font_xs,
            COLOR_NEON_CYAN,
            (12, bot_y - 6),
        )
        self.draw_text_outlined(
            surface,
            f"CREDITS: {credits:02d}  [INSERT COIN: 5/TAB | P1-P4 START: 1-4/ENTER | STAGE SKIP: F3]",
            self.font_xs,
            COLOR_HUNMOON_GOLD,
            (INTERNAL_WIDTH - 485, bot_y - 6),
        )

    def draw_title_screen(self, surface: pygame.Surface, credits: int, anim_time: float):
        """Render the Arcade Attract / Title Screen using the illustrated marquee artwork."""
        ASSET_BANK.ensure_loaded()
        if ASSET_BANK.marquee_surface is not None:
            surface.blit(ASSET_BANK.marquee_surface, (0, 0))
            # Subtle bottom vignette for crisp readability of arcade prompts
            vignette = pygame.Surface((INTERNAL_WIDTH, 145), pygame.SRCALPHA)
            pygame.draw.rect(vignette, (8, 6, 20, 195), (0, 0, INTERNAL_WIDTH, 145))
            pygame.draw.line(vignette, COLOR_HUNMOON_GOLD, (0, 0), (INTERNAL_WIDTH, 0), 2)
            surface.blit(vignette, (0, INTERNAL_HEIGHT - 145))
        else:
            surface.fill((18, 10, 34))
            self.draw_text_outlined(
                surface,
                "K-POP DEMON HUNTERS",
                self.font_xl,
                COLOR_NEON_PINK,
                (INTERNAL_WIDTH // 2, 160),
                center=True,
            )

        blink = int(anim_time * 3.0) % 2 == 0
        prompt = "PRESS 1P–4P START OR ENTER TO PLAY!" if credits > 0 else "INSERT COIN (PRESS 5 OR TAB)"
        if blink:
            self.draw_text_outlined(
                surface,
                prompt,
                self.font_md,
                COLOR_HUNMOON_GOLD if credits > 0 else COLOR_NEON_PINK,
                (INTERNAL_WIDTH // 2, INTERNAL_HEIGHT - 105),
                center=True,
            )

        self.draw_text_outlined(
            surface,
            f"ARCADE CREDITS: {credits:02d}   (PRESS 5 / TAB / SELECT TO INSERT COIN)",
            self.font_sm,
            COLOR_NEON_CYAN,
            (INTERNAL_WIDTH // 2, INTERNAL_HEIGHT - 68),
            center=True,
        )
        self.draw_text_outlined(
            surface,
            "CONTROLS: 8-WAY JOYSTICK / ARROWS / WASD  |  BTN1 (Z/J): ATTACK  |  BTN2 (X/K): JUMP  |  BTN3 (C/SPACE): HUNMOON SPECIAL",
            self.font_xs,
            COLOR_WHITE,
            (INTERNAL_WIDTH // 2, INTERNAL_HEIGHT - 34),
            center=True,
        )

    def draw_character_select(
        self,
        surface: pygame.Surface,
        selected_indices: list[int],
        joined_players: list[bool],
        locked_players: list[bool],
        ai_companions_enabled: bool,
        credits: int,
        countdown: float,
        anim_time: float,
    ):
        """Render the 4-Player Arcade Character Select Screen."""
        ASSET_BANK.ensure_loaded()
        surface.fill((16, 12, 34))

        # Neon stage grid lines
        for x in range(0, INTERNAL_WIDTH, 60):
            pygame.draw.line(surface, (32, 24, 62), (x, 0), (x, INTERNAL_HEIGHT), 1)

        self.draw_text_outlined(
            surface,
            "CHOOSE YOUR DEMON HUNTER!",
            self.font_lg,
            COLOR_HUNMOON_GOLD,
            (INTERNAL_WIDTH // 2, 36),
            center=True,
        )
        self.draw_text_outlined(
            surface,
            f"STARTING IN {int(math.ceil(countdown))}s  —  MOVE LEFT/RIGHT TO SELECT, PRESS ATTACK OR START TO LOCK IN!",
            self.font_xs,
            COLOR_NEON_CYAN,
            (INTERNAL_WIDTH // 2, 68),
            center=True,
        )

        card_w = 212
        card_h = 355
        gap = 20
        start_x = (INTERNAL_WIDTH - (card_w * 4 + gap * 3)) // 2
        card_y = 92

        for idx, cid in enumerate(CHARACTER_ORDER):
            cfg = CHARACTERS[cid]
            cx = start_x + idx * (card_w + gap)
            rect = pygame.Rect(cx, card_y, card_w, card_h)

            pygame.draw.rect(surface, (26, 22, 52), rect, border_radius=10)
            pygame.draw.rect(surface, cfg["color_primary"], rect, 3, border_radius=10)

            # High-res illustrated portrait
            port = ASSET_BANK.portraits_select.get(cid)
            if port is not None:
                surface.blit(port, (cx + (card_w - 136) // 2, card_y + 14))
                pygame.draw.rect(
                    surface,
                    cfg["color_secondary"],
                    (cx + (card_w - 136) // 2, card_y + 14, 136, 136),
                    2,
                )

            self.draw_text_outlined(
                surface,
                cfg["name"],
                self.font_md,
                cfg["color_primary"],
                (cx + card_w // 2, card_y + 168),
                center=True,
            )
            self.draw_text_outlined(
                surface,
                cfg["title"],
                self.font_xs,
                COLOR_HUNMOON_GOLD,
                (cx + card_w // 2, card_y + 192),
                center=True,
            )
            self.draw_text_outlined(
                surface,
                cfg["weapon_name"],
                self.font_xs,
                COLOR_WHITE,
                (cx + card_w // 2, card_y + 216),
                center=True,
            )

            # Stat bars
            stats = [
                ("POWER", cfg["attack_damage"][-1] / 42.0),
                ("SPEED", cfg["speed"] / 260.0),
                ("REACH", cfg["attack_reach"] / 110.0),
            ]
            for s_i, (s_label, s_val) in enumerate(stats):
                sy = card_y + 240 + s_i * 22
                self.draw_text_outlined(surface, s_label, self.font_xs, COLOR_NEON_CYAN, (cx + 14, sy))
                bx = cx + 74
                bw = card_w - 88
                pygame.draw.rect(surface, (14, 12, 26), (bx, sy + 3, bw, 10), border_radius=3)
                pygame.draw.rect(
                    surface,
                    cfg["color_secondary"],
                    (bx, sy + 3, int(bw * min(1.0, s_val)), 10),
                    border_radius=3,
                )

            # Show which player cursors are currently on this character card
            p_badges = []
            for p_i in range(4):
                if joined_players[p_i] and selected_indices[p_i] == idx:
                    status = "READY!" if locked_players[p_i] else f"P{p_i + 1}"
                    p_badges.append((p_i, status))

            for b_idx, (p_i, status_txt) in enumerate(p_badges):
                tag_cols = [COLOR_NEON_CYAN, COLOR_NEON_PINK, COLOR_HUNMOON_GOLD, COLOR_HP_GREEN]
                badge_rect = pygame.Rect(cx + 12 + b_idx * 48, card_y + card_h - 38, 44, 26)
                pygame.draw.rect(surface, tag_cols[p_i], badge_rect, border_radius=5)
                pygame.draw.rect(surface, COLOR_BLACK, badge_rect, 2, border_radius=5)
                self.draw_text_outlined(
                    surface,
                    status_txt,
                    self.font_xs,
                    COLOR_WHITE,
                    badge_rect.center,
                    center=True,
                )

        self.draw_text_outlined(
            surface,
            f"P1–P4 PRESS START (1–4) TO JOIN!   |   ARCADE CREDITS: {credits:02d} (PRESS 5/TAB TO INSERT COIN)",
            self.font_sm,
            COLOR_HUNMOON_GOLD,
            (INTERNAL_WIDTH // 2, INTERNAL_HEIGHT - 36),
            center=True,
        )
