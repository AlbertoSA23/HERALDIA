"""_comun/piezas.py: piezas comunes en estado coherente al colocarse."""
import pytest
import lint
from core import Template, ADULTO_TAG, ANCLADO_TAG
from unicas._comun import piezas, redstone as rs


def nueva():
    t = Template("p")
    return t, (lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt))


def test_spawner_luz_y_potentials():
    t, put = nueva()
    piezas.spawner(put, 0, 0, 0, "zombie", potentials=True, luz=7)
    st, nbt = t.blocks[(0, 0, 0)]
    assert st == "minecraft:spawner"
    assert nbt["SpawnData"]["entity"]["id"] == "minecraft:zombie"
    assert nbt["SpawnData"]["custom_spawn_rules"]["block_light_limit"]["max_inclusive"] == 7
    assert nbt["SpawnPotentials"][0]["data"] is nbt["SpawnData"]


def test_chest_barril_y_anegado():
    t, put = nueva()
    piezas.chest(put, 0, 0, 0, "north", "heraldia:x")
    piezas.chest(put, 1, 0, 0, "up", "heraldia:y", kind="barrel")
    piezas.chest(put, 2, 0, 0, "east", "heraldia:z", waterlogged=True)
    assert t.blocks[(0, 0, 0)][1] == {"id": "minecraft:chest", "LootTable": "heraldia:x"}
    assert t.get(1, 0, 0) == "minecraft:barrel[facing=up]" and t.blocks[(1, 0, 0)][1]["id"] == "minecraft:barrel"
    assert "waterlogged=true" in t.get(2, 0, 0) and "type=single" in t.get(2, 0, 0)


def test_sign_cuatro_lineas():
    t, put = nueva()
    piezas.sign(put, 0, 0, 0, "south", [piezas.text("k", "f")])
    st, nbt = t.blocks[(0, 0, 0)]
    assert st.startswith("minecraft:dark_oak_wall_sign") and len(nbt["front_text"]["messages"]) == 4
    assert nbt["is_waxed"] == 1


def test_guardian_etiquetas_y_atributos():
    g = piezas.guardian("zombie", "k", "Fb", 40, armor=4, attributes={"attack_damage": 5},
                        extra={"Tags": ["otra", piezas.GUARDIAN_TAG], "NoAI": 1})
    assert g["Tags"][0] == piezas.GUARDIAN_TAG and g["Tags"].count(piezas.GUARDIAN_TAG) == 1
    assert "otra" in g["Tags"] and ADULTO_TAG in g["Tags"]            # zombi: siempre adulto
    ids = {a["id"]: a["base"] for a in g["attributes"]}
    assert ids == {"minecraft:max_health": 40.0, "minecraft:armor": 4.0, "minecraft:attack_damage": 5.0}
    assert g["NoAI"] == 1 and g["CustomName"] == {"translate": "k", "fallback": "Fb"}
    assert ADULTO_TAG not in piezas.guardian("skeleton", "k", "f", 20)["Tags"]


@pytest.mark.parametrize("mob", ["zombie", "drowned", "skeleton", "evoker", "vindicator", "elder_guardian"])
def test_guardian_siempre_anclado(mob):
    g = piezas.guardian(mob, "k", "f", 40, extra={"Tags": ["otra"]})
    assert g["Tags"].count(ANCLADO_TAG) == 1 and piezas.GUARDIAN_TAG in g["Tags"] and "otra" in g["Tags"]


def test_wire_formas():
    t, put = nueva()
    piezas.wire(put, [(0, 0), (1, 0), (1, 1)], y=1)
    assert "east=side" in t.get(0, 1, 0) and "west=side" in t.get(0, 1, 0)     # extremo suelto en línea recta
    assert "west=side" in t.get(1, 1, 0) and "south=side" in t.get(1, 1, 0)
    t, put = nueva()
    piezas.wire(put, [(0, 1, 0), (1, 2, 0)])
    assert "east=up" in t.get(0, 1, 0)


def test_tripwire_trap_estado_tenso():
    t, put = nueva()
    piezas.tripwire_trap(put, (0, 0), (0, 4), 1, "z", [((1, 1, 0), "south")])
    assert "facing=south" in t.get(0, 1, 0) and "facing=north" in t.get(0, 1, 4)
    assert all("attached=true" in t.get(0, 1, z) for z in range(1, 4))
    assert len(t.blocks[(1, 1, 0)][1]["Items"]) == 3


