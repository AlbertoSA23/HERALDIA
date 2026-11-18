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
from . import constructions
from .chest_loot import LOOT

PREFIX = "costa"
# Las etiquetas de biomas van aparte: heraldia:costa ya es la de la familia de aldeas de la costa.
BIOME_MAP = "litoral"
KINDS = ("faro", "naufragio")
VARIANTS = ("a", "b")
DISPLAY_NAME = {"faro": ("Faro", "Lighthouse"), "naufragio": ("Galeón naufragado", "Wrecked Galleon")}
# Opciones de cada tipo (opciones.py): <OPCION>.activado y <OPCION>.separacion_bloques
OPTION = {"faro": "faros", "naufragio": "naufragios"}
SEPARATION = {"faro": 1024, "naufragio": 768}
SEPARATION_RANGE = (256, 4000)
SALT = {"faro": 1907261201, "naufragio": 1907261202}
VANILLA_VILLAGE_EXCLUSION = 8
BIOME_NEIGHBORS = 2                  # las playas son franjas de pocas decenas de bloques (como la cabaña de pescador)
MODE = {("faro", "a"): "faro", ("faro", "b"): "faro", ("naufragio", "a"): "encallado", ("naufragio", "b"): "hundido"}

# Grupos de biomas de tierra y de mar (listas vanilla de 26.3). Cada bioma de tierra de la costa está en un solo grupo.
LAND = {
    "nevada": ["snowy_beach", "snowy_plains", "snowy_taiga", "ice_spikes", "grove", "snowy_slopes", "frozen_peaks",
               "jagged_peaks"],
    "rocosa": ["stony_shore", "windswept_hills", "windswept_gravelly_hills", "windswept_forest", "stony_peaks", "taiga",
               "old_growth_pine_taiga", "old_growth_spruce_taiga"],
    "calida": ["desert", "savanna", "savanna_plateau", "windswept_savanna", "badlands", "eroded_badlands",
               "wooded_badlands", "jungle", "sparse_jungle", "bamboo_jungle", "mangrove_swamp"],
    "templada": ["beach", "plains", "sunflower_plains", "forest", "flower_forest", "birch_forest",
                 "old_growth_birch_forest", "dark_forest", "pale_garden", "meadow", "cherry_grove", "swamp"],
}
SEA = {
    "todos": ["ocean", "deep_ocean", "cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean",
              "lukewarm_ocean", "deep_lukewarm_ocean", "warm_ocean"],
    "calido": ["lukewarm_ocean", "deep_lukewarm_ocean", "warm_ocean"],
    "templado": ["ocean", "deep_ocean"],
    "frio": ["cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean"],
}
SEA["no_calido"] = SEA["templado"] + SEA["frio"]
# Candidata de la rejilla: en una playa (de ahí se busca la orilla).
BEACHES = ["beach", "snowy_beach", "stony_shore"]

