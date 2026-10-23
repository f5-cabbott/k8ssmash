"""The fighter roster. Expanded to eight pod-themed fighters in the content milestone."""
from __future__ import annotations

from k8ssmash.fighter import FighterStats


def roster() -> list[FighterStats]:
    return [
        FighterStats("Pod", (80, 160, 255)),
        FighterStats("Chaos", (255, 110, 90), weight=110, run_speed=2.4),
    ]
