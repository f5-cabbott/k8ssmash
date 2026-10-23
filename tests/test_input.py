import pygame

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
    assert d.gpu and d.screen.get_size() == (640, 360)
    d.canvas.fill((10, 20, 30))
    d.present()
    out = tmp_path / "s.png"
    d.screenshot(out)
    img = pygame.image.load(str(out))
    assert img.get_size() == (640 * d.scale, 360 * d.scale)
    d.cycle_resolution()
    assert (cfg.width, cfg.height) == (2560, 1440)


def test_display_software_fallback(tmp_path):
    from k8ssmash.render import Display
    pygame.init()
    d = Display(Config(), prefer_gpu=False)
    assert not d.gpu and d.scale == 3
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
