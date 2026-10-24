import pygame
import pytest

from k8ssmash.ai import SimpleAI
from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.scenes.attract import Attract
from k8ssmash.scenes.battle import Battle
from k8ssmash.scenes.padtest import ControllerTest
from k8ssmash.scenes.results import Results
from k8ssmash.scenes.select import CharacterSelect
from k8ssmash.scenes.title import ATTRACT_AFTER, Title
from k8ssmash.roster import roster


@pytest.fixture
def app():
    a = App(Config())
    a.input.poll = lambda: None  # tests drive PlayerInput directly
    a.set_scene(Title(a))
    yield a
    pygame.quit()


def frame(app, p0=(), p1=()):
    app.input.players[0].update(set(p0))
    app.input.players[1].update(set(p1))
    app.step()


def tap(app, p0=(), p1=()):
    frame(app, p0, p1)
    frame(app)


def test_title_start_goes_to_select(app):
    tap(app, {"START"})
    assert isinstance(app.scene, CharacterSelect)


def test_title_idle_goes_to_attract_and_back_on_input(app):
    for _ in range(ATTRACT_AFTER + 1):
        frame(app)
    assert isinstance(app.scene, Attract)
    for _ in range(200):
        frame(app)
    assert isinstance(app.scene, Attract)  # demo is CPU vs CPU and keeps running
    tap(app, {"JUMP"})
    frame(app)
    assert isinstance(app.scene, Title)


def test_select_two_players_starts_battle(app):
    tap(app, {"START"})
    tap(app, {"START"}, {"START"})
    sel = app.scene
    assert sel.joined == [True, True]
    tap(app, {"ATTACK"}, {"RIGHT"})
    tap(app, {}, {"ATTACK"})
    assert sel.locked == [True, True]
    for _ in range(60):
        frame(app)
    assert isinstance(app.scene, Battle) and app.scene.human == [True, True]


def test_lone_player_gets_cpu_opponent(app):
    tap(app, {"START"})
    tap(app, {"START"})
    tap(app, {"SELECT"})
    sel = app.scene
    assert sel.cpu[1] and not sel.joined[1]
    tap(app, {"ATTACK"})
    for _ in range(60):
        frame(app)
    assert isinstance(app.scene, Battle) and app.scene.human == [True, False]


def test_select_back_unlocks(app):
    tap(app, {"START"})
    tap(app, {"START"})
    tap(app, {"ATTACK"})
    assert app.scene.locked[0]
    tap(app, {"SPECIAL"})
    assert not app.scene.locked[0]


def test_select_times_out_to_title(app):
    tap(app, {"START"})
    for _ in range(30 * 60 + 5):
        frame(app)
    assert isinstance(app.scene, Title)


def test_cpu_match_finishes_with_results_and_kos(app):
    r = roster()
    battle = Battle(app, r[:2], human=[False, False], demo=False)
    app.set_scene(battle)
    for _ in range(120 * 60 + 400):
        frame(app)
        if isinstance(app.scene, Results):
            break
    assert isinstance(app.scene, Results)


def test_results_rematch_and_select(app):
    app.set_scene(Results(app, 0, [{"name": "A", "kos": 1, "damage": 20, "stocks": 1},
                                   {"name": "B", "kos": 0, "damage": 5, "stocks": 0}]))
    for _ in range(50):
        frame(app)
    tap(app, {"START"})
    assert isinstance(app.scene, Battle)
    app.set_scene(Results(app, 1, [{"name": "A", "kos": 0, "damage": 0, "stocks": 0}] * 2))
    for _ in range(50):
        frame(app)
    tap(app, {"SELECT"})
    assert isinstance(app.scene, CharacterSelect)


def test_battle_idle_abort(app):
    app.set_scene(Battle(app, roster()[:2]))
    for _ in range(45 * 60 + 200):
        frame(app)
    assert isinstance(app.scene, Title)


def test_pad_unplug_pauses_battle(app):
    battle = Battle(app, roster()[:2])
    app.set_scene(battle)
    for _ in range(100):
        frame(app)
    t = battle.time_left
    app.input.lost.add(0)
    for _ in range(10):
        battle.update()
    assert battle.paused_for_pad and battle.time_left == t
    app.input.lost.clear()
    battle.update()
    assert battle.time_left == t - 1


def test_pad_unplug_of_cpu_slot_does_not_pause(app):
    battle = Battle(app, roster()[:2], human=[True, False])
    app.input.lost.add(1)
    assert not battle.paused_for_pad


def test_test_combo_toggles_controller_screen(app):
    for _ in range(100):
        frame(app, {"SELECT", "START"})
    assert isinstance(app.scene, ControllerTest)
    for _ in range(10):
        frame(app)  # release re-arms the combo
    for _ in range(100):
        frame(app, {"SELECT", "START"})
    assert isinstance(app.scene, Title)


def test_ai_returns_to_stage_when_off_left(app):
    battle = Battle(app, roster()[:2], human=[False, False])
    f = battle.fighters[0]
    f.x, f.y, f.on_ground = battle.stage.platforms[0].rect.left - 40, 300, False
    held = SimpleAI(f, battle.fighters[1], battle.stage, seed=1).decide()
    assert "RIGHT" in held


def test_kos_credited_to_last_attacker(app):
    battle = Battle(app, roster()[:2], human=[False, False])
    a, b = battle.fighters
    b.last_hit_by = a
    b.x = -500  # far outside the blast zone
    battle.frame = 1000
    battle.update()
    assert a.kos == 1 and b.stocks == 2


# --- character select: backing out and the move list ---------------------------------------------
def test_select_a_button_backs_out_to_the_title(app):
    tap(app, {"START"})
    assert isinstance(app.scene, CharacterSelect)
    tap(app, {"SPECIAL"})  # nobody has joined yet: A leaves
    assert isinstance(app.scene, Title)


def test_select_back_out_steps_lock_then_join_then_leave(app):
    tap(app, {"START"})
    tap(app, {"START"})  # P1 joins
    tap(app, {"ATTACK"})  # P1 locks in
    assert app.scene.locked[0]
    tap(app, {"SPECIAL"})
    assert not app.scene.locked[0] and app.scene.joined[0]
    tap(app, {"SPECIAL"})
    assert not app.scene.joined[0] and isinstance(app.scene, CharacterSelect)
    tap(app, {"SPECIAL"})
    assert isinstance(app.scene, Title)


def test_every_special_is_named_and_shown(app):
    from k8ssmash.roster import roster
    from k8ssmash.scenes.select import MOVE_ROWS
    for st in roster():
        for _, key, _ in MOVE_ROWS:
            move = st.moves[key]
            assert (move.announce or move.name).strip(), (st.name, key)
    sel = CharacterSelect(app)
    sel.joined, sel.cursor = [True, True], [0, 7]
    sel.draw(app.display.canvas)  # renders every panel without error
