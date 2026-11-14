"""Objetos con datos: textos traducibles, cofres, llaves, generadores, mobs, carteles y dispensadores (NBT de 26.3)."""
from core import B, F

LANG = {"es_es": {}, "en_us": {}}
TABLA = "heraldia:unicas/atlantida/"


def texto(clave, es, en, **estilo):
    """Componente de texto traducible con respaldo en español; registra la clave en los dos idiomas."""
    k = "heraldia.atlantida." + clave
    LANG["es_es"][k], LANG["en_us"][k] = es, en
    c = {"translate": k, "fallback": es}
    c.update(estilo)
    return c


def nombre_objeto(clave, es, en, color="aqua"):
    return texto(clave, es, en, color=color, italic=B(0))


# --- llaves (objeto con nombre y dato propio; los cofres cerrados piden ese dato) ---
LLAVES = {
    "arsenal": ("Llave del Arsenal", "Arsenal Key"),
    "academia": ("Llave de la Academia", "Academy Key"),
    "anfiteatro": ("Llave del Anfiteatro", "Amphitheatre Key"),
    "poseidon": ("Llave de Poseidón", "Key of Poseidon"),
}
OBJETO_LLAVE = "minecraft:nautilus_shell"


def componentes_llave(cual):
    es, en = LLAVES[cual]
    return {"minecraft:custom_name": nombre_objeto("llave." + cual, es, en, "gold"),
            "minecraft:custom_data": {"heraldia_llave": cual},
            "minecraft:enchantment_glint_override": B(1), "minecraft:max_stack_size": 1}


def tabla_llave(cual):
    """Tabla de botín que da exactamente la llave (cofres de recompensa y muerte del guardián final)."""
    c = componentes_llave(cual)
    return {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [{
        "type": "minecraft:item", "name": OBJETO_LLAVE, "modifier": [
            {"type": "minecraft:set_components", "components": {
                "minecraft:custom_name": {k: (bool(v) if isinstance(v, B) else v) for k, v in c["minecraft:custom_name"].items()},
                "minecraft:custom_data": c["minecraft:custom_data"],
                "minecraft:enchantment_glint_override": True, "minecraft:max_stack_size": 1}}]}]}]}


def cerradura(cual):
    return {"items": OBJETO_LLAVE, "predicates": {"minecraft:custom_data": {"heraldia_llave": cual}}}


# --- cofres ---
def cofre(v, u, y, w, mira, tabla, llave=None, tipo="chest"):
    nbt = {"id": "minecraft:" + ("chest" if tipo == "trapped_chest" else tipo), "LootTable": TABLA + tabla}
    if tipo == "trapped_chest":
        nbt["id"] = "minecraft:trapped_chest"
    if llave:
        nbt["lock"] = cerradura(llave)
    v.set(u, y, w, f"{tipo}[facing={mira}]" if tipo != "barrel" else f"barrel[facing={mira}]", nbt)
    v.marca("cofre", u, y, w)


def cofre_fijo(v, u, y, w, mira, objetos, llave=None):
    """Cofre con contenido fijo (sin tabla: Lootr no lo convierte). objetos = [(id, cantidad, componentes | None)]."""
    items = []
    for i, (oid, n, comp) in enumerate(objetos):
        it = {"Slot": B(i), "id": "minecraft:" + oid, "count": n}
        if comp:
            it["components"] = comp
        items.append(it)
    nbt = {"id": "minecraft:chest", "Items": items}
    if llave:
        nbt["lock"] = cerradura(llave)
    v.set(u, y, w, f"chest[facing={mira}]", nbt)
    v.marca("cofre", u, y, w)


# --- mobs ---
def mob(tipo, nombre=None, mano=None, vida=None, armadura=None, botin=None, **extra):
    n = {"id": "minecraft:" + tipo, "PersistenceRequired": B(1)}
    if nombre:
        n["CustomName"] = nombre
    eq = {}
    if mano:
        eq["mainhand"] = {"id": "minecraft:" + mano, "count": 1}
    for hueco, obj in (armadura or {}).items():
        eq[hueco] = {"id": "minecraft:" + obj, "count": 1}
    if eq:
        n["equipment"] = eq
        n["drop_chances"] = {k: F(0.03) for k in eq}
    if vida:
        n["attributes"] = [{"id": "minecraft:max_health", "base": float(vida)}]
        n["Health"] = F(vida)
    if botin:
        n["DeathLootTable"] = TABLA + botin
    n.update(extra)
    return n


def ahogado(elite=False):
    if elite:
        return mob("drowned", texto("mob.hoplita", "Hoplita ahogado", "Drowned Hoplite"), mano="trident", vida=40,
                   armadura={"head": "golden_helmet", "chest": "chainmail_chestplate"})
    return mob("drowned", texto("mob.centinela", "Centinela ahogado", "Drowned Sentinel"), mano="trident")


def guardian():
    return mob("guardian", texto("mob.vigia", "Vigía de la Atlántida", "Watcher of Atlantis"))


def anciano():
    return mob("elder_guardian", texto("mob.anciano", "Guardián anciano", "Elder Warden"))


def jefe():
    return mob("elder_guardian", texto("mob.jefe", "Guardián de Poseidón", "Warden of Poseidon", color="gold"), vida=240, botin="jefe",
               attributes=[{"id": "minecraft:max_health", "base": 240.0}, {"id": "minecraft:attack_damage", "base": 12.0},
                           {"id": "minecraft:armor", "base": 8.0}, {"id": "minecraft:scale", "base": 1.5}])


def generador(v, u, y, w, tipo, tridente=False):
    ent = {"id": "minecraft:" + tipo}
    if tridente:
        ent["equipment"] = {"mainhand": {"id": "minecraft:trident", "count": 1}}
        ent["drop_chances"] = {"mainhand": F(0.03)}
    v.set(u, y, w, "spawner", {"id": "minecraft:mob_spawner", "SpawnData": {"entity": ent}, "Delay": 40, "MinSpawnDelay": 300,
                               "MaxSpawnDelay": 900, "SpawnCount": 2, "MaxNearbyEntities": 5, "RequiredPlayerRange": 14, "SpawnRange": 3})
    v.marca("generador", u, y, w)


# --- carteles y dispensadores ---
def cartel(v, u, y, w, mira, lineas, madera="warped"):
    """Cartel de pared (mira = hacia dónde da la cara). lineas = hasta 4 componentes de texto."""
    vacio = {"text": ""}
    msgs = list(lineas) + [vacio] * (4 - len(lineas))
    v.set(u, y, w, f"{madera}_wall_sign[facing={mira}]", {"id": "minecraft:sign", "is_waxed": B(1),
                                                         "front_text": {"messages": msgs, "color": "black", "has_glowing_text": B(0)},
                                                         "back_text": {"messages": [vacio] * 4}})


def dispensador(v, u, y, w, mira, objeto, n, comp=None):
    it = {"Slot": B(0), "id": "minecraft:" + objeto, "count": n}
    if comp:
        it["components"] = comp
    v.set(u, y, w, f"dispenser[facing={mira},triggered=false]", {"id": "minecraft:dispenser", "Items": [it]})
