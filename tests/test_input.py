import pygame
import pytest

from k8ssmash.config import PIX_H, PIX_W, RS

from k8ssmash.config import Config
from k8ssmash.input import InputManager, PlayerInput


def test_player_input_pressed_released():
    p = PlayerInput()
    p.update({"JUMP"})
    assert p.pressed == {"JUMP"} and not p.released
    p.update({"JUMP", "LEFT"})
    assert p.pressed == {"LEFT"}
    p.update(set())
    assert p.released == {"JUMP", "LEFT"} and p.axis_x == 0


def test_axes():
    p = PlayerInput()
    p.update({"LEFT", "DOWN"})
    assert p.axis_x == -1 and p.axis_y == 1


def test_default_pad_filter_excludes_xbox_style_pads():
    assert Config().pad_name_filter == ["USB Gamepad"]


def test_manager_builds_with_keyboard_only():
    pygame.init()
    pygame.display.set_mode((64, 64))
    mgr = InputManager(Config())
    mgr.poll()
    assert len(mgr.players) == 2


def test_display_gpu_path_and_screenshot(tmp_path):
    from k8ssmash.render import Display
    pygame.init()
    cfg = Config()
    d = Display(cfg)
    assert d.gpu and d.screen.get_size() == (PIX_W, PIX_H)
    d.canvas.fill((10, 20, 30))
    d.present()
    out = tmp_path / "s.png"
    d.screenshot(out)
    img = pygame.image.load(str(out))
    assert img.get_size() == (PIX_W, PIX_H)  # the screenshot is the canvas as drawn
    d.cycle_resolution()
    assert (cfg.width, cfg.height) == (2560, 1440)


@pytest.mark.skipif(RS != 2, reason="expectations are for the default 2x render scale")
def test_display_software_fallback(tmp_path, monkeypatch):
    from k8ssmash.render import Display
    pygame.init()
    monkeypatch.setattr(Display, "desktop_size", staticmethod(lambda: (3440, 1440)))
    d = Display(Config(), prefer_gpu=False)
    assert not d.gpu and d.scale == 1.0  # a 1080p window shows the 1080p canvas 1:1
    d.present()
    d.screenshot(tmp_path / "s.png")


def test_swap_pads_exchanges_slots_and_persists():
    pygame.init()
    pygame.display.set_mode((64, 64))
    cfg = Config()
    mgr = InputManager(cfg)
    mgr.pads = ["A", "B"]
    mgr.lost = {0}
    mgr.swap_pads()
    assert mgr.pads == ["B", "A"] and mgr.lost == {1} and cfg.swap_pads
    mgr.swap_pads()
    assert mgr.pads == ["A", "B"] and not cfg.swap_pads


def test_default_pad_mapping_matches_the_real_snes_clones():
    """Measured with tools/padtest.py on the booth pads: B=2 A=1 Y=3 X=0 L=4 R=5 Select=8 Start=9."""
    from k8ssmash.config import DEFAULT_PAD
    assert DEFAULT_PAD == {"JUMP": [3, 0], "ATTACK": [2], "SPECIAL": [1], "SHIELD": [4, 5], "START": [9], "SELECT": [8]}


def test_menus_keep_their_layout_when_drawn_on_the_world_canvas(tmp_path):
    """Menu scenes draw on a 640x360 grid and are scaled up to the 960x540 world; battles draw natively."""
    from k8ssmash.render import Display
    from k8ssmash.scenes.base import Scene
    from k8ssmash.scenes.battle import Battle
    pygame.init()
    d = Display(Config())

    class Menu(Scene):
        native = (640, 360)  # a scene may still opt into a smaller design grid; it is scaled up

        def draw(self, canvas):
            assert canvas.get_size() == (640, 360)  # the scene sees its own design size
            canvas.fill((200, 0, 0))
            pygame.draw.rect(canvas, (0, 0, 255), (320, 180, 320, 180))  # bottom-right quarter

    d.draw_scene(Menu(None))
    assert d.canvas.get_at((100, 100))[:3] == (200, 0, 0)
    assert d.canvas.get_at((PIX_W - 100, PIX_H - 100))[:3] == (0, 0, 255)  # quarter maps to the same quarter of the bigger canvas
    assert Battle.native == (PIX_W, PIX_H) and Scene.native == (PIX_W, PIX_H)  # battles and menus both draw at render size


def test_windows_always_fit_the_desktop(monkeypatch):
    """On an ultrawide (3440x1440) a 2560x1440 window ran off the top of the screen; sizes now shrink to fit."""
    from k8ssmash.render import Display
    monkeypatch.setattr(Display, "desktop_size", staticmethod(lambda: (3440, 1440)))
    w, h = Display.fit_to_desktop(2560, 1440)
    assert h <= 1440 * 0.86 and abs(w / h - 16 / 9) < 0.02  # still 16:9, with room for the title bar
    assert Display.fit_to_desktop(1920, 1080) == (1920, 1080)  # already fits: untouched
    assert Display.fit_to_desktop(1280, 720) == (1280, 720)
    monkeypatch.setattr(Display, "desktop_size", staticmethod(lambda: (1366, 768)))
    w, h = Display.fit_to_desktop(1920, 1080)
    assert w <= 1366 and h <= 768 * 0.86


def test_f10_only_cycles_through_sizes_that_fit(monkeypatch):
    from k8ssmash.render import Display
    pygame.init()
    monkeypatch.setattr(Display, "desktop_size", staticmethod(lambda: (3440, 1440)))
    cfg = Config()
    d = Display(cfg)
    seen = set()
    for _ in range(6):
        d.cycle_resolution()
        seen.add((cfg.width, cfg.height))
    assert (2560, 1440) not in seen and seen <= {(1280, 720), (1600, 900), (1920, 1080)}
