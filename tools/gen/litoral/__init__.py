"""Faros y naufragios de la costa (heraldia:costa/<tipo>/<estilo>/<variante>, T42).

  faro       torre de 28 bloques en tierra firme junto al agua, con la luz siempre encendida arriba (lámpara de
             redstone sobre un bloque de redstone, sin circuitos), la casa del farero y un embarcadero sobre pilotes.
             Variantes: a, torre octogonal con bandas y el farero (aldeano quieto con tratos marinos); b, torre cuadrada a
             franjas, la casa al otro lado y sin nadie.
  naufragio  galeón de Heraldia partido, con un mástil en pie y su vela rota, el muñón de otro y el camarote del capitán
             a popa. Variantes: a, encallado en la playa (la proa en la arena, la popa en el agua); b, semihundido en
             aguas poco profundas (la bodega inundada, con un ahogado anclado).

Estilos según la costa (el clima: el bioma de la tierra y el del mar de delante): templada (piedra y ladrillo; roble),
calida (arenisca; jungla), fria (pizarra y piedra oscura; roble oscuro) y nevada (madera de abeto y nieve). Cada estilo
dice en `climas` qué parejas (tierra, mar) le tocan; las cuatro se reparten todas las parejas sin solaparse
(test_costa lo comprueba), así que el structure_set de cada tipo sale con el estilo de su costa.

Cada plantilla es una sola pieza que coloca el tipo propio heraldia:costa (Java, costa/): busca la orilla alrededor de la
candidata (tierra firme y baja detrás, agua delante, con la profundidad que pide la variante), gira la plantilla para
que su +z mire al mar y pone su `ancla` en la orilla. El faro va a la altura del terreno (sus cimientos y pilotes bajan
hasta el suelo con heraldia:acueducto_hasta_el_suelo); el naufragio, con la fila `fila_mar` de la plantilla en el nivel
del mar - 1. Bajo esa fila la plantilla no tiene aire (el agua y la arena de dentro del casco se quedan: nada se
derrama), lo comprueba auditoria.py. Colocación: heraldia:rejilla (grupo costa/<tipo>, opciones faros.* y naufragios.*)
con la candidata en las playas y la regla de costa/Costa.java (la de las minas: nunca junto a aldeas, únicas, medianas,
minas ni estructuras vanilla o de otros mods que asoman; entre faros y naufragios, la distancia mínima de las medianas).

Ids: estructura, plantilla y pool heraldia:costa/<tipo>/<estilo>/<variante>, structure_set heraldia:costa/<tipo>,
etiquetas de estructura #heraldia:costa y #heraldia:costa/<tipo>, etiquetas de biomas #heraldia:litoral (las playas,
para la rejilla), #heraldia:litoral/<estilo> (su tierra), #heraldia:litoral/tierra/<grupo> y
#heraldia:litoral/mar/<grupo> (heraldia:costa es la de la familia de aldeas de la costa), botín
heraldia:costa/<tabla> (lo repone loot/Reposicion), textos heraldia.costa.*.
"""
import functools
from core import NS, nsid
from . import obras
from .botin import LOOT

PREFIJO = "costa"
# Las etiquetas de biomas van aparte: heraldia:costa ya es la de la familia de aldeas de la costa.
BIOMAS = "litoral"
TIPOS = ("faro", "naufragio")
VARIANTES = ("a", "b")
NOMBRE = {"faro": ("Faro", "Lighthouse"), "naufragio": ("Galeón naufragado", "Wrecked Galleon")}
# Opciones de cada tipo (opciones.py): <OPCION>.activado y <OPCION>.separacion_bloques
OPCION = {"faro": "faros", "naufragio": "naufragios"}
SEPARACION = {"faro": 1024, "naufragio": 768}
SEPARACION_RANGO = (256, 4000)
SALT = {"faro": 1907261201, "naufragio": 1907261202}
EXCLUSION_ALDEAS_VANILLA = 8
BIOMA_VECINOS = 2                  # las playas son franjas de pocas decenas de bloques (como la cabaña de pescador)
MODO = {("faro", "a"): "faro", ("faro", "b"): "faro", ("naufragio", "a"): "encallado", ("naufragio", "b"): "hundido"}