def test_double_door_sin_fallos_de_bisagra():
    t, put = nueva()
    piezas.double_door(put, 0, 0, 0, "north", "east")
    assert lint.door_pair_issues(t) == []
    # al cambiar la bisagra de una hoja, la auditoría lo ve
    st = t.get(0, 0, 0)
    t.set(0, 0, 0, st.replace("hinge=left", "hinge=X").replace("hinge=right", "hinge=left").replace("hinge=X", "hinge=right"))
    assert lint.door_pair_issues(t)


def test_tnt_trap():
    t, put = nueva()
    piezas.tnt_trap(put, 0, 2, 0, warn=[(1, 1, 0)])
    assert t.get(0, 0, 0) == "minecraft:tnt[unstable=false]" and t.get(1, 1, 0) == "minecraft:cracked_stone_bricks"


def test_lever_door_estable_y_abre():
    t, put = nueva()
    for x in range(-1, 6):
        for y in range(0, 3):
            for z in range(-1, 2):
                put(x, y, z, "stone_bricks")
    r = piezas.lever_door(put, (0, 0, 0), "east", "north", "stone_bricks", "stone_bricks")
    assert rs.check_static(t)[0] == []
    pist = [(2, 0, 0), (2, 1, 0)]
    assert all(rs.Sim(t).powered(p) for p in pist)                       # cerrada: pistones con señal
    assert not any(rs.Sim(t, {r["lever"]: True}).powered(p) for p in pist)   # palanca: se recogen
    assert r["opened"][r["lever"]].endswith("powered=true]")


def test_plate_y_lever_trap():
    t, put = nueva()
    piezas.plate_trap(put, [(0, 1, 0)], "east")
    assert t.get(1, 1, 0).startswith("minecraft:dispenser[facing=west") and t.get(-1, 1, 0).startswith("minecraft:dispenser[facing=east")
    t, put = nueva()
    piezas.lever_trap(put, (0, 1, 0), (1, 1, 0), (1, 1, 1), "south")
    assert "facing=west" in t.get(0, 1, 0)


def test_item_frame_y_painting():
    f = piezas.item_frame(1, 2, 3, 2, item="compass")
    assert f["block_pos"] == [1, 2, 3] and f["Item"]["id"] == "minecraft:compass"
    p = piezas.painting(1, 2, 3, "east", "kebab")
    assert int(p["facing"]) == 3 and list(p["block_pos"]) == [1, 2, 3]


def test_spiral_stair_sube_seis_por_tramo():
    t, put = nueva()
    guard = piezas.spiral_stair(put, 0, 0, [1, 7], "stone_brick_stairs", "stone_bricks", "stone_bricks")
    assert guard == piezas.GUARD
    steps = sorted(p for p, (st, _) in t.blocks.items() if "half=bottom" in st)
    assert sorted(y for _, y, _ in steps) == list(range(1, 13))
    assert all(t.get(0, y, 0) == "minecraft:stone_bricks" for y in range(0, 14))   # machón


def test_spiral_slabs_y_slab_y():
    assert piezas.slab_y(3) == (2, "top") and piezas.slab_y(3.5) == (3, "bottom")
    t, put = nueva()
    steps = piezas.spiral_slabs(put, 0, 0, 1, 3, 0, "stone_slab")
    assert len(steps) == 5 and steps[-1][3] == 3


def test_circle():
    c = piezas.circle(0, 0, 1)
    assert sorted(c) == sorted([(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)])


def test_connect_vallas_y_muros():
    t, put = nueva()
    put(0, 0, 0, "oak_fence")
    put(1, 0, 0, "oak_fence")
    put(0, 0, 1, "stone")
    put(5, 0, 0, "cobblestone_wall")
    put(5, 0, 1, "cobblestone_wall")
    put(5, 0, -1, "cobblestone_wall")
    piezas.connect(t)
    assert "east=true" in t.get(0, 0, 0) and "south=true" in t.get(0, 0, 0) and "west=false" in t.get(0, 0, 0)
    w = t.get(5, 0, 0)
    assert "north=low" in w and "south=low" in w and "up=false" in w     # tramo recto: sin poste


def test_open_stairwells_quita_el_techo_bajo():
    t, put = nueva()
    for x in range(-1, 6):
        put(x, -1, 0, "stone")
    for i in range(4):
        put(i, i, 0, "oak_stairs[facing=east,half=bottom]")
    put(1, 4, 0, "stone")                   # techo a 3 del peldaño 1 cuando sigue otro peldaño
    assert ("escalera con techo bajo en la subida", (1, 1, 0)) in lint.stair_headroom_issues(t)
    assert piezas.open_stairwells(t) == [(1, 4, 0)]
    assert t.get(1, 4, 0) == "minecraft:air"
