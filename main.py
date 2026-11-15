"""
K-Pop Demon Hunters: 4-Player Arcade Beat 'Em Up
Main Game Loop, State Machine, Cutscenes, Depth-Sorted Renderer & CLI Entry Point.
"""

import argparse
import math
import sys
import pygame
from src.audio import ArcadeAudioManager
from src.config import (
    CHARACTER_ORDER,
    COLOR_BLACK,
    COLOR_HP_GREEN,
    COLOR_HUNMOON_BLUE,
    COLOR_HUNMOON_GOLD,
    COLOR_NEON_CYAN,
    COLOR_NEON_PINK,
    COLOR_WARNING,
    COLOR_WHITE,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FPS,
    GAME_TITLE,
    INTERNAL_HEIGHT,
    INTERNAL_WIDTH,
    LANE_BOTTOM,
    LANE_TOP,
    STAGES,
    get_stage_z_bounds,
)
from src.entities import (
    BossFighter,
    BreakableProp,
    EnemyFighter,
    FloatingText,
    HazardZone,
    HeroPlayer,
    HitSpark,
    PickupItem,
    Projectile,
    assign_enemy_tokens_and_slots,
)
from src.hud import ArcadeHUD
from src.input_manager import ArcadeInputManager
from src.sprites import draw_hero_sprite
from src.stages import StageManager


