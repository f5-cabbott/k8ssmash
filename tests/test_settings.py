import pygame
import pytest

from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.scenes.settings import HUB, PAGES, ROWS, STEP, Settings, SettingsPage
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


def test_title_menu_opens_settings_with_a_and_the_hub_enters_pages_with_a(app):
    tap(app, {"DOWN"})
    tap(app, {"DOWN"})
    tap(app, {"DOWN"})
    tap(app, {"SPECIAL"})
    assert isinstance(app.scene, Settings)
    for _ in range(12):  # a press carried over from the title must not trigger the first row
        frame(app)
    tap(app, {"DOWN"})
    tap(app, {"UP"})
    assert HUB[app.scene.row] == "audio"
    tap(app, {"DOWN"})
    tap(app, {"SPECIAL"})
    assert isinstance(app.scene, SettingsPage) and app.scene.page == "display"
    for _ in range(12):
        frame(app)
    tap(app, {"ATTACK"})  # B backs out to the hub, on the row we came from
    assert isinstance(app.scene, Settings) and HUB[app.scene.row] == "display"
    for _ in range(12):
        frame(app)
    tap(app, {"ATTACK"})
    assert isinstance(app.scene, Title)


def test_holding_shield_no_longer_opens_settings(app):
    for _ in range(60):
        frame(app, {"SHIELD"})
    assert isinstance(app.scene, Title)


def test_volume_sliders_change_config_and_the_live_audio(app):
    app.set_scene(SettingsPage(app, "audio"))
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
    app.set_scene(SettingsPage(app, "audio"))
    for _ in range(40):
        tap(app, {"LEFT"})
    assert app.cfg.master_volume == 0.0
    app.cfg.master_volume = 0.5
    for _ in range(60):
        frame(app, {"RIGHT"})  # held, no taps
    assert app.cfg.master_volume > 0.6


def test_toggles_and_saving(app, tmp_path):
    s = SettingsPage(app, "audio")
    app.set_scene(s)
    for _ in range(3):
        tap(app, {"DOWN"})
    assert s.rows[s.row][0] == "mute"
    tap(app, {"RIGHT"})
    assert app.cfg.muted and app.audio.muted
    for _ in range(12):
        frame(app)
    tap(app, {"SPECIAL"})  # A flips a toggle back
    assert not app.cfg.muted
    app.set_scene(SettingsPage(app, "display"))
    for _ in range(12):
        frame(app)
    for _ in range(3):
        tap(app, {"DOWN"})
    assert app.scene.rows[app.scene.row][0] == "colorblind"
    tap(app, {"RIGHT"})
    assert app.cfg.colorblind
    tap(app, {"START"})  # saves and goes back to the hub
    assert isinstance(app.scene, Settings)
    assert Config.load().colorblind


def test_gameplay_page_sets_stocks_and_time_which_battles_use(app):
    from k8ssmash.roster import roster
    from k8ssmash.scenes.battle import Battle
    app.set_scene(SettingsPage(app, "gameplay"))
    tap(app, {"RIGHT"})
    assert app.cfg.stocks == 4
    tap(app, {"DOWN"})
    tap(app, {"RIGHT"})
    assert app.cfg.match_seconds == 180
    b = Battle(app, roster()[:2])
    assert [f.stocks for f in b.fighters] == [4, 4] and b.time_left == 180 * 60


def test_controls_page_opens_the_tools_on_top_of_the_menu(app):
    from k8ssmash.scenes.padtest import ControllerTest
    from k8ssmash.scenes.rebind import Rebind
    app.set_scene(SettingsPage(app, "controls"))
    for _ in range(12):
        frame(app)
    tap(app, {"SPECIAL"})
    assert isinstance(app.scene, Rebind)
    app.pop_scene()
    tap(app, {"DOWN"})
    tap(app, {"SPECIAL"})
    assert isinstance(app.scene, ControllerTest)


def test_master_volume_scales_both_effects_and_music(app):
    app.audio.set_volumes(master=0.5, sfx=0.6, music=0.4)
    assert app.audio.master == 0.5
    app.audio.set_volumes(master=2.0)
    assert app.audio.master == 1.0  # clamped
    app.audio.set_volumes(sfx=-1)
    assert app.audio.sfx_volume == 0.0


def test_settings_screens_draw(app):
    hub = Settings(app)
    for row in range(len(HUB)):
        hub.row = row
        hub.draw(pygame.Surface((960, 540)))
    for page in PAGES:
        s = SettingsPage(app, page)
        for row in range(len(s.rows)):
            s.row = row
            s.draw(pygame.Surface((960, 540)))
