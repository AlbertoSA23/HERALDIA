"""Campamento de bandidos (heraldia:medianas/campamento/<estilo>): claro de 21 x 21 con tiendas de lona alrededor de
una fogata con bancos de troncos, un tonel con el botín robado y dos bandidos (illagers persistentes y anclados, sin
patrulla: ni capitán ni ronda; no vuelven a salir). Variante a: dos tiendas y dos saqueadores; b: tres tiendas,
empalizada y un vindicador con un saqueador."""
from core import Template, B
from loot import item, empty
from unicas._comun import botin
from . import _comun as c

MID = "campamento"
NOMBRE = {"es_es": "Campamento de bandidos", "en_us": "Bandit Camp"}
SEPARACION = 768
LOGRO_ICONO = "minecraft:crossbow"
LANG = botin.lang("heraldia.medianas.campamento.", {
    "saqueador": ("Bandido", "Bandit"),
    "vindicador": ("Jefe de los bandidos", "Bandit Chief"),
})
LOOT = {
    "botin": botin.cofre(((3, 5), [item("emerald", 6, 1, 3), item("iron_ingot", 6, 1, 3), item("gold_nugget", 6, 2, 7),
                                   item("arrow", 6, 3, 9), item("crossbow", 2, dmg=(0.3, 0.8)), item("leather", 5, 1, 3),
                                   item("saddle", 1), item("lead", 2), item("bread", 5, 1, 3),
                                   item("iron_axe", 2, dmg=(0.4, 0.9)), item("book", 2, rand_ench=True), empty(4)]),
                         ((1, 2), [item("emerald", 4, 1, 2), item("gold_ingot", 2), empty(8)])),
    "tienda": botin.cofre(((2, 3), [item("bread", 6, 1, 2), item("cooked_beef", 4, 1, 2), item("string", 5, 1, 3),
                                    item("arrow", 5, 2, 6), item("rabbit_hide", 4, 1, 2), item("torch", 4, 1, 4),
                                    empty(6)]),
                          ((1, 1), [item("emerald", 2), empty(8)])),
}

L = 21
CX, CZ = 10, 11            # fogata


def _suelo(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 3 + z * 7 + (x ^ z)) % len(mats)]


def _tienda(t, p, x0, z0, abierta, color):
    """Tienda de 5 de ancho (x0..x0+4) y 4 de fondo, con la entrada hacia `abierta` (north o south): dos faldones de
    lona, cumbrera de lona y el fondo cerrado; dentro, un saco de dormir (cama) y un tonel."""
    lona = f"{color}_wool"
    z1 = z0 + 3
    fondo = z1 if abierta == "north" else z0
    for z in range(z0, z1 + 1):
        t.set(x0, 1, z, lona)
        t.set(x0 + 4, 1, z, lona)
        t.set(x0 + 1, 2, z, lona)
        t.set(x0 + 3, 2, z, lona)
        t.set(x0 + 2, 3, z, lona)
        for x, y in ((x0 + 1, 1), (x0 + 2, 1), (x0 + 3, 1), (x0 + 2, 2)):
            t.set(x, y, z, "air")
    for x, y in ((x0 + 1, 1), (x0 + 2, 1), (x0 + 3, 1), (x0 + 2, 2)):
        t.set(x, y, fondo, lona)
    paso = -1 if abierta == "north" else 1        # del fondo hacia la entrada
    t.set(x0 + 1, 1, fondo + paso, f"{p['cama']}_bed[facing={'south' if abierta == 'north' else 'north'},occupied=false,part=head]")
    t.set(x0 + 1, 1, fondo + 2 * paso, f"{p['cama']}_bed[facing={'south' if abierta == 'north' else 'north'},occupied=false,part=foot]")
    t.set(x0 + 3, 1, fondo + paso, f"{p['carpet']}_carpet")
    return x0 + 3, fondo + paso


def _claro(x, z):
    """Claro redondo (sin empalizada): fuera queda el terreno natural."""
    return (x - CX) ** 2 + (z - CX) ** 2 <= (CX + 0.5) ** 2


