import time

import pygame
import pytest

from k8ssmash import backdrops
from k8ssmash.config import CANVAS_H, CANVAS_W
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
