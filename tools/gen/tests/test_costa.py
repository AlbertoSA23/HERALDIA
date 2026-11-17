"""Faros y naufragios de la costa (costa/): plantillas de los dos tipos en los cuatro estilos y sus dos variantes (auditoría
propia y genérica, forma, la luz, el embarcadero, el agua bajo el casco), los estilos por clima (todas las parejas tierra-
mar con un solo estilo), el botín modesto y la pista del tesoro, lo que escribe en el datapack (estructuras, rejillas,
etiquetas, procesadores, botín), sus opciones, sus logros, la página de la Guía y sus textos en los 8 idiomas. Con casos
negativos de la auditoría (aire bajo el agua, la luz apagada, sin escalera) para que un cambio que lo rompa falle aquí."""
import json
import pytest
import litoral as costa
import guia
import idiomas
import lint
import logros
import opciones
import unicas
from litoral import auditoria, obras
from litoral.botin import LOOT, PROHIBIDO
from pack import Registry

TODAS = [(t, e, v) for t in costa.TIPOS for e in costa.ESTILOS for v in costa.VARIANTES]


@pytest.fixture(scope="module")
def escrito(tmp_path_factory):
    """Lo que costa.write deja en el datapack: ({ruta: json} de jdump, {ruta: json} de las etiquetas de bioma, textos)."""
    import os
    import biomas
    previo = dict(biomas._ESCRITAS)
    files, etiquetas = {}, {}
    d = str(tmp_path_factory.mktemp("costa"))
    lang = costa.write(d, lambda _out, path, obj: files.__setitem__(path, obj))
    for root, _, fs in os.walk(d):
        for f in fs:
            with open(os.path.join(root, f), encoding="utf-8") as h:
                etiquetas[os.path.relpath(os.path.join(root, f), d).replace(os.sep, "/")] = json.load(h)
    biomas._ESCRITAS.clear()
    biomas._ESCRITAS.update(previo)
    return files, etiquetas, lang


# ------------------------------------------------------------------ plantillas
@pytest.mark.parametrize("clave", TODAS, ids=["/".join(k) for k in TODAS])
def test_auditoria_de_cada_variante(clave):
    o, _, _ = costa.obra(*clave)
    assert auditoria.errores(o, clave[0]) == []


def test_auditoria_generica_de_apoyos():
    for tipo in costa.TIPOS:
        reg = Registry()
        costa.build(reg, tipo)
        assert reg.warnings == []
        assert len(reg.templates) == len(costa.ESTILOS) * len(costa.VARIANTES)
        for name, t in reg.templates.items():
            assert lint.template_issues(t) == [], name
            assert name in [p.split(":", 1)[1] for p in reg.pools], "una pool por plantilla"
        for pid, pool in reg.pools.items():
            (_, peso, proyeccion, proc), = pool["elements"]
            assert proyeccion == "rigid" and proc == costa.procesadores(tipo)


def test_el_faro_es_alto_y_tiene_la_luz_arriba():
    for estilo in costa.ESTILOS:
        for v in costa.VARIANTES:
            o, _, meta = costa.obra("faro", estilo, v)
            x0, y0, z0, x1, y1, z1 = o.t.bounds()
            assert costa.ALTURA_FARO[0] <= y1 - y0 + 1 <= costa.ALTURA_FARO[1]
            x, y, z = o.luz
            assert o.t.get(x, y, z) == "minecraft:redstone_lamp[lit=true]"
            assert o.t.get(x, y - 1, z) == "minecraft:redstone_block", "siempre encendida, sin circuitos"
            assert o.t.get(x, y + 1, z) == "minecraft:glowstone"
            assert y >= 20, "visible de lejos"
            assert not any("redstone_wire" in st or "repeater" in st or "comparator" in st or "lever" in st
                           for st, _ in o.t.blocks.values()), "sin redstone compleja"
            assert meta["modo"] == "faro" and meta["fila_mar"] == -1


