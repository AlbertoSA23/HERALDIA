"""Contenido del Nether y el End (T44, dimensiones.py): las medianas y las únicas con DIMENSION, sus plantillas (auditoría
genérica, recorrido, guardián, trampa, sala oculta), lo que escriben (tipo heraldia:dimension, rejilla sin búsqueda de
bioma ni zona de aldeas vanilla), su botín (lista prohibida, fragmentos de netherita), que no llevan mapa del tesoro,
sus logros y sus textos en los 8 idiomas."""
import json
import pytest
import dimensiones
import idiomas
import lint
import logros
import mapas
import medianas
import tratos
import unicas
import writer
from pack import Registry, _parte
from unicas._comun import botin

MED = [(mid, m) for mid, m in medianas.modules() if dimensiones.de(m) != dimensiones.PRINCIPAL]
UNI = [(sid, m) for sid, m in unicas.modules() if dimensiones.de(m) != dimensiones.PRINCIPAL]
NETHER_MED = {"puesto_piglin", "altar_magma", "atalaya_basalto", "santuario_hongos"}
END_MED = {"observatorio_vacio", "mausoleo_purpura", "embarcadero_shulker"}


@pytest.fixture(scope="module")
def reg():
    r = Registry()
    for mid, _ in MED:
        medianas.build(r, mid)
    return r


@pytest.fixture(scope="module")
def regu():
    return {sid: _parte(("unica", sid), 2026) for sid, _ in UNI}


def test_lotes_por_dimension():
    assert {mid for mid, m in MED if dimensiones.de(m) == "nether"} == NETHER_MED
    assert {mid for mid, m in MED if dimensiones.de(m) == "end"} == END_MED
    assert {sid: dimensiones.de(m) for sid, m in UNI} == {"ciudadela_ceniza": "nether", "sagrario_vacio": "end"}


@pytest.mark.parametrize("mid, m", MED, ids=[m for m, _ in MED])
def test_biomas_de_su_dimension(mid, m):
    """Cada estilo, en biomas de su dimensión; en el End, solo las islas exteriores (ni the_end ni small_end_islands)."""
    dim = dimensiones.de(m)
    for estilo, d in m.ESTILOS.items():
        assert d["biomas"] and set(d["biomas"]) <= set(dimensiones.BIOMAS[dim]), (mid, estilo)
    assert len(m.ESTILOS) >= 2


def test_biomas_de_las_unicas():
    for sid, m in UNI:
        bs = {b.split(":")[1] for b in m.STRUCTURE["biomes"]}
        assert bs <= set(dimensiones.BIOMAS[dimensiones.de(m)]), sid
        assert "the_end" not in bs and "small_end_islands" not in bs


def test_plantillas_sin_avisos(reg):
    assert reg.warnings == []
    assert len(reg.templates) == sum(len(d["variantes"]) for _, m in MED for d in m.ESTILOS.values())


@pytest.mark.parametrize("mid", [m for m, _ in MED])
def test_auditoria_y_patio_sin_suelo_vivo(reg, mid):
    for name, t in reg.templates.items():
        if not name.startswith(f"medianas/{mid}/"):
            continue
        assert lint.template_issues(t) == [], name
        assert len(lint.walk(t)) > 100, name
        # ni nilio, ni netherrack, ni arena de almas, ni piedra del End a la vista en el patio (dimensiones.SUELO_VIVO)
        for (x, y, z), (st, _) in t.blocks.items():
            if y == 0:
                assert st.split("[")[0] not in dimensiones.SUELO_VIVO, (name, (x, z), st)


def test_suelo_vivo_detectado():
    from core import Template
    t = Template("x")
    t.set(0, 0, 0, "crimson_nylium")
    t.normalize()
    assert any("suelo fértil" in e for e in medianas.plantilla_errores(t, "x", {}, "nether"))
    assert not any("suelo fértil" in e for e in medianas.plantilla_errores(t, "x", {}, "overworld"))


def test_escritura_tipo_dimension(tmp_path):
    files = {}
    medianas.write(str(tmp_path), lambda out, rel, obj: files.__setitem__(rel, obj))
    for mid, m in MED:
        pl = files[f"data/heraldia/worldgen/structure_set/medianas/{mid}.json"]["placement"]
        assert pl["type"] == "heraldia:rejilla" and pl["grupo"] == f"medianas/{mid}"
        # sin búsqueda de bioma (solo lee el ruido del mundo principal) ni zona de las aldeas vanilla
        assert "bioma" not in pl and "exclusion_zone" not in pl and "bioma_y" not in pl
        for estilo, d in m.ESTILOS.items():
            s = files[f"data/heraldia/worldgen/structure/medianas/{mid}/{estilo}.json"]
            assert s["type"] == "heraldia:dimension" and s["modo"] == dimensiones.de(m)
            assert "project_start_to_heightmap" not in s and "start_height" not in s
            alto = max(fn(d["paleta"], "x").size()[1] for fn in d["variantes"].values())
            lado = max(max(fn(d["paleta"], "x").size()[0], fn(d["paleta"], "x").size()[2]) for fn in d["variantes"].values())
            assert s["libre"] == alto + dimensiones.HOLGURA and s["radio"] == lado // 2, (mid, estilo)
            assert s["size"] == 1 and 1 <= s["max_distance_from_center"] <= 116


