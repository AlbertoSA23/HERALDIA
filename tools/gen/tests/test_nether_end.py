"""Contenido del Nether y el End (T44, dimensiones.py): las medianas y las únicas con DIMENSION, sus plantillas (auditoría
genérica, recorrido, guardián, trampa, sala oculta), lo que escriben (tipo heraldia:dimension, rejilla sin búsqueda de
bioma ni zona de aldeas vanilla), su botín (lista prohibida, fragmentos de netherita), que no llevan mapa del tesoro,
sus logros y sus textos en los 8 idiomas."""
import json
import pytest
import dimensions
import languages
import lint
import advancements
import maps
import mediums
import trades
import uniques
import writer
from pack import Registry, _part
from uniques._common import chest_loot

MEDIUM_MODULES = [(mid, m) for mid, m in mediums.modules() if dimensions.dimension_of(m) != dimensions.MAIN]
UNIQUE_MODS = [(sid, m) for sid, m in uniques.modules() if dimensions.dimension_of(m) != dimensions.MAIN]
NETHER_MED = {"puesto_piglin", "altar_magma", "atalaya_basalto", "santuario_hongos"}
END_MED = {"observatorio_vacio", "mausoleo_purpura", "embarcadero_shulker"}


@pytest.fixture(scope="module")
def reg():
    r = Registry()
    for mid, _ in MEDIUM_MODULES:
        mediums.build(r, mid)
    return r


@pytest.fixture(scope="module")
def reg_stub():
    return {sid: _part(("unica", sid), 2026) for sid, _ in UNIQUE_MODS}


def test_batches_per_dimension():
    assert {mid for mid, m in MEDIUM_MODULES if dimensions.dimension_of(m) == "nether"} == NETHER_MED
    assert {mid for mid, m in MEDIUM_MODULES if dimensions.dimension_of(m) == "end"} == END_MED
    assert {sid: dimensions.dimension_of(m) for sid, m in UNIQUE_MODS} == {"ciudadela_ceniza": "nether", "sagrario_vacio": "end"}


@pytest.mark.parametrize("mid, m", MEDIUM_MODULES, ids=[m for m, _ in MEDIUM_MODULES])
def test_biomes_of_its_dimension(mid, m):
    """Cada estilo, en biomas de su dimensión; en el End, solo las islas exteriores (ni the_end ni small_end_islands)."""
    dim = dimensions.dimension_of(m)
    for style, d in m.STYLES.items():
        assert d["biomas"] and set(d["biomas"]) <= set(dimensions.BIOME_MAP[dim]), (mid, style)
    assert len(m.STYLES) >= 2


def test_biomes_of_the_uniques():
    for sid, m in UNIQUE_MODS:
        bs = {b.split(":")[1] for b in m.STRUCTURE["biomes"]}
        assert bs <= set(dimensions.BIOME_MAP[dimensions.dimension_of(m)]), sid
        assert "the_end" not in bs and "small_end_islands" not in bs


def test_templates_without_warnings(reg):
    assert reg.warnings == []
    assert len(reg.templates) == sum(len(d["variantes"]) for _, m in MEDIUM_MODULES for d in m.STYLES.values())


@pytest.mark.parametrize("mid", [m for m, _ in MEDIUM_MODULES])
def test_audit_and_courtyard_without_floor_live(reg, mid):
    for name, t in reg.templates.items():
        if not name.startswith(f"medianas/{mid}/"):
            continue
        assert lint.template_issues(t) == [], name
        assert len(lint.walk(t)) > 100, name
        # ni nilio, ni netherrack, ni arena de almas, ni piedra del End a la vista en el patio (dimensiones.SUELO_VIVO)
        for (x, y, z), (st, _) in t.blocks.items():
            if y == 0:
                assert st.split("[")[0] not in dimensions.LIVE_FLOOR, (name, (x, z), st)


def test_live_floor_detected():
    from core import Template
    t = Template("x")
    t.set(0, 0, 0, "crimson_nylium")
    t.normalize()
    assert any("suelo fértil" in e for e in mediums.template_errors(t, "x", {}, "nether"))
    assert not any("suelo fértil" in e for e in mediums.template_errors(t, "x", {}, "overworld"))


def test_write_kind_dimension(tmp_path):
    files = {}
    mediums.write(str(tmp_path), lambda out, rel, obj: files.__setitem__(rel, obj))
    for mid, m in MEDIUM_MODULES:
        pl = files[f"data/heraldia/worldgen/structure_set/medianas/{mid}.json"]["placement"]
        assert pl["type"] == "heraldia:rejilla" and pl["grupo"] == f"medianas/{mid}"
        # sin búsqueda de bioma (solo lee el ruido del mundo principal) ni zona de las aldeas vanilla
        assert "bioma" not in pl and "exclusion_zone" not in pl and "bioma_y" not in pl
        for style, d in m.STYLES.items():
            s = files[f"data/heraldia/worldgen/structure/medianas/{mid}/{style}.json"]
            assert s["type"] == "heraldia:dimension" and s["modo"] == dimensions.dimension_of(m)
            assert "project_start_to_heightmap" not in s and "start_height" not in s
            height = max(fn(d["paleta"], "x").size()[1] for fn in d["variantes"].values())
            side = max(max(fn(d["paleta"], "x").size()[0], fn(d["paleta"], "x").size()[2]) for fn in d["variantes"].values())
            assert s["libre"] == height + dimensions.SLACK and s["radio"] == side // 2, (mid, style)
            assert s["size"] == 1 and 1 <= s["max_distance_from_center"] <= 116


