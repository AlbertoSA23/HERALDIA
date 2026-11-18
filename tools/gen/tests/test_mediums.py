"""Medium structures (medianas/): contract of each type, built templates (generic lint audit, size,
entrance, entities, modest loot, lifeless floor), what it writes to the datapack, its options and its advancements. With negative
contract cases (medianas.errores) so that a new medium structure that does not meet it fails here in seconds."""
import json
import pytest
import core
import lint
import advancements
import mediums
import options
import uniques
from core import Template
from loot import item
from pack import Registry
from uniques._common import chest_loot

MODS = mediums.modules()
IDS = [mid for mid, _ in MODS]


@pytest.fixture(scope="module")
def reg():
    r = Registry()
    for mid in IDS:
        mediums.build(r, mid)
    return r


BATCH_1 = ["campamento", "ermita", "posada", "torre_vigia"]
BATCH_2 = ["cazadores", "molino", "pescador", "templete"]
NETHER = ["altar_magma", "atalaya_basalto", "puesto_piglin", "santuario_hongos"]      # T44 (test_nether_end.py)
END = ["embarcadero_shulker", "mausoleo_purpura", "observatorio_vacio"]
HUTS = ["choza_mago"]                 # T43: the wizard huts


def test_batches_and_discovery():
    assert IDS == sorted(IDS) == sorted(BATCH_1 + BATCH_2 + HUTS + NETHER + END)
    assert not any(m.startswith("_") for m in IDS)


def test_salt_stable_and_distinct_of_the_uniques():
    import zlib
    assert mediums.salt("posada") == zlib.crc32(b"heraldia:medianas/posada") & 0x7FFFFFFF
    salts = {mediums.salt(m) for m in IDS}
    assert len(salts) == len(IDS) and not salts & {uniques.salt(s) for s, _ in uniques.modules()}


@pytest.mark.parametrize("mid, m", MODS, ids=IDS)
def test_contract(mid, m):
    assert m.DISPLAY_NAME["es_es"] and m.DISPLAY_NAME["en_us"]
    assert mediums.SEPARATION_RANGE[0] <= m.SEPARATION <= mediums.SEPARATION_RANGE[1]
    assert len(m.STYLES) >= 2
    for style, d in m.STYLES.items():
        assert d["biomas"] and len(d["variantes"]) >= 2, style
    assert "premium" not in m.LOOT
    lang = getattr(m, "LANG", {})
    assert set(lang.get("es_es", {})) == set(lang.get("en_us", {}))


def test_built_without_warnings(reg):
    assert reg.warnings == []
    assert len([n for n in reg.templates if n.startswith("medianas/")]) == sum(
        len(d["variantes"]) for _, m in MODS for d in m.STYLES.values())


@pytest.mark.parametrize("mid", IDS)
def test_audit_generic_and_walkthrough(reg, mid):
    for name, t in reg.templates.items():
        if not name.startswith(f"medianas/{mid}/"):
            continue
        assert lint.template_issues(t) == [], name
        cells = lint.walk(t)
        # one enters by the north face and reaches all the containers (access_issues) and a good part of the courtyard
        assert len(cells) > 100, name


def test_entities_marked_persistent_and_anchored(reg):
    mobs = 0
    for name, t in reg.templates.items():
        for *_, n in t.entities:
            tags = n["Tags"]
            mid = name.split("/")[1]
            assert mediums.MARK in tags and f"{mediums.MARK}.{mid}" in tags, name
            assert n["PersistenceRequired"] == 1
            if n["id"] != "minecraft:villager":
                mobs += 1
                assert core.ANCHORED_TAG in tags, name
    # camp: 2 in each of its 6 templates; tall tower (2 styles): the archer; fisherman a (3 styles): the cat;
    # hunters a (2 styles): the wolf; gazebo a (2 styles): two custodians
    # T44: piglin outpost (2 renegades in a and 1 in b, 2 styles), broken altar (2 magma cubes, 2 styles), watchtower
    # whole (the lookout, 2 styles) and pier a (the shulker, 2 styles)
    # wizard hut a (6 styles): the cat
    assert mobs == 2 * 6 + 1 * 2 + 1 * 3 + 1 * 2 + 2 * 2 + 3 * 2 + 2 * 2 + 1 * 2 + 1 * 2 + 1 * 6


def test_bandits_without_patrol(reg):
    for name, t in reg.templates.items():
        if name.startswith("medianas/campamento/"):
            for *_, n in t.entities:
                assert n["PatrolLeader"] == 0 and n["Patrolling"] == 0 and n["CanJoinRaid"] == 0