def test_escritura_principal_sin_cambios(tmp_path):
    files = {}
    medianas.write(str(tmp_path), lambda out, rel, obj: files.__setitem__(rel, obj))
    s = files["data/heraldia/worldgen/structure/medianas/posada/llanura.json"]
    assert s["type"] == "minecraft:jigsaw" and s["project_start_to_heightmap"] == "WORLD_SURFACE_WG"


def test_estructura_dimension_limites():
    s = dimensiones.estructura("p", "#b", 1, 40, "nether", 200, 1)
    assert s["radio"] == 64 and s["libre"] == 2
    with pytest.raises(AssertionError):
        dimensiones.estructura("p", "#b", 1, 40, "overworld", 8, 8)
    assert dimensiones.errores("x", type("M", (), {"DIMENSION": "aether"})) != []
    assert dimensiones.errores("x", type("M", (), {})) == []


# ---------------------------------------------------------------- botín
def _objetos(tabla):
    return medianas._objetos(tabla)


@pytest.mark.parametrize("mid, m", MED, ids=[m for m, _ in MED])
def test_botin_medianas_modesto(mid, m):
    for name, tabla in m.LOOT.items():
        obs = _objetos(tabla)
        assert not dimensiones.objetos_prohibidos(obs), (mid, name)
        assert not any(p in o for o in obs for p in medianas.PROHIBIDO), (mid, name)
        assert "minecraft:netherite_scrap" not in obs


@pytest.mark.parametrize("sid, m", UNI, ids=[s for s, _ in UNI])
def test_botin_unicas_sin_romper_el_progreso(sid, m):
    for name, tabla in m.LOOT.items():
        assert not dimensiones.objetos_prohibidos(_objetos(tabla)), (sid, name)
        assert dimensiones.fragmentos_de_mas(tabla) == [], (sid, name)
    assert "netherite" not in m.TROFEO["objeto"] and botin.trofeo_errores(sid, m.TROFEO) == []
    shulker = sum(1 for t in m.LOOT.values() for o in _objetos(t) if o == "minecraft:shulker_shell")
    assert shulker <= 1


def test_lista_prohibida_detecta():
    assert dimensiones.objetos_prohibidos(["minecraft:netherite_sword", "minecraft:elytra", "minecraft:gold_ingot"]) == [
        "minecraft:netherite_sword", "minecraft:elytra"]
    from loot import item
    t = botin.table(botin.pool(1, [item("netherite_scrap", 1, 1, 3)]))
    assert len(dimensiones.fragmentos_de_mas(t)) == 1
    assert dimensiones.fragmentos_de_mas(botin.table(botin.pool(1, [item("netherite_scrap", 1)]))) == []

    class Falsa:
        DIMENSION = "nether"
        NOMBRE = {"es_es": "F", "en_us": "F"}
        SEPARACION = 600
        ESTILOS = {}
        LOOT = {"x": botin.table(botin.pool(1, [item("elytra", 1)]))}
    errs = medianas.errores(Registry(), "falsa", Falsa)
    assert any("dimensiones.PROHIBIDO" in e for e in errs)


# ---------------------------------------------------------------- únicas: plantilla, guardián, mapas, crónica
@pytest.mark.parametrize("sid", [s for s, _ in UNI])
def test_unica_construida(regu, sid):
    r = regu[sid]
    assert r.warnings == []
    (t,) = r.templates.values()
    assert lint.template_issues(t) == []
    m = dict(UNI)[sid]
    sx, sy, sz = t.size()
    assert m.STRUCTURE["json"]["libre"] >= sy + 1, "aire bajo el techo para toda la plantilla"
    assert m.STRUCTURE["json"]["type"] == "heraldia:dimension" and m.STRUCTURE["json"]["modo"] == dimensiones.de(m)
    guard = [n for *_, n in t.entities if "heraldia_guardian" in (n.get("Tags") or [])]
    assert len(guard) == 1 and sid in r.guardianes
    estados = [st for st, _ in t.blocks.values()]
    assert any("pressure_plate" in s for s in estados) and any(s.startswith("minecraft:dispenser") for s in estados), "trampa"
    assert any(s.startswith("minecraft:spawner") for s in estados), "generador"
    assert any("sticky_piston" in s for s in estados) and t.lint_open, "sala oculta"
    tablas = {str(n["LootTable"]).split("/")[-1] for _, n in t.blocks.values() if n and n.get("LootTable")}
    assert set(m.LOOT) <= tablas and m.HISTORIA["cofre"] in tablas
    # la sala oculta (el pliego de la Crónica) solo se alcanza con la puerta de pistones abierta
    abierta = t.lint_open
    try:
        t.lint_open = {}
        cerrada = set(lint.walk(t))
    finally:
        t.lint_open = abierta
    vista = set(lint.walk(t))
    oculto = [p for p, (_, n) in t.blocks.items() if n and str(n.get("LootTable", "")).endswith("/oculto")]

    def cerca(celdas, p):
        return any((p[0] + dx, p[1] + dy, p[2] + dz) in celdas for dx in (-1, 0, 1) for dz in (-1, 0, 1) for dy in (-1, 0, 1))
    assert oculto and all(cerca(vista, p) and not cerca(cerrada, p) for p in oculto)


