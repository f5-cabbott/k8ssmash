"""Per-player input: keyboard (dev) and SNES-style USB pads, merged into one action set."""
from __future__ import annotations

import pygame

from k8ssmash.config import ACTIONS, Config

AXIS_THRESHOLD = 0.5


class PlayerInput:
    """Held / just-pressed action sets for one player, updated once per logic frame."""

    def __init__(self) -> None:
        self.held: set[str] = set()
        self.pressed: set[str] = set()
        self.released: set[str] = set()

    def update(self, held: set[str]) -> None:
        self.pressed = held - self.held
        self.released = self.held - held
        self.held = set(held)

    def __contains__(self, action: str) -> bool:
        return action in self.held

    @property
    def axis_x(self) -> int:
        return ("RIGHT" in self.held) - ("LEFT" in self.held)

    @property
    def axis_y(self) -> int:
        return ("DOWN" in self.held) - ("UP" in self.held)


class InputManager:
    def __init__(self, cfg: Config, players: int = 2):
        self.cfg = cfg
        self.players = [PlayerInput() for _ in range(players)]
        self.pads: list[pygame.joystick.JoystickType | None] = [None] * players
        self.lost: set[int] = set()  # slots that had a pad and lost it
        self._had_pad: set[int] = set()
        self._keycodes = [
            {a: pygame.key.key_code(name) for a, name in keys.items() if name} for keys in cfg.keys
        ]
        pygame.joystick.init()
        for index in range(pygame.joystick.get_count()):
            self._add_pad(index)

    # --- hotplug -------------------------------------------------------------------------
    def _add_pad(self, device_index: int) -> None:
        try:
            joy = pygame.joystick.Joystick(device_index)
        except pygame.error:
            return
        if any(p is not None and p.get_instance_id() == joy.get_instance_id() for p in self.pads):
            return
        wanted = [n.lower() for n in self.cfg.pad_name_filter]
        if wanted and not any(n in joy.get_name().lower() for n in wanted):
            return
        # Prefer a slot that lost its pad so a re-plug resumes the right player.
        order = sorted(range(len(self.pads)), key=lambda s: (s not in self.lost, s))
        for slot in order:
            if self.pads[slot] is None:
                self.pads[slot] = joy
                self.lost.discard(slot)
                self._had_pad.add(slot)
                return

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.JOYDEVICEADDED:
            self._add_pad(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED:
            for slot, pad in enumerate(self.pads):
                if pad is not None and pad.get_instance_id() == event.instance_id:
                    self.pads[slot] = None
                    self.lost.add(slot)

    # --- polling -------------------------------------------------------------------------
    def _keyboard_held(self, slot: int) -> set[str]:
        keys = pygame.key.get_pressed()
        return {a for a, code in self._keycodes[slot].items() if keys[code]}

    def _pad_held(self, slot: int) -> set[str]:
        pad = self.pads[slot]
        held: set[str] = set()
        if pad is None:
            return held
        x = y = 0.0
        if pad.get_numaxes() >= 2:
            x, y = pad.get_axis(0), pad.get_axis(1)
        if pad.get_numhats() >= 1:
            hx, hy = pad.get_hat(0)
            x, y = x or hx, y or -hy
        if x < -AXIS_THRESHOLD:
            held.add("LEFT")
        elif x > AXIS_THRESHOLD:
            held.add("RIGHT")
        if y < -AXIS_THRESHOLD:
            held.add("UP")
        elif y > AXIS_THRESHOLD:
            held.add("DOWN")
        nbuttons = pad.get_numbuttons()
        for action, buttons in self.cfg.pad.items():
            if action in ACTIONS and any(b < nbuttons and pad.get_button(b) for b in buttons):
                held.add(action)
        return held

    def poll(self) -> None:
        for slot, player in enumerate(self.players):
            player.update(self._keyboard_held(slot) | self._pad_held(slot))

    def raw_state(self, slot: int) -> tuple[list[int], list[float], tuple[int, int]] | None:
        """Physical buttons down, axis values and hat for a slot's pad (for the test screen)."""
        pad = self.pads[slot]
        if pad is None:
            return None
        buttons = [b for b in range(pad.get_numbuttons()) if pad.get_button(b)]
        axes = [round(pad.get_axis(a), 2) for a in range(pad.get_numaxes())]
        hat = pad.get_hat(0) if pad.get_numhats() else (0, 0)
        return buttons, axes, hat

    def any_pressed(self, action: str) -> bool:
        return any(action in p.pressed for p in self.players)