def test_innkeeper_with_fixed_trades(reg):
    t = reg.templates["medianas/posada/llanura/a"]
    (v,) = [n for *_, n in t.entities if n["id"] == "minecraft:villager"]
    assert v["NoAI"] == 1 and v["Invulnerable"] == 1
    sales = [o["sell"]["id"] for o in v["Offers"]["Recipes"]]
    assert "minecraft:white_bed" in sales and "minecraft:bread" in sales


def test_hermitage_diary_translatable():
    from mediums import hermitage
    tbl = hermitage.LOOT["celda"]
    written_book = tbl["pools"][0]["entries"][0]
    comp = written_book["modifier"][0]["components"]["minecraft:written_book_content"]
    assert all(p["raw"]["translate"].startswith("heraldia.medianas.ermita.diario.") for p in comp["pages"])
    for k in ("heraldia.medianas.ermita.diario.p1", "heraldia.medianas.ermita.diario.p2"):
        assert k in hermitage.LANG["es_es"] and k in hermitage.LANG["en_us"]


# ---------------------------------------------------------------- negative contract cases
class _Fake:
    DISPLAY_NAME = {"es_es": "Falsa", "en_us": "Fake"}
    SEPARATION = 600
    LOOT = {"cofre": chest_loot.place_chest(((1, 1), [item("bread", 1)]), ((1, 1), [item("emerald", 1)]))}

    @staticmethod
    def fine(p, name):
        t = Template(name)
        from mediums import _common as c
        c.courtyard(t, 0, 0, 12, 12, "minecraft:dirt_path")
        c.entrance(t, 6, "minecraft:dirt_path")
        c.place_chest(t, 6, 1, 6, "north", "falsa", "cofre")
        return t

    STYLES = {"x": dict(biomas=["plains"], paleta={}, variantes={"a": fine})}


def _errors(mod, change=None):
    r = Registry()
    t = mod.fine({}, mediums.template("falsa", "x", "a"))
    if change:
        change(t)
    mediums.mark_entities(t, "falsa")
    r.add(t, "mediana:falsa")
    return mediums.errors(r, "falsa", mod)


def test_contract_valid():
    assert _errors(_Fake) == []


@pytest.mark.parametrize("change, text", [
    (lambda t: t.fill(0, 0, 0, 12, 0, 12, "grass_block"), "fertile ground"),
    (lambda t: [t.entity(1, 1, 1, {"id": "minecraft:pillager", "PersistenceRequired": core.B(1)}) for _ in range(5)],
     "entities"),
    (lambda t: t.entity(1, 1, 1, {"id": "minecraft:pillager"}), "PersistenceRequired"),
    (lambda t: (t.set(1, 1, 1, "spawner"), t.set(2, 1, 1, "spawner")), "spawners"),
    (lambda t: t.fill(0, 0, 0, 45, 0, 0, "dirt_path"), "size 46"),
    (lambda t: t.jigsaws.clear(), "entrada"),
    (lambda t: t.chest(3, 1, 3, "north", "heraldia:unicas/castillo/premium"), "not from its LOOT"),
])
def test_contract_detects(change, text):
    errs = _errors(_Fake, change)
    assert any(text in e for e in errs), errs


def test_loot_premium_and_forbidden():
    class Rich(_Fake):
        LOOT = {"cofre": chest_loot.place_chest(((1, 1), [item("diamond_sword", 1)]), ((1, 1), [item("emerald", 1)])),
                "premium": chest_loot.place_chest(((1, 1), [item("bread", 1)]), ((1, 1), [item("bread", 1)]))}
    errs = _errors(Rich)
    assert any("is not modest loot" in e for e in errs)
    assert any("no premium chest" in e for e in errs)
    assert any("table premium is not used by any container" in e for e in errs)


def test_no_name_and_separation_out_of_range():
    class Bad(_Fake):
        DISPLAY_NAME = {"es_es": "Mala"}
        SEPARATION = 100
    errs = _errors(Bad)
    assert any("NOMBRE" in e for e in errs) and any("SEPARACION" in e for e in errs)


