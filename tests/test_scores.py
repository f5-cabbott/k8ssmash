import json

import pytest

from k8ssmash.scores import (BLOCKED, DEFAULT_NAME, MAX_ENTRIES, MIN_VALUE, RunTracker, ScoreBoard, clean_name)


@pytest.fixture
def sb(tmp_path):
    return ScoreBoard(tmp_path / "scores.json")


def test_clean_name():
    assert clean_name("abc") == "ABC"
    assert clean_name("a-b!cd") == "ABC"
    assert clean_name("x") == "XAA"
    assert clean_name("   ") == DEFAULT_NAME
    assert all(clean_name(w) == DEFAULT_NAME for w in BLOCKED)


def test_minimum_values_keep_junk_off_the_board(sb):
    assert sb.rank_for("streak", MIN_VALUE["streak"] - 1) is None
    assert sb.rank_for("streak", MIN_VALUE["streak"]) == 1
    assert sb.upsert("kos", "r1", "AAA", MIN_VALUE["kos"] - 1, "Pod") is None
    assert sb.top("kos") == []


def test_ranking_and_ties(sb):
    sb.upsert("streak", "a", "AAA", 5, "Pod")
    sb.upsert("streak", "b", "BBB", 3, "Pod")
    assert sb.rank_for("streak", 4) == 2
    assert sb.rank_for("streak", 5) == 2  # tie ranks below the incumbent
    sb.upsert("streak", "c", "CCC", 5, "Pod")
    assert [e.name for e in sb.top("streak")] == ["AAA", "CCC", "BBB"]


def test_board_is_capped_and_low_scores_rejected(sb):
    for i in range(MAX_ENTRIES):
        sb.upsert("streak", f"r{i}", "AAA", 10 + i, "Pod")
    assert len(sb.top("streak")) == MAX_ENTRIES
    assert sb.rank_for("streak", 5) is None
    assert sb.upsert("streak", "new", "ZZZ", 100, "Pod") == 1
    assert len(sb.top("streak")) == MAX_ENTRIES and min(e.value for e in sb.top("streak")) == 11


def test_upsert_updates_same_run_without_duplicating(sb):
    sb.upsert("streak", "r", "AAA", 2, "Pod")
    sb.upsert("streak", "r", "AAA", 4, "Pod")
    assert len(sb.top("streak")) == 1 and sb.top("streak")[0].value == 4


def test_persistence_roundtrip_and_atomic_write(sb, tmp_path):
    sb.upsert("kos", "r", "K8S", 7, "Helm")
    again = ScoreBoard(tmp_path / "scores.json")
    assert again.top("kos")[0].name == "K8S" and again.top("kos")[0].fighter == "Helm"
    assert not (tmp_path / "scores.tmp").exists()


@pytest.mark.parametrize("content", ["", "not json", "[]", '{"streak": [{"bogus": 1}]}'])
def test_corrupt_file_is_tolerated(tmp_path, content):
    path = tmp_path / "scores.json"
    path.write_text(content)
    sb = ScoreBoard(path)
    assert sb.top("streak") == []
    sb.upsert("streak", "r", "AAA", 3, "Pod")
    assert json.loads(path.read_text())["streak"][0]["value"] == 3


def test_unwritable_location_does_not_crash(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    sb = ScoreBoard(blocker / "scores.json")  # parent is a file: every write fails
    assert sb.upsert("streak", "r", "AAA", 3, "Pod") == 1  # still works in memory


def test_run_tracker_streak_and_prompts(sb):
    rt = RunTracker(sb)
    human = [True, True]
    assert rt.record(0, human, [1, 0], ["Pod", "Helm"]) == []  # first win: streak 1, kos 1: no entry yet
    prompts = rt.record(0, human, [1, 1], ["Pod", "Helm"])  # streak 2, kos 2 -> streak board only
    assert len(prompts) == 1 and prompts[0].slot == 0 and prompts[0].boards == ["streak"]
    ranks = rt.commit_name(0, "abc")
    assert ranks["streak"] == 1 and sb.top("streak")[0].name == "ABC" and ranks["kos"] is None
    # a named run updates its entry silently, with no further prompt
    assert rt.record(0, human, [2, 0], ["Pod", "Helm"]) == []
    assert sb.top("streak")[0].value == 3 and sb.top("kos")[0].value == 4
    assert len(sb.top("streak")) == 1


def test_loss_ends_run_and_next_run_gets_new_entry(sb):
    rt = RunTracker(sb)
    human = [True, True]
    rt.record(0, human, [1, 0], ["Pod", "Helm"])
    rt.record(0, human, [1, 0], ["Pod", "Helm"])
    rt.commit_name(0, "AAA")
    first = rt.runs[0].id
    rt.record(1, human, [0, 2], ["Pod", "Helm"])  # slot 0 loses
    assert rt.runs[0].streak == 0 and rt.runs[0].id != first and rt.runs[0].name is None
    assert rt.runs[1].streak == 1
    assert len(sb.top("streak")) == 1  # the finished run's entry stays


def test_draw_and_cpu_slots_never_start_runs(sb):
    rt = RunTracker(sb)
    assert rt.record(-1, [True, True], [0, 0], ["A", "B"]) == []
    assert rt.record(1, [True, False], [0, 3], ["A", "B"]) == []  # CPU won
    assert all(r.streak == 0 for r in rt.runs)
