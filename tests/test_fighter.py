import pygame
import pytest

from k8ssmash.config import CANVAS_W
from k8ssmash.fighter import Fighter, FighterStats
from k8ssmash.input import PlayerInput
from k8ssmash.render import integer_scale
from k8ssmash.stage import datacenter_stage


@pytest.fixture
def stage():
    return datacenter_stage()


def make(stage, slot=0):
    f = Fighter(FighterStats("T", (255, 255, 255)), slot)
    f.spawn(stage.spawns[slot], 1)
    return f


def tick(f, stage, held=(), frames=1):
    inp = f._test_inp = getattr(f, "_test_inp", PlayerInput())
    for _ in range(frames):
        inp.update(set(held))
        f.update(inp, stage)


def test_lands_on_platform(stage):
    f = make(stage)
    f.y -= 60
    tick(f, stage, frames=60)
    assert f.on_ground and f.y == stage.platforms[0].top


def test_double_jump_exactly_two_jumps(stage):
    f = make(stage)
    tick(f, stage, frames=2)
    tick(f, stage, {"JUMP"})
    assert f.vy < 0 and f.aerial_jumps == 1
    tick(f, stage, frames=3)
    tick(f, stage, {"JUMP"})
    assert f.aerial_jumps == 0
    vy_after_double = f.vy
    tick(f, stage, frames=2)
    tick(f, stage, {"JUMP"})  # third jump must do nothing
    assert f.vy >= vy_after_double  # only gravity acted
    tick(f, stage, frames=200)
    assert f.on_ground and f.aerial_jumps == 1


def test_walk_off_ledge_keeps_one_air_jump(stage):
    f = make(stage)
    f.x = stage.platforms[0].rect.right + 20
    f.on_ground = False
    f.y = stage.platforms[0].top
    tick(f, stage, frames=3)
    assert not f.on_ground and f.aerial_jumps == 1


def test_dropthrough_platform(stage):
    f = make(stage)
    thin = stage.platforms[1]
    f.x, f.y = thin.rect.centerx, thin.top
    tick(f, stage, frames=2)
    assert f.on_ground
    tick(f, stage, {"DOWN"}, frames=20)
    assert f.y > thin.top


def test_knockback_scales_with_percent(stage):
    a, b = make(stage), make(stage, 1)
    a.apply_hit(5, 3.0, 0.05, 40, 1)
    low = a.vx
    b.percent = 150
    b.apply_hit(5, 3.0, 0.05, 40, 1)
    assert b.vx > low > 0 and b.vy < 0 and b.hitstun > a.hitstun


def test_heavier_fighter_flies_less(stage):
    light, heavy = make(stage), make(stage, 1)
    heavy.stats.weight = 130
    light.apply_hit(8, 4, 0.05, 30, 1)
    heavy.apply_hit(8, 4, 0.05, 30, 1)
    assert heavy.vx < light.vx


def test_shield_blocks_damage_and_breaks(stage):
    f = make(stage)
    tick(f, stage, frames=2)
    tick(f, stage, {"SHIELD"})
    assert f.shielding
    assert f.apply_hit(10, 3, 0.05, 40, 1) == "shield" and f.percent == 0
    for _ in range(10):
        f.apply_hit(10, 3, 0.05, 40, 1)
    assert f.shield_break > 0 and f.hitstun > 0


def test_invulnerable_ignores_hits(stage):
    f = make(stage)
    f.invuln = 30
    assert f.apply_hit(10, 3, 0.05, 40, 1) == "ignored" and f.percent == 0


def test_attack_hitbox_active_only_in_window_and_flips(stage):
    f = make(stage)
    tick(f, stage, frames=2)
    tick(f, stage, {"ATTACK"})
    m = f.move
    assert m is not None and m.name == "jab" and f.active_hitbox() is None
    while f.move_frame < m.startup:
        tick(f, stage)
    box_r = f.active_hitbox()
    assert box_r is not None and box_r.left >= f.x
    f.facing = -1
    assert f.active_hitbox().right <= f.x


def test_ko_and_respawn_invulnerable(stage):
    f = make(stage)
    f.knock_out()
    assert f.stocks == 2 and not f.alive
    tick(f, stage, frames=60)
    assert f.alive and f.invuln > 0 and f.percent == 0


def test_last_stock_eliminates(stage):
    f = make(stage)
    f.stocks = 1
    f.knock_out()
    assert f.eliminated


def test_special_spawns_projectile(stage):
    f = make(stage)
    tick(f, stage, frames=2)
    tick(f, stage, {"SPECIAL"})
    tick(f, stage, frames=15)
    assert len(f.spawn_queue) == 1 and f.spawn_queue[0].vx > 0


@pytest.mark.parametrize("size,scale", [((1920, 1080), 3), ((2560, 1440), 4), ((1280, 720), 2), ((800, 600), 1)])
def test_integer_scale(size, scale):
    assert integer_scale(*size) == scale
    assert CANVAS_W * scale <= size[0]


def test_moving_platform_carries_rider():
    from k8ssmash.stage import node_pool_stage
    stage = node_pool_stage()
    mover = stage.platforms[2]
    f = Fighter(FighterStats("T", (255, 255, 255)), 0)
    f.spawn((mover.rect.centerx, mover.rect.top - 1), 1)
    for frame in range(1, 400):
        stage.tick(frame)
        tick(f, stage)
    assert f.on_ground and f.standing_on is mover and f.y == mover.rect.top
    assert abs(f.x - mover.rect.centerx) < 2  # still riding the platform


