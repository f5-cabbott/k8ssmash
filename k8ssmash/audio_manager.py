"""Sound effect and music playback. Every call is a safe no-op when audio is unavailable."""
from __future__ import annotations

from pathlib import Path

import pygame

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "audio"
MUSIC_FOR_THEME = {"datacenter": "datacenter", "controlplane": "controlplane", "nodepool": "nodepool"}
# Loud moments briefly pull the music down so the effects stay clear of it (name -> music level while it plays).
DUCK = {"hit_heavy": 0.5, "ko": 0.4, "special": 0.72, "explosion": 0.5, "counter": 0.6, "pickup": 0.8, "go": 0.6,
        "shield_break": 0.6}
DUCK_RECOVERY = 0.035  # fraction of the gap closed per logic frame (about a third of a second)


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


class Audio:
    def __init__(self, sfx_volume: float = 0.9, music_volume: float = 0.4, muted: bool = False):
        self.sfx_volume, self.music_volume, self.muted = sfx_volume, music_volume, muted
        self.ok = False
        self.current: str | None = None
        self.played: list[str] = []  # last sounds requested, handy for tests
        self.last_file = ""
        self._duck = 1.0
        self._applied = -1.0
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

    def has(self, name: str) -> bool:
        return (ASSETS / f"{name}.wav").exists()

    def play(self, name: str, volume: float = 1.0, pan: float = 0.0, fighter: str | None = None) -> None:
        """Play an effect. With `fighter`, that character's own version is used when it exists, and `pan`
        (-1 left .. +1 right) places it where the action is on screen."""
        self.played.append(name)
        del self.played[:-32]
        resolved = f"{slug(fighter)}__{name}" if fighter and self.has(f"{slug(fighter)}__{name}") else name
        self.last_file = resolved
        if name in DUCK:
            self._duck = min(self._duck, DUCK[name])
        if not self.ok or self.muted:
            return
        snd = self._sound(resolved)
        if snd is None:
            return
        snd.set_volume(1.0)
        channel = snd.play()
        if channel is not None:
            vol = self.sfx_volume * volume
            pan = max(-1.0, min(1.0, pan))
            channel.set_volume(vol * min(1.0, 1.0 - pan * 0.9 if pan > 0 else 1.0),
                               vol * min(1.0, 1.0 + pan * 0.9 if pan < 0 else 1.0))

    def update(self) -> None:
        """Call once per logic frame: eases the music back up after a duck."""
        self._duck += (1.0 - self._duck) * DUCK_RECOVERY
        if self.ok and not self.muted and abs(self._duck - self._applied) > 0.01:
            pygame.mixer.music.set_volume(self.music_volume * self._duck)
            self._applied = self._duck

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
            pygame.mixer.music.set_volume(self.music_volume * self._duck)
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
