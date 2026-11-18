"""Faros y naufragios de la costa (costa/): plantillas de los dos tipos en los cuatro estilos y sus dos variantes (auditoría
propia y genérica, forma, la luz, el embarcadero, el agua bajo el casco), los estilos por clima (todas las parejas tierra-
mar con un solo estilo), el botín modesto y la pista del tesoro, lo que escribe en el datapack (estructuras, rejillas,
etiquetas, procesadores, botín), sus opciones, sus logros, la página de la Guía y sus textos en los 8 idiomas. Con casos
negativos de la auditoría (aire bajo el agua, la luz apagada, sin escalera) para que un cambio que lo rompa falle aquí."""
import json
import pytest
import shore as coast
import guide
import languages
import lint
import advancements
import options
import uniques
from shore import audit, constructions
from shore.chest_loot import LOOT, FORBIDDEN
from pack import Registry

ALL_COMBOS = [(t, e, v) for t in coast.KINDS for e in coast.STYLES for v in coast.VARIANTS]


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    """Lo que costa.write deja en el datapack: ({ruta: json} de jdump, {ruta: json} de las etiquetas de bioma, textos)."""
    import os
    import biomes
    previous = dict(biomes._WRITTEN)
    files, tags = {}, {}
    d = str(tmp_path_factory.mktemp("costa"))
    lang = coast.write(d, lambda _out, path, obj: files.__setitem__(path, obj))
    for root, _, fs in os.walk(d):
        for f in fs:
            with open(os.path.join(root, f), encoding="utf-8") as h:
                tags[os.path.relpath(os.path.join(root, f), d).replace(os.sep, "/")] = json.load(h)
    biomes._WRITTEN.clear()
    biomes._WRITTEN.update(previous)
    return files, tags, lang


# ------------------------------------------------------------------ plantillas
@pytest.mark.parametrize("key", ALL_COMBOS, ids=["/".join(k) for k in ALL_COMBOS])
def test_audit_of_each_variant(key):
    o, _, _ = coast.construction(*key)
    assert audit.errors(o, key[0]) == []


def test_audit_generic_of_supports():
    for kind in coast.KINDS:
        reg = Registry()
        coast.build(reg, kind)
        assert reg.warnings == []
        assert len(reg.templates) == len(coast.STYLES) * len(coast.VARIANTS)
        for name, t in reg.templates.items():
            assert lint.template_issues(t) == [], name
            assert name in [p.split(":", 1)[1] for p in reg.pools], "una pool por plantilla"
        for pid, pool in reg.pools.items():
            (_, weight, projection, proc), = pool["elements"]
            assert projection == "rigid" and proc == coast.processors(kind)


def test_the_lighthouse_es_tall_and_has_the_light_top():
    for style in coast.STYLES:
        for v in coast.VARIANTS:
            o, _, meta = coast.construction("faro", style, v)
            x0, y0, z0, x1, y1, z1 = o.t.bounds()
            assert coast.LIGHTHOUSE_HEIGHT[0] <= y1 - y0 + 1 <= coast.LIGHTHOUSE_HEIGHT[1]
            x, y, z = o.light
            assert o.t.get(x, y, z) == "minecraft:redstone_lamp[lit=true]"
            assert o.t.get(x, y - 1, z) == "minecraft:redstone_block", "siempre encendida, sin circuitos"
            assert o.t.get(x, y + 1, z) == "minecraft:glowstone"
            assert y >= 20, "visible de lejos"
            assert not any("redstone_wire" in st or "repeater" in st or "comparator" in st or "lever" in st
                           for st, _ in o.t.blocks.values()), "sin redstone compleja"
            assert meta["modo"] == "faro" and meta["fila_mar"] == -1


