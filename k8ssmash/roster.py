"""The eight fighters. Every fighter overrides the shared normals where it wants a different feel
and has four unique specials: neutral, side, up (recovery) and down."""
from __future__ import annotations

from k8ssmash.fighter import BUFF_ARMOR, BUFF_HASTE, FighterStats
from k8ssmash.moves import Move, ProjectileDef, default_moveset


def moveset(**overrides: Move) -> dict[str, Move]:
    moves = default_moveset()
    moves.update(overrides)
    return moves


def pod() -> FighterStats:
    """Balanced all-rounder: the reference fighter."""
    return FighterStats(
        "Pod", (70, 150, 255), blurb="Balanced all-rounder.",
        moves=moveset(**{
            "jab": Move("splash", 3, 8, 10, (6, -34, 28, 20), 3, 2.0, 0.016, 40, rehit=4, anim="jab"),
            "side": Move("tail whip", 8, 5, 16, (2, -33, 50, 16), 9, 3.6, 0.055, 22, anim="side"),
            "up": Move("spout", 7, 7, 14, (-4, -88, 24, 62), 7, 3.8, 0.05, 88, anim="up"),
            "down": Move("belly flop", 6, 5, 15, (-32, -16, 66, 16), 6, 2.8, 0.04, 70, anim="down"),
            "special": Move("bubble", 11, 1, 20, anim="cast", announce="Bubble Blast", projectile=ProjectileDef(
                speed=3.6, width=20, height=20, damage=7, base_kb=3.0, kb_growth=0.045, angle=50, life=120, wave=1.3,
                color=(150, 215, 255), shape="bubble")),
            "special_side": Move("rolling update", 9, 14, 16, (4, -38, 24, 32), 10, 4.2, 0.065, 35, dash=4.4,
                                 anim="dash", announce="Rolling Update"),
            "special_up": Move("restart", 7, 8, 14, (-10, -62, 24, 40), 8, 3.8, 0.06, 80, rise=9.6,
                               once_per_air=True, anim="rise", announce="Restart"),
            "special_down": Move("replica", 12, 1, 18, anim="cast", announce="Replica!", projectile=ProjectileDef(
                speed=0, width=14, height=14, damage=0, base_kb=0, kb_growth=0, angle=0, life=100,
                gravity=0.3, spawn_dx=18, spawn_dy=-8, color=(70, 150, 255), shape="bomb", stick=True,
                explode_radius=40, explode_damage=10, replace_existing=True)),
        }))


def statefulset() -> FighterStats:
    """Sturdy foreman: big, friendly and tough, but no longer slow. Carries a storage drum and a pallet of ideas."""
    return FighterStats(
        "StatefulSet", (240, 204, 58), weight=118, run_speed=3.3, air_speed=2.95, jump_vel=-8.9,
        gravity=0.39, width=30, height=52, air_jumps=3, blurb="Sturdy foreman. Big hits, big heart.",
        moves=moveset(**{
            "jab": Move("glove punch", 3, 3, 9, (8, -34, 30, 18), 5, 2.6, 0.024, 35, anim="jab"),
            "side": Move("drum swing", 9, 5, 18, (8, -46, 50, 34), 13, 4.6, 0.075, 30, lunge=1.5, anim="side"),
            "up": Move("hard-hat bonk", 5, 7, 14, (-10, -84, 28, 38), 9, 3.8, 0.06, 80, anim="up"),
            "down": Move("ground pound", 10, 6, 20, (-48, -16, 96, 18), 12, 3.8, 0.065, 70, anim="down"),
            "special": Move("persistent volume", 12, 1, 18, anim="cast", announce="Persistent Volume",
                            projectile=ProjectileDef(
                                speed=4.4, width=22, height=22, damage=7, base_kb=3.0, kb_growth=0.04, angle=40, life=80,
                                spawn_dy=-30, color=(110, 150, 210), shape="drum", boomerang=True, pierce=True,
                                hit_interval=30)),
            "special_side": Move("barrel roll", 9, 18, 18, (6, -44, 38, 40), 5, 3.2, 0.04, 28, dash=4.6, rehit=6,
                                 anim="dash", announce="Barrel Roll"),
            "special_up": Move("scale up", 8, 10, 15, (-14, -72, 32, 54), 10, 4.2, 0.065, 82, rise=9.2,
                               once_per_air=True, anim="rise", announce="Scale Up"),
            "special_down": Move("volume snapshot", 10, 1, 24, anim="buff", announce="Snapshot",
                                 buff=(BUFF_ARMOR, 200)),
        }))


