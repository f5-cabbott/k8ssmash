#!/usr/bin/env bash
# Install K8s Smash as a boot-time kiosk service on Raspberry Pi OS (64-bit).
#
#   sudo deploy/setup-pi.sh [--user kiosk] [--dir /opt/k8ssmash] [--readonly]
#
# Safe to re-run: it updates the code, venv and service in place.
set -euo pipefail

USER_NAME=kiosk
APP_DIR=/opt/k8ssmash
READONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --user) USER_NAME="$2"; shift 2 ;;
    --dir) APP_DIR="$2"; shift 2 ;;
    --readonly) READONLY=1; shift ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "run as root: sudo $0 $*" >&2
  exit 1
fi
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(uname -m)" != "aarch64" ]]; then
  echo "warning: this is $(uname -m), not aarch64 (Raspberry Pi 5, 64-bit OS). Continuing anyway." >&2
fi

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv python3-pip rsync alsa-utils \
  libdrm2 libgbm1 libegl1 libgles2 libudev1
# libasound2 was renamed libasound2t64 on newer Debian; whichever exists is fine.
apt-get install -y --no-install-recommends libasound2t64 2>/dev/null \
  || apt-get install -y --no-install-recommends libasound2

echo "==> Creating service user '$USER_NAME'"
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "/var/lib/$USER_NAME" --shell /usr/sbin/nologin "$USER_NAME"
fi
usermod -aG video,render,input,audio "$USER_NAME"

echo "==> Copying game to $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude 'screenshots' \
  "$SRC_DIR"/ "$APP_DIR"/

echo "==> Building virtualenv"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -e "$APP_DIR"
chown -R root:root "$APP_DIR"
chmod -R a+rX "$APP_DIR"

echo "==> Installing udev rule, defaults and systemd unit"
install -m 0644 "$APP_DIR/deploy/99-snes-pads.rules" /etc/udev/rules.d/99-snes-pads.rules
[[ -e /etc/default/k8ssmash ]] || install -m 0644 "$APP_DIR/deploy/k8ssmash.default" /etc/default/k8ssmash
sed -e "s|__USER__|$USER_NAME|g" -e "s|__APP_DIR__|$APP_DIR|g" \
  "$APP_DIR/deploy/k8ssmash.service" > /etc/systemd/system/k8ssmash.service
udevadm control --reload-rules && udevadm trigger --subsystem-match=input || true
systemctl daemon-reload
systemctl enable k8ssmash.service
systemctl set-default multi-user.target >/dev/null

if [[ $READONLY -eq 1 ]]; then
  echo "==> Enabling the read-only root overlay (takes effect after reboot)"
  if command -v raspi-config >/dev/null; then
    raspi-config nonint enable_overlayfs
    raspi-config nonint enable_bootro || true
  else
    echo "raspi-config not found; see deploy/README.md for the manual steps." >&2
  fi
fi

cat <<MSG

Done. Next:
  1. Smoke test now:      sudo systemctl start k8ssmash && journalctl -fu k8ssmash
  2. Benchmark (stop the service first):  sudo systemctl stop k8ssmash
        sudo -u $USER_NAME SDL_VIDEODRIVER=kmsdrm $APP_DIR/.venv/bin/python $APP_DIR/tools/benchmark.py 20
  3. Reboot to confirm it starts on its own:  sudo reboot
Staff quit combo (hold ~3s on one pad): SELECT + START + L/R + B. Restart with: sudo systemctl start k8ssmash
MSG
