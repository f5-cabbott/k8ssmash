import time

import pygame
import pytest

from k8ssmash import backdrops
from k8ssmash.config import WORLD_H as CANVAS_H, WORLD_W as CANVAS_W
from k8ssmash.stage import STAGES

THEMES = ["datacenter", "controlplane", "nodepool"]


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    pygame.quit()


def test_every_stage_has_a_backdrop_builder():
    for make in STAGES:
        assert make().theme in backdrops.BUILDERS


@pytest.mark.parametrize("theme", THEMES)
def test_backdrop_fills_the_screen_and_survives_camera_extremes(theme):
    canvas = pygame.Surface((CANVAS_W, CANVAS_H)).convert()
    bd = backdrops.get_backdrop(theme)
    for cam in (-9999, -100, 0, 100, 9999):  # the camera is clamped, so layers never run out of art
        canvas.fill((255, 0, 255))
        bd.draw(canvas, 500, cam)
        magenta = sum(1 for x in range(0, CANVAS_W, 40) for y in range(0, CANVAS_H, 40)
                      if canvas.get_at((x, y))[:3] == (255, 0, 255))
        assert magenta == 0, f"{theme} cam={cam} left unpainted sky"


@pytest.mark.parametrize("theme", THEMES)
def test_layers_move_at_different_speeds_for_parallax(theme):
    bd = backdrops.get_backdrop(theme)
    factors = sorted({round(i.factor, 3) for i in bd.items if hasattr(i, "factor")})
    assert len(factors) >= 3  # at least three depth layers
    a, b = pygame.Surface((CANVAS_W, CANVAS_H)), pygame.Surface((CANVAS_W, CANVAS_H))
    bd.draw(a, 100, -100)
    bd.draw(b, 100, 100)
    assert pygame.image.tobytes(a, "RGB") != pygame.image.tobytes(b, "RGB")


@pytest.mark.parametrize("theme", THEMES)
def test_animation_changes_over_time(theme):
    bd = backdrops.get_backdrop(theme)
    a, b = pygame.Surface((CANVAS_W, CANVAS_H)), pygame.Surface((CANVAS_W, CANVAS_H))
    bd.draw(a, 10, 0)
    bd.draw(b, 200, 0)
    assert pygame.image.tobytes(a, "RGB") != pygame.image.tobytes(b, "RGB")


@pytest.mark.parametrize("theme", THEMES)
def test_drawing_is_cheap_enough_for_a_pi(theme):
    canvas = pygame.Surface((CANVAS_W, CANVAS_H)).convert()
    bd = backdrops.get_backdrop(theme)
    t0 = time.perf_counter()
    for i in range(30):
        bd.draw(canvas, i, i)
    assert (time.perf_counter() - t0) / 30 < 0.012  # well under a 16 ms frame even on a desktop at half speed


def test_dither_gradient_is_banded_and_dithered():
    g = backdrops.dither_gradient(64, 64, [(0, (0, 0, 0)), (1, (255, 255, 255))], bands=8)
    colors = {g.get_at((x, y))[:3] for x in range(64) for y in range(64)}
    assert 6 <= len(colors) <= 12  # a handful of discrete tones, not a smooth ramp
    assert g.get_at((0, 0))[0] < g.get_at((0, 63))[0]


@pytest.mark.parametrize("theme", THEMES)
def test_platforms_render_for_every_size(theme):
    from k8ssmash.stage import Platform
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    for rect, thin in ((pygame.Rect(100, 250, 400, 40), False), (pygame.Rect(170, 185, 120, 8), True)):
        backdrops.draw_platform(canvas, Platform(rect, dropthrough=thin), theme)


# --- calm backgrounds: the fighters and platforms must read first -------------------------------------
def _luma(surf):
    a = pygame.surfarray.array3d(surf).astype(float)
    return 0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2]


def blob_motion(a, b, jump=45):
    """Share of the screen covered by *small* sharp changes between two frames. Full-width lines (the floor grid rolling a
    pixel) are not counted: they cannot be mistaken for a projectile, small bright movers can."""
    changed = abs(b - a) > jump
    row_total = changed.sum(axis=0)  # changed pixels per screen row
    changed[:, row_total > a.shape[0] * 0.4] = False
    return float(changed.mean())


@pytest.mark.parametrize("theme", THEMES)
def test_backdrops_are_dim_and_have_no_bright_specks(theme):
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    backdrops.get_backdrop(theme).draw(canvas, 300, 0)
    luma = _luma(canvas)
    assert (luma > 150).mean() < 0.03, "too much of the background is brightly lit"
    assert (luma > 215).mean() < 0.006, "near-white specks in the background steal attention"
    assert luma.mean() < 40  # a low-value scene: the fighters (and the HUD) are the brightest things on screen


@pytest.mark.parametrize("theme", THEMES)
def test_background_has_no_small_fast_movers(theme):
    """Small bright things moving quickly look like projectiles. Only slow, large motion is allowed."""
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    bd = backdrops.get_backdrop(theme)
    changed = []
    for start in range(400, 472, 9):  # many frame pairs, so one unlucky frame can't decide it
        bd.draw(canvas, start, 0)
        a = _luma(canvas)
        bd.draw(canvas, start + 1, 0)
        changed.append(blob_motion(a, _luma(canvas)))
    assert sum(changed) / len(changed) < 0.0008 and max(changed) < 0.002  # the old busy stages measured 0.4-0.6%
    bd.draw(canvas, 400, 0)
    a = _luma(canvas)
    bd.draw(canvas, 640, 0)
    assert (abs(_luma(canvas) - a) > 5).any()  # but it is not frozen: something slow and large still moves


@pytest.mark.parametrize("theme", THEMES)
def test_platforms_outshine_the_scenery(theme):
    """A platform's top edge must be brighter than anything the backdrop itself draws around it."""
    from k8ssmash.stage import Platform
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    backdrops.get_backdrop(theme).draw(canvas, 300, 0)
    backdrop_peak = float(_luma(canvas).max())
    for rect, thin in ((pygame.Rect(100, 250, 400, 40), False), (pygame.Rect(170, 185, 120, 8), True)):
        canvas.fill((0, 0, 0))
        backdrops.draw_platform(canvas, Platform(rect, dropthrough=thin), theme)
        assert float(_luma(canvas).max()) >= min(backdrop_peak, 235), (theme, thin)
