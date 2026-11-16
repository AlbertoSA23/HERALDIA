"""Entradas a mina (minas/): plantillas de los tres tamaños y los cinco estilos (auditoría propia, forma, boca, galería,
vías), estilos por bioma, botín moderado, lo que escribe en el datapack (estructuras, rejillas, etiquetas, la colocación
de las minas vanilla), sus opciones, sus logros y la guía. Con casos negativos de la auditoría (una fuga en el forro,
la bajada o el pozo tapiados, una vía cortada) para que un cambio que rompa la mina falle aquí en segundos."""
import json
import pytest
import guia
import logros
import minas
import opciones
import unicas
from minas import auditoria, planos
from minas.botin import PROHIBIDO, DIAMANTES_MAX
from pack import Registry

TODAS = [(t, e, v) for t in minas.TAMANOS for e in minas.ESTILOS for v in minas.VARIANTES]


@pytest.fixture(scope="module")
def obras():
    return {k: minas.obra(*k)[0] for k in TODAS}


@pytest.fixture(scope="module")
def escrito(tmp_path_factory):
    """Lo que minas.write deja en el datapack: ({ruta: json} de jdump, {ruta: json} de las etiquetas de bioma, textos)."""
    import os
    import biomas
    previo = dict(biomas._ESCRITAS)
    files, etiquetas = {}, {}
    d = str(tmp_path_factory.mktemp("minas"))
    lang = minas.write(d, lambda _out, path, obj: files.__setitem__(path, obj))
    for root, _, fs in os.walk(d):
        for f in fs:
            with open(os.path.join(root, f), encoding="utf-8") as h:
                etiquetas[os.path.relpath(os.path.join(root, f), d).replace(os.sep, "/")] = json.load(h)
    biomas._ESCRITAS.clear()
    biomas._ESCRITAS.update(previo)
    return files, etiquetas, lang


# ------------------------------------------------------------------ plantillas
@pytest.mark.parametrize("clave", TODAS, ids=["/".join(k) for k in TODAS])
def test_auditoria_de_cada_variante(obras, clave):
    assert auditoria.errores(obras[clave], clave[0]) == []


def test_tamanos_y_profundidad(obras):
    for (tam, est, v), o in obras.items():
        x0, y0, z0, x1, y1, z1 = o.t.bounds()
        sx, sy, sz = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1
        assert max(sx, sz) <= 8 * 16, f"{tam}/{est}/{v}: {sx} x {sz}: no cabe en el alcance de un inicio (8 chunks)"
        hondo = min(y for _, y, _ in o.nodos) + 1
        assert hondo <= -planos.TAMANOS[tam]["hondo"] + 1
    medida = {t: max(len(obras[(t, e, v)].t.blocks) for e in minas.ESTILOS for v in minas.VARIANTES) for t in minas.TAMANOS}
    assert medida["pequena"] < medida["mediana"] < medida["grande"] < 40000, medida


def test_la_boca_esta_donde_dice_el_json():
    for tam, est, v in TODAS:
        o, (x0, y0, z0), meta = minas.obra(tam, est, v)
        ex, ey, ez = meta["entrada"]
        assert (ex + x0, ey + y0, ez + z0) == (0, 0, 0)
        assert o.t.get(0, 1, 0).startswith("minecraft:rail"), "vía bajo el dintel de la boca"
        assert "_log" in o.t.get(2, 1, 0) and "_log" in o.t.get(-2, 1, 0), "postes de la boca"
        px0, pz0, px1, pz1 = meta["patio"]
        assert pz1 == ez - 1 and px0 < ex < px1, "el patio queda delante de la boca"
        assert 4 <= len(meta["techo"]) <= 12, "muestras de techo para el Java (cada una cuesta una columna)"
        for x, z, dy in meta["techo"]:
            assert z > ez and dy < 0, "las muestras están sobre la galería, por debajo del patio"


def test_variantes_distintas_y_reflejadas(obras):
    for tam in minas.TAMANOS:
        for est in minas.ESTILOS:
            a, b = obras[(tam, est, "a")], obras[(tam, est, "b")]
            assert a.t.blocks != b.t.blocks
            assert {p for p, _ in a.cofres} != {p for p, _ in b.cofres}
    # lo que lleva lado (escaleras, puertas) se refleja: el capataz de la mediana b mira al otro lado
    a, b = obras[("mediana", "montana", "a")], obras[("mediana", "montana", "b")]
    puertas_a = [p for p, (st, _) in a.t.blocks.items() if "_door" in st and "lower" in st]
    puertas_b = [p for p, (st, _) in b.t.blocks.items() if "_door" in st and "lower" in st]
    assert [(-x, y, z) for x, y, z in puertas_a] == puertas_b