def kubectl() -> FighterStats:
    """Fast technical fighter: command-line combos."""
    return FighterStats(
        "Kubectl", (110, 235, 170), weight=92, run_speed=3.9, air_speed=3.38, air_accel=0.34,
        blurb="Fast and technical. Fires commands.",
        moves=moveset(**{
            "jab": Move("rapid ping", 2, 7, 6, (6, -33, 24, 12), 1.6, 1.8, 0.01, 36, rehit=3, anim="jab"),
            "side": Move("curl", 7, 3, 14, (6, -35, 52, 10), 7, 3.2, 0.05, 20, anim="side"),
            "up": Move("pipe", 5, 6, 13, (-8, -80, 20, 48), 6, 3.4, 0.05, 80, anim="up"),
            "down": Move("rm -rf", 9, 4, 18, (6, -12, 36, 12), 8, 3.0, 0.045, 58, anim="down"),
            "special": Move("get pods", 11, 1, 20, anim="cast", announce="kubectl get pods", projectile=ProjectileDef(
                speed=5.2, width=9, height=7, damage=4, base_kb=2.2, kb_growth=0.025, angle=28, count=3,
                spread=22, color=(130, 255, 190), shape="bolt")),
            "special_side": Move("exec", 5, 9, 14, (2, -36, 22, 22), 8, 3.6, 0.055, 30, dash=6.0,
                                 anim="dash", announce="kubectl exec"),
            "special_up": Move("port-forward", 6, 8, 14, (-8, -64, 20, 36), 6, 3.2, 0.05, 85, rise=10.8,
                               once_per_air=True, anim="rise", announce="port-forward"),
            "special_down": Move("watch", 8, 1, 16, anim="buff", announce="--watch", buff=(BUFF_HASTE, 240)),
        }))


def cronjob() -> FighterStats:
    """CronJob: light and slippery, with scheduled trap-laying."""
    return FighterStats(
        "CronJob", (240, 170, 60), weight=84, width=22, height=42, run_speed=3.9, air_speed=3.51,
        jump_vel=-9.4, gravity=0.37, air_jumps=4, blurb="Light trickster. Sets timed traps.",
        moves=moveset(**{
            "jab": Move("tick", 2, 2, 7, (6, -34, 22, 14), 3, 2.0, 0.018, 55, anim="jab"),
            "side": Move("alarm bonk", 9, 5, 17, (8, -44, 30, 30), 11, 4.4, 0.07, 40, lunge=2.4, anim="side"),
            "up": Move("snooze kick", 4, 6, 12, (-14, -74, 36, 38), 6, 3.0, 0.045, 75, anim="up"),
            "down": Move("clockwork spin", 6, 12, 13, (-27, -24, 58, 26), 2.5, 2.1, 0.014, 80, rehit=5, anim="down"),
            "special": Move("scheduled job", 9, 1, 16, anim="cast", announce="Scheduled Job", projectile=ProjectileDef(
                speed=3.2, width=12, height=10, damage=7, base_kb=3.0, kb_growth=0.035, angle=60, life=420,
                gravity=0.16, vy=-3.2, color=(255, 225, 80), shape="clock", stick=True,
                replace_existing=True)),
            "special_side": Move("next run", 7, 6, 12, (6, -34, 26, 22), 6, 3.4, 0.05, 40, blink=70,
                                 anim="dash", announce="Next Run"),
            "special_up": Move("snooze", 5, 8, 12, (-10, -62, 22, 40), 6, 3.0, 0.05, 82, rise=10.1,
                               once_per_air=True, anim="rise", announce="Snooze"),
            "special_down": Move("gravity well", 14, 1, 22, anim="cast", announce="Gravity Well", projectile=ProjectileDef(
                speed=0, width=30, height=30, damage=2.0, base_kb=1.2, kb_growth=0.0, angle=80, life=180, gravity=0.0,
                spawn_dx=46, spawn_dy=-38, color=(190, 150, 255), shape="well", pierce=True, hit_interval=30,
                explode_radius=72, explode_damage=11, pull=0.52, pull_radius=108, replace_existing=True)),
        }))


