"""CronJob, stage set pieces, reactive scenery, leitmotifs, the title/select polish and the lifelike instruments."""
import numpy as np
import pygame
import pytest

from k8ssmash import backdrops, ui
from k8ssmash.audio import arranger, instruments as I, sfx
from k8ssmash.config import PIX_H, PIX_W, RS, Config
from k8ssmash.input import PlayerInput
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


# --- unique moves ------------------------------------------------------------------------------------------
def test_every_fighters_four_normals_are_their_own():
    from k8ssmash.moves import default_moveset
    base = default_moveset()
    seen = {}
    for st in roster():
        for key in ("jab", "side", "up", "down"):
            m = st.moves[key]
            assert m != base[key], (st.name, key)  # nobody is left with the generic default
            sig = (m.startup, m.active, m.recovery, m.hitbox, m.damage, m.angle, m.rehit, m.projectile is not None)
            assert sig not in seen, (st.name, key, seen.get(sig))
            seen[sig] = (st.name, key)
    jabs = {st.moves["jab"].name for st in roster()}
    assert len(jabs) == 8  # eight different named jabs


def test_a_multi_hit_move_strikes_the_same_target_again_but_a_normal_one_does_not(app):
    b = Battle(app, roster()[:2], human=[False, False])
    a, v = b.fighters
    a.stats.moves["jab"]  # Pod's splash is a multi-hit move
    v.x, v.y = a.x + 14, a.y
    v.invuln = 0
    a._begin(a.stats.moves["jab"])
    hits = []
    for _ in range(14):
        a.move_frame += 1
        before = v.percent
        b._resolve_melee()
        if v.percent > before:
            hits.append(a.move_frame)
        v.hitstun = 0
        v.invuln = 0
    assert len(hits) >= 2 and a.stats.moves["jab"].rehit
    a2, v2 = Battle(app, roster()[1:3], human=[False, False]).fighters
    assert a2.stats.moves["jab"].rehit == 0


def test_projectile_normals_and_wavy_projectiles_exist(app):
    side = next(r for r in roster() if r.name == "Sidecar")
    assert side.moves["jab"].projectile is not None and side.moves["jab"].projectile.life <= 10
    waves = [r.name for r in roster() for m in r.moves.values() if m.projectile and m.projectile.wave]
    assert {"Pod", "Sidecar"} <= set(waves)
    b = Battle(app, roster()[:2], human=[False, False])
    from k8ssmash.fighter import Projectile
    d = roster()[0].moves["special"].projectile
    p = Projectile(b.fighters[0], d, 100.0, 100.0, d.speed, 0.0, 1, d.life)
    ys = []
    for _ in range(30):
        p.update(b.stage)
        ys.append(p.y)
    assert max(ys) - min(ys) > 5  # the bubble weaves
    from k8ssmash.fx import draw_projectile
    for shape in ("bubble", "spark"):
        from k8ssmash.moves import ProjectileDef
        q = Projectile(b.fighters[0], ProjectileDef(3, 18, 14, 1, 1, 0, 0, shape=shape, color=(200, 200, 255)), 100.0, 100.0, 3.0, 0.0, 1, 10)
        draw_projectile(pygame.Surface((PIX_W, PIX_H)), q)


def test_a_fighter_knocked_off_screen_gets_an_edge_indicator(app):
    b = Battle(app, roster()[:2], human=[False, False])
    canvas = pygame.Surface((PIX_W, PIX_H))
    canvas.fill((0, 0, 0))
    b._draw_offscreen(canvas)
    assert pygame.mask.from_threshold(canvas, (0, 0, 0), (1, 1, 1)).count() == PIX_W * PIX_H  # both on screen: nothing drawn
    b.fighters[0].x, b.fighters[0].y = -240.0, 300.0
    b._draw_offscreen(canvas)
    assert pygame.mask.from_threshold(canvas, (0, 0, 0), (1, 1, 1)).count() < PIX_W * PIX_H
    left = [canvas.get_at((x, 300 * RS - 40 + dy))[:3] for x in range(0, 140, 6) for dy in range(0, 80, 6)]
    assert any(c != (0, 0, 0) for c in left)  # the bubble sits on the left edge, level with the fighter
    b.fighters[0].y = 3000.0  # far below: the bubble stays above the damage panels
    canvas.fill((0, 0, 0))
    b._draw_offscreen(canvas)
    b.draw(app.display.canvas)


