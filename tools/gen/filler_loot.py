"""Filler loot: no container of any Heraldia template is empty when a player opens it (the owner: «every chest of every
structure must have loot inside, even if it is low level, so the world feels lived in»).

What counts as a container: the blocks the game fills from a loot table when they are first opened (chest, trapped
chest, barrel, dispenser, dropper, hopper, crafter, shulker and copper chests) and the entities that do the same (chest
minecarts, hopper minecarts, chest boats and rafts). Not counted, because the game cannot give them a loot table and they
are not storage: furnaces, smokers, blast furnaces, brewing stands, lecterns (one book), decorated pots (broken, not
opened) and chiseled bookshelves.

Every container either has a table (or hand-placed Items), or is marked empty on purpose (leave_empty: the mark travels
in its block nbt, is never written to the .nbt, and says why), or its template matches one of RULES and gets that rule's
filler table when the template is saved (core.Template.save calls fill). A container with none of the three makes the
generation fail (FillerError), so a new structure cannot ship an empty chest by omission: give it a table where it is
built, add a rule here, or mark it with a reason.

The filler tables (heraldia:relleno/<name>) are poor on purpose: one to three cheap stacks, never empty, no emeralds,
no diamonds, no enchantments and no treasure-map fragment. Their prefix is not one of Restock.PREFIXES, so they never
restock (botin.reponer) and the mod's difficulty does not scale them (MobDifficulty.isChestLoot): looting forty village
houses gives bread, sticks and wool, not a living. The structures' own tables (cofres/, unicas/, medianas/, minas/,
costa/) are untouched.
"""
import fnmatch

from core import NS, EMPTY_MARK
from loot import item, table

PREFIX = "relleno"

CONTAINER_BLOCKS = {"minecraft:" + b for b in ("chest", "trapped_chest", "barrel", "dispenser", "dropper", "hopper",
                                               "crafter")}
CONTAINER_SUFFIXES = ("shulker_box", "copper_chest")
CONTAINER_ENTITIES = ("chest_minecart", "hopper_minecart", "chest_boat", "chest_raft")


def table_id(name):
    return f"{NS}:{PREFIX}/{name}"