def sidecar() -> FighterStats:
    """Support fighter fighting alongside an orbiting drone."""
    return FighterStats(
        "Sidecar", (190, 140, 255), weight=96, blurb="Fights with an orbiting drone.",
        moves=moveset(**{
            "jab": Move("drone poke", 4, 1, 13, anim="cast", projectile=ProjectileDef(
                speed=6.0, width=14, height=10, damage=2.5, base_kb=2.0, kb_growth=0.018, angle=35, life=7, spawn_dx=12, spawn_dy=-32,
                color=(210, 170, 255), shape="orb")),
            "side": Move("hover slam", 8, 5, 15, (4, -32, 34, 24), 8, 3.4, 0.05, 20, lunge=2.6, anim="side"),
            "up": Move("rotor lift", 5, 12, 12, (-8, -72, 26, 42), 2, 2.0, 0.01, 88, rehit=4, anim="up"),
            "down": Move("scrap", 6, 4, 13, (-4, -11, 46, 11), 5, 2.8, 0.035, 68, anim="down"),
            "special": Move("deploy", 12, 1, 18, anim="cast", announce="Deploy Sidecar", projectile=ProjectileDef(
                speed=0, width=12, height=12, damage=3, base_kb=2.2, kb_growth=0.02, angle=45, life=420,
                color=(190, 140, 255), shape="drone", orbit=True, hit_interval=24, replace_existing=True)),
            "special_side": Move("injected", 10, 1, 18, anim="cast", announce="Sidecar Shot", projectile=ProjectileDef(
                speed=7.0, width=18, height=14, damage=8, base_kb=3.4, kb_growth=0.05, angle=30, life=62, wave=1.7,
                pierce=True, hit_interval=999, color=(220, 180, 255), shape="spark")),
            "special_up": Move("hover boost", 6, 9, 16, (-10, -60, 22, 38), 5, 3.0, 0.04, 85, rise=9.9,
                               once_per_air=True, anim="rise", announce="Hover Boost"),
            "special_down": Move("shield drone", 10, 1, 18, anim="buff", announce="Mesh Shield",
                                 buff=(BUFF_ARMOR, 180)),
        }))


def ingress() -> FighterStats:
    """Gatekeeper: zoning with ports, routes and a firewall wall."""
    return FighterStats(
        "Ingress", (90, 215, 220), weight=108, run_speed=3.12, width=26, height=48,
        blurb="Gatekeeper. Ports and walls.",
        moves=moveset(**{
            "jab": Move("shield jab", 4, 3, 11, (8, -36, 22, 22), 4, 2.4, 0.02, 30, anim="jab"),
            "side": Move("gate slam", 13, 5, 22, (6, -48, 40, 44), 13, 4.6, 0.07, 28, lunge=1.0, anim="side"),
            "up": Move("portcullis", 8, 8, 16, (-6, -86, 32, 52), 9, 3.8, 0.06, 82, anim="up"),
            "down": Move("stomp", 8, 5, 18, (-30, -12, 66, 12), 8, 3.2, 0.05, 65, anim="down"),
            "special": Move("open port", 14, 1, 20, anim="cast", announce="Open Port", projectile=ProjectileDef(
                speed=2.6, width=26, height=26, damage=9, base_kb=3.4, kb_growth=0.05, angle=35, life=110,
                pierce=True, hit_interval=999, color=(90, 215, 220), shape="ring")),
            "special_side": Move("route", 8, 6, 14, (6, -40, 28, 30), 8, 3.6, 0.055, 35, blink=64,
                                 anim="dash", announce="Route"),
            "special_up": Move("gateway", 8, 10, 16, (-12, -66, 26, 44), 8, 3.6, 0.06, 80, rise=9.2,
                               once_per_air=True, anim="rise", announce="Gateway"),
            "special_down": Move("firewall", 14, 1, 24, anim="cast", announce="Firewall", projectile=ProjectileDef(
                speed=0, width=10, height=46, damage=4, base_kb=3.0, kb_growth=0.03, angle=75, life=200,
                gravity=0.3, spawn_dx=40, spawn_dy=-30, color=(255, 120, 70), shape="wall", stick=True,
                pierce=True, hit_interval=24, replace_existing=True)),
        }))


