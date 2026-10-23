"""Pose generators for every animation. Attack styles have three frames: startup, active, recovery."""
from __future__ import annotations

import math

from k8ssmash.art.rig import Pose

# name -> (frame count, fps, loops)
ANIMS: dict[str, tuple[int, int, bool]] = {
    "idle": (4, 5, True),
    "run": (6, 14, True),
    "jump": (1, 1, False),
    "fall": (1, 1, False),
    "djump": (3, 16, False),
    "shield": (1, 1, False),
    "duck": (1, 1, False),
    "hurt": (2, 8, True),
    "jab": (3, 0, False),
    "side": (3, 0, False),
    "up": (3, 0, False),
    "down": (3, 0, False),
    "cast": (3, 0, False),
    "dash": (3, 0, False),
    "rise": (3, 0, False),
    "counter": (3, 0, False),
    "buff": (3, 0, False),
}


def pose_for(anim: str, i: int) -> Pose:
    return _POSES[anim](i)


def idle(i: int) -> Pose:
    bob = (0, -1, -1, 0)[i]
    return Pose(bob=bob, crouch=(0, 0, 0, 0)[i], arm_f=(14, 10 + i), arm_b=(-12, -4), head_dy=-bob * 0.3)


def run(i: int) -> Pose:
    ph = i / 6 * 2 * math.pi
    sw = lambda p: (math.sin(p) * 11, max(0.0, -math.cos(p)) * 8)
    return Pose(lean=4, bob=-abs(math.sin(ph)) * 2, crouch=1,
                f_foot=sw(ph), b_foot=sw(ph + math.pi),
                arm_f=(-math.sin(ph) * 55, -math.sin(ph) * 55 + 35),
                arm_b=(math.sin(ph) * 55, math.sin(ph) * 55 + 35))


def jump(i: int) -> Pose:
    return Pose(lean=1, crouch=-1, f_foot=(7, 7), b_foot=(-3, 9), arm_f=(150, 160), arm_b=(-150, -160))


def fall(i: int) -> Pose:
    return Pose(lean=0, f_foot=(9, 3), b_foot=(-9, 3), arm_f=(125, 150), arm_b=(-125, -150), head_dy=1)


def djump(i: int) -> Pose:
    tuck = (0.5, 1.0, 0.7)[i]
    return Pose(lean=2 * i, crouch=2 * tuck, f_foot=(6, 9 * tuck), b_foot=(-4, 10 * tuck),
                arm_f=(70, 100), arm_b=(-70, -100), flash=False)


def shield(i: int) -> Pose:
    return Pose(crouch=3, lean=2, arm_f=(60, 150), arm_b=(30, 170), f_foot=(7, 0), b_foot=(-6, 0))


def duck(i: int) -> Pose:
    return Pose(crouch=11, lean=3, head_dy=2, arm_f=(40, 70), arm_b=(-25, 0), f_foot=(9, 0), b_foot=(-9, 0))


def hurt(i: int) -> Pose:
    return Pose(lean=-5 - i, head_dx=-3, head_dy=1 + i, arm_f=(-120, -150 + i * 20),
                arm_b=(-95, -110), f_foot=(4, 0), b_foot=(-8, 3 + i * 2))


def jab(i: int) -> Pose:
    return [
        Pose(lean=-2, arm_f=(-30, -10), arm_b=(30, 40), f_foot=(6, 0), b_foot=(-7, 0)),
        Pose(lean=5, arm_f=(88, 92), arm_b=(-20, 15), f_foot=(9, 0), b_foot=(-6, 0)),
        Pose(lean=2, arm_f=(60, 80), arm_b=(-12, 10), f_foot=(7, 0), b_foot=(-5, 0)),
    ][i]


def side(i: int) -> Pose:
    return [
        Pose(lean=-5, crouch=2, arm_f=(-60, -110), arm_b=(-40, -90), f_foot=(4, 0), b_foot=(-10, 0)),
        Pose(lean=8, crouch=3, arm_f=(95, 100), arm_b=(30, 60), f_foot=(13, 0), b_foot=(-9, 0)),
        Pose(lean=4, crouch=2, arm_f=(70, 90), arm_b=(0, 20), f_foot=(10, 0), b_foot=(-7, 0)),
    ][i]