def test_cronjob_gravity_well_pulls_the_opponent_and_never_hurts_cronjob(app):
    rs = {r.name: r for r in roster()}
    b = Battle(app, [rs["CronJob"], rs["Pod"]], human=[False, False])
    app.set_scene(b)
    owner, foe = b.fighters
    d = owner.stats.moves["special_down"].projectile
    assert d.pull > 0 and d.harmless_to_owner
    from k8ssmash.fighter import Projectile
    well = Projectile(owner, d, owner.x + 40, owner.y - 36, 0.0, 0.0, 1, d.life)
    b.projectiles.append(well)
    foe.x, foe.y = owner.x + 40 + 60, owner.y
    foe.vx = foe.vy = 0.0
    x0 = foe.x
    owner_pct = owner.percent
    for _ in range(40):
        b._update_projectiles()
        foe.x += foe.vx
    assert foe.x < x0 - 8  # drawn in toward the well
    assert owner.percent == owner_pct
    well.life = 0  # collapse: the owner standing in it is untouched
    owner.x, owner.y = well.x, well.y + 30
    b._update_projectiles()
    assert owner.percent == owner_pct
    from k8ssmash.fx import draw_projectile
    draw_projectile(pygame.Surface((PIX_W, PIX_H)), Projectile(owner, d, 200.0, 200.0, 0.0, 0.0, 1, d.life))


# --- power-ups --------------------------------------------------------------------------------------------
def test_every_item_has_its_own_icon_and_the_auras_and_timers_draw(app):
    from k8ssmash.items import BUFF_ITEM, ITEMS, draw_icon
    canvas = pygame.Surface((PIX_W, PIX_H))
    shapes = set()
    for key in ITEMS:
        canvas.fill((0, 0, 0))
        draw_icon(canvas, key, 100, 100, 9.5)
        shapes.add(pygame.image.tobytes(canvas.subsurface((60 * RS, 60 * RS, 80 * RS, 80 * RS)), "RGB"))
    assert len(shapes) == len(ITEMS) >= 9  # nine different emblems
    b = Battle(app, roster()[:2], human=[False, False])
    f = b.fighters[0]
    for buff in BUFF_ITEM:
        f.add_buff(buff, 300)
    f.add_buff("scaled", 300)
    b.draw(app.display.canvas)  # every aura and a timer ring per power-up
    assert set(BUFF_ITEM.values()) <= set(ITEMS)


def test_canary_adds_a_bird_to_every_swing_and_rate_limit_slows_the_opponent(app):
    from k8ssmash.fighter import BUFF_CANARY, BUFF_THROTTLED
    from k8ssmash.items import ITEMS
    b = Battle(app, roster()[:2], human=[False, False])
    a, v = b.fighters
    a._begin(a.stats.moves["jab"])
    for _ in range(a.stats.moves["jab"].startup + 2):
        a._advance_move(PlayerInput())
    assert not a.spawn_queue  # no canary yet: a plain jab sends nothing
    a.move = None
    a.add_buff(BUFF_CANARY, 600)
    a._begin(a.stats.moves["side"])
    for _ in range(a.stats.moves["side"].startup + 2):
        a._advance_move(PlayerInput())
    assert any(p.defn.shape == "bird" for p in a.spawn_queue)
    base = v.speed_mult
    ITEMS["ratelimit"].apply(a, [v])
    assert v.has(BUFF_THROTTLED) and v.speed_mult < base * 0.7 and not a.has(BUFF_THROTTLED)
    v.move = None
    v.state = "attack"
    v._begin(v.stats.moves["jab"])
    v.anim_frame = 2
    before = v.move_frame
    v._advance_move(PlayerInput())
    assert v.move_frame == before  # a dropped frame: its swing runs slower


def test_chaos_bomb_is_lobbed_and_cannot_hurt_its_thrower(app):
    from k8ssmash.items import CHAOS_BOMB
    assert CHAOS_BOMB.harmless_to_owner and CHAOS_BOMB.speed > 0 and CHAOS_BOMB.vy < 0


def test_oomkiller_and_statefulset_are_quicker_and_have_odd_new_tricks():
    rs = {r.name: r for r in roster()}
    oom, ss = rs["OOMKiller"], rs["StatefulSet"]
    assert oom.run_speed > 3.5 and oom.air_jumps >= 3 and oom.moves["jab"].startup <= 3 and oom.moves["side"].startup <= 10
    assert oom.moves["special"].projectile.count == 2 and oom.moves["special"].projectile.wave  # two weaving skulls
    assert oom.moves["special_side"].blink and oom.moves["special_up"].rehit and oom.moves["special_down"].hitbox[2] >= 120
    assert ss.run_speed > 3.2 and ss.moves["special_side"].rehit and ss.moves["special_down"].buff  # barrel roll, armor snapshot


def test_cloud_native_arena_has_autoscaling_replicas_in_pairs_and_its_own_music():
    from k8ssmash.audio_manager import ASSETS, MUSIC_FOR_THEME
    from k8ssmash.stage import cloud_stage
    st = cloud_stage()
    assert st.theme == "cloud" and MUSIC_FOR_THEME["cloud"] == "cloud"
    sched = [p for p in st.platforms if p.schedule]
    assert len(sched) == 4 and len({p.schedule[2] for p in sched}) == 2  # two waves of two replica clouds
    st.tick(300)
    assert len(st.live) < len(st.platforms)
    for suffix in ("", "_hot", "_stem", "_hot_stem"):
        assert (ASSETS / f"cloud{suffix}.ogg").stat().st_size > 50_000


