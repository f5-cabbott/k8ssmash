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
        "Pod", (70, 150, 255), blurb="Balanced. Does a bit of everything.",
        moves=moveset(**{
            "special": Move("apply", 10, 1, 18, anim="cast", announce="kubectl apply", projectile=ProjectileDef(
                speed=4.8, width=12, height=9, damage=5, base_kb=2.6, kb_growth=0.03, angle=30,
                color=(130, 205, 255), shape="bolt")),
            "special_side": Move("rolling update", 9, 14, 16, (4, -38, 24, 32), 9, 4.0, 0.06, 35, dash=4.4,
                                 anim="dash", announce="Rolling Update"),
            "special_up": Move("restart", 7, 8, 14, (-10, -62, 24, 40), 8, 3.8, 0.06, 80, rise=8.6,
                               once_per_air=True, anim="rise", announce="Restart"),
            "special_down": Move("replica", 12, 1, 18, anim="cast", announce="Replica!", projectile=ProjectileDef(
                speed=0, width=14, height=14, damage=0, base_kb=0, kb_growth=0, angle=0, life=100,
                gravity=0.3, spawn_dx=18, spawn_dy=-8, color=(70, 150, 255), shape="bomb", stick=True,
                explode_radius=40, explode_damage=10, replace_existing=True)),
        }))


def helm() -> FighterStats:
    """Heavy captain. Slow, hits like a tugboat, wheel boomerang."""
    return FighterStats(
        "Helm", (232, 190, 70), weight=122, run_speed=2.2, air_speed=2.0, jump_vel=-7.2, djump_vel=-6.6,
        gravity=0.4, width=28, height=50, blurb="Heavy captain. Slow, but every hit is a broadside.",
        moves=moveset(**{
            "jab": Move("jab", 4, 3, 11, (8, -34, 26, 16), 4, 2.4, 0.02, 35, anim="jab"),
            "side": Move("side", 11, 4, 20, (8, -40, 38, 22), 12, 4.4, 0.07, 30, lunge=1.2, anim="side"),
            "special": Move("helm install", 14, 1, 20, anim="cast", announce="helm install", projectile=ProjectileDef(
                speed=4.0, width=20, height=20, damage=7, base_kb=3.0, kb_growth=0.04, angle=40, life=80,
                spawn_dy=-26, color=(232, 190, 70), shape="wheel", boomerang=True, pierce=True,
                hit_interval=30)),
            "special_side": Move("chart charge", 14, 16, 22, (6, -42, 32, 38), 13, 4.6, 0.075, 30, dash=3.2,
                                 anim="dash", announce="Chart Charge"),
            "special_up": Move("anchors aweigh", 10, 10, 16, (-14, -70, 30, 52), 10, 4.2, 0.065, 82, rise=7.2,
                               once_per_air=True, anim="rise", announce="Anchors Aweigh"),
            "special_down": Move("release lock", 16, 5, 22, (-40, -26, 80, 26), 12, 4.0, 0.07, 55,
                                 anim="down", announce="Release Lock"),
        }))


def kubectl() -> FighterStats:
    """Fast technical fighter: command-line combos."""
    return FighterStats(
        "Kubectl", (110, 235, 170), weight=92, run_speed=3.0, air_speed=2.6, air_accel=0.26,
        blurb="Fast and technical. Fires off commands.",
        moves=moveset(**{
            "jab": Move("jab", 2, 3, 7, (6, -32, 22, 14), 2.5, 2.0, 0.015, 38, anim="jab"),
            "special": Move("get pods", 11, 1, 20, anim="cast", announce="kubectl get pods", projectile=ProjectileDef(
                speed=5.2, width=9, height=7, damage=3, base_kb=2.0, kb_growth=0.02, angle=28, count=3,
                spread=22, color=(130, 255, 190), shape="bolt")),
            "special_side": Move("exec", 5, 9, 14, (2, -36, 22, 22), 7, 3.4, 0.05, 30, dash=6.0,
                                 anim="dash", announce="kubectl exec"),
            "special_up": Move("port-forward", 6, 8, 14, (-8, -64, 20, 36), 6, 3.2, 0.05, 85, rise=9.6,
                               once_per_air=True, anim="rise", announce="port-forward"),
            "special_down": Move("watch", 8, 1, 16, anim="buff", announce="--watch", buff=(BUFF_HASTE, 240)),
        }))


