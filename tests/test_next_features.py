"""CronJob, stage set pieces, reactive scenery, leitmotifs, the title/select polish and the lifelike instruments."""
import numpy as np
import pygame
import pytest

from k8ssmash import backdrops, ui
from k8ssmash.audio import arranger, instruments as I, sfx
from k8ssmash.config import PIX_H, PIX_W, RS, Config
from k8ssmash.fighter import Fighter
from k8ssmash.main import App
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import Battle
from k8ssmash.stage import STAGES, WARN, Platform, datacenter_stage, node_pool_stage


@pytest.fixture
def app():
    a = App(Config())
    a.input.poll = lambda: None
    yield a
    pygame.quit()


def test_cronjob_replaces_chaos_monkey_with_clock_moves():
    names = [r.name for r in roster()]
    assert "CronJob" in names and "Chaos Monkey" not in names
    moves = next(r for r in roster() if r.name == "CronJob").moves
    assert moves["special"].projectile.shape == "clock"
    assert moves["special_side"].blink and moves["special_up"].rise and moves["special_down"].projectile.explode_radius


def test_set_piece_platform_ghosts_then_solid_then_fades_and_goes():
    plat = Platform(pygame.Rect(0, 0, 100, 8), dropthrough=True, schedule=(1000, 400, 0))
    plat.tick(10)
    assert not plat.solid and 0 < plat.glow < 0.7  # a ghost: coming, not yet standable
    plat.tick(WARN + 50)
    assert plat.solid and plat.glow == 1.0
    plat.tick(WARN + 400 - 40)
    assert plat.solid and 0.5 <= plat.glow < 1.0  # dimming before it leaves
    plat.tick(WARN + 400 + 5)
    assert not plat.solid and plat.glow == 0.0


def test_every_stage_has_a_set_piece_and_live_excludes_absent_platforms():
    for make in STAGES:
        st = make()
        assert any(p.schedule for p in st.platforms), st.name
        st.tick(0)
        assert all(p.solid for p in st.live) and len(st.live) <= len(st.platforms)


def test_a_fighter_standing_on_a_retracting_bridge_falls():
    from k8ssmash.input import PlayerInput
    st = node_pool_stage()
    bridge = next(p for p in st.platforms if p.schedule)
    inp = PlayerInput()
    f = Fighter(roster()[0], 0)
    f.spawn((480, 400), 1)
    frame = 1200  # bridge solid
    st.tick(frame)
    assert bridge.solid
    for _ in range(20):
        inp.update(set())
        f.update(inp, st)
    assert f.on_ground and f.standing_on is bridge
    frame = 2100 - 1100 + WARN + 720 + 2  # just past its window
    st.tick(frame)
    assert not bridge.solid
    for _ in range(30):
        inp.update(set())
        f.update(inp, st)
    assert f.y > 400 and not f.on_ground


def test_heavy_hits_send_a_floor_ripple_that_expires(app):
    b = Battle(app, roster()[:2], human=[False, False])
    a, v = b.fighters
    v.x, v.y = a.x + 10, a.y
    b._hit(v, a, 12, 4, 0.05, 40, 1)
    assert backdrops.REACT["ripples"]
    for _ in range(backdrops.RIPPLE_LIFE + 2):
        backdrops.tick_ripples()
    assert backdrops.REACT["ripples"] == []
    b.draw(app.display.canvas)


def test_a_three_hit_combo_plays_the_fighters_leitmotif_once_per_ten_seconds(app):
    b = Battle(app, roster()[:2], human=[False, False])
    a, v = b.fighters
    for _ in range(3):
        b._count_combo(a, v, chained=True)
    assert app.audio.played.count("motif0") == 1
    for _ in range(3):
        b._count_combo(a, v, chained=True)
    assert app.audio.played.count("motif0") == 1  # cooling down
    b.frame += 11 * 60
    b.hot = True
    b._count_combo(a, v, chained=True)
    assert app.audio.played[-1] in ("motif2", "counter")
    assert "motif2" in app.audio.played


def test_leitmotif_files_exist_in_every_key_for_every_fighter():
    from k8ssmash.audio_manager import ASSETS, slug
    for st in roster():
        for shift in sfx.MOTIF_SHIFTS:
            assert (ASSETS / f"{slug(st.name)}__motif{shift}.wav").stat().st_size > 1500