def test_cada_tamano_tiene_lo_suyo(obras):
    def nombres(o):
        return {st.split("[")[0].replace("minecraft:", "") for st, _ in o.t.blocks.values()}
    for est in minas.ESTILOS:
        p, m, g = (obras[(t, est, "a")] for t in minas.TAMANOS)
        ids = lambda o: sorted(n["id"] for *_, n in o.t.entities)
        assert ids(p) == ["minecraft:minecart"], "la boca pequeña: una vagoneta en sus vías"
        assert "minecraft:chest_minecart" in ids(m) and "minecraft:cave_spider" not in ids(m), "sin mobs: un generador"
        assert "minecraft:chest_minecart" in ids(g)
        assert {"blast_furnace", "furnace", "anvil", "campfire", "crafting_table"} <= nombres(m), "fundición y cabaña"
        assert "spawner" in nombres(g) and "spawner" in nombres(m) and "spawner" not in nombres(p)
        assert "iron_chain" in nombres(g), "la cadena de la polea"
        assert g.bajada is not None and p.bajada is None and m.bajada is None, "solo la grande tiene pozo"
        assert len({y for _, y, _ in g.nodos}) == 2, "la grande tiene dos niveles"


def test_generador_pequeno_de_aranas(obras):
    for tam, est in [(t, e) for t in ("mediana", "grande") for e in minas.ESTILOS]:
        o = obras[(tam, est, "a")]
        (x, y, z), = o.generadores
        st, nbt = o.t.blocks[(x, y, z)]
        assert nbt["SpawnData"]["entity"]["id"] == "minecraft:cave_spider"
        assert nbt["MaxNearbyEntities"] <= 4 and nbt["SpawnCount"] <= 2 and nbt["RequiredPlayerRange"] <= 16
        assert y <= -planos.TAMANOS[tam]["hondo"] + 2, "en lo hondo de la galería"


def test_mobs_persistentes_y_anclados(obras):
    from core import ANCLADO_TAG
    for o in obras.values():
        for *_, n in o.t.entities:
            if "minecart" not in n["id"]:
                assert n.get("PersistenceRequired") and ANCLADO_TAG in n["Tags"]


# ------------------------------------------------------------------ estilos por bioma
MATERIALES = {"montana": ("oak_log", "cobblestone"), "taiga": ("spruce_log", "cobblestone"),
              "desierto": ("birch_log", "sandstone"), "badlands": ("dark_oak_log", "terracotta"),
              "picos": ("stripped_spruce_log", "cobbled_deepslate")}


def test_estilos_por_bioma():
    vistos = set()
    for est, d in minas.ESTILOS.items():
        assert d["biomas"] and not (set(d["biomas"]) & vistos), f"{est}: biomas repetidos en otro estilo"
        vistos |= set(d["biomas"])
    assert {"desert"} == set(minas.ESTILOS["desierto"]["biomas"])
    assert "snowy_slopes" in minas.ESTILOS["taiga"]["biomas"] and "jagged_peaks" in minas.ESTILOS["picos"]["biomas"]
    assert "eroded_badlands" in minas.ESTILOS["badlands"]["biomas"]


def test_materiales_del_estilo(obras):
    for (tam, est, v), o in obras.items():
        tronco, piedra = MATERIALES[est]
        cuenta = {}
        for st, _ in o.t.blocks.values():
            n = st.split("[")[0].replace("minecraft:", "")
            cuenta[n] = cuenta.get(n, 0) + 1
        assert cuenta.get(tronco, 0) > 20, f"{tam}/{est}/{v}: entibado de {tronco}"
        assert cuenta.get(piedra, 0) > 100, f"{tam}/{est}/{v}: obra de {piedra}"
        otros = [t for e, (t, _) in MATERIALES.items() if e != est and t != tronco]
        assert not any(cuenta.get(t) for t in otros), f"{tam}/{est}/{v}: madera de otro estilo"


# ------------------------------------------------------------------ botín
def _entradas(tabla):
    for p in tabla["pools"]:
        for e in p["entries"]:
            yield p, e


def test_botin_moderado():
    for name, tabla in minas.LOOT.items():
        assert any(p.get("solo_sin_lootr") for p in tabla["pools"]), f"{name}: sin grupo «solo sin Lootr»"
        for p, e in _entradas(tabla):
            obj = e.get("name", "")
            assert not any(x in obj for x in PROHIBIDO), f"{name}: {obj}"
            if obj == "minecraft:diamond":
                mods = e.get("modifier") or e.get("functions") or {}
                mods = mods if isinstance(mods, list) else [mods]
                for m in mods:
                    if m.get("type") == "minecraft:set_count":
                        assert m["count"]["max"] <= DIAMANTES_MAX


