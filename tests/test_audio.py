import pygame
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
    for n in set(MUSIC_FOR_THEME.values()) | {"splash", "results"}:
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


# --- the SNES-style soundtrack and per-fighter effects ----------------------------------------
import json

import numpy as np

from k8ssmash.audio.sfx import EVENTS, VOICES
from k8ssmash.audio_manager import DUCK, slug

MUSIC = ["splash", "select", "datacenter", "controlplane", "nodepool", "etcd", "mesh", "cloud", "training", "leaderboard"]


def _pcm(path):
    pygame.mixer.init() if not pygame.mixer.get_init() else None
    raw = pygame.mixer.Sound(str(path)).get_raw()
    arr = np.frombuffer(raw, np.int16).astype(float) / 32768
    return arr.reshape(-1, 2) if pygame.mixer.get_init()[2] == 2 else arr.reshape(-1, 1)


@pytest.mark.parametrize("name", MUSIC)
def test_music_is_long_quiet_and_unclipped(name):
    a = _pcm(ASSETS / f"{name}.ogg")
    secs = len(a) / pygame.mixer.get_init()[0]
    assert 60 <= secs <= 130, f"{name} is {secs:.0f}s"  # long enough to evolve, like the reference tracks
    rms = float(np.sqrt((a.mean(axis=1) ** 2).mean()))
    assert 0.07 <= rms <= 0.13 and np.abs(a).max() < 0.95


@pytest.mark.parametrize("name", MUSIC)
def test_music_loops_without_a_click(name):
    a = _pcm(ASSETS / f"{name}.ogg").mean(axis=1)
    sr = pygame.mixer.get_init()[0]
    jump = abs(a[0] - a[-1])
    typical = np.abs(np.diff(a)).mean() * 40
    assert jump < max(0.05, typical)


def test_every_fighter_has_a_full_distinct_sound_set():
    centroids = {}
    for fighter in VOICES:
        for event in EVENTS:
            f = ASSETS / f"{slug(fighter)}__{event}.wav"
            assert f.stat().st_size > 1500, f
        a = _pcm(ASSETS / f"{slug(fighter)}__jump.wav").mean(axis=1)[:8192]
        spec = np.abs(np.fft.rfft(a * np.hanning(len(a))))
        freqs = np.fft.rfftfreq(len(a), 1 / pygame.mixer.get_init()[0])
        centroids[fighter] = float((spec * freqs).sum() / spec.sum())
    assert len(set(round(c / 150) for c in centroids.values())) >= 6  # clearly different timbres


def test_effects_are_louder_than_music():
    def rms(path, seconds=None):
        a = _pcm(path).mean(axis=1)
        if seconds:  # the body of a sound, ignoring its long quiet tail
            a = a[: int(seconds * pygame.mixer.get_init()[0])]
        return float(np.sqrt((a ** 2).mean()))
    music = np.mean([rms(ASSETS / f"{n}.ogg") for n in MUSIC]) * Config().music_volume
    for fighter in VOICES:
        sfx = rms(ASSETS / f"{slug(fighter)}__hit_heavy.wav", 0.15) * Config().sfx_volume
        assert sfx > music * 2.0, (fighter, sfx, music)  # at least 6 dB over the music


def test_default_mix_and_old_saved_volumes_are_migrated(tmp_path, monkeypatch):
    cfg = Config()
    assert cfg.music_volume <= 0.45 and 0.4 <= cfg.sfx_volume <= 0.7 and 0.5 <= cfg.master_volume <= 1.0
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"mix_version": 2, "sfx_volume": 0.9, "music_volume": 0.5, "width": 2560, "height": 1440}))
    monkeypatch.setenv("K8SSMASH_CONFIG", str(old))
    loaded = Config.load()
    assert (loaded.music_volume, loaded.sfx_volume) == (cfg.music_volume, cfg.sfx_volume)  # old mix ignored
    assert loaded.width == 2560  # everything else is kept
    new = tmp_path / "new.json"
    new.write_text(json.dumps({"mix_version": 3, "music_volume": 0.2}))
    monkeypatch.setenv("K8SSMASH_CONFIG", str(new))
    assert Config.load().music_volume == 0.2  # a volume chosen under the new mix is respected


def test_dev_keys_are_never_persisted(tmp_path, monkeypatch):
    path = tmp_path / "c.json"
    monkeypatch.setenv("K8SSMASH_CONFIG", str(path))
    cfg = Config()
    cfg.dev_keys = False
    cfg.save()
    assert "dev_keys" not in json.loads(path.read_text())
    assert Config.load().dev_keys is True


def test_fighter_sounds_resolve_and_fall_back():
    a = Audio()
    a.play("jump", fighter="Pod")
    assert a.last_file == "pod__jump"
    a.play("jump", fighter="Nobody")
    assert a.last_file == "jump"
    a.play("pickup", fighter="Pod")
    assert a.last_file == "pickup"  # no per-fighter pickup: the generic one plays
    a.play("jump")
    assert a.last_file == "jump"


