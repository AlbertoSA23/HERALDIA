"""Entradas a mina (heraldia:minas/<tamaño>/<estilo>): bocas de mina en laderas reales que bajan de verdad a una
galería propia, en tres tamaños y cinco estilos por bioma (ver planos.py y superficie.py).

  tamaños  pequena (boca con vías, vagoneta y faroles), mediana (campamento minero: cabaña del capataz, montón de
           mineral, vagoneta de carga y fundición) y grande (complejo con la torre de extracción y su polea, vías y un
           pozo vertical con escalera de caracol hasta una red mayor de dos niveles).
  estilos  montana (roble y piedra), taiga (abeto; también la nieve), desierto (arenisca), badlands (terracota) y
           picos (pizarra profunda, en los picos), cada uno con dos variantes (a, b: el patio reflejado y otra galería).

Cada plantilla es una sola pieza: el patio y su cimiento, la boca, la bajada y la galería, sin caja (lo excavado lleva
su forro y dos capas de casco; fuera, nada). La coloca el tipo propio heraldia:mina_entrada (Java, minas/), que busca
una ladera: delante de la boca terreno seco y casi llano, detrás el monte más alto que el túnel y encima de la galería
roca bastante (las muestras de `techo`). Su colocación es la rejilla heraldia:rejilla (grupo minas/<tamaño>, opciones
minas.entradas.*) y la regla de minas/Minas.java (nunca junto a aldeas, únicas, medianas ni estructuras vanilla que
asoman; entre los tres tamaños, la distancia mínima de las medianas).

Además, minas.vanilla.multiplicador multiplica la frecuencia de las minas abandonadas vanilla en los chunks nuevos
(heraldia:minas_vanilla, que sustituye la colocación del structure_set minecraft:mineshafts; con 1, idéntica a vanilla).

Ids: estructura, plantilla y pool heraldia:minas/<tamaño>/<estilo>/<variante> (una estructura por variante: cada una
sabe dónde está su boca), structure_set heraldia:minas/<tamaño> (sus 10 estructuras; el bioma elige el estilo), etiquetas
de estructura #heraldia:minas y #heraldia:minas/<tamaño>, etiquetas de biomas #heraldia:minas (todos) y
#heraldia:minas/<estilo>, botín heraldia:minas/<tabla>, textos heraldia.minas.*.
"""
import functools
from core import NS, nsid
from . import planos, botin as _botin
from .botin import LOOT

PREFIJO = "minas"
TAMANOS = ("pequena", "mediana", "grande")
NOMBRE = {"pequena": ("Boca de mina", "Mine Adit"), "mediana": ("Campamento minero", "Mining Camp"),
          "grande": ("Complejo minero", "Mining Complex")}
# separación entre dos del mismo tamaño (bloques): la pequeña es la de la opción minas.entradas.separacion_bloques y
# las otras guardan la proporción (GridPlacement escala las tres con la opción)
SEPARACION = {"pequena": 768, "mediana": 1152, "grande": 1920}
SEPARACION_RANGO = (256, 4000)
SALT = {"pequena": 1907261101, "mediana": 1907261102, "grande": 1907261103}
BIOMA_Y = 96
EXCLUSION_ALDEAS_VANILLA = 8
VARIANTES = ("a", "b")

