"""Contrato de los módulos de unicas/ (unicas/__init__.py), sin construir sus plantillas: descubrimiento, sal,
STRUCTURE, LOOT, TROFEO, HISTORIA, LLAVES, LANG, NOMBRE y MAPA. Si una única nueva no lo cumple, falla aquí en
milisegundos en vez de al final de la generación."""
import pytest
import unicas
import writer
from unicas._comun import botin

MODS = unicas.modules()
IDS = [sid for sid, _ in MODS]
TERRENO = {"beard_thin", "beard_box", "bury", "encapsulate", "none"}


def test_descubrimiento_ordenado_y_sin_privados():
    assert IDS == sorted(IDS) and len(IDS) >= 20
    assert not any(sid.startswith("_") for sid in IDS)


def test_sal_estable_y_distinta():
    # la sal fija la rejilla de cada tipo en los mundos ya existentes: no puede cambiar
    assert unicas.salt("castillo") == unicas.salt("castillo") and 0 <= unicas.salt("castillo") < 2 ** 31
    import zlib
    assert unicas.salt("x") == zlib.crc32(b"heraldia:unicas/x") & 0x7FFFFFFF
    assert len({unicas.salt(s) for s in IDS}) == len(IDS)


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_contrato_structure(sid, m):
    # dict.get / dict.keys: sin disparar los STRUCTURE perezosos (mina, ciudadela), que construyen la obra al leer "json"
    st = m.STRUCTURE
    assert callable(m.build)
    claves = set(dict.keys(st))
    if "start_pool" in claves:
        assert dict.get(st, "start_pool").startswith(f"unicas/{sid}/")
        assert 1 <= dict.get(st, "size") <= 20 and 1 <= dict.get(st, "max_distance") <= 116
        assert dict.get(st, "terrain_adaptation", "beard_thin") in TERRENO
    else:      # tipo propio: build() escribe STRUCTURE["json"] (galeón)
        assert "json" in claves or "build" in dir(m)
    b = dict.get(st, "biomes")
    assert b is None or isinstance(b, list) and b or isinstance(b, str) and b.startswith("#heraldia:")
    if "placement" not in claves:
        sp, se = dict.get(st, "spacing", unicas.DEFAULT_SPACING), dict.get(st, "separation", unicas.DEFAULT_SEPARATION)
        assert 0 < se < sp


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_contrato_botin_trofeo_historia(sid, m):
    loot = getattr(m, "LOOT", {})
    assert loot, "sin LOOT"
    assert botin.trofeo_errores(sid, getattr(m, "TROFEO", None)) == []
    assert botin.historia_errores(sid, getattr(m, "HISTORIA", None), loot) == []
    for nombre, tabla in loot.items():
        assert tabla.get("pools"), nombre
        writer.lootr_aware(tabla)                       # la marca solo_sin_lootr se convierte sin errores
    for llave, d in getattr(m, "LLAVES", {}).items():
        assert {"tabla", "cerradura"} <= set(d), llave


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_contrato_textos(sid, m):
    lang = getattr(m, "LANG", None)
    if lang:
        assert set(lang) == {"es_es", "en_us"} and set(lang["es_es"]) == set(lang["en_us"])
    n = getattr(m, "NOMBRE", None)
    if n:
        assert n.get("es_es")
    mapa = getattr(m, "MAPA", None)
    if mapa:
        assert mapa["decoration"].startswith("minecraft:") and mapa["decoration"] != "minecraft:woodland_mansion"


def test_una_sola_final_y_cadena_completa():
    assert botin.historia_cadena_errores(MODS) == []
    cadena = botin.historia_cadena(MODS)
    assert sorted(cadena) == IDS and MODS and dict(MODS)[cadena[-1]].HISTORIA.get("final")


def test_cadena_real_es_un_ciclo():
    t = writer.history_tables(MODS)
    sig = {}
    for sid, tabla in t.items():
        pista = tabla["pools"][0]["entries"][0]["modifier"][0]["components"]["minecraft:written_book_content"]["pages"][-1]["raw"]["with"][2]
        sig[sid] = pista["translate"].split(".")[-2]
    visto, s = [], IDS[0]
    while s not in visto:
        visto.append(s)
        s = sig[s]
    assert sorted(visto) == IDS and s == IDS[0]