def test_sin_mapas_del_tesoro_ni_tratos(tmp_path):
    principal = dimensiones.del_mundo_principal(unicas.modules())
    ids = {s for s, _ in principal}
    assert not ids & {s for s, _ in UNI} and len(ids) == len(unicas.modules()) - len(UNI)
    epico = mapas.with_maps({"pools": []}, principal)
    destinos = json.dumps(epico)
    for sid, _ in UNI:
        assert sid not in destinos
    cartografos = [i for i, *_ in tratos.todos(unicas.modules())]
    assert not any(sid in i for i in cartografos for sid, _ in UNI)


def test_cronica_sin_mapa_entre_dimensiones():
    mods = unicas.modules()
    t = writer.history_tables(mods)
    dim = {s: dimensiones.de(m) for s, m in mods}
    cadena = botin.historia_cadena(mods)
    for i, sid in enumerate(cadena):
        nxt = cadena[(i + 1) % len(cadena)]
        con_mapa = len(t[sid]["pools"]) > 1
        assert con_mapa == (dim[sid] == dim[nxt] == "overworld"), (sid, nxt)


def test_logros_por_dimension(reg):
    advs, lang = logros.build(reg, [], medianas.modules())
    principal = {m for m, mod in medianas.modules() if dimensiones.de(mod) == "overworld"}
    assert set(advs["medianas/todas"]["criteria"]) == principal
    assert set(advs["medianas/nether"]["criteria"]) == NETHER_MED
    assert set(advs["medianas/end"]["criteria"]) == END_MED
    for p in ("medianas/nether", "medianas/end"):
        assert advs[p]["parent"] == "heraldia:medianas/descubrir"
        k = f"advancements.heraldia.{p.replace('/', '.')}.title"
        assert lang["es_es"][k] and lang["en_us"][k]


def test_logros_de_las_unicas():
    advs, _ = logros.build(Registry(), unicas.modules())
    for sid, _ in UNI:
        assert f"unicas/{sid}/descubrir" in advs
        crit = json.dumps(advs[f"unicas/{sid}/descubrir"]["criteria"])
        assert f"heraldia:unicas/{sid}" in crit and "dimension" not in crit     # en cualquier dimensión


# ---------------------------------------------------------------- textos en los 8 idiomas
def _claves_nuevas():
    claves = set()
    for mid, m in MED:
        claves.add(medianas.nombre_clave(mid))
        claves |= set(getattr(m, "LANG", {}).get("es_es", {}))
        for ex in getattr(m, "LOGROS", ()):
            claves |= {f"advancements.heraldia.medianas.{mid}.{ex['id']}.{p}" for p in ("title", "description")}
    for sid, m in UNI:
        claves |= set(m.LANG["es_es"])
        claves |= {f"heraldia.historia.{sid}.pagina1", f"heraldia.historia.{sid}.pagina2", f"heraldia.historia.{sid}.pista",
                   f"heraldia.trofeo.{sid}", f"heraldia.unicas.{sid}.nombre"}
        claves |= {f"advancements.heraldia.unicas.{sid}.{a}.{p}" for a in ("descubrir", "guardian", "tesoro")
                   for p in ("title", "description")}
    claves |= {f"advancements.heraldia.medianas.{d}.{p}" for d in ("nether", "end") for p in ("title", "description")}
    return claves


@pytest.mark.parametrize("codigo", idiomas.TRADUCCIONES)
def test_textos_traducidos(codigo):
    trad = idiomas.cargar(codigo)
    faltan = sorted(k for k in _claves_nuevas() if not trad.get(k))
    assert faltan == [], faltan
    en = {}
    for _, m in MED + UNI:
        en.update(getattr(m, "LANG", {}).get("en_us", {}))
    for k, v in en.items():
        assert idiomas.marcadores(trad[k]) == idiomas.marcadores(v), k


def test_paginas_de_la_cronica_caben():
    for sid, m in UNI:
        assert botin.historia_errores(sid, m.HISTORIA, m.LOOT) == []
        for codigo in idiomas.TRADUCCIONES:
            trad = idiomas.cargar(codigo)
            for i in (1, 2):
                assert botin.lineas_libro(trad[f"heraldia.historia.{sid}.pagina{i}"]) <= 14, (sid, codigo, i)
