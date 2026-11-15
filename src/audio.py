"""
Arcade Sound & K-Pop Music Manager.
- Automatically loads user-supplied .mp3 / .ogg / .wav tracks from `assets/music/`
  for all 6 stages ("How It's Done", "Golden", "Free", "Takedown", "Your Idol", "What It Sounds Like").
- Generates built-in synthesized K-Pop arcade loops & crisp arcade sound effects
  in memory so the game has full music and SFX out of the box!
"""

import array
import math
import os
import pygame
from src.config import MUSIC_DIR, STAGES


class ArcadeAudioManager:
    """Manages stage music streaming and synthesized arcade sound effects."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.sample_rate = 22050
        self.sfx: dict[str, pygame.mixer.Sound] = {}
        self.synth_tracks: dict[str, pygame.mixer.Sound] = {}
        self.current_synth_channel: pygame.mixer.Channel | None = None
        self.current_track_name: str = ""
        self.using_external_file: bool = False
        self.muted: bool = False

        os.makedirs(MUSIC_DIR, exist_ok=True)

        if self.enabled:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=1024)
                pygame.mixer.set_num_channels(16)
                self._generate_sfx()
                self._generate_kpop_synth_loops()
            except pygame.error:
                self.enabled = False

    def _make_sound(self, samples: list[int]) -> pygame.mixer.Sound:
        buf = array.array("h", [max(-32767, min(32767, int(s))) for s in samples])
        return pygame.mixer.Sound(buffer=buf)

    def _generate_sfx(self):
        """Synthesize classic arcade sound effects in memory."""
        sr = self.sample_rate

        # 1. Coin Insert Chime (Classic two-tone arcade coin ding: B5 -> E6)
        coin_samples = []
        for i in range(int(sr * 0.38)):
            t = i / sr
            freq = 987.77 if t < 0.09 else 1318.51
            env = math.exp(-t * 7.5)
            val = math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(2 * math.pi * freq * 2 * t)
            coin_samples.append(int(val * env * 14000))
        self.sfx["coin"] = self._make_sound(coin_samples)

        # 2. Player Join / Start Arpeggio
        start_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50]
        for i in range(int(sr * 0.44)):
            t = i / sr
            idx = min(3, int(t / 0.11))
            freq = notes[idx]
            env = 1.0 - (t % 0.11) * 5.0
            val = math.sin(2 * math.pi * freq * t) + 0.5 * (1 if math.sin(2 * math.pi * freq * t) > 0 else -1)
            start_samples.append(int(val * max(0.1, env) * 9500))
        self.sfx["start"] = self._make_sound(start_samples)

        # 3. Light Weapon Slash / Whoosh
        slash_samples = []
        for i in range(int(sr * 0.13)):
            t = i / sr
            freq = 680.0 - (t / 0.13) * 460.0
            noise = math.sin(i * 1.7) * math.cos(i * 0.37)
            env = (1.0 - t / 0.13) ** 1.4
            val = 0.6 * math.sin(2 * math.pi * freq * t) + 0.4 * noise
            slash_samples.append(int(val * env * 11000))
        self.sfx["slash_light"] = self._make_sound(slash_samples)

        # 4. Heavy Weapon Cleave (Mira Gok-Do / Rumi Finisher)
        heavy_samples = []
        for i in range(int(sr * 0.22)):
            t = i / sr
            freq = 420.0 - (t / 0.22) * 310.0
            noise = math.sin(i * 2.3) * math.cos(i * 0.51)
            env = (1.0 - t / 0.22) ** 1.2
            val = 0.65 * math.sin(2 * math.pi * freq * t) + 0.5 * noise
            heavy_samples.append(int(val * env * 14500))
        self.sfx["slash_heavy"] = self._make_sound(heavy_samples)

        # 5. Bobby Cell Phone Ring-Toss
        phone_samples = []
        for i in range(int(sr * 0.16)):
            t = i / sr
            freq = 1174.66 if int(t * 36) % 2 == 0 else 1567.98
            env = 1.0 - (t / 0.16)
            val = math.sin(2 * math.pi * freq * t)
            phone_samples.append(int(val * env * 9500))
        self.sfx["phone_throw"] = self._make_sound(phone_samples)

        # 6. Punch / Weapon Impact Hit
        hit_samples = []
        for i in range(int(sr * 0.12)):
            t = i / sr
            freq = 190.0 * math.exp(-t * 18.0) + 55.0
            snap = math.sin(i * 3.1) * math.cos(i * 0.73) * math.exp(-t * 35.0)
            env = (1.0 - t / 0.12) ** 1.5
            val = 0.75 * math.sin(2 * math.pi * freq * t) + 0.6 * snap
            hit_samples.append(int(val * env * 16500))
        self.sfx["hit"] = self._make_sound(hit_samples)

        # 7. Enemy KO / Demon Vanish
        ko_samples = []
        for i in range(int(sr * 0.28)):
            t = i / sr
            freq = 360.0 - (t / 0.28) * 260.0
            env = 1.0 - (t / 0.28)
            val = math.sin(2 * math.pi * freq * t) + 0.4 * math.sin(2 * math.pi * (freq * 1.5) * t)
            ko_samples.append(int(val * env * 12000))
        self.sfx["enemy_ko"] = self._make_sound(ko_samples)

        # 8. Hunmoon Special Summon (Magical K-Pop Synth Chord Burst)
        spec_samples = []
        chord = [523.25, 659.25, 783.99, 1046.50, 1318.51]
        for i in range(int(sr * 0.55)):
            t = i / sr
            sweep = 1.0 + 0.15 * t
            env = math.sin(math.pi * (t / 0.55))
            val = sum(math.sin(2 * math.pi * (f * sweep) * t) for f in chord) / len(chord)
            spec_samples.append(int(val * env * 15500))
        self.sfx["special_hunmoon"] = self._make_sound(spec_samples)

        # 9. Food / Lightstick Pickup
        pick_samples = []
        p_notes = [587.33, 880.0, 1174.66]
        for i in range(int(sr * 0.24)):
            t = i / sr
            f = p_notes[min(2, int(t / 0.08))]
            env = 1.0 - (t / 0.24) * 0.5
            val = math.sin(2 * math.pi * f * t)
            pick_samples.append(int(val * env * 11500))
        self.sfx["pickup"] = self._make_sound(pick_samples)

        # 10. Boss Warning Siren
        warn_samples = []
        for i in range(int(sr * 0.65)):
            t = i / sr
            freq = 440.0 + 240.0 * math.sin(2 * math.pi * 3.0 * t)
            val = 0.7 * math.sin(2 * math.pi * freq * t) + 0.3 * (1 if math.sin(2 * math.pi * freq * t) > 0 else -1)
            warn_samples.append(int(val * 12000))
        self.sfx["boss_warning"] = self._make_sound(warn_samples)

        # 11. Stage Clear / Jinu Soul Empowerment Fanfare
        clear_samples = []
        c_notes = [523.25, 659.25, 783.99, 1046.50, 1318.51, 1567.98]
        for i in range(int(sr * 0.90)):
            t = i / sr
            idx = min(len(c_notes) - 1, int(t / 0.14))
            f = c_notes[idx]
            env = min(1.0, (0.92 - t) * 2.5)
            val = 0.65 * math.sin(2 * math.pi * f * t) + 0.35 * math.sin(2 * math.pi * (f * 0.5) * t)
            clear_samples.append(int(val * max(0.0, env) * 14000))
        self.sfx["stage_clear"] = self._make_sound(clear_samples)

    def _generate_kpop_synth_loops(self):
        """
        Generate upbeat procedural K-Pop arcade synth loops for each of the 6 stage tracks
        so every stage has distinct music even before external MP3/OGG files are placed in `assets/music/`.
        """
        sr = self.sample_rate
        # Distinct melodic hooks (MIDI-style frequencies) per song
        patterns = {
            "stage1_how_its_done": {
                "step_sec": 0.14,
                "lead": [440, 523.25, 659.25, 587.33, 440, 659.25, 587.33, 523.25,
                         440, 523.25, 659.25, 783.99, 659.25, 587.33, 523.25, 493.88],
                "bass": [110, 110, 130.81, 130.81, 146.83, 146.83, 130.81, 123.47] * 2,
            },
            "stage2_golden": {
                "step_sec": 0.15,
                "lead": [523.25, 659.25, 783.99, 1046.50, 987.77, 783.99, 659.25, 783.99,
                         880.0, 783.99, 659.25, 587.33, 523.25, 587.33, 659.25, 783.99],
                "bass": [130.81, 130.81, 164.81, 164.81, 174.61, 174.61, 196.00, 196.00] * 2,
            },
            "stage3_free": {
                "step_sec": 0.16,
                "lead": [392.00, 493.88, 587.33, 783.99, 659.25, 587.33, 493.88, 440.00,
                         392.00, 493.88, 587.33, 659.25, 587.33, 493.88, 440.00, 392.00],
                "bass": [98.00, 98.00, 123.47, 123.47, 146.83, 146.83, 130.81, 130.81] * 2,
            },
            "stage4_takedown": {
                "step_sec": 0.125,
                "lead": [493.88, 493.88, 587.33, 659.25, 739.99, 659.25, 587.33, 493.88,
                         587.33, 659.25, 739.99, 880.00, 739.99, 659.25, 587.33, 554.37],
                "bass": [123.47, 123.47, 123.47, 146.83, 164.81, 164.81, 146.83, 185.00] * 2,
            },
            "stage5_your_idol": {
                "step_sec": 0.145,
                # Hypnotic minor-key Saja Boys dark pop progression
                "lead": [466.16, 554.37, 622.25, 698.46, 622.25, 554.37, 466.16, 415.30,
                         466.16, 622.25, 698.46, 830.61, 739.99, 698.46, 622.25, 554.37],
                "bass": [116.54, 116.54, 138.59, 138.59, 155.56, 155.56, 138.59, 103.83] * 2,
            },
            "stage6_what_it_sounds_like": {
                "step_sec": 0.14,
                # Emotional, triumphant anthem progression
                "lead": [587.33, 739.99, 880.00, 1174.66, 1108.73, 987.77, 880.00, 739.99,
                         659.25, 739.99, 880.00, 987.77, 1108.73, 987.77, 880.00, 1174.66],
                "bass": [146.83, 146.83, 185.00, 185.00, 220.00, 220.00, 164.81, 196.00] * 2,
            },
        }

        for stem, cfg in patterns.items():
            step_sec = cfg["step_sec"]
            lead_notes = cfg["lead"]
            bass_notes = cfg["bass"]
            total_steps = len(lead_notes)
            total_samples = int(sr * step_sec * total_steps)
            samples = [0] * total_samples

            for i in range(total_samples):
                t = i / sr
                step = min(total_steps - 1, int(t / step_sec))
                local_t = t - step * step_sec
                note_env = max(0.15, 1.0 - (local_t / step_sec) * 0.75)

                f_lead = lead_notes[step]
                f_bass = bass_notes[step]

                # Lead synth + octave shimmer
                lead_wave = (
                    0.55 * math.sin(2 * math.pi * f_lead * t)
                    + 0.25 * math.sin(2 * math.pi * (f_lead * 2.0) * t)
                ) * note_env

                # Punchy synth bass
                bass_wave = 0.45 * math.sin(2 * math.pi * f_bass * t)

                # Electronic kick + hi-hat beat
                kick = 0.0
                if step % 2 == 0 and local_t < 0.06:
                    kick = math.sin(2 * math.pi * (130.0 - local_t * 1400.0) * local_t) * 0.55
                hat = 0.0
                if step % 2 == 1 and local_t < 0.03:
                    hat = math.sin(i * 2.9) * math.cos(i * 0.81) * 0.22

                samples[i] = int((lead_wave + bass_wave + kick + hat) * 6200)

            self.synth_tracks[stem] = self._make_sound(samples)

    def play_sfx(self, name: str):
        if not self.enabled or self.muted:
            return
        snd = self.sfx.get(name)
        if snd is not None:
            try:
                snd.play()
            except pygame.error:
                pass

    def find_external_song_file(self, stage_cfg: dict) -> str | None:
        """
        Look inside `assets/music/` for a matching .ogg, .mp3, or .wav file
        by exact stem or by song title keywords.
        """
        if not os.path.isdir(MUSIC_DIR):
            return None
        exts = (".ogg", ".mp3", ".wav", ".flac")
        stem = stage_cfg.get("song_file_stem", "").lower()
        keywords = [k.lower() for k in stage_cfg.get("song_keywords", [])]

        try:
            files = os.listdir(MUSIC_DIR)
        except OSError:
            return None

        # First pass: exact stem match
        for fname in files:
            low = fname.lower()
            if low.endswith(exts) and os.path.splitext(low)[0] == stem:
                return os.path.join(MUSIC_DIR, fname)

        # Second pass: keyword substring match (e.g., "Golden.mp3" or "05 - Your Idol.ogg")
        for fname in files:
            low = fname.lower()
            if low.endswith(exts):
                normalized = low.replace("'", "").replace("-", "_").replace(" ", "_")
                for kw in keywords:
                    kw_norm = kw.replace("'", "").replace(" ", "_")
                    if kw_norm in normalized or kw in low:
                        return os.path.join(MUSIC_DIR, fname)
        return None

    def play_stage_music(self, stage_index: int):
        """Play the stage's soundtrack (external MP3/OGG if present, otherwise built-in K-Pop synth loop)."""
        if not self.enabled:
            return
        self.stop_music()

        stage_cfg = STAGES[stage_index % len(STAGES)]
        stem = stage_cfg["song_file_stem"]
        self.current_track_name = f"{stage_cfg['song_title']} — {stage_cfg['song_artist']}"

        ext_file = self.find_external_song_file(stage_cfg)
        if ext_file:
            try:
                pygame.mixer.music.load(ext_file)
                pygame.mixer.music.set_volume(0.0 if self.muted else 0.72)
                pygame.mixer.music.play(-1)
                self.using_external_file = True
                return
            except pygame.error:
                pass

        # Fallback to built-in synthesized K-Pop arcade loop
        self.using_external_file = False
        synth_snd = self.synth_tracks.get(stem)
        if synth_snd is not None and not self.muted:
            try:
                self.current_synth_channel = synth_snd.play(loops=-1)
                if self.current_synth_channel:
                    self.current_synth_channel.set_volume(0.55)
            except pygame.error:
                pass

    def stop_music(self):
        if not self.enabled:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
        if self.current_synth_channel is not None:
            try:
                self.current_synth_channel.stop()
            except pygame.error:
                pass
            self.current_synth_channel = None

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self.muted:
            self.stop_music()
        return self.muted