def test_loud_events_duck_the_music_then_it_recovers():
    a = Audio()
    assert a._duck == 1.0
    a.play("ko")
    assert a._duck == DUCK["ko"]
    for _ in range(120):
        a.update()
    assert a._duck > 0.97


def test_music_names_for_each_screen(app):
    from k8ssmash.scenes.scoreboard import HighScores
    from k8ssmash.scenes.select import CharacterSelect
    from k8ssmash.scenes.training import Training
    from k8ssmash.scenes.title import Title
    CharacterSelect(app)
    assert app.audio.current == "select"
    HighScores(app, on_done=lambda: None)
    assert app.audio.current == "leaderboard"
    Training(app, roster()[:2])
    assert app.audio.current == "training"
    Title(app)
    assert app.audio.current == "splash"


def test_battle_hits_use_the_attackers_sound_and_pan(app):
    b = Battle(app, roster()[:2], human=[False, False])
    app.set_scene(b)
    b.frame = READY_FRAMES + 1
    a, v = b.fighters
    v.x, v.y, a.x = 880, a.y, 860
    b._hit(v, a, 9, 4, 0.05, 40, 1)
    assert app.audio.last_file == "pod__hit_heavy"
    assert b.pan_of(v) > 0.3 and b.pan_of(b.fighters[0]) > 0
    v.x = 80
    assert b.pan_of(v) < -0.3


# --- fighting-game attack sounds -------------------------------------------------------------------
def test_normals_and_specials_have_their_own_swing_and_shout(app):
    from k8ssmash.fighter import Fighter
    from k8ssmash.input import PlayerInput
    from k8ssmash.stage import datacenter_stage
    st = datacenter_stage()
    f = Fighter(roster()[0], 0)
    f.spawn(st.spawns[0], 1)
    inp = PlayerInput()
    inp.update(set()); f.update(inp, st)
    inp.update({"ATTACK"}); f.update(inp, st)
    assert f.events[-1] == "attack_light"  # a jab is a light grunt
    f.events.clear(); f.move = None; f.state = "idle"
    inp.update(set()); f.update(inp, st)
    f.events.clear(); f.move = None; f.state = "idle"
    inp.update({"ATTACK", "RIGHT"}); f.update(inp, st)
    assert f.events[-1] == "attack_heavy"  # a side attack is heavier
    f.events.clear(); f.move = None; f.state = "idle"
    inp.update(set()); f.update(inp, st)
    inp.update({"SPECIAL"}); f.update(inp, st)
    assert f.events[-1] == "special"


def test_every_fighter_has_voiced_attacks_and_punchy_hits():
    for fighter in VOICES:
        for event in ("attack_light", "attack_heavy", "special", "hit_light", "hit_heavy", "ko"):
            assert (ASSETS / f"{slug(fighter)}__{event}.wav").stat().st_size > 2500, (fighter, event)
    for event in ("attack_light", "attack_heavy", "special", "hit_light", "hit_heavy"):
        assert (ASSETS / f"{event}.wav").exists()  # the generic fallbacks


def _low_share(a, sr):
    """Share of the shout's energy below 250 Hz: high for gravelly voices, near zero for squeaky ones."""
    seg = a[:12000]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)
    return float(spec[(freqs > 50) & (freqs < 250)].sum() / spec[(freqs > 50) & (freqs < 4000)].sum())


def test_fighter_voices_are_distinct():
    """Each fighter shouts in their own voice: a gravelly reaper and a deep keeper, mid robots, a squeaky clockwork imp."""
    sr = pygame.mixer.get_init()[0] if pygame.mixer.get_init() else 44100
    low = {f: _low_share(_pcm(ASSETS / f"{slug(f)}__attack_heavy.wav").mean(axis=1), sr) for f in VOICES}
    assert low["OOMKiller"] > 0.5 and low["StatefulSet"] > 0.5  # deep voices
    assert low["CronJob"] < 0.1 and low["Pod"] < 0.1 and low["Operator"] < 0.1  # high voices
    assert low["OOMKiller"] > low["Kubectl"]  # and the reaper is the deepest


def test_impacts_are_meatier_than_the_old_blips():
    """A heavy hit should carry real low-end weight, unlike a chiptune beep."""
    a = _pcm(ASSETS / "hit_heavy.wav").mean(axis=1)
    sr = pygame.mixer.get_init()[0]
    spec = np.abs(np.fft.rfft(a[: sr // 2]))
    freqs = np.fft.rfftfreq(len(a[: sr // 2]), 1 / sr)
    assert spec[freqs < 200].sum() / spec.sum() > 0.25