def up(i: int) -> Pose:
    return [
        Pose(crouch=4, lean=-1, arm_f=(30, 10), arm_b=(-30, -10), f_foot=(6, 0), b_foot=(-6, 0)),
        Pose(lean=1, crouch=-1, arm_f=(172, 178), arm_b=(150, 170), f_foot=(4, 2), b_foot=(-4, 2), head_dy=1),
        Pose(lean=0, arm_f=(120, 150), arm_b=(100, 130), f_foot=(5, 0), b_foot=(-5, 0)),
    ][i]


def down(i: int) -> Pose:
    return [
        Pose(crouch=5, lean=-2, arm_f=(40, 20), arm_b=(-40, -20), f_foot=(4, 0), b_foot=(-9, 0)),
        Pose(crouch=7, lean=5, arm_f=(60, 40), arm_b=(-60, -20), f_foot=(17, 1), b_foot=(-9, 0)),
        Pose(crouch=4, lean=2, arm_f=(30, 20), arm_b=(-30, -10), f_foot=(10, 0), b_foot=(-7, 0)),
    ][i]


def cast(i: int) -> Pose:
    return [
        Pose(lean=-3, arm_f=(40, 100), arm_b=(30, 110), f_foot=(6, 0), b_foot=(-7, 0)),
        Pose(lean=3, arm_f=(88, 90), arm_b=(84, 90), f_foot=(8, 0), b_foot=(-7, 0)),
        Pose(lean=1, arm_f=(70, 85), arm_b=(60, 80), f_foot=(7, 0), b_foot=(-6, 0)),
    ][i]


def dash(i: int) -> Pose:
    return [
        Pose(lean=-4, crouch=3, arm_f=(-50, -80), arm_b=(-70, -100), f_foot=(5, 0), b_foot=(-10, 0)),
        Pose(lean=11, crouch=5, arm_f=(100, 95), arm_b=(-60, -50), f_foot=(14, 1), b_foot=(-12, 5)),
        Pose(lean=5, crouch=3, arm_f=(60, 70), arm_b=(-20, -10), f_foot=(9, 0), b_foot=(-8, 0)),
    ][i]


def rise(i: int) -> Pose:
    return [
        Pose(crouch=5, lean=-1, arm_f=(20, 10), arm_b=(-20, -10), f_foot=(5, 0), b_foot=(-5, 0)),
        Pose(crouch=-2, lean=1, arm_f=(170, 175), arm_b=(165, 175), f_foot=(2, 7), b_foot=(-2, 8), head_dy=1),
        Pose(lean=0, arm_f=(135, 160), arm_b=(125, 150), f_foot=(4, 5), b_foot=(-4, 6)),
    ][i]


def counter(i: int) -> Pose:
    return [
        Pose(crouch=4, lean=-2, arm_f=(70, 160), arm_b=(40, 170), f_foot=(7, 0), b_foot=(-7, 0)),
        Pose(crouch=5, lean=-1, arm_f=(75, 165), arm_b=(45, 175), f_foot=(8, 0), b_foot=(-8, 0), flash=True),
        Pose(crouch=2, lean=1, arm_f=(40, 80), arm_b=(0, 30), f_foot=(6, 0), b_foot=(-6, 0)),
    ][i]


def buff(i: int) -> Pose:
    return [
        Pose(crouch=3, arm_f=(30, 10), arm_b=(-30, -10), f_foot=(6, 0), b_foot=(-6, 0)),
        Pose(crouch=-1, lean=0, arm_f=(120, 150), arm_b=(-120, -150), f_foot=(8, 0), b_foot=(-8, 0), flash=True),
        Pose(arm_f=(60, 90), arm_b=(-60, -90), f_foot=(7, 0), b_foot=(-7, 0)),
    ][i]


_POSES = {"idle": idle, "run": run, "jump": jump, "fall": fall, "djump": djump, "shield": shield, "duck": duck,
          "hurt": hurt, "jab": jab, "side": side, "up": up, "down": down, "cast": cast,
          "dash": dash, "rise": rise, "counter": counter, "buff": buff}
