import math

import pygame
import pytest

from k8ssmash.config import Config
from k8ssmash.fighter import Fighter
from k8ssmash.input import PlayerInput
from k8ssmash.main import App
from k8ssmash.particles import MAX_PARTICLES, Particles
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import READY_FRAMES, Battle
from k8ssmash.sprites import pick_frame
from k8ssmash.stage import datacenter_stage


@pytest.fixture
def app():
    a = App(Config())
    a.input.poll = lambda: None
    yield a
    pygame.quit()


def started(app, **kw):
    b = Battle(app, roster()[:2], human=[False, False], **kw)
    app.set_scene(b)
    b.frame = READY_FRAMES + 1
    return b


def test_particles_age_out_and_are_capped():
    ps = Particles(seed=1)
    ps.burst(100, 100, (255, 255, 255), count=20)
    assert len(ps) == 20
    for _ in range(60):
        ps.update()
    assert len(ps) == 0
    for _ in range(100):
        ps.confetti(0, 0, 10)
    assert len(ps) <= MAX_PARTICLES


def test_every_particle_kind_draws():
    ps = Particles(seed=2)
    ps.dust(50, 50, 1.0)
    ps.ring(60, 60)
    ps.burst(70, 70, (255, 0, 0), 4, kind="square")
    ps.burst(70, 70, (255, 0, 0), 4)
    ps.star(80, 80, (255, 200, 0))
    ps.confetti(90, 0, 3)
    ps.sparkle(40, 40)
    ps.streak(30, 30, 8, -3)
    canvas = pygame.Surface((200, 200))
    for _ in range(40):
        ps.draw(canvas)
        ps.update()


def test_landing_squashes_and_kicks_up_dust(app):
    b = started(app)
    f = b.fighters[0]
    f.y -= 80
    f.on_ground = False
    stage = datacenter_stage()
    inp = PlayerInput()
    for _ in range(60):
        f.update(inp, stage)
        if f.land_timer:
            break
    assert f.land_timer > 0 and any(kind == "land" for kind, _ in f.fx)
    f.state = "idle"
    assert pick_frame(f)[0] == "land"  # the squash frame while the timer runs
    before = len(b.fx)
    b._fighter_fx(f)
    assert len(b.fx) > before and not f.fx


def test_jump_frames_follow_the_velocity():
    f = Fighter(roster()[0], 0)
    f.state, f.vy = "jump", -6.0
    assert pick_frame(f) == ("jump", 0)  # rising: stretched
    f.vy = -1.0
    assert pick_frame(f) == ("jump", 1)  # apex
    f.state, f.vy = "fall", 6.5
    assert pick_frame(f) == ("fall", 1)


def test_idle_blinks_every_few_seconds():
    f = Fighter(roster()[0], 0)
    f.state = "idle"
    seen = set()
    for n in range(0, 420):
        f.anim_frame = n
        seen.add(pick_frame(f)[1])
    assert {6, 7} <= seen and {0, 3} <= seen  # blink frames plus the breathing loop


def test_hits_burst_in_proportion_to_damage(app):
    b = started(app)
    a, v = b.fighters
    v.x, v.y, a.x = 400, a.y, 380
    b._hit(v, a, 3, 2, 0.02, 40, 1)
    small = len(b.fx)
    b.fx.items.clear()
    b._hit(v, a, 14, 5, 0.08, 40, 1)
    assert len(b.fx) > small


def test_ko_throws_a_star_at_the_screen_edge(app):
    b = started(app)
    v = b.fighters[1]
    v.x = -400  # well past the blast zone
    b.hitstop = 0
    b.update()
    stars = [p for p in b.fx.items if p.kind == "star"]
    assert stars and 20 <= stars[0].x <= 60  # clamped to the left edge, not off screen


