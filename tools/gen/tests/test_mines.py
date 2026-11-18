"""Mine entrances (minas/): templates of the three sizes and the five styles (own audit, shape, mouth, gallery,
tracks), styles by biome, moderate loot, what it writes to the datapack (structures, grids, tags, the placement
of the vanilla mines), its options, its advancements and the guide. With negative audit cases (a leak in the lining,
the descent or the shaft walled up, a cut track) so that a change that breaks the mine fails here in seconds."""
import json
import pytest
import guide
import advancements
import mines
import options
import uniques
from mines import audit, blueprints
from mines.chest_loot import FORBIDDEN, DIAMONDS_MAX
from pack import Registry

ALL_COMBOS = [(t, e, v) for t in mines.SIZES for e in mines.STYLES for v in mines.VARIANTS]


@pytest.fixture(scope="module")
def constructions():
    return {k: mines.construction(*k)[0] for k in ALL_COMBOS}


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    """What minas.write leaves in the datapack: ({path: json} from jdump, {path: json} of the biome tags, texts)."""
    import os
    import biomes
    previous = dict(biomes._WRITTEN)
    files, tags = {}, {}
    d = str(tmp_path_factory.mktemp("minas"))
    lang = mines.write(d, lambda _out, path, obj: files.__setitem__(path, obj))
    for root, _, fs in os.walk(d):
        for f in fs:
            with open(os.path.join(root, f), encoding="utf-8") as h:
                tags[os.path.relpath(os.path.join(root, f), d).replace(os.sep, "/")] = json.load(h)
    biomes._WRITTEN.clear()
    biomes._WRITTEN.update(previous)
    return files, tags, lang


# ------------------------------------------------------------------ templates
@pytest.mark.parametrize("key", ALL_COMBOS, ids=["/".join(k) for k in ALL_COMBOS])
def test_audit_of_each_variant(constructions, key):
    assert audit.errors(constructions[key], key[0]) == []


def test_sizes_and_depth(constructions):
    for (size, sty, v), o in constructions.items():
        x0, y0, z0, x1, y1, z1 = o.t.bounds()
        sx, sy, sz = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1
        assert max(sx, sz) <= 8 * 16, f"{size}/{sty}/{v}: {sx} x {sz}: does not fit in the reach of a start (8 chunks)"
        deep = min(y for _, y, _ in o.nodes) + 1
        assert deep <= -blueprints.SIZES[size]["hondo"] + 1
    measurement = {t: max(len(constructions[(t, e, v)].t.blocks) for e in mines.STYLES for v in mines.VARIANTS) for t in mines.SIZES}
    assert measurement["pequena"] < measurement["mediana"] < measurement["grande"] < 40000, measurement


def test_the_mouth_is_where_the_json_says():
    for size, sty, v in ALL_COMBOS:
        o, (x0, y0, z0), meta = mines.construction(size, sty, v)
        ex, ey, ez = meta["entrada"]
        assert (ex + x0, ey + y0, ez + z0) == (0, 0, 0)
        assert o.t.get(0, 1, 0).startswith("minecraft:rail"), "track under the mouth lintel"
        assert "_log" in o.t.get(2, 1, 0) and "_log" in o.t.get(-2, 1, 0), "mouth posts"
        px0, pz0, px1, pz1 = meta["patio"]
        assert pz1 == ez - 1 and px0 < ex < px1, "the yard is in front of the mouth"
        assert 4 <= len(meta["techo"]) <= 12, "ceiling samples for the Java (each one costs a column)"
        for x, z, dy in meta["techo"]:
            assert z > ez and dy < 0, "the samples are above the gallery, below the yard"


def test_variants_distinct_and_mirrored(constructions):
    for size in mines.SIZES:
        for sty in mines.STYLES:
            a, b = constructions[(size, sty, "a")], constructions[(size, sty, "b")]
            assert a.t.blocks != b.t.blocks
            assert {p for p, _ in a.chest_list} != {p for p, _ in b.chest_list}
    # what has a side (stairs, doors) is mirrored: the foreman of medium structure b looks the other way
    a, b = constructions[("mediana", "montana", "a")], constructions[("mediana", "montana", "b")]
    doors_a = [p for p, (st, _) in a.t.blocks.items() if "_door" in st and "lower" in st]
    doors_b = [p for p, (st, _) in b.t.blocks.items() if "_door" in st and "lower" in st]
    assert [(-x, y, z) for x, y, z in doors_a] == doors_b


