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
    for _ in range(120 * 60 + 1800):  # hit-stop freezes the clock, so a full-length match runs a bit past 7200 frames
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


# --- the results screen and the splash ---------------------------------------------------------------
def test_results_a_button_returns_to_the_main_menu(app):
    from k8ssmash.scenes.results import LOCK, Results
    app.set_scene(Results(app, 0, [{"name": "Pod", "kos": 1, "damage": 20, "stocks": 1},
                                   {"name": "Kubectl", "kos": 0, "damage": 5, "stocks": 0}], [True, True]))
    tap(app, {"SPECIAL"})  # too early: the screen is still locked so a mashed button can't skip it
    assert not isinstance(app.scene, Title)
    for _ in range(LOCK + 5):
        frame(app)
    tap(app, {"SPECIAL"})
    assert isinstance(app.scene, Title)


def test_results_draws_winner_loser_draw_and_mirror_match(app):
    from k8ssmash.scenes.results import Results
    rows = lambda a, b: [{"name": a, "kos": 1, "damage": 20, "stocks": 1}, {"name": b, "kos": 0, "damage": 5, "stocks": 0}]
    for winner, names in ((0, ("Pod", "Kubectl")), (1, ("Pod", "Kubectl")), (-1, ("Pod", "Kubectl")), (0, ("Pod", "Pod"))):
        scene = Results(app, winner, rows(*names), [True, True])
        for _ in range(40):
            scene.update()
        scene.draw(pygame.Surface((960, 540)))


def test_splash_runs_the_whole_roster_and_stays_responsive(app):
    t = Title(app)
    app.set_scene(t)
    for _ in range(600):
        frame(app)
    assert len(t.parade) == 8 and len(t.fx) > 0
    t.draw(pygame.Surface((960, 540)))
    tap(app, {"START"})
    assert isinstance(app.scene, CharacterSelect)


def test_splash_has_its_own_fast_happy_track(app):
    from k8ssmash.audio.songs import SONGS
    assert "splash" in SONGS and SONGS["splash"]().bpm >= 140
    Title(app)
    assert app.audio.current == "splash"


def test_menus_draw_at_native_resolution_with_no_rescaling(app):
    """Menus used to be drawn small and bilinear-stretched, which blurred them. They must draw straight onto the world canvas."""
    from k8ssmash.scenes.padtest import ControllerTest
    from k8ssmash.scenes.rebind import Rebind
    from k8ssmash.scenes.scoreboard import HighScores, NameEntry
    from k8ssmash.scenes.settings import Settings, SettingsPage
    from k8ssmash.scores import Prompt
    scenes = [Title(app), CharacterSelect(app), CharacterSelect(app, training=True), Settings(app), SettingsPage(app, "audio"), ControllerTest(app),
              Rebind(app), HighScores(app, on_done=lambda: None), NameEntry(app, Prompt(0, ["streak"], "Pod"), lambda n: None)]
    for scene in scenes:
        assert scene.native == app.display.canvas.get_size(), type(scene).__name__
        app.display.draw_scene(scene)
    assert app.display._scratch == {}  # nothing went through the scale-up path


def test_menu_text_is_rendered_at_real_size_but_reports_design_units():
    from k8ssmash import ui
    pygame.init()
    big = ui.UIFont(20).render("Hello", False, (255, 255, 255))
    real = pygame.Surface.get_width(big)
    assert real > big.get_width() and abs(real / big.get_width() - ui.SCALE) < 0.1  # drawn 1.5x, reported in design px
