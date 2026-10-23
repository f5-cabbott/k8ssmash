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
