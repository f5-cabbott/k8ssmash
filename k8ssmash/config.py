"""Game constants and the persisted user config."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

CANVAS_W = 640
CANVAS_H = 360
FPS = 60

RESOLUTIONS = [(1920, 1080), (2560, 1440)]

ACTIONS = ("LEFT", "RIGHT", "UP", "DOWN", "JUMP", "ATTACK", "SPECIAL", "SHIELD", "START", "SELECT")

# Keyboard defaults for development: P1 on the left of the keyboard, P2 on the right.
DEFAULT_KEYS = [
    {
        "LEFT": "a", "RIGHT": "d", "UP": "w", "DOWN": "s",
        "JUMP": "l", "ATTACK": "j", "SPECIAL": "k", "SHIELD": "i",
        "START": "return", "SELECT": "backspace",
    },
    {
        "LEFT": "left", "RIGHT": "right", "UP": "up", "DOWN": "down",
        "JUMP": ".", "ATTACK": "n", "SPECIAL": "m", "SHIELD": ",",
        "START": "[1]", "SELECT": "[0]",
    },
]

# Generic USB SNES clone (0079:0011) as seen by SDL on Linux: X=0 A=1 B=2 Y=3 L=4 R=5
# Select=8 Start=9, D-pad on axes 0/1. Confirm with tools/padtest.py and override in config.
# SNES layout -> B attack, A special, Y/X jump, L/R shield.
DEFAULT_PAD = {
    "JUMP": [3, 0],
    "ATTACK": [2],
    "SPECIAL": [1],
    "SHIELD": [4, 5],
    "START": [9],
    "SELECT": [8],
}


def config_path() -> Path:
    override = os.environ.get("K8SSMASH_CONFIG")
    if override:
        return Path(override)
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "k8ssmash" / "config.json"


def data_dir() -> Path:
    """Where persistent game data (scores) lives: next to the config file."""
    return config_path().parent


@dataclass
class Config:
    width: int = 1920
    height: int = 1080
    fullscreen: bool = False
    sfx_volume: float = 0.8
    music_volume: float = 0.5
    muted: bool = False
    swap_pads: bool = False  # P1/P2 pad order; fix it from the controller test screen
    colorblind: bool = False  # colorblind-safe player colors
    event_name: str = "KubeCon"  # shown on the title and leaderboard
    items: bool = True  # k8s power-ups drop during matches
    dev_keys: bool = True  # Esc quits, F-keys active; disabled by the booth service
    # Only joysticks whose name contains one of these (case-insensitive) become players.
    # Keeps other attached pads (e.g. an Xbox-style controller) out of the game; [] accepts all.
    pad_name_filter: list[str] = field(default_factory=lambda: ["USB Gamepad"])
    keys: list[dict[str, str]] = field(default_factory=lambda: [dict(k) for k in DEFAULT_KEYS])
    pad: dict[str, list[int]] = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_PAD.items()})

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        path = config_path()
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return cfg
        for name in ("width", "height", "fullscreen", "dev_keys", "pad_name_filter", "items", "sfx_volume", "music_volume", "muted", "swap_pads", "colorblind", "event_name"):
            if name in data:
                setattr(cfg, name, data[name])
        for slot, keys in enumerate(data.get("keys", [])[:2]):
            cfg.keys[slot].update(keys)
        cfg.pad.update(data.get("pad", {}))
        return cfg

    def save(self) -> None:
        path = config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(self), indent=2))
        except OSError:
            pass