def test_fit_shrinks_text_until_it_fits_and_never_below_the_minimum(app):
    wide = "A very long blurb that would never fit in a small window at the normal size"
    surf = ui.fit(wide, (255, 255, 255), 120, 15, 8)
    assert surf.get_width() <= 120 or surf.get_height() <= round(9 * ui.SCALE) + 4
    short = ui.fit("Pod", (255, 255, 255), 120, 15, 8)
    assert short.get_height() >= surf.get_height()


def test_title_and_select_draw_with_the_new_art(app):
    from k8ssmash.scenes.select import CharacterSelect, portrait
    from k8ssmash.scenes.title import MENU, Title
    t = Title(app)
    for i in range(len(MENU)):
        t.row = i
        for _ in range(130):
            t.update()
        t.draw(pygame.Surface((960, 540)))
    sel = CharacterSelect(app)
    sel.joined = [True, True]
    sel.draw(pygame.Surface((960, 540)))
    st = roster()[0]
    assert portrait(st.name, st.color, 213, 126, 93) is portrait(st.name, st.color, 213, 126, 93)  # built once


@pytest.mark.parametrize("name", ["piano", "pizz", "nylon", "bass_pluck", "strings", "horn", "clarinet", "oboe"])
def test_lifelike_instruments_are_in_tune_and_finite(name):
    for midi in (48, 60, 72):
        x = I.INSTRUMENTS[name](midi, 0.6)
        assert np.isfinite(x).all() and np.abs(x).max() > 0.01
        seg = x[int(0.03 * 44100):int(0.35 * 44100)]
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
        lo = int(44100 / 1200)
        f0 = 44100 / (lo + int(np.argmax(ac[lo:int(44100 / 50)])))
        assert abs(1200 * np.log2(f0 / (440 * 2 ** ((midi - 69) / 12)))) < 40, (name, midi, f0)


def test_voice_leading_keeps_chords_close_and_in_range():
    prev = None
    prog = [(0, "maj"), (5, "maj"), (7, "7"), (9, "min")] * 2
    moves = []
    for chord in prog:
        notes = arranger.voice_lead(48, chord, prev, 52, 76)
        assert len(set(notes)) == 4 and all(52 <= n <= 76 for n in notes)
        if prev:
            moves.append(sum(abs(a - b) for a, b in zip(notes, prev)))
        prev = notes
    assert max(moves) <= 12


def test_generated_melodies_stay_in_a_playable_range():
    """Phrase-built melodies (hook, answer, reach, cadence) stay inside a singable range and inside the section."""
    from k8ssmash.audio import theory as T
    import random
    scale = T.SCALES["major"]
    bars = [("4/4", (0, "maj"))] * 8
    notes = T.melody(random.Random(5), 57, scale, bars, 72, busy=0.5)
    assert len(notes) >= 12 and all(-6 <= (n.midi - 57) <= 40 for n in notes)
    assert max(n.step for n in notes) < 8 * 16


def test_arena_music_fades_out_when_a_match_ends_and_victory_theme_is_a_real_fanfare(app):
    b = Battle(app, roster()[:2], human=[False, False])
    app.set_scene(b)
    assert app.audio.current is not None
    b.fighters[1].stocks = 0
    b.fighters[1].eliminated = True
    b._check_end()
    b._report_result()
    assert app.audio.current is None  # the arena song is gone before the results screen
    from k8ssmash.audio.songs import SONGS
    song = SONGS["results"]()
    assert not song.loop and song.emu > 0 and song.sections[0].line and len(song.sections[0].prog) >= 12
    from k8ssmash.audio_manager import ASSETS
    assert (ASSETS / "results.ogg").stat().st_size > 100_000  # ~20+ seconds, not the old 11 s sting


def test_select_panel_rows_and_legend_stay_inside_their_windows(app):
    from k8ssmash.scenes.select import CharacterSelect
    sel = CharacterSelect(app)
    sel.joined = [True, True]
    for st_idx in range(len(sel.roster)):
        sel.cursor = [st_idx, st_idx]
        surf = pygame.Surface((PIX_W, PIX_H))
        sel.draw(surf)
        panel_bottom = round((174 + 112) * ui.SCALE)
        legend_top = round(290 * ui.SCALE)
        # the strip between the player panels and the legend holds nothing but background
        strip = [surf.get_at((x, y))[:3] for x in range(30, 930, 40) for y in range(panel_bottom + 6, legend_top - 1)]
        assert all(c == (16, 20, 38) for c in strip)


