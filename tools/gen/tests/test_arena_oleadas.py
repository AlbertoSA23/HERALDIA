"""Arena de oleadas (arena_oleadas.py): la plantilla cumple lo que dice arena.json (ruedo cerrado, cristal y techo,
puntos de aparición, campana, puerta, reaparición, luz), solo materiales que no arden ni coge un enderman, sus textos,
recompensas y logros, y su página en la Guía del Heraldo."""
import json
import math
import re

import pytest

import arena_oleadas as a
import guia
import loot
from unicas._comun import botin


@pytest.fixture(scope="module")
def t():
    return a.construir()


def nombre(st):
    return st.split("[")[0].removeprefix("minecraft:")


def test_la_plantilla_cumple(t):
    assert a.errores(t) == []


def test_tamano_contenido(t):
    sx, sy, sz = t.size()
    assert 48 <= sx <= 64 and 48 <= sz <= 64, "tamaño contenido: 48-64 bloques de lado"
    assert (sx, sy, sz) == tuple(a.datos()["tamano"])


def test_solo_materiales_seguros(t):
    usados = {nombre(st) for st, _ in t.blocks.values()}
    assert usados <= a.PALETA
    # ninguno arde ni lo coge un enderman (#minecraft:enderman_holdable de 26.3, sin sus subetiquetas de tierra y flores)
    holdable = {"sand", "red_sand", "gravel", "tnt", "cactus", "clay", "pumpkin", "carved_pumpkin", "melon", "dirt",
                "grass_block", "mud", "moss_block", "brown_mushroom", "red_mushroom"}
    assert not usados & holdable
    assert not any(set(b.split("_")) & {"planks", "log", "wood", "wool", "leaves", "carpet"} for b in usados)


def test_ruedo_cerrado_sin_puerta(t):
    """Con la puerta abierta (como está en la plantilla) se sale del ruedo; cerrada (rejas), no."""
    d = a.datos()
    assert a.errores(t, d) == []
    # si quitamos la puerta de la lista, la comprobación debe encontrar la salida
    d2 = dict(d, puerta=[[0, 0, 0], [0, 0, 0]])
    assert any("no está cerrado" in e for e in a.errores(t, d2))


def test_un_hueco_en_el_cristal_se_detecta(t):
    x, z = a.C + a.R_RUEDO, a.C              # columna del muro, al este
    t2 = a.construir()
    t2.set(x, a.CRISTAL[0] + 2, z, "air")
    assert any("cristal" in e for e in a.errores(t2))
    t3 = a.construir()
    t3.set(a.C, a.TECHO, a.C, "air")
    assert any("techo" in e for e in a.errores(t3))


def test_material_prohibido_se_detecta():
    t2 = a.construir()
    t2.set(a.C, 0, a.C, "oak_planks")
    assert any("PALETA" in e for e in a.errores(t2))


def test_puntos_de_aparicion(t):
    d = a.datos()
    assert len(d["puntos"]) >= 4
    for p in d["puntos"]:
        assert math.hypot(p[0] - a.C, p[2] - a.C) < a.R_RUEDO - 1
        assert nombre(t.get(p[0], 0, p[2])) == "chiseled_red_sandstone", "marca en el suelo"
        assert nombre(t.get(*p)) == "air" and nombre(t.get(p[0], 2, p[2])) == "air"
    # repartidos: ninguno en la entrada (sur) y lejos entre sí
    for i, p in enumerate(d["puntos"]):
        assert not (abs(p[0] - a.C) <= 2 and p[2] > a.C), "un punto delante de la entrada"
        for q in d["puntos"][i + 1:]:
            assert math.hypot(p[0] - q[0], p[2] - q[2]) >= 6


def test_campana_puerta_y_reaparicion(t):
    d = a.datos()
    assert nombre(t.get(*d["campana"])) == "bell"
    (x0, y0, z0), (x1, y1, z1) = d["puerta"]
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                assert nombre(t.get(x, y, z)) == "air"
                assert a.R_RUEDO <= math.hypot(x - a.C, z - a.C) < a.R_MURO, "la puerta corta el muro del ruedo"
    rp = d["reaparicion"]
    assert nombre(t.get(*rp)) == "air" and nombre(t.get(rp[0], rp[1] - 1, rp[2])) != "air"
    assert rp[1] - 1 == a.SUELO, "la reaparición está a ras del suelo exterior"


