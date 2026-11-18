"""Heraldia content in the Nether and the End (T44): what their medium structures (medianas/<id> with DIMENSION) and their
unique structures (unicas/<id> with DIMENSION) share.

A medium or unique structure module that declares DIMENSION = "nether" or "end" is written with its own structure type
heraldia:dimension (Java: dimensiones/DimensionStructure), which looks for the start height in the noise column: in the
Nether there is no surface heightmap (the bedrock roof) and in the End the void heightmap is the world's minimum
height. Their grids do not look for the candidate in the biome (the GridPlacement search only reads the overworld's
noise) nor carry the vanilla village exclusion zone (there are no villages there); the separation rules (between
unique structures, between medium ones and with vanilla ones and those of other mods) are applied with those of their own dimension
(Dimensiones.posible). The treasure maps, the cartographers' trades and the Chronicle sheet's map only
point to the unique structures of the overworld: an exploration map searches in the dimension where it is created.
"""
from core import NS, nsid

MAIN, NETHER, END = "overworld", "nether", "end"
DIMENSIONS = (MAIN, NETHER, END)
# Vanilla biomes of each dimension (those of other mods come in through each style's conventional tags).
BIOME_MAP = {
    NETHER: ["nether_wastes", "crimson_forest", "warped_forest", "soul_sand_valley", "basalt_deltas"],
    # outer islands: neither the_end (the central island and the dragon fight) nor small_end_islands (loose islets)
    END: ["end_highlands", "end_midlands", "end_barrens"],
}
# What each dimension's generation decorates on top if it is left exposed in the courtyard (y = 0): nylium (fungi and roots),
# netherrack (fire), sand and soul soil (soul fire and bones) and End stone (chorus).
LIVE_FLOOR = {f"minecraft:{b}" for b in ("crimson_nylium", "warped_nylium", "netherrack", "soul_sand", "soul_soil",
                                          "end_stone")}
# Clearance over the template required by the Nether under the roof (air above the highest row).
SLACK = 2
# Nothing that breaks progression outside the overworld: no netherite equipment, no ingots, no ancient debris (the
# scraps, at most one, in the premium chest of the Nether unique structure), no elytra, nothing from the dragon.
FORBIDDEN = ("netherite_ingot", "netherite_sword", "netherite_axe", "netherite_pickaxe", "netherite_shovel",
             "netherite_hoe", "netherite_helmet", "netherite_chestplate", "netherite_leggings", "netherite_boots",
             "netherite_block", "ancient_debris", "netherite_upgrade_smithing_template", "elytra", "dragon_egg",
             "dragon_head", "dragon_breath", "end_crystal", "enchanted_golden_apple", "totem_of_undying")
MAX_FRAGMENTS = 1      # netherite scraps (netherite_scrap) per chest, at most (a bastion's treasure)


def dimension_of(mod):
    """Dimension of a medium or unique structure module (by default, the overworld)."""
    return getattr(mod, "DIMENSION", MAIN)


def overworld_only(modules):
    """[(id, module)] of those in the overworld (those that can carry a treasure map)."""
    return [(i, m) for i, m in modules if dimension_of(m) == MAIN]


def errors(name, mod):
    d = dimension_of(mod)
    return [] if d in DIMENSIONS else [f"{name}: DIMENSION {d!r} no es {DIMENSIONS}"]


def structure(start_pool, biomes, size, max_distance, mode, radius, free, terrain_adaptation="beard_thin",
               step="surface_structures"):
    """JSON of a heraldia:dimension structure. `radius`: blocks from the center to the corners of the footprint that are checked
    (flat ground); `free`: air it needs above the ground in the Nether (template height + SLACK)."""
    assert mode in (NETHER, END), mode
    return {"type": f"{NS}:dimension", "biomes": biomes, "step": step, "spawn_overrides": {},
            "terrain_adaptation": terrain_adaptation, "start_pool": nsid(start_pool), "size": size,
            "max_distance_from_center": max_distance, "modo": mode, "radio": max(1, min(64, radius)),
            "libre": max(2, min(64, free))}


def forbidden_items(items):
    """The ids in `items` (["minecraft:..."]) that cannot appear in the Nether or the End."""
    return [o for o in items if o.split(":")[-1] in FORBIDDEN]


def extra_fragments(tbl):
    """netherite_scrap entries with more than MAX_FRAGMENTS (maximum set_count quantity)."""
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
                if hi > MAX_FRAGMENTS:
                    out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tbl)
    return out
