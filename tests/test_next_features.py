"""CronJob, stage set pieces, reactive scenery, leitmotifs, the title/select polish and the lifelike instruments."""
import numpy as np
import pygame
import pytest

from k8ssmash import backdrops, ui
from k8ssmash.audio import arranger, instruments as I, sfx
from k8ssmash.config import Config
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
        surf = pygame.Surface((960, 540))
        sel.draw(surf)
        panel_bottom = round((174 + 112) * ui.SCALE)
        legend_top = round(290 * ui.SCALE)
        # the strip between the player panels and the legend holds nothing but background
        strip = [surf.get_at((x, y))[:3] for x in range(30, 930, 40) for y in range(panel_bottom + 6, legend_top - 1)]
        assert all(c == (16, 20, 38) for c in strip)