def test_lighthouse_house_dock_and_keeper():
    for style in coast.STYLES:
        a, _, _ = coast.construction("faro", style, "a")
        b, _, _ = coast.construction("faro", style, "b")
        for o in (a, b):
            assert any("_bed[" in st for st, _ in o.t.blocks.values()), "la casa del farero"
            assert any(st.startswith("minecraft:furnace") for st, _ in o.t.blocks.values())
            dock = [(x, z) for (x, y, z), (st, _) in o.t.blocks.items() if z > 0 and y == 0]
            assert len(dock) >= 30 and max(z for _, z in dock) == constructions.DOCK, "embarcadero sobre el mar"
            assert all(-1 <= x <= 1 for x, _ in dock), "3 de ancho"
            assert all(z < 0 for (x, y, z) in o.t.blocks if y > 2), "solo el embarcadero (y su farol) sobre el agua: lo alto, en tierra"
        assert [n["id"] for *_, n in a.t.entities] == ["minecraft:villager"], "el farero, solo en la a"
        assert b.t.entities == []
        lighthouse_keeper = a.t.entities[0][3]
        assert lighthouse_keeper["NoAI"] and lighthouse_keeper["Invulnerable"]
        sells = {r["sell"]["id"] for r in lighthouse_keeper["Offers"]["Recipes"]}
        assert {"minecraft:map", "minecraft:compass", "minecraft:spyglass"} <= sells, "tratos marinos"
        assert a.t.blocks != b.t.blocks, "dos variantes distintas"


def test_lighthouse_variants_distinct():
    a, _, _ = coast.construction("faro", "templada", "a")
    b, _, _ = coast.construction("faro", "templada", "b")
    corners_a = a.t.get(3, 5, constructions.TOWER_Z + 3)
    corners_b = b.t.get(3, 5, constructions.TOWER_Z + 3)
    assert corners_a is None and corners_b is not None, "octogonal frente a cuadrada"
    house_a = [x for (x, y, z), (st, _) in a.t.blocks.items() if "_bed[" in st]
    house_b = [x for (x, y, z), (st, _) in b.t.blocks.items() if "_bed[" in st]
    assert max(house_a) < 0 < min(house_b), "la casa a cada lado"


def test_shipwreck_without_air_underwater():
    for style in coast.STYLES:
        for v in coast.VARIANTS:
            o, (x0, y0, z0), meta = coast.construction("naufragio", style, v)
            row = o.sea_row
            assert meta["fila_mar"] == row - y0
            assert not [p for p, (st, _) in o.t.blocks.items() if p[1] <= row and st.startswith("minecraft:air")]
            assert meta["modo"] == {"a": "encallado", "b": "hundido"}[v]


def test_split_shipwreck_with_masts_and_cabin():
    for style in coast.STYLES:
        for v in coast.VARIANTS:
            o, _, _ = coast.construction("naufragio", style, v)
            z0 = o.bow
            broken = [o.t.get(x, 5, z0 + 16) for x in range(0, 4)]
            assert all(st is None for st in broken), "partido: sin cubierta en la rotura"
            assert o.t.get(4, 3, z0 + 16) is None, "y el costado de estribor abierto"
            assert o.t.get(0, 17, z0 + 12) and "_log" in o.t.get(0, 17, z0 + 12), "el mástil mayor en pie"
            sail = [st for (x, y, z), (st, _) in o.t.blocks.items() if st.endswith("_wool")]
            assert 20 <= len(sail) <= 49, "una vela rota (con agujeros)"
            tables = {str(n["LootTable"]): p for p, (st, n) in o.t.blocks.items() if n and n.get("LootTable")}
            assert set(tables) == {"heraldia:costa/camarote", "heraldia:costa/bodega"}
            assert tables["heraldia:costa/camarote"][1] > o.sea_row, "el camarote en seco"
        sunken, _, _ = coast.construction("naufragio", style, "b")
        place_chest = next(st for st, n in sunken.t.blocks.values() if n and str(n.get("LootTable")).endswith("bodega"))
        assert "waterlogged=true" in place_chest, "la bodega inundada"
        drowned_list = [n for *_, n in sunken.t.entities if n["id"] == "minecraft:drowned"]
        assert len(drowned_list) == 1, "un ahogado como mucho"
        assert {"heraldia_anclado", "heraldia_adulto"} <= set(drowned_list[0]["Tags"])
        beached, _, _ = coast.construction("naufragio", style, "a")
        assert beached.t.entities == [], "el encallado, sin nadie"


