"""Headless scripted run: plays a few frames with injected inputs and saves screenshots."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from k8ssmash.config import Config
from k8ssmash.main import App, placeholder_roster
from k8ssmash.scenes.battle import READY_FRAMES, Battle

out = sys.argv[1] if len(sys.argv) > 1 else "screenshots/headless.png"
cfg = Config()
cfg.dev_keys = True
app = App(cfg)
battle = Battle(app, placeholder_roster())
app.set_scene(battle)

script = {
    READY_FRAMES + 20: (set(), {"LEFT"}),
    READY_FRAMES + 40: ({"RIGHT", "ATTACK"}, set()),
    READY_FRAMES + 60: ({"RIGHT"}, {"SPECIAL"}),
}
held0, held1 = set(), set()
for frame in range(READY_FRAMES + 90):
    if frame in script:
        held0, held1 = script[frame]
    app.input.players[0].update(held0)
    app.input.players[1].update(held1)
    battle.update()
battle.debug = True
battle.draw(app.display.canvas)
app.display.present()
app.display.screenshot(out)
print("saved", out)
