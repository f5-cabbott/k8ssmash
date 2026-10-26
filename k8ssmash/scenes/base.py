from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from k8ssmash.config import PIX_H, PIX_W

if TYPE_CHECKING:
    from k8ssmash.main import App


class Scene:
    # The design size this scene draws at. Display.draw_scene scales it to the world canvas when it differs.
    native: tuple[int, int] = (PIX_W, PIX_H)

    def __init__(self, app: "App"):
        self.app = app

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self) -> None:
        pass

    def draw(self, canvas: pygame.Surface) -> None:
        pass