def test_botin_algo_mejor_que_vanilla():
    """La tabla de las salas de la galería tira más veces que el cofre de mina vanilla (2-4 objetos de valor y 3 de
    raíles) y lleva esmeraldas y menas en bruto que el vanilla no tiene."""
    g = minas.LOOT["galeria"]["pools"]
    assert g[1]["rolls"]["min"] >= 3 and g[1]["rolls"]["max"] >= 5
    nombres = {e["name"] for _, e in _entradas(minas.LOOT["galeria"]) if "name" in e}
    assert {"minecraft:emerald", "minecraft:raw_iron", "minecraft:iron_ingot", "minecraft:rail"} <= nombres
    assert "minecraft:enchanted_golden_apple" not in nombres


def test_tablas_identificables_de_heraldia():
    assert set(minas.tablas()) == {f"minas/{n}" for n in minas.LOOT}
    for tam in minas.TAMANOS:
        assert auditoria.TABLAS[tam] <= set(minas.LOOT)


# ------------------------------------------------------------------ datapack
def test_lo_que_escribe(escrito):
    files, etiquetas, lang = escrito
    for tam in minas.TAMANOS:
        s = files[f"data/heraldia/worldgen/structure_set/minas/{tam}.json"]
        assert len(s["structures"]) == len(minas.ESTILOS) * len(minas.VARIANTES)
        pl = s["placement"]
        assert pl["type"] == "heraldia:rejilla" and pl["grupo"] == f"minas/{tam}" and pl["bioma"] == "heraldia:minas"
        assert pl["spacing"] == round(minas.SEPARACION[tam] / 16) and pl["exclusion_zone"]["other_set"] == "minecraft:villages"
        tag = files[f"data/heraldia/tags/worldgen/structure/minas/{tam}.json"]["values"]
        assert tag == [e["structure"] for e in s["structures"]]
        for e in s["structures"]:
            st = files["data/heraldia/worldgen/structure/" + e["structure"].split(":")[1] + ".json"]
            assert st["type"] == "heraldia:mina_entrada" and st["terrain_adaptation"] == "none"
            assert st["start_pool"] == e["structure"] and st["biomes"].startswith("#heraldia:minas/")
            assert len(st["entrada"]) == 3 and len(st["patio"]) == 4 and st["techo"]
    assert len(files["data/heraldia/tags/worldgen/structure/minas.json"]["values"]) == 30
    assert set(minas.estructuras()) == set(files["data/heraldia/tags/worldgen/structure/minas.json"]["values"])
    sales = {files[f"data/heraldia/worldgen/structure_set/minas/{t}.json"]["placement"]["salt"] for t in minas.TAMANOS}
    assert len(sales) == 3
    for n in minas.LOOT:
        assert f"data/heraldia/loot_table/minas/{n}.json" in files
    assert set(lang["es_es"]) == set(lang["en_us"])
    # etiquetas de bioma: la de todos los estilos y una por estilo, con sus convencionales opcionales
    assert "data/heraldia/tags/worldgen/biome/minas.json" in etiquetas
    for est, d in minas.ESTILOS.items():
        vals = etiquetas[f"data/heraldia/tags/worldgen/biome/minas/{est}.json"]["values"]
        assert [v for v in vals if isinstance(v, str)] == [f"minecraft:{b}" for b in d["biomas"]]
        assert all(v["required"] is False for v in vals if isinstance(v, dict))


def test_minas_vanilla_mismos_valores_que_26_3(escrito):
    files, _, _ = escrito
    s = files["data/minecraft/worldgen/structure_set/mineshafts.json"]
    assert [e["structure"] for e in s["structures"]] == ["minecraft:mineshaft", "minecraft:mineshaft_mesa"]
    p = dict(s["placement"])
    assert p.pop("type") == "heraldia:minas_vanilla"
    assert p == {"frequency": 0.004, "frequency_reduction_method": "legacy_type_3", "salt": 0, "separation": 0, "spacing": 1}


def test_build_registra_plantillas_y_pools():
    reg = Registry()
    minas.build(reg, "pequena")
    assert reg.warnings == []
    assert set(reg.templates) == {minas.plantilla("pequena", e, v) for e in minas.ESTILOS for v in minas.VARIANTES}
    for name, t in reg.templates.items():
        assert t.sin_auditoria_generica
        assert reg.pools[f"heraldia:{name}"]["elements"][0][0] == name
        assert min(t.bounds()[:3]) == 0, "normalizada"
    assert min(minas.obra("pequena", "montana", "a")[0].t.bounds()[:3]) < 0, "la obra en caché no se toca"


# ------------------------------------------------------------------ auditoría: casos negativos
def _copia(tam):
    import copy
    return copy.deepcopy(minas.obra(tam, "montana", "a")[0])


