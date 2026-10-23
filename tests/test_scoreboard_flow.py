import pygame
import pytest

from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.scenes.attract import Attract
from k8ssmash.scenes.results import LOCK, Results
from k8ssmash.scenes.scoreboard import ENTRY_TIMEOUT, HighScores, NameEntry
from k8ssmash.scenes.title import Title
from k8ssmash.scores import Prompt


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


def summary(kos=(1, 0)):
    return [{"name": "Pod", "kos": kos[0], "damage": 10, "stocks": 1},
            {"name": "Helm", "kos": kos[1], "damage": 5, "stocks": 0}]


def test_tap_select_on_title_opens_leaderboard(app):
    frame(app, {"SELECT"})
    frame(app)
    assert isinstance(app.scene, HighScores)


def test_select_start_combo_does_not_open_leaderboard(app):
    for _ in range(100):
        frame(app, {"SELECT", "START"})
    for _ in range(3):
        frame(app)
    assert not isinstance(app.scene, HighScores)


def test_leaderboard_returns_to_title_on_button_and_timeout(app):
    app.set_scene(HighScores(app, on_done=app.go_title))
    for _ in range(25):
        frame(app)
    tap(app, {"START"})
    assert isinstance(app.scene, Title)
    app.set_scene(HighScores(app, on_done=app.go_title, seconds=1))
    for _ in range(70):
        frame(app)
    assert isinstance(app.scene, Title)


def test_attract_ends_on_leaderboard_then_title(app):
    att = Attract(app)
    app.set_scene(att)
    att.battle.winner, att.battle.finished_frames = 0, 200
    app.idle_frames = 999
    att.update()
    assert isinstance(app.scene, HighScores)


def test_results_to_name_entry_to_leaderboard_and_back(app):
    app.last_match = ([0, 1], [True, True], 0)
    app.runs.record(0, [True, True], [1, 0], ["Pod", "Helm"])  # already one win in the run
    res = Results(app, 0, summary((2, 0)), [True, True])
    app.set_scene(res)
    assert res.prompts and res.prompts[0].slot == 0
    for _ in range(LOCK + 5):
        frame(app)
    tap(app, {"START"})
    assert isinstance(app.scene, NameEntry)
    # type "ZAP": UP moves the first letter from K to ... just confirm three times
    tap(app, {"ATTACK"})
    tap(app, {"ATTACK"})
    tap(app, {"ATTACK"})
    assert isinstance(app.scene, HighScores)
    assert app.scores.top("streak")[0].name == "K8S" and app.scores.top("streak")[0].value == 2
    for _ in range(25):
        frame(app)
    tap(app, {"START"})
    assert app.scene is res and not res.prompts


def test_name_entry_edits_letters(app):
    got = []
    ne = NameEntry(app, Prompt(0, ["streak"], "Pod"), got.append)
    app.set_scene(ne)
    app.runs.runs[0].streak = 2
    tap(app, {"UP"})  # K -> L
    tap(app, {"RIGHT"})
    tap(app, {"DOWN"})  # 8 -> 7
    tap(app, {"LEFT"})
    tap(app, {"RIGHT"})
    tap(app, {"RIGHT"})
    tap(app, {"ATTACK"})
    assert got == ["L7S"]


def test_name_entry_times_out_with_current_name(app):
    got = []
    app.set_scene(NameEntry(app, Prompt(0, ["streak"], "Pod"), got.append))
    for _ in range(ENTRY_TIMEOUT + 5):
        frame(app)
        if got:
            break
    assert got == ["K8S"]


def test_screens_render(app):
    app.runs.runs[0].streak = 2
    app.scores.upsert("streak", "x", "ABC", 4, "Pod")
    for scene in (HighScores(app, on_done=lambda: None, highlight={"x"}),
                  NameEntry(app, Prompt(0, ["streak"], "Pod"), lambda n: None),
                  Results(app, 0, summary(), [True, True])):
        scene.draw(app.display.canvas)
