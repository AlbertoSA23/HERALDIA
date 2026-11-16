"""Estructuras medianas (medianas/): contrato de cada tipo, plantillas construidas (auditoría genérica de lint, tamaño,
entrada, entidades, botín modesto, suelo sin vida), lo que escribe en el datapack, sus opciones y sus logros. Con casos
negativos del contrato (medianas.errores) para que una mediana nueva que no lo cumpla falle aquí en segundos."""
import json
import pytest
import core
import lint
import logros
import medianas
import opciones
import unicas
from core import Template
from loot import item
from pack import Registry
from unicas._comun import botin

MODS = medianas.modules()
IDS = [mid for mid, _ in MODS]


@pytest.fixture(scope="module")
def reg():
    r = Registry()
    for mid in IDS:
        medianas.build(r, mid)
    return r


def test_lote_1_y_descubrimiento():
    assert IDS == sorted(IDS) == ["campamento", "ermita", "posada", "torre_vigia"]
    assert not any(m.startswith("_") for m in IDS)


def test_sal_estable_y_distinta_de_las_unicas():
    import zlib
    assert medianas.salt("posada") == zlib.crc32(b"heraldia:medianas/posada") & 0x7FFFFFFF
    sales = {medianas.salt(m) for m in IDS}
    assert len(sales) == len(IDS) and not sales & {unicas.salt(s) for s, _ in unicas.modules()}


@pytest.mark.parametrize("mid, m", MODS, ids=IDS)
def test_contrato(mid, m):
    assert m.NOMBRE["es_es"] and m.NOMBRE["en_us"]
    assert medianas.SEPARACION_RANGO[0] <= m.SEPARACION <= medianas.SEPARACION_RANGO[1]
    assert len(m.ESTILOS) >= 2
    for estilo, d in m.ESTILOS.items():
        assert d["biomas"] and len(d["variantes"]) >= 2, estilo
    assert "premium" not in m.LOOT
    lang = getattr(m, "LANG", {})
    assert set(lang.get("es_es", {})) == set(lang.get("en_us", {}))


def test_construidas_sin_avisos(reg):
    assert reg.warnings == []
    assert len([n for n in reg.templates if n.startswith("medianas/")]) == sum(
        len(d["variantes"]) for _, m in MODS for d in m.ESTILOS.values())


@pytest.mark.parametrize("mid", IDS)
def test_auditoria_generica_y_recorrido(reg, mid):
    for name, t in reg.templates.items():
        if not name.startswith(f"medianas/{mid}/"):
            continue
        assert lint.template_issues(t) == [], name
        cells = lint.walk(t)
        # se entra por la cara norte y se llega a todos los contenedores (access_issues) y a buena parte del patio
        assert len(cells) > 100, name


def test_entidades_marcadas_persistentes_y_ancladas(reg):
    mobs = 0
    for name, t in reg.templates.items():
        for *_, n in t.entities:
            tags = n["Tags"]
            mid = name.split("/")[1]
            assert medianas.MARCA in tags and f"{medianas.MARCA}.{mid}" in tags, name
            assert n["PersistenceRequired"] == 1
            if n["id"] != "minecraft:villager":
                mobs += 1
                assert core.ANCLADO_TAG in tags, name
    assert mobs == 2 * 6 + 1 * 2   # campamento: 2 en cada una de sus 6 plantillas; torre alta (2 estilos): el arquero


def test_bandidos_sin_patrulla(reg):
    for name, t in reg.templates.items():
        if name.startswith("medianas/campamento/"):
            for *_, n in t.entities:
                assert n["PatrolLeader"] == 0 and n["Patrolling"] == 0 and n["CanJoinRaid"] == 0


def test_posadero_con_tratos_fijos(reg):
    t = reg.templates["medianas/posada/llanura/a"]
    (v,) = [n for *_, n in t.entities if n["id"] == "minecraft:villager"]
    assert v["NoAI"] == 1 and v["Invulnerable"] == 1
    ventas = [o["sell"]["id"] for o in v["Offers"]["Recipes"]]
    assert "minecraft:white_bed" in ventas and "minecraft:bread" in ventas