# Estilos por bioma (listas vanilla; las etiquetas extra siguen las reglas de biomas.CONVENCIONALES).
ESTILOS = {
    "montana": dict(
        biomas=["windswept_hills", "windswept_gravelly_hills", "windswept_forest", "meadow", "cherry_grove"],
        paleta=dict(madera="oak", tronco="minecraft:oak_log", tablas="oak_planks", cama="brown",
                    muro=["cobblestone", "cobblestone", "cobblestone", "mossy_cobblestone", "stone_bricks"],
                    techo=["cobblestone", "stone_bricks"], suelo=["cobblestone", "stone_bricks", "polished_andesite"],
                    escalon_piedra="cobblestone_stairs", casco="stone", casco_hondo="deepslate",
                    patio=["gravel", "packed_mud", "packed_mud", "cobblestone"], cimiento=["cobblestone", "mossy_cobblestone"],
                    mineral=["gravel", "cobblestone", "coal_ore", "iron_ore", "copper_ore", "stone"],
                    vetas=["coal_ore", "coal_ore", "iron_ore", "copper_ore"],
                    vetas_ricas=["iron_ore", "coal_ore", "copper_ore", "gold_ore", "redstone_ore", "lapis_ore"])),
    "taiga": dict(
        biomas=["taiga", "snowy_taiga", "old_growth_pine_taiga", "old_growth_spruce_taiga", "grove", "snowy_slopes"],
        convencionales=["minecraft:is_taiga", "c:is_taiga"],
        paleta=dict(madera="spruce", tronco="minecraft:spruce_log", tablas="spruce_planks", cama="blue",
                    muro=["cobblestone", "cobblestone", "stone_bricks", "mossy_stone_bricks"],
                    techo=["cobblestone", "stone_bricks"], suelo=["cobblestone", "stone_bricks"],
                    escalon_piedra="cobblestone_stairs", casco="stone", casco_hondo="deepslate",
                    patio=["gravel", "packed_mud", "cobblestone", "packed_mud"], cimiento=["cobblestone", "stone_bricks"],
                    mineral=["gravel", "cobblestone", "coal_ore", "iron_ore", "iron_ore", "stone"],
                    vetas=["coal_ore", "iron_ore", "iron_ore", "copper_ore"],
                    vetas_ricas=["iron_ore", "coal_ore", "gold_ore", "lapis_ore", "redstone_ore", "copper_ore"])),
    "desierto": dict(
        biomas=["desert"], convencionales=["c:is_desert"],
        paleta=dict(madera="birch", tronco="minecraft:birch_log", tablas="birch_planks", cama="yellow",
                    muro=["sandstone", "sandstone", "cut_sandstone", "smooth_sandstone"],
                    techo=["cut_sandstone", "sandstone"], suelo=["sandstone", "smooth_sandstone"],
                    escalon_piedra="sandstone_stairs", casco="sandstone", casco_hondo="stone",
                    patio=["smooth_sandstone", "sandstone", "gravel"], cimiento=["sandstone", "cut_sandstone"],
                    mineral=["gravel", "sandstone", "coal_ore", "iron_ore", "copper_ore", "gold_ore"],
                    vetas=["coal_ore", "iron_ore", "copper_ore", "copper_ore"],
                    vetas_ricas=["gold_ore", "iron_ore", "copper_ore", "coal_ore", "lapis_ore", "redstone_ore"])),
    "badlands": dict(
        biomas=["badlands", "eroded_badlands", "wooded_badlands"], convencionales=["minecraft:is_badlands", "c:is_badlands"],
        paleta=dict(madera="dark_oak", tronco="minecraft:dark_oak_log", tablas="dark_oak_planks", cama="red",
                    muro=["terracotta", "orange_terracotta", "red_terracotta", "yellow_terracotta", "brown_terracotta",
                          "white_terracotta"],
                    techo=["terracotta", "red_sandstone"], suelo=["red_sandstone", "smooth_red_sandstone"],
                    escalon_piedra="red_sandstone_stairs", casco="terracotta", casco_hondo="stone",
                    patio=["smooth_red_sandstone", "red_sandstone", "gravel"], cimiento=["red_sandstone", "cut_red_sandstone"],
                    mineral=["gravel", "terracotta", "gold_ore", "iron_ore", "coal_ore", "red_sandstone"],
                    vetas=["gold_ore", "coal_ore", "iron_ore", "gold_ore"],
                    vetas_ricas=["gold_ore", "gold_ore", "iron_ore", "redstone_ore", "copper_ore", "coal_ore"])),
    "picos": dict(
        biomas=["jagged_peaks", "frozen_peaks", "stony_peaks"], convencionales=["c:is_mountain/peak"],
        paleta=dict(madera="spruce", tronco="minecraft:stripped_spruce_log", tablas="spruce_planks", cama="light_gray",
                    muro=["cobbled_deepslate", "cobbled_deepslate", "deepslate_bricks", "deepslate_tiles"],
                    techo=["deepslate_bricks", "cobbled_deepslate"], suelo=["polished_deepslate", "cobbled_deepslate"],
                    escalon_piedra="cobbled_deepslate_stairs", casco="stone", casco_hondo="deepslate",
                    patio=["gravel", "cobbled_deepslate", "polished_andesite"], cimiento=["cobbled_deepslate", "deepslate_bricks"],
                    mineral=["gravel", "cobbled_deepslate", "deepslate_iron_ore", "deepslate_coal_ore", "deepslate_copper_ore"],
                    vetas=["deepslate_coal_ore", "deepslate_iron_ore", "deepslate_copper_ore", "deepslate_iron_ore"],
                    vetas_ricas=["deepslate_iron_ore", "deepslate_gold_ore", "deepslate_redstone_ore", "deepslate_lapis_ore",
                                 "deepslate_copper_ore", "deepslate_coal_ore"])),
}

