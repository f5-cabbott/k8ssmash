import random

import pytest

from k8ssmash.fighter import BUFF_ARMOR, BUFF_GUARD, BUFF_HASTE, BUFF_POWER, BUFF_SCALED, Fighter
from k8ssmash.input import PlayerInput
from k8ssmash.items import FIRST_SPAWN, ITEM_LIFE, ITEMS, MAX_ITEMS, ItemSpawner
from k8ssmash.roster import roster
from k8ssmash.stage import datacenter_stage


@pytest.fixture
def stage():
    return datacenter_stage()


def fighter(stage):
    f = Fighter(roster()[0], 0)
    f.spawn(stage.spawns[0], 1)
    return f


def test_nine_k8s_items():
    assert len(ITEMS) == 9 and len({i.glyph for i in ITEMS.values()}) == 9


def test_first_item_spawns_and_lands_on_a_platform(stage):
    sp = ItemSpawner(random.Random(1))
    for _ in range(FIRST_SPAWN + 400):
        sp.update(stage, [])
    assert sp.items and sp.items[0].landed
    assert any(sp.items[0].y == p.rect.top for p in stage.platforms)


def test_spawner_caps_items_and_expires_them(stage):
    sp = ItemSpawner(random.Random(2))
    for _ in range(30 * 60 * 5):
        sp.update(stage, [])
        assert len(sp.items) <= MAX_ITEMS
    sp.items.clear()
    item = sp.spawn(stage)
    for _ in range(ITEM_LIFE + 5):
        item.update(stage)
    sp.update(stage, [])
    assert item not in sp.items


def test_disabled_spawner_never_spawns(stage):
    sp = ItemSpawner(random.Random(3), enabled=False)
    for _ in range(FIRST_SPAWN * 3):
        sp.update(stage, [])
    assert not sp.items


@pytest.mark.parametrize("key,check", [
    ("hpa", lambda f: f.has(BUFF_POWER) and f.has(BUFF_SCALED) and f.damage_mult > 1),
    ("cordon", lambda f: f.has(BUFF_ARMOR)),
    ("pdb", lambda f: f.has(BUFF_GUARD) and f.taken_mult == 0.5),
    ("probe", lambda f: f.has(BUFF_HASTE)),
    ("undo", lambda f: f.percent == 15),
    ("sidecar", lambda f: len(f.spawn_queue) == 1 and f.spawn_queue[0].defn.orbit),
    ("chaos", lambda f: len(f.spawn_queue) == 1 and f.spawn_queue[0].defn.explode_radius > 0
     and f.spawn_queue[0].defn.harmless_to_owner),
    ("canary", lambda f: f.has("canary")),
])
def test_pickup_applies_effect(stage, key, check):
    f = fighter(stage)
    f.percent = 50
    sp = ItemSpawner(random.Random(4), enabled=False)
    item = sp.spawn(stage, key)
    item.x, item.y, item.landed = f.x, f.y, True
    picked = sp.update(stage, [f])
    assert picked and picked[0][1] is item and not sp.items
    assert f.callout == ITEMS[key].name
    assert check(f)


def test_dead_fighter_cannot_pick_up(stage):
    f = fighter(stage)
    f.ko_timer = 10
    sp = ItemSpawner(random.Random(5), enabled=False)
    item = sp.spawn(stage, "hpa")
    item.x, item.y, item.landed = f.x, f.y, True
    assert not sp.update(stage, [f])


def test_buffs_expire(stage):
    f = fighter(stage)
    f.add_buff(BUFF_HASTE, 5)
    p = PlayerInput()
    for _ in range(6):
        f.update(p, stage)
    assert not f.has(BUFF_HASTE) and f.speed_mult == 1.0
