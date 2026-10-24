import pygame
import pytest

from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.scenes.settings import ROWS, STEP, Settings
from k8ssmash.scenes.title import Title


@pytest.fixture
def app():
    a = App(Config())
    a.input.poll = lambda: None
    a.set_scene(Title(a))
    yield a
    pygame.quit()


def frame(app, p0=(), p1=()):
    app.input.players[0].update(set(p0))
    app.input.players[1].update(set(p1))
    app.step()


def tap(app, p0=()):
    frame(app, p0)
    frame(app)


def test_holding_shield_on_the_title_opens_settings_but_a_tap_does_not(app):
    tap(app, {"SHIELD"})
    assert isinstance(app.scene, Title)
    for _ in range(45):
        frame(app, {"SHIELD"})
    assert isinstance(app.scene, Settings)


def test_volume_sliders_change_config_and_the_live_audio(app):
    s = Settings(app)
    app.set_scene(s)
    start = app.cfg.master_volume
    tap(app, {"LEFT"})
    assert app.cfg.master_volume == pytest.approx(start - STEP) and app.audio.master == pytest.approx(start - STEP)
    tap(app, {"DOWN"})
    tap(app, {"RIGHT"})
    assert app.cfg.sfx_volume == pytest.approx(0.55 + STEP) and app.audio.sfx_volume == pytest.approx(0.55 + STEP)
    tap(app, {"DOWN"})
    for _ in range(3):
        tap(app, {"LEFT"})
    assert app.cfg.music_volume == pytest.approx(0.4 - 3 * STEP) and app.audio.music_volume == pytest.approx(0.4 - 3 * STEP)


def test_sliders_clamp_and_holding_repeats(app):
    app.set_scene(Settings(app))
    for _ in range(40):
        tap(app, {"LEFT"})
    assert app.cfg.master_volume == 0.0
    app.cfg.master_volume = 0.5
    for _ in range(60):
        frame(app, {"RIGHT"})  # held, no taps
    assert app.cfg.master_volume > 0.6


def test_toggles_and_saving(app, tmp_path):
    s = Settings(app)
    app.set_scene(s)
    for _ in range(3):
        tap(app, {"DOWN"})
    assert ROWS[s.row][0] == "mute"
    tap(app, {"RIGHT"})
    assert app.cfg.muted and app.audio.muted
    tap(app, {"ATTACK"})  # attack toggles the row back
    assert not app.cfg.muted
    tap(app, {"DOWN"})
    tap(app, {"RIGHT"})
    assert app.cfg.colorblind
    for _ in range(12):
        frame(app)
    tap(app, {"START"})  # saves and leaves
    assert isinstance(app.scene, Title)
    assert Config.load().colorblind


def test_master_volume_scales_both_effects_and_music(app):
    app.audio.set_volumes(master=0.5, sfx=0.6, music=0.4)
    assert app.audio.master == 0.5
    app.audio.set_volumes(master=2.0)
    assert app.audio.master == 1.0  # clamped
    app.audio.set_volumes(sfx=-1)
    assert app.audio.sfx_volume == 0.0


def test_settings_screen_draws(app):
    s = Settings(app)
    for row in range(len(ROWS)):
        s.row = row
        s.draw(pygame.Surface((640, 360)))