# The filler tables: rolls of at least one, no empty entries (opening one always gives something), cheap items only.
TABLES = {
    # a humble house: what someone keeps by the bed
    "casa": table(((1, 2), [item("bread", 8, 1, 2), item("apple", 6, 1, 2), item("potato", 6, 1, 3), item("carrot", 5, 1, 3),
                            item("stick", 8, 1, 4), item("string", 5, 1, 2), item("torch", 5, 1, 3), item("coal", 4, 1, 2),
                            item("white_wool", 3), item("candle", 3), item("paper", 4, 1, 3), item("feather", 4, 1, 2),
                            item("leather", 2), item("bowl", 4), item("wheat_seeds", 5, 1, 4), item("bone", 3, 1, 2)])),
    # a pantry, a cellar, a kitchen store
    "despensa": table(((1, 3), [item("bread", 10, 1, 3), item("potato", 8, 1, 4), item("carrot", 8, 1, 4), item("apple", 6, 1, 3),
                                item("beetroot", 5, 1, 3), item("wheat", 6, 1, 4), item("sugar", 4, 1, 3), item("egg", 4, 1, 2),
                                item("dried_kelp", 4, 1, 4), item("sweet_berries", 4, 1, 4), item("bowl", 4, 1, 2),
                                item("cookie", 2, 1, 3), item("cod", 3, 1, 2)])),
    # the kegs of an inn or a tavern
    "bodega": table(((1, 2), [item("glass_bottle", 10, 1, 3), item("sugar", 6, 1, 3), item("wheat", 6, 1, 4), item("apple", 6, 1, 2),
                              item("sweet_berries", 5, 1, 4), item("melon_slice", 5, 1, 4), item("bread", 5, 1, 2),
                              item("bowl", 3), item("honey_bottle", 1)])),
    # a market stall's crates and a street's stacked goods
    "mercado": table(((1, 2), [item("white_wool", 6, 1, 2), item("leather", 5), item("string", 6, 1, 3), item("wheat", 6, 1, 4),
                               item("apple", 6, 1, 2), item("carrot", 5, 1, 3), item("melon_slice", 5, 1, 4),
                               item("pumpkin_seeds", 4, 1, 3), item("paper", 5, 1, 3), item("flint", 4, 1, 2),
                               item("feather", 4, 1, 3), item("egg", 3), item("red_dye", 2), item("yellow_dye", 2)])),
    # a smithy: fuel, scraps and worn tools (a rare ingot)
    "herreria": table(((1, 2), [item("coal", 10, 1, 3), item("charcoal", 6, 1, 3), item("iron_nugget", 8, 1, 5), item("flint", 5, 1, 2),
                                item("stick", 6, 1, 4), item("leather", 3), item("cobblestone", 5, 2, 6),
                                item("stone_pickaxe", 3, dmg=(0.2, 0.6)), item("stone_axe", 3, dmg=(0.2, 0.6)),
                                item("stone_shovel", 3, dmg=(0.2, 0.6)), item("iron_shovel", 1, dmg=(0.1, 0.3)),
                                item("iron_ingot", 1)])),
    # a mill or a bakery: sacks of grain and flour
    "molino": table(((1, 3), [item("wheat", 12, 1, 4), item("wheat_seeds", 10, 1, 5), item("bread", 8, 1, 2), item("sugar", 4, 1, 2),
                              item("egg", 3), item("paper", 2)])),
    # a fisherman's hut, a port, a lighthouse store
    "pesca": table(((1, 2), [item("cod", 10, 1, 3), item("salmon", 6, 1, 2), item("dried_kelp", 6, 1, 4), item("kelp", 4, 1, 3),
                             item("string", 6, 1, 3), item("stick", 5, 1, 3), item("bone_meal", 4, 1, 3), item("ink_sac", 3),
                             item("lily_pad", 2), item("fishing_rod", 1, dmg=(0.2, 0.6))])),
    # a ship's hold
    "barco": table(((1, 2), [item("dried_kelp", 8, 1, 4), item("string", 7, 1, 3), item("stick", 6, 1, 4), item("paper", 4, 1, 2),
                             item("bread", 6, 1, 2), item("cod", 4, 1, 2), item("white_wool", 3), item("leather", 3),
                             item("coal", 4, 1, 2), item("bone", 3, 1, 2), item("gunpowder", 2), item("lead", 1)])),
    # a garrison's or a castle's storeroom
    "almacen": table(((1, 2), [item("arrow", 8, 1, 4), item("stick", 8, 1, 4), item("string", 6, 1, 3), item("flint", 5, 1, 2),
                               item("feather", 4, 1, 3), item("bread", 5, 1, 2), item("coal", 5, 1, 2), item("torch", 5, 1, 3),
                               item("leather", 3), item("iron_nugget", 3, 1, 3), item("bone", 4, 1, 2),
                               item("cobblestone", 4, 2, 6)])),
    # a mine's supplies
    "mina": table(((1, 2), [item("coal", 10, 1, 3), item("torch", 8, 1, 4), item("stick", 6, 1, 4), item("cobblestone", 6, 2, 6),
                            item("rail", 3, 1, 3), item("bread", 4, 1, 2), item("raw_copper", 3, 1, 2), item("raw_iron", 2),
                            item("flint", 3, 1, 2), item("string", 3, 1, 2), item("stone_pickaxe", 2, dmg=(0.2, 0.6))])),
    # a study, a library, a wizard's or an astronomer's shelves
    "estudio": table(((1, 2), [item("paper", 10, 1, 3), item("feather", 6, 1, 2), item("ink_sac", 5), item("candle", 4),
                               item("glass_bottle", 5, 1, 2), item("book", 2), item("string", 3, 1, 2), item("sugar", 3, 1, 2),
                               item("redstone", 2, 1, 2), item("glowstone_dust", 1), item("spider_eye", 2),
                               item("bone_meal", 3, 1, 2)])),
    # a chapel, a monastery's or a sanctuary's store
    "templo": table(((1, 2), [item("candle", 8, 1, 2), item("bread", 8, 1, 2), item("paper", 6, 1, 3), item("glass_bottle", 5, 1, 2),
                              item("white_wool", 4), item("honeycomb", 2), item("wheat", 4, 1, 3), item("feather", 3),
                              item("bowl", 3)])),
    # a farm's sacks, a stable, a herbalist's seeds
    "granja": table(((1, 3), [item("wheat", 8, 1, 4), item("wheat_seeds", 10, 1, 5), item("beetroot_seeds", 6, 1, 4),
                              item("potato", 6, 1, 3), item("carrot", 6, 1, 3), item("bone_meal", 6, 1, 3), item("egg", 4, 1, 2),
                              item("leather", 3), item("feather", 4, 1, 2), item("pumpkin_seeds", 3, 1, 2),
                              item("melon_seeds", 2, 1, 2)])),
    # a cannon: powder and shot (dispensed, it only drops them: nothing that burns)
    "canon": table(((1, 2), [item("gunpowder", 6, 1, 2), item("iron_nugget", 6, 1, 4), item("string", 3, 1, 2), item("flint", 3)])),
    # a Nether outpost
    "nether": table(((1, 2), [item("gold_nugget", 8, 1, 4), item("porkchop", 5, 1, 2), item("string", 5, 1, 2), item("leather", 4),
                              item("crimson_fungus", 4, 1, 2), item("warped_fungus", 3, 1, 2), item("crimson_roots", 3, 1, 2),
                              item("soul_sand", 2, 1, 3), item("quartz", 2, 1, 2), item("bone", 3, 1, 2)])),
    # an End outpost
    "fin": table(((1, 2), [item("chorus_fruit", 10, 1, 3), item("end_stone", 6, 1, 4), item("paper", 4, 1, 2), item("string", 4, 1, 2),
                           item("popped_chorus_fruit", 3), item("purpur_block", 2, 1, 2)])),
    # a sunken ruin: what the sea left
    "ruinas": table(((1, 2), [item("kelp", 8, 1, 4), item("dried_kelp", 5, 1, 3), item("bone", 6, 1, 2), item("sea_pickle", 4, 1, 2),
                              item("ink_sac", 4), item("prismarine_shard", 3, 1, 2), item("gold_nugget", 3, 1, 3),
                              item("string", 3), item("prismarine_crystals", 1)])),
}