def test_write_main_without_changes(tmp_path):
    files = {}
    mediums.write(str(tmp_path), lambda out, rel, obj: files.__setitem__(rel, obj))
    s = files["data/heraldia/worldgen/structure/medianas/posada/llanura.json"]
    assert s["type"] == "minecraft:jigsaw" and s["project_start_to_heightmap"] == "WORLD_SURFACE_WG"


def test_structure_dimension_limits():
    s = dimensions.structure("p", "#b", 1, 40, "nether", 200, 1)
    assert s["radio"] == 64 and s["libre"] == 2
    with pytest.raises(AssertionError):
        dimensions.structure("p", "#b", 1, 40, "overworld", 8, 8)
    assert dimensions.errors("x", type("M", (), {"DIMENSION": "aether"})) != []
    assert dimensions.errors("x", type("M", (), {})) == []


# ---------------------------------------------------------------- botín
def _items(tbl):
    return mediums._items(tbl)


@pytest.mark.parametrize("mid, m", MEDIUM_MODULES, ids=[m for m, _ in MEDIUM_MODULES])
def test_loot_mediums_modest(mid, m):
    for name, tbl in m.LOOT.items():
        obs = _items(tbl)
        assert not dimensions.forbidden_items(obs), (mid, name)
        assert not any(p in o for o in obs for p in mediums.FORBIDDEN), (mid, name)
        assert "minecraft:netherite_scrap" not in obs


@pytest.mark.parametrize("sid, m", UNIQUE_MODS, ids=[s for s, _ in UNIQUE_MODS])
def test_loot_uniques_without_break_the_progress(sid, m):
    for name, tbl in m.LOOT.items():
        assert not dimensions.forbidden_items(_items(tbl)), (sid, name)
        assert dimensions.extra_fragments(tbl) == [], (sid, name)
    assert "netherite" not in m.TROPHY["objeto"] and chest_loot.trophy_errors(sid, m.TROPHY) == []
    shulker = sum(1 for t in m.LOOT.values() for o in _items(t) if o == "minecraft:shulker_shell")
    assert shulker <= 1


def test_forbidden_list_detects():
    assert dimensions.forbidden_items(["minecraft:netherite_sword", "minecraft:elytra", "minecraft:gold_ingot"]) == [
        "minecraft:netherite_sword", "minecraft:elytra"]
    from loot import item
    t = chest_loot.table(chest_loot.pool(1, [item("netherite_scrap", 1, 1, 3)]))
    assert len(dimensions.extra_fragments(t)) == 1
    assert dimensions.extra_fragments(chest_loot.table(chest_loot.pool(1, [item("netherite_scrap", 1)]))) == []

    class Fake:
        DIMENSION = "nether"
        DISPLAY_NAME = {"es_es": "F", "en_us": "F"}
        SEPARATION = 600
        STYLES = {}
        LOOT = {"x": chest_loot.table(chest_loot.pool(1, [item("elytra", 1)]))}
    errs = mediums.errors(Registry(), "falsa", Fake)
    assert any("dimensiones.PROHIBIDO" in e for e in errs)


# ---------------------------------------------------------------- únicas: plantilla, guardián, mapas, crónica
@pytest.mark.parametrize("sid", [s for s, _ in UNIQUE_MODS])
def test_unique_built(reg_stub, sid):
    r = reg_stub[sid]
    assert r.warnings == []
    (t,) = r.templates.values()
    assert lint.template_issues(t) == []
    m = dict(UNIQUE_MODS)[sid]
    sx, sy, sz = t.size()
    assert m.STRUCTURE["json"]["libre"] >= sy + 1, "aire bajo el techo para toda la plantilla"
    assert m.STRUCTURE["json"]["type"] == "heraldia:dimension" and m.STRUCTURE["json"]["modo"] == dimensions.dimension_of(m)
    guard = [n for *_, n in t.entities if "heraldia_guardian" in (n.get("Tags") or [])]
    assert len(guard) == 1 and sid in r.guardians
    states = [st for st, _ in t.blocks.values()]
    assert any("pressure_plate" in s for s in states) and any(s.startswith("minecraft:dispenser") for s in states), "trampa"
    assert any(s.startswith("minecraft:spawner") for s in states), "generador"
    assert any("sticky_piston" in s for s in states) and t.lint_open, "sala oculta"
    tables = {str(n["LootTable"]).split("/")[-1] for _, n in t.blocks.values() if n and n.get("LootTable")}
    assert set(m.LOOT) <= tables and m.STORY["cofre"] in tables
    # la sala oculta (el pliego de la Crónica) solo se alcanza con la puerta de pistones abierta
    abierta = t.lint_open
    try:
        t.lint_open = {}
        shut = set(lint.walk(t))
    finally:
        t.lint_open = abierta
    view = set(lint.walk(t))
    concealed = [p for p, (_, n) in t.blocks.items() if n and str(n.get("LootTable", "")).endswith("/oculto")]

    def nearby_flag(cell_list, p):
        return any((p[0] + dx, p[1] + dy, p[2] + dz) in cell_list for dx in (-1, 0, 1) for dz in (-1, 0, 1) for dy in (-1, 0, 1))
    assert concealed and all(nearby_flag(view, p) and not nearby_flag(shut, p) for p in concealed)


