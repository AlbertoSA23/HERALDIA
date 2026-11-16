"""Templete en ruinas (heraldia:medianas/templete/<estilo>): claro de 19 x 19 con un templete de columnas sobre un podio
de 11 x 11 (gradas al norte), las columnas de levante y poniente rotas y sus tambores caídos en el suelo, y vasijas con
ofrendas. Variante a: el altar con el cofre de las ofrendas y dos custodios (esqueletos con casco en la jungla,
momias en el desierto; persistentes y anclados); b: el pozo sagrado (agua quieta en un brocal) en el centro, con el
cofre al lado y sin nadie."""
from core import Template, F, adulto
from loot import item, empty
from unicas._comun import botin
from . import _comun as c

MID = "templete"
NOMBRE = {"es_es": "Templete en ruinas", "en_us": "Ruined Shrine"}
SEPARACION = 768
LOGRO_ICONO = "minecraft:chiseled_stone_bricks"
LANG = botin.lang("heraldia.medianas.templete.", {
    "custodio": ("Custodio del templete", "Shrine Keeper"),
})
LOGROS = [dict(id="custodios", icono="minecraft:bone",
               titulo=("Sin custodia", "Unguarded"),
               descripcion=("Derrota a un custodio de un templete en ruinas", "Defeat a keeper of a ruined shrine"),
               criterios={m: {"trigger": "minecraft:player_killed_entity", "conditions": {"entity": {
                   "type": "minecraft:entity_properties", "entity": "this",
                   "predicate": {"minecraft:entity_type": f"minecraft:{m}",
                                 "minecraft:entity_tags": {"all_of": ["heraldia_mediana.templete"]}}}}}
                          for m in ("skeleton", "husk")})]
LOOT = {
    "ofrenda": botin.cofre(((2, 4), [item("gold_nugget", 8, 2, 8), item("emerald", 5, 1, 3), item("lapis_lazuli", 5, 2, 6),
                                     item("candle", 5, 1, 3), item("gold_ingot", 2), item("amethyst_shard", 3, 1, 3),
                                     item("golden_carrot", 2, 1, 2), item("book", 2, rand_ench=True),
                                     item("archer_pottery_sherd", 1), item("prize_pottery_sherd", 1), empty(5)]),
                           ((1, 1), [item("emerald", 3, 1, 2), item("golden_apple", 1), empty(8)])),
    "vasija": botin.table(botin.pool((1, 2), [item("gold_nugget", 6, 1, 4), item("bone", 5, 1, 3), item("arrow", 4, 2, 5),
                                              item("lapis_lazuli", 3, 1, 3), item("emerald", 1), empty(6)])),
}

L = 19
B0, B1 = 4, 14                     # base del podio (11 x 11) en y = 0
P0, P1 = 5, 13                     # podio en y = 1 (9 x 9); columnas en su borde, cada 2
CX = 9


def _h(x, z):
    return (x * 73856093 ^ z * 19349663) & 0xFFFF


def _suelo(p):
    mats = p["suelo"]
    return lambda x, z: mats[_h(x, z) % len(mats)]