# Estilos: parejas (tierra, mar) del clima y su paleta (faro y naufragio).
STYLES = {
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
ADVANCEMENTS = {
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

TEXTS = {
    "farero": ("Farero", "Lighthouse Keeper"),
}

MAX_ENTITIES = 2
LIGHTHOUSE_HEIGHT = (20, 35)


def salt(kind):
    return SALT[kind]


def template(kind, style, variant):
    return f"{PREFIX}/{kind}/{style}/{variant}"


def table_ident(tbl):
    return f"{NS}:{PREFIX}/{tbl}"


# ------------------------------------------------------------------ construcción
@functools.lru_cache(maxsize=None)
def construction(kind, style, variant):
    """Obra de una variante (cacheada: la construyen build, la auditoría y las pruebas) y sus metadatos para Java (en
    coordenadas de la plantilla ya normalizada)."""
    pal = STYLES[style]["faro" if kind == "faro" else "barco"]
    o = constructions.construct(kind, variant, pal, template(kind, style, variant))
    x0, y0, z0, *_ = o.t.bounds()
    ax, az = o.anchor_point
    meta = dict(modo=MODE[(kind, variant)], ancla=[ax - x0, az - z0], tierra=list(o.land), mar=list(o.sea),
                fila_mar=(o.sea_row - y0) if o.sea_row is not None else -1)
    return o, (x0, y0, z0), meta


def build(reg, kind):
    """Plantillas y pools de un tipo (una parte de pack.build_all) y los errores de su auditoría."""
    from . import audit
    for style in STYLES:
        for v in VARIANTS:
            o, _, _ = construction(kind, style, v)
            reg.warnings += [f"{o.t.name}: {e}" for e in audit.errors(o, kind)]
            reg.pool(template(kind, style, v), [(reg.add(_copy(o.t), f"costa:{kind}"), 1, "rigid", processors(kind))])


def _copy(t):
    """Otra plantilla con los mismos bloques (Registry.add la normaliza: la obra en caché, que usan la auditoría y los
    metadatos del Java, se queda en coordenadas de diseño). La auditoría genérica de apoyos sí la recorre."""
    from core import Template
    c = Template(t.name)
    c.blocks, c.entities, c.jigsaws = dict(t.blocks), list(t.entities), [dict(j) for j in t.jigsaws]
    return c


# Procesador de cada tipo: lo que va en la fila inferior de la plantilla (cimientos y pilotes del faro; quilla y fondo
# del casco del naufragio) baja hasta el suelo firme atravesando el agua. Uno por tipo: los tablones del embarcadero del
# faro no deben bajar (los del fondo del casco, sí).
DEPTH_MAX = 12


def processors(kind):
    return f"{NS}:{PREFIX}/{kind}_suelo"


def descend(kind):
    """Bloques de la fila inferior que el procesador del tipo alarga hasta el suelo (los de todas sus paletas)."""
    out = set()
    for d in STYLES.values():
        if kind == "faro":
            out |= {f"minecraft:{x}" for x in d["faro"]["cimiento"]} | {f"minecraft:{d['faro']['tronco']}"}
        else:
            out |= {f"minecraft:{d['barco']['tronco']}", f"minecraft:{d['barco']['madera']}_planks"}
    return sorted(out)


# ------------------------------------------------------------------ escritura
def structure(kind, style, variant):
    _, _, meta = construction(kind, style, variant)
    climates = [{"tierra": f"#{NS}:{BIOME_MAP}/tierra/{t}", "mar": f"#{NS}:{BIOME_MAP}/mar/{m}"}
              for t, m in STYLES[style]["climas"]]
    return {"type": f"{NS}:costa", "biomes": f"#{NS}:{BIOME_MAP}/{style}", "step": "surface_structures",
            "spawn_overrides": {}, "terrain_adaptation": "none", "start_pool": nsid(template(kind, style, variant)),
            "climas": climates, **meta}


def placement(kind):
    """heraldia:rejilla del tipo (spacing de por defecto; el Java lo recalcula con la configuración) con la candidata
    buscada en las playas."""
    spacing = round(SEPARATION[kind] / 16)
    return {"type": f"{NS}:rejilla", "grupo": f"{PREFIX}/{kind}", "spacing": spacing, "separation": spacing // 3,
            "salt": salt(kind), "bioma": f"{NS}:{BIOME_MAP}", "bioma_vecinos": BIOME_NEIGHBORS,
            "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": VANILLA_VILLAGE_EXCLUSION}}


def land_of(style):
    return sorted({b for t, _ in STYLES[style]["climas"] for b in LAND[t]})


def write(out, jdump):
    """Estructuras, etiquetas de biomas y de estructura, structure_sets, el procesador y el botín."""
    import biomes
    from writer import lootr_aware, down_to_floor
    import treasure
    biomes.tag(out, BIOME_MAP, BEACHES)
    for g, lst in LAND.items():
        biomes.tag(out, f"{BIOME_MAP}/tierra/{g}", lst)
    for g, lst in SEA.items():
        biomes.tag(out, f"{BIOME_MAP}/mar/{g}", lst)
    for style in STYLES:
        biomes.tag(out, f"{BIOME_MAP}/{style}", land_of(style))
    for kind in KINDS:
        jdump(out, f"data/{NS}/worldgen/processor_list/{PREFIX}/{kind}_suelo.json",
              {"processors": [down_to_floor(descend(kind), DEPTH_MAX)]})
    all_items = []
    for kind in KINDS:
        ids = []
        for style in STYLES:
            for v in VARIANTS:
                jdump(out, f"data/{NS}/worldgen/structure/{template(kind, style, v)}.json", structure(kind, style, v))
                ids.append(f"{NS}:{template(kind, style, v)}")
        jdump(out, f"data/{NS}/worldgen/structure_set/{PREFIX}/{kind}.json",
              {"structures": [{"structure": s, "weight": 1} for s in ids], "placement": placement(kind)})
        jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}/{kind}.json", {"values": ids})
        all_items += ids
    jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}.json", {"values": all_items})
    for name, tbl in LOOT.items():
        if name == "camarote":          # una pista del tesoro, rara, en el cofre del capitán
            tbl = treasure.with_hint(tbl, PREFIX)
        jdump(out, f"data/{NS}/loot_table/{PREFIX}/{name}.json", lootr_aware(tbl))
    return lang()


LANG = {"es_es": {}, "en_us": {}}
for _t in KINDS:
    LANG["es_es"][f"{NS}.costa.{_t}.nombre"], LANG["en_us"][f"{NS}.costa.{_t}.nombre"] = DISPLAY_NAME[_t]
for _k, (_es, _en) in TEXTS.items():
    LANG["es_es"][f"{NS}.costa.{_k}"], LANG["en_us"][f"{NS}.costa.{_k}"] = _es, _en
# /heraldia info (los de status, mapas web y review van con los demás en admin.py)
LANG["es_es"][f"{NS}.info.costa"] = "Costa: faros %s, cada %s bloques; galeones naufragados %s, cada %s bloques; %s estructuras"
LANG["en_us"][f"{NS}.info.costa"] = "Coast: lighthouses %s, every %s blocks; wrecked galleons %s, every %s blocks; %s structures"


def lang():
    return {k: dict(v) for k, v in LANG.items()}


def tables():
    """{id corto: tabla} de todo el botín de la costa (para validate_loot)."""
    return {f"{PREFIX}/{n}": t for n, t in LOOT.items()}


def structures():
    """Ids de todas las estructuras de la costa (para /heraldia info y las pruebas)."""
    return [f"{NS}:{template(t, e, v)}" for t in KINDS for e in STYLES for v in VARIANTS]