def test_faro_casa_embarcadero_y_farero():
    for estilo in costa.ESTILOS:
        a, _, _ = costa.obra("faro", estilo, "a")
        b, _, _ = costa.obra("faro", estilo, "b")
        for o in (a, b):
            assert any("_bed[" in st for st, _ in o.t.blocks.values()), "la casa del farero"
            assert any(st.startswith("minecraft:furnace") for st, _ in o.t.blocks.values())
            muelle = [(x, z) for (x, y, z), (st, _) in o.t.blocks.items() if z > 0 and y == 0]
            assert len(muelle) >= 30 and max(z for _, z in muelle) == obras.MUELLE, "embarcadero sobre el mar"
            assert all(-1 <= x <= 1 for x, _ in muelle), "3 de ancho"
            assert all(z < 0 for (x, y, z) in o.t.blocks if y > 2), "solo el embarcadero (y su farol) sobre el agua: lo alto, en tierra"
        assert [n["id"] for *_, n in a.t.entities] == ["minecraft:villager"], "el farero, solo en la a"
        assert b.t.entities == []
        farero = a.t.entities[0][3]
        assert farero["NoAI"] and farero["Invulnerable"]
        vende = {r["sell"]["id"] for r in farero["Offers"]["Recipes"]}
        assert {"minecraft:map", "minecraft:compass", "minecraft:spyglass"} <= vende, "tratos marinos"
        assert a.t.blocks != b.t.blocks, "dos variantes distintas"


def test_variantes_del_faro_distintas():
    a, _, _ = costa.obra("faro", "templada", "a")
    b, _, _ = costa.obra("faro", "templada", "b")
    esquinas_a = a.t.get(3, 5, obras.TORRE_Z + 3)
    esquinas_b = b.t.get(3, 5, obras.TORRE_Z + 3)
    assert esquinas_a is None and esquinas_b is not None, "octogonal frente a cuadrada"
    casa_a = [x for (x, y, z), (st, _) in a.t.blocks.items() if "_bed[" in st]
    casa_b = [x for (x, y, z), (st, _) in b.t.blocks.items() if "_bed[" in st]
    assert max(casa_a) < 0 < min(casa_b), "la casa a cada lado"


def test_naufragio_sin_aire_bajo_el_agua():
    for estilo in costa.ESTILOS:
        for v in costa.VARIANTES:
            o, (x0, y0, z0), meta = costa.obra("naufragio", estilo, v)
            fila = o.fila_mar
            assert meta["fila_mar"] == fila - y0
            assert not [p for p, (st, _) in o.t.blocks.items() if p[1] <= fila and st.startswith("minecraft:air")]
            assert meta["modo"] == {"a": "encallado", "b": "hundido"}[v]


def test_naufragio_partido_con_mastiles_y_camarote():
    for estilo in costa.ESTILOS:
        for v in costa.VARIANTES:
            o, _, _ = costa.obra("naufragio", estilo, v)
            z0 = o.proa
            roto = [o.t.get(x, 5, z0 + 16) for x in range(0, 4)]
            assert all(st is None for st in roto), "partido: sin cubierta en la rotura"
            assert o.t.get(4, 3, z0 + 16) is None, "y el costado de estribor abierto"
            assert o.t.get(0, 17, z0 + 12) and "_log" in o.t.get(0, 17, z0 + 12), "el mástil mayor en pie"
            vela = [st for (x, y, z), (st, _) in o.t.blocks.items() if st.endswith("_wool")]
            assert 20 <= len(vela) <= 49, "una vela rota (con agujeros)"
            tablas = {str(n["LootTable"]): p for p, (st, n) in o.t.blocks.items() if n and n.get("LootTable")}
            assert set(tablas) == {"heraldia:costa/camarote", "heraldia:costa/bodega"}
            assert tablas["heraldia:costa/camarote"][1] > o.fila_mar, "el camarote en seco"
        hundido, _, _ = costa.obra("naufragio", estilo, "b")
        cofre = next(st for st, n in hundido.t.blocks.values() if n and str(n.get("LootTable")).endswith("bodega"))
        assert "waterlogged=true" in cofre, "la bodega inundada"
        ahogados = [n for *_, n in hundido.t.entities if n["id"] == "minecraft:drowned"]
        assert len(ahogados) == 1, "un ahogado como mucho"
        assert {"heraldia_anclado", "heraldia_adulto"} <= set(ahogados[0]["Tags"])
        encallado, _, _ = costa.obra("naufragio", estilo, "a")
        assert encallado.t.entities == [], "el encallado, sin nadie"