def test_gradas_protegidas_por_cristal(t):
    """Entre el ruedo y las gradas hay cristal hasta el techo de barreras en toda la vuelta (también sobre la puerta)."""
    for g in range(0, 360, 5):
        r = math.radians(g)
        x, z = a.C + round(15 * math.cos(r)), a.C + round(15 * math.sin(r))
        col = [nombre(t.get(x, y, z)) for y in range(a.CRISTAL[0], a.TECHO + 1)]
        assert col == ["glass"] * (a.CRISTAL[1] - a.CRISTAL[0] + 1) + ["barrier"], (g, col)


def test_entrada_baja_del_paseo_al_ruedo(t):
    """La rampa de la entrada sube de peldaño en peldaño (escaleras) del suelo del ruedo al del paseo."""
    pisos = []
    for z in range(a.PUERTA_Z[0], a.N):
        y = next(y for y in range(a.ALTO) if nombre(t.get(a.C, y, z)) == "air") - 1     # el piso: bajo el primer aire
        pisos.append(y)
    assert pisos[0] == 0 and pisos[-1] == a.SUELO
    assert all(0 <= b - c <= 1 for c, b in zip(pisos, pisos[1:])), pisos


def test_datos_json_serializable_y_completo():
    d = a.datos()
    json.dumps(d)
    assert set(d) >= {"plantilla", "tamano", "suelo", "centro", "radio_ruedo", "ruedo_y", "puntos", "campana", "puerta",
                      "reaparicion"}
    assert d["plantilla"] == "heraldia:arena/arena"


def test_textos_completos():
    lang = a.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    assert all(v.strip() for textos in lang.values() for v in textos.values())
    for k, es in lang["es_es"].items():
        assert re.findall(r"%[sd]", es) == re.findall(r"%[sd]", lang["en_us"][k]), k
    for i in range(len(a.JEFES)):
        assert f"heraldia.arena.jefe.{i}" in lang["es_es"]
    # los textos de éxito no deben cortar la espera de las pruebas de servidor (ERROR_PATTERN de server_smoke)
    for textos in lang.values():
        for k, v in textos.items():
            assert not re.search(r"Unknown|Incorrect|Failed|Invalid|error|not loaded", v), k


def test_recompensas_mejoran_con_la_oleada():
    tablas = a.tablas()
    assert sorted(tablas) == [f"arena/recompensa_{n}" for n in range(1, 5)]
    for t in tablas.values():
        s = json.dumps(t)
        assert "netherite" not in s and "elytra" not in s
        assert all(p["rolls"] for p in t["pools"])
    caros = lambda t: json.dumps(t).count("diamond")
    assert caros(tablas["arena/recompensa_1"]) < caros(tablas["arena/recompensa_4"])


def test_logros_5_10_20():
    ls = a.logros()
    assert sorted(ls) == ["arena/oleada_10", "arena/oleada_20", "arena/oleada_5"]
    assert ls["arena/oleada_5"]["parent"] == "heraldia:raiz"
    assert ls["arena/oleada_10"]["parent"] == "heraldia:arena/oleada_5"
    assert ls["arena/oleada_20"]["parent"] == "heraldia:arena/oleada_10"
    for l in ls.values():
        assert l["criteria"] == {"oleada": {"trigger": "minecraft:impossible"}}
        assert set(l["rewards"]) == {"experience"}


def test_pagina_de_la_guia():
    paginas = {pid: (titulo, texto) for pid, titulo, texto in guia.PAGINAS}
    assert "arena" in paginas
    titulo, texto = paginas["arena"]
    for i in (0, 1):
        assert guia.lineas_pagina(titulo[i], texto[i]) <= botin.LIBRO_LINEAS
        assert "/heraldia arena" in texto[i]
    assert guia.lang()["es_es"]["heraldia.guia.pagina.arena.titulo"] == "La arena"
