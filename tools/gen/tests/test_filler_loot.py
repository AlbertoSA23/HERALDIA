"""filler_loot: no container of any template is empty when opened (the owner's rule), the filler tables stay poor, and
the containers left empty on purpose are exactly the listed ones."""
import fnmatch
import os
import re

import nbtlib
import pytest

import filler_loot
from core import Template, EMPTY_MARK

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# The containers left empty on purpose, by template: {template: (how many, reason)}. Adding one here is a decision, not
# an omission: say why in its leave_empty / empty_nbt reason.
EMPTY_ON_PURPOSE = {
    "casa_heraldo/casa": (12, "return barrel: Market only uses it while it is empty"),
    "unicas/palacio/palacio": (1, "palace: redstone part of the secret door, not storage"),
}

# What a filler table must never give: currency, gems, rare metals in bulk, enchanted or named things, treasure.
FORBIDDEN = {"emerald", "diamond", "netherite_scrap", "ancient_debris", "gold_ingot", "golden_apple",
             "enchanted_golden_apple", "experience_bottle", "name_tag", "saddle", "nautilus_shell", "heart_of_the_sea",
             "totem_of_undying", "ender_pearl", "blaze_rod", "map", "filled_map", "compass", "spyglass", "diamond_sword"}


def chest(t, p, nbt=None, kind="chest"):
    t.set(*p, f"{kind}[facing=north]" if kind != "barrel" else "barrel[facing=up]", nbt)


def test_fill_gives_the_rule_table_and_keeps_the_rest():
    t = Template("taiga_nordica/houses/small_0")
    chest(t, (0, 0, 0), {"id": "minecraft:barrel"}, kind="barrel")
    chest(t, (1, 0, 0))                                                           # no nbt at all
    chest(t, (2, 0, 0), {"id": "minecraft:chest", "LootTable": "heraldia:cofres/comun"})
    chest(t, (3, 0, 0), {"id": "minecraft:chest", "Items": [{"Slot": 0, "id": "minecraft:arrow", "count": 3}]})
    t.set(4, 0, 0, "barrel[facing=up]", filler_loot.empty_nbt("barrel", "a test"))
    t.set(5, 0, 0, "furnace[facing=north]", {"id": "minecraft:furnace"})       # not a lootable container
    t.entity(0, 1, 0, {"id": "minecraft:chest_minecart"})
    filler_loot.fill(t)
    lt = lambda p: (t.blocks[p][1] or {}).get("LootTable")
    assert lt((0, 0, 0)) == lt((1, 0, 0)) == "heraldia:relleno/casa"
    assert lt((2, 0, 0)) == "heraldia:cofres/comun" and lt((3, 0, 0)) is None and lt((4, 0, 0)) is None
    assert lt((5, 0, 0)) is None and t.entities[0][3]["LootTable"] == "heraldia:relleno/casa"
    assert filler_loot.unfilled(filler_loot.fill(t)) == []                      # idempotent


def test_a_container_with_no_rule_fails_the_generation():
    t = Template("nueva_familia/pieza")
    chest(t, (0, 0, 0), {"id": "minecraft:chest"})
    assert filler_loot.unfilled(t) == [((0, 0, 0), "minecraft:chest")]
    with pytest.raises(filler_loot.FillerError, match="nueva_familia/pieza"):
        t.save("/nonexistent")                                                    # fails before writing anything
    t2 = Template("nueva_familia/pieza")
    t2.entity(0, 0, 0, {"id": "minecraft:hopper_minecart"})
    assert filler_loot.unfilled(t2) == [("entity", "minecraft:hopper_minecart")]


def test_rules_are_specific_before_general():
    assert filler_loot.rule_for("unicas/isla_corsario/isla", "minecraft:dispenser") == "canon"
    assert filler_loot.rule_for("unicas/isla_corsario/isla", "minecraft:barrel") == "barco"
    assert filler_loot.rule_for("unicas/mansion/sotano", "minecraft:barrel") == "despensa"
    assert filler_loot.rule_for("unicas/ciudadela_ceniza/x", "minecraft:barrel") is None   # not the citadel's rule
    assert filler_loot.rule_for("costa_mercante/specials/inn_b", "minecraft:barrel") == "bodega"
    assert filler_loot.rule_for("casa_heraldo/casa", "minecraft:barrel") is None   # each one has its own table
    assert {tbl for *_, tbl in filler_loot.RULES} <= set(filler_loot.TABLES)


def test_the_empty_mark_is_never_written(tmp_path):
    t = Template("prueba/vacio")
    t.set(0, 0, 0, "barrel[facing=up]", filler_loot.empty_nbt("barrel", "a test"))
    t.set(1, 0, 0, "stone")
    p = t.save(str(tmp_path))
    n = nbtlib.load(p)
    assert dict(n["blocks"][0]["nbt"]) == {"id": "minecraft:barrel"}
    assert EMPTY_MARK not in t.nbt_raw().decode("latin-1")
    with pytest.raises(ValueError):
        filler_loot.empty_nbt("barrel", "")


def entries(tbl):
    for pool in tbl["pools"]:
        yield pool, pool["entries"]


