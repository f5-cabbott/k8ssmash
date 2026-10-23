import json

import pygame
import pytest

from k8ssmash.art.poses import ANIMS
from k8ssmash.roster import roster
from k8ssmash.sprites import ASSETS, SpriteSet, pick_frame, slug
from k8ssmash.fighter import Fighter
from k8ssmash.stage import datacenter_stage


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    pygame.quit()


@pytest.mark.parametrize("stats", roster(), ids=lambda s: s.name)
def test_sheet_complete(stats):
    assert (ASSETS / f"{slug(stats.name)}.png").exists()
    meta = json.loads((ASSETS / f"{slug(stats.name)}.json").read_text())
    assert set(meta["anims"]) == set(ANIMS)
    sprites = SpriteSet(stats.name)
    for anim, (count, _, _) in ANIMS.items():
        assert len(sprites.frames[anim]) == count
        # every frame has drawn pixels
        assert all(pygame.mask.from_surface(fr).count() > 100 for fr in sprites.frames[anim]), anim


@pytest.mark.parametrize("stats", roster(), ids=lambda s: s.name)
def test_every_move_has_an_animation(stats):
    for key, move in stats.moves.items():
        assert (move.anim or key) in ANIMS, f"{stats.name}.{key} -> {move.anim!r}"


def test_pick_frame_follows_state():
    f = Fighter(roster()[0], 0)
    f.spawn(datacenter_stage().spawns[0], 1)
    f.state = "run"
    f.anim_frame = 5
    assert pick_frame(f)[0] == "run"
    f.state = "attack"
    f.move = f.stats.moves["special_up"]
    f.move_frame = 0
    assert pick_frame(f) == ("rise", 0)
    f.move_frame = f.move.startup
    assert pick_frame(f) == ("rise", 1)
    f.move_frame = f.move.total - 1
    assert pick_frame(f) == ("rise", 2)