# Logros: una cadena pequeña -> mediana -> grande (logros.py los añade bajo la raíz).
LOGROS = {
    "pequena": dict(icono="minecraft:minecart", titulo=("Bajo la ladera", "Under the Hillside"),
                    descripcion=("Entra en una boca de mina de Heraldia", "Enter a Heraldia mine adit")),
    "mediana": dict(icono="minecraft:iron_pickaxe", titulo=("Campamento minero", "Mining Camp"),
                    descripcion=("Entra en un campamento minero", "Enter a mining camp")),
    "grande": dict(icono="minecraft:chest_minecart", titulo=("Señor de las galerías", "Lord of the Galleries"),
                   descripcion=("Entra en un complejo minero con su torre de extracción",
                                "Enter a mining complex with its headframe")),
}
XP = {"pequena": 20, "mediana": 40, "grande": 80}

LANG = {
    "es_es": {f"{NS}.minas.{t}.nombre": NOMBRE[t][0] for t in TAMANOS},
    "en_us": {f"{NS}.minas.{t}.nombre": NOMBRE[t][1] for t in TAMANOS},
}
for _t, ((_es1, _en1), (_es2, _en2)) in planos.sup.CARTELES.items():
    LANG["es_es"].update({f"{NS}.minas.cartel.{_t}.1": _es1, f"{NS}.minas.cartel.{_t}.2": _es2})
    LANG["en_us"].update({f"{NS}.minas.cartel.{_t}.1": _en1, f"{NS}.minas.cartel.{_t}.2": _en2})

MAX_ENTIDADES = 6
MAX_GENERADORES = {"pequena": 0, "mediana": 1, "grande": 1}


def salt(tam):
    return SALT[tam]


def plantilla(tam, estilo, variante):
    return f"{PREFIJO}/{tam}/{estilo}/{variante}"


def tabla_id(tabla):
    return f"{NS}:{PREFIJO}/{tabla}"


# ------------------------------------------------------------------ construcción
@functools.lru_cache(maxsize=None)
def obra(tam, estilo, variante):
    """Obra de una variante (cacheada: la construyen build, la auditoría y las pruebas) y sus metadatos para Java."""
    pal = ESTILOS[estilo]["paleta"]
    o = planos.construir(tam, estilo, variante, pal, plantilla(tam, estilo, variante))
    x0, y0, z0, *_ = o.t.bounds()
    sh = lambda x, y, z: (x - x0, y - y0, z - z0)
    px, pz = planos.TAMANOS[tam]["patio"]
    meta = dict(entrada=list(sh(0, 0, 0)), patio=[-px - x0, -pz - z0, px - x0, -1 - z0],
                techo=[[x - x0, z - z0, y + 1] for (x, z), y in o.muestras_techo()])
    return o, (x0, y0, z0), meta


def build(reg, tam):
    """Plantillas y pools de un tamaño (una parte de pack.build_all) y los errores de su auditoría."""
    from . import auditoria
    for estilo in ESTILOS:
        for v in VARIANTES:     # una estructura por variante: cada una con la posición de su boca en la plantilla
            o, _, _ = obra(tam, estilo, v)
            reg.warnings += [f"{o.t.name}: {e}" for e in auditoria.errores(o, tam)]
            reg.pool(plantilla(tam, estilo, v), [(reg.add(_copia(o.t), f"mina:{tam}"), 1, "rigid", None)])


def _copia(t):
    """Otra plantilla con los mismos bloques (Registry.add la normaliza y le añade cadenas: la obra en caché, que usan
    la auditoría y los metadatos del Java, se queda en coordenadas de diseño)."""
    from core import Template
    c = Template(t.name)
    c.blocks, c.entities, c.jigsaws = dict(t.blocks), list(t.entities), [dict(j) for j in t.jigsaws]
    c.sin_auditoria_generica = True
    return c