def test_fingerprints_for_java():
    for key in ALL_COMBOS:
        o, (x0, y0, z0), meta = coast.construction(*key)
        ax, az = meta["ancla"]
        assert (ax + x0, az + z0) == o.anchor_point == (0, 0)
        tx0, tz0, tx1, tz1 = meta["tierra"]
        mx0, mz0, mx1, mz1 = meta["mar"]
        assert tz1 < 0 < mz0, "tierra detrás del ancla, mar delante"
        bx0, _, bz0, bx1, _, bz1 = o.t.bounds()
        assert bx0 <= tx0 and tx1 <= bx1 and bx0 <= mx0 and mx1 <= bx1
        assert mz1 <= bz1, "el mar que se mira está dentro de la plantilla"
        if key[0] == "faro":
            assert (tx0, tz0, tx1, tz1) == (bx0, bz0, bx1, -1), "toda la plataforma en tierra"


def test_processor_drops_just_enough():
    lighthouse, ship = coast.descend("faro"), coast.descend("naufragio")
    assert not any("planks" in b for b in lighthouse), "los tablones del embarcadero no bajan"
    assert any("planks" in b for b in ship), "el fondo del casco sí"
    for d in coast.STYLES.values():
        assert f"minecraft:{d['faro']['tronco']}" in lighthouse, "los pilotes"
        assert f"minecraft:{d['barco']['tronco']}" in ship, "la quilla"
        assert f"minecraft:{d['faro']['madera']}_planks" not in lighthouse


# ------------------------------------------------------------------ estilos y climas
def test_each_pair_of_climate_has_a_only_style():
    land = [b for g in coast.LAND.values() for b in g]
    assert len(land) == len(set(land)), "cada bioma de tierra en un grupo"
    for g, biomes in coast.LAND.items():
        for b in biomes:
            for m in coast.SEA["todos"]:
                styles = [e for e, d in coast.STYLES.items()
                           if any(b in coast.LAND[t] and m in coast.SEA[mm] for t, mm in d["climas"])]
                assert len(styles) == 1, (b, m, styles)
    assert set(coast.BEACHES) <= set(land)


def test_styles_according_to_the_coast():
    def style(land, sea):
        return next(e for e, d in coast.STYLES.items()
                    if any(land in coast.LAND[t] and sea in coast.SEA[m] for t, m in d["climas"]))
    assert style("beach", "ocean") == "templada"
    assert style("beach", "warm_ocean") == "calida"
    assert style("desert", "ocean") == "calida"
    assert style("stony_shore", "ocean") == "fria"
    assert style("beach", "cold_ocean") == "fria"
    assert style("snowy_beach", "frozen_ocean") == "nevada"
    assert style("snowy_beach", "warm_ocean") == "nevada"
    pal = coast.STYLES
    assert "stone" in pal["templada"]["faro"]["muro"] or "brick" in pal["templada"]["faro"]["muro"]
    assert "sandstone" in pal["calida"]["faro"]["muro"]
    assert "deepslate" in pal["fria"]["faro"]["muro"]
    assert "spruce" in pal["nevada"]["faro"]["muro"] and pal["nevada"]["faro"]["nieve"]


def test_style_materials():
    for style, d in coast.STYLES.items():
        o, _, _ = coast.construction("faro", style, "a")
        assert any(st.startswith(f"minecraft:{d['faro']['muro']}") for st, _ in o.t.blocks.values())
        n, _, _ = coast.construction("naufragio", style, "a")
        assert any(st.startswith(f"minecraft:{d['barco']['madera']}_planks") for st, _ in n.t.blocks.values())
        snow = any(st.startswith("minecraft:snow[") for st, _ in o.t.blocks.values())
        assert snow == d["faro"]["nieve"], style


