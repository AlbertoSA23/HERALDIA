"""Puesto de piglins renegados (heraldia:medianas/puesto_piglin/<estilo>, Nether): una empalizada de piedra negra de
17 x 17 alrededor de un patio con una choza de techo de losas, desterrados de su bastión. Variante a: la choza con dos
renegados de guardia (piglins brutos, persistentes y anclados) y el cofre del botín robado dentro; b: el corral de un
hoglin, una hoguera de almas con su asador y el cofre junto al fuego.

Estilos: yermo (desiertos del Nether: piedra negra y ladrillo del Nether) y carmesí (bosque carmesí: tablones y tallos
carmesí). Botín acorde: oro en pepitas, cuarzo, flechas, carne de cerdo; nada de netherita (dimensiones.PROHIBIDO)."""
from core import Template, F, B
from loot import item, empty
from unicas._comun import botin, piezas
from . import _comun as c

MID = "puesto_piglin"
DIMENSION = "nether"
NOMBRE = {"es_es": "Puesto de piglins renegados", "en_us": "Renegade Piglin Outpost"}
SEPARACION = 576
LOGRO_ICONO = "minecraft:gold_nugget"
LANG = botin.lang("heraldia.medianas.puesto_piglin.", {
    "renegado": ("Piglin renegado", "Renegade Piglin"),
})
LOGROS = [dict(id="renegados", icono="minecraft:golden_axe",
               titulo=("Desterrados del bastión", "Cast Out of the Bastion"),
               descripcion=("Derrota a un piglin renegado de un puesto del Nether",
                            "Defeat a renegade piglin of a Nether outpost"),
               criterios={"bruto": {"trigger": "minecraft:player_killed_entity", "conditions": {"entity": {
                   "type": "minecraft:entity_properties", "entity": "this",
                   "predicate": {"minecraft:entity_type": "minecraft:piglin_brute",
                                 "minecraft:entity_tags": {"all_of": ["heraldia_mediana.puesto_piglin"]}}}}}})]
LOOT = {
    "botin": botin.cofre(((2, 4), [item("gold_nugget", 10, 3, 9), item("quartz", 6, 2, 6), item("arrow", 6, 3, 8),
                                   item("cooked_porkchop", 6, 1, 3), item("leather", 4, 1, 3), item("string", 4, 1, 3),
                                   item("crossbow", 2, dmg=(0.4, 0.8)), item("golden_carrot", 2, 1, 2),
                                   item("gold_ingot", 2), empty(5)]),
                         ((1, 1), [item("gold_ingot", 3, 1, 2), item("golden_apple", 1), item("spectral_arrow", 2, 2, 4),
                                   empty(8)])),
    "asador": botin.table(botin.pool((1, 3), [item("cooked_porkchop", 8, 1, 4), item("porkchop", 6, 1, 3),
                                              item("leather", 4, 1, 2), item("gold_nugget", 5, 1, 4),
                                              item("crimson_fungus", 3, 1, 2), empty(6)])),
}

L = 17
CX = 8
H0, H1 = 5, 11          # choza de 7 x 7 (x y z de 5 a 11)


def _suelo(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 7 + z * 13 + x * z) % len(mats)]


def _recinto(p, name):
    """Patio, empalizada (muro de 2 de alto con postes cada 4) y portón al norte con dos braseros de almas."""
    t = Template(name)
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=7)
    for x in range(L):
        for z in range(L):
            if x in (0, L - 1) or z in (0, L - 1):
                if z == 0 and CX - 1 <= x <= CX + 1:
                    continue                                  # portón
                poste = x % 4 == 0 and z % 4 == 0
                t.set(x, 1, z, p["poste"] if poste else p["muro"])
                t.set(x, 2, z, p["poste"] if poste else p["muro"])
                if poste:
                    t.set(x, 3, z, p["remate"])
    for x in (CX - 2, CX + 2):
        t.set(x, 3, 0, "soul_lantern[hanging=false,waterlogged=false]")
    c.entrada(t, CX, p["suelo"][0])
    return t


