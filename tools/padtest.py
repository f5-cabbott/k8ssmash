"""Print raw joystick events so you can see which button number is which physical button.

Run:  .venv/bin/python tools/padtest.py   (Ctrl+C to quit). Press each button on each pad.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

pygame.init()
pygame.display.set_mode((64, 64))
pygame.joystick.init()
pads = {}
for i in range(pygame.joystick.get_count()):
    j = pygame.joystick.Joystick(i)
    pads[j.get_instance_id()] = j
    print(f"device {i}: instance={j.get_instance_id()} name={j.get_name()!r} "
          f"axes={j.get_numaxes()} buttons={j.get_numbuttons()} hats={j.get_numhats()}")
print("Press buttons... (Ctrl+C to quit)")
clock = pygame.time.Clock()
try:
    while True:
        for e in pygame.event.get():
            if e.type == pygame.JOYBUTTONDOWN:
                print(f"instance {e.instance_id}: button {e.button} DOWN")
            elif e.type == pygame.JOYAXISMOTION and abs(e.value) > 0.5:
                print(f"instance {e.instance_id}: axis {e.axis} = {e.value:+.0f}")
            elif e.type == pygame.JOYHATMOTION and e.value != (0, 0):
                print(f"instance {e.instance_id}: hat {e.value}")
        clock.tick(120)
except KeyboardInterrupt:
    pass