def test_all_stages_have_valid_spawns():
    from k8ssmash.stage import STAGES
    for make in STAGES:
        st = make()
        assert len(st.spawns) >= 2 and st.name
        for sx, sy in st.spawns:
            assert any(p.rect.left <= sx <= p.rect.right and p.rect.top == sy for p in st.platforms)


# --- ducking -----------------------------------------------------------------------------------
def test_hold_down_ducks_with_a_shorter_hurtbox_and_no_movement(stage):
    f = make(stage)
    tick(f, stage, frames=3)
    full = f.hurtbox.height
    tick(f, stage, {"DOWN", "RIGHT"}, frames=10)
    assert f.state == "duck" and f.ducking
    assert f.hurtbox.height < full * 0.7 and f.hurtbox.bottom == int(f.y)
    assert abs(f.vx) < 0.01  # ducking roots you in place
    assert f.facing == 1
    tick(f, stage, {"LEFT", "DOWN"}, frames=2)
    assert f.facing == -1  # but you can turn around


def test_release_down_stands_up(stage):
    f = make(stage)
    tick(f, stage, {"DOWN"}, frames=5)
    assert f.ducking
    tick(f, stage, frames=2)
    assert not f.ducking and f.state == "idle"


def test_holding_down_on_a_thin_platform_ducks_but_tapping_drops(stage):
    f = make(stage)
    thin = stage.platforms[1]
    f.x, f.y = thin.rect.centerx, thin.top
    tick(f, stage, frames=3)
    tick(f, stage, {"DOWN"}, frames=1)  # the press frame: drops through
    tick(f, stage, {"DOWN"}, frames=20)
    assert f.y > thin.top

    g = make(stage)
    g.x, g.y = thin.rect.centerx, thin.top
    g.on_ground = True
    g.standing_on = thin
    inp = PlayerInput()
    inp.update({"DOWN"})
    inp.pressed = set()  # already holding down before landing: no fresh press
    g.update(inp, stage)
    for _ in range(20):
        g.update(inp, stage)
    assert g.y == thin.top and g.ducking


def test_duck_dodges_chest_height_projectiles(stage):
    from k8ssmash.moves import ProjectileDef
    f = make(stage)
    tick(f, stage, {"DOWN"}, frames=3)
    d = ProjectileDef(speed=4, width=10, height=8, damage=5, base_kb=2, kb_growth=0.03, angle=30)
    rect = pygame.Rect(0, 0, d.width, d.height)
    rect.center = (int(f.x), int(f.y + d.spawn_dy))
    assert not rect.colliderect(f.hurtbox)
    g = make(stage)
    tick(g, stage, frames=3)
    assert rect.colliderect(g.hurtbox)  # standing up it connects


def test_can_jump_out_of_a_duck_and_attack_low(stage):
    f = make(stage)
    tick(f, stage, {"DOWN"}, frames=3)
    tick(f, stage, {"DOWN", "JUMP"})
    assert f.vy < 0
    g = make(stage)
    tick(g, stage, {"DOWN"}, frames=3)
    tick(g, stage, {"DOWN", "ATTACK"})
    assert g.move is not None and g.move.name == "down" and g.ducking


# --- jump height and off-stage recovery -------------------------------------------------------
def apex(f, stage, held):
    start = f.y
    tick(f, stage, held)
    top = f.y
    for _ in range(80):
        tick(f, stage)
        top = min(top, f.y)
    return start - top


def test_jumps_are_high_enough(stage):
    f = make(stage)
    tick(f, stage, frames=3)
    assert apex(f, stage, {"JUMP"}) >= 85  # about two body heights; it was ~70 px before the retune


def test_ledge_assist_pulls_you_onto_the_stage(stage):
    main = stage.platforms[0].rect
    f = make(stage)
    f.x, f.y = main.left - 8, main.top + 14  # just below and outside the left edge
    f.vy, f.on_ground = 1.0, False
    tick(f, stage, {"RIGHT"})
    assert f.on_ground and f.y == main.top and f.x > main.left


def test_ledge_assist_needs_you_to_push_toward_the_stage(stage):
    main = stage.platforms[0].rect
    f = make(stage)
    f.x, f.y = main.left - 8, main.top + 14
    f.vy, f.on_ground = 1.0, False
    tick(f, stage, {"LEFT"})
    assert not f.on_ground
    g = make(stage)
    g.x, g.y = main.right + 8, main.top + 14
    g.vy, g.on_ground = 1.0, False
    tick(g, stage, {"LEFT"})
    assert g.on_ground and g.x < main.right  # the same works on the right edge


def test_ledge_assist_ignores_deep_or_far_positions_and_thin_planks(stage):
    main = stage.platforms[0].rect
    deep = make(stage)
    deep.x, deep.y, deep.vy, deep.on_ground = main.left - 8, main.top + 90, 1.0, False
    tick(deep, stage, {"RIGHT"})
    assert not deep.on_ground
    far = make(stage)
    far.x, far.y, far.vy, far.on_ground = main.left - 70, main.top + 14, 1.0, False
    tick(far, stage, {"RIGHT"})
    assert not far.on_ground
    thin = stage.platforms[1].rect
    plank = make(stage)
    plank.x, plank.y, plank.vy, plank.on_ground = thin.left - 8, thin.top + 14, 1.0, False
    tick(plank, stage, {"RIGHT"})
    assert not plank.on_ground


def test_air_jump_launches_in_the_held_direction(stage):
    f = make(stage)
    f.y -= 150
    f.on_ground = False
    f.aerial_jumps = 1
    tick(f, stage, {"JUMP", "LEFT"})
    assert f.vx < -2 and f.vy < 0  # a double jump steered back toward the stage
