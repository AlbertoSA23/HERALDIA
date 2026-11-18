"""Contrato de los módulos de unicas/ (unicas/__init__.py), sin construir sus plantillas: descubrimiento, sal,
STRUCTURE, LOOT, TROFEO, HISTORIA, LLAVES, LANG, NOMBRE y MAPA. Si una única nueva no lo cumple, falla aquí en
milisegundos en vez de al final de la generación."""
import pytest
import uniques
import writer
from uniques._common import chest_loot

MODS = uniques.modules()
IDS = [sid for sid, _ in MODS]
TERRAIN = {"beard_thin", "beard_box", "bury", "encapsulate", "none"}


def test_discovery_sorted_and_without_private():
    assert IDS == sorted(IDS) and len(IDS) >= 20
    assert not any(sid.startswith("_") for sid in IDS)


def test_salt_stable_and_distinct():
    # la sal fija la rejilla de cada tipo en los mundos ya existentes: no puede cambiar
    assert uniques.salt("castillo") == uniques.salt("castillo") and 0 <= uniques.salt("castillo") < 2 ** 31
    import zlib
    assert uniques.salt("x") == zlib.crc32(b"heraldia:unicas/x") & 0x7FFFFFFF
    assert len({uniques.salt(s) for s in IDS}) == len(IDS)


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_contract_structure(sid, m):
    # dict.get / dict.keys: sin disparar los STRUCTURE perezosos (mina, ciudadela), que construyen la obra al leer "json"
    st = m.STRUCTURE
    assert callable(m.build)
    keys = set(dict.keys(st))
    if "start_pool" in keys:
        assert dict.get(st, "start_pool").startswith(f"unicas/{sid}/")
        assert 1 <= dict.get(st, "size") <= 20 and 1 <= dict.get(st, "max_distance") <= 116
        assert dict.get(st, "terrain_adaptation", "beard_thin") in TERRAIN
    else:      # tipo propio: build() escribe STRUCTURE["json"] (galeón)
        assert "json" in keys or "build" in dir(m)
    b = dict.get(st, "biomes")
    assert b is None or isinstance(b, list) and b or isinstance(b, str) and b.startswith("#heraldia:")
    if "placement" not in keys:
        sp, se = dict.get(st, "spacing", uniques.DEFAULT_SPACING), dict.get(st, "separation", uniques.DEFAULT_SEPARATION)
        assert 0 < se < sp


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_contract_loot_trophy_story(sid, m):
    loot = getattr(m, "LOOT", {})
    assert loot, "sin LOOT"
    assert chest_loot.trophy_errors(sid, getattr(m, "TROPHY", None)) == []
    assert chest_loot.story_errors(sid, getattr(m, "STORY", None), loot) == []
    for name, tbl in loot.items():
        assert tbl.get("pools"), name
        writer.lootr_aware(tbl)                       # la marca solo_sin_lootr se convierte sin errores
    for key, d in getattr(m, "KEYS", {}).items():
        assert {"tabla", "cerradura"} <= set(d), key


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_contract_texts(sid, m):
    lang = getattr(m, "LANG", None)
    if lang:
        assert set(lang) == {"es_es", "en_us"} and set(lang["es_es"]) == set(lang["en_us"])
    n = getattr(m, "DISPLAY_NAME", None)
    if n:
        assert n.get("es_es")
    map_obj = getattr(m, "MAP", None)
    if map_obj:
        assert map_obj["decoration"].startswith("minecraft:") and map_obj["decoration"] != "minecraft:woodland_mansion"


def test_a_single_final_and_full_chain():
    assert chest_loot.story_chain_errors(MODS) == []
    chain = chest_loot.story_chain(MODS)
    assert sorted(chain) == IDS and MODS and dict(MODS)[chain[-1]].STORY.get("final")


def test_chain_real_es_a_cycle():
    t = writer.history_tables(MODS)
    next_unique = {}
    for sid, tbl in t.items():
        clue = tbl["pools"][0]["entries"][0]["modifier"][0]["components"]["minecraft:written_book_content"]["pages"][-1]["raw"]["with"][2]
        next_unique[sid] = clue["translate"].split(".")[-2]
    seen, s = [], IDS[0]
    while s not in seen:
        seen.append(s)
        s = next_unique[s]
    assert sorted(seen) == IDS and s == IDS[0]