# ------------------------------------------------------------------ botín
def _items(tbl):
    out = []
    for p in tbl["pools"]:
        for e in p["entries"]:
            if e.get("type") == "minecraft:item":
                out.append(e["name"])
    return out


def test_loot_modest():
    for name, tbl in LOOT.items():
        for o in _items(tbl):
            assert not any(x in o for x in FORBIDDEN), (name, o)
        assert tbl["pools"][-1].get("solo_sin_lootr"), "el grupo extra, solo sin Lootr"
    assert {"minecraft:map", "minecraft:compass", "minecraft:spyglass"} <= set(_items(LOOT["faro"]))
    assert "minecraft:map" in _items(LOOT["camarote"])


def test_what_it_writes(written):
    files, tags, lang = written
    for kind in coast.KINDS:
        s = files[f"data/heraldia/worldgen/structure_set/costa/{kind}.json"]
        p = s["placement"]
        assert p["type"] == "heraldia:rejilla" and p["grupo"] == f"costa/{kind}"
        assert p["spacing"] == round(coast.SEPARATION[kind] / 16) and p["bioma"] == "heraldia:litoral"
        assert p["bioma_vecinos"] == coast.BIOME_NEIGHBORS
        assert len(s["structures"]) == len(coast.STYLES) * len(coast.VARIANTS)
        assert files[f"data/heraldia/tags/worldgen/structure/costa/{kind}.json"]["values"] == [e["structure"] for e in s["structures"]]
        proc = files[f"data/heraldia/worldgen/processor_list/costa/{kind}_suelo.json"]["processors"][0]
        assert proc["processor_type"] == "heraldia:acueducto_hasta_el_suelo" and proc["bloques"] == coast.descend(kind)
    assert len(files["data/heraldia/tags/worldgen/structure/costa.json"]["values"]) == 16
    e = files["data/heraldia/worldgen/structure/costa/naufragio/fria/b.json"]
    assert e["type"] == "heraldia:costa" and e["modo"] == "hundido" and e["terrain_adaptation"] == "none"
    assert e["biomes"] == "#heraldia:litoral/fria" and e["step"] == "surface_structures"
    assert {"tierra": "#heraldia:litoral/tierra/rocosa", "mar": "#heraldia:litoral/mar/no_calido"} in e["climas"]
    for t in ("faro", "bodega", "camarote"):
        assert f"data/heraldia/loot_table/costa/{t}.json" in files
    cabin = files["data/heraldia/loot_table/costa/camarote.json"]
    clues = [p for p in cabin["pools"] if any("tesoro/fragmento" in json.dumps(x) for x in p["entries"])]
    assert len(clues) == 1, "una pista del tesoro en el camarote"
    assert clues[0]["condition"]["factor"] == 0.5, "rara: la mitad que en una mediana"
    for t in ("faro", "bodega"):
        assert "tesoro/fragmento" not in json.dumps(files[f"data/heraldia/loot_table/costa/{t}.json"])
    assert tags["data/heraldia/tags/worldgen/biome/litoral.json"]["values"] == [f"minecraft:{b}" for b in coast.BEACHES]
    assert "data/heraldia/tags/worldgen/biome/costa.json" not in tags, "la de la familia de aldeas de la costa, intacta"
    for style in coast.STYLES:
        assert f"data/heraldia/tags/worldgen/biome/litoral/{style}.json" in tags
    assert lang["es_es"]["heraldia.costa.faro.nombre"] == "Faro"


def test_tables_and_structures():
    assert set(coast.tables()) == {f"costa/{t}" for t in LOOT}
    assert len(coast.structures()) == 16 and all(s.startswith("heraldia:costa/") for s in coast.structures())


