"""_comun/recorrido.py: recorrido estricto, sin vuelta, flotantes, luz y superficie dañada."""
from uniques._common import walkthrough as rc
from core import Template


def floor(n=5, y=0, st="minecraft:stone"):
    return {(x, y, z): st for x in range(n) for z in range(n)}


def test_view_virtual_floor_and_air():
    v = rc.View({(0, 0, 0): "minecraft:air", (1, 0, 0): "minecraft:stone"}, resolved_map={(2, 0, 0): "dirt"}, floor_y=-1)
    assert v.get(0, 0, 0) is None and v.get(1, 0, 0) == "minecraft:stone"
    assert v.get(2, 0, 0) == "minecraft:dirt" and v.get(9, -1, 9) == "minecraft:grass_block"


def test_walk_flat():
    v = rc.View(floor())
    seen, edges = rc.strict_walk(v, (0, 1, 0), (0, 4, 0, 4))
    assert len(seen) == 25 and rc.no_return(edges, (0, 1, 0)) == []


def test_walk_no_climbs_a_block_whole_and_yes_a_step():
    b = floor()
    b[(2, 1, 0)] = "minecraft:stone"                      # escalón de un bloque: no se salta
    v = rc.View(b)
    seen, _ = rc.strict_walk(v, (0, 1, 0), (0, 2, 0, 0))
    assert (2, 2, 0) not in seen
    b[(1, 1, 0)] = "minecraft:oak_stairs[facing=east,half=bottom]"     # con un peldaño delante, sí
    seen, _ = rc.strict_walk(rc.View(b), (0, 1, 0), (0, 2, 0, 0))
    assert (2, 2, 0) in seen


def test_fall_without_return():
    b = {(x, 3, 0): "minecraft:stone" for x in range(2)}
    b.update({(x, 0, 0): "minecraft:stone" for x in range(2, 5)})     # bajar 3 bloques: en el estricto no se baja
    seen, _ = rc.strict_walk(rc.View(b), (0, 4, 0), (0, 4, 0, 0))
    assert (2, 1, 0) not in seen
    b[(2, 2, 0)] = "minecraft:stone"                       # bajar 1 (a y=3) y luego 2 hasta el suelo: tampoco
    b.update({(x, 1, 0): "minecraft:stone" for x in (3,)})
    seen, edges = rc.strict_walk(rc.View(b), (0, 4, 0), (0, 4, 0, 0))
    # bajada de un bloque permitida; desde (2,3) a (3,2) también; la vuelta (3,2)->(2,3) sube 1: no
    assert (3, 2, 0) in seen and (3, 2, 0) in rc.no_return(edges, (0, 4, 0))


def test_ladder():
    b = floor(3)
    for y in range(1, 5):
        b[(0, y, 1)] = "minecraft:stone"
        b[(1, y, 1)] = "minecraft:ladder[facing=east]"
    b.update({(x, 4, z): "minecraft:stone" for x in range(2, 4) for z in range(3)})
    b[(1, 4, 1)] = "minecraft:ladder[facing=east]"
    seen, edges = rc.strict_walk(rc.View(b), (2, 1, 1), (0, 3, 0, 2))
    assert (1, 4, 1) in seen and rc.no_return(edges, (2, 1, 1)) == []


def test_swim():
    b = {(x, 0, 0): "minecraft:stone" for x in range(4)}
    b.update({(x, y, 0): "minecraft:water" for x in (1, 2) for y in (1, 2)})
    b.update({(x, 0, 0): "minecraft:stone" for x in (1, 2)})
    b[(3, 1, 0)] = "minecraft:stone"
    b[(3, 2, 0)] = "minecraft:stone"
    seen, _ = rc.strict_walk(rc.View(b), (0, 1, 0), (0, 3, 0, 0), water=True)
    assert (3, 3, 0) in seen                               # se sale del agua subiendo
    seen, _ = rc.strict_walk(rc.View(b), (0, 1, 0), (0, 3, 0, 0))
    assert (3, 3, 0) not in seen


def test_floating_and_near():
    b = {(0, 0, 0): "minecraft:stone", (0, 1, 0): "minecraft:stone", (5, 5, 5): "minecraft:stone",
         (6, 5, 5): "minecraft:air"}
    assert rc.floating_blocks(b, {0}) == [(5, 5, 5)]
    assert rc.nearby_flag({(0, 0, 0)}, (1, 1, 0)) and not rc.nearby_flag({(0, 0, 0)}, (2, 0, 0))


def test_light_and_generator():
    b = {(x, 0, 0): "minecraft:air" for x in range(20)}
    b[(0, 0, 0)] = "minecraft:lantern[hanging=false]"
    b[(10, 0, 0)] = "minecraft:stone"                       # un bloque macizo corta la luz
    lv = rc.light(b)
    assert lv[(0, 0, 0)] == 15 and lv[(5, 0, 0)] == 10 and (11, 0, 0) not in lv
    assert rc.light_generator(lv, (9, 0, 0), span=1) == 7
    assert rc.light({(0, 0, 0): "minecraft:redstone_torch[lit=false]"}) == {}


def test_shifted_and_walk_with_basement():
    t = Template("s")
    for x in range(3):
        t.set(x, -3, 0, "stone")
    t.jigsaw(0, -2, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty")
    s = rc.shifted(t)
    assert (0, -3 + rc.DY, 0) in s.blocks and s.jigsaws[0]["pos"] == (0, -2 + rc.DY, 0)
    assert {(1, -2, 0), (2, -2, 0)} <= rc.walk(t)


def test_rules_and_expectation():
    decay = [("stone_bricks", 0.2, "cracked_stone_bricks"), ("stone_bricks", 0.5, "mossy_stone_bricks")]
    p = rc.processor(decay)
    assert p["rules"][0]["output_state"] == "minecraft:cracked_stone_bricks"          # cadena, no {"Name": ...}
    assert abs(rc.expectation("minecraft:stone_bricks", decay) - (0.2 + 0.8 * 0.5)) < 1e-9
    assert rc.expectation("minecraft:dirt", decay) == 0


def test_damaged_surface():
    b = {(x, y, z): "minecraft:stone_bricks" for x in range(3) for y in range(2) for z in range(3)}
    surf, frac = rc.damaged_surface(b, set(), [("stone_bricks", 0.1, "cracked_stone_bricks")], (-1, 3, -1, 3))
    assert surf == 17 and abs(frac - 0.1) < 1e-9          # el centro de la capa baja no se ve
    surf, frac = rc.damaged_surface(b, {(1, 1, 1)}, [], (-1, 3, -1, 3))
    assert frac == 1 / 17


def test_lint_view_and_open():
    v = rc.lint_view({(0, 0, 0): ("minecraft:stone", None)}, {(0, 0, 0): None, (1, 0, 0): "minecraft:dirt"})
    assert v.get(0, 0, 0) is None or v.get(0, 0, 0).startswith("minecraft:jigsaw")
    assert v.get(1, 0, 0) == "minecraft:dirt" and v.jigsaws[0]["name"] == "heraldia:entrance"
