# K-Pop Demon Hunters: The Arcade Game

Classic 4-player 2D scrolling arcade beat 'em up (inspired by the 1989 *TMNT* arcade game) themed around **K-Pop Demon Hunters**—built for Windows and **Batocera / RetroPie** arcade cabinets using Python & `pygame-ce`.

---

## Quick Start (Play in VS Code or Terminal)

1. **Press `F5` in VS Code** (uses [launch.json](file:///c:/GitHub%20Projects/KpopDemonHunters/.vscode/launch.json))
   — or run from terminal:
   ```powershell
   python main.py
   ```
2. **Fullscreen Arcade Mode:**
   ```powershell
   python main.py --fullscreen
   ```

---

## Arcade Controls (Up to 4 USB Joysticks/Gamepads + Keyboard/IPAC)

| Action | Arcade Cabinet / Gamepad | Player 1 (Keyboard) | Player 2 (Keyboard) |
| :--- | :--- | :--- | :--- |
| **Move (8-Way)** | Joystick / D-Pad (Double-tap Left/Right to Dash) | Arrow Keys or `W/A/S/D` | Numpad `8/4/5/6` or `T/F/G/H` |
| **Button 1: Attack / Combo** | Button A / X | `Z`, `J`, or `Left Ctrl` | `Numpad 1`, `U`, or `Right Ctrl` |
| **Button 2: Jump / Escape Vault** | Button B / Circle *(Press again in mid-air to Escape Vault across the screen!)* | `X`, `K`, or `Left Alt` | `Numpad 0`, `O`, or `Right Shift` |
| **Button 3: Hunmoon Special** | Button Y / R1 | `C`, `L`, or `Space` | `Numpad 3` or `P` |
| **Button 4: Team Synergy / Dodge** | Button L1 | `V`, `;`, or `Left Shift` | `Numpad 7` or `Y` |
| **Insert Coin** | `Select` / Coin Door (`5`–`8`) | `5` or `Tab` | `6` |
| **Start / Join / Continue** | `Start` (`1`–`4`) | `1` or `Enter` | `2` or `Numpad Enter` |

### Handy Shortcuts
- **`F1`**: Toggle Fullscreen / Windowed
- **`F3`**: Skip to the Next Stage (great for testing all 6 stages & bosses)
- **`M`**: Mute / Unmute Audio
- **`Esc`**: Return to Title Screen / Exit

---

## Playable Roster

- **Rumi** *(Lead Singer & Leader)* — Wields the **Sain-geom** light sword summoned from the Hunmoon. Her **Half-Demon Resonance** special ignites her blue half-demon skin patterns, unleashing a 360° light shockwave and curing team debuffs.
- **Zoey** *(Lead Rapper)* — Fastest fighter; dual **Shin-kal** spirit daggers with rapid combos and her **Spitfire Spirit Barrage** fan of piercing daggers.
- **Mira** *(Lead Dancer, Visual & Choreographer)* — Fierce heavy hitter; sweeps crowds with her **Gok-Do** curved moon polearm and slams the floor with **Crescent Moon Cleave**.
- **Bobby** *(Group Manager)* — Loyal, cheerful, and bumbling! Throws ringing cell phones in spread combos and calls in crashing concert spotlights + healing Boba tea with **"Hold Please!" VIP Drop**.

---

## 6-Stage Campaign, Bosses & Soundtrack

Drop your `.mp3` or `.ogg` song files into [assets/music/](file:///c:/GitHub%20Projects/KpopDemonHunters/assets/music/README.md) (built-in synthesized K-Pop arcade loops play automatically if external files aren't added yet):

1. **Stage 1: Mile-High Ambush (Huntr/x Private Jet)** — Boss: **Mystery** | Song: *"How It's Done"*
2. **Stage 2: Crash the Concert (Seoul Neon Dome)** — Boss: **Romance** | Song: *"Golden"*
3. **Stage 3: Steam & Shadows (Traditional Bathhouse)** — Boss: **Abby** | Song: *"Free"*
4. **Stage 4: Runaway Bullet Train (KTX Rooftop)** — Boss: **Baby** | Song: *"Takedown"*
5. **Stage 5: The Dark Encore (Saja Boys Stadium)** — Boss: **Jinu** *(Soul Empowerment)* | Song: *"Your Idol"*
6. **Stage 6: Heart of the Inferno (Final Boss)** — Boss: **Gwi-Ma** | Song: *"What It Sounds Like"*

---

## Deploying to Your Arcade Machine (Batocera / RetroPie)

Run the packager script:
```powershell
python build_arcade_package.py
```
This builds a self-contained `dist/KpopDemonHunters.pygame/` folder that **already bundles `main.py`, `src/`, and `assets/` (all sprites, backgrounds, UI art, and music) inside it**:
- **Batocera:** Copy the entire `dist/KpopDemonHunters.pygame` folder and `dist/KpopDemonHunters.pygame.keys` into `/userdata/roms/pygame/` on your Batocera machine and refresh your game list (no need to copy the root `assets/` or `src/` folders separately).
- **RetroPie:** Copy the `dist/KpopDemonHunters.pygame` folder and `dist/KpopDemonHunters.sh` into `~/RetroPie/roms/ports/`.
