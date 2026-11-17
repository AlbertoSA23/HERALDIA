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


LOTE_1 = ["campamento", "ermita", "posada", "torre_vigia"]
LOTE_2 = ["cazadores", "molino", "pescador", "templete"]
CHOZAS = ["choza_mago"]                 # T43: las chozas de mago


def test_lotes_y_descubrimiento():
    assert IDS == sorted(IDS) == sorted(LOTE_1 + LOTE_2 + CHOZAS)
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
    # campamento: 2 en cada una de sus 6 plantillas; torre alta (2 estilos): el arquero; pescador a (3 estilos): el gato;
    # cazadores a (2 estilos): el lobo; templete a (2 estilos): dos custodios; choza de mago a (6 estilos): el gato
    assert mobs == 2 * 6 + 1 * 2 + 1 * 3 + 1 * 2 + 2 * 2 + 1 * 6


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
        assert pl.get("bioma_vecinos") == getattr(m, "BIOMA_VECINOS", None)
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


# ---------------------------------------------------------------- lote 2: molino, pescador, cazadores, templete
def _entidades(reg, mid):
    return {name: [n for *_, n in t.entities] for name, t in reg.templates.items() if name.startswith(f"medianas/{mid}/")}


def test_lote_2_estilos_y_biomas_poco_servidos():
    """Cada tipo nuevo tiene varios estilos, 2 variantes en cada uno y biomas que el lote 1 no tenía (o casi)."""
    lote_1 = {b for mid, m in MODS if mid in LOTE_1 for d in m.ESTILOS.values() for b in d["biomas"]}
    for mid, m in MODS:
        if mid not in LOTE_2:
            continue
        assert len(m.ESTILOS) >= 2 and all(len(d["variantes"]) == 2 for d in m.ESTILOS.values()), mid
        nuevos = {b for d in m.ESTILOS.values() for b in d["biomas"]} - lote_1
        assert nuevos, mid
    nuevos = {b for mid, m in MODS if mid in LOTE_2 for d in m.ESTILOS.values() for b in d["biomas"]} - lote_1
    assert {"swamp", "beach", "snowy_beach", "stony_shore", "snowy_plains", "ice_spikes", "jungle", "desert"} <= nuevos


@pytest.mark.parametrize("mid", LOTE_2)
def test_lote_2_tamano(reg, mid):
    for name, t in reg.templates.items():
        if name.startswith(f"medianas/{mid}/"):
            sx, _, sz = t.size()
            assert 15 <= sx <= 21 and 15 <= sz <= 21, (name, sx, sz)


def test_aldeanos_del_lote_2_con_tratos_fijos(reg):
    esperado = {"molino": ("farmer", "minecraft:bread"), "pescador": ("fisherman", "minecraft:fishing_rod"),
                "cazadores": ("leatherworker", "minecraft:leather_chestplate")}
    for mid, (prof, vende) in esperado.items():
        for name, ns in _entidades(reg, mid).items():
            vs = [n for n in ns if n["id"] == "minecraft:villager"]
            if name.endswith("/a"):
                (v,) = vs
                assert v["NoAI"] == 1 and v["Invulnerable"] == 1, name
                assert v["VillagerData"]["profession"] == f"minecraft:{prof}", name
                assert vende in [o["sell"]["id"] for o in v["Offers"]["Recipes"]], name
            else:
                assert vs == [], name


def test_animales_y_custodios_del_lote_2(reg):
    for name, ns in _entidades(reg, "pescador").items():
        gatos = [n for n in ns if n["id"] == "minecraft:cat"]
        assert len(gatos) == (1 if name.endswith("/a") else 0), name
    for name, ns in _entidades(reg, "cazadores").items():
        assert len([n for n in ns if n["id"] == "minecraft:wolf"]) == (1 if name.endswith("/a") else 0), name
    for name, ns in _entidades(reg, "templete").items():
        if name.endswith("/b"):
            assert ns == [], name
            continue
        assert len(ns) == 2, name
        for n in ns:
            assert n["id"] in ("minecraft:skeleton", "minecraft:husk"), name
            if n["id"] == "minecraft:husk":
                assert core.ADULTO_TAG in n["Tags"], name       # no sale bebé
            else:
                assert n["equipment"]["head"]["id"] == "minecraft:chainmail_helmet", name   # no arde de día


def test_agua_quieta_y_contenida(reg):
    """El agua de las medianas (caz del molino, trigal, acequias, pozo del templete) es toda fuente y no tiene ninguna
    cara lateral abierta dentro de la plantilla: no corre."""
    for name, t in reg.templates.items():
        if not name.startswith("medianas/"):
            continue
        for (x, y, z), (st, _) in t.blocks.items():
            if lint.bname(st) != "water":
                continue
            assert "level=0" in st, (name, (x, y, z))
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                vecino = t.get(x + dx, y, z + dz)
                if vecino is None:
                    assert y == 0, (name, (x, y, z), "agua sobre el terreno, junto al vacío")
                    continue
                assert lint.bname(vecino) == "water" or not lint.passable(vecino), (name, (x, y, z), vecino)
            debajo = t.get(x, y - 1, z)
            assert y == 0 or (debajo and not lint.passable(debajo)), (name, (x, y, z))