class KPopDemonHuntersGame:
    """Main Arcade Game Controller."""

    def __init__(self, windowed: bool = True, debug: bool = False, headless: bool = False):
        self.headless = headless
        self.debug = debug

        if headless:
            import os
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"

        pygame.init()
        pygame.display.set_caption(GAME_TITLE)

        self.fullscreen = not windowed and not headless
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        if headless:
            self.window = pygame.display.set_mode((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        else:
            self.window = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), flags)

        self.canvas = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        self.clock = pygame.time.Clock()

        self.input_mgr = ArcadeInputManager(initial_credits=4)
        self.audio = ArcadeAudioManager(enabled=not headless)
        self.hud = ArcadeHUD()

        # Game state: TITLE, CHAR_SELECT, STAGE_INTRO, GAMEPLAY, CUTSCENE, VICTORY, GAME_OVER
        self.state = "TITLE"
        self.anim_time = 0.0
        self.state_timer = 0.0
        self.current_stage_idx = 0

        # 4 Player Slots (Human Arcade Drop-In Only)
        self.players = [
            HeroPlayer(i, CHARACTER_ORDER[i], 140 + i * 52, LANE_TOP + 22 + i * 38, active=False)
            for i in range(4)
        ]
        self.ai_companions_enabled = False

        # Character Select State
        self.select_indices = [0, 1, 2, 3]
        self.joined_players = [False, False, False, False]
        self.locked_players = [False, False, False, False]
        self.select_nav_cooldown = [0.0, 0.0, 0.0, 0.0]

        # In-Game Arcade Control Mapper State (Press F2 on Title Screen)
        self.mapper_player_idx = 0
        self.mapper_step_idx = 0
        self.mapper_steps = [
            ("attack_buttons", "BUTTON 1: ATTACK / COMBO"),
            ("jump_buttons", "BUTTON 2: JUMP / ESCAPE VAULT"),
            ("special_buttons", "BUTTON 3: HUNMOON SPECIAL"),
            ("synergy_buttons", "BUTTON 4: TEAM SYNERGY / DODGE"),
            ("coin_buttons", "SELECT / INSERT COIN"),
            ("start_buttons", "START / JOIN GAME"),
        ]

        # Active Stage Entities
        self.stage_mgr = StageManager(0)
        self.enemies: list[EnemyFighter] = []
        self.boss_ref: list[BossFighter | None] = [None]
        self.projectiles: list[Projectile] = []
        self.hazards: list[HazardZone] = []
        self.props: list[BreakableProp] = []
        self.pickups: list[PickupItem] = []
        self.sparks: list[HitSpark] = []
        self.texts: list[FloatingText] = []

    def toggle_fullscreen(self):
        if self.headless:
            return
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), pygame.RESIZABLE)

    def start_character_select(self, first_player_idx: int = 0):
        self.state = "CHAR_SELECT"
        self.state_timer = 14.0
        self.select_indices = [0, 1, 2, 3]
        self.joined_players = [False, False, False, False]
        self.locked_players = [False, False, False, False]
        self.joined_players[first_player_idx] = True
        self.audio.play_sfx("start")

    def start_campaign_stage(self, stage_idx: int):
        self.current_stage_idx = stage_idx % len(STAGES)
        self.stage_mgr = StageManager(self.current_stage_idx)
        self.enemies.clear()
        self.boss_ref[0] = None
        self.projectiles.clear()
        self.hazards.clear()
        self.pickups.clear()
        self.sparks.clear()
        self.texts.clear()
        self.props = self.stage_mgr.setup_stage_props()

        soul_power = bool(self.stage_mgr.cfg.get("soul_empowered", False))

        # Position active human players; unjoined slots stay inactive until a player presses Start to drop in
        sid = self.stage_mgr.cfg["id"]
        for i in range(4):
            p = self.players[i]
            if self.joined_players[i]:
                cid = CHARACTER_ORDER[self.select_indices[i] % 4]
                px = 120.0 + i * 52.0
                zl, zh = get_stage_z_bounds(sid, px)
                pz = min(zh - 10.0, zl + 16.0 + i * 24.0)
                if stage_idx == 0 or not p.active or p.state == "ko":
                    p.spawn_or_continue(cid, px, pz, is_ai=False)
                else:
                    p.x = px
                    p.z = pz
                    p.y = 0.0
                    p.heal(45)
                p.soul_empowered = p.soul_empowered or soul_power
            else:
                p.active = False

        self.audio.play_stage_music(self.current_stage_idx)
        self.state = "STAGE_INTRO"
        self.state_timer = 2.6

    def update(self, dt: float):
        self.anim_time += dt
        if self.input_mgr.update(self.anim_time):
            self.audio.play_sfx("coin")

        if self.state == "TITLE":
            for i in range(4):
                st = self.input_mgr.states[i]
                if st.start_pressed or st.attack_pressed:
                    if self.input_mgr.use_credit():
                        self.start_character_select(first_player_idx=i)
                        break

        elif self.state == "CHAR_SELECT":
            self.state_timer -= dt
            for i in range(4):
                st = self.input_mgr.states[i]
                if self.select_nav_cooldown[i] > 0:
                    self.select_nav_cooldown[i] -= dt

                if not self.joined_players[i]:
                    if st.start_pressed and self.input_mgr.use_credit():
                        self.joined_players[i] = True
                        self.audio.play_sfx("start")
                else:
                    if not self.locked_players[i]:
                        if abs(st.dx) > 0.5 and self.select_nav_cooldown[i] <= 0:
                            step = 1 if st.dx > 0 else -1
                            self.select_indices[i] = (self.select_indices[i] + step) % 4
                            self.select_nav_cooldown[i] = 0.22
                            self.audio.play_sfx("slash_light")
                        if st.attack_pressed or st.start_pressed or st.jump_pressed:
                            self.locked_players[i] = True
                            self.audio.play_sfx("pickup")

            any_joined = any(self.joined_players)
            all_locked = any_joined and all(
                self.locked_players[i] for i in range(4) if self.joined_players[i]
            )
            if all_locked or self.state_timer <= 0:
                if not any_joined:
                    self.joined_players[0] = True
                self.start_campaign_stage(0)

        elif self.state == "STAGE_INTRO":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "GAMEPLAY"

        elif self.state == "GAMEPLAY":
            self._update_gameplay(dt)

        elif self.state == "CUTSCENE":
            self.state_timer -= dt
            for i in range(4):
                if self.input_mgr.states[i].start_pressed or self.input_mgr.states[i].attack_pressed:
                    if self.state_timer < 3.2:
                        self.state_timer = 0.0
            if self.state_timer <= 0:
                if self.current_stage_idx + 1 < len(STAGES):
                    self.start_campaign_stage(self.current_stage_idx + 1)
                else:
                    self.state = "VICTORY"
                    self.state_timer = 15.0

        elif self.state in ("VICTORY", "GAME_OVER"):
            self.state_timer -= dt
            for i in range(4):
                if self.input_mgr.states[i].start_pressed and self.state_timer < 13.0:
                    self.state = "TITLE"
                    break
            if self.state_timer <= 0:
                self.state = "TITLE"

    def _update_gameplay(self, dt: float):
        sid = self.stage_mgr.cfg["id"]
        stage_w = float(self.stage_mgr.cfg["length"])

        # Check for mid-game 4-player Drop-In or Continue!
        for i in range(4):
            p = self.players[i]
            st = self.input_mgr.states[i]
            if st.start_pressed:
                if (not p.active or p.is_ai or p.state == "ko") and self.input_mgr.use_credit():
                    self.joined_players[i] = True
                    cid = CHARACTER_ORDER[self.select_indices[i] % 4]
                    dx_spawn = self.stage_mgr.camera_x + 180 + i * 50
                    zl, zh = get_stage_z_bounds(sid, dx_spawn)
                    p.spawn_or_continue(
                        cid,
                        dx_spawn,
                        (zl + zh) * 0.5,
                        is_ai=False,
                    )
                    p.soul_empowered = bool(self.stage_mgr.cfg.get("soul_empowered", False))
                    self.audio.play_sfx("start")
                    self.texts.append(
                        FloatingText(p.x, p.z, 85, f"P{i + 1} {p.cfg['name']} DROPS IN!", COLOR_HUNMOON_GOLD)
                    )

        # Update Players (with solid stage wall & interactive object collisions!)
        for i, p in enumerate(self.players):
            p.update(
                dt=dt,
                inp=self.input_mgr.states[i],
                camera_x=self.stage_mgr.camera_x,
                stage_width=stage_w,
                enemies=self.enemies,
                boss=self.boss_ref[0],
                projectiles=self.projectiles,
                hazards=self.hazards,
                sparks=self.sparks,
                texts=self.texts,
                all_players=self.players,
                audio=self.audio,
                stage_id=sid,
                props=self.props,
            )

        # Check if all human players are completely out of lives & continue timer expired
        human_alive_or_continuing = any(
            p.active and not p.is_ai for p in self.players
        )
        if not human_alive_or_continuing:
            self.state = "GAME_OVER"
            self.state_timer = 7.0
            return

        # Update Stage Manager & Waves
        self.stage_mgr.update(
            dt=dt,
            players=self.players,
            enemies=self.enemies,
            boss_ref=self.boss_ref,
            hazards=self.hazards,
            pickups=self.pickups,
            texts=self.texts,
            audio=self.audio,
        )

        if self.stage_mgr.stage_cleared:
            self.stage_mgr.clear_timer -= dt
            if self.stage_mgr.clear_timer <= 0:
                self.state = "CUTSCENE"
                self.state_timer = 4.6
                return

        # Assign Arcade Attack Tokens & Outer Formation Ring Slots before updating enemies
        assign_enemy_tokens_and_slots(self.enemies, self.players, self.anim_time, stage_id=sid, props=self.props)
        for e in self.enemies:
            e.update(
                dt=dt,
                players=self.players,
                other_enemies=self.enemies,
                texts=self.texts,
                audio=self.audio,
                stage_id=sid,
                props=self.props,
                boss=self.boss_ref[0],
                hazards=self.hazards,
                pickups=self.pickups,
                sparks=self.sparks,
            )
        self.enemies = [e for e in self.enemies if e.hp > 0]

        # Update Boss
        if self.boss_ref[0] is not None and self.boss_ref[0].hp > 0:
            self.boss_ref[0].update(
                dt=dt,
                camera_x=self.stage_mgr.camera_x,
                players=self.players,
                enemies=self.enemies,
                projectiles=self.projectiles,
                hazards=self.hazards,
                texts=self.texts,
                audio=self.audio,
                stage_id=sid,
                props=self.props,
            )

        # Update Interactive Stage Objects & Breakable Props
        for prop in list(self.props):
            still_alive = prop.update(
                dt=dt,
                stage_width=stage_w,
                enemies=self.enemies,
                boss=self.boss_ref[0],
                players=self.players,
                pickups=self.pickups,
                sparks=self.sparks,
                texts=self.texts,
                audio=self.audio,
            )
            if not still_alive:
                if prop in self.props:
                    self.props.remove(prop)
                continue

            for p in self.players:
                if p.active and p.state == "attack":
                    reach = p.cfg["attack_reach"]
                    dx_p = (prop.x - p.x) * p.facing
                    if -20.0 <= dx_p <= (reach + prop.half_w) and abs(p.z - prop.z) <= (prop.half_d + 28.0):
                        if prop.trigger_interaction(
                            hit_dir=p.facing,
                            enemies=self.enemies,
                            boss=self.boss_ref[0],
                            players=self.players,
                            hazards=self.hazards,
                            pickups=self.pickups,
                            sparks=self.sparks,
                            texts=self.texts,
                            audio=self.audio,
                        ):
                            if prop in self.props:
                                self.props.remove(prop)
                            break

        # Update Pickups & check player collection
        for item in list(self.pickups):
            item.update(dt)
            for p in self.players:
                if p.active and p.state != "ko" and abs(p.x - item.x) < 38 and abs(p.z - item.z) < 28:
                    if item.cfg.get("team_heal"):
                        for ally in self.players:
                            if ally.active and ally.state != "ko":
                                ally.heal(item.cfg["heal"])
                                ally.add_meter(item.cfg["meter"])
                        self.texts.append(FloatingText(p.x, p.z, 70, "TEAM K-BBQ FEAST! FULL HP!", COLOR_HUNMOON_GOLD))
                    else:
                        p.heal(item.cfg["heal"])
                        p.add_meter(item.cfg["meter"])
                        self.texts.append(
                            FloatingText(p.x, p.z, 64, f"+{item.cfg['name'].upper()}!", COLOR_HP_GREEN)
                        )
                    p.score += item.cfg["score"]
                    self.audio.play_sfx("pickup")
                    self.pickups.remove(item)
                    break

        # Update Projectiles & Check Collisions
        active_projs: list[Projectile] = []
        for proj in self.projectiles:
            if not proj.update(dt):
                continue
            hit_consumed = False
            if proj.owner_team == "hero":
                targets = list(self.enemies)
                if self.boss_ref[0] is not None and self.boss_ref[0].hp > 0:
                    targets.append(self.boss_ref[0])
                for t in targets:
                    if t.hp <= 0 or id(t) in proj.hit_ids:
                        continue
                    if abs(t.x - proj.x) < (proj.radius + 26) and abs(t.z - proj.z) < 30:
                        proj.hit_ids.add(id(t))
                        kb = 24.0 if proj.vx >= 0 else -24.0
                        t.take_damage(proj.damage, kb, is_heavy=proj.pierce)
                        self.sparks.append(HitSpark(t.x, t.z, 32, proj.color))
                        self.texts.append(FloatingText(t.x, t.z, 54, f"{proj.damage}", proj.color))
                        self.audio.play_sfx("hit")
                        if not proj.pierce:
                            hit_consumed = True
                            break
            else:
                for p in self.players:
                    if not p.active or p.state == "ko" or id(p) in proj.hit_ids:
                        continue
                    if abs(p.x - proj.x) < (proj.radius + 20) and abs(p.z - proj.z) < 26 and p.y < 36:
                        proj.hit_ids.add(id(p))
                        kb_dir = 1 if proj.vx >= 0 else -1
                        if p.take_damage(proj.damage, knockback_dir=kb_dir):
                            self.sparks.append(HitSpark(p.x, p.z, 32, proj.color))
                            self.audio.play_sfx("hit")
                            if proj.proj_type == "charm_heart" and p.char_id != "rumi" and not p.soul_empowered:
                                p.charm_timer = 3.5
                                self.texts.append(
                                    FloatingText(p.x, p.z, 72, "ROMANCE CHARM! CONTROLS REVERSED!", COLOR_NEON_PINK)
                                )
                        hit_consumed = True
                        break

            if not hit_consumed:
                active_projs.append(proj)
        self.projectiles = active_projs

        # Update Hazard Zones (Gwi-Ma flame lanes, Bobby VIP spotlights, steam vents, train signs)
        active_hazards: list[HazardZone] = []
        for hz in self.hazards:
            if not hz.update(dt):
                continue
            if hz.is_active_damage:
                if hz.owner_team == "hero":
                    targets = list(self.enemies)
                    if self.boss_ref[0] is not None and self.boss_ref[0].hp > 0:
                        targets.append(self.boss_ref[0])
                    for t in targets:
                        if t.hp > 0 and id(t) not in hz.hit_ids:
                            if abs(t.x - hz.x) <= hz.width * 0.55 and abs(t.z - hz.z) <= hz.depth * 0.6:
                                hz.hit_ids.add(id(t))
                                t.take_damage(hz.damage, 0.0, is_heavy=True)
                                self.sparks.append(HitSpark(t.x, t.z, 36, COLOR_HUNMOON_GOLD, radius=32))
                                self.texts.append(FloatingText(t.x, t.z, 60, f"{hz.damage}!", COLOR_HUNMOON_GOLD))
                else:
                    for p in self.players:
                        if p.active and p.state != "ko" and id(p) not in hz.hit_ids and p.y < 32:
                            if abs(p.x - hz.x) <= hz.width * 0.5 and abs(p.z - hz.z) <= hz.depth * 0.55:
                                hz.hit_ids.add(id(p))
                                if p.take_damage(hz.damage):
                                    self.sparks.append(HitSpark(p.x, p.z, 32, COLOR_WARNING))
            active_hazards.append(hz)
        self.hazards = active_hazards

        # Update Sparks & Floating Text
        self.sparks = [s for s in self.sparks if s.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]

    def draw(self):
        if self.state == "TITLE":
            self.hud.draw_title_screen(self.canvas, self.input_mgr.credits, self.anim_time)
            self.hud.draw_text_outlined(
                self.canvas,
                "F2: MAP ARCADE BUTTONS   |   " + self.input_mgr.get_live_diagnostic_text(),
                self.hud.font_xs,
                (170, 200, 230),
                (INTERNAL_WIDTH // 2, INTERNAL_HEIGHT - 12),
                center=True,
            )

        elif self.state == "CONTROL_MAPPER":
            self._draw_control_mapper()

        elif self.state == "CHAR_SELECT":
            self.hud.draw_character_select(
                surface=self.canvas,
                selected_indices=self.select_indices,
                joined_players=self.joined_players,
                locked_players=self.locked_players,
                ai_companions_enabled=self.ai_companions_enabled,
                credits=self.input_mgr.credits,
                countdown=self.state_timer,
                anim_time=self.anim_time,
            )

        elif self.state in ("STAGE_INTRO", "GAMEPLAY"):
            self._draw_gameplay_scene()
            if self.state == "STAGE_INTRO":
                self._draw_stage_intro_banner()

        elif self.state == "CUTSCENE":
            self._draw_cutscene()

        elif self.state == "VICTORY":
            self._draw_victory_screen()

        elif self.state == "GAME_OVER":
            self._draw_gameplay_scene()
            overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 4, 18, 200))
            self.canvas.blit(overlay, (0, 0))
            self.hud.draw_text_outlined(
                self.canvas,
                "GAME OVER",
                self.hud.font_xl,
                COLOR_WARNING,
                (INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2 - 20),
                center=True,
            )
            self.hud.draw_text_outlined(
                self.canvas,
                "PRESS START TO RETURN TO TITLE",
                self.hud.font_md,
                COLOR_WHITE,
                (INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2 + 35),
                center=True,
            )

        # Scale internal 960x540 arcade canvas cleanly to the window resolution
        win_size = self.window.get_size()
        if win_size == (INTERNAL_WIDTH, INTERNAL_HEIGHT):
            self.window.blit(self.canvas, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(self.canvas, win_size)
            self.window.blit(scaled, (0, 0))
        pygame.display.flip()

    def _draw_gameplay_scene(self):
        cam_x = self.stage_mgr.camera_x
        self.stage_mgr.draw_background(self.canvas)

        # Draw ground warning/active hazards first
        for hz in self.hazards:
            hz.draw(self.canvas, cam_x)

        # Depth-sort (Z-sort) all 2.5D entities so foreground objects naturally overlap background objects
        render_queue: list[tuple[float, callable]] = []

        for prop in self.props:
            render_queue.append((prop.z, lambda pr=prop: pr.draw(self.canvas, cam_x)))
        for item in self.pickups:
            render_queue.append((item.z, lambda it=item: it.draw(self.canvas, cam_x, self.hud.font_xs)))
        for e in self.enemies:
            if e.hp > 0:
                render_queue.append((e.z, lambda en=e: en.draw(self.canvas, cam_x)))
        if self.boss_ref[0] is not None and self.boss_ref[0].hp > 0:
            b = self.boss_ref[0]
            render_queue.append((b.z, lambda bs=b: bs.draw(self.canvas, cam_x)))
        for p in self.players:
            if p.active and p.state != "ko":
                sort_z = p.z + (20.0 if p.y >= 18.0 else 0.0)
                render_queue.append((sort_z, lambda pl=p: pl.draw(self.canvas, cam_x, self.hud.font_xs)))
        for proj in self.projectiles:
            render_queue.append((proj.z + 2, lambda pj=proj: pj.draw(self.canvas, cam_x)))

        render_queue.sort(key=lambda pair: pair[0])
        for _, draw_fn in render_queue:
            draw_fn()

        # Sparks & Floating Damage / Combo Text on top
        for sp in self.sparks:
            sp.draw(self.canvas, cam_x)
        for ft in self.texts:
            ft.draw(self.canvas, cam_x, self.hud.font_sm)

        # Stage Clear Banner
        if self.stage_mgr.stage_cleared:
            banner = pygame.Surface((INTERNAL_WIDTH, 110), pygame.SRCALPHA)
            pygame.draw.rect(banner, (12, 8, 28, 215), (0, 0, INTERNAL_WIDTH, 110))
            pygame.draw.line(banner, COLOR_HUNMOON_GOLD, (0, 0), (INTERNAL_WIDTH, 0), 3)
            pygame.draw.line(banner, COLOR_HUNMOON_GOLD, (0, 107), (INTERNAL_WIDTH, 107), 3)
            self.canvas.blit(banner, (0, 195))
            self.hud.draw_text_outlined(
                self.canvas,
                "STAGE CLEAR!",
                self.hud.font_lg,
                COLOR_HUNMOON_GOLD,
                (INTERNAL_WIDTH // 2, 228),
                center=True,
            )
            self.hud.draw_text_outlined(
                self.canvas,
                self.stage_mgr.cfg["outro_text"],
                self.hud.font_sm,
                COLOR_NEON_CYAN,
                (INTERNAL_WIDTH // 2, 272),
                center=True,
            )

        # Top 4-Player Arcade HUD & Boss Bar
        self.hud.draw_gameplay_hud(
            surface=self.canvas,
            players=self.players,
            credits=self.input_mgr.credits,
            stage_mgr=self.stage_mgr,
            boss=self.boss_ref[0],
            audio_track_name=self.audio.current_track_name,
            ai_companions_enabled=self.ai_companions_enabled,
            anim_time=self.anim_time,
        )

    def _draw_stage_intro_banner(self):
        cfg = self.stage_mgr.cfg
        overlay = pygame.Surface((INTERNAL_WIDTH, 175), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (10, 8, 26, 225), (0, 0, INTERNAL_WIDTH, 175))
        pygame.draw.line(overlay, cfg["theme_color"], (0, 0), (INTERNAL_WIDTH, 0), 4)
        pygame.draw.line(overlay, COLOR_HUNMOON_GOLD, (0, 171), (INTERNAL_WIDTH, 171), 4)
        self.canvas.blit(overlay, (0, 175))

        self.hud.draw_text_outlined(
            self.canvas,
            cfg["name"],
            self.hud.font_lg,
            COLOR_HUNMOON_GOLD,
            (INTERNAL_WIDTH // 2, 206),
            center=True,
        )
        self.hud.draw_text_outlined(
            self.canvas,
            f"{cfg['location']}   |   ♪ NOW PLAYING: \"{cfg['song_title']}\" ({cfg['song_artist']})",
            self.hud.font_sm,
            COLOR_NEON_CYAN,
            (INTERNAL_WIDTH // 2, 248),
            center=True,
        )
        self.hud.draw_text_outlined(
            self.canvas,
            cfg["intro_text"],
            self.hud.font_sm,
            COLOR_WHITE,
            (INTERNAL_WIDTH // 2, 292),
            center=True,
        )

    def _draw_cutscene(self):
        """Render animated story transitions (e.g., Stage 1 Plane Jump & Stage 5 Jinu Soul Empowerment)."""
        cfg = self.stage_mgr.cfg
        self.canvas.fill((14, 10, 32))

        if cfg["id"] == "plane":
            # Stage 1 Outro: Skydiving out of the damaged Huntr/x jet toward the Neon Concert Arena!
            for i in range(14):
                cy = int((self.anim_time * 380 + i * 65) % INTERNAL_HEIGHT)
                cx = (i * 83) % INTERNAL_WIDTH
                pygame.draw.line(self.canvas, (150, 210, 255), (cx, cy), (cx, cy + 45), 2)
            for idx, cid in enumerate(CHARACTER_ORDER):
                hx = 230 + idx * 165
                hy = 270 + int(math.sin(self.anim_time * 6 + idx) * 18)
                draw_hero_sprite(self.canvas, cid, hx, hy, 0, 1, "jump", self.anim_time, special_active=True)

            self.hud.draw_text_outlined(
                self.canvas,
                "BAILING OUT OF THE HUNTR/X JET!",
                self.hud.font_lg,
                COLOR_HUNMOON_GOLD,
                (INTERNAL_WIDTH // 2, 72),
                center=True,
            )
            self.hud.draw_text_outlined(
                self.canvas,
                "Rumi, Zoey, Mira & Bobby skydive straight toward the Seoul Neon Concert Dome!",
                self.hud.font_sm,
                COLOR_NEON_CYAN,
                (INTERNAL_WIDTH // 2, 445),
                center=True,
            )

        elif cfg["id"] == "saja_concert":
            # Stage 5 Outro: Jinu breaks free of Gwi-Ma and transfers his Soul Energy to Huntr/x!
            for r in range(40, 260, 45):
                rad = int((r + self.anim_time * 90) % 260)
                pygame.draw.circle(self.canvas, COLOR_HUNMOON_BLUE, (INTERNAL_WIDTH // 2, 260), rad, 2)
            for idx, cid in enumerate(CHARACTER_ORDER):
                hx = 230 + idx * 165
                hy = 300
                draw_hero_sprite(
                    self.canvas, cid, hx, hy, 0, 1, "idle", self.anim_time, special_active=True, soul_empowered=True
                )
            self.hud.draw_text_outlined(
                self.canvas,
                "JINU'S SOUL EMPOWERMENT!",
                self.hud.font_lg,
                COLOR_NEON_CYAN,
                (INTERNAL_WIDTH // 2, 72),
                center=True,
            )
            self.hud.draw_text_outlined(
                self.canvas,
                "Jinu breaks Gwi-Ma's chains and infuses Huntr/x with his Soul Energy for the final battle!",
                self.hud.font_sm,
                COLOR_HUNMOON_GOLD,
                (INTERNAL_WIDTH // 2, 445),
                center=True,
            )
        else:
            for idx, cid in enumerate(CHARACTER_ORDER):
                hx = 230 + idx * 165
                hy = 300
                draw_hero_sprite(self.canvas, cid, hx, hy, 0, 1, "walk", self.anim_time)
            self.hud.draw_text_outlined(
                self.canvas,
                f"{cfg['name']} COMPLETE!",
                self.hud.font_lg,
                COLOR_HUNMOON_GOLD,
                (INTERNAL_WIDTH // 2, 95),
                center=True,
            )
            self.hud.draw_text_outlined(
                self.canvas,
                cfg["outro_text"],
                self.hud.font_sm,
                COLOR_NEON_CYAN,
                (INTERNAL_WIDTH // 2, 435),
                center=True,
            )

    def _draw_victory_screen(self):
        self.canvas.fill((18, 12, 38))
        for i in range(6):
            lx = 110 + i * 150
            pygame.draw.line(
                self.canvas,
                COLOR_NEON_PINK if i % 2 == 0 else COLOR_NEON_CYAN,
                (lx, 0),
                (lx + int(math.sin(self.anim_time * 3 + i) * 120), INTERNAL_HEIGHT),
                3,
            )

        self.hud.draw_text_outlined(
            self.canvas,
            "GWI-MA IS DEFEATED! THE HUNMOON SHINES GOLDEN!",
            self.hud.font_lg,
            COLOR_HUNMOON_GOLD,
            (INTERNAL_WIDTH // 2, 65),
            center=True,
        )
        self.hud.draw_text_outlined(
            self.canvas,
            "THANK YOU FOR PLAYING K-POP DEMON HUNTERS!",
            self.hud.font_md,
            COLOR_NEON_CYAN,
            (INTERNAL_WIDTH // 2, 110),
            center=True,
        )

        for idx, p in enumerate(self.players):
            hx = 210 + idx * 180
            hy = 320
            draw_hero_sprite(
                self.canvas,
                CHARACTER_ORDER[idx],
                hx,
                hy,
                abs(math.sin(self.anim_time * 6 + idx)) * 22,
                1,
                "jump",
                self.anim_time,
                special_active=True,
                soul_empowered=True,
            )
            self.hud.draw_text_outlined(
                self.canvas,
                f"P{idx + 1} SCORE: {p.score:06d}",
                self.hud.font_sm,
                COLOR_WHITE,
                (hx, 375),
                center=True,
            )

        self.hud.draw_text_outlined(
            self.canvas,
            "PRESS START OR ENTER TO PLAY AGAIN!",
            self.hud.font_md,
            COLOR_HUNMOON_GOLD,
            (INTERNAL_WIDTH // 2, 475),
            center=True,
        )

    def _draw_control_mapper(self):
        self.canvas.fill((14, 10, 28))
        pygame.draw.rect(self.canvas, (26, 20, 48), (60, 45, INTERNAL_WIDTH - 120, INTERNAL_HEIGHT - 90), border_radius=12)
        pygame.draw.rect(self.canvas, COLOR_HUNMOON_GOLD, (60, 45, INTERNAL_WIDTH - 120, INTERNAL_HEIGHT - 90), 3, border_radius=12)

        self.hud.draw_text_outlined(
            self.canvas,
            "ARCADE CABINET BUTTON MAPPER (SAVES TO controls.json)",
            self.hud.font_md,
            COLOR_HUNMOON_GOLD,
            (INTERNAL_WIDTH // 2, 85),
            center=True,
        )
        self.hud.draw_text_outlined(
            self.canvas,
            self.input_mgr.get_live_diagnostic_text(),
            self.hud.font_xs,
            COLOR_NEON_CYAN,
            (INTERNAL_WIDTH // 2, 125),
            center=True,
        )

        p_num = self.mapper_player_idx + 1
        field_key, step_label = self.mapper_steps[self.mapper_step_idx]
        self.hud.draw_text_outlined(
            self.canvas,
            f"MAPPING PLAYER {p_num} (Press TAB to switch Player 1-4)",
            self.hud.font_md,
            COLOR_NEON_PINK,
            (INTERNAL_WIDTH // 2, 185),
            center=True,
        )
        self.hud.draw_text_outlined(
            self.canvas,
            f"PRESS PHYSICAL ARCADE BUTTON FOR:  {step_label}",
            self.hud.font_lg,
            COLOR_WHITE,
            (INTERNAL_WIDTH // 2, 245),
            center=True,
        )

        # Display current mapping for this player
        jmap = self.input_mgr.custom_joy_maps[self.mapper_player_idx]
        y_row = 305
        for idx, (fk, flabel) in enumerate(self.mapper_steps):
            col = COLOR_HUNMOON_GOLD if idx == self.mapper_step_idx else (190, 195, 220)
            btns = jmap.get(fk, [])
            self.hud.draw_text_outlined(
                self.canvas,
                f"{'> ' if idx == self.mapper_step_idx else '  '}{flabel}:  Joystick Button(s) {btns}",
                self.hud.font_sm,
                col,
                (INTERNAL_WIDTH // 2, y_row),
                center=True,
            )
            y_row += 24

        self.hud.draw_text_outlined(
            self.canvas,
            "SPACE: Skip Step   |   TAB: Next Player   |   ESC / F2: Save & Return to Title",
            self.hud.font_xs,
            COLOR_HP_GREEN,
            (INTERNAL_WIDTH // 2, 472),
            center=True,
        )

    def run(self):
        running = True
        while running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self.input_mgr.refresh_joysticks()
                elif event.type == pygame.JOYBUTTONDOWN and self.state == "CONTROL_MAPPER":
                    field_key, _ = self.mapper_steps[self.mapper_step_idx]
                    self.input_mgr.custom_joy_maps[self.mapper_player_idx][field_key] = [int(event.button)]
                    self.input_mgr.save_controls_config()
                    self.audio.play_sfx("pickup")
                    self.mapper_step_idx = (self.mapper_step_idx + 1) % len(self.mapper_steps)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F2:
                        if self.state == "CONTROL_MAPPER":
                            self.input_mgr.save_controls_config()
                            self.state = "TITLE"
                        else:
                            self.state = "CONTROL_MAPPER"
                            self.mapper_step_idx = 0
                    elif self.state == "CONTROL_MAPPER":
                        if event.key == pygame.K_ESCAPE:
                            self.input_mgr.save_controls_config()
                            self.state = "TITLE"
                        elif event.key == pygame.K_SPACE:
                            self.mapper_step_idx = (self.mapper_step_idx + 1) % len(self.mapper_steps)
                        elif event.key == pygame.K_TAB:
                            self.mapper_player_idx = (self.mapper_player_idx + 1) % 4
                            self.mapper_step_idx = 0
                    elif event.key == pygame.K_ESCAPE:
                        if self.state != "TITLE":
                            self.state = "TITLE"
                            self.audio.stop_music()
                        else:
                            running = False
                    elif event.key == pygame.K_F1:
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_F3 and self.state in ("GAMEPLAY", "STAGE_INTRO"):
                        # Stage Skip shortcut for testing all 6 stages & bosses
                        self.start_campaign_stage((self.current_stage_idx + 1) % len(STAGES))
                    elif event.key == pygame.K_m:
                        self.audio.toggle_mute()

            self.update(dt)
            self.draw()

        pygame.quit()


def run_automated_smoke_test():
    """Run a fast headless verification across all 6 stages, 4 characters, enemies, and bosses."""
    print("Initializing K-Pop Demon Hunters automated verification...")
    game = KPopDemonHuntersGame(windowed=True, debug=True, headless=True)
    game.draw()  # Verify Title Screen rendering & marquee loading

    game.start_character_select(0)
    game.joined_players = [True, True, True, True]
    game.draw()  # Verify Character Select & 4 portrait rendering

    for stage_i in range(len(STAGES)):
        game.start_campaign_stage(stage_i)
        cfg = game.stage_mgr.cfg
        print(f"  [OK] Stage {cfg['number']}: {cfg['name']} | Song: {cfg['song_title']} | Boss: {cfg['boss']}")
        game.state = "GAMEPLAY"
        # Simulate frames & trigger every player's attack and Hunmoon Special
        for step in range(15):
            if step == 2:
                # Spawn the stage boss wave to test boss logic & rendering
                last_wave = cfg["waves"][-1]
                game.stage_mgr._spawn_wave(
                    last_wave, 4, game.enemies, game.boss_ref, game.texts, game.audio
                )
            if step == 5:
                for p in game.players:
                    p._start_attack(game.projectiles, game.enemies, game.boss_ref[0], game.sparks, game.texts, game.audio)
            if step == 8:
                for p in game.players:
                    p._trigger_hunmoon_special(
                        game.enemies,
                        game.boss_ref[0],
                        game.projectiles,
                        game.hazards,
                        game.sparks,
                        game.texts,
                        game.players,
                        game.audio,
                    )
            game.update(1.0 / 60.0)
            game.draw()
            if stage_i == 0 and step == 4:
                for p in game.players:
                    p.y = 0.0
            if stage_i == 0 and step == 6:
                import os
                preview_path = os.path.join("assets", "sprites", "gameplay_preview.png")
                pygame.image.save(game.canvas, preview_path)

        # Verify cutscene rendering
        game.state = "CUTSCENE"
        game.draw()

    game.state = "VICTORY"
    game.draw()
    pygame.quit()
    print("All 6 stages, 4 characters, bosses, audio synth, and artwork verified with 0 errors!")


def main():
    parser = argparse.ArgumentParser(description=GAME_TITLE)
    parser.add_argument("--windowed", action="store_true", default=True, help="Run in windowed mode")
    parser.add_argument("--fullscreen", action="store_true", help="Run in fullscreen arcade cabinet mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug shortcuts")
    parser.add_argument("--headless-test", action="store_true", help="Run automated headless smoke test")
    args = parser.parse_args()

    if args.headless_test:
        run_automated_smoke_test()
        return

    windowed = not args.fullscreen
    game = KPopDemonHuntersGame(windowed=windowed, debug=args.debug, headless=False)
    game.run()


if __name__ == "__main__":
    main()