def test_each_size_has_what_is_own(constructions):
    def names(o):
        return {st.split("[")[0].replace("minecraft:", "") for st, _ in o.t.blocks.values()}
    for sty in mines.STYLES:
        p, m, g = (constructions[(t, sty, "a")] for t in mines.SIZES)
        ids = lambda o: sorted(n["id"] for *_, n in o.t.entities)
        assert ids(p) == ["minecraft:minecart"], "the small mouth: a minecart on its tracks"
        assert "minecraft:chest_minecart" in ids(m) and "minecraft:cave_spider" not in ids(m), "no mobs: a spawner"
        assert "minecraft:chest_minecart" in ids(g)
        assert {"blast_furnace", "furnace", "anvil", "campfire", "crafting_table"} <= names(m), "smelter and cabin"
        assert "spawner" in names(g) and "spawner" in names(m) and "spawner" not in names(p)
        assert "iron_chain" in names(g), "the pulley chain"
        assert g.descent is not None and p.descent is None and m.descent is None, "only the large one has a shaft"
        assert len({y for _, y, _ in g.nodes}) == 2, "the large one has two levels"


def test_generator_small_of_spiders(constructions):
    for size, sty in [(t, e) for t in ("mediana", "grande") for e in mines.STYLES]:
        o = constructions[(size, sty, "a")]
        (x, y, z), = o.generators
        st, nbt = o.t.blocks[(x, y, z)]
        assert nbt["SpawnData"]["entity"]["id"] == "minecraft:cave_spider"
        assert nbt["MaxNearbyEntities"] <= 4 and nbt["SpawnCount"] <= 2 and nbt["RequiredPlayerRange"] <= 16
        assert y <= -blueprints.SIZES[size]["hondo"] + 2, "deep in the gallery"


def test_persistent_and_anchored_mobs(constructions):
    from core import ANCHORED_TAG
    for o in constructions.values():
        for *_, n in o.t.entities:
            if "minecart" not in n["id"]:
                assert n.get("PersistenceRequired") and ANCHORED_TAG in n["Tags"]


# ------------------------------------------------------------------ styles by biome
MATERIALS = {"montana": ("oak_log", "cobblestone"), "taiga": ("spruce_log", "cobblestone"),
              "desierto": ("birch_log", "sandstone"), "badlands": ("dark_oak_log", "terracotta"),
              "picos": ("stripped_spruce_log", "cobbled_deepslate")}


def test_styles_by_biome():
    seen_all = set()
    for sty, d in mines.STYLES.items():
        assert d["biomas"] and not (set(d["biomas"]) & seen_all), f"{sty}: biomas repetidos en otro estilo"
        seen_all |= set(d["biomas"])
    assert {"desert"} == set(mines.STYLES["desierto"]["biomas"])
    assert "snowy_slopes" in mines.STYLES["taiga"]["biomas"] and "jagged_peaks" in mines.STYLES["picos"]["biomas"]
    assert "eroded_badlands" in mines.STYLES["badlands"]["biomas"]


def test_style_materials(constructions):
    for (size, sty, v), o in constructions.items():
        trunk, stone = MATERIALS[sty]
        tally = {}
        for st, _ in o.t.blocks.values():
            n = st.split("[")[0].replace("minecraft:", "")
            tally[n] = tally.get(n, 0) + 1
        assert tally.get(trunk, 0) > 20, f"{size}/{sty}/{v}: entibado de {trunk}"
        assert tally.get(stone, 0) > 100, f"{size}/{sty}/{v}: obra de {stone}"
        others = [t for e, (t, _) in MATERIALS.items() if e != sty and t != trunk]
        assert not any(tally.get(t) for t in others), f"{size}/{sty}/{v}: madera de otro estilo"


# ------------------------------------------------------------------ loot
def _entries(tbl):
    for p in tbl["pools"]:
        for e in p["entries"]:
            yield p, e


def test_loot_moderate():
    for name, tbl in mines.LOOT.items():
        assert any(p.get("solo_sin_lootr") for p in tbl["pools"]), f"{name}: no 'only without Lootr' group"
        for p, e in _entries(tbl):
            obj = e.get("name", "")
            assert not any(x in obj for x in FORBIDDEN), f"{name}: {obj}"
            if obj == "minecraft:diamond":
                mods = e.get("modifier") or e.get("functions") or {}
                mods = mods if isinstance(mods, list) else [mods]
                for m in mods:
                    if m.get("type") == "minecraft:set_count":
                        assert m["count"]["max"] <= DIAMONDS_MAX


