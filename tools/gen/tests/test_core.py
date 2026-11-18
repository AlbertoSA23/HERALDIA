"""core.py: states, template NBT and Template utilities."""
import nbtlib
import pytest
from core import (parse_state, state_str, with_props, nsid, norm_id, to_tag, B, F, Template, adult, ADULT_TAG, anchored, ANCHORED_TAG, PICKS_UP_LOOT, BABY_ZOMBIE,
                  villager, DATA_VERSION)


def test_parse_state_and_state_str():
    assert parse_state("stone") == ("minecraft:stone", {})
    bid, p = parse_state("minecraft:oak_stairs[half=bottom, facing=east]")
    assert bid == "minecraft:oak_stairs" and p == {"half": "bottom", "facing": "east"}
    # the properties come out sorted: two writes of the same state are the same string
    assert state_str(bid, p) == "minecraft:oak_stairs[facing=east,half=bottom]"
    assert state_str("minecraft:air", {}) == "minecraft:air"


def test_parse_state_invalid():
    with pytest.raises(ValueError):
        parse_state("Stone Bricks")


def test_with_props_and_ids():
    assert with_props("lever[powered=false]", powered=True) == "minecraft:lever[powered=true]"
    assert norm_id("dirt") == "minecraft:dirt" and norm_id("heraldia:x") == "heraldia:x"
    assert nsid("aldeas/x") == "heraldia:aldeas/x" and nsid("minecraft:empty") == "minecraft:empty"


def test_to_tag_types():
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
    t.fill(2, 3, 4, 1, 3, 5, "stone")      # reversed extremes: fill sorts them
    assert len(t.blocks) == 4 and t.get(1, 3, 4) == "minecraft:stone"
    t.set(1, 3, 4, "dirt", keep=True)       # keep does not overwrite a block that is not air
    assert t.get(1, 3, 4) == "minecraft:stone"
    t.jigsaw(1, 3, 5, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty")
    t.normalize()
    assert t.bounds()[:3] == (0, 0, 0) and t.jigsaws[0]["pos"] == (0, 0, 1)
    assert t.size() == (2, 1, 2)
    assert t.is_free(5, 5, 5)


def test_to_nbt_palette_and_order():
    t = Template("x")
    t.set(1, 0, 0, "stone")
    t.set(0, 0, 0, "oak_log[axis=y]")
    t.set(0, 1, 0, "stone")
    t.chest(1, 1, 0, "north", "heraldia:botin")
    t.entity(0, 1, 0, {"id": "minecraft:cat"})
    n = t.to_nbt()
    assert int(n["DataVersion"]) == DATA_VERSION
    assert [int(c) for c in n["size"]] == [2, 2, 1]
    assert len(n["palette"]) == 3                     # stone is reused
    assert str(n["palette"][0]["properties"]["axis"]) == "y"
    # order y, z, x: (0,0,0) first
    assert [list(map(int, b["pos"])) for b in n["blocks"]][:2] == [[0, 0, 0], [1, 0, 0]]
    assert str(n["blocks"][3]["nbt"]["LootTable"]) == "heraldia:botin"
    e = n["entities"][0]
    assert [float(c) for c in e["pos"]] == [0.5, 1.0, 0.5] and [float(c) for c in e["nbt"]["Pos"]] == [0.5, 1.0, 0.5]


def test_to_nbt_rejects_negatives():
    t = Template("x")
    t.set(-1, 0, 0, "stone")
    with pytest.raises(AssertionError):
        t.to_nbt()


def test_anchored():
    z = anchored({"id": "minecraft:zombie", "Tags": ["a"]})
    assert z["Tags"] == ["a", ANCHORED_TAG]
    assert anchored(dict(z))["Tags"].count(ANCHORED_TAG) == 1       # idempotente
    assert anchored({"id": "minecraft:skeleton"})["Tags"] == [ANCHORED_TAG]
    assert "Tags" not in anchored({"id": "minecraft:evoker"})          # does not pick up objects: only if it is a guardian
    assert anchored({"id": "minecraft:evoker"}, always=True)["Tags"] == [ANCHORED_TAG]
    assert "Tags" not in anchored({"id": "minecraft:villager"})        # villagers pick up crops
    assert BABY_ZOMBIE <= PICKS_UP_LOOT and "minecraft:wither_skeleton" in PICKS_UP_LOOT
    assert all(m.startswith("minecraft:") for m in PICKS_UP_LOOT)


def test_adult_and_villager():
    z = adult({"id": "minecraft:zombie", "Tags": ["a"]})
    assert z["Tags"] == ["a", ADULT_TAG]
    assert adult(dict(z))["Tags"].count(ADULT_TAG) == 1      # idempotente
    assert "Tags" not in adult({"id": "minecraft:skeleton"})
    v = villager("librarian", "plains")
    assert v["Tags"] == ["heraldia"] and v["Xp"] == 1
    assert villager("librarian", "plains", employed=False)["VillagerData"]["profession"] == "minecraft:none"


def _nbtlib(t):
    import io
    from nbtlib import File
    b = io.BytesIO()
    File(t.to_nbt()).write(b, "big")
    return b.getvalue()


def test_nbt_raw_same_as_nbtlib():
    """The direct serialiser Template.nbt_raw gives the same bytes as nbtlib (to_nbt + File.write)."""
    from uniques._common import pieces
    t = Template("x")
    t.fill(0, 0, 0, 3, 1, 2, "stone_bricks")
    t.set(1, 2, 1, "oak_stairs[half=bottom,facing=east]")
    t.chest(2, 2, 1, "north", "heraldia:x")
    t.jigsaw(0, 2, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty")
    t.entity(1, 2, 1, pieces.guardian("zombie", "k", "f", 30, equipment={"mainhand": {"id": "minecraft:iron_axe", "count": 1}},
                                      drop_chances={"mainhand": 0.0}))
    t.entity(0, 2, 2, pieces.painting(0, 2, 2, "south", "kebab"))
    t.entity(2, 2, 2, pieces.item_frame(2, 2, 2, 2, item="compass"))
    assert t.nbt_raw() == _nbtlib(t)
    blank = Template("v")
    blank.set(0, 0, 0, "air")
    assert blank.nbt_raw() == _nbtlib(blank)          # without entities: empty list of compounds


def test_nbt_bytes_deterministic():
    import gzip
    t = Template("x")
    t.set(0, 0, 0, "stone")
    a = t.nbt_bytes()
    assert a == t.nbt_bytes() and gzip.decompress(a) == t.nbt_raw()
    assert a[4:8] == b"\x00\x00\x00\x00"              # mtime 0 in the gzip header


def test_save(tmp_path):
    import gzip, nbtlib
    t = Template("tema/casas/a")
    t.set(0, 0, 0, "stone")
    p = t.save(str(tmp_path))
    assert p.endswith("data/heraldia/structure/tema/casas/a.nbt")
    assert int(nbtlib.load(p)["DataVersion"]) == DATA_VERSION
    assert gzip.open(p).read() == t.nbt_raw()