# --- pause, announcer, stage select, rematch, training tools, colours, tutorial, intensity layer ----------------
def _frame(app, p0=(), p1=()):
    app.input.players[0].update(set(p0))
    app.input.players[1].update(set(p1))
    app.step()


def _tap(app, p0=(), p1=()):
    _frame(app, p0, p1)
    _frame(app)


def _fight(app, human=(True, True)):
    b = Battle(app, roster()[:2], human=list(human))
    app.set_scene(b)
    for _ in range(100):
        _frame(app)
    return b


def test_start_pauses_the_match_and_the_menu_resumes_restarts_or_quits(app):
    from k8ssmash.scenes.title import Title
    b = _fight(app)
    frame_before = b.frame
    _tap(app, {"START"})
    assert b.paused
    for _ in range(30):
        _frame(app)
    assert b.frame == frame_before  # nothing advances while paused
    b.draw(app.display.canvas)
    _tap(app, {"ATTACK"})  # B resumes
    assert not b.paused
    _tap(app, {"START"})
    _tap(app, {"DOWN"})
    _tap(app, {"SPECIAL"})  # Restart match
    assert isinstance(app.scene, Battle) and app.scene is not b
    _tap(app, {"START"})
    _tap(app, {"UP"})  # wraps to Quit to title
    _tap(app, {"SPECIAL"})
    assert isinstance(app.scene, Title)


def test_announcer_clips_exist_and_the_battle_calls_ready_and_fight(app):
    from k8ssmash.audio.announcer import LINES, NAME_SPEECH
    from k8ssmash.audio_manager import ASSETS
    for key in list(LINES) + [f"ann_win_{n.lower()}" for n in NAME_SPEECH]:
        assert (ASSETS / f"{key}.wav").stat().st_size > 5000, key
    b = Battle(app, roster()[:2], human=[True, True])
    app.set_scene(b)
    for _ in range(100):
        _frame(app)
    assert "ann_ready" in app.audio.played or app.audio.played.count("go") >= 1
    assert "ann_fight" in app.audio.played