def test_molino_rueda_y_aspas(reg):
    a = reg.templates["medianas/molino/llanura/a"]
    assert sum(1 for (x, _, _), (st, _) in a.blocks.items() if x == 12 and st == "minecraft:oak_planks") == 16  # aro
    assert a.get(12, 0, 9).startswith("minecraft:water")              # la rueda moja en el caz
    b = reg.templates["medianas/molino/llanura/b"]
    lona = [p for p, (st, _) in b.blocks.items() if st == "minecraft:white_wool"]
    assert len(lona) == 16 and all(z == 12 for _, _, z in lona)       # cuatro aspas en la cara sur


def test_embarcadero_del_pescador(reg):
    for v, largo in (("a", 17), ("b", 20)):
        t = reg.templates[f"medianas/pescador/playa/{v}"]
        tablas = [z for (x, y, z), (st, _) in t.blocks.items() if y == 1 and x == 12 and st == "minecraft:birch_planks"]
        assert max(tablas) == largo and min(tablas) == 6


def test_templete_columnas_rotas_y_arquitrabe(reg):
    from medianas import templete as tp
    t = reg.templates["medianas/templete/desierto/a"]
    for x in range(tp.P0, tp.P1 + 1):
        for z in (tp.P0, tp.P1):
            assert t.get(x, 7, z) is not None          # arquitrabe entero al norte y al sur
    rotas = {(x, z): max(y for (xx, y, zz), (st, _) in t.blocks.items() if (xx, zz) == (x, z) and st != "minecraft:air")
             for x in (tp.P0, tp.P1)
             for z in range(tp.P0 + 2, tp.P1 - 1, 2)}
    assert all(h < 7 for h in rotas.values()) and len(set(rotas.values())) > 1


def test_vasijas_con_botin(reg):
    t = reg.templates["medianas/templete/jungla/b"]
    vasijas = [nbt for (st, nbt) in t.blocks.values() if st.startswith("minecraft:decorated_pot") and nbt and nbt.get("LootTable")]
    assert len(vasijas) == 2 and all(n["LootTable"] == "heraldia:medianas/templete/vasija" for n in vasijas)


def test_logros_propios_del_lote_2(reg):
    advs, lang = logros.build(reg, [], MODS)
    for mid, m in MODS:
        for ex in getattr(m, "LOGROS", ()):
            adv = advs[f"medianas/{mid}/{ex['id']}"]
            assert adv["parent"] == "heraldia:medianas/descubrir"
            assert adv["rewards"]["experience"] == logros.XP["mediana_extra"]
            k = f"advancements.heraldia.medianas.{mid}.{ex['id']}.title"
            assert lang["es_es"][k] == ex["titulo"][0] and lang["en_us"][k] == ex["titulo"][1]
            if ex.get("tabla"):
                (crit,) = adv["criteria"].values()
                assert crit["conditions"]["loot_tables"] == f"heraldia:medianas/{mid}/{ex['tabla']}"
    assert {p for p in advs if p.startswith("medianas/") and p.count("/") == 2} == {
        "medianas/molino/molienda", "medianas/pescador/pesca", "medianas/cazadores/pieles", "medianas/templete/custodios",
        "medianas/choza_mago/tratos", "medianas/choza_mago/malvado"}
    custodios = advs["medianas/templete/custodios"]["criteria"]
    assert set(custodios) == {"skeleton", "husk"}
    assert custodios["husk"]["conditions"]["entity"]["predicate"]["minecraft:entity_tags"] == {"all_of": ["heraldia_mediana.templete"]}


def test_logro_mal_definido():
    class ConLogro(_Falsa):
        LOGROS = [dict(id="x", icono="minecraft:cod", titulo=("a", "b"), descripcion=("c", "d"), tabla="no_existe"),
                  dict(id="y", icono="minecraft:cod", titulo=("a", "b"))]
    errs = _errores(ConLogro)
    assert any("no está en LOOT" in e for e in errs) and any("logro 'y'" in e for e in errs)


def test_bioma_vecinos_solo_en_el_pescador_y_en_rango():
    """Las playas son franjas: solo el pescador pide menos vecinos a la búsqueda de bioma de su rejilla."""
    assert {mid: m.BIOMA_VECINOS for mid, m in MODS if hasattr(m, "BIOMA_VECINOS")} == {"pescador": 2}

    class Franja(_Falsa):
        BIOMA_VECINOS = 0
    assert any("BIOMA_VECINOS" in e for e in _errores(Franja))
