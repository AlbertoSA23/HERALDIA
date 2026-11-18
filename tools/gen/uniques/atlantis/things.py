"""Objects with data: translatable texts, chests, keys, spawners, mobs, signs and dispensers (NBT of 26.3)."""
from core import B, F, adult, anchored
from .._common import pieces as P

LANG = {"es_es": {}, "en_us": {}}
TABLE = "heraldia:unicas/atlantida/"


def text(lang_key, es, en, **style):
    """Translatable text component with a Spanish fallback; registers the key in both languages."""
    k = "heraldia.atlantida." + lang_key
    LANG["es_es"][k], LANG["en_us"][k] = es, en
    c = P.text(k, es)
    c.update(style)
    return c


def item_name(lang_key, es, en, color="aqua"):
    return text(lang_key, es, en, color=color, italic=B(0))


# --- keys (named item with its own data; locked chests ask for that data) ---
KEYS = {
    "arsenal": ("Llave del Arsenal", "Arsenal Key"),
    "academia": ("Llave de la Academia", "Academy Key"),
    "anfiteatro": ("Llave del Anfiteatro", "Amphitheatre Key"),
    "poseidon": ("Llave de Poseidón", "Key of Poseidon"),
}
KEY_ITEM = "minecraft:nautilus_shell"


def key_components(which):
    es, en = KEYS[which]
    return {"minecraft:custom_name": item_name("llave." + which, es, en, "gold"),
            "minecraft:custom_data": {"heraldia_llave": which},
            "minecraft:enchantment_glint_override": B(1), "minecraft:max_stack_size": 1}


def key_table(which):
    """Loot table that gives exactly the key (reward chests and final guardian's death)."""
    c = key_components(which)
    return {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [{
        "type": "minecraft:item", "name": KEY_ITEM, "modifier": [
            {"type": "minecraft:set_components", "components": {
                "minecraft:custom_name": {k: (bool(v) if isinstance(v, B) else v) for k, v in c["minecraft:custom_name"].items()},
                "minecraft:custom_data": c["minecraft:custom_data"],
                "minecraft:enchantment_glint_override": True, "minecraft:max_stack_size": 1}}]}]}]}


def lock(which):
    return {"items": KEY_ITEM, "predicates": {"minecraft:custom_data": {"heraldia_llave": which}}}


# --- cofres ---
def place_chest(v, u, y, w, facing, tbl, key=None, kind="chest"):
    """Chest, trapped chest or barrel with a loot table (common piece), optionally locked with a key."""
    def put(x, y_, z, st, nbt):
        v.set(x, y_, z, st, dict(nbt, lock=lock(key)) if key else nbt)
    P.chest(put, u, y, w, facing, TABLE + tbl, kind=kind)
    v.mark("cofre", u, y, w)


# Mark (block custom_data) of a fixed-content chest that, with the option unicas.<id>.cofre_unico_por_jugador,
# gives each player their own copy (loot/CofrePorJugador.java reads the same key).
MARK_PER_PLAYER = "heraldia_cofre_unico"


def fixed_chest(v, u, y, w, facing, item_specs, key=None, per_player=None):
    """Chest with fixed content (no table: Lootr does not convert it). objetos = [(id, count, components | None)].
    por_jugador = structure id: marks the chest for the option unicas.<id>.cofre_unico_por_jugador."""
    items = []
    for i, (oid, n, comp) in enumerate(item_specs):
        it = {"Slot": B(i), "id": "minecraft:" + oid, "count": n}
        if comp:
            it["components"] = comp
        items.append(it)
    nbt = {"id": "minecraft:chest", "Items": items}
    if key:
        nbt["lock"] = lock(key)
    if per_player:
        nbt["components"] = {"minecraft:custom_data": {MARK_PER_PLAYER: per_player}}
    v.set(u, y, w, f"chest[facing={facing}]", nbt)
    v.mark("cofre", u, y, w)


# --- mobs ---
def mob(kind, name=None, hand=None, health=None, armour_set=None, chest_loot=None, **extra):
    n = {"id": "minecraft:" + kind, "PersistenceRequired": B(1)}
    if name:
        n["CustomName"] = name
    eq = {}
    if hand:
        eq["mainhand"] = {"id": "minecraft:" + hand, "count": 1}
    for cavity, obj in (armour_set or {}).items():
        eq[cavity] = {"id": "minecraft:" + obj, "count": 1}
    if eq:
        n["equipment"] = eq
        n["drop_chances"] = {k: F(0.03) for k in eq}
    if health:
        n["attributes"] = [{"id": "minecraft:max_health", "base": float(health)}]
        n["Health"] = F(health)
    if chest_loot:
        n["DeathLootTable"] = TABLE + chest_loot
    n.update(extra)
    # Drowned: adults and anchored (core.ANCHORED_TAG: no picking up items or wandering until attacked); the boss too.
    return anchored(adult(n), always=P.GUARDIAN_TAG in n.get("Tags", []))


def drowned(elite=False):
    if elite:
        return mob("drowned", text("mob.hoplita", "Hoplita ahogado", "Drowned Hoplite"), hand="trident", health=40,
                   armour_set={"head": "golden_helmet", "chest": "chainmail_chestplate"})
    return mob("drowned", text("mob.centinela", "Centinela ahogado", "Drowned Sentinel"), hand="trident")


def guardian():
    return mob("guardian", text("mob.vigia", "Vigía de la Atlántida", "Watcher of Atlantis"))


def elder():
    return mob("elder_guardian", text("mob.anciano", "Guardián anciano", "Elder Warden"))


def boss():
    return mob("elder_guardian", text("mob.jefe", "Guardián de Poseidón", "Warden of Poseidon", color="gold"), health=240, chest_loot="jefe",
               attributes=[{"id": "minecraft:max_health", "base": 240.0}, {"id": "minecraft:attack_damage", "base": 12.0},
                           {"id": "minecraft:armor", "base": 8.0}, {"id": "minecraft:scale", "base": 1.5}],
               Tags=[P.GUARDIAN_TAG])   # the final guardian: advancement heraldia:unicas/atlantida/guardian


def generator(v, u, y, w, kind, trident=False):
    """Spawner (common piece); with a trident, the drowned spawn armed."""
    def put(x, y_, z, st, nbt):
        if trident:
            nbt["SpawnData"]["entity"].update(equipment={"mainhand": {"id": "minecraft:trident", "count": 1}}, drop_chances={"mainhand": F(0.03)})
        v.set(x, y_, z, st, nbt)
    P.spawner(put, u, y, w, kind)
    v.mark("generador", u, y, w)


# --- signs and dispensers ---
def sign(v, u, y, w, facing, lines, wood="warped"):
    """Wall sign (common piece). mira = which way the face points; lineas = up to 4 text components."""
    P.sign(v.set, u, y, w, facing, lines, wood=wood)


def dispenser(v, u, y, w, facing, item, n, comp=None):
    it = {"Slot": B(0), "id": "minecraft:" + item, "count": n}
    if comp:
        it["components"] = comp
    v.set(u, y, w, f"dispenser[facing={facing},triggered=false]", {"id": "minecraft:dispenser", "Items": [it]})