# ---------------------------------------------------------------- datapack, options and advancements
def test_write(tmp_path):
    files = {}
    mediums.write(str(tmp_path), lambda out, rel, obj: files.__setitem__(rel, obj))
    for mid, m in MODS:
        st = files[f"data/heraldia/worldgen/structure_set/medianas/{mid}.json"]
        pl = st["placement"]
        assert pl["type"] == "heraldia:rejilla" and pl["grupo"] == f"medianas/{mid}" and pl["salt"] == mediums.salt(mid)
        if mediums.dimension(m) == "overworld":        # those of the Nether and the End: test_nether_end.py
            assert pl["exclusion_zone"]["other_set"] == "minecraft:villages"
            assert pl["bioma"] == f"heraldia:medianas/{mid}" and pl["bioma_y"] == mediums.BIOME_Y
        union = json.loads((tmp_path / f"data/heraldia/tags/worldgen/biome/medianas/{mid}.json").read_text())["values"]
        assert {v for v in union if isinstance(v, str)} == {f"minecraft:{b}" for d in m.STYLES.values() for b in d["biomas"]}
        assert 0 < pl["separation"] < pl["spacing"] == round(m.SEPARATION / 16)
        assert pl.get("bioma_vecinos") == getattr(m, "BIOME_NEIGHBORS", None)
        assert [e["structure"] for e in st["structures"]] == [f"heraldia:medianas/{mid}/{e}" for e in m.STYLES]
        for style in m.STYLES:
            s = files[f"data/heraldia/worldgen/structure/medianas/{mid}/{style}.json"]
            assert s["biomes"] == f"#heraldia:medianas/{mid}/{style}"
            assert s["start_pool"] == f"heraldia:medianas/{mid}/{style}" and s["terrain_adaptation"] == "beard_thin"
            assert (tmp_path / f"data/heraldia/tags/worldgen/biome/medianas/{mid}/{style}.json").exists()
        for tbl in m.LOOT:
            assert f"data/heraldia/loot_table/medianas/{mid}/{tbl}.json" in files
    all_items = files["data/heraldia/tags/worldgen/structure/medianas.json"]["values"]
    assert len(all_items) == sum(len(m.STYLES) for _, m in MODS)


def test_biomes_conventional_valid():
    """The extra tags of each style resolve in vanilla to a subset of their list (like biomas.comprobar)."""
    import biomes
    tags = biomes.conventional()
    for mid, m in MODS:
        for style, d in m.STYLES.items():
            lst = {b if ":" in b else f"minecraft:{b}" for b in d["biomas"]}
            for c in d.get("convencionales", []):
                if c.startswith("c:"):
                    vals = tags[c[2:]]
                    direct_ids = {v for v in vals if isinstance(v, str) and not v.startswith("#")}
                    assert direct_ids <= lst, (mid, style, c)


def test_options():
    sch = options.schema()
    keys = {o["clave"]: o for o in sch["opciones"]}
    for k in ("medianas.activadas", "medianas.frecuencia_porcentaje", "medianas.distancia_minima.bloques",
              "medianas.distancia_aldeas_unicas_bloques"):
        assert keys[k]["seccion"] == "medianas"
    for mid, m in MODS:
        o = keys[f"medianas.{mid}.separacion_bloques"]
        assert o["defecto"] == m.SEPARATION and (o["min"], o["max"]) == mediums.SEPARATION_RANGE
        assert o["args_nombre"] == [f"heraldia.medianas.{mid}.nombre"]
        assert keys[f"medianas.{mid}.activada"]["defecto"] is True
    assert "medianas" in [s["id"] for s in sch["secciones"]]
    lang = options.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])


def test_advancements(reg):
    advs, lang = advancements.build(reg, [], MODS)
    assert set(advs["raiz"]["criteria"]) == {"aldea", "unica", "mediana"}
    all_items = advs["medianas/todas"]
    assert all_items["parent"] == "heraldia:medianas/descubrir" and all_items["requirements"] == [[m] for m in sorted(BATCH_1 + BATCH_2 + HUTS)]
    assert all_items["criteria"]["posada"]["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == "#heraldia:medianas/posada"
    assert set(lang["es_es"]) == set(lang["en_us"])


def test_texts():
    lang = mediums.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])
    for mid, m in MODS:
        assert lang["en_us"][mediums.key_name(mid)] == m.DISPLAY_NAME["en_us"]
    json.dumps(lang)


# ---------------------------------------------------------------- lote 2: molino, pescador, cazadores, templete
def _entities(reg, mid):
    return {name: [n for *_, n in t.entities] for name, t in reg.templates.items() if name.startswith(f"medianas/{mid}/")}


