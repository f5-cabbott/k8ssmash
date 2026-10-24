# Deploying K8s Smash on a Raspberry Pi 5

Target: Raspberry Pi 5, **Raspberry Pi OS Lite (64-bit)**, two SNES-clone USB pads, HDMI to the booth screen
(1440p). The game runs as a systemd service that owns the screen directly through SDL's KMS/DRM backend:
no desktop, no compositor, and it comes back by itself after a crash, a hang or a power cut.

> **Status:** everything here was written and checked on a desktop (unit file validated with
> `systemd-analyze`, setup script syntax-checked, game benchmarked). It has **not yet been run on a Pi**.
> Work through the smoke test below first, and expect to tweak the audio device or display mode.

## 1. Hardware checklist

- Pi 5 (4 GB is plenty) with the **active cooler**, a **27 W USB-C supply** and a good microSD (or NVMe).
- micro-HDMI to HDMI cable, into **HDMI0** (the port next to USB-C).
- Both pads plugged in **before** power-up. Left pad in the left USB port, right pad in the right one: the
  order they enumerate in decides who is P1 (fixable in software, see "Pads" below).

## 2. Prepare the OS

1. Flash **Raspberry Pi OS Lite (64-bit)** with Raspberry Pi Imager. In the advanced options set a
   hostname, enable SSH with your key, and set Wi-Fi/locale.
2. Boot, SSH in, then:
   ```bash
   sudo apt update && sudo apt full-upgrade -y && sudo reboot
   ```

## 3. Install

Copy the repository to the Pi (for example `rsync -a --exclude .venv --exclude .git ./ pi@booth:~/k8ssmash/`), then:

```bash
cd ~/k8ssmash
sudo deploy/setup-pi.sh            # installs to /opt/k8ssmash, creates user 'kiosk', enables the service
```

The script is idempotent: re-run it after you change code or art. It installs system libraries, builds a
venv, installs the udev rule and the `k8ssmash.service` unit, and enables it for boot.

## 4. Smoke test (do this before trusting it)

```bash
sudo systemctl start k8ssmash
journalctl -fu k8ssmash          # expect: "running: driver=KMSDRM gpu_scaled=True window=(2560, 1440) pads=[...]"
```

| Check | What good looks like |
|---|---|
| Display | Title screen on the booth screen at the native mode, crisp pixels, no tearing |
| Frame rate | Run the benchmark (dev hotkeys like F8 are off in booth mode): `sudo systemctl stop k8ssmash`, then<br>`sudo -u kiosk SDL_VIDEODRIVER=kmsdrm /opt/k8ssmash/.venv/bin/python /opt/k8ssmash/tools/benchmark.py 20` → `PASS: holds 60 fps` |
| Pads | Hold **SELECT+START** for 1.5 s: the controller test screen lights every button for both pads |
| Buttons | If a button lights the wrong thing, fix the numbers in `pad` in `/var/lib/k8ssmash/config.json` (see "Pads") |
| Audio | Title music plays; jump and hit sounds are audible |
| Crash recovery | `sudo pkill -9 -f k8ssmash` → game is back within ~3 s |
| Hang recovery | `sudo pkill -STOP -f k8ssmash` → systemd restarts it within 20 s (watchdog) |
| Power cut | Pull the plug mid-match, power on: game starts by itself, nothing to repair |

Staff quit combo: hold **SELECT + START + L/R + B** on one pad for 3 s. The service stays stopped until
`sudo systemctl start k8ssmash`.

## 5. Making the SD card power-cut proof (read-only root)

At a booth the plug will get pulled. Enable the overlay file system so the SD card is never written:

```bash
sudo deploy/setup-pi.sh --readonly      # or: sudo raspi-config nonint enable_overlayfs; sudo raspi-config nonint enable_bootro
sudo reboot
```

With the overlay on, all changes are kept in RAM and lost at reboot. That is what you want for the game,
but it also means **config changes and (later) high scores don't survive**. To keep them, either:

- skip `--readonly` (the game writes only a tiny JSON file; ext4 journaling makes that survivable), or
- put `/var/lib/k8ssmash` on its own small partition or USB stick, mounted read-write.