def _comun(p, name, tiendas, redondo=True):
    t = Template(name)
    m = p["madera"]
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=3, dentro=_claro if redondo else None)
    c.entrada(t, CX, "minecraft:dirt_path")
    t.set(CX, 1, CZ, "campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    for dx, dz, ax in ((-2, 0, "z"), (2, 0, "z"), (0, 2, "x")):    # bancos de troncos alrededor (abierto al norte)
        for k in (-1, 0, 1):
            x, z = CX + dx + (k if ax == "x" else 0), CZ + dz + (k if ax == "z" else 0)
            t.set(x, 1, z, f"{p['tronco']}[axis={ax}]")
    huecos = []
    for x0, z0, abierta, color in tiendas:
        huecos.append(_tienda(t, p, x0, z0, abierta, color))
    # tonel del botín junto a la fogata y estandarte del grupo en un poste
    c.cofre(t, CX + 3, 1, CZ - 2, "up", MID, "botin", kind="barrel")
    t.set(CX - 3, 1, CZ - 3, f"{m}_fence")
    t.set(CX - 3, 2, CZ - 3, f"{m}_fence")
    t.set(CX - 3, 3, CZ - 3, f"{p['estandarte']}_banner[rotation=0]")
    return t, huecos


def bandido(mob, clave, fallback, rot, arma=None):
    extra = {"PatrolLeader": B(0), "Patrolling": B(0), "CanJoinRaid": B(0)}
    if arma:
        extra["equipment"] = {"mainhand": {"id": f"minecraft:{arma}", "count": 1}}
    return c.mob(mob, MID, clave, fallback, rot=rot, **extra)


def dos_tiendas(p, name):
    t, huecos = _comun(p, name, [(2, 4, "south", p["lonas"][0]), (14, 4, "south", p["lonas"][1])])
    x, z = huecos[0]
    c.cofre(t, x, 1, z, "north", MID, "tienda", kind="barrel")
    t.entity(CX - 1, 1, CZ - 2, bandido("pillager", "saqueador", "Bandido", 0.0))
    t.entity(CX + 2, 1, CZ + 3, bandido("pillager", "saqueador", "Bandido", 180.0))
    return t


def empalizada(p, name):
    t, huecos = _comun(p, name, [(2, 4, "south", p["lonas"][0]), (14, 4, "south", p["lonas"][1]),
                                 (2, 14, "north", p["lonas"][0])], redondo=False)
    # empalizada de troncos en el borde (con la entrada abierta al norte, ancho 3)
    for x in range(L):
        for z in range(L):
            if (x in (0, L - 1) or z in (0, L - 1)) and not (z == 0 and abs(x - CX) <= 1):
                h = 2 if (x + z) % 3 or (z == 0 and abs(x - CX) == 2) else 3
                for y in range(1, h + 1):
                    t.set(x, y, z, f"{p['tronco']}[axis=y]")
    for x in (CX - 2, CX + 2):
        c.farol(t, x, 3, 0, colgado=False)
    x, z = huecos[2]
    c.cofre(t, x, 1, z, "south", MID, "tienda", kind="barrel")
    t.entity(CX + 1, 1, CZ - 2, bandido("vindicator", "vindicador", "Jefe de los bandidos", 0.0, arma="iron_axe"))
    t.entity(CX - 2, 1, CZ + 3, bandido("pillager", "saqueador", "Bandido", 180.0))
    return t


ESTILOS = {
    "bosque": dict(biomas=["forest", "birch_forest", "old_growth_birch_forest", "flower_forest"],
                   convencionales=["c:is_birch_forest", "c:is_flower_forest"],
                   paleta=dict(madera="oak", tronco="oak_log", cama="brown", carpet="green", estandarte="black",
                               lonas=["white", "light_gray"],
                               suelo=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:dirt_path"]),
                   variantes={"a": dos_tiendas, "b": empalizada}),
    "taiga": dict(biomas=["taiga", "old_growth_pine_taiga", "old_growth_spruce_taiga", "snowy_taiga"],
                  convencionales=["minecraft:is_taiga", "c:is_taiga"],
                  paleta=dict(madera="spruce", tronco="spruce_log", cama="gray", carpet="brown", estandarte="black",
                              lonas=["brown", "gray"],
                              suelo=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:cobblestone"]),
                  variantes={"a": dos_tiendas, "b": empalizada}),
    "badlands": dict(biomas=["badlands", "wooded_badlands", "eroded_badlands"],
                     convencionales=["minecraft:is_badlands", "c:is_badlands"],
                     paleta=dict(madera="dark_oak", tronco="dark_oak_log", cama="red", carpet="orange", estandarte="black",
                                 lonas=["orange", "brown"],
                                 suelo=["minecraft:red_sandstone", "minecraft:dirt_path", "minecraft:smooth_red_sandstone"]),
                     variantes={"a": dos_tiendas, "b": empalizada}),
}