def test_batch_2_styles_and_underserved_biomes():
    """Each new type has several styles, 2 variants in each one and biomes that batch 1 did not have (or almost)."""
    batch_1 = {b for mid, m in MODS if mid in BATCH_1 for d in m.STYLES.values() for b in d["biomas"]}
    for mid, m in MODS:
        if mid not in BATCH_2:
            continue
        assert len(m.STYLES) >= 2 and all(len(d["variantes"]) == 2 for d in m.STYLES.values()), mid
        new_items = {b for d in m.STYLES.values() for b in d["biomas"]} - batch_1
        assert new_items, mid
    new_items = {b for mid, m in MODS if mid in BATCH_2 for d in m.STYLES.values() for b in d["biomas"]} - batch_1
    assert {"swamp", "beach", "snowy_beach", "stony_shore", "snowy_plains", "ice_spikes", "jungle", "desert"} <= new_items


@pytest.mark.parametrize("mid", BATCH_2)
def test_batch_2_size(reg, mid):
    for name, t in reg.templates.items():
        if name.startswith(f"medianas/{mid}/"):
            sx, _, sz = t.size()
            assert 15 <= sx <= 21 and 15 <= sz <= 21, (name, sx, sz)


def test_villagers_of_the_batch_2_with_trades_fixed(reg):
    expected = {"molino": ("farmer", "minecraft:bread"), "pescador": ("fisherman", "minecraft:fishing_rod"),
                "cazadores": ("leatherworker", "minecraft:leather_chestplate")}
    for mid, (depth, sells) in expected.items():
        for name, ns in _entities(reg, mid).items():
            vs = [n for n in ns if n["id"] == "minecraft:villager"]
            if name.endswith("/a"):
                (v,) = vs
                assert v["NoAI"] == 1 and v["Invulnerable"] == 1, name
                assert v["VillagerData"]["profession"] == f"minecraft:{depth}", name
                assert sells in [o["sell"]["id"] for o in v["Offers"]["Recipes"]], name
            else:
                assert vs == [], name


def test_animals_and_custodians_of_the_batch_2(reg):
    for name, ns in _entities(reg, "pescador").items():
        cats = [n for n in ns if n["id"] == "minecraft:cat"]
        assert len(cats) == (1 if name.endswith("/a") else 0), name
    for name, ns in _entities(reg, "cazadores").items():
        assert len([n for n in ns if n["id"] == "minecraft:wolf"]) == (1 if name.endswith("/a") else 0), name
    for name, ns in _entities(reg, "templete").items():
        if name.endswith("/b"):
            assert ns == [], name
            continue
        assert len(ns) == 2, name
        for n in ns:
            assert n["id"] in ("minecraft:skeleton", "minecraft:husk"), name
            if n["id"] == "minecraft:husk":
                assert core.ADULT_TAG in n["Tags"], name       # no baby comes out
            else:
                assert n["equipment"]["head"]["id"] == "minecraft:chainmail_helmet", name   # does not burn in daylight


def test_water_still_and_contained(reg):
    """The water of the medium structures (mill race, wheat field, irrigation ditches, gazebo well) is all source and has no
    open side face inside the template: it does not flow."""
    for name, t in reg.templates.items():
        if not name.startswith("medianas/"):
            continue
        for (x, y, z), (st, _) in t.blocks.items():
            if lint.bname(st) != "water":
                continue
            assert "level=0" in st, (name, (x, y, z))
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = t.get(x + dx, y, z + dz)
                if neighbor is None:
                    assert y == 0, (name, (x, y, z), "water on the terrain, next to the void")
                    continue
                assert lint.bname(neighbor) == "water" or not lint.passable(neighbor), (name, (x, y, z), neighbor)
            below = t.get(x, y - 1, z)
            assert y == 0 or (below and not lint.passable(below)), (name, (x, y, z))


def test_mill_wheel_and_blades(reg):
    a = reg.templates["medianas/molino/llanura/a"]
    assert sum(1 for (x, _, _), (st, _) in a.blocks.items() if x == 12 and st == "minecraft:oak_planks") == 16  # aro
    assert a.get(12, 0, 9).startswith("minecraft:water")              # the wheel wets in the race
    b = reg.templates["medianas/molino/llanura/b"]
    tarp = [p for p, (st, _) in b.blocks.items() if st == "minecraft:white_wool"]
    assert len(tarp) == 16 and all(z == 12 for _, _, z in tarp)       # four sails on the south face


