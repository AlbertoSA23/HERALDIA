"""_comun/piezas.py: piezas comunes en estado coherente al colocarse."""
import pytest
import lint
from core import Template, ADULT_TAG, ANCHORED_TAG
from uniques._common import pieces, redstone as rs


def new_one():
    t = Template("p")
    return t, (lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt))


def test_spawner_light_and_potentials():
    t, put = new_one()
    pieces.spawner(put, 0, 0, 0, "zombie", potentials=True, light=7)
    st, nbt = t.blocks[(0, 0, 0)]
    assert st == "minecraft:spawner"
    assert nbt["SpawnData"]["entity"]["id"] == "minecraft:zombie"
    assert nbt["SpawnData"]["custom_spawn_rules"]["block_light_limit"]["max_inclusive"] == 7
    assert nbt["SpawnPotentials"][0]["data"] is nbt["SpawnData"]


def test_chest_barrel_and_waterlogged():
    t, put = new_one()
    pieces.chest(put, 0, 0, 0, "north", "heraldia:x")
    pieces.chest(put, 1, 0, 0, "up", "heraldia:y", kind="barrel")
    pieces.chest(put, 2, 0, 0, "east", "heraldia:z", waterlogged=True)
    assert t.blocks[(0, 0, 0)][1] == {"id": "minecraft:chest", "LootTable": "heraldia:x"}
    assert t.get(1, 0, 0) == "minecraft:barrel[facing=up]" and t.blocks[(1, 0, 0)][1]["id"] == "minecraft:barrel"
    assert "waterlogged=true" in t.get(2, 0, 0) and "type=single" in t.get(2, 0, 0)


def test_sign_four_lines():
    t, put = new_one()
    pieces.sign(put, 0, 0, 0, "south", [pieces.text("k", "f")])
    st, nbt = t.blocks[(0, 0, 0)]
    assert st.startswith("minecraft:dark_oak_wall_sign") and len(nbt["front_text"]["messages"]) == 4
    assert nbt["is_waxed"] == 1


def test_guardian_tags_and_attributes():
    g = pieces.guardian("zombie", "k", "Fb", 40, armor=4, attributes={"attack_damage": 5},
                        extra={"Tags": ["otra", pieces.GUARDIAN_TAG], "NoAI": 1})
    assert g["Tags"][0] == pieces.GUARDIAN_TAG and g["Tags"].count(pieces.GUARDIAN_TAG) == 1
    assert "otra" in g["Tags"] and ADULT_TAG in g["Tags"]            # zombi: siempre adulto
    ids = {a["id"]: a["base"] for a in g["attributes"]}
    assert ids == {"minecraft:max_health": 40.0, "minecraft:armor": 4.0, "minecraft:attack_damage": 5.0}
    assert g["NoAI"] == 1 and g["CustomName"] == {"translate": "k", "fallback": "Fb"}
    assert ADULT_TAG not in pieces.guardian("skeleton", "k", "f", 20)["Tags"]


@pytest.mark.parametrize("mob", ["zombie", "drowned", "skeleton", "evoker", "vindicator", "elder_guardian"])
def test_guardian_always_anchored(mob):
    g = pieces.guardian(mob, "k", "f", 40, extra={"Tags": ["otra"]})
    assert g["Tags"].count(ANCHORED_TAG) == 1 and pieces.GUARDIAN_TAG in g["Tags"] and "otra" in g["Tags"]


def test_wire_shapes():
    t, put = new_one()
    pieces.wire(put, [(0, 0), (1, 0), (1, 1)], y=1)
    assert "east=side" in t.get(0, 1, 0) and "west=side" in t.get(0, 1, 0)     # extremo suelto en línea recta
    assert "west=side" in t.get(1, 1, 0) and "south=side" in t.get(1, 1, 0)
    t, put = new_one()
    pieces.wire(put, [(0, 1, 0), (1, 2, 0)])
    assert "east=up" in t.get(0, 1, 0)


def test_tripwire_trap_taut_state():
    t, put = new_one()
    pieces.tripwire_trap(put, (0, 0), (0, 4), 1, "z", [((1, 1, 0), "south")])
    assert "facing=south" in t.get(0, 1, 0) and "facing=north" in t.get(0, 1, 4)
    assert all("attached=true" in t.get(0, 1, z) for z in range(1, 4))
    assert len(t.blocks[(1, 1, 0)][1]["Items"]) == 3