def test_loot_somewhat_better_that_vanilla():
    """The gallery rooms table rolls more times than the vanilla mine chest (2-4 valuable items and 3 of
    rails) and carries emeralds and raw ores that vanilla does not have."""
    g = mines.LOOT["galeria"]["pools"]
    assert g[1]["rolls"]["min"] >= 3 and g[1]["rolls"]["max"] >= 5
    names = {e["name"] for _, e in _entries(mines.LOOT["galeria"]) if "name" in e}
    assert {"minecraft:emerald", "minecraft:raw_iron", "minecraft:iron_ingot", "minecraft:rail"} <= names
    assert "minecraft:enchanted_golden_apple" not in names


def test_identifiable_tables_of_heraldia():
    assert set(mines.tables()) == {f"minas/{n}" for n in mines.LOOT}
    for size in mines.SIZES:
        assert audit.TABLES[size] <= set(mines.LOOT)


# ------------------------------------------------------------------ datapack
def test_what_it_writes(written):
    files, tags, lang = written
    for size in mines.SIZES:
        s = files[f"data/heraldia/worldgen/structure_set/minas/{size}.json"]
        assert len(s["structures"]) == len(mines.STYLES) * len(mines.VARIANTS)
        pl = s["placement"]
        assert pl["type"] == "heraldia:rejilla" and pl["grupo"] == f"minas/{size}" and pl["bioma"] == "heraldia:minas"
        assert pl["spacing"] == round(mines.SEPARATION[size] / 16) and pl["exclusion_zone"]["other_set"] == "minecraft:villages"
        tag = files[f"data/heraldia/tags/worldgen/structure/minas/{size}.json"]["values"]
        assert tag == [e["structure"] for e in s["structures"]]
        for e in s["structures"]:
            st = files["data/heraldia/worldgen/structure/" + e["structure"].split(":")[1] + ".json"]
            assert st["type"] == "heraldia:mina_entrada" and st["terrain_adaptation"] == "none"
            assert st["start_pool"] == e["structure"] and st["biomes"].startswith("#heraldia:minas/")
            assert len(st["entrada"]) == 3 and len(st["patio"]) == 4 and st["techo"]
    assert len(files["data/heraldia/tags/worldgen/structure/minas.json"]["values"]) == 30
    assert set(mines.structures()) == set(files["data/heraldia/tags/worldgen/structure/minas.json"]["values"])
    salts = {files[f"data/heraldia/worldgen/structure_set/minas/{t}.json"]["placement"]["salt"] for t in mines.SIZES}
    assert len(salts) == 3
    for n in mines.LOOT:
        assert f"data/heraldia/loot_table/minas/{n}.json" in files
    assert set(lang["es_es"]) == set(lang["en_us"])
    # biome tags: the one for all styles and one per style, with their optional conventional ones
    assert "data/heraldia/tags/worldgen/biome/minas.json" in tags
    for sty, d in mines.STYLES.items():
        vals = tags[f"data/heraldia/tags/worldgen/biome/minas/{sty}.json"]["values"]
        assert [v for v in vals if isinstance(v, str)] == [f"minecraft:{b}" for b in d["biomas"]]
        assert all(v["required"] is False for v in vals if isinstance(v, dict))


def test_vanilla_mines_same_values_as_26_3(written):
    files, _, _ = written
    s = files["data/minecraft/worldgen/structure_set/mineshafts.json"]
    assert [e["structure"] for e in s["structures"]] == ["minecraft:mineshaft", "minecraft:mineshaft_mesa"]
    p = dict(s["placement"])
    assert p.pop("type") == "heraldia:minas_vanilla"
    assert p == {"frequency": 0.004, "frequency_reduction_method": "legacy_type_3", "salt": 0, "separation": 0, "spacing": 1}


def test_build_registers_templates_and_pools():
    reg = Registry()
    mines.build(reg, "pequena")
    assert reg.warnings == []
    assert set(reg.templates) == {mines.template("pequena", e, v) for e in mines.STYLES for v in mines.VARIANTS}
    for name, t in reg.templates.items():
        assert t.no_generic_audit
        assert reg.pools[f"heraldia:{name}"]["elements"][0][0] == name
        assert min(t.bounds()[:3]) == 0, "normalizada"
    assert min(mines.construction("pequena", "montana", "a")[0].t.bounds()[:3]) < 0, "the cached work is not touched"


# ------------------------------------------------------------------ audit: negative cases
def _copy(size):
    import copy
    return copy.deepcopy(mines.construction(size, "montana", "a")[0])