# Grupos de biomas de tierra y de mar (listas vanilla de 26.3). Cada bioma de tierra de la costa está en un solo grupo.
TIERRA = {
    "nevada": ["snowy_beach", "snowy_plains", "snowy_taiga", "ice_spikes", "grove", "snowy_slopes", "frozen_peaks",
               "jagged_peaks"],
    "rocosa": ["stony_shore", "windswept_hills", "windswept_gravelly_hills", "windswept_forest", "stony_peaks", "taiga",
               "old_growth_pine_taiga", "old_growth_spruce_taiga"],
    "calida": ["desert", "savanna", "savanna_plateau", "windswept_savanna", "badlands", "eroded_badlands",
               "wooded_badlands", "jungle", "sparse_jungle", "bamboo_jungle", "mangrove_swamp"],
    "templada": ["beach", "plains", "sunflower_plains", "forest", "flower_forest", "birch_forest",
                 "old_growth_birch_forest", "dark_forest", "pale_garden", "meadow", "cherry_grove", "swamp"],
}
MAR = {
    "todos": ["ocean", "deep_ocean", "cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean",
              "lukewarm_ocean", "deep_lukewarm_ocean", "warm_ocean"],
    "calido": ["lukewarm_ocean", "deep_lukewarm_ocean", "warm_ocean"],
    "templado": ["ocean", "deep_ocean"],
    "frio": ["cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean"],
}
MAR["no_calido"] = MAR["templado"] + MAR["frio"]
# Candidata de la rejilla: en una playa (de ahí se busca la orilla).
PLAYAS = ["beach", "snowy_beach", "stony_shore"]

# Estilos: parejas (tierra, mar) del clima y su paleta (faro y naufragio).
ESTILOS = {
    "templada": dict(
        climas=[("templada", "templado")],
        faro=dict(muro="stone_bricks", banda="bricks", zocalo="mossy_stone_bricks", esquina="chiseled_stone_bricks",
                  cimiento=["stone_bricks", "cobblestone", "stone_bricks", "andesite"], losa="stone_brick_slab",
                  escalon="stone_brick_stairs", madera="spruce", tronco="spruce_log", casa="spruce_planks",
                  teja="dark_oak_stairs", cumbrera="dark_oak_planks", cama="blue", aldeano="plains", nieve=False),
        barco=dict(madera="oak", tronco="spruce_log", banda="dark_oak_planks", vela="white_wool", nieve=False)),
    "calida": dict(
        climas=[("calida", "todos"), ("templada", "calido"), ("rocosa", "calido")],
        faro=dict(muro="smooth_sandstone", banda="cut_red_sandstone", zocalo="cut_sandstone", esquina="chiseled_sandstone",
                  cimiento=["sandstone", "smooth_sandstone", "sandstone", "cut_sandstone"], losa="smooth_sandstone_slab",
                  escalon="sandstone_stairs", madera="jungle", tronco="jungle_log", casa="birch_planks",
                  teja="jungle_stairs", cumbrera="jungle_planks", cama="yellow", aldeano="desert", nieve=False),
        barco=dict(madera="jungle", tronco="birch_log", banda="acacia_planks", vela="yellow_wool", nieve=False)),
    "fria": dict(
        climas=[("rocosa", "no_calido"), ("templada", "frio")],
        faro=dict(muro="deepslate_bricks", banda="polished_blackstone_bricks", zocalo="cobbled_deepslate",
                  esquina="polished_deepslate", cimiento=["cobbled_deepslate", "deepslate_tiles", "cobbled_deepslate", "tuff"],
                  losa="deepslate_tile_slab", escalon="deepslate_tile_stairs", madera="dark_oak", tronco="dark_oak_log",
                  casa="dark_oak_planks", teja="deepslate_tile_stairs", cumbrera="deepslate_tiles", cama="gray",
                  aldeano="taiga", nieve=False),
        barco=dict(madera="dark_oak", tronco="spruce_log", banda="spruce_planks", vela="gray_wool", nieve=False)),
    "nevada": dict(
        climas=[("nevada", "todos")],
        faro=dict(muro="spruce_planks", banda="stripped_spruce_wood", zocalo="cobblestone", esquina="stripped_spruce_log",
                  cimiento=["cobblestone", "stone_bricks", "cobblestone", "mossy_cobblestone"], losa="spruce_slab",
                  escalon="spruce_stairs", madera="spruce", tronco="spruce_log", casa="spruce_planks",
                  teja="spruce_stairs", cumbrera="dark_oak_planks", cama="white", aldeano="snow", nieve=True),
        barco=dict(madera="spruce", tronco="dark_oak_log", banda="dark_oak_planks", vela="light_gray_wool", nieve=True)),
}

