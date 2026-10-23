"""Sound effect and music playback. Every call is a safe no-op when audio is unavailable."""
from __future__ import annotations

from pathlib import Path

import pygame

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "audio"
MUSIC_FOR_THEME = {"datacenter": "datacenter", "controlplane": "controlplane", "nodepool": "nodepool"}


class Audio:
    def __init__(self, sfx_volume: float = 0.8, music_volume: float = 0.5, muted: bool = False):
        self.sfx_volume, self.music_volume, self.muted = sfx_volume, music_volume, muted
        self.ok = False
        self.current: str | None = None
        self.played: list[str] = []  # last sounds requested, handy for tests
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            self.ok = True
        except pygame.error:
            self.ok = False

    def _sound(self, name: str) -> pygame.mixer.Sound | None:
        if name not in self._sounds:
            try:
                self._sounds[name] = pygame.mixer.Sound(str(ASSETS / f"{name}.wav"))
            except (pygame.error, FileNotFoundError):
                self._sounds[name] = None
        return self._sounds[name]

    def play(self, name: str, volume: float = 1.0) -> None:
        self.played.append(name)
        del self.played[:-32]
        if not self.ok or self.muted:
            return
        snd = self._sound(name)
        if snd is not None:
            snd.set_volume(self.sfx_volume * volume)
            snd.play()

    def music(self, name: str | None, loop: bool = True) -> None:
        if name == self.current:
            return
        self.current = name
        if not self.ok:
            return
        pygame.mixer.music.stop()
        if name is None or self.muted:
            return
        try:
            pygame.mixer.music.load(str(ASSETS / f"{name}.ogg"))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1 if loop else 0)
        except (pygame.error, FileNotFoundError):
            pass

    def toggle_mute(self) -> None:
        self.muted = not self.muted
        if not self.ok:
            return
        if self.muted:
            pygame.mixer.music.pause()
            pygame.mixer.stop()
        else:
            pygame.mixer.music.unpause()
            if self.current and not pygame.mixer.music.get_busy():
                name, self.current = self.current, None
                self.music(name)