def _templo(p, name):
    t = Template(name)
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=7)
    c.entrada(t, CX, p["suelo"][0])
    # base, podio (con piezas gastadas) y gradas al norte
    for x in range(B0, B1 + 1):
        for z in range(B0, B1 + 1):
            t.set(x, 0, z, p["base"])
            if P0 <= x <= P1 and P0 <= z <= P1:
                t.set(x, 1, z, p["ruina"][_h(x, z) % len(p["ruina"])] if _h(x, z) % 7 == 0 else p["podio"])
    for x in range(CX - 1, CX + 2):
        t.set(x, 1, B0, f"{p['grada']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
    # columnas: las del norte y el sur, enteras con su arquitrabe; las de levante y poniente, rotas a distinta altura
    for x in range(P0, P1 + 1, 2):
        for z in range(P0, P1 + 1, 2):
            if not (x in (P0, P1) or z in (P0, P1)) or (x, z) == (CX, P0):
                continue
            entera = z in (P0, P1)
            alto = 5 if entera else (1, 2, 3, 2)[_h(x, z) % 4]
            for y in range(2, 2 + alto):
                t.set(x, y, z, p["capitel"] if entera and y == 6 else p["columna"])
    for z in (P0, P1):
        for x in range(P0, P1 + 1):
            t.set(x, 7, z, p["arquitrabe"] if _h(x, 7 * z) % 9 else p["ruina"][0])
    # tambores caídos fuera del podio y vasijas en las esquinas
    for x, z, eje in ((1, 8, "z"), (1, 9, "z"), (16, 11, "x"), (17, 11, "x"), (12, 16, "x")):
        t.set(x, 1, z, p["tambor"] + (f"[axis={eje}]" if p["tambor"].endswith("_pillar") else ""))
    for x, z in ((P0 + 1, P0 + 1), (P1 - 1, P1 - 1)):
        c.cofre(t, x, 2, z, "north", MID, "vasija", kind="decorated_pot")
    t.set(P1 - 1, 2, P0 + 1, "decorated_pot[cracked=true,facing=north,waterlogged=false]", {"id": "minecraft:decorated_pot"})
    return t


def custodio(p, rot):
    extra = {}
    if p["custodio"] == "skeleton":          # con casco: en la jungla no arde de día
        extra = dict(equipment={"mainhand": {"id": "minecraft:bow", "count": 1},
                                "head": {"id": "minecraft:chainmail_helmet", "count": 1}},
                     drop_chances={"head": F(0.0)})
    return c.mob(p["custodio"], MID, "custodio", "Custodio del templete", rot=rot, **extra)


def altar(p, name):
    """Altar con el cofre de las ofrendas y velas; dos custodios a sus lados."""
    t = _templo(p, name)
    t.set(CX, 2, 11, p["capitel"])
    c.cofre(t, CX, 3, 11, "north", MID, "ofrenda")
    for x in (CX - 1, CX + 1):
        t.set(x, 2, 11, "candle[candles=3,lit=true,waterlogged=false]")
    t.entity(CX - 2, 2, 9, adulto(custodio(p, 180.0)))
    t.entity(CX + 2, 2, 9, adulto(custodio(p, 180.0)))
    return t


def pozo(p, name):
    """Pozo sagrado: brocal de 5 x 5 con agua quieta (todo fuentes) a ras del podio, y el cofre de las ofrendas."""
    t = _templo(p, name)
    for x in range(CX - 2, CX + 3):
        for z in range(8, 13):
            if x in (CX - 2, CX + 2) or z in (8, 12):
                t.set(x, 2, z, p["brocal"])
            else:
                t.set(x, 1, z, "water[level=0]")
    c.cofre(t, CX + 3, 2, 10, "west", MID, "ofrenda")
    t.set(CX - 3, 2, 12, "candle[candles=2,lit=true,waterlogged=false]")
    return t


ESTILOS = {
    "jungla": dict(biomas=["jungle", "sparse_jungle", "bamboo_jungle"],
                   convencionales=["minecraft:is_jungle", "c:is_jungle"],
                   paleta=dict(base="mossy_stone_bricks", podio="stone_bricks",
                               ruina=["cracked_stone_bricks", "mossy_stone_bricks"], grada="stone_brick_stairs",
                               columna="mossy_stone_brick_wall", capitel="chiseled_stone_bricks",
                               arquitrabe="stone_bricks", tambor="mossy_stone_bricks", brocal="mossy_stone_brick_wall",
                               custodio="skeleton",
                               suelo=["minecraft:packed_mud", "minecraft:mossy_cobblestone", "minecraft:dirt_path",
                                      "minecraft:packed_mud"]),
                   variantes={"a": altar, "b": pozo}),
    "desierto": dict(biomas=["desert"], convencionales=["c:is_desert"],
                     paleta=dict(base="sandstone", podio="smooth_sandstone", ruina=["cut_sandstone", "sandstone"],
                                 grada="sandstone_stairs", columna="sandstone_wall", capitel="chiseled_sandstone",
                                 arquitrabe="cut_sandstone", tambor="cut_sandstone", brocal="sandstone_wall",
                                 custodio="husk",
                                 suelo=["minecraft:sandstone", "minecraft:smooth_sandstone", "minecraft:sand",
                                        "minecraft:sandstone"]),
                     variantes={"a": altar, "b": pozo}),
}