def test_dock_of_the_fisherman(reg):
    for v, length in (("a", 17), ("b", 20)):
        t = reg.templates[f"medianas/pescador/playa/{v}"]
        tables = [z for (x, y, z), (st, _) in t.blocks.items() if y == 1 and x == 12 and st == "minecraft:birch_planks"]
        assert max(tables) == length and min(tables) == 6


def test_shrine_broken_columns_and_architrave(reg):
    from mediums import shrine as tp
    t = reg.templates["medianas/templete/desierto/a"]
    for x in range(tp.P0, tp.P1 + 1):
        for z in (tp.P0, tp.P1):
            assert t.get(x, 7, z) is not None          # whole architrave to the north and south
    broken_ones = {(x, z): max(y for (xx, y, zz), (st, _) in t.blocks.items() if (xx, zz) == (x, z) and st != "minecraft:air")
             for x in (tp.P0, tp.P1)
             for z in range(tp.P0 + 2, tp.P1 - 1, 2)}
    assert all(h < 7 for h in broken_ones.values()) and len(set(broken_ones.values())) > 1


def test_jars_with_loot(reg):
    t = reg.templates["medianas/templete/jungla/b"]
    jars = [nbt for (st, nbt) in t.blocks.values() if st.startswith("minecraft:decorated_pot") and nbt and nbt.get("LootTable")]
    assert len(jars) == 2 and all(n["LootTable"] == "heraldia:medianas/templete/vasija" for n in jars)


def test_advancements_own_to_batch_2(reg):
    advs, lang = advancements.build(reg, [], MODS)
    for mid, m in MODS:
        for ex in getattr(m, "ADVANCEMENTS", ()):
            adv = advs[f"medianas/{mid}/{ex['id']}"]
            assert adv["parent"] == "heraldia:medianas/descubrir"
            assert adv["rewards"]["experience"] == advancements.XP["mediana_extra"]
            k = f"advancements.heraldia.medianas.{mid}.{ex['id']}.title"
            assert lang["es_es"][k] == ex["titulo"][0] and lang["en_us"][k] == ex["titulo"][1]
            if ex.get("tabla"):
                (crit,) = adv["criteria"].values()
                assert crit["conditions"]["loot_tables"] == f"heraldia:medianas/{mid}/{ex['tabla']}"
    assert {p for p in advs if p.startswith("medianas/") and p.count("/") == 2} == {
        "medianas/molino/molienda", "medianas/pescador/pesca", "medianas/cazadores/pieles", "medianas/templete/custodios",
        "medianas/choza_mago/tratos", "medianas/choza_mago/malvado",
        "medianas/puesto_piglin/renegados", "medianas/santuario_hongos/ofrendas"}      # the last two, from the Nether (T44)
    keepers = advs["medianas/templete/custodios"]["criteria"]
    assert set(keepers) == {"skeleton", "husk"}
    assert keepers["husk"]["conditions"]["entity"]["predicate"]["minecraft:entity_tags"] == {"all_of": ["heraldia_mediana.templete"]}


def test_advancement_badly_defined():
    class WithAdvancement(_Fake):
        ADVANCEMENTS = [dict(id="x", icono="minecraft:cod", titulo=("a", "b"), descripcion=("c", "d"), tabla="no_existe"),
                  dict(id="y", icono="minecraft:cod", titulo=("a", "b"))]
    errs = _errors(WithAdvancement)
    assert any("which is not in LOOT" in e for e in errs) and any("advancement 'y'" in e for e in errs)


def test_biome_neighbors_only_in_the_fisherman_and_in_range():
    """Beaches are strips: only the fisherman asks for fewer neighbours in the biome search of its grid."""
    assert {mid: m.BIOME_NEIGHBORS for mid, m in MODS if hasattr(m, "BIOME_NEIGHBORS")} == {"pescador": 2}

    class Strip(_Fake):
        BIOME_NEIGHBORS = 0
    assert any("BIOMA_VECINOS" in e for e in _errors(Strip))


def test_only_the_huts_yield_to_the_mines(tmp_path):
    """The wizard huts look for the interior of the same biomes as the mines: they yield (tag for the Java)."""
    assert mediums.yield_to_mines() == [f"heraldia:medianas/choza_mago/{e}" for e in dict(MODS)["choza_mago"].STYLES]
    assert all(not getattr(m, "YIELDS_TO_MINES", False) for mid, m in MODS if mid != "choza_mago")
    assert mediums.YIELD_TO_MINES == "medianas/ceden_a_minas"
