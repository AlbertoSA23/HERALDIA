"""The Herald's House (herald_house.py): the template keeps what casa_heraldo.json promises, it fits the brief (128 x 128,
a bell, the job board reused, beds and workstations for 18 villagers, eight empty stalls, return barrels, an unlit
portal frame, gates on every side), the placement, residents and fire rules hold (and the placement rules fail on the
first town's layout), the generic audit passes and the sign lines fit; version 1's blueprint travels frozen."""
import pytest

import board
import herald_house as h
import lint


@pytest.fixture(scope="module")
def t():
    return h.construct()


def test_template_keeps_its_promises(t):
    assert h.errors(t) == []


def test_size_is_128_by_128(t):
    sx, sy, sz = t.size()
    assert (sx, sz) == (128, 128)
    assert h.dataset(t)["tamano"] == [sx, sy, sz]


def test_generic_audit(t):
    assert lint.template_issues(t) == []


def test_portal_is_not_lit(t):
    names = {h._name(st) for st, _ in t.blocks.values()}
    assert "nether_portal" not in names and "fire" not in names
    assert "obsidian" in names


def test_job_board_is_the_villages_one(t):
    b = board.piece(h.THEME, "x")
    lectern = next(st for st, nbt in b.blocks.values() if st.startswith("minecraft:lectern"))
    bx, by, bz = h.BOARD
    assert t.get(bx, by, bz) == lectern
    assert any(n.get("Tags") and board.TAG_CONSTABLE in n["Tags"] for *_, n in t.entities)


def test_every_villager_is_a_heraldia_villager_with_its_own_workstation(t):
    villagers = [n for *_, n in t.entities if n["id"] == "minecraft:villager" and board.TAG_CONSTABLE not in n["Tags"]]
    assert len(villagers) == len(t.villagers) == 18
    assert all("heraldia" in n["Tags"] for n in villagers)
    assert len(t.stations) == len(villagers)
    assert len({n["VillagerData"]["profession"] for n in villagers}) >= 12


def test_rules_hold(t):
    cells = h.walk_cells(t)
    assert h.placement_errors(t.blds, t, cells) == []
    assert h.resident_errors(t, cells) == []
    assert h.fire_errors(t) == []


# the first town's buildings (version 1, herald_house.py as first released): (name, x0, z0, x1, z1, door side, along)
V1 = [("posada", 24, 26, 42, 36, "south", 33), ("hostal", 54, 26, 70, 36, "south", 62),
      ("capilla", 60, 8, 74, 22, "south", 67), ("herreria", 24, 38, 34, 44, "east", 41),
      ("carniceria", 24, 52, 34, 58, "east", 55), ("biblioteca", 62, 38, 72, 44, "west", 41),
      ("cartografo", 62, 52, 72, 58, "west", 55), ("taller", 54, 64, 64, 72, "west", 68),
      ("oficina", 34, 82, 44, 92, "north", 39)]


def test_placement_rules_fail_on_the_first_towns_layout():
    """The regression: the inn's door opened one block from the smithy's north wall."""
    e = h.placement_errors([h.Bld(n, a, b, c, d, side, al, None) for n, a, b, c, d, side, al in V1])
    assert "casa_heraldo: the door of posada at 33 36 opens onto herreria 2 blocks out" in e
    assert "casa_heraldo: the door of posada at 33 36 faces the wall of herreria 2 blocks away" in e
    assert any(m.startswith("casa_heraldo: posada and herreria are") for m in e)
    assert h.placement_errors(h._buildings()) == []


def test_placement_rules_catch_a_door_facing_a_wall():
    a = h.Bld("a", 10, 10, 20, 20, "east", 15, None)
    assert h.placement_errors([a, h.Bld("b", 30, 10, 40, 20, "west", 15, None)]) == []
    e = h.placement_errors([a, h.Bld("b", 27, 30, 37, 40, "west", 35, None)])
    assert e == []           # not in front of the door
    e = h.placement_errors([a, h.Bld("b", 27, 12, 37, 18, "north", 30, None)])
    assert e == ["casa_heraldo: the door of a at 20 15 faces the wall of b 7 blocks away"]
    e = h.placement_errors([a, h.Bld("b", 23, 14, 30, 18, "north", 27, None)])
    assert any("are 2 blocks apart" in m for m in e) and any("opens onto b 3 blocks out" in m for m in e)


def test_fire_model_finds_flammables_in_the_open(t):
    u = h.construct()
    u.set(60, h.FLOOR + 1, 80, "bookshelf")
    u.set(45, h.FLOOR + 1, 47, "red_carpet")            # under the inn's overhang, but open to the plaza
    e = h.fire_errors(u)
    assert "casa_heraldo: bookshelf at (60, 5, 80) is within reach of a fire started by lightning" in e
    assert "casa_heraldo: red_carpet at (45, 5, 47) is within reach of a fire started by lightning" in e
    names = {h._name(st) for st, _ in t.blocks.values()}
    assert {"bookshelf", "lectern", "composter", "hay_block", "coal_block"} <= names     # inside, and proven safe


def test_previous_blueprints_are_frozen():
    d = h.dataset(h.construct())
    assert d["version"] == 2
    v1 = d["anteriores"]["1"]
    assert v1["version"] == 1 and v1["tamano"] == [96, 21, 96] and len(v1["puestos"]) == 8
    assert v1["plantilla"] == d["plantilla"]
    assert d["plaza_eventos"] == [53, h.FLOOR, 49, 23]


def test_house_entities_are_tagged(t):
    # Building.finish keeps the house's own entities (HeraldHouse.HOUSE_TAG) where the template puts them
    assert t.entities and all(h.HOUSE_TAG in n.get("Tags", []) for *_, n in t.entities)


def test_stalls_are_empty_boxes_with_a_sign(t):
    d = h.dataset(t)
    assert [s["id"] for s in d["puestos"]] == list(range(1, 9))
    for s in d["puestos"]:
        (x0, y0, z0), (x1, y1, z1) = s["caja"]
        assert (x1 - x0, y1 - y0, z1 - z0) == (2, 2, 2)


def test_dock_template():
    dk = h.dock()
    w, length = h.DOCK_SIZE
    assert dk.size()[0] == w and dk.size()[2] == length


def test_sign_texts_fit():
    assert h.text_errors() == []


def test_texts_are_paired():
    out = h.lang()
    assert out["es_es"].keys() == out["en_us"].keys()
    assert out["en_us"]["heraldia.casa_heraldo.nombre"] == "The Herald's House"
    assert out["es_es"]["heraldia.casa_heraldo.nombre"] == "La Casa del Heraldo"