# Logros: entrar en un faro, en un naufragio y abrir el cofre del camarote (logros.py los cuelga de la raíz).
LOGROS = {
    "faro": dict(icono="minecraft:spyglass", titulo=("Luz en la costa", "Light on the Coast"),
                 descripcion=("Encuentra un faro de Heraldia", "Find a Heraldia lighthouse"),
                 criterio=("faro", f"#{NS}:costa/faro")),
    "naufragio": dict(icono="minecraft:oak_boat", titulo=("Restos del naufragio", "Flotsam and Jetsam"),
                      descripcion=("Encuentra un galeón naufragado en la costa", "Find a galleon wrecked on the coast"),
                      criterio=("naufragio", f"#{NS}:costa/naufragio")),
    "camarote": dict(icono="minecraft:compass", padre="naufragio", titulo=("El cofre del capitán", "The Captain's Chest"),
                     descripcion=("Abre el cofre del camarote de un galeón naufragado",
                                  "Open the cabin chest of a wrecked galleon"),
                     tabla="camarote"),
}
XP = {"faro": 20, "naufragio": 20, "camarote": 30}

TEXTOS = {
    "farero": ("Farero", "Lighthouse Keeper"),
}

MAX_ENTIDADES = 2
ALTURA_FARO = (20, 35)


def salt(tipo):
    return SALT[tipo]


def plantilla(tipo, estilo, variante):
    return f"{PREFIJO}/{tipo}/{estilo}/{variante}"


def tabla_id(tabla):
    return f"{NS}:{PREFIJO}/{tabla}"


# ------------------------------------------------------------------ construcción
@functools.lru_cache(maxsize=None)
def obra(tipo, estilo, variante):
    """Obra de una variante (cacheada: la construyen build, la auditoría y las pruebas) y sus metadatos para Java (en
    coordenadas de la plantilla ya normalizada)."""
    pal = ESTILOS[estilo]["faro" if tipo == "faro" else "barco"]
    o = obras.construir(tipo, variante, pal, plantilla(tipo, estilo, variante))
    x0, y0, z0, *_ = o.t.bounds()
    ax, az = o.ancla
    meta = dict(modo=MODO[(tipo, variante)], ancla=[ax - x0, az - z0], tierra=list(o.tierra), mar=list(o.mar),
                fila_mar=(o.fila_mar - y0) if o.fila_mar is not None else -1)
    return o, (x0, y0, z0), meta


def build(reg, tipo):
    """Plantillas y pools de un tipo (una parte de pack.build_all) y los errores de su auditoría."""
    from . import auditoria
    for estilo in ESTILOS:
        for v in VARIANTES:
            o, _, _ = obra(tipo, estilo, v)
            reg.warnings += [f"{o.t.name}: {e}" for e in auditoria.errores(o, tipo)]
            reg.pool(plantilla(tipo, estilo, v), [(reg.add(_copia(o.t), f"costa:{tipo}"), 1, "rigid", procesadores(tipo))])


def _copia(t):
    """Otra plantilla con los mismos bloques (Registry.add la normaliza: la obra en caché, que usan la auditoría y los
    metadatos del Java, se queda en coordenadas de diseño). La auditoría genérica de apoyos sí la recorre."""
    from core import Template
    c = Template(t.name)
    c.blocks, c.entities, c.jigsaws = dict(t.blocks), list(t.entities), [dict(j) for j in t.jigsaws]
    return c


# Procesador de cada tipo: lo que va en la fila inferior de la plantilla (cimientos y pilotes del faro; quilla y fondo
# del casco del naufragio) baja hasta el suelo firme atravesando el agua. Uno por tipo: los tablones del embarcadero del
# faro no deben bajar (los del fondo del casco, sí).
PROFUNDIDAD_MAX = 12


def procesadores(tipo):
    return f"{NS}:{PREFIJO}/{tipo}_suelo"


def bajan(tipo):
    """Bloques de la fila inferior que el procesador del tipo alarga hasta el suelo (los de todas sus paletas)."""
    out = set()
    for d in ESTILOS.values():
        if tipo == "faro":
            out |= {f"minecraft:{x}" for x in d["faro"]["cimiento"]} | {f"minecraft:{d['faro']['tronco']}"}
        else:
            out |= {f"minecraft:{d['barco']['tronco']}", f"minecraft:{d['barco']['madera']}_planks"}
    return sorted(out)


