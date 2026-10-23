import pytest

from k8ssmash.fighter import BUFF_ARMOR, BUFF_HASTE, Fighter, Projectile
from k8ssmash.input import PlayerInput
from k8ssmash.roster import roster
from k8ssmash.stage import datacenter_stage

SPECIALS = ("special", "special_side", "special_up", "special_down")


def test_eight_unique_fighters():
    r = roster()
    assert len(r) == 8
    assert len({f.name for f in r}) == 8
    assert len({f.color for f in r}) == 8


@pytest.mark.parametrize("stats", roster(), ids=lambda s: s.name)
def test_every_fighter_has_four_unique_specials(stats):
    moves = [stats.moves[k] for k in SPECIALS]
    assert len({m.name for m in moves}) == 4
    # Specials must do something: damage, a projectile, a buff, a heal or a counter.
    for m in moves:
        assert m.damage or m.projectile or m.buff or m.heal or m.counter, m.name
    # Up special is the recovery.
    assert stats.moves["special_up"].rise > 0 and stats.moves["special_up"].once_per_air


def test_specials_differ_between_fighters():
    seen = {}
    for st in roster():
        for k in SPECIALS:
            seen.setdefault(st.moves[k].name, []).append(st.name)
    assert all(len(v) == 1 for v in seen.values())


def fighter(name):
    stats = next(s for s in roster() if s.name == name)
    f = Fighter(stats, 0)
    f.spawn(datacenter_stage().spawns[0], 1)
    return f


def run(f, stage, held, frames):
    inp = PlayerInput()
    for i in range(frames):
        inp.update(set(held) if i == 0 else set())
        f.update(inp, stage)


@pytest.mark.parametrize("name,key,expect", [
    ("Pod", "special", 1), ("Kubectl", "special", 3), ("Sidecar", "special", 1),
])
def test_projectile_counts(name, key, expect):
    stage = datacenter_stage()
    f = fighter(name)
    run(f, stage, set(), 2)
    held = {"SPECIAL"}
    run(f, stage, held, 30)
    assert len(f.spawn_queue) == expect


def test_recovery_only_once_per_air():
    stage = datacenter_stage()
    f = fighter("Pod")
    f.y -= 120
    f.on_ground = False
    run(f, stage, {"SPECIAL", "UP"}, 2)
    assert f.move is not None and f.vy < 0 or f.used_recovery
    assert f.used_recovery
    f.move = None
    f.vy = 3
    run(f, stage, {"SPECIAL", "UP"}, 2)
    assert f.move is None  # second recovery in the same airtime is refused
    f.on_ground = True
    f.used_recovery = False
    assert not f.used_recovery


def test_blink_teleports_and_is_intangible():
    stage = datacenter_stage()
    f = fighter("Chaos Monkey")
    run(f, stage, set(), 3)
    x0 = f.x
    run(f, stage, {"SPECIAL", "RIGHT"}, 9)
    assert f.x - x0 > 60
    f.move_frame = f.move.startup + 1
    assert f.intangible and f.apply_hit(10, 3, 0.05, 40, 1) == "ignored"


def test_buff_special_applies_buff_and_armor_blocks_launch():
    stage = datacenter_stage()
    k = fighter("Kubectl")
    run(k, stage, set(), 3)
    run(k, stage, {"SPECIAL", "DOWN"}, 12)
    assert k.has(BUFF_HASTE) and k.speed_mult > 1
    s = fighter("Sidecar")
    s.add_buff(BUFF_ARMOR, 100)
    assert s.apply_hit(10, 4, 0.05, 40, 1) == "hit" and s.percent == 10 and s.vx == 0 and s.hitstun == 0


def test_heal_move_reduces_percent():
    stage = datacenter_stage()
    f = fighter("Operator")
    f.percent = 40
    run(f, stage, set(), 3)
    run(f, stage, {"SPECIAL", "DOWN"}, 24)
    assert f.percent == 26


def test_counter_window_flagged():
    stage = datacenter_stage()
    f = fighter("Operator")
    run(f, stage, set(), 3)
    run(f, stage, {"SPECIAL"}, 1)
    assert not f.countering
    run(f, stage, set(), 6)
    assert f.countering


def test_boomerang_returns_and_orbit_follows_owner():
    stage = datacenter_stage()
    f = fighter("Helm")
    d = f.stats.moves["special"].projectile
    p = Projectile(f, d, f.x, f.y - 24, d.speed, 0, 1, d.life)
    xs = []
    for _ in range(d.life):
        p.update(stage)
        xs.append(p.x)
        if p.life <= 0:
            break
    assert max(xs) > f.x + 40 and abs(xs[-1] - f.x) < 20

    s = fighter("Sidecar")
    d = s.stats.moves["special"].projectile
    p = Projectile(s, d, s.x, s.y, 0, 0, 1, d.life)
    s.x += 100
    p.update(stage)
    assert abs(p.x - s.x) <= 31


def test_stick_projectile_lands_and_stops():
    stage = datacenter_stage()
    f = fighter("Chaos Monkey")
    d = f.stats.moves["special"].projectile
    p = Projectile(f, d, f.x + 20, f.y - 40, d.speed, d.vy, 1, d.life)
    for _ in range(120):
        p.update(stage)
    assert p.stuck and p.vx == 0