def test_huellas_para_el_java():
    for clave in TODAS:
        o, (x0, y0, z0), meta = costa.obra(*clave)
        ax, az = meta["ancla"]
        assert (ax + x0, az + z0) == o.ancla == (0, 0)
        tx0, tz0, tx1, tz1 = meta["tierra"]
        mx0, mz0, mx1, mz1 = meta["mar"]
        assert tz1 < 0 < mz0, "tierra detrás del ancla, mar delante"
        bx0, _, bz0, bx1, _, bz1 = o.t.bounds()
        assert bx0 <= tx0 and tx1 <= bx1 and bx0 <= mx0 and mx1 <= bx1
        assert mz1 <= bz1, "el mar que se mira está dentro de la plantilla"
        if clave[0] == "faro":
            assert (tx0, tz0, tx1, tz1) == (bx0, bz0, bx1, -1), "toda la plataforma en tierra"


def test_procesador_baja_lo_justo():
    faro, barco = costa.bajan("faro"), costa.bajan("naufragio")
    assert not any("planks" in b for b in faro), "los tablones del embarcadero no bajan"
    assert any("planks" in b for b in barco), "el fondo del casco sí"
    for d in costa.ESTILOS.values():
        assert f"minecraft:{d['faro']['tronco']}" in faro, "los pilotes"
        assert f"minecraft:{d['barco']['tronco']}" in barco, "la quilla"
        assert f"minecraft:{d['faro']['madera']}_planks" not in faro


# ------------------------------------------------------------------ estilos y climas
def test_cada_pareja_de_clima_tiene_un_solo_estilo():
    tierra = [b for g in costa.TIERRA.values() for b in g]
    assert len(tierra) == len(set(tierra)), "cada bioma de tierra en un grupo"
    for g, biomas in costa.TIERRA.items():
        for b in biomas:
            for m in costa.MAR["todos"]:
                estilos = [e for e, d in costa.ESTILOS.items()
                           if any(b in costa.TIERRA[t] and m in costa.MAR[mm] for t, mm in d["climas"])]
                assert len(estilos) == 1, (b, m, estilos)
    assert set(costa.PLAYAS) <= set(tierra)


def test_estilos_segun_la_costa():
    def estilo(tierra, mar):
        return next(e for e, d in costa.ESTILOS.items()
                    if any(tierra in costa.TIERRA[t] and mar in costa.MAR[m] for t, m in d["climas"]))
    assert estilo("beach", "ocean") == "templada"
    assert estilo("beach", "warm_ocean") == "calida"
    assert estilo("desert", "ocean") == "calida"
    assert estilo("stony_shore", "ocean") == "fria"
    assert estilo("beach", "cold_ocean") == "fria"
    assert estilo("snowy_beach", "frozen_ocean") == "nevada"
    assert estilo("snowy_beach", "warm_ocean") == "nevada"
    pal = costa.ESTILOS
    assert "stone" in pal["templada"]["faro"]["muro"] or "brick" in pal["templada"]["faro"]["muro"]
    assert "sandstone" in pal["calida"]["faro"]["muro"]
    assert "deepslate" in pal["fria"]["faro"]["muro"]
    assert "spruce" in pal["nevada"]["faro"]["muro"] and pal["nevada"]["faro"]["nieve"]


def test_materiales_del_estilo():
    for estilo, d in costa.ESTILOS.items():
        o, _, _ = costa.obra("faro", estilo, "a")
        assert any(st.startswith(f"minecraft:{d['faro']['muro']}") for st, _ in o.t.blocks.values())
        n, _, _ = costa.obra("naufragio", estilo, "a")
        assert any(st.startswith(f"minecraft:{d['barco']['madera']}_planks") for st, _ in n.t.blocks.values())
        nieve = any(st.startswith("minecraft:snow[") for st, _ in o.t.blocks.values())
        assert nieve == d["faro"]["nieve"], estilo