def test_kill_cam_zooms_toward_the_ko_point_without_changing_the_canvas_size(app):
    b = Battle(app, roster()[:2], human=[False, False])
    canvas = pygame.Surface((PIX_W, PIX_H))
    canvas.fill((10, 10, 10))
    pygame.draw.rect(canvas, (255, 0, 0), (PIX_W - 100, PIX_H // 2, 40, 40))
    b.kill_focus = (PIX_W / RS - 50, PIX_H / RS / 2)
    b._punch_in(canvas, 1.0)
    assert canvas.get_size() == (PIX_W, PIX_H)
    red = sum(1 for x in range(0, PIX_W, 8) for y in range(0, PIX_H, 8) if canvas.get_at((x, y))[:3] == (255, 0, 0))
    assert red > 0  # the marker grew toward the camera


def test_stage_select_previews_choose_and_go_back(app):
    from k8ssmash.scenes.select import CharacterSelect
    from k8ssmash.scenes.stageselect import StageSelect
    rs = roster()
    sc = StageSelect(app, [rs[0], rs[1]], [True, True], [0, 1], 0)
    app.set_scene(sc)
    for _ in range(10):
        _frame(app)
    _tap(app, {"RIGHT"})
    assert sc.row == 1
    sc.draw(app.display.canvas)
    _tap(app, {"SPECIAL"})
    assert isinstance(app.scene, Battle) and app.scene.stage.name == STAGES[1]().name and app.last_match[2] == 1
    sc2 = StageSelect(app, [rs[0], rs[1]], [True, True], [0, 1], 0)
    app.set_scene(sc2)
    for _ in range(10):
        _frame(app)
    _tap(app, {"ATTACK"})
    assert isinstance(app.scene, CharacterSelect)


def test_results_rematch_options_change_stage_and_swap_sides(app):
    from k8ssmash.scenes.results import Results
    summary = [{"name": "Pod", "kos": 2, "damage": 120, "stocks": 1, "combo": 4},
               {"name": "Kubectl", "kos": 1, "damage": 80, "stocks": 0, "combo": 2}]
    app.last_match = ([0, 2], [True, True], 0)
    res = Results(app, 0, summary, [True, True])
    app.set_scene(res)
    assert "ann_win_pod" not in app.audio.played
    for _ in range(80):
        _frame(app)
    assert "ann_win_pod" in app.audio.played  # the announcer names the winner once the fanfare settles
    _tap(app, {"SHIELD"})
    assert app.last_match[2] == 1
    _tap(app, {"JUMP"})
    assert app.last_match[0] == [2, 0] and res.winner == 1 and res.summary[0]["name"] == "Kubectl"
    res.draw(app.display.canvas)


def test_training_records_the_players_moves_and_replays_them_mirrored(app):
    from k8ssmash.scenes.training import DUMMY_MODES, Training
    t = Training(app, roster()[:2])
    app.set_scene(t)
    while DUMMY_MODES[t.mode] != "Record":
        app.input.players[0].update({"SELECT"})
        app.step()
        app.input.players[0].update(set())
        app.step()
    for _ in range(40):
        _frame(app, {"RIGHT"})
    assert len(t.recording) >= 40
    while DUMMY_MODES[t.mode] != "Replay":
        app.input.players[0].update({"SELECT"})
        app.step()
        app.input.players[0].update(set())
        app.step()
    x0 = t.fighters[1].x
    for _ in range(30):
        _frame(app)
    assert t.fighters[1].x < x0  # the recorded RIGHT is replayed as LEFT, toward the player
    t.last_move = t.fighters[0].stats.moves["jab"]
    t.draw(app.display.canvas)


def test_colour_variants_cycle_on_select_and_mirror_matches_stay_distinct(app):
    from k8ssmash.scenes.select import CharacterSelect
    from k8ssmash.sprites import VARIANT_NAMES, VARIANT_TAGS, resolve_variants, sprite_set
    assert resolve_variants(["Pod", "Pod"], [0, 0]) == [0, 1]
    assert resolve_variants(["Pod", "Pod"], [1, 1]) == [1, 2]
    assert resolve_variants(["Pod", "Kubectl"], [2, 2]) == [2, 2]
    sel = CharacterSelect(app)
    app.set_scene(sel)
    _tap(app, {"START"})
    _tap(app, {"JUMP"})
    assert sel.variant[0] == 1
    for _ in range(3):
        _tap(app, {"JUMP"})
    assert sel.variant[0] == (1 + 3) % len(VARIANT_NAMES)
    sel.draw(app.display.canvas)
    for st in roster():
        for v in range(len(VARIANT_TAGS)):
            assert sprite_set(st.name, v) is not None


def test_tutorial_runs_every_lesson_and_the_scripted_fighter_acts(app):
    from k8ssmash.scenes.title import Title
    from k8ssmash.scenes.tutorial import LESSONS, Tutorial
    sc = Tutorial(app, 0)
    app.set_scene(sc)
    for i in range(len(LESSONS)):
        sc.lesson = i
        sc._start_lesson()
        x0 = sc.battle.fighters[0].x
        for _ in range(240):
            _frame(app)
        sc.draw(app.display.canvas)
        assert sc.battle.fighters[0].x != x0 or sc.battle.fighters[0].y != sc.battle.stage.spawns[0][1] or i in (3, 4)
    _tap(app, {"ATTACK"})
    assert isinstance(app.scene, Title)


def test_music_intensity_layer_starts_with_the_song_and_follows_the_damage(app):
    from k8ssmash.audio_manager import ASSETS
    for song in ("datacenter", "controlplane", "nodepool"):
        assert (ASSETS / f"{song}_stem.ogg").stat().st_size > 50_000
        assert (ASSETS / f"{song}_hot_stem.ogg").stat().st_size > 50_000
    b = Battle(app, roster()[:2], human=[True, True])
    app.set_scene(b)
    assert app.audio.stem_name and app.audio.stem_name.endswith("_stem")
    for f in b.fighters:
        f.percent = 200.0
    for _ in range(400):
        _frame(app)
    assert app.audio._stem_level > 0.5
    app.audio.music("select")
    assert app.audio.stem_name is None  # moving to another screen drops the layer
