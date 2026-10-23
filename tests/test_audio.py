import pytest

from k8ssmash.audio_manager import ASSETS, Audio, MUSIC_FOR_THEME
from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import READY_FRAMES, Battle
from k8ssmash.stage import STAGES


def test_all_expected_assets_exist():
    names = {"jump", "djump", "hit_light", "hit_heavy", "shield", "shield_break", "ko", "special", "pickup",
             "countdown", "go", "menu_move", "menu_select", "join", "counter", "explosion"}
    for n in names:
        assert (ASSETS / f"{n}.wav").stat().st_size > 500, n
    for n in set(MUSIC_FOR_THEME.values()) | {"title", "results"}:
        assert (ASSETS / f"{n}.ogg").stat().st_size > 10_000, n


def test_every_stage_theme_has_music():
    for make in STAGES:
        assert make().theme in MUSIC_FOR_THEME


def test_audio_survives_missing_files():
    a = Audio()
    a.play("does_not_exist")
    a.music("nope")
    a.music(None)


def test_mute_toggle():
    a = Audio()
    a.toggle_mute()
    assert a.muted
    a.toggle_mute()
    assert not a.muted


@pytest.fixture
def app():
    a = App(Config())
    a.input.poll = lambda: None
    return a


def test_battle_plays_countdown_music_and_game_sounds(app):
    b = Battle(app, roster()[:2], human=[False, False])
    app.set_scene(b)
    assert app.audio.current == MUSIC_FOR_THEME[b.stage.theme]
    for _ in range(READY_FRAMES + 2):
        b.update()
    assert app.audio.played.count("countdown") == 3 and "go" in app.audio.played
    a, v = b.fighters
    v.x = a.x + 10
    v.y = a.y
    b._hit(v, a, 3, 2, 0.02, 40, 1)
    b._hit(v, a, 12, 4, 0.05, 40, 1)
    assert "hit_light" in app.audio.played and "hit_heavy" in app.audio.played
    v.x = -999
    b.hitstop = 0
    b.update()
    assert "ko" in app.audio.played


def test_fighter_jump_events(app):
    from k8ssmash.fighter import Fighter
    from k8ssmash.input import PlayerInput
    from k8ssmash.stage import datacenter_stage
    st = datacenter_stage()
    f = Fighter(roster()[0], 0)
    f.spawn(st.spawns[0], 1)
    inp = PlayerInput()
    inp.update(set()); f.update(inp, st)
    inp.update({"JUMP"}); f.update(inp, st)
    assert f.events == ["jump"]