def test_audit_detects_leak_in_the_lining():
    o = _copy("pequena")
    c = sorted(o.carved)[len(o.carved) // 2]
    for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)):
        q = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
        if q not in o.carved and q in o.t.blocks and q not in o.surface:
            o.t.clear(*q)
            break
    assert any("sin cerrar" in e for e in audit.errors(o, "pequena"))


def test_audit_detects_descent_walled_up():
    o = _copy("mediana")
    for y in range(-4, 3):
        for x in range(-1, 2):
            o.t.set(x, y, 5, "minecraft:cobblestone")
    errs = audit.errors(o, "mediana")
    assert any("inalcanzable" in e for e in errs) and any("vía" in e or "acaba" in e for e in errs)


def test_audit_detects_well_walled_up():
    o = _copy("grande")
    bx, by, bz = o.descent
    for y in range(by, by + 6):
        for dx, dz in ((0, 1), (-1, 1), (1, 1), (0, 2)):
            o.t.set(bx + dx, y, bz + dz, "minecraft:cobblestone")
    assert any("escalera de caracol" in e for e in audit.errors(o, "grande"))


def test_audit_detects_rail_without_support():
    o = _copy("pequena")
    o.t.set(0, 0, -3, "minecraft:dirt_path")
    assert any("sin apoyo" in e for e in audit.errors(o, "pequena"))


def test_audit_detects_lining_natural():
    o = _copy("pequena")
    c = sorted(o.carved)[0]
    q = (c[0], c[1] - 1, c[2])
    while q in o.carved:
        q = (q[0], q[1] - 1, q[2])
    o.t.set(*q, "minecraft:stone")
    o.surface.discard(q)
    assert any("naturales" in e for e in audit.errors(o, "pequena"))


# ------------------------------------------------------------------ options, advancements and guide
def test_options():
    sch = {o["clave"]: o for o in options.schema()["opciones"]}
    assert sch["minas.entradas.activado"]["defecto"] is True and sch["minas.entradas.activado"]["seccion"] == "minas"
    sep = sch["minas.entradas.separacion_bloques"]
    assert (sep["defecto"], sep["min"], sep["max"]) == (mines.SEPARATION["pequena"], *mines.SEPARATION_RANGE)
    mul = sch["minas.vanilla.multiplicador"]
    assert isinstance(mul["defecto"], float) and (mul["defecto"], mul["min"], mul["max"]) == mines.MULTIPLIER
    assert json.dumps(mul["defecto"]) == "2.0", "with a dot: the Java recognises it as a decimal"
    lang = options.lang()
    for k in ("minas.entradas.activado", "minas.entradas.separacion_bloques", "minas.vanilla.multiplicador"):
        assert f"heraldia.config.{k}" in lang["es_es"] and f"heraldia.config.{k}.nombre" in lang["en_us"]


def test_advancements_in_chain():
    advs, lang = advancements.build(Registry(), [], None, mines)
    assert "mina" in advs["raiz"]["criteria"]
    assert advs["minas/pequena"]["parent"] == "heraldia:raiz"
    assert advs["minas/mediana"]["parent"] == "heraldia:minas/pequena"
    assert advs["minas/grande"]["parent"] == "heraldia:minas/mediana"
    for size in mines.SIZES:
        crit = advs[f"minas/{size}"]["criteria"][size]
        assert crit["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == f"#heraldia:minas/{size}"
        assert 0 < advs[f"minas/{size}"]["rewards"]["experience"] <= 100
    assert set(lang["es_es"]) == set(lang["en_us"])
    assert advs["minas/grande"]["display"]["frame"] == "goal"


def test_guide_talks_about_mines_and_bosses():
    ids = [pid for pid, _, _ in guide.PAGES]
    assert "minas" in ids and "jefes" in ids
    assert ids.index("minas") < ids.index("unicas")
    assert guide.errors(uniques.modules()) == [], "all pages fit in both languages"
    for pid, title, text in guide.PAGES:
        if pid in ("minas", "jefes"):
            for i in (0, 1):
                assert guide.page_lines(title[i], text[i]) <= 14
    bosses = dict((p, t) for p, _, t in guide.PAGES)["jefes"]
    assert "fases" in bosses[0] and "refuerzos" in bosses[0] and "barra" in bosses[0]


def test_signs_translatable():
    from mines.surface import SIGNS
    for size, lines in SIGNS.items():
        for i in (1, 2):
            assert f"heraldia.minas.cartel.{size}.{i}" in mines.LANG["es_es"]
            assert f"heraldia.minas.cartel.{size}.{i}" in mines.LANG["en_us"]
