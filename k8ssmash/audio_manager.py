"""Sound effect and music playback. Every call is a safe no-op when audio is unavailable."""
from __future__ import annotations

from pathlib import Path

import pygame

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "audio"
MUSIC_FOR_THEME = {"datacenter": "datacenter", "controlplane": "controlplane", "nodepool": "nodepool", "etcd": "etcd",
                   "mesh": "mesh"}
# Loud moments briefly pull the music down so the effects stay clear of it (name -> music level while it plays).
DUCK = {"hit_heavy": 0.5, "ko": 0.4, "special": 0.72, "explosion": 0.5, "counter": 0.6, "pickup": 0.8, "go": 0.6,
        "shield_break": 0.6,
        "ann_ready": 0.55, "ann_fight": 0.5, "ann_game": 0.5, "ann_final_stock": 0.55}
STEM_GAIN = 0.95  # the intensity layer at full level, relative to the song
DUCK_RECOVERY = 0.035  # fraction of the gap closed per logic frame (about a third of a second)


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


class Audio:
    def __init__(self, sfx_volume: float = 0.55, music_volume: float = 0.4, muted: bool = False,
                 master_volume: float = 1.0):
        self.sfx_volume, self.music_volume, self.muted, self.master = sfx_volume, music_volume, muted, master_volume
        self.ok = False
        self.current: str | None = None
        self.played: list[str] = []  # last sounds requested, handy for tests
        self.last_file = ""
        self._duck = 1.0
        self.stem_name: str | None = None
        self._stem_level = 0.0
        self._stem_sound: pygame.mixer.Sound | None = None
        self._applied = -1.0
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)  # channel 0 is kept for the music's intensity layer
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
            vol = self.sfx_volume * self.master * volume
            pan = max(-1.0, min(1.0, pan))
            channel.set_volume(vol * min(1.0, 1.0 - pan * 0.9 if pan > 0 else 1.0),
                               vol * min(1.0, 1.0 + pan * 0.9 if pan < 0 else 1.0))

    def set_volumes(self, master: float | None = None, sfx: float | None = None, music: float | None = None) -> None:
        """Change volumes live (the settings screen): the music follows immediately."""
        if master is not None:
            self.master = max(0.0, min(1.0, master))
        if sfx is not None:
            self.sfx_volume = max(0.0, min(1.0, sfx))
        if music is not None:
            self.music_volume = max(0.0, min(1.0, music))
        self._applied = -1.0  # force the next update to re-apply the music volume

    def update(self) -> None:
        """Call once per logic frame: eases the music back up after a duck."""
        self._duck += (1.0 - self._duck) * DUCK_RECOVERY
        if self.ok and not self.muted and abs(self._duck - self._applied) > 0.01:
            pygame.mixer.music.set_volume(self.music_volume * self.master * self._duck)
            self._applied = self._duck
        self._apply_stem()

    def music(self, name: str | None, loop: bool = True, stem: str | None = None) -> None:
        """Start a song. With `stem`, a second recording of the same song (just percussion and arpeggios) is started in
        step with it; set_stem_level() then brings it in and out as a match heats up."""
        if name == self.current and (stem is None or stem == self.stem_name):
            return
        self.current = name
        self._stop_stem()
        if not self.ok:
            return
        pygame.mixer.music.stop()
        if name is None or self.muted:
            return
        layer = None
        if stem is not None:  # decode the stem first, so both start within a few microseconds of each other
            try:
                layer = pygame.mixer.Sound(str(ASSETS / f"{stem}.ogg"))
            except (pygame.error, FileNotFoundError):
                layer = None
        try:
            pygame.mixer.music.load(str(ASSETS / f"{name}.ogg"))
            pygame.mixer.music.set_volume(self.music_volume * self.master * self._duck)
            pygame.mixer.music.play(-1 if loop else 0)
        except (pygame.error, FileNotFoundError):
            return
        if layer is not None:
            self._stem_sound, self.stem_name, self._stem_level = layer, stem, 0.0
            pygame.mixer.Channel(0).play(layer, loops=-1)
            self._apply_stem()

    def set_stem_level(self, level: float) -> None:
        self._stem_level = max(0.0, min(1.0, level))

    def _apply_stem(self) -> None:
        if self.ok and self._stem_sound is not None and not self.muted:
            pygame.mixer.Channel(0).set_volume(self._stem_level * STEM_GAIN * self.music_volume * self.master * self._duck)

    def _stop_stem(self) -> None:
        self.stem_name, self._stem_sound, self._stem_level = None, None, 0.0
        if self.ok:
            pygame.mixer.Channel(0).stop()

    def pause_music(self, paused: bool) -> None:
        if self.ok and not self.muted:
            (pygame.mixer.music.pause if paused else pygame.mixer.music.unpause)()
            (pygame.mixer.Channel(0).pause if paused else pygame.mixer.Channel(0).unpause)()

    def fade_out(self, ms: int = 900) -> None:
        """Let the current music die away (the arena song when a match ends) instead of cutting or carrying on."""
        self.current = None
        if self.ok:
            pygame.mixer.music.fadeout(ms)
            pygame.mixer.Channel(0).fadeout(ms)
        self.stem_name, self._stem_sound = None, None

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
