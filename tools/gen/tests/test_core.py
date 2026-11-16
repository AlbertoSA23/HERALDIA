"""core.py: estados, NBT de plantillas y utilidades de Template."""
import nbtlib
import pytest
from core import (parse_state, state_str, with_props, nsid, norm_id, to_tag, B, F, Template, adulto, ADULTO_TAG, anclado, ANCLADO_TAG, RECOGE_BOTIN, BEBE_ZOMBI,
                  villager, DATA_VERSION)


def test_parse_state_y_state_str():
    assert parse_state("stone") == ("minecraft:stone", {})
    bid, p = parse_state("minecraft:oak_stairs[half=bottom, facing=east]")
    assert bid == "minecraft:oak_stairs" and p == {"half": "bottom", "facing": "east"}
    # las propiedades salen ordenadas: dos escrituras del mismo estado son la misma cadena
    assert state_str(bid, p) == "minecraft:oak_stairs[facing=east,half=bottom]"
    assert state_str("minecraft:air", {}) == "minecraft:air"


def test_parse_state_invalido():
    with pytest.raises(ValueError):
        parse_state("Stone Bricks")


def test_with_props_y_ids():
    assert with_props("lever[powered=false]", powered=True) == "minecraft:lever[powered=true]"
    assert norm_id("dirt") == "minecraft:dirt" and norm_id("heraldia:x") == "heraldia:x"
    assert nsid("aldeas/x") == "heraldia:aldeas/x" and nsid("minecraft:empty") == "minecraft:empty"


def test_to_tag_tipos():
    assert isinstance(to_tag(B(1)), nbtlib.Byte) and isinstance(to_tag(True), nbtlib.Byte)
    assert isinstance(to_tag(F(0.5)), nbtlib.Float) and isinstance(to_tag(0.5), nbtlib.Double)
    assert isinstance(to_tag(3), nbtlib.Int) and isinstance(to_tag("a"), nbtlib.String)
    c = to_tag({"a": [1, 2], "b": {}})
    assert isinstance(c, nbtlib.Compound) and isinstance(c["a"], nbtlib.List)
    ia = nbtlib.IntArray([1, 2, 3])
    assert to_tag(ia) is ia            # etiquetas ya construidas pasan tal cual
    with pytest.raises(TypeError):
        to_tag(object())