# (template name pattern, container blocks it applies to or None for all, filler table). First match wins. The unique
# and medium structures go first so that the village patterns ("*/houses/*") cannot catch one of their pieces. The
# Herald's House and its huts (casa_heraldo/*) have no rule: each of their containers is given a table where it is built.
RULES = [
    ("unicas/atlantida/*", None, "ruinas"),
    ("unicas/acueducto/*", None, "despensa"),
    ("unicas/castillo/*", None, "almacen"),
    ("unicas/catedral/*", None, "templo"),
    ("unicas/ciudadela/*", None, "almacen"),
    ("unicas/coliseo/*", None, "almacen"),
    ("unicas/faro/*", None, "pesca"),
    ("unicas/fortaleza_hielo/*", None, "almacen"),
    ("unicas/galeon/*", None, "barco"),
    ("unicas/isla_corsario/*", {"minecraft:dispenser"}, "canon"),    # the fort's cannons
    ("unicas/isla_corsario/*", None, "barco"),
    ("unicas/laboratorio_micelio/*", None, "estudio"),
    ("unicas/mansion/sotano*", None, "despensa"),
    ("unicas/mansion/*", None, "casa"),
    ("unicas/mina_perdida/*", None, "mina"),
    ("unicas/monasterio/*", None, "despensa"),
    ("unicas/observatorio/*", None, "estudio"),
    ("unicas/salon_jarl/*", None, "despensa"),
    ("unicas/santuario/*", None, "templo"),
    ("unicas/torre_mago/*", None, "estudio"),
    ("medianas/choza_mago/*", None, "estudio"),
    ("medianas/embarcadero_shulker/*", None, "fin"),
    ("medianas/molino/*", None, "molino"),
    ("medianas/pescador/*", None, "pesca"),
    ("medianas/puesto_piglin/*", None, "nether"),
    ("minas/*", None, "mina"),
    ("costa/faro/*", None, "pesca"),
    ("costa/naufragio/*", None, "barco"),
    # villages (every style): <style>/<kind>/<piece>
    ("*/houses/*", None, "casa"),
    ("*/specials/inn*", None, "bodega"),
    ("*/specials/tavern*", None, "bodega"),
    ("*/specials/market*", None, "mercado"),
    ("*/specials/blacksmith*", None, "herreria"),
    ("*/specials/mill*", None, "molino"),
    ("*/specials/port*", None, "pesca"),
    ("*/specials/townhall*", None, "casa"),
    ("*/fillers/fishrack*", None, "pesca"),
    ("*/fillers/dryrack*", None, "granja"),
    ("*/fillers/minecart*", None, "mina"),
    ("*/fillers/*", None, "mercado"),          # stacked barrels and crates, carts, awnings, tents
]