def test_dash_leaves_afterimages_without_flicker(app):
    b = started(app)
    f = b.fighters[0]
    f.move = f.stats.moves["special_side"]
    f.move_frame = f.move.startup + 1
    f.state = "attack"
    canvas = pygame.Surface((960, 540))
    for i in range(8):
        b.frame += 1
        b._draw_fighter(canvas, f)
    assert 1 <= len(b.ghosts[0]) <= 4
    alphas = [g[0].get_alpha() for g in b.ghosts[0]]
    assert alphas == sorted(alphas)  # older ghosts are always fainter: a smooth fade


def test_no_strobing_sprite_visible_every_frame_while_invulnerable(app):
    b = started(app)
    f = b.fighters[0]
    f.invuln = 90
    canvas = pygame.Surface((960, 540))
    for i in range(30):
        canvas.fill((0, 0, 0))
        b.frame += 1
        b._draw_fighter(canvas, f)
        assert pygame.mask.from_threshold(canvas, (0, 0, 0), (1, 1, 1)).count() < 960 * 540  # something is drawn every frame


def test_heavy_hit_star_draws_and_settles():
    import pygame
    from k8ssmash.fx import draw_effect
    canvas = pygame.Surface((200, 200))
    sizes = []
    for left in (13, 10, 6, 2):
        canvas.fill((0, 0, 0))
        draw_effect(canvas, "hit_heavy", 100, 100, left)
        sizes.append(sum(1 for x in range(0, 200, 2) for y in range(0, 200, 2) if canvas.get_at((x, y))[:3] != (0, 0, 0)))
    assert sizes[1] > sizes[0] > 0 and sizes[3] < sizes[1]  # pops out, then shrinks away: no flashing


def _arena():
    from k8ssmash.config import Config
    from k8ssmash.main import App
    from k8ssmash.roster import roster
    from k8ssmash.scenes.battle import READY_FRAMES, Battle
    from k8ssmash.stage import STAGES
    app = App(Config())
    app.input.poll = lambda: None
    b = Battle(app, roster()[:2], stage=STAGES[0](), human=[False, False], items=False)
    app.set_scene(b)
    for _ in range(READY_FRAMES + 5):
        b.update()
    return b


def test_grab_beats_a_shield_and_the_stick_picks_the_throw():
    b = _arena()
    a, v = b.fighters
    a.x, a.y, a.facing, a.on_ground = 400.0, 400.0, 1, True
    v.x, v.y, v.on_ground = 420.0, 400.0, True
    v.shielding = True
    v.invuln = a.invuln = 0
    a.last_axis = (0, 0)
    before = v.percent
    assert b._throw(a, v)
    assert v.percent > before and not v.shielding and v.vx > 0  # forward throw sends them away from the thrower
    v.hitstun = 0
    a.last_axis = (0, -1)
    v.percent = 0
    b._throw(a, v)
    assert v.vy < -2.5  # up throw launches high


def test_combo_counter_counts_chained_hits_and_resets():
    b = _arena()
    a, v = b.fighters
    v.invuln = 0
    for _ in range(3):
        v.invuln = 0
        b._hit(v, a, 3, 2.0, 0.02, 40, 1)  # each lands while the last still stuns
    assert b.combos[a.slot][0] == 3
    v.hitstun = 0
    v.invuln = 0
    b._hit(v, a, 3, 2.0, 0.02, 40, 1)
    assert b.combos[a.slot][0] == 1  # a fresh exchange starts over


def test_second_wind_only_on_the_last_stock_when_behind():
    b = _arena()
    a, v = b.fighters
    a.stocks, v.stocks = 1, 3
    b._second_wind(a)
    assert a.comeback and a.damage_mult > 1.1 and a.speed_mult > 1.0
    b._second_wind(v)
    assert not v.comeback
    b2 = _arena()
    for f in b2.fighters:
        f.stocks = 1
    b2._second_wind(b2.fighters[0])
    assert not b2.fighters[0].comeback  # no boost when the opponent is also on the last stock