def operator() -> FighterStats:
    """Counter-puncher that reconciles state back to what it wants."""
    return FighterStats(
        "Operator", (255, 150, 190), weight=98, blurb="Counter-puncher. Self-heals.",
        moves=moveset(**{
            "jab": Move("patch lash", 4, 3, 9, (6, -35, 42, 8), 3, 2.0, 0.016, 20, anim="jab"),
            "side": Move("switch flip", 7, 5, 14, (6, -38, 30, 24), 8, 3.6, 0.055, 40, lunge=1.8, anim="side"),
            "up": Move("headset swing", 5, 6, 13, (-16, -78, 40, 36), 7, 3.3, 0.05, 75, anim="up"),
            "down": Move("heel stab", 6, 3, 13, (8, -12, 32, 12), 6, 2.6, 0.04, 50, anim="down"),
            "special": Move("reconcile", 4, 26, 20, (0, 0, 0, 0), 12, 4.6, 0.07, 40, counter=True,
                            anim="counter", announce="Reconcile"),
            "special_side": Move("watch loop", 11, 1, 18, anim="cast", announce="Watch Loop", projectile=ProjectileDef(
                speed=4.4, width=14, height=14, damage=4, base_kb=2.4, kb_growth=0.03, angle=40, life=70,
                color=(255, 170, 205), shape="wheel", boomerang=True, pierce=True, hit_interval=28)),
            "special_up": Move("reschedule", 6, 8, 14, (-10, -62, 22, 40), 6, 3.2, 0.05, 82, rise=9.9,
                               once_per_air=True, anim="rise", announce="Reschedule"),
            "special_down": Move("self-heal", 18, 1, 20, anim="buff", announce="Self-Heal", heal=14),
        }))


def oomkiller() -> FighterStats:
    """A lanky, floaty reaper: fast on its feet, wildly hard-hitting, and full of odd tricks."""
    return FighterStats(
        "OOMKiller", (205, 60, 70), weight=100, run_speed=3.7, air_speed=3.3, jump_vel=-9.0, gravity=0.37, width=26, height=54,
        air_jumps=3, blurb="Floaty reaper. Fast, spooky and fun.",
        moves=moveset(**{
            "jab": Move("claw rake", 3, 3, 9, (8, -38, 30, 18), 3.5, 2.4, 0.02, 40, anim="jab"),
            "side": Move("scythe swing", 10, 6, 17, (4, -56, 58, 52), 12, 4.6, 0.08, 30, lunge=1.6, anim="side"),
            "up": Move("reaper's lift", 7, 7, 15, (-16, -94, 42, 62), 10, 4.2, 0.07, 84, anim="up"),
            "down": Move("grave dig", 9, 5, 17, (-38, -16, 78, 16), 9, 3.6, 0.06, 60, anim="down"),
            "special": Move("zombie process", 12, 1, 18, anim="cast", announce="Zombie Process", projectile=ProjectileDef(
                speed=3.4, width=20, height=16, damage=7, base_kb=3.2, kb_growth=0.05, angle=34, life=110, count=2, spread=26,
                wave=1.2, color=(235, 70, 80), shape="skull")),
            "special_side": Move("segfault", 8, 7, 16, (6, -48, 38, 40), 10, 4.2, 0.07, 30, blink=90,
                                 anim="dash", announce="Segfault"),
            "special_up": Move("memory leak", 7, 12, 17, (-14, -80, 34, 58), 3, 2.6, 0.02, 84, rise=9.4, rehit=4,
                               once_per_air=True, anim="rise", announce="Memory Leak"),
            "special_down": Move("fork bomb", 14, 5, 22, (-62, -62, 124, 62), 11, 4.4, 0.075, 70,
                                 anim="down", announce="Fork Bomb"),
        }))


def roster() -> list[FighterStats]:
    return [pod(), statefulset(), kubectl(), cronjob(), sidecar(), ingress(), operator(), oomkiller()]