def _choza(t, p):
    """Choza de 7 x 7 con puerta al norte, ventanas de barrotes y techo de losas; un farol de almas dentro."""
    c.caja(t, H0, 1, H0, H1, 4, H1, p["pared"], esquina=p["poste"], suelo=p["suelo"][0])
    t.fill(H0, 5, H0, H1, 5, H1, f"{p['losa']}[type=bottom,waterlogged=false]")
    for x in (H0 + 2, H1 - 2):
        t.set(x, 2, H1, "iron_bars")
    for z in (H0 + 2, H1 - 2):
        t.set(H0, 2, z, "iron_bars")
        t.set(H1, 2, z, "iron_bars")
    t.set(CX, 1, H0, "air")
    t.set(CX, 2, H0, "air")
    c.door(t, CX, 1, H0, "north", p["puerta"])
    c.farol(t, CX, 4, CX + 1)


def renegado(rot):
    return c.mob("piglin_brute", MID, "renegado", "Piglin renegado", rot=rot,
                 equipment={"mainhand": {"id": "minecraft:golden_axe", "count": 1}}, drop_chances={"mainhand": F(0.05)},
                 IsImmuneToZombification=B(1))


def choza(p, name):
    """La choza con el botín robado y dos renegados de guardia en el patio."""
    t = _recinto(p, name)
    _choza(t, p)
    c.cofre(t, CX, 1, H1 - 1, "north", MID, "botin")
    t.set(H0 + 1, 1, H1 - 1, "barrel[facing=up,open=false]")
    t.set(H1 - 1, 1, H1 - 1, p["mesa"])
    for x in (CX - 3, CX + 3):
        t.entity(x, 1, 3, renegado(180.0))
    piezas.connect(t)
    return t


def corral(p, name):
    """Corral de hoglins vacío (valla de ladrillo del Nether) con su renegado de guardia, hoguera de almas con el asador y
    el cofre junto al fuego. Sin hoglin: saldría cría una de cada cinco veces (validate)."""
    t = _recinto(p, name)
    # corral al este: de x 10 a 14, z 9 a 14
    for x in range(10, 15):
        for z in range(9, 15):
            if x in (10, 14) or z in (9, 14):
                t.set(x, 1, z, "nether_brick_fence")
    t.set(12, 1, 12, "bone_block[axis=x]")                       # el corral, vacío: el hoglin se lo comieron
    t.entity(9, 1, 11, renegado(90.0))
    # hoguera de almas con el asador (vasija) al oeste
    t.set(4, 1, 10, "soul_campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    c.cofre(t, 2, 1, 10, "east", MID, "asador", kind="barrel")
    c.cofre(t, 4, 1, 13, "north", MID, "botin")
    for x in (3, 5):
        t.set(x, 1, 8, f"{p['escalon']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
    piezas.connect(t)
    return t


ESTILOS = {
    "yermo": dict(biomas=["nether_wastes"], convencionales=[],
                  paleta=dict(suelo=["minecraft:polished_blackstone_bricks", "minecraft:blackstone",
                                     "minecraft:cracked_polished_blackstone_bricks", "minecraft:polished_blackstone"],
                              muro="blackstone_wall", poste="polished_blackstone", remate="gilded_blackstone",
                              pared="polished_blackstone_bricks", losa="blackstone_slab", puerta="crimson_door",
                              mesa="smithing_table", escalon="blackstone_stairs"),
                  variantes={"a": choza, "b": corral}),
    "carmesi": dict(biomas=["crimson_forest"], convencionales=[],
                    paleta=dict(suelo=["minecraft:crimson_planks", "minecraft:polished_blackstone",
                                       "minecraft:crimson_planks", "minecraft:blackstone"],
                                muro="crimson_fence", poste="stripped_crimson_stem[axis=y]", remate="shroomlight",
                                pared="crimson_planks", losa="crimson_slab", puerta="crimson_door",
                                mesa="crafting_table", escalon="crimson_stairs"),
                    variantes={"a": choza, "b": corral}),
}
