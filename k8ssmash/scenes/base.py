from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from k8ssmash.main import App


class Scene:
    # The design size this scene draws at. Display.draw_scene scales it to the world canvas when it differs.
    native: tuple[int, int] = (960, 540)

    def __init__(self, app: "App"):
        self.app = app

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self) -> None:
        pass

    def draw(self, canvas: pygame.Surface) -> None:
        pass