class FillerError(ValueError):
    pass


def is_container(state):
    bid = state.split("[")[0]
    return bid in CONTAINER_BLOCKS or bid.endswith(CONTAINER_SUFFIXES)


def is_container_entity(n):
    return str(n.get("id", "")).endswith(CONTAINER_ENTITIES)


def has_loot(nbt):
    return bool(nbt and (nbt.get("LootTable") or nbt.get("Items")))


def empty_nbt(block, reason):
    """Block nbt of a container left empty on purpose (pass it to Template.set): `reason` says why."""
    if not reason:
        raise ValueError("a container left empty needs a reason")
    return {"id": "minecraft:" + block, EMPTY_MARK: reason}


def leave_empty(t, x, y, z, reason):
    """Marks the container at (x, y, z) of template t as empty on purpose (with its reason)."""
    st, nbt = t.blocks[(x, y, z)]
    if not is_container(st):
        raise ValueError(f"{t.name} {(x, y, z)}: {st} is not a container")
    t.blocks[(x, y, z)] = (st, dict(nbt or {"id": st.split("[")[0]}, **{EMPTY_MARK: reason}))


def rule_for(name, block):
    for pattern, blocks, tbl in RULES:
        if fnmatch.fnmatchcase(name, pattern) and (blocks is None or block in blocks):
            return tbl
    return None


def unfilled(t):
    """[(position or "entity", what)] of the containers of t without a table, without Items, not marked empty and with
    no rule that fills them."""
    out = []
    for p, (st, nbt) in t.blocks.items():
        bid = st.split("[")[0]
        if is_container(st) and not has_loot(nbt) and not (nbt and nbt.get(EMPTY_MARK)) and rule_for(t.name, bid) is None:
            out.append((p, bid))
    for x, y, z, n in t.entities:
        if is_container_entity(n) and not has_loot(n) and rule_for(t.name, str(n["id"])) is None:
            out.append(("entity", str(n["id"])))
    return out


def fill(t):
    """Gives each container of t without a table its rule's filler table; FillerError if one has neither table nor
    rule nor the empty mark. Idempotent."""
    missing = unfilled(t)
    if missing:
        raise FillerError(f"{t.name}: container(s) without a loot table: {missing[:5]}"
                          f"{' ...' if len(missing) > 5 else ''} (give them a table, a rule in filler_loot.RULES"
                          f" or filler_loot.leave_empty with a reason)")
    for p, (st, nbt) in list(t.blocks.items()):
        if is_container(st) and not has_loot(nbt) and not (nbt and nbt.get(EMPTY_MARK)):
            t.blocks[p] = (st, dict(nbt or {"id": st.split("[")[0]}, LootTable=table_id(rule_for(t.name, st.split("[")[0]))))
    for i, (x, y, z, n) in enumerate(t.entities):
        if is_container_entity(n) and not has_loot(n):
            t.entities[i] = (x, y, z, dict(n, LootTable=table_id(rule_for(t.name, str(n["id"])))))
    return t


def empty_on_purpose(t):
    """{position: reason} of the containers of t marked empty."""
    return {p: nbt[EMPTY_MARK] for p, (st, nbt) in t.blocks.items() if nbt and nbt.get(EMPTY_MARK)}


def tables():
    """{name: table} for validate_loot."""
    return {f"{PREFIX}/{k}": v for k, v in TABLES.items()}


def write(out, jdump):
    for name, tbl in TABLES.items():
        jdump(out, f"data/{NS}/loot_table/{PREFIX}/{name}.json", tbl)
