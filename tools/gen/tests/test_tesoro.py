"""tesoro.py (T40, búsqueda del tesoro encadenada): la primera pista en el botín y su probabilidad, el cofre final, los
textos en los 8 idiomas, la página de la Guía, los logros, las opciones y que lo que lee el Java coincide."""
import json
import os
import re
import types

import pytest

import guia
import idiomas
import medianas
import minas
import opciones
import tablon
import tesoro
import unicas
from unicas._comun import botin

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JAVA = os.path.join(RAIZ, "src/main/java/io/github/albertosa23/heraldia")


def _java(rel):
    with open(os.path.join(JAVA, rel), encoding="utf-8") as f:
        return f.read()


def _trad():
    return {c: idiomas.leer(c) if hasattr(idiomas, "leer") else json.load(open(idiomas.ruta(c), encoding="utf-8"))
            for c in idiomas.TRADUCCIONES}


# ------------------------------------------------------------------ la primera pista en el botín
def test_con_pista_anade_un_grupo_con_la_condicion_y_el_factor():
    tabla = {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:bread"}]}]}
    for familia, factor in tesoro.FACTOR.items():
        t = tesoro.con_pista(tabla, familia)
        assert t["pools"][:-1] == tabla["pools"], "no toca lo que había"
        p = t["pools"][-1]
        assert p["rolls"] == 1 and p["entries"] == [{"type": "minecraft:loot_table", "value": tesoro.FRAGMENTO}]
        assert p["condition"] == {"type": tesoro.CONDICION, "factor": factor}
        assert "solo_sin_lootr" not in p, "con Lootr también: cada jugador el suyo"
    assert len(tabla["pools"]) == 1, "no cambia la tabla original"


def test_probabilidad_de_la_primera_pista():
    assert tesoro.probabilidad(3.0, tesoro.FACTOR["medianas"]) == pytest.approx(0.03)
    assert tesoro.probabilidad(3.0, tesoro.FACTOR["minas"]) == pytest.approx(0.03)
    assert tesoro.probabilidad(3.0, tesoro.FACTOR["unicas"]) == pytest.approx(0.015)
    assert tesoro.probabilidad(3.0, tesoro.FACTOR["hazanas"]) == pytest.approx(0.15)
    assert tesoro.probabilidad(3.0, tesoro.FACTOR["encargos"]) == pytest.approx(0.03)
    assert tesoro.probabilidad(0, 5) == 0 and tesoro.probabilidad(100, 5) == 1 and tesoro.probabilidad(50, 0.5) == 0.25


def test_simulacion_de_la_probabilidad():
    """Con la misma cuenta que PistaCondition (azar < probabilidad), la frecuencia observada se acerca a la esperada."""
    import random
    rnd = random.Random(40)
    for pct, factor in ((3.0, 1.0), (3.0, 0.5), (10.0, 5.0)):
        p = tesoro.probabilidad(pct, factor)
        n = 200_000
        sale = sum(rnd.random() < p for _ in range(n))
        assert abs(sale / n - p) < 4 * (p * (1 - p) / n) ** 0.5 + 1e-9


def test_la_misma_cuenta_que_el_java():
    java = _java("treasure/ClueCondition.java")
    assert "Math.max(0, Math.min(1, percent / 100.0 * factor))" in java
    assert 'optionalFieldOf("factor", 1.0)' in java
    assert f'"{tesoro.CONDICION.split(":")[1]}"' in _java("treasure/Treasure.java")


def test_medianas_y_minas_llevan_la_pista_en_todas_sus_tablas(tmp_path):
    escritas = {}

    def jdump(out, rel, obj):
        escritas[rel] = obj
    medianas.write(str(tmp_path), jdump)
    minas.write(str(tmp_path), jdump)
    tablas = {k: v for k, v in escritas.items() if "/loot_table/" in k}
    assert len(tablas) == len(medianas.tablas()) + len(minas.tablas())
    for rel, t in tablas.items():
        familia = "minas" if "/loot_table/minas/" in rel else "medianas"
        assert t["pools"][-1] == tesoro.pool_pista(familia), rel


def test_solo_en_cofres_barriles_y_vasijas():
    """Las tablas de las únicas que llevan la pista: las de algún contenedor (nunca la de un dispensador de trampa)."""
    def t(*bloques):
        return types.SimpleNamespace(blocks={i: b for i, b in enumerate(bloques)})
    reg = types.SimpleNamespace(templates={
        "a": t(("minecraft:chest[facing=north]", {"LootTable": "heraldia:unicas/x/premium"}),
               ("minecraft:trapped_chest", {"LootTable": "heraldia:unicas/x/trampa"}),
               ("minecraft:barrel[facing=up]", {"LootTable": "heraldia:unicas/x/barril"}),
               ("minecraft:decorated_pot[facing=north]", {"LootTable": "heraldia:unicas/x/vasija"}),
               ("minecraft:dispenser[facing=up]", {"LootTable": "heraldia:unicas/x/flechas"}),
               ("minecraft:dropper", {"LootTable": "heraldia:unicas/x/soltador"}),
               ("minecraft:stone", None), ("minecraft:chest", {"Items": []}))})
    assert tesoro.tablas_en_contenedores(reg) == {"heraldia:unicas/x/premium", "heraldia:unicas/x/trampa",
                                                  "heraldia:unicas/x/barril", "heraldia:unicas/x/vasija"}


def test_recompensa_de_las_hazanas_del_tablon():
    for nombre, t in tablon.tablas().items():
        assert t["type"] == "minecraft:advancement_reward"
        assert t["pools"][-1] == tesoro.pool_pista("hazanas"), nombre


def test_paga_de_los_encargos_del_tablon():
    """T38: cada encargo entregado tira heraldia:tesoro/encargo (solo el fragmento, con el factor de los encargos)."""
    t = tesoro.encargo()
    assert t["pools"] == [tesoro.pool_pista("encargos")]
    assert tesoro.ENCARGO == "heraldia:tesoro/encargo"
    assert 'Heraldia.id("tesoro/encargo")' in _java("treasure/Treasure.java")
    assert "Treasure.reward(p)" in _java("quests/Quests.java")


def test_el_escritor_aplica_la_pista_a_las_unicas():
    with open(os.path.join(os.path.dirname(tesoro.__file__), "writer.py"), encoding="utf-8") as f:
        w = f.read()
    assert 'tesoro.con_pista(table, "unicas")' in w and "tesoro.tablas_en_contenedores(reg)" in w
    assert "tesoro.write(out, jdump)" in w and "tesoro.lang()" in w and "tesoro.errores(" in w


# ------------------------------------------------------------------ el fragmento y el cofre final
def _componentes(entrada):
    return next(m["components"] for m in entrada["modifier"] if m["type"] == "minecraft:set_components")


def test_fragmento():
    t = tesoro.fragmento()
    (e,) = t["pools"][0]["entries"]
    assert e["name"] == "minecraft:paper"
    c = _componentes(e)
    assert c["minecraft:custom_data"] == "{heraldia_busqueda: {v: 1}}"
    assert c["minecraft:max_stack_size"] == 1, "cada fragmento, su propia cadena"
    assert c["minecraft:item_name"]["translate"] == tesoro.clave("fragmento.nombre")
    assert [l["translate"] for l in c["minecraft:lore"]] == [tesoro.clave("fragmento.lore"), tesoro.clave("fragmento.uso")]
    assert all(l["italic"] is False for l in c["minecraft:lore"])


def test_la_marca_es_la_del_java_y_distinta_de_las_demas():
    assert f'MARK = "{tesoro.MARCA}"' in _java("treasure/Chain.java")
    import logros
    assert tesoro.MARCA not in (logros.TREASURE_MARK, botin.HISTORIA_MARCA, guia.MARCA)


def test_cofre_final_bueno_sin_romper_la_progresion():
    t = tesoro.cofre()
    assert t["pools"][0]["rolls"] == 1 and t["pools"][0]["entries"] == [tesoro.recuerdo()]
    texto = json.dumps(t)
    for p in tesoro.PROHIBIDO:
        assert p not in texto
    valiosos = {e["name"].split(":")[1] for e in tesoro.VALIOSO}
    assert {"diamond", "emerald", "gold_ingot"} <= valiosos
    assert tesoro.errores() == []


def test_recuerdo_con_nombre():
    c = _componentes(tesoro.recuerdo())
    assert tesoro.recuerdo()["name"] == "minecraft:compass"
    assert c["minecraft:item_name"]["translate"] == tesoro.clave("recuerdo.nombre")
    assert c["minecraft:custom_data"] == "{heraldia_recuerdo_tesoro: 1b}"
    assert c["minecraft:rarity"] == "rare"


def test_los_objetos_existen():
    """Contra el registro real de 26.3 (resumen de mcmeta que deja la compilación); sin él, se salta."""
    f = os.path.join(RAIZ, "build/mcmeta-summary/registries/data.json")
    if not os.path.isfile(f):
        pytest.skip("sin build/mcmeta-summary")
    with open(f, encoding="utf-8") as fh:
        items = set(json.load(fh)["item"])
    nombres = re.findall(r'"name": "minecraft:([a-z0-9_]+)"', json.dumps([tesoro.fragmento(), tesoro.cofre()]))
    assert nombres and set(nombres) <= items, set(nombres) - items
    iconos = [a["display"]["icon"]["id"].split(":")[1] for a in tesoro.logros().values()]
    assert set(iconos) <= items


def test_errores_detecta_lore_largo(monkeypatch):
    monkeypatch.setitem(tesoro.TEXTOS, "mapa.uso", ("x" * 80, "ok"))
    assert any("mapa.uso" in e for e in tesoro.errores())


# ------------------------------------------------------------------ textos en los 8 idiomas
def test_textos_en_los_dos_idiomas_base():
    l = tesoro.lang()
    assert l["es_es"].keys() == l["en_us"].keys()
    assert all(v.strip() for d in l.values() for v in d.values())
    marca = re.compile(r"%(?:\d+\$)?s")
    for k in l["es_es"]:
        assert len(marca.findall(l["es_es"][k])) == len(marca.findall(l["en_us"][k])), k


def test_textos_en_las_traducciones():
    base = dict(tesoro.lang()["en_us"], **tesoro.lang_logros()["en_us"])
    marca = re.compile(r"%(?:\d+\$)?s")
    for codigo, t in _trad().items():
        for k, en in base.items():
            assert t.get(k, "").strip(), f"{codigo}: falta {k}"
            assert len(marca.findall(t[k])) == len(marca.findall(en)), f"{codigo}: huecos de {k}"
        for k in ("heraldia.guia.pagina.tesoro", "heraldia.guia.pagina.tesoro.titulo", "heraldia.config.tesoro.activado",
                  "heraldia.config.tesoro.probabilidad", "heraldia.config.tesoro.radio_max", "heraldia.config.seccion.tesoro"):
            assert t.get(k, "").strip(), f"{codigo}: falta {k}"
    assert tesoro.errores(_trad()) == [], "el lore cabe en todos los idiomas"


def test_lore_de_los_mapas_cabe_con_un_bioma_largo():
    for codigo, t in [("en", tesoro.lang()["en_us"]), ("es", tesoro.lang()["es_es"])] + list(_trad().items()):
        linea = idiomas.formatear(t[tesoro.clave("pista.donde")], ["Old Growth Spruce Taiga", t.get("heraldia.info.dir.ne", "northeast")])
        assert botin.ancho(linea) <= tesoro.LORE_MAX_PX + 60, f"{codigo}: {linea}"


# ------------------------------------------------------------------ la Guía
def test_pagina_de_la_guia():
    ids = [pid for pid, _, _ in guia.PAGINAS]
    assert "tesoro" in ids and ids.index("tesoro") == ids.index("mapas") + 1, "junto a los mapas del tesoro"
    assert "tesoro" in guia.datos(unicas.modules())["paginas"]
    es = guia.lang()["es_es"]
    assert "Ysolda" in es["heraldia.guia.pagina.tesoro"]
    assert guia.errores(unicas.modules(), _trad()) == []


def test_pagina_de_la_guia_cabe_en_cada_idioma():
    for codigo, t in list(_trad().items()) + [("es", guia.lang()["es_es"]), ("en", guia.lang()["en_us"])]:
        titulo, texto = t["heraldia.guia.pagina.tesoro.titulo"], t["heraldia.guia.pagina.tesoro"]
        assert guia.lineas_pagina(titulo, texto) <= botin.LIBRO_LINEAS, codigo
        assert guia.lineas_titulo(titulo) == 1, codigo


# ------------------------------------------------------------------ logros
def test_logros():
    a = tesoro.logros()
    assert set(a) == {"tesoro/fragmento", "tesoro/cofre"}
    assert a["tesoro/fragmento"]["parent"] == "heraldia:raiz" and a["tesoro/cofre"]["parent"] == "heraldia:tesoro/fragmento"
    pred = a["tesoro/fragmento"]["criteria"]["fragmento"]["conditions"]["items"][0]
    assert pred["items"] == "minecraft:paper" and pred["predicates"]["minecraft:custom_data"] == {tesoro.MARCA: {}}
    assert a["tesoro/cofre"]["criteria"]["cofre"] == {"trigger": "minecraft:player_generates_container_loot",
                                                      "conditions": {"loot_tables": tesoro.COFRE}}
    assert a["tesoro/cofre"]["display"]["frame"] == "goal"
    assert all(set(x.get("rewards", {})) <= {"experience"} for x in a.values()), "solo experiencia"
    l = tesoro.lang_logros()["es_es"]
    for x in a.values():
        assert x["display"]["title"]["translate"] in l and x["display"]["description"]["translate"] in l


def test_los_logros_van_con_los_demas():
    import logros
    import inspect
    assert "advs.update(tesoro.logros())" in inspect.getsource(logros.build)


def test_el_java_usa_las_tablas():
    t = _java("treasure/Treasure.java")
    assert 'Heraldia.id("tesoro/fragmento")' in t and 'Heraldia.id("tesoro/cofre")' in t
    assert tesoro.FRAGMENTO == "heraldia:tesoro/fragmento" and tesoro.COFRE == "heraldia:tesoro/cofre"


# ------------------------------------------------------------------ opciones
def test_opciones():
    o = {x["clave"]: x for x in opciones.schema()["opciones"]}
    assert o["tesoro.activado"]["defecto"] is True
    assert o["tesoro.probabilidad"]["defecto"] == tesoro.PROBABILIDAD_DEFECTO
    assert (o["tesoro.probabilidad"]["min"], o["tesoro.probabilidad"]["max"]) == (0, 100)
    assert o["tesoro.radio_max"]["defecto"] == tesoro.RADIO_DEFECTO
    assert o["tesoro.radio_max"]["min"] >= 300
    for k in ("tesoro.activado", "tesoro.probabilidad", "tesoro.radio_max"):
        assert not o[k].get("generacion"), f"{k} no es de generación"
        assert o[k]["seccion"] == "tesoro"
        assert not o[k].get("perfil"), "los perfiles no la tocan"
    j = _java("treasure/ClueCondition.java")
    assert all(f'"{k}"' in j for k in ("tesoro.activado", "tesoro.probabilidad", "tesoro.radio_max"))


def test_opciones_recargables_en_java():
    assert re.search(r'RELOADABLE = List\.of\([^;]*"tesoro\."', _java("config/Reload.java"), re.S)
