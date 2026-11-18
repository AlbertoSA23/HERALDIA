"""lint.py (auditoría genérica) con plantillas sintéticas pequeñas."""
import lint
from core import Template


def house(door=True, cofre_dentro=True):
    """Sala de 5 x 5 con muros, entrada al norte (jigsaw heraldia:entrance) y una puerta en el muro."""
    t = Template("x/houses/h")
    t.fill(0, 0, 0, 6, 0, 6, "stone")
    for y in (1, 2):
        for i in range(7):
            for p in ((i, 0), (i, 6), (0, i), (6, i)):
                t.set(p[0], y, p[1], "oak_planks")
    t.fill(0, 3, 0, 6, 3, 6, "oak_planks")
    if door:
        t.set(3, 1, 0, "oak_door[facing=south,half=lower,hinge=left,open=false,powered=false]")
        t.set(3, 2, 0, "oak_door[facing=south,half=upper,hinge=left,open=false,powered=false]")
    t.fill(3, 0, -2, 3, 0, -1, "stone")
    t.jigsaw(3, 0, -2, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="stone")
    if cofre_dentro:
        t.chest(1, 1, 5, "south", "heraldia:x")
    return t


def test_passable_and_heights():
    assert lint.passable(None) and lint.passable("minecraft:air") and lint.passable("minecraft:oak_door[half=lower]")
    assert not lint.passable("minecraft:stone") and not lint.passable("minecraft:oak_fence")
    assert lint.passable("minecraft:oak_trapdoor[open=true]") and not lint.passable("minecraft:oak_trapdoor[open=false]")
    assert not lint.passable("minecraft:stone_stairs")       # «stairs» contiene «air»: se compara el nombre exacto
    assert lint.top_height("minecraft:stone_slab[type=bottom]") == 0.5
    assert lint.top_height("minecraft:oak_stairs[half=bottom]") == 0.5 and lint.top_height("minecraft:oak_fence") == 1.5
    assert lint.top_height("minecraft:white_carpet") == 0.0 and lint.top_height("minecraft:air") is None
    assert lint.top_height("minecraft:lantern") == 1.5


def test_walk_and_access_correct_house():
    t = house()
    cells = lint.walk(t)
    assert (3, 1, 3) in cells and (1, 1, 4) in cells
    assert lint.access_issues(t) == []
    assert lint.support_issues(t) == []


def test_walled_up_door_leaves_no_access():
    t = house()
    t.set(3, 1, 1, "oak_planks")            # tabique justo detrás de la puerta
    t.set(3, 2, 1, "oak_planks")
    msgs = {m for m, _ in lint.access_issues(t)}
    assert "puerta sin salida o sin acceso" in msgs and "chest inaccesible" in msgs


def test_without_entrance_access_is_not_audited():
    t = Template("x")
    t.chest(0, 0, 0, "north", "heraldia:x")
    assert lint.access_issues(t) == []


def test_supports():
    t = Template("x/houses/h")
    t.fill(0, 0, 0, 4, 0, 0, "stone")
    t.set(0, 2, 0, "lantern[hanging=true]")              # colgado de nada
    t.set(1, 2, 0, "lantern[hanging=false]")             # de pie sobre aire
    t.set(2, 1, 0, "iron_chain[axis=y]")                 # cadena sin enganche
    t.set(3, 1, 0, "ladder[facing=north]")               # sin pared detrás
    t.set(4, 1, 0, "wheat[age=0]")                       # cultivo sobre piedra
    msgs = {m for m, _ in lint.support_issues(t)}
    assert {"farol colgante sin techo", "farol de pie sin apoyo", "cadena sin enganche",
            "escalera de mano sin pared detrás", "cultivo fuera de tierra labrada"} <= msgs


def test_jigsaw_overwritten():
    t = house()
    t.set(3, 0, -2, "stone")
    assert ("jigsaw sobrescrito", (3, 0, -2)) in lint.support_issues(t)


def test_walk_does_not_cross_a_solid_roof():
    # terraza encima de una sala cerrada: desde la terraza no se «cae» a la sala atravesando el techo
    t = Template("x")
    t.fill(0, 0, 0, 4, 0, 4, "stone")
    t.fill(0, 4, 0, 4, 4, 4, "stone")
    t.fill(0, 4, -1, 0, 4, -1, "stone")
    t.jigsaw(0, 4, -1, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="stone")
    cells = lint.walk(t)
    assert (2, 5, 2) in cells and (2, 1, 2) not in cells


def test_lint_open_and_lint_view():
    t = house()
    t.set(3, 1, 0, "oak_planks")
    t.set(3, 2, 0, "oak_planks")
    assert (3, 1, 3) not in lint.walk(t)
    t.lint_open = {(3, 1, 0): None, (3, 2, 0): None}
    assert (3, 1, 3) in lint.walk(t)


def test_door_hinge():
    assert lint.door_hinge("north", "west") == "right" and lint.door_hinge("north", "east") == "left"
    import pytest
    with pytest.raises(ValueError):
        lint.door_hinge("north", "south")


def test_staircase_with_roof_under():
    t = Template("x")
    t.fill(-1, -1, 0, 6, -1, 0, "stone")
    for i in range(3):
        t.set(i, i, 0, "oak_stairs[facing=east,half=bottom]")
    assert lint.stair_headroom_issues(t) == []
    t.set(1, 2, 0, "stone")
    assert ("escalera con techo bajo", (1, 1, 0)) in lint.stair_headroom_issues(t)


def test_roof_is_not_a_staircase():
    t = Template("x")
    for i in range(3):                         # peldaños apilados sobre peldaños: masa de un tejado
        for k in range(i + 1):
            t.set(i, k, 0, "oak_stairs[facing=east,half=bottom]")
    assert lint.stair_headroom_issues(t) == []


def test_lint_registry_and_summarize():
    class R:
        templates = {"t/houses/a": house(), "t/houses/b": house(door=True)}
    R.templates["t/houses/b"].set(3, 1, 1, "oak_planks")
    R.templates["t/houses/b"].set(3, 2, 1, "oak_planks")
    res = lint.lint_registry(R)
    assert list(res) == ["t/houses/b"]
    c, ex = lint.summarize(res)
    assert c[("houses/b", "puerta sin salida o sin acceso")] == 1
    assert lint.lint_registry(R, only=lambda n: n.endswith("/a")) == {}
    # sin_auditoria_generica: solo puertas dobles y escaleras
    R.templates["t/houses/b"].no_generic_audit = True
    assert lint.lint_registry(R) == {}
