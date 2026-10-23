import pygame
import pytest

from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.palette import COLORBLIND, DEFAULT, damage_color, player_colors
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import KO_REASONS, READY_FRAMES, SLOWMO_FRAMES, Battle


@pytest.fixture
def app():
    a = App(Config())
    a.input.poll = lambda: None
    yield a
    pygame.quit()


def started(app, stocks=3):
    b = Battle(app, roster()[:2], human=[False, False], stocks=stocks)
    b.demo = False
    app.set_scene(b)
    b.frame = READY_FRAMES + 1
    return b


def test_palette_choices_and_severity():
    assert player_colors(Config()) == DEFAULT
    assert player_colors(Config(colorblind=True)) == COLORBLIND
    assert len(set(DEFAULT)) == len(set(COLORBLIND)) == 2
    colors = [damage_color(p) for p in (0, 50, 100, 200)]
    assert len(set(colors)) == 4


def test_ko_posts_a_k8s_status_banner(app):
    b = started(app)
    b.fighters[1].x = -999
    b.update()
    assert b.banners and any(r in b.banners[-1][0] for r in KO_REASONS)
    assert b.fighters[1].stats.name in b.banners[-1][0]


def test_banner_expires_and_queue_is_capped(app):
    b = started(app)
    for i in range(5):
        b.announce(f"msg {i}")
    assert len(b.banners) == 2
    for _ in range(100):
        b.update()
    assert not b.banners


def test_final_ko_triggers_slow_motion_before_the_winner_is_declared(app):
    b = started(app, stocks=1)
    b.fighters[1].x = -999
    b.update()
    assert b.fighters[1].eliminated
    assert b.slowmo > 0 and b.winner is None  # the finish is delayed so the KO can play out
    t0 = b.time_left
    for _ in range(40):
        b.update()
    assert 8 <= t0 - b.time_left <= 12  # ~quarter speed: 40 frames -> ~10 logic ticks
    for _ in range(SLOWMO_FRAMES + 5):
        b.update()
    assert b.winner == 0


def test_non_final_ko_has_no_slow_motion(app):
    b = started(app, stocks=3)
    b.fighters[1].x = -999
    b.update()
    assert b.slowmo == 0 and b.winner is None


def test_hud_pulse_on_hit(app):
    b = started(app)
    a, v = b.fighters
    v.x, v.y = a.x + 10, a.y
    b._hit(v, a, 5, 2, 0.02, 40, 1)
    assert b.hud_pulse[v.slot] > 0


def test_every_status_draws(app):
    b = started(app)
    b.announce("Pod: OOMKilled", b.colors[0])
    b.slowmo = 50
    b.frame = 0
    b.draw(app.display.canvas)
    b.frame = READY_FRAMES + 20
    b.draw(app.display.canvas)
    b.winner = 0
    b.draw(app.display.canvas)