# ------------------------------------------------------------------ escritura
def estructura(tipo, estilo, variante):
    _, _, meta = obra(tipo, estilo, variante)
    climas = [{"tierra": f"#{NS}:{BIOMAS}/tierra/{t}", "mar": f"#{NS}:{BIOMAS}/mar/{m}"}
              for t, m in ESTILOS[estilo]["climas"]]
    return {"type": f"{NS}:costa", "biomes": f"#{NS}:{BIOMAS}/{estilo}", "step": "surface_structures",
            "spawn_overrides": {}, "terrain_adaptation": "none", "start_pool": nsid(plantilla(tipo, estilo, variante)),
            "climas": climas, **meta}


def colocacion(tipo):
    """heraldia:rejilla del tipo (spacing de por defecto; el Java lo recalcula con la configuración) con la candidata
    buscada en las playas."""
    spacing = round(SEPARACION[tipo] / 16)
    return {"type": f"{NS}:rejilla", "grupo": f"{PREFIJO}/{tipo}", "spacing": spacing, "separation": spacing // 3,
            "salt": salt(tipo), "bioma": f"{NS}:{BIOMAS}", "bioma_vecinos": BIOMA_VECINOS,
            "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": EXCLUSION_ALDEAS_VANILLA}}


def tierra_de(estilo):
    return sorted({b for t, _ in ESTILOS[estilo]["climas"] for b in TIERRA[t]})


def write(out, jdump):
    """Estructuras, etiquetas de biomas y de estructura, structure_sets, el procesador y el botín."""
    import biomas
    from writer import lootr_aware, hasta_el_suelo
    import tesoro
    biomas.etiqueta(out, BIOMAS, PLAYAS)
    for g, lista in TIERRA.items():
        biomas.etiqueta(out, f"{BIOMAS}/tierra/{g}", lista)
    for g, lista in MAR.items():
        biomas.etiqueta(out, f"{BIOMAS}/mar/{g}", lista)
    for estilo in ESTILOS:
        biomas.etiqueta(out, f"{BIOMAS}/{estilo}", tierra_de(estilo))
    for tipo in TIPOS:
        jdump(out, f"data/{NS}/worldgen/processor_list/{PREFIJO}/{tipo}_suelo.json",
              {"processors": [hasta_el_suelo(bajan(tipo), PROFUNDIDAD_MAX)]})
    todas = []
    for tipo in TIPOS:
        ids = []
        for estilo in ESTILOS:
            for v in VARIANTES:
                jdump(out, f"data/{NS}/worldgen/structure/{plantilla(tipo, estilo, v)}.json", estructura(tipo, estilo, v))
                ids.append(f"{NS}:{plantilla(tipo, estilo, v)}")
        jdump(out, f"data/{NS}/worldgen/structure_set/{PREFIJO}/{tipo}.json",
              {"structures": [{"structure": s, "weight": 1} for s in ids], "placement": colocacion(tipo)})
        jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIJO}/{tipo}.json", {"values": ids})
        todas += ids
    jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIJO}.json", {"values": todas})
    for name, tabla in LOOT.items():
        if name == "camarote":          # una pista del tesoro, rara, en el cofre del capitán
            tabla = tesoro.con_pista(tabla, PREFIJO)
        jdump(out, f"data/{NS}/loot_table/{PREFIJO}/{name}.json", lootr_aware(tabla))
    return lang()


LANG = {"es_es": {}, "en_us": {}}
for _t in TIPOS:
    LANG["es_es"][f"{NS}.costa.{_t}.nombre"], LANG["en_us"][f"{NS}.costa.{_t}.nombre"] = NOMBRE[_t]
for _k, (_es, _en) in TEXTOS.items():
    LANG["es_es"][f"{NS}.costa.{_k}"], LANG["en_us"][f"{NS}.costa.{_k}"] = _es, _en
# /heraldia info (los de status, mapas web y review van con los demás en admin.py)
LANG["es_es"][f"{NS}.info.costa"] = "Costa: faros %s, cada %s bloques; galeones naufragados %s, cada %s bloques; %s estructuras"
LANG["en_us"][f"{NS}.info.costa"] = "Coast: lighthouses %s, every %s blocks; wrecked galleons %s, every %s blocks; %s structures"


def lang():
    return {k: dict(v) for k, v in LANG.items()}


def tablas():
    """{id corto: tabla} de todo el botín de la costa (para validate_loot)."""
    return {f"{PREFIJO}/{n}": t for n, t in LOOT.items()}


def estructuras():
    """Ids de todas las estructuras de la costa (para /heraldia info y las pruebas)."""
    return [f"{NS}:{plantilla(t, e, v)}" for t in TIPOS for e in ESTILOS for v in VARIANTES]
