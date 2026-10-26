# K8s Smash

A 2-player, Smash-style platform fighter with a hand-painted 16-bit look, built for conference booths.
**Pods vs. chaos**: eight Kubernetes-themed fighters, k8s power-ups, three stages, played with two SNES-style USB pads
on a Raspberry Pi 5 (or any computer: the keyboard works too). Kubernetes is the *theme*; nothing here needs a cluster.

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m k8ssmash --windowed        # play
.venv/bin/python -m pytest                      # tests
```

For the Raspberry Pi booth (what it needs, install, smoke test, performance), see [`deploy/README.md`](deploy/README.md). In short: a 64-bit Pi OS Lite, `sudo deploy/setup-pi.sh`, and `pygame-ce` is the only Python package the game needs; `numpy`, `scipy` and `ffmpeg` are only for regenerating assets.

## Playing

| SNES pad | Action | Keyboard P1 / P2 |
|---|---|---|
| D-pad | move and aim attacks. **Hold down to duck** (high attacks and shots pass over you); **tap down** on a thin platform to drop through; hold down in the air to fast-fall | `WASD` / arrows |
| Y or X | jump (press again in the air to double jump: the second jump reaches 65% of the first, and steers where you push) | `L` / `.` |
| B | attack: tap = jab, hold a direction + B = side / up / down | `J` / `N` |
| A | special: neutral, or with a direction (side / up = recovery / down) | `K` / `M` |
| L or R | shield (hold) | `I` / `,` |
| Start | join, confirm (menus: A or Start enters, B or Select backs out) | `Enter` / numpad 1 |
| Select | add a CPU opponent (select screen), leaderboard (title) | `Backspace` / numpad 0 |

Knock the other pod off the stage. Damage % makes every hit launch farther; 3 stocks, 2 minutes (both are in Settings > Gameplay).
Grab the heptagon power-ups: **HPA** (bigger + stronger), **Sidecar** (drone), **Cordon** (armor),
**PDB** (half damage), **Chaos Bomb**, **Rollout Undo** (heal), **Readiness Probe** (speed).

### Modes and screens
- **Pause**: START during a match opens a pause menu (Resume, Restart match, Quit to title).
- **Stage select**: after the fighters are locked in, pick an arena from live previews (or Random); each shows its set piece.
- **Colors**: press Y or X on the fighter select to cycle four colour schemes (Classic, Twilight, Sunset, Lagoon). A mirror match always gets two different ones.
- **How to play**: a title-menu entry with six short live demos (moving, gliding, attacks, specials, shield and grab, ledge hang) and the buttons shown.
- **Rematch**: the results screen offers START rematch, L/R next stage, Y/X swap sides and SELECT change fighters, and shows each fighter's best combo.
- **Announcer**: a deep ring announcer calls "Ready... Fight!", "Final stock!", "Game!" and "<Fighter> wins!".
- **Versus / vs CPU**: press START to join; a lone player presses SELECT to add a CPU. Shoulder buttons change the stage.
- **Title menu**: UP / DOWN pick Versus, Training, Leaderboard or Settings; A or START enters (START on the default Versus
  row starts a match, as before).
- **Training**: pick it on the title menu. Dummy modes (SELECT): stand, shield, jump, CPU, Record, Replay (it records up to six seconds of your moves, then repeats them mirrored). Hitboxes are shown (F3 toggles), the last move's startup, active and recovery frames, damage and knockback are listed, and a combo counter is kept. START resets, hold START leaves.
- **Settings**: a hub of Audio, Display, Gameplay and Controls; UP / DOWN pick, A enters, B goes back. Audio has master /
  effects / music volume and mute; Display has fullscreen, screen shape, window size and colorblind colors; Gameplay has
  stocks, time limit and power-ups; Controls opens the button rebinder, the controller test and the P1/P2 pad swap.
- **Stage set pieces**: each stage changes shape now and then. Datacenter hot-swaps a server rack into the middle, the
  Control Plane hands its crown perch from one side to the other (leader election), and the Node Pool scheduler lays a
  bridge over the gap. They fade in as a ghost first and dim before they leave; none of them hurt.
- **Leaving**: press A to back out of character select (un-lock, un-join, then leave) and on the results screen to return to the main menu.
- **Leaderboard**: longest win streak and most KOs in a run (rematches continue a run; a loss ends it).
  Pick it on the title menu or tap SELECT on the title screen. Winners enter a 3-letter name.
- **Attract mode**: idle on the title and a CPU demo plays, then the leaderboard.

### Booth / staff
| Do this | To get |
|---|---|
| Hold **SELECT+START** 1.5 s | Controller test screen (shows every button, raw numbers) |
| On that screen: **JUMP on the P2 pad** | Swap P1/P2 |
| On that screen: hold **SELECT** 2 s | Rebind buttons |
| Hold **SELECT+START+L/R+B** 3 s | Quit (service stays stopped) |
| `--booth` | Fullscreen, mouse hidden, dev hotkeys off |

Dev hotkeys (off in booth mode): `F3` hitboxes, `F6` colorblind colors, `F8` FPS, `F9` mute, `F10` 1080p/1440p,
`F11` fullscreen, `F12` screenshot, `Esc` quit.

## Display and performance

The game logic runs on a 960x540 grid but everything is drawn at twice that, 1920x1080 by default, then scaled to the window
(720p, 900p, 1080p and 1440p are in Settings > Display). Set `K8SSMASH_RS=1` (or `--lowres` / `--render-scale 1`) to draw at
the classic size, which is much lighter on weak hardware. The Raspberry Pi service defaults to 1 until its frame time at 1080p
has been measured with `python tools/benchmark.py`; set `K8SSMASH_RS=2` in `/etc/default/k8ssmash` to try the hi-res picture.

## Flags and config

`python -m k8ssmash --help`: `--booth --windowed --fullscreen --size WxH --no-items --mute --colorblind --fps
--rebind --metrics-port N --software-render --render-scale N --lowres`. Saved settings live in `~/.config/k8ssmash/config.json`
(`K8SSMASH_CONFIG` overrides the path; scores are stored next to it). Notable keys: `pad` (button numbers),
`pad_name_filter`, `event_name`, `items`, `colorblind`, `stocks`, `match_seconds`, `sfx_volume`, `music_volume`.

## How it is built

- **Engine**: Python + pygame-ce, fixed 60 Hz logic. Battles draw on a 960x540 world (a farther-out view: smaller fighters, bigger
  arenas with four levels); menus keep a 640x360 layout and are scaled up. 960x540 is exactly 2x at 1080p, and fullscreen
  letterboxes cleanly on ultrawides. Windows are sized to fit your desktop and centered.
- **Art**: sprites are generated by a posable-rig pipeline. Each fighter has hand-shaped contours (spline heads, torsos, mitts and boots; see `art/shapes.py`) and is painted in a cel style with deliberate shadow shapes, rim light and gloss, so every fighter and animation is reproducible:
  `python -m k8ssmash.art.build [--contact]` writes `assets/sprites/*.png|json`. Replace any sheet with hand-drawn art
  that keeps the same layout (see `assets/sprites/pod.json`).
- **Audio**: `python -m k8ssmash.audio.build` synthesizes everything (needs `numpy`, `scipy`, `ffmpeg`; `pip install -e '.[audio]'` adds `espeakng-loader`, which speaks the announcer lines at build time):
  eight 60-95 s original songs with sampled-style instruments (a string section with bow noise, piano, plucked
  strings from a Karplus-Strong model, horn, clarinet, oboe, sax, brass, choir, vibes, plus the odd accordion and kazoo),
  tunes built from a hook and its answer, voice-led chords, walking bass lines, ghost-note drums and fills, human timing,
  harmonized choruses, odd-meter detours and a convolution-reverb space, one per stage plus title, select, training
  and leaderboard themes and a victory sting. Every fighter has its own sound set (bubbles, foghorn, bleeps, squeaks,
  servos, portals, phone tones, growls) and its own tune (`motif`), which plays over the music in the song's key when
  that fighter lands a three-hit combo. Effects are panned by screen position and duck the music; music sits ~8 dB under
  them. `python tools/audio_report.py` measures the music against a reference profile.
- **Moves** are data (`k8ssmash/roster.py`, `k8ssmash/moves.py`): frames, hitboxes, knockback, projectiles, buffs.

```
k8ssmash/          game code (fighter, battle, scenes/, input, render, ...)
  art/ audio/      asset generators
assets/            generated sprites and audio
deploy/            Raspberry Pi service, installer, Grafana dashboard
tools/             padtest.py  benchmark.py  balance.py  shot.py
tests/             pytest suite (physics, flow, input, audio, scores, metrics, ...)
```

### Optional: Prometheus metrics
Off by default. `--metrics-port 9877` serves `/metrics` (matches, picks, wins, KOs, specials, items, FPS, uptime)
and `/healthz`. Import [`deploy/grafana/k8ssmash-dashboard.json`](deploy/grafana/k8ssmash-dashboard.json) into Grafana.

### Balance
`python tools/balance.py 3 7` plays a CPU round-robin and prints win rates. The CPU is simple, so treat it as a smoke
alarm for outliers, not a substitute for people playing.
