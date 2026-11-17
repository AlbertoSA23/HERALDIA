"""Contenido de Heraldia en el Nether y el End (T44): lo que comparten sus medianas (medianas/<id> con DIMENSION) y sus
únicas (unicas/<id> con DIMENSION).

Un módulo de mediana o de única que declara DIMENSION = "nether" o "end" se escribe con el tipo de estructura propio
heraldia:dimension (Java: dimensiones/DimensionStructure), que busca la altura del inicio en la columna de ruido: en el
Nether no hay heightmap de superficie (el techo de bedrock) y en el End el heightmap del vacío es la altura mínima del
mundo. Sus rejillas no buscan la candidata en el bioma (la búsqueda de GridPlacement solo lee el ruido del mundo
principal) ni llevan la zona de exclusión de las aldeas vanilla (no hay aldeas allí); las reglas de separación (entre
únicas, entre medianas y con las vanilla y las de otros mods) se aplican con las de su misma dimensión
(Dimensiones.posible). Los mapas del tesoro, los tratos de los cartógrafos y el mapa del pliego de la Crónica solo
señalan las únicas del mundo principal: un mapa de exploración busca en la dimensión donde se crea.
"""
from core import NS, nsid

PRINCIPAL, NETHER, END = "overworld", "nether", "end"
DIMENSIONES = (PRINCIPAL, NETHER, END)
# Biomas vanilla de cada dimensión (los de otros mods entran por las etiquetas convencionales de cada estilo).
BIOMAS = {
    NETHER: ["nether_wastes", "crimson_forest", "warped_forest", "soul_sand_valley", "basalt_deltas"],
    # islas exteriores: ni the_end (la isla central y el combate del dragón) ni small_end_islands (islotes sueltos)
    END: ["end_highlands", "end_midlands", "end_barrens"],
}
# Lo que la generación de cada dimensión decora encima si queda a la vista en el patio (y = 0): nilio (hongos y raíces),
# netherrack (fuego), arena y tierra de almas (fuego de almas y huesos) y piedra del End (coros).
SUELO_VIVO = {f"minecraft:{b}" for b in ("crimson_nylium", "warped_nylium", "netherrack", "soul_sand", "soul_soil",
                                          "end_stone")}
# Holgura sobre la plantilla que pide el Nether bajo el techo (aire encima de la fila más alta).
HOLGURA = 2
# Nada que rompa la progresión fuera del mundo principal: ni equipo de netherita, ni lingotes, ni restos antiguos (los
# fragmentos, como mucho uno, en el cofre premium de la única del Nether), ni élitros, ni nada del dragón.
PROHIBIDO = ("netherite_ingot", "netherite_sword", "netherite_axe", "netherite_pickaxe", "netherite_shovel",
             "netherite_hoe", "netherite_helmet", "netherite_chestplate", "netherite_leggings", "netherite_boots",
             "netherite_block", "ancient_debris", "netherite_upgrade_smithing_template", "elytra", "dragon_egg",
             "dragon_head", "dragon_breath", "end_crystal", "enchanted_golden_apple", "totem_of_undying")
MAX_FRAGMENTOS = 1      # fragmentos de netherita (netherite_scrap) por cofre, como mucho (el tesoro de un bastión)


def de(mod):
    """Dimensión de un módulo de mediana o de única (por defecto, el mundo principal)."""
    return getattr(mod, "DIMENSION", PRINCIPAL)


def del_mundo_principal(modules):
    """[(id, módulo)] de las del mundo principal (las que pueden llevar mapa del tesoro)."""
    return [(i, m) for i, m in modules if de(m) == PRINCIPAL]


def errores(nombre, mod):
    d = de(mod)
    return [] if d in DIMENSIONES else [f"{nombre}: DIMENSION {d!r} no es {DIMENSIONES}"]


def estructura(start_pool, biomes, size, max_distance, modo, radio, libre, terrain_adaptation="beard_thin",
               step="surface_structures"):
    """JSON de una estructura heraldia:dimension. `radio`: bloques del centro a las esquinas de la huella que se miran
    (suelo llano); `libre`: aire que necesita encima del suelo en el Nether (alto de la plantilla + HOLGURA)."""
    assert modo in (NETHER, END), modo
    return {"type": f"{NS}:dimension", "biomes": biomes, "step": step, "spawn_overrides": {},
            "terrain_adaptation": terrain_adaptation, "start_pool": nsid(start_pool), "size": size,
            "max_distance_from_center": max_distance, "modo": modo, "radio": max(1, min(64, radio)),
            "libre": max(2, min(64, libre))}


def objetos_prohibidos(objetos):
    """Los ids de `objetos` (["minecraft:..."]) que no pueden salir en el Nether o el End."""
    return [o for o in objetos if o.split(":")[-1] in PROHIBIDO]


def fragmentos_de_mas(tabla):
    """Entradas de netherite_scrap con más de MAX_FRAGMENTOS (cantidad máxima de set_count)."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "minecraft:item" and str(o.get("name", "")).endswith("netherite_scrap"):
                hi = 1
                mods = o.get("functions") or o.get("modifier") or []
                for f in mods if isinstance(mods, list) else [mods]:
                    if "set_count" in str(f.get("type", f.get("function", ""))):
                        c = f["count"]
                        hi = c.get("max", c) if isinstance(c, dict) else c
                if hi > MAX_FRAGMENTOS:
                    out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tabla)
    return out