def test_auditoria_detecta_fuga_en_el_forro():
    o = _copia("pequena")
    c = sorted(o.carved)[len(o.carved) // 2]
    for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)):
        q = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
        if q not in o.carved and q in o.t.blocks and q not in o.superficie:
            o.t.clear(*q)
            break
    assert any("sin cerrar" in e for e in auditoria.errores(o, "pequena"))


def test_auditoria_detecta_bajada_tapiada():
    o = _copia("mediana")
    for y in range(-4, 3):
        for x in range(-1, 2):
            o.t.set(x, y, 5, "minecraft:cobblestone")
    errs = auditoria.errores(o, "mediana")
    assert any("inalcanzable" in e for e in errs) and any("vía" in e or "acaba" in e for e in errs)


def test_auditoria_detecta_pozo_tapiado():
    o = _copia("grande")
    bx, by, bz = o.bajada
    for y in range(by, by + 6):
        for dx, dz in ((0, 1), (-1, 1), (1, 1), (0, 2)):
            o.t.set(bx + dx, y, bz + dz, "minecraft:cobblestone")
    assert any("escalera de caracol" in e for e in auditoria.errores(o, "grande"))


def test_auditoria_detecta_rail_sin_apoyo():
    o = _copia("pequena")
    o.t.set(0, 0, -3, "minecraft:dirt_path")
    assert any("sin apoyo" in e for e in auditoria.errores(o, "pequena"))


def test_auditoria_detecta_forro_natural():
    o = _copia("pequena")
    c = sorted(o.carved)[0]
    q = (c[0], c[1] - 1, c[2])
    while q in o.carved:
        q = (q[0], q[1] - 1, q[2])
    o.t.set(*q, "minecraft:stone")
    o.superficie.discard(q)
    assert any("naturales" in e for e in auditoria.errores(o, "pequena"))


# ------------------------------------------------------------------ opciones, logros y guía
def test_opciones():
    sch = {o["clave"]: o for o in opciones.schema()["opciones"]}
    assert sch["minas.entradas.activado"]["defecto"] is True and sch["minas.entradas.activado"]["seccion"] == "minas"
    sep = sch["minas.entradas.separacion_bloques"]
    assert (sep["defecto"], sep["min"], sep["max"]) == (minas.SEPARACION["pequena"], *minas.SEPARACION_RANGO)
    mul = sch["minas.vanilla.multiplicador"]
    assert isinstance(mul["defecto"], float) and (mul["defecto"], mul["min"], mul["max"]) == minas.MULTIPLICADOR
    assert json.dumps(mul["defecto"]) == "2.0", "con punto: el Java la reconoce como decimal"
    lang = opciones.lang()
    for k in ("minas.entradas.activado", "minas.entradas.separacion_bloques", "minas.vanilla.multiplicador"):
        assert f"heraldia.config.{k}" in lang["es_es"] and f"heraldia.config.{k}.nombre" in lang["en_us"]


def test_logros_en_cadena():
    advs, lang = logros.build(Registry(), [], None, minas)
    assert "mina" in advs["raiz"]["criteria"]
    assert advs["minas/pequena"]["parent"] == "heraldia:raiz"
    assert advs["minas/mediana"]["parent"] == "heraldia:minas/pequena"
    assert advs["minas/grande"]["parent"] == "heraldia:minas/mediana"
    for tam in minas.TAMANOS:
        crit = advs[f"minas/{tam}"]["criteria"][tam]
        assert crit["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == f"#heraldia:minas/{tam}"
        assert 0 < advs[f"minas/{tam}"]["rewards"]["experience"] <= 100
    assert set(lang["es_es"]) == set(lang["en_us"])
    assert advs["minas/grande"]["display"]["frame"] == "goal"


def test_guia_habla_de_las_minas_y_de_los_jefes():
    ids = [pid for pid, _, _ in guia.PAGINAS]
    assert "minas" in ids and "jefes" in ids
    assert ids.index("minas") < ids.index("unicas")
    assert guia.errores(unicas.modules()) == [], "todas las páginas caben en los dos idiomas"
    for pid, titulo, texto in guia.PAGINAS:
        if pid in ("minas", "jefes"):
            for i in (0, 1):
                assert guia.lineas_pagina(titulo[i], texto[i]) <= 14
    jefes = dict((p, t) for p, _, t in guia.PAGINAS)["jefes"]
    assert "fases" in jefes[0] and "refuerzos" in jefes[0] and "barra" in jefes[0]


def test_carteles_traducibles():
    from minas.superficie import CARTELES
    for tam, lineas in CARTELES.items():
        for i in (1, 2):
            assert f"heraldia.minas.cartel.{tam}.{i}" in minas.LANG["es_es"]
            assert f"heraldia.minas.cartel.{tam}.{i}" in minas.LANG["en_us"]