def test_double_door_without_hinge_failures():
    t, put = new_one()
    pieces.double_door(put, 0, 0, 0, "north", "east")
    assert lint.door_pair_issues(t) == []
    # al cambiar la bisagra de una hoja, la auditoría lo ve
    st = t.get(0, 0, 0)
    t.set(0, 0, 0, st.replace("hinge=left", "hinge=X").replace("hinge=right", "hinge=left").replace("hinge=X", "hinge=right"))
    assert lint.door_pair_issues(t)


def test_tnt_trap():
    t, put = new_one()
    pieces.tnt_trap(put, 0, 2, 0, warn=[(1, 1, 0)])
    assert t.get(0, 0, 0) == "minecraft:tnt[unstable=false]" and t.get(1, 1, 0) == "minecraft:cracked_stone_bricks"


def test_lever_door_stable_and_opens():
    t, put = new_one()
    for x in range(-1, 6):
        for y in range(0, 3):
            for z in range(-1, 2):
                put(x, y, z, "stone_bricks")
    r = pieces.lever_door(put, (0, 0, 0), "east", "north", "stone_bricks", "stone_bricks")
    assert rs.check_static(t)[0] == []
    pist = [(2, 0, 0), (2, 1, 0)]
    assert all(rs.Sim(t).powered(p) for p in pist)                       # cerrada: pistones con señal
    assert not any(rs.Sim(t, {r["lever"]: True}).powered(p) for p in pist)   # palanca: se recogen
    assert r["opened"][r["lever"]].endswith("powered=true]")


def test_plate_and_lever_trap():
    t, put = new_one()
    pieces.plate_trap(put, [(0, 1, 0)], "east")
    assert t.get(1, 1, 0).startswith("minecraft:dispenser[facing=west") and t.get(-1, 1, 0).startswith("minecraft:dispenser[facing=east")
    t, put = new_one()
    pieces.lever_trap(put, (0, 1, 0), (1, 1, 0), (1, 1, 1), "south")
    assert "facing=west" in t.get(0, 1, 0)


def test_item_frame_and_painting():
    f = pieces.item_frame(1, 2, 3, 2, item="compass")
    assert f["block_pos"] == [1, 2, 3] and f["Item"]["id"] == "minecraft:compass"
    p = pieces.painting(1, 2, 3, "east", "kebab")
    assert int(p["facing"]) == 3 and list(p["block_pos"]) == [1, 2, 3]


def test_spiral_stair_rises_six_per_flight():
    t, put = new_one()
    guard = pieces.spiral_stair(put, 0, 0, [1, 7], "stone_brick_stairs", "stone_bricks", "stone_bricks")
    assert guard == pieces.GUARD
    steps = sorted(p for p, (st, _) in t.blocks.items() if "half=bottom" in st)
    assert sorted(y for _, y, _ in steps) == list(range(1, 13))
    assert all(t.get(0, y, 0) == "minecraft:stone_bricks" for y in range(0, 14))   # machón


def test_spiral_slabs_and_slab_y():
    assert pieces.slab_y(3) == (2, "top") and pieces.slab_y(3.5) == (3, "bottom")
    t, put = new_one()
    steps = pieces.spiral_slabs(put, 0, 0, 1, 3, 0, "stone_slab")
    assert len(steps) == 5 and steps[-1][3] == 3


def test_circle():
    c = pieces.circle(0, 0, 1)
    assert sorted(c) == sorted([(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)])


def test_connect_fences_and_walls():
    t, put = new_one()
    put(0, 0, 0, "oak_fence")
    put(1, 0, 0, "oak_fence")
    put(0, 0, 1, "stone")
    put(5, 0, 0, "cobblestone_wall")
    put(5, 0, 1, "cobblestone_wall")
    put(5, 0, -1, "cobblestone_wall")
    pieces.connect(t)
    assert "east=true" in t.get(0, 0, 0) and "south=true" in t.get(0, 0, 0) and "west=false" in t.get(0, 0, 0)
    w = t.get(5, 0, 0)
    assert "north=low" in w and "south=low" in w and "up=false" in w     # tramo recto: sin poste


def test_open_stairwells_removes_the_roof_below():
    t, put = new_one()
    for x in range(-1, 6):
        put(x, -1, 0, "stone")
    for i in range(4):
        put(i, i, 0, "oak_stairs[facing=east,half=bottom]")
    put(1, 4, 0, "stone")                   # techo a 3 del peldaño 1 cuando sigue otro peldaño
    assert ("escalera con techo bajo en la subida", (1, 1, 0)) in lint.stair_headroom_issues(t)
    assert pieces.open_stairwells(t) == [(1, 4, 0)]
    assert t.get(1, 4, 0) == "minecraft:air"
