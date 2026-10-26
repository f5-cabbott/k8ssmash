"""Generate fighter sprite sheets: python -m k8ssmash.art.build [name ...] [--contact]"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from k8ssmash.art.looks import LOOKS
from k8ssmash.art.poses import ANIMS, pose_for
from k8ssmash.art.rig import FEET, FRAME, FRAME_U, alternate_look, render

OUT = Path(__file__).resolve().parents[2] / "assets" / "sprites"


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


VARIANT_SHIFTS = {1: 0.42, 2: 0.16, 3: -0.18}  # hue rotations for the colour variants (0 is the original)
VARIANT_TAGS = {0: "", 1: "_alt", 2: "_v2", 3: "_v3"}


def build(name: str, variant: int = 0) -> pygame.Surface:
    look = LOOKS[name]()
    if variant:
        look = alternate_look(look, VARIANT_SHIFTS[variant])  # the mirror-match and extra colour schemes
    cols = max(n for n, _, _ in ANIMS.values())
    sheet = pygame.Surface((cols * FRAME, len(ANIMS) * FRAME), pygame.SRCALPHA)
    meta = {"frame": FRAME, "units": FRAME_U, "feet": list(FEET), "anims": {}}
    for row, (anim, (count, fps, loop)) in enumerate(ANIMS.items()):
        for i in range(count):
            sheet.blit(render(look, pose_for(anim, i)), (i * FRAME, row * FRAME))
        meta["anims"][anim] = {"row": row, "frames": count, "fps": fps, "loop": loop}
    OUT.mkdir(parents=True, exist_ok=True)
    tag = VARIANT_TAGS[variant]
    pygame.image.save(sheet, str(OUT / f"{slug(name)}{tag}.png"))
    (OUT / f"{slug(name)}{tag}.json").write_text(json.dumps(meta, indent=1))
    return sheet


def contact_sheet(sheets: dict[str, pygame.Surface], path: Path, scale: int = 1) -> None:
    """One image: a few key poses for every fighter, for eyeballing the whole roster."""
    show = [("idle", 0), ("run", 1), ("jump", 0), ("jab", 1), ("side", 1), ("cast", 1), ("rise", 1), ("hurt", 0)]
    names = list(ANIMS)
    out = pygame.Surface((len(show) * FRAME * scale, len(sheets) * FRAME * scale))
    out.fill((40, 48, 80))
    for r, sheet in enumerate(sheets.values()):
        for c, (anim, i) in enumerate(show):
            frame = sheet.subsurface((i * FRAME, names.index(anim) * FRAME, FRAME, FRAME))
            out.blit(pygame.transform.scale(frame, (FRAME * scale, FRAME * scale)),
                     (c * FRAME * scale, r * FRAME * scale))
    pygame.image.save(out, str(path))


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = args or list(LOOKS)
    only = [int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--variant=")]
    sheets = {} if only else {n: build(n) for n in names}  # --variant=N rebuilds just those colour variants
    for n in names:
        for v in (only or [1, 2, 3]):
            build(n, v)
    if "--contact" in sys.argv and sheets:
        path = Path("screenshots/contact.png")
        path.parent.mkdir(exist_ok=True)
        contact_sheet(sheets, path)
        print("contact sheet:", path)
    print("built:", ", ".join(names))


if __name__ == "__main__":
    main()