def test_ermita_diario_traducible():
    from medianas import ermita
    tabla = ermita.LOOT["celda"]
    libro = tabla["pools"][0]["entries"][0]
    comp = libro["modifier"][0]["components"]["minecraft:written_book_content"]
    assert all(p["raw"]["translate"].startswith("heraldia.medianas.ermita.diario.") for p in comp["pages"])
    for k in ("heraldia.medianas.ermita.diario.p1", "heraldia.medianas.ermita.diario.p2"):
        assert k in ermita.LANG["es_es"] and k in ermita.LANG["en_us"]


# ---------------------------------------------------------------- casos negativos del contrato
class _Falsa:
    NOMBRE = {"es_es": "Falsa", "en_us": "Fake"}
    SEPARACION = 600
    LOOT = {"cofre": botin.cofre(((1, 1), [item("bread", 1)]), ((1, 1), [item("emerald", 1)]))}

    @staticmethod
    def buena(p, name):
        t = Template(name)
        from medianas import _comun as c
        c.patio(t, 0, 0, 12, 12, "minecraft:dirt_path")
        c.entrada(t, 6, "minecraft:dirt_path")
        c.cofre(t, 6, 1, 6, "north", "falsa", "cofre")
        return t

    ESTILOS = {"x": dict(biomas=["plains"], paleta={}, variantes={"a": buena})}


def _errores(mod, cambio=None):
    r = Registry()
    t = mod.buena({}, medianas.plantilla("falsa", "x", "a"))
    if cambio:
        cambio(t)
    medianas.marcar_entidades(t, "falsa")
    r.add(t, "mediana:falsa")
    return medianas.errores(r, "falsa", mod)


def test_contrato_valido():
    assert _errores(_Falsa) == []


@pytest.mark.parametrize("cambio, texto", [
    (lambda t: t.fill(0, 0, 0, 12, 0, 12, "grass_block"), "suelo fértil"),
    (lambda t: [t.entity(1, 1, 1, {"id": "minecraft:pillager", "PersistenceRequired": core.B(1)}) for _ in range(5)],
     "entidades"),
    (lambda t: t.entity(1, 1, 1, {"id": "minecraft:pillager"}), "PersistenceRequired"),
    (lambda t: (t.set(1, 1, 1, "spawner"), t.set(2, 1, 1, "spawner")), "generadores"),
    (lambda t: t.fill(0, 0, 0, 45, 0, 0, "dirt_path"), "tamaño"),
    (lambda t: t.jigsaws.clear(), "entrada"),
    (lambda t: t.chest(3, 1, 3, "north", "heraldia:unicas/castillo/premium"), "no es de su LOOT"),
])
def test_contrato_detecta(cambio, texto):
    errs = _errores(_Falsa, cambio)
    assert any(texto in e for e in errs), errs


def test_botin_premium_y_prohibido():
    class Rica(_Falsa):
        LOOT = {"cofre": botin.cofre(((1, 1), [item("diamond_sword", 1)]), ((1, 1), [item("emerald", 1)])),
                "premium": botin.cofre(((1, 1), [item("bread", 1)]), ((1, 1), [item("bread", 1)]))}
    errs = _errores(Rica)
    assert any("no es botín modesto" in e for e in errs)
    assert any("cofre premium" in e for e in errs)
    assert any("la tabla premium no la usa" in e for e in errs)


def test_sin_nombre_y_separacion_fuera_de_rango():
    class Mala(_Falsa):
        NOMBRE = {"es_es": "Mala"}
        SEPARACION = 100
    errs = _errores(Mala)
    assert any("NOMBRE" in e for e in errs) and any("SEPARACION" in e for e in errs)


