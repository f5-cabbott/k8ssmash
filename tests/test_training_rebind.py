import pygame
import pytest

from k8ssmash.config import Config
from k8ssmash.main import App, apply_args, parse_args
from k8ssmash.roster import roster
from k8ssmash.scenes.padtest import ControllerTest
from k8ssmash.scenes.rebind import STEPS, Rebind
from k8ssmash.scenes.select import CharacterSelect
from k8ssmash.scenes.title import Title
from k8ssmash.scenes.training import DUMMY_MODES, EXIT_HOLD, Training


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


def tap(app, p0=(), p1=()):
    frame(app, p0, p1)
    frame(app)


def test_title_special_opens_training_select_and_starts_training(app):
    tap(app, {"SPECIAL"})
    assert isinstance(app.scene, CharacterSelect) and app.scene.training
    tap(app, {"START"})
    tap(app, {"ATTACK"})
    for _ in range(60):
        frame(app)
    assert isinstance(app.scene, Training)
    assert app.scene.fighters[0].stats is not app.scene.fighters[1].stats


def make_training(app):
    t = Training(app, roster()[:2])
    app.set_scene(t)
    return t


def test_training_has_no_clock_stocks_or_end(app):
    t = make_training(app)
    t0 = t.time_left
    t.fighters[1].x = -999
    for _ in range(300):
        frame(app)
    assert t.time_left == t0 and t.winner is None and t.fighters[1].stocks == 99
    assert t.fighters[1].alive or t.fighters[1].ko_timer >= 0


def test_dummy_modes_cycle_and_behave(app):
    t = make_training(app)
    assert DUMMY_MODES[t.mode] == "Stand"
    tap(app, {"SELECT"})
    assert DUMMY_MODES[t.mode] == "Shield"
    for _ in range(5):
        frame(app)
    assert t.fighters[1].shielding
    tap(app, {"SELECT"})
    assert DUMMY_MODES[t.mode] == "Jump"


def test_combo_and_damage_tracking(app):
    t = make_training(app)
    a, d = t.fighters
    d.x, d.y = a.x + 10, a.y
    t._hit(d, a, 4, 2, 0.02, 40, 1)
    t.frame += 10
    t._hit(d, a, 6, 2, 0.02, 40, 1)
    assert t.combo == 2 and t.last_damage == 6 and t.combo_damage == 10 and t.best_combo == 2
    t.frame += 200
    frame(app)
    assert t.combo == 0 and t.best_combo == 2


def test_start_tap_resets_and_hold_leaves(app):
    t = make_training(app)
    t.fighters[1].percent = 80
    t.fighters[0].x += 50
    tap(app, {"START"})
    assert t.fighters[1].percent == 0 and t.fighters[0].x == t.stage.spawns[0][0]
    for _ in range(EXIT_HOLD + 2):
        frame(app, {"START"})
    assert isinstance(app.scene, CharacterSelect) and app.scene.training


def test_training_draws(app):
    t = make_training(app)
    t.draw(app.display.canvas)


# --- rebind -------------------------------------------------------------------------------------
def joy(button):
    return pygame.event.Event(pygame.JOYBUTTONDOWN, button=button, instance_id=0)


def test_rebind_full_sequence_saves_mapping(app):
    done = []
    r = Rebind(app, on_done=lambda: done.append(1))
    app.set_scene(r)
    for b in (4, 5, 6, 7, 8, 1, 2):
        r.handle_event(joy(b))
    assert r.finished
    assert app.cfg.pad["JUMP"] == [4] and app.cfg.pad["ATTACK"] == [5] and app.cfg.pad["SPECIAL"] == [6]
    assert app.cfg.pad["SHIELD"] == [7, 8] and app.cfg.pad["START"] == [1] and app.cfg.pad["SELECT"] == [2]
    for _ in range(100):
        frame(app)
    assert done


def test_rebind_rejects_duplicate_buttons(app):
    r = Rebind(app)
    r.press(3)
    r.press(3)  # same button for ATTACK: refused
    assert r.step == 1 and "already" in r.message
    r.press(9)
    assert r.step == 2


def test_rebind_timeout_saves_nothing(app):
    before = {k: list(v) for k, v in app.cfg.pad.items()}
    done = []
    r = Rebind(app, on_done=lambda: done.append(1))
    app.set_scene(r)
    r.press(4)
    for _ in range(40 * 60 + 5):
        frame(app)
        if done:
            break
    assert done and app.cfg.pad == before


def test_new_mapping_is_used_by_input_manager(app):
    app.cfg.pad["JUMP"] = [7]
    assert app.input.cfg.pad["JUMP"] == [7]


def test_controller_test_hold_select_opens_rebind(app):
    app.push_scene(ControllerTest(app))
    for _ in range(130):
        frame(app, {"SELECT"})
    assert isinstance(app.scene, Rebind)
    app.scene.on_done()
    assert isinstance(app.scene, ControllerTest)


def test_steps_cover_every_button_action():
    assert {a for a, _ in STEPS} == {"JUMP", "ATTACK", "SPECIAL", "SHIELD", "START", "SELECT"}


def test_colorblind_flag():
    assert apply_args(Config(), parse_args(["--colorblind"])).colorblind