def monkey() -> FighterStats:
    """Chaos Monkey: light and slippery, with trap-laying."""
    return FighterStats(
        "Chaos Monkey", (230, 130, 70), weight=84, width=22, height=42, run_speed=3.0, air_speed=2.7,
        jump_vel=-8.0, djump_vel=-7.6, gravity=0.37, blurb="Light and slippery. Leaves traps everywhere.",
        moves=moveset(**{
            "special": Move("banana toss", 9, 1, 16, anim="cast", announce="Banana Toss", projectile=ProjectileDef(
                speed=3.2, width=12, height=10, damage=6, base_kb=2.8, kb_growth=0.03, angle=60, life=420,
                gravity=0.16, vy=-3.2, color=(255, 225, 80), shape="banana", stick=True,
                replace_existing=True)),
            "special_side": Move("vine swing", 7, 6, 12, (6, -34, 26, 22), 6, 3.4, 0.05, 40, blink=70,
                                 anim="dash", announce="Vine Swing"),
            "special_up": Move("tree hop", 5, 8, 12, (-10, -62, 22, 40), 6, 3.0, 0.05, 82, rise=9.0,
                               once_per_air=True, anim="rise", announce="Tree Hop"),
            "special_down": Move("chaos!", 14, 1, 22, anim="cast", announce="CHAOS!", projectile=ProjectileDef(
                speed=0, width=14, height=14, damage=0, base_kb=0, kb_growth=0, angle=0, life=70,
                gravity=0.3, spawn_dx=16, spawn_dy=-8, color=(240, 90, 60), shape="bomb", stick=True,
                explode_radius=54, explode_damage=14, harmless_to_owner=False, replace_existing=True)),
        }))


def sidecar() -> FighterStats:
    """Support fighter fighting alongside an orbiting drone."""
    return FighterStats(
        "Sidecar", (190, 140, 255), weight=96, blurb="Fights alongside an orbiting drone buddy.",
        moves=moveset(**{
            "special": Move("deploy", 12, 1, 18, anim="cast", announce="Deploy Sidecar", projectile=ProjectileDef(
                speed=0, width=12, height=12, damage=3, base_kb=2.2, kb_growth=0.02, angle=45, life=420,
                color=(190, 140, 255), shape="drone", orbit=True, hit_interval=24, replace_existing=True)),
            "special_side": Move("injected", 10, 1, 18, anim="cast", announce="Sidecar Shot", projectile=ProjectileDef(
                speed=6.2, width=14, height=8, damage=8, base_kb=3.4, kb_growth=0.05, angle=30, life=70,
                pierce=True, hit_interval=999, color=(220, 180, 255), shape="bolt")),
            "special_up": Move("hover boost", 6, 9, 16, (-10, -60, 22, 38), 5, 3.0, 0.04, 85, rise=8.8,
                               once_per_air=True, anim="rise", announce="Hover Boost"),
            "special_down": Move("shield drone", 10, 1, 18, anim="buff", announce="Mesh Shield",
                                 buff=(BUFF_ARMOR, 180)),
        }))


