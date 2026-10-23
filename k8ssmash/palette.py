"""Player colors (with a colorblind-safe set) and damage-severity colors."""
from __future__ import annotations

from k8ssmash.config import Config

Color = tuple[int, int, int]

DEFAULT: list[Color] = [(80, 160, 255), (255, 110, 90)]
# Okabe-Ito sky blue / orange: distinguishable under all common color-vision deficiencies.
COLORBLIND: list[Color] = [(86, 180, 233), (240, 170, 30)]


def player_colors(cfg: Config) -> list[Color]:
    return COLORBLIND if cfg.colorblind else DEFAULT


def damage_color(percent: float) -> Color:
    if percent < 30:
        return (245, 245, 255)
    if percent < 80:
        return (255, 235, 120)
    if percent < 130:
        return (255, 160, 70)
    return (255, 80, 70)
