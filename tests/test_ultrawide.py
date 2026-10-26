import pygame
import pytest

from k8ssmash import backdrops
from k8ssmash.config import PIX_H, PIX_W, RS, Config
from k8ssmash.main import App
from k8ssmash.render import Display
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import READY_FRAMES, Battle
from k8ssmash.scenes.title import Title
from k8ssmash.stage import STAGES


@pytest.fixture
def ultrawide(monkeypatch):
    monkeypatch.setattr(Display, "desktop_size", staticmethod(lambda: (3440, 1440)))
    pygame.init()
    yield
    pygame.quit()


def display(**cfg):
    c = Config()
    for k, v in cfg.items():
        setattr(c, k, v)
    return Display(c)


@pytest.mark.parametrize("desktop,expected", [((1920, 1080), 960), ((2560, 1440), 960), ((3440, 1440), 1290),
                                              ((2560, 1080), 1280), ((1920, 1200), 960), ((5120, 1440), 1296)])
def test_fullscreen_canvas_follows_the_display_aspect(monkeypatch, desktop, expected):
    monkeypatch.setattr(Display, "desktop_size", staticmethod(lambda: desktop))
    pygame.init()
    d = display(fullscreen=True, shape="auto")
    assert d.canvas.get_size() == (expected * RS, PIX_H)
    assert d.play_rect.width == PIX_W and d.play_rect.centerx == expected * RS // 2  # the arena stays centred
    assert d.play.get_size() == (PIX_W, PIX_H)


def test_the_scaled_canvas_exactly_fills_an_ultrawide_screen(ultrawide):
    d = display(fullscreen=True, shape="auto")
    cw = d.canvas.get_width()
    assert abs(cw / PIX_H - 3440 / 1440) < 0.01  # same aspect as the screen: no black bars


def test_default_is_16_by_9_and_explicit_21_by_9_widens(ultrawide):
    assert display().canvas.get_size() == (PIX_W, PIX_H)
    assert display(fullscreen=True).canvas.get_size() == (PIX_W, PIX_H)  # even fullscreen on an ultrawide: true 16:9 by default
    d = display(shape="21:9")
    assert d.canvas.get_size() == (1260 * RS, PIX_H)
    w, h = d.window_size()
    assert abs(w / h - 1260 / 540) < 0.02 and h <= 1440 * 0.86  # a wide window that still fits the desktop
    assert display(shape="16:9", fullscreen=True).canvas.get_width() == PIX_W


def test_changing_aspect_rebuilds_the_canvas_and_saves(ultrawide, tmp_path, monkeypatch):
    monkeypatch.setenv("K8SSMASH_CONFIG", str(tmp_path / "c.json"))
    d = display()
    d.set_aspect("21:9")
    assert d.canvas.get_width() == 1260 * RS
    assert Config.load().shape == "21:9"
    d.set_aspect("nonsense")
    assert d.cfg.shape == "16:9"


@pytest.mark.parametrize("theme", ["datacenter", "controlplane", "nodepool"])
@pytest.mark.parametrize("cw", [960, 1290])
def test_backdrops_cover_a_wide_canvas_edge_to_edge(ultrawide, theme, cw):
    canvas = pygame.Surface((cw * RS, PIX_H))
    for cam in (-200, 0, 200):
        canvas.fill((255, 0, 255))
        backdrops.draw_backdrop(canvas, theme, 300, cam)
        gaps = sum(1 for x in range(0, cw * RS, 30) for y in range(0, PIX_H, 30) if canvas.get_at((x, y))[:3] == (255, 0, 255))
        assert gaps == 0, f"{theme} cw={cw} cam={cam}: scenery stopped short of the edge"


def test_a_wide_battle_draws_the_arena_in_the_middle(ultrawide):
    app = App(Config(shape="21:9"))
    app.input.poll = lambda: None
    b = Battle(app, roster()[:2], stage=STAGES[0](), human=[False, False], items=False)
    app.set_scene(b)
    for _ in range(READY_FRAMES + 30):
        b.update()
    app.display.draw_scene(b)
    canvas = app.display.canvas
    assert canvas.get_width() == 1260 * RS
    # platforms land in the centred arena area, the scenery continues out to both screen edges
    left_edge = canvas.get_at((4, PIX_H // 2))[:3]
    assert left_edge != (0, 0, 0) or canvas.get_at((4, 100 * RS))[:3] != (0, 0, 0)
    platform_x = (150 + 300) * RS + app.display.play_rect.left  # the main floor's neon edge sits inside the arena area
    top = STAGES[0]().platforms[0].rect.top
    # scan a stretch of the floor so a fighter standing on one spot cannot hide the edge
    assert max(canvas.get_at((platform_x + dx, top * RS + dy))[:3] for dx in range(0, 200 * RS, 10) for dy in range(0, 4 * RS))[2] > 100  # a bright edge pixel


def test_menus_sit_centred_on_border_art(ultrawide):
    app = App(Config(shape="21:9"))
    app.input.poll = lambda: None
    t = Title(app)
    for _ in range(30):
        t.update()
    app.display.draw_scene(t)
    canvas = app.display.canvas
    side, centre = canvas.get_at((20, PIX_H // 2))[:3], canvas.get_at((630 * RS, PIX_H // 2))[:3]
    assert side != (0, 0, 0)  # the border art, not black bars
    assert side != centre
    # and nothing is stretched: the logo's centre column stays at the middle of the wider canvas
    assert app.display.play_rect.centerx == 630 * RS


def test_settings_changes_screen_shape_and_fullscreen(ultrawide, tmp_path, monkeypatch):
    from k8ssmash.scenes.settings import PAGES, SettingsPage
    monkeypatch.setenv("K8SSMASH_CONFIG", str(tmp_path / "c.json"))
    app = App(Config())
    app.input.poll = lambda: None
    s = SettingsPage(app, "display")
    s.adjust("aspect", 1)  # 16:9 -> 21:9
    assert app.cfg.shape == "21:9" and app.display.canvas.get_width() == 1260 * RS
    s.adjust("size", 1)
    assert (app.cfg.width, app.cfg.height) in app.display.sizes()
    assert [r[0] for r in PAGES["display"][2]][:3] == ["fullscreen", "aspect", "size"]
    s.frame = 20
    app.display.draw_scene(s)  # draws centred on border art without error