def test_without_treasure_maps_or_trades(tmp_path):
    main = dimensions.overworld_only(uniques.modules())
    ids = {s for s, _ in main}
    assert not ids & {s for s, _ in UNIQUE_MODS} and len(ids) == len(uniques.modules()) - len(UNIQUE_MODS)
    epic = maps.with_maps({"pools": []}, main)
    destinations = json.dumps(epic)
    for sid, _ in UNIQUE_MODS:
        assert sid not in destinations
    cartographers = [i for i, *_ in trades.everyone(uniques.modules())]
    assert not any(sid in i for i in cartographers for sid, _ in UNIQUE_MODS)


def test_chronicle_without_map_between_dimensions():
    mods = uniques.modules()
    t = writer.history_tables(mods)
    dim = {s: dimensions.dimension_of(m) for s, m in mods}
    chain = chest_loot.story_chain(mods)
    for i, sid in enumerate(chain):
        nxt = chain[(i + 1) % len(chain)]
        with_map = len(t[sid]["pools"]) > 1
        assert with_map == (dim[sid] == dim[nxt] == "overworld"), (sid, nxt)


def test_advancements_per_dimension(reg):
    advs, lang = advancements.build(reg, [], mediums.modules())
    main = {m for m, mod in mediums.modules() if dimensions.dimension_of(mod) == "overworld"}
    assert set(advs["medianas/todas"]["criteria"]) == main
    assert set(advs["medianas/nether"]["criteria"]) == NETHER_MED
    assert set(advs["medianas/end"]["criteria"]) == END_MED
    for p in ("medianas/nether", "medianas/end"):
        assert advs[p]["parent"] == "heraldia:medianas/descubrir"
        k = f"advancements.heraldia.{p.replace('/', '.')}.title"
        assert lang["es_es"][k] and lang["en_us"][k]


def test_advancements_of_the_uniques():
    advs, _ = advancements.build(Registry(), uniques.modules())
    for sid, _ in UNIQUE_MODS:
        assert f"unicas/{sid}/descubrir" in advs
        crit = json.dumps(advs[f"unicas/{sid}/descubrir"]["criteria"])
        assert f"heraldia:unicas/{sid}" in crit and "dimension" not in crit     # en cualquier dimensión


# ---------------------------------------------------------------- textos en los 8 idiomas
def _new_keys():
    keys = set()
    for mid, m in MEDIUM_MODULES:
        keys.add(mediums.key_name(mid))
        keys |= set(getattr(m, "LANG", {}).get("es_es", {}))
        for ex in getattr(m, "ADVANCEMENTS", ()):
            keys |= {f"advancements.heraldia.medianas.{mid}.{ex['id']}.{p}" for p in ("title", "description")}
    for sid, m in UNIQUE_MODS:
        keys |= set(m.LANG["es_es"])
        keys |= {f"heraldia.historia.{sid}.pagina1", f"heraldia.historia.{sid}.pagina2", f"heraldia.historia.{sid}.pista",
                   f"heraldia.trofeo.{sid}", f"heraldia.unicas.{sid}.nombre"}
        keys |= {f"advancements.heraldia.unicas.{sid}.{a}.{p}" for a in ("descubrir", "guardian", "tesoro")
                   for p in ("title", "description")}
    keys |= {f"advancements.heraldia.medianas.{d}.{p}" for d in ("nether", "end") for p in ("title", "description")}
    return keys


@pytest.mark.parametrize("codigo", languages.TRANSLATIONS)
def test_translated_texts(codigo):
    translated = languages.load_data(codigo)
    missing = sorted(k for k in _new_keys() if not translated.get(k))
    assert missing == [], missing
    en = {}
    for _, m in MEDIUM_MODULES + UNIQUE_MODS:
        en.update(getattr(m, "LANG", {}).get("en_us", {}))
    for k, v in en.items():
        assert languages.markers(translated[k]) == languages.markers(v), k


def test_chronicle_pages_fit():
    for sid, m in UNIQUE_MODS:
        assert chest_loot.story_errors(sid, m.STORY, m.LOOT) == []
        for codigo in languages.TRANSLATIONS:
            translated = languages.load_data(codigo)
            for i in (1, 2):
                assert chest_loot.book_lines(translated[f"heraldia.historia.{sid}.pagina{i}"]) <= 14, (sid, codigo, i)