@pytest.mark.parametrize("name", sorted(filler_loot.TABLES))
def test_filler_tables_are_never_empty_and_stay_poor(name):
    tbl = filler_loot.TABLES[name]
    assert tbl["type"] == "minecraft:chest" and len(tbl["pools"]) == 1
    for pool, es in entries(tbl):
        r = pool["rolls"]
        lo, hi = (r, r) if isinstance(r, int) else (r["min"], r["max"])
        assert 1 <= lo <= hi <= 3, "one to three stacks: opening it always gives something, never much"
        for e in es:
            assert e["type"] == "minecraft:item", "no empty entries (an empty roll could leave the container empty)"
            item = e["name"].removeprefix("minecraft:")
            assert item not in FORBIDDEN, f"{name}: {item} is not filler"
            mods = e.get("modifier", [])
            mods = mods if isinstance(mods, list) else [mods]
            assert not any("enchant" in m["type"] or m["type"] in ("minecraft:set_name", "minecraft:set_components")
                           for m in mods), f"{name}: {item} enchanted or named"
            count = next((m["count"] for m in mods if m["type"] == "minecraft:set_count"), {"max": 1})
            assert count["max"] <= 6, f"{name}: {item} up to {count['max']}"
            if item in ("iron_ingot", "iron_shovel", "fishing_rod", "honey_bottle", "lead", "raw_iron", "book",
                        "glowstone_dust", "prismarine_crystals"):
                assert e["weight"] <= 2 and count["max"] == 1, f"{name}: {item} must stay rare and single"


def test_filler_tables_do_not_restock_nor_scale():
    """Their prefix is none of Restock.PREFIXES: they never restock and MobDifficulty does not scale them."""
    src = open(os.path.join(ROOT, "src/main/java/io/github/albertosa23/heraldia/loot/Restock.java"), encoding="utf-8").read()
    prefixes = re.findall(r'"([a-z_]+/)"', re.search(r"PREFIXES = \{([^}]*)\}", src).group(1))
    assert prefixes and filler_loot.PREFIX + "/" not in prefixes


@pytest.fixture(scope="module")
def all_templates():
    """Every template the mod ships: the generated registry, the Herald's House and its dock, the spawn roads' huts and
    the arena (the same set the .jar carries)."""
    # building the registry needs the 26.3 registry summary (Atlantis floods by block properties): the build leaves it in
    # build/mcmeta-summary and CI's unit-test job clones it; without it (a bare checkout) this is skipped, and the same
    # rule is still enforced by the generation itself (Template.save, in ./gradlew build)
    summary = os.environ.get("MCMETA_SUMMARY") or os.path.join(ROOT, "build", "mcmeta-summary")
    if not os.path.isfile(os.path.join(summary, "blocks", "data.json")):
        pytest.skip(f"without the 26.3 registry summary ({summary}): run ./gradlew fetchRegistries or set MCMETA_SUMMARY")
    from pack import build_all
    import herald_house, spawn_roads, arena_waves
    reg = build_all()
    ts = dict(reg.templates)
    for t in [herald_house.construct(), herald_house.dock(), arena_waves.construct()] + list(spawn_roads.templates().values()):
        ts[t.name] = t
    return ts


def test_every_container_of_every_template_has_loot(all_templates):
    """The regression test of the owner's rule: a container without a table, without a rule and not listed as empty on
    purpose anywhere in the mod fails here (and fails the generation)."""
    assert len(all_templates) > 3000
    missing = {name: filler_loot.unfilled(t) for name, t in all_templates.items() if filler_loot.unfilled(t)}
    assert not missing, f"containers without a loot table: {dict(list(missing.items())[:10])}"


def test_the_empty_on_purpose_list_is_explicit(all_templates):
    found = {}
    for name, t in all_templates.items():
        for p, reason in filler_loot.empty_on_purpose(t).items():
            found.setdefault(name, []).append(reason)
    assert {k: (len(v), v[0]) for k, v in found.items()} == EMPTY_ON_PURPOSE
    assert all(len(set(v)) == 1 for v in found.values())


def test_the_herald_return_barrels_are_the_empty_ones(all_templates):
    import herald_house
    t = all_templates[herald_house.TEMPLATE]
    assert sorted(map(tuple, herald_house.dataset(t)["devolucion"])) == sorted(filler_loot.empty_on_purpose(t))


def test_every_rule_is_used(all_templates):
    """A rule that matches no container is stale (a renamed piece would silently fall to a broader rule)."""
    used = set()
    for name, t in all_templates.items():
        for p, (st, nbt) in t.blocks.items():
            if filler_loot.is_container(st) and not filler_loot.has_loot(nbt) and not (nbt and nbt.get(EMPTY_MARK)):
                for i, (pattern, blocks, _) in enumerate(filler_loot.RULES):
                    if fnmatch.fnmatchcase(name, pattern) and (blocks is None or st.split("[")[0] in blocks):
                        used.add(i)
                        break
    assert [filler_loot.RULES[i][0] for i in range(len(filler_loot.RULES)) if i not in used] == []
