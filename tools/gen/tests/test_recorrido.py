"""_comun/recorrido.py: recorrido estricto, sin vuelta, flotantes, luz y superficie dañada."""
from unicas._comun import recorrido as rc
from core import Template


def suelo(n=5, y=0, st="minecraft:stone"):
    return {(x, y, z): st for x in range(n) for z in range(n)}


def test_vista_suelo_virtual_y_aire():
    v = rc.Vista({(0, 0, 0): "minecraft:air", (1, 0, 0): "minecraft:stone"}, resuelto={(2, 0, 0): "dirt"}, suelo_y=-1)
    assert v.get(0, 0, 0) is None and v.get(1, 0, 0) == "minecraft:stone"
    assert v.get(2, 0, 0) == "minecraft:dirt" and v.get(9, -1, 9) == "minecraft:grass_block"


def test_andar_llano():
    v = rc.Vista(suelo())
    seen, edges = rc.andar(v, (0, 1, 0), (0, 4, 0, 4))
    assert len(seen) == 25 and rc.sin_vuelta(edges, (0, 1, 0)) == []


def test_andar_no_sube_un_bloque_entero_y_si_un_peldano():
    b = suelo()
    b[(2, 1, 0)] = "minecraft:stone"                      # escalón de un bloque: no se salta
    v = rc.Vista(b)
    seen, _ = rc.andar(v, (0, 1, 0), (0, 2, 0, 0))
    assert (2, 2, 0) not in seen
    b[(1, 1, 0)] = "minecraft:oak_stairs[facing=east,half=bottom]"     # con un peldaño delante, sí
    seen, _ = rc.andar(rc.Vista(b), (0, 1, 0), (0, 2, 0, 0))
    assert (2, 2, 0) in seen


def test_caida_sin_vuelta():
    b = {(x, 3, 0): "minecraft:stone" for x in range(2)}
    b.update({(x, 0, 0): "minecraft:stone" for x in range(2, 5)})     # bajar 3 bloques: en el estricto no se baja
    seen, _ = rc.andar(rc.Vista(b), (0, 4, 0), (0, 4, 0, 0))
    assert (2, 1, 0) not in seen
    b[(2, 2, 0)] = "minecraft:stone"                       # bajar 1 (a y=3) y luego 2 hasta el suelo: tampoco
    b.update({(x, 1, 0): "minecraft:stone" for x in (3,)})
    seen, edges = rc.andar(rc.Vista(b), (0, 4, 0), (0, 4, 0, 0))
    # bajada de un bloque permitida; desde (2,3) a (3,2) también; la vuelta (3,2)->(2,3) sube 1: no
    assert (3, 2, 0) in seen and (3, 2, 0) in rc.sin_vuelta(edges, (0, 4, 0))


def test_escalera_de_mano():
    b = suelo(3)
    for y in range(1, 5):
        b[(0, y, 1)] = "minecraft:stone"
        b[(1, y, 1)] = "minecraft:ladder[facing=east]"
    b.update({(x, 4, z): "minecraft:stone" for x in range(2, 4) for z in range(3)})
    b[(1, 4, 1)] = "minecraft:ladder[facing=east]"
    seen, edges = rc.andar(rc.Vista(b), (2, 1, 1), (0, 3, 0, 2))
    assert (1, 4, 1) in seen and rc.sin_vuelta(edges, (2, 1, 1)) == []


def test_nadar():
    b = {(x, 0, 0): "minecraft:stone" for x in range(4)}
    b.update({(x, y, 0): "minecraft:water" for x in (1, 2) for y in (1, 2)})
    b.update({(x, 0, 0): "minecraft:stone" for x in (1, 2)})
    b[(3, 1, 0)] = "minecraft:stone"
    b[(3, 2, 0)] = "minecraft:stone"
    seen, _ = rc.andar(rc.Vista(b), (0, 1, 0), (0, 3, 0, 0), agua=True)
    assert (3, 3, 0) in seen                               # se sale del agua subiendo
    seen, _ = rc.andar(rc.Vista(b), (0, 1, 0), (0, 3, 0, 0))
    assert (3, 3, 0) not in seen


def test_flotantes_y_cerca():
    b = {(0, 0, 0): "minecraft:stone", (0, 1, 0): "minecraft:stone", (5, 5, 5): "minecraft:stone",
         (6, 5, 5): "minecraft:air"}
    assert rc.flotantes(b, {0}) == [(5, 5, 5)]
    assert rc.cerca({(0, 0, 0)}, (1, 1, 0)) and not rc.cerca({(0, 0, 0)}, (2, 0, 0))


def test_luz_y_generador():
    b = {(x, 0, 0): "minecraft:air" for x in range(20)}
    b[(0, 0, 0)] = "minecraft:lantern[hanging=false]"
    b[(10, 0, 0)] = "minecraft:stone"                       # un bloque macizo corta la luz
    lv = rc.luz(b)
    assert lv[(0, 0, 0)] == 15 and lv[(5, 0, 0)] == 10 and (11, 0, 0) not in lv
    assert rc.luz_generador(lv, (9, 0, 0), rango=1) == 7
    assert rc.luz({(0, 0, 0): "minecraft:redstone_torch[lit=false]"}) == {}


def test_shifted_y_walk_con_sotano():
    t = Template("s")
    for x in range(3):
        t.set(x, -3, 0, "stone")
    t.jigsaw(0, -2, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty")
    s = rc.shifted(t)
    assert (0, -3 + rc.DY, 0) in s.blocks and s.jigsaws[0]["pos"] == (0, -2 + rc.DY, 0)
    assert {(1, -2, 0), (2, -2, 0)} <= rc.walk(t)


def test_reglas_y_esperanza():
    decay = [("stone_bricks", 0.2, "cracked_stone_bricks"), ("stone_bricks", 0.5, "mossy_stone_bricks")]
    p = rc.procesador(decay)
    assert p["rules"][0]["output_state"] == "minecraft:cracked_stone_bricks"          # cadena, no {"Name": ...}
    assert abs(rc.esperanza("minecraft:stone_bricks", decay) - (0.2 + 0.8 * 0.5)) < 1e-9
    assert rc.esperanza("minecraft:dirt", decay) == 0


def test_superficie_danada():
    b = {(x, y, z): "minecraft:stone_bricks" for x in range(3) for y in range(2) for z in range(3)}
    surf, frac = rc.superficie_danada(b, set(), [("stone_bricks", 0.1, "cracked_stone_bricks")], (-1, 3, -1, 3))
    assert surf == 17 and abs(frac - 0.1) < 1e-9          # el centro de la capa baja no se ve
    surf, frac = rc.superficie_danada(b, {(1, 1, 1)}, [], (-1, 3, -1, 3))
    assert frac == 1 / 17


def test_vista_lint_y_abrir():
    v = rc.vista_lint({(0, 0, 0): ("minecraft:stone", None)}, {(0, 0, 0): None, (1, 0, 0): "minecraft:dirt"})
    assert v.get(0, 0, 0) is None or v.get(0, 0, 0).startswith("minecraft:jigsaw")
    assert v.get(1, 0, 0) == "minecraft:dirt" and v.jigsaws[0]["name"] == "heraldia:entrance"