# ------------------------------------------------------------------ opciones, logros, guía, idiomas
def test_options():
    keys = {k: (d, lo, hi) for k, d, lo, hi, *_ in options._FIXED}
    for kind, o in coast.OPTION.items():
        assert keys[f"{o}.activado"][0] is True
        d, lo, hi = keys[f"{o}.separacion_bloques"]
        assert d == coast.SEPARATION[kind] and (lo, hi) == coast.SEPARATION_RANGE
        assert options.is_generation(f"{o}.activado"), "no lo cambia un perfil"
    assert keys["mapas_web.capas.costa"][0] is True


def test_advancements():
    reg = Registry()
    advs, lang = advancements.build(reg, uniques.modules(), None, None, coast)
    assert advs["raiz"]["criteria"]["costa"]["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == "#heraldia:costa"
    for t in ("faro", "naufragio"):
        crit = advs[f"costa/{t}"]["criteria"][t]
        assert crit["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == f"#heraldia:costa/{t}"
        assert advs[f"costa/{t}"]["parent"] == "heraldia:raiz"
    cabin_adv = advs["costa/camarote"]
    assert cabin_adv["parent"] == "heraldia:costa/naufragio"
    assert cabin_adv["criteria"]["camarote"]["conditions"]["loot_tables"] == "heraldia:costa/camarote"
    for p in ("faro", "naufragio", "camarote"):
        assert f"advancements.heraldia.costa.{p}.title" in lang["es_es"]


def test_guide_page():
    ids = [pid for pid, _, _ in guide.PAGES]
    assert "costa" in ids and ids.index("minas") < ids.index("costa") < ids.index("unicas")
    assert "costa" in guide.dataset(uniques.modules())["paginas"]
    assert guide.errors(uniques.modules()) == []


@pytest.mark.parametrize("lang_code", list(languages.TRANSLATIONS))
def test_texts_in_the_8_languages(lang_code):
    import writer
    es = dict(coast.lang()["es_es"])
    es.update({k: v for k, v in guide.lang()["es_es"].items() if ".costa" in k})
    with open(languages.route(lang_code), encoding="utf-8") as f:
        translated = json.load(f)
    for k, v in es.items():
        assert k in translated, (lang_code, k)
        assert translated[k].count("%s") == v.count("%s"), (lang_code, k)
    import admin
    for k in admin.lang()["es_es"]:
        if "costa" in k:
            assert k in translated, (lang_code, k)
    for k in ("faros.activado", "naufragios.separacion_bloques", "mapas_web.capas.costa"):
        assert f"heraldia.config.{k}" in translated and f"heraldia.config.{k}.nombre" in translated
    assert guide.errors(uniques.modules(), {lang_code: translated}) == []


# ------------------------------------------------------------------ casos negativos de la auditoría
def _copy(o):
    from types import SimpleNamespace
    from core import Template
    t = Template(o.t.name)
    t.blocks, t.entities = dict(o.t.blocks), list(o.t.entities)
    return SimpleNamespace(**{**vars(o), "t": t})


def test_audit_detects_air_under_the_water():
    o = _copy(coast.construction("naufragio", "templada", "b")[0])
    o.t.set(0, 2, o.bow + 6, "air")
    assert any("aire bajo el agua" in e for e in audit.errors(o, "naufragio"))


def test_audit_detects_the_light_off():
    o = _copy(coast.construction("faro", "templada", "a")[0])
    x, y, z = o.light
    o.t.set(x, y - 1, z, "stone_bricks")
    assert any("luz" in e for e in audit.errors(o, "faro"))


def test_audit_detects_staircase_cut():
    o = _copy(coast.construction("faro", "fria", "b")[0])
    o.t.set(0, 9, constructions.TOWER_Z + 2, "air")
    assert any("escalera" in e for e in audit.errors(o, "faro"))


def test_audit_detects_drowned_loose():
    o = _copy(coast.construction("naufragio", "nevada", "b")[0])
    o.t.entities = [(0, 2, 10, {"id": "minecraft:drowned", "PersistenceRequired": 1})]
    assert any("sin anclar" in e for e in audit.errors(o, "naufragio"))