def test_oomkiller_scythe_is_steel_and_wood_and_swings_with_the_attack_pose():
    from k8ssmash.art.looks import LOOKS
    from k8ssmash.art.poses import pose_for
    from k8ssmash.art.rig import FEET, FRAME, render
    look = LOOKS["OOMKiller"]()
    assert look.pal["steel"][2] > look.pal["steel"][1] > 150 and look.pal["wood"][0] > look.pal["wood"][2]  # a pale steel blade, brown shaft
    assert all(name != "pcb" or fn.__name__ != "blade" for fn, name in look.front)  # the blade is not the old green board
    idle = render(look, pose_for("idle", 0))
    swing = render(look, pose_for("side", 3))
    assert pygame.image.tobytes(idle, "RGBA") != pygame.image.tobytes(swing, "RGBA")
    # the whole weapon stays inside its frame on a forward swing: nothing touches the right-hand edge
    right_edge = pygame.mask.from_surface(swing).get_bounding_rects()
    assert max(r.right for r in right_edge) < FRAME - 2 and FEET[0] < FRAME // 2


def test_every_arena_has_whimsy_props_and_cloud_has_no_wheel(app):
    import inspect
    from k8ssmash import backdrops
    for fn in ("_duck", "_cat", "_mug", "_sign", "_bonsai", "_trophy", "_pennant", "_sleepy_face", "_key", "_chest", "_bat", "_planet",
               "_satellite", "_comet", "_whale", "_zeppelin", "_balloon", "_cumulus"):
        assert callable(getattr(backdrops, fn)), fn
    assert "helm" not in inspect.getsource(backdrops.build_cloud).lower() and "sun_fn" not in inspect.getsource(backdrops.build_cloud)
    surf = pygame.Surface((PIX_W, PIX_H), pygame.SRCALPHA)
    backdrops._zeppelin(surf, 400, 200, 1.0, 10)
    backdrops._whale(surf, 600, 300, 1.0, 10)
    backdrops._balloon(surf, 200, 150, 1.0, 10, 0.0)


# --- regression tests for the two issues found on the Pi ------------------------------------------------------------
def test_a_counter_that_cancels_the_attackers_move_mid_loop_does_not_crash_melee(app):
    """Issue 1: with a counter-stance victim and a third fighter later in the list, the bounced attacker's move became
    None part-way through the victim loop and the next iteration read None.rehit."""
    from k8ssmash.fighter import Fighter
    rs = {r.name: r for r in roster()}
    b = Battle(app, [rs["Pod"], rs["Operator"]], human=[False, False])
    atk, vic = b.fighters
    third = Fighter(rs["Kubectl"], 2)
    third.spawn((atk.x + 10, atk.y), -1)
    b.fighters = [atk, vic, third]
    vic.x, vic.y = atk.x + 16, atk.y
    third.x, third.y = atk.x + 14, atk.y
    vic.invuln = third.invuln = 0
    vic._begin(vic.stats.moves["special"])  # Operator's Reconcile: a counter
    vic.move_frame = vic.move.startup + 1
    atk._begin(atk.stats.moves["jab"])
    atk.move_frame = atk.stats.moves["jab"].startup + 1
    b._resolve_melee()  # used to raise AttributeError
    assert atk.move is None  # the attacker ate the counter ...
    assert third.percent == 0.0  # ... and the cancelled move did not carry on and hit the third fighter


def test_the_game_runs_with_only_the_declared_dependencies():
    """Issue 2: numpy is needed at runtime and must be declared; scipy and the speech library must not be needed."""
    import subprocess
    import sys
    import tomllib
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    deps = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    declared = {d.split(">")[0].split("=")[0].strip() for d in deps["dependencies"]}
    assert {"pygame-ce", "numpy"} <= declared
    assert "numpy" not in " ".join(deps["optional-dependencies"]["audio"])
    code = (
        "import sys, os\n"
        "os.environ['SDL_VIDEODRIVER']='dummy'; os.environ['SDL_AUDIODRIVER']='dummy'\n"
        "for m in ('scipy', 'espeakng_loader'):\n    sys.modules[m] = None\n"
        "from k8ssmash.config import Config\nfrom k8ssmash.main import App\nfrom k8ssmash.roster import roster\n"
        "from k8ssmash.scenes.battle import Battle\nfrom k8ssmash.stage import STAGES\n"
        "app = App(Config())\n"
        "for make in STAGES:\n    Battle(app, roster()[:2], stage=make(), human=[False, False]).draw(app.display.canvas)\n"
        "print('ok')\n")
    out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr[-800:]