To change anything while the overlay is on: `sudo raspi-config nonint disable_overlayfs && sudo reboot`, make
the change, then enable it again.

## 6. Pads

- **Which pad is P1:** open the controller test screen (hold SELECT+START) and press **JUMP on the pad
  labelled P2** to make it P1. The choice is saved as `swap_pads` in the config.
- **Wrong button mapping:** find the numbers with
  `sudo -u kiosk /opt/k8ssmash/.venv/bin/python /opt/k8ssmash/tools/padtest.py` (or look at the test screen),
  then edit `/var/lib/k8ssmash/config.json`:
  ```json
  "pad": { "ATTACK": [2], "SPECIAL": [1], "JUMP": [3, 0], "SHIELD": [4, 5], "START": [9], "SELECT": [8] }
  ```
  Restart with `sudo systemctl restart k8ssmash`.
- **Other pads are ignored:** only devices whose name contains an entry of `pad_name_filter`
  (default `["USB Gamepad"]`) become players.

## 7. Display modes

The game draws a 960x540 world and SDL scales it to the screen: exactly 2x at 1080p, and about 2.67x at 1440p (SDL
scales on the GPU, so the extra fraction costs nothing). If
the Pi picks the wrong mode for your TV, force one on the kernel command line
(`/boot/firmware/cmdline.txt`, keep it a single line, append):

```
video=HDMI-A-1:2560x1440@60
```

Other aspect ratios still work; the picture is centered with black bars.

## 8. Troubleshooting

| Symptom | Try |
|---|---|
| Black screen, service restarting | `journalctl -u k8ssmash -b`. Permission errors on `/dev/dri/card*` → check `id kiosk` lists `video render input`. "No available video device" → another process owns the display (a desktop session?). Boot to console: `sudo raspi-config nonint do_boot_behaviour B1` |
| No sound | `aplay -L`, pick the HDMI device, set `SDL_AUDIODRIVER=alsa` and `AUDIODEV=...` in `/etc/default/k8ssmash`, restart |
| Pads not detected | `lsusb` should list `0079:0011`; `ls /dev/input/js*`; confirm the udev rule: `udevadm test /sys/class/input/event*` |
| Choppy frames | Run the benchmark. Check for throttling: `vcgencmd get_throttled` (`0x0` is healthy) |
| Need the game windowed on a desktop Pi OS | `python -m k8ssmash --windowed --fps` (not the kiosk path; F8 toggles the FPS overlay, F10 cycles 1080p/1440p) |

Useful flags: `--booth`, `--windowed`, `--size 2560x1440`, `--fps`, `--no-items`, `--mute`,
`--colorblind`, `--rebind`, `--metrics-port`, `--software-render`. Set extra ones for the service with `K8SSMASH_EXTRA_ARGS` in `/etc/default/k8ssmash`.

## 9. Optional: metrics for the booth dashboard

The game can expose Prometheus metrics (matches played, picks, wins, KOs, special-move usage, power-ups, FPS,
pads connected). It is **off by default**. To turn it on, add to `/etc/default/k8ssmash`:

```
K8SSMASH_EXTRA_ARGS=--metrics-port 9877
```

then `sudo systemctl restart k8ssmash` and check `curl localhost:9877/metrics`. Scrape it from Prometheus:

```yaml
scrape_configs:
  - job_name: k8ssmash
    static_configs:
      - targets: ["booth-pi.local:9877"]
```

For a ready-made Prometheus + Grafana stack, see [`deploy/monitoring/`](monitoring/README.md) (one `docker compose up`).
The endpoint has no authentication and listens
on all interfaces, so only enable it on a network you trust (or set `metrics_host` to `127.0.0.1` in the config).
If the port is taken the game just logs a warning and carries on.

## 10. Running it on a desktop Pi OS instead

If you would rather keep the Wayland desktop, skip the systemd unit and start the game from the compositor's
autostart (`~/.config/labwc/autostart`):

```
/opt/k8ssmash/.venv/bin/python -m k8ssmash --booth &
```

You lose the crash/hang watchdog and the clean-boot guarantees, so the Lite + service route above is the
recommended one for the booth.