# ------------------------------------------------------------------ escritura
def estructura(tam, estilo, variante, biomes):
    _, _, meta = obra(tam, estilo, variante)
    return {"type": f"{NS}:mina_entrada", "biomes": biomes, "step": "surface_structures", "spawn_overrides": {},
            "terrain_adaptation": "none", "start_pool": nsid(plantilla(tam, estilo, variante)), **meta}


def colocacion(tam):
    """heraldia:rejilla del tamaño (spacing y separation de por defecto; el Java los recalcula con la configuración)
    con la candidata buscada en los biomas de todos los estilos (como las medianas)."""
    spacing = round(SEPARACION[tam] / 16)
    return {"type": f"{NS}:rejilla", "grupo": f"{PREFIJO}/{tam}", "spacing": spacing, "separation": spacing // 3,
            "salt": salt(tam), "bioma": f"{NS}:{PREFIJO}", "bioma_y": BIOMA_Y,
            "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": EXCLUSION_ALDEAS_VANILLA}}


# Minas abandonadas vanilla (structure_set minecraft:mineshafts de 26.3): la misma colocación con el tipo propio, que
# multiplica la frecuencia por minas.vanilla.multiplicador (1 = vanilla exacta: misma rejilla, sal y sorteo).
VANILLA_SET = {"structures": [{"structure": "minecraft:mineshaft", "weight": 1},
                              {"structure": "minecraft:mineshaft_mesa", "weight": 1}],
               "placement": {"type": f"{NS}:minas_vanilla", "frequency": 0.004,
                             "frequency_reduction_method": "legacy_type_3", "salt": 0, "separation": 0, "spacing": 1}}
MULTIPLICADOR = (2.0, 1, 5)          # por defecto, mínimo y máximo de minas.vanilla.multiplicador


def write(out, jdump):
    """Estructuras, etiquetas de biomas y de estructura, structure_sets, botín y la colocación de las minas vanilla."""
    import biomas
    from writer import lootr_aware
    todas = []
    biomas.CONVENCIONALES[PREFIJO] = sorted({c for d in ESTILOS.values() for c in d.get("convencionales", [])})
    biomas.etiqueta(out, PREFIJO, sorted({b for d in ESTILOS.values() for b in d["biomas"]}))
    for estilo, d in ESTILOS.items():
        if d.get("convencionales"):
            biomas.CONVENCIONALES[f"{PREFIJO}/{estilo}"] = list(d["convencionales"])
        biomas.etiqueta(out, f"{PREFIJO}/{estilo}", d["biomas"])
    for tam in TAMANOS:
        ids = []
        for estilo in ESTILOS:
            for v in VARIANTES:
                jdump(out, f"data/{NS}/worldgen/structure/{plantilla(tam, estilo, v)}.json",
                      estructura(tam, estilo, v, f"#{NS}:{PREFIJO}/{estilo}"))
                ids.append(f"{NS}:{plantilla(tam, estilo, v)}")
        jdump(out, f"data/{NS}/worldgen/structure_set/{PREFIJO}/{tam}.json",
              {"structures": [{"structure": s, "weight": 1} for s in ids], "placement": colocacion(tam)})
        jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIJO}/{tam}.json", {"values": ids})
        todas += ids
    jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIJO}.json", {"values": todas})
    for name, tabla in LOOT.items():
        jdump(out, f"data/{NS}/loot_table/{PREFIJO}/{name}.json", lootr_aware(tabla))
    jdump(out, "data/minecraft/worldgen/structure_set/mineshafts.json", VANILLA_SET)
    return lang()


def lang():
    return {k: dict(v) for k, v in LANG.items()}


def tablas():
    """{id corto: tabla} de todo el botín de las minas (para validate_loot)."""
    return {f"{PREFIJO}/{n}": t for n, t in LOOT.items()}


def estructuras():
    """Ids de todas las estructuras de las minas (para /heraldia info y las pruebas)."""
    return [f"{NS}:{plantilla(t, e, v)}" for t in TAMANOS for e in ESTILOS for v in VARIANTES]