# ------------------------------------------------------------------ botín
def _objetos(tabla):
    out = []
    for p in tabla["pools"]:
        for e in p["entries"]:
            if e.get("type") == "minecraft:item":
                out.append(e["name"])
    return out


def test_botin_modesto():
    for name, tabla in LOOT.items():
        for o in _objetos(tabla):
            assert not any(x in o for x in PROHIBIDO), (name, o)
        assert tabla["pools"][-1].get("solo_sin_lootr"), "el grupo extra, solo sin Lootr"
    assert {"minecraft:map", "minecraft:compass", "minecraft:spyglass"} <= set(_objetos(LOOT["faro"]))
    assert "minecraft:map" in _objetos(LOOT["camarote"])


def test_lo_que_escribe(escrito):
    files, etiquetas, lang = escrito
    for tipo in costa.TIPOS:
        s = files[f"data/heraldia/worldgen/structure_set/costa/{tipo}.json"]
        p = s["placement"]
        assert p["type"] == "heraldia:rejilla" and p["grupo"] == f"costa/{tipo}"
        assert p["spacing"] == round(costa.SEPARACION[tipo] / 16) and p["bioma"] == "heraldia:litoral"
        assert p["bioma_vecinos"] == costa.BIOMA_VECINOS
        assert len(s["structures"]) == len(costa.ESTILOS) * len(costa.VARIANTES)
        assert files[f"data/heraldia/tags/worldgen/structure/costa/{tipo}.json"]["values"] == [e["structure"] for e in s["structures"]]
        proc = files[f"data/heraldia/worldgen/processor_list/costa/{tipo}_suelo.json"]["processors"][0]
        assert proc["processor_type"] == "heraldia:acueducto_hasta_el_suelo" and proc["bloques"] == costa.bajan(tipo)
    assert len(files["data/heraldia/tags/worldgen/structure/costa.json"]["values"]) == 16
    e = files["data/heraldia/worldgen/structure/costa/naufragio/fria/b.json"]
    assert e["type"] == "heraldia:costa" and e["modo"] == "hundido" and e["terrain_adaptation"] == "none"
    assert e["biomes"] == "#heraldia:litoral/fria" and e["step"] == "surface_structures"
    assert {"tierra": "#heraldia:litoral/tierra/rocosa", "mar": "#heraldia:litoral/mar/no_calido"} in e["climas"]
    for t in ("faro", "bodega", "camarote"):
        assert f"data/heraldia/loot_table/costa/{t}.json" in files
    camarote = files["data/heraldia/loot_table/costa/camarote.json"]
    pistas = [p for p in camarote["pools"] if any("tesoro/fragmento" in json.dumps(x) for x in p["entries"])]
    assert len(pistas) == 1, "una pista del tesoro en el camarote"
    assert pistas[0]["condition"]["factor"] == 0.5, "rara: la mitad que en una mediana"
    for t in ("faro", "bodega"):
        assert "tesoro/fragmento" not in json.dumps(files[f"data/heraldia/loot_table/costa/{t}.json"])
    assert etiquetas["data/heraldia/tags/worldgen/biome/litoral.json"]["values"] == [f"minecraft:{b}" for b in costa.PLAYAS]
    assert "data/heraldia/tags/worldgen/biome/costa.json" not in etiquetas, "la de la familia de aldeas de la costa, intacta"
    for estilo in costa.ESTILOS:
        assert f"data/heraldia/tags/worldgen/biome/litoral/{estilo}.json" in etiquetas
    assert lang["es_es"]["heraldia.costa.faro.nombre"] == "Faro"


def test_tablas_y_estructuras():
    assert set(costa.tablas()) == {f"costa/{t}" for t in LOOT}
    assert len(costa.estructuras()) == 16 and all(s.startswith("heraldia:costa/") for s in costa.estructuras())