# ---------------------------------------------------------------- datapack, opciones y logros
def test_escritura(tmp_path):
    files = {}
    medianas.write(str(tmp_path), lambda out, rel, obj: files.__setitem__(rel, obj))
    for mid, m in MODS:
        st = files[f"data/heraldia/worldgen/structure_set/medianas/{mid}.json"]
        pl = st["placement"]
        assert pl["type"] == "heraldia:rejilla" and pl["grupo"] == f"medianas/{mid}" and pl["salt"] == medianas.salt(mid)
        assert pl["exclusion_zone"]["other_set"] == "minecraft:villages"
        assert pl["bioma"] == f"heraldia:medianas/{mid}" and pl["bioma_y"] == medianas.BIOMA_Y
        union = json.loads((tmp_path / f"data/heraldia/tags/worldgen/biome/medianas/{mid}.json").read_text())["values"]
        assert {v for v in union if isinstance(v, str)} == {f"minecraft:{b}" for d in m.ESTILOS.values() for b in d["biomas"]}
        assert 0 < pl["separation"] < pl["spacing"] == round(m.SEPARACION / 16)
        assert [e["structure"] for e in st["structures"]] == [f"heraldia:medianas/{mid}/{e}" for e in m.ESTILOS]
        for estilo in m.ESTILOS:
            s = files[f"data/heraldia/worldgen/structure/medianas/{mid}/{estilo}.json"]
            assert s["biomes"] == f"#heraldia:medianas/{mid}/{estilo}"
            assert s["start_pool"] == f"heraldia:medianas/{mid}/{estilo}" and s["terrain_adaptation"] == "beard_thin"
            assert (tmp_path / f"data/heraldia/tags/worldgen/biome/medianas/{mid}/{estilo}.json").exists()
        for tabla in m.LOOT:
            assert f"data/heraldia/loot_table/medianas/{mid}/{tabla}.json" in files
    todas = files["data/heraldia/tags/worldgen/structure/medianas.json"]["values"]
    assert len(todas) == sum(len(m.ESTILOS) for _, m in MODS)


def test_biomas_convencionales_validos():
    """Las etiquetas extra de cada estilo resuelven en vanilla a un subconjunto de su lista (como biomas.comprobar)."""
    import biomas
    tags = biomas.convencionales()
    for mid, m in MODS:
        for estilo, d in m.ESTILOS.items():
            lista = {b if ":" in b else f"minecraft:{b}" for b in d["biomas"]}
            for c in d.get("convencionales", []):
                if c.startswith("c:"):
                    vals = tags[c[2:]]
                    directos = {v for v in vals if isinstance(v, str) and not v.startswith("#")}
                    assert directos <= lista, (mid, estilo, c)


def test_opciones():
    sch = opciones.schema()
    claves = {o["clave"]: o for o in sch["opciones"]}
    for k in ("medianas.activadas", "medianas.frecuencia_porcentaje", "medianas.distancia_minima.bloques",
              "medianas.distancia_aldeas_unicas_bloques"):
        assert claves[k]["seccion"] == "medianas"
    for mid, m in MODS:
        o = claves[f"medianas.{mid}.separacion_bloques"]
        assert o["defecto"] == m.SEPARACION and (o["min"], o["max"]) == medianas.SEPARACION_RANGO
        assert o["args_nombre"] == [f"heraldia.medianas.{mid}.nombre"]
        assert claves[f"medianas.{mid}.activada"]["defecto"] is True
    assert "medianas" in [s["id"] for s in sch["secciones"]]
    lang = opciones.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])


def test_logros(reg):
    advs, lang = logros.build(reg, [], MODS)
    assert set(advs["raiz"]["criteria"]) == {"aldea", "unica", "mediana"}
    todas = advs["medianas/todas"]
    assert todas["parent"] == "heraldia:medianas/descubrir" and todas["requirements"] == [[m] for m in IDS]
    assert todas["criteria"]["posada"]["conditions"]["player"]["predicate"]["minecraft:location"]["structures"] == "#heraldia:medianas/posada"
    assert set(lang["es_es"]) == set(lang["en_us"])


def test_textos():
    lang = medianas.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])
    for mid, m in MODS:
        assert lang["en_us"][medianas.nombre_clave(mid)] == m.NOMBRE["en_us"]
    json.dumps(lang)