def test_template_set_get_fill_normalize():
    t = Template("x")
    t.fill(2, 3, 4, 1, 3, 5, "stone")      # extremos al revés: fill los ordena
    assert len(t.blocks) == 4 and t.get(1, 3, 4) == "minecraft:stone"
    t.set(1, 3, 4, "dirt", keep=True)       # keep no pisa un bloque que no es aire
    assert t.get(1, 3, 4) == "minecraft:stone"
    t.jigsaw(1, 3, 5, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty")
    t.normalize()
    assert t.bounds()[:3] == (0, 0, 0) and t.jigsaws[0]["pos"] == (0, 0, 1)
    assert t.size() == (2, 1, 2)
    assert t.is_free(5, 5, 5)


def test_to_nbt_paleta_y_orden():
    t = Template("x")
    t.set(1, 0, 0, "stone")
    t.set(0, 0, 0, "oak_log[axis=y]")
    t.set(0, 1, 0, "stone")
    t.chest(1, 1, 0, "north", "heraldia:botin")
    t.entity(0, 1, 0, {"id": "minecraft:cat"})
    n = t.to_nbt()
    assert int(n["DataVersion"]) == DATA_VERSION
    assert [int(c) for c in n["size"]] == [2, 2, 1]
    assert len(n["palette"]) == 3                     # stone se reutiliza
    assert str(n["palette"][0]["properties"]["axis"]) == "y"
    # orden y, z, x: el (0,0,0) primero
    assert [list(map(int, b["pos"])) for b in n["blocks"]][:2] == [[0, 0, 0], [1, 0, 0]]
    assert str(n["blocks"][3]["nbt"]["LootTable"]) == "heraldia:botin"
    e = n["entities"][0]
    assert [float(c) for c in e["pos"]] == [0.5, 1.0, 0.5] and [float(c) for c in e["nbt"]["Pos"]] == [0.5, 1.0, 0.5]


def test_to_nbt_rechaza_negativos():
    t = Template("x")
    t.set(-1, 0, 0, "stone")
    with pytest.raises(AssertionError):
        t.to_nbt()


def test_anclado():
    z = anclado({"id": "minecraft:zombie", "Tags": ["a"]})
    assert z["Tags"] == ["a", ANCLADO_TAG]
    assert anclado(dict(z))["Tags"].count(ANCLADO_TAG) == 1       # idempotente
    assert anclado({"id": "minecraft:skeleton"})["Tags"] == [ANCLADO_TAG]
    assert "Tags" not in anclado({"id": "minecraft:evoker"})          # no recoge objetos: solo si es guardián
    assert anclado({"id": "minecraft:evoker"}, siempre=True)["Tags"] == [ANCLADO_TAG]
    assert "Tags" not in anclado({"id": "minecraft:villager"})        # los aldeanos recogen cosechas
    assert BEBE_ZOMBI <= RECOGE_BOTIN and "minecraft:wither_skeleton" in RECOGE_BOTIN
    assert all(m.startswith("minecraft:") for m in RECOGE_BOTIN)


def test_adulto_y_aldeano():
    z = adulto({"id": "minecraft:zombie", "Tags": ["a"]})
    assert z["Tags"] == ["a", ADULTO_TAG]
    assert adulto(dict(z))["Tags"].count(ADULTO_TAG) == 1      # idempotente
    assert "Tags" not in adulto({"id": "minecraft:skeleton"})
    v = villager("librarian", "plains")
    assert v["Tags"] == ["heraldia"] and v["Xp"] == 1
    assert villager("librarian", "plains", employed=False)["VillagerData"]["profession"] == "minecraft:none"


def _nbtlib(t):
    import io
    from nbtlib import File
    b = io.BytesIO()
    File(t.to_nbt()).write(b, "big")
    return b.getvalue()


def test_nbt_raw_igual_que_nbtlib():
    """El serializador directo de Template.nbt_raw da los mismos bytes que nbtlib (to_nbt + File.write)."""
    from unicas._comun import piezas
    t = Template("x")
    t.fill(0, 0, 0, 3, 1, 2, "stone_bricks")
    t.set(1, 2, 1, "oak_stairs[half=bottom,facing=east]")
    t.chest(2, 2, 1, "north", "heraldia:x")
    t.jigsaw(0, 2, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty")
    t.entity(1, 2, 1, piezas.guardian("zombie", "k", "f", 30, equipment={"mainhand": {"id": "minecraft:iron_axe", "count": 1}},
                                      drop_chances={"mainhand": 0.0}))
    t.entity(0, 2, 2, piezas.painting(0, 2, 2, "south", "kebab"))
    t.entity(2, 2, 2, piezas.item_frame(2, 2, 2, 2, item="compass"))
    assert t.nbt_raw() == _nbtlib(t)
    vacia = Template("v")
    vacia.set(0, 0, 0, "air")
    assert vacia.nbt_raw() == _nbtlib(vacia)          # sin entidades: lista vacía de compuestos


def test_nbt_bytes_deterministas():
    import gzip
    t = Template("x")
    t.set(0, 0, 0, "stone")
    a = t.nbt_bytes()
    assert a == t.nbt_bytes() and gzip.decompress(a) == t.nbt_raw()
    assert a[4:8] == b"\x00\x00\x00\x00"              # mtime 0 en la cabecera gzip


def test_save(tmp_path):
    import gzip, nbtlib
    t = Template("tema/casas/a")
    t.set(0, 0, 0, "stone")
    p = t.save(str(tmp_path))
    assert p.endswith("data/heraldia/structure/tema/casas/a.nbt")
    assert int(nbtlib.load(p)["DataVersion"]) == DATA_VERSION
    assert gzip.open(p).read() == t.nbt_raw()