# ------------------------------------------------------------------ opciones, logros, guía, idiomas
def test_opciones():
    claves = {k: (d, lo, hi) for k, d, lo, hi, *_ in opciones._FIXED}
    for tipo, o in costa.OPCION.items():
        assert claves[f"{o}.activado"][0] is True
        d, lo, hi = claves[f"{o}.separacion_bloques"]
        assert d == costa.SEPARACION[tipo] and (lo, hi) == costa.SEPARACION_RANGO
        assert opciones.es_generacion(f"{o}.activado"), "no lo cambia un perfil"
    assert claves["mapas_web.capas.costa"][0] is True


def test_logros():
    reg = Registry()
    advs, lang = logros.build(reg, unicas.modules(), None, None, costa)
    assert advs["raiz"]["criteria"]["costa"]["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == "#heraldia:costa"
    for t in ("faro", "naufragio"):
        crit = advs[f"costa/{t}"]["criteria"][t]
        assert crit["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == f"#heraldia:costa/{t}"
        assert advs[f"costa/{t}"]["parent"] == "heraldia:raiz"
    cam = advs["costa/camarote"]
    assert cam["parent"] == "heraldia:costa/naufragio"
    assert cam["criteria"]["camarote"]["conditions"]["loot_tables"] == "heraldia:costa/camarote"
    for p in ("faro", "naufragio", "camarote"):
        assert f"advancements.heraldia.costa.{p}.title" in lang["es_es"]


def test_pagina_de_la_guia():
    ids = [pid for pid, _, _ in guia.PAGINAS]
    assert "costa" in ids and ids.index("minas") < ids.index("costa") < ids.index("unicas")
    assert "costa" in guia.datos(unicas.modules())["paginas"]
    assert guia.errores(unicas.modules()) == []


@pytest.mark.parametrize("codigo", list(idiomas.TRADUCCIONES))
def test_textos_en_los_8_idiomas(codigo):
    import writer
    es = dict(costa.lang()["es_es"])
    es.update({k: v for k, v in guia.lang()["es_es"].items() if ".costa" in k})
    with open(idiomas.ruta(codigo), encoding="utf-8") as f:
        trad = json.load(f)
    for k, v in es.items():
        assert k in trad, (codigo, k)
        assert trad[k].count("%s") == v.count("%s"), (codigo, k)
    import admin
    for k in admin.lang()["es_es"]:
        if "costa" in k:
            assert k in trad, (codigo, k)
    for k in ("faros.activado", "naufragios.separacion_bloques", "mapas_web.capas.costa"):
        assert f"heraldia.config.{k}" in trad and f"heraldia.config.{k}.nombre" in trad
    assert guia.errores(unicas.modules(), {codigo: trad}) == []


# ------------------------------------------------------------------ casos negativos de la auditoría
def _copia(o):
    from types import SimpleNamespace
    from core import Template
    t = Template(o.t.name)
    t.blocks, t.entities = dict(o.t.blocks), list(o.t.entities)
    return SimpleNamespace(**{**vars(o), "t": t})


def test_auditoria_detecta_aire_bajo_el_agua():
    o = _copia(costa.obra("naufragio", "templada", "b")[0])
    o.t.set(0, 2, o.proa + 6, "air")
    assert any("aire bajo el agua" in e for e in auditoria.errores(o, "naufragio"))


def test_auditoria_detecta_la_luz_apagada():
    o = _copia(costa.obra("faro", "templada", "a")[0])
    x, y, z = o.luz
    o.t.set(x, y - 1, z, "stone_bricks")
    assert any("luz" in e for e in auditoria.errores(o, "faro"))


def test_auditoria_detecta_escalera_cortada():
    o = _copia(costa.obra("faro", "fria", "b")[0])
    o.t.set(0, 9, obras.TORRE_Z + 2, "air")
    assert any("escalera" in e for e in auditoria.errores(o, "faro"))


def test_auditoria_detecta_ahogado_suelto():
    o = _copia(costa.obra("naufragio", "nevada", "b")[0])
    o.t.entities = [(0, 2, 10, {"id": "minecraft:drowned", "PersistenceRequired": 1})]
    assert any("sin anclar" in e for e in auditoria.errores(o, "naufragio"))