def ingress() -> FighterStats:
    """Gatekeeper: zoning with ports, routes and a firewall wall."""
    return FighterStats(
        "Ingress", (90, 215, 220), weight=108, run_speed=2.4, width=26, height=48,
        blurb="Gatekeeper. Controls space with ports and walls.",
        moves=moveset(**{
            "special": Move("open port", 14, 1, 20, anim="cast", announce="Open Port", projectile=ProjectileDef(
                speed=2.6, width=26, height=26, damage=9, base_kb=3.4, kb_growth=0.05, angle=35, life=110,
                pierce=True, hit_interval=999, color=(90, 215, 220), shape="ring")),
            "special_side": Move("route", 8, 6, 14, (6, -40, 28, 30), 8, 3.6, 0.055, 35, blink=64,
                                 anim="dash", announce="Route"),
            "special_up": Move("gateway", 8, 10, 16, (-12, -66, 26, 44), 8, 3.6, 0.06, 80, rise=8.2,
                               once_per_air=True, anim="rise", announce="Gateway"),
            "special_down": Move("firewall", 14, 1, 24, anim="cast", announce="Firewall", projectile=ProjectileDef(
                speed=0, width=10, height=46, damage=4, base_kb=3.0, kb_growth=0.03, angle=75, life=200,
                gravity=0.3, spawn_dx=40, spawn_dy=-30, color=(255, 120, 70), shape="wall", stick=True,
                pierce=True, hit_interval=24, replace_existing=True)),
        }))


def operator() -> FighterStats:
    """Counter-puncher that reconciles state back to what it wants."""
    return FighterStats(
        "Operator", (255, 150, 190), weight=98, blurb="Counter-puncher. Punishes mistakes and self-heals.",
        moves=moveset(**{
            "special": Move("reconcile", 4, 26, 20, (0, 0, 0, 0), 12, 4.6, 0.07, 40, counter=True,
                            anim="counter", announce="Reconcile"),
            "special_side": Move("watch loop", 11, 1, 18, anim="cast", announce="Watch Loop", projectile=ProjectileDef(
                speed=4.4, width=14, height=14, damage=4, base_kb=2.4, kb_growth=0.03, angle=40, life=70,
                color=(255, 170, 205), shape="wheel", boomerang=True, pierce=True, hit_interval=28)),
            "special_up": Move("reschedule", 6, 8, 14, (-10, -62, 22, 40), 6, 3.2, 0.05, 82, rise=8.8,
                               once_per_air=True, anim="rise", announce="Reschedule"),
            "special_down": Move("self-heal", 18, 1, 20, anim="buff", announce="Self-Heal", heal=14),
        }))


def oomkiller() -> FighterStats:
    """Heavy glass cannon. Huge damage, short reach, big recoveries."""
    return FighterStats(
        "OOMKiller", (205, 60, 70), weight=116, run_speed=2.3, width=28, height=50, jump_vel=-7.0,
        blurb="Glass cannon. Everything it touches gets OOMKilled.",
        moves=moveset(**{
            "jab": Move("jab", 5, 3, 12, (8, -36, 28, 16), 4, 2.6, 0.022, 38, anim="jab"),
            "side": Move("side", 12, 4, 22, (8, -42, 40, 24), 13, 4.8, 0.08, 30, lunge=1.3, anim="side"),
            "special": Move("sigkill", 18, 1, 26, anim="cast", announce="SIGKILL", projectile=ProjectileDef(
                speed=3.0, width=22, height=16, damage=14, base_kb=4.2, kb_growth=0.07, angle=28, life=90,
                color=(235, 70, 80), shape="skull")),
            "special_side": Move("reap", 14, 14, 26, (4, -44, 40, 40), 15, 5.0, 0.085, 28, dash=3.0,
                                 anim="dash", announce="Reap"),
            "special_up": Move("memory leak", 10, 10, 20, (-14, -72, 32, 56), 11, 4.4, 0.07, 82, rise=7.0,
                               once_per_air=True, anim="rise", announce="Memory Leak"),
            "special_down": Move("oom!", 20, 6, 26, (-46, -40, 92, 40), 14, 4.8, 0.08, 50,
                                 anim="down", announce="OOM!"),
        }))


def roster() -> list[FighterStats]:
    return [pod(), helm(), kubectl(), monkey(), sidecar(), ingress(), operator(), oomkiller()]
