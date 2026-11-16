"""Molino (heraldia:medianas/molino/<estilo>): patio de 19 x 19 con un molino y su campo. Variante a: molino de agua,
casa de 7 x 9 con la muela (afiladera), la rueda de paletas en un caz con agua quieta al este y el molinero (aldeano
quieto con tratos fijos: compra trigo, vende pan y harina para tarta); b: molino de viento, torre de 7 x 7 y tres plantas
con las aspas al sur y un trigal con su acequia al este, sin nadie. Sin monstruos."""
from core import Template
from loot import item, empty
from unicas._comun import botin
from . import _comun as c

MID = "molino"
NOMBRE = {"es_es": "Molino", "en_us": "Mill"}
SEPARACION = 832
LOGRO_ICONO = "minecraft:wheat"
LANG = botin.lang("heraldia.medianas.molino.", {
    "molinero": ("Molinero", "Miller"),
})
LOGROS = [dict(id="molienda", icono="minecraft:bread", tabla="molienda",
               titulo=("Grano y muela", "Grist for the Mill"),
               descripcion=("Abre los costales de un molino", "Open the sacks of a mill"))]
LOOT = {
    "molienda": botin.cofre(((3, 5), [item("wheat", 10, 3, 9), item("bread", 8, 1, 4), item("sugar", 5, 1, 4),
                                      item("egg", 4, 1, 3), item("wheat_seeds", 6, 2, 6), item("beetroot_seeds", 3, 1, 4),
                                      item("bone_meal", 4, 2, 5), item("hay_block", 2), item("pumpkin_pie", 2),
                                      empty(4)]),
                            ((1, 1), [item("cake", 1), item("emerald", 2), empty(8)])),
    "molinero": botin.cofre(((2, 4), [item("bread", 6, 1, 3), item("paper", 4, 1, 3), item("candle", 4, 1, 2),
                                      item("iron_nugget", 5, 2, 6), item("shears", 2, dmg=(0.3, 0.8)),
                                      item("iron_hoe", 2, dmg=(0.4, 0.9)), item("leather", 3, 1, 2), item("compass", 1),
                                      empty(6)]),
                            ((1, 1), [item("emerald", 3, 1, 2), empty(8)])),
}

L = 19
PUERTA = 6                         # eje de la puerta (las dos variantes)


def ofertas():
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [c.oferta({"id": "minecraft:wheat", "count": 20}, em(1), 16),
            c.oferta(em(1), {"id": "minecraft:bread", "count": 6}, 12),
            c.oferta(em(1), {"id": "minecraft:sugar", "count": 8}, 8),
            c.oferta(em(2), {"id": "minecraft:cake", "count": 1}, 4)]


def _suelo(p):
    mats = p["patio"]
    return lambda x, z: "minecraft:dirt_path" if x == PUERTA and z < 5 else mats[(x * 5 + z * 9 + x * z) % len(mats)]


def _patio(t, p):
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=3)
    c.entrada(t, PUERTA, f"{p['peldano']}[facing=south,half=bottom,shape=straight,waterlogged=false]")


def _rueda(t, p, x, cy, cz, r=3):
    """Rueda de paletas en el plano x (eje a lo largo de x): aro de tablones, radios de valla y el cubo de tronco."""
    m = p["madera"]
    for dy in range(-r, r + 1):
        for dz in range(-r, r + 1):
            d = (dy * dy + dz * dz) ** 0.5
            if r - 0.5 <= d < r + 0.5:
                t.set(x, cy + dy, cz + dz, f"{m}_planks")
    for k in range(1, r):
        for dy, dz in ((k, 0), (-k, 0), (0, k), (0, -k)):
            t.set(x, cy + dy, cz + dz, f"{m}_fence")
    t.set(x, cy, cz, f"{p['tronco']}[axis=x]")


def agua(p, name):
    """Molino de agua: casa de 7 x 9 (x 3..9, z 5..13), caz al este (x = 12) con la rueda y el molinero dentro."""
    t = Template(name)
    _patio(t, p)
    m = p["madera"]
    X0, Z0, X1, Z1 = 3, 5, 9, 13
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    t.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, f"{m}_planks")
    c.caja(t, X0, 1, Z0, X1, 4, Z1, p["muro"], esquina=f"{p['tronco']}[axis=y]")
    t.fill(X0, 1, Z0, X1, 1, Z1, p["zocalo"])                      # hilada baja de piedra
    for x, z in ((X0, Z0), (X0, Z1), (X1, Z0), (X1, Z1)):
        t.set(x, 1, z, f"{p['tronco']}[axis=y]")
    t.fill(X0 + 1, 1, Z0 + 1, X1 - 1, 1, Z1 - 1, "air")
    t.fill(X0, 5, Z0, X1, 5, Z1, f"{m}_planks")
    c.tejado(t, X0, Z0, X1, Z1, 5, p["teja"], p["cumbrera"], p["muro"])
    c.door(t, PUERTA, 1, Z0, "south", f"{m}_door")
    for z in (7, 11):
        c.ventana(t, X0, 2, z)
    c.ventana(t, X1, 2, 7)
    c.ventana(t, X1, 2, 11)
    # caz: agua quieta en y = 0 (todo fuentes) entre dos pretiles, con la rueda encima; el eje entra por el muro este
    for z in range(3, 16):
        t.set(11, 0, z, p["pretil"])
        t.set(13, 0, z, p["pretil"])
        t.set(12, 0, z, "water[level=0]")
    t.set(12, 0, 2, p["pretil"])
    t.set(12, 0, 16, p["pretil"])
    _rueda(t, p, 12, 4, 9)
    t.set(X1, 4, 9, f"{p['tronco']}[axis=x]")
    t.set(10, 4, 9, f"{p['tronco']}[axis=x]")
    t.set(11, 4, 9, f"{p['tronco']}[axis=x]")
    # dentro: la muela junto al eje, costales (toneles y paja), el cofre y la cama del molinero
    t.set(X1 - 1, 1, 9, "grindstone[face=floor,facing=north]")
    t.set(X1 - 1, 4, 9, f"stripped_{p['tronco']}[axis=x]")
    t.fill(X1 - 1, 2, 9, X1 - 1, 3, 9, f"{m}_fence")
    c.cofre(t, X1 - 1, 1, Z1 - 1, "west", MID, "molienda", kind="barrel")
    t.set(X1 - 1, 1, Z1 - 2, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    t.set(X1 - 1, 1, Z0 + 1, "hay_block[axis=y]")
    t.set(X1 - 1, 2, Z0 + 1, "hay_block[axis=y]")
    t.set(X1 - 2, 1, Z0 + 1, "hay_block[axis=y]")
    c.cama(t, X0 + 1, Z1 - 1, "west", p["cama"])
    c.cofre(t, X0 + 1, 1, Z1 - 3, "east", MID, "molinero")
    t.set(X0 + 1, 1, Z0 + 1, "crafting_table")
    c.farol(t, PUERTA, 4, 9)
    t.entity(PUERTA, 1, 11, c.aldeano(MID, "molinero", "Molinero", "farmer", p["aldeano"], ofertas(), rot=0.0))
    # fuera: sacos apilados junto a la puerta y una carreta de heno
    t.set(PUERTA + 2, 1, 3, "hay_block[axis=x]")
    t.set(PUERTA + 3, 1, 3, "hay_block[axis=x]")
    t.set(PUERTA - 2, 1, 3, "composter[level=0]")
    return t


def viento(p, name):
    """Molino de viento: torre de 7 x 7 (x 3..9, z 5..11), tres plantas con escalera de mano, aspas en la cara sur y un
    trigal con acequia al este; sin nadie."""
    t = Template(name)
    _patio(t, p)
    m = p["madera"]
    X0, Z0, X1, Z1 = 3, 5, 9, 11
    CX = 6
    techo = 13
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    t.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, f"{m}_planks")
    c.caja(t, X0, 1, Z0, X1, techo - 1, Z1, p["muro"], esquina=f"{p['tronco']}[axis=y]")
    t.fill(X0, 1, Z0, X1, 4, Z1, p["zocalo"])                       # el primer piso, de piedra
    for x, z in ((X0, Z0), (X0, Z1), (X1, Z0), (X1, Z1)):
        t.fill(x, 1, z, x, techo - 1, z, f"{p['tronco']}[axis=y]")
    t.fill(X0 + 1, 1, Z0 + 1, X1 - 1, techo - 1, Z1 - 1, "air")
    for y in (5, 9):
        t.fill(X0 + 1, y, Z0 + 1, X1 - 1, y, Z1 - 1, f"{m}_planks")
    t.fill(X0, techo, Z0, X1, techo, Z1, f"{m}_planks")
    # tejado a cuatro aguas: anillos de escalones que se cierran hasta una cumbrera
    for k in range(4):
        y = techo + 1 + k
        xa, xb, za, zb = X0 - 1 + k, X1 + 1 - k, Z0 - 1 + k, Z1 + 1 - k
        if xa >= xb or za >= zb:
            break
        for x in range(xa, xb + 1):
            t.set(x, y, za, f"{p['teja']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
            t.set(x, y, zb, f"{p['teja']}[facing=north,half=bottom,shape=straight,waterlogged=false]")
        for z in range(za + 1, zb):
            t.set(xa, y, z, f"{p['teja']}[facing=east,half=bottom,shape=straight,waterlogged=false]")
            t.set(xb, y, z, f"{p['teja']}[facing=west,half=bottom,shape=straight,waterlogged=false]")
        for x in range(xa + 1, xb):
            for z in range(za + 1, zb):
                t.set(x, y, z, p["cumbrera"])
    c.door(t, CX, 1, Z0, "south", f"{m}_door")
    c.escalera_mano(t, X0 + 1, Z1 - 1, 1, 9, "north")               # pegada al muro sur; atraviesa los dos forjados
    for y in (2, 7, 11):
        c.ventana(t, X0, y, 8)
        c.ventana(t, X1, y, 8)
    c.ventana(t, CX, 7, Z0)
    c.ventana(t, CX, 11, Z0)
    # aspas: eje de tronco que sale por el muro sur (y = 10) y cuatro brazos con su lona
    hy, hz = 10, Z1 + 1
    t.set(CX, hy, Z1, f"{p['tronco']}[axis=z]")
    t.set(CX, hy, hz, f"{p['tronco']}[axis=z]")
    for k in range(1, 6):
        t.set(CX, hy + k, hz, f"stripped_{p['tronco']}[axis=y]")
        t.set(CX, hy - k, hz, f"stripped_{p['tronco']}[axis=y]")
        t.set(CX + k, hy, hz, f"stripped_{p['tronco']}[axis=x]")
        t.set(CX - k, hy, hz, f"stripped_{p['tronco']}[axis=x]")
        if k >= 2:
            t.set(CX + 1, hy + k, hz, p["lona"])
            t.set(CX - 1, hy - k, hz, p["lona"])
            t.set(CX + k, hy - 1, hz, p["lona"])
            t.set(CX - k, hy + 1, hz, p["lona"])
    # planta baja: la muela y los costales; primera: grano; segunda: el eje con su rueda dentada
    t.set(X1 - 1, 1, Z0 + 2, "grindstone[face=floor,facing=north]")
    c.cofre(t, X1 - 1, 1, Z1 - 1, "west", MID, "molienda", kind="barrel")
    t.set(X1 - 1, 1, Z0 + 1, "hay_block[axis=y]")
    c.farol(t, CX, 4, 8)
    t.set(X1 - 1, 6, Z0 + 1, "hay_block[axis=y]")
    t.set(X1 - 1, 6, Z0 + 2, "hay_block[axis=y]")
    t.set(X1 - 1, 7, Z0 + 1, "hay_block[axis=y]")
    c.cofre(t, X1 - 1, 6, Z1 - 1, "west", MID, "molinero")
    c.farol(t, CX, 8, 8)
    t.fill(CX, hy, Z0 + 2, CX, hy, Z1 - 1, f"stripped_{p['tronco']}[axis=z]")
    t.set(CX, 10, Z0 + 1, f"{m}_planks")                            # cojinete del eje en el muro norte
    c.farol(t, X1 - 1, 12, Z0 + 1)
    # trigal al este con su acequia (una fuente en el centro) y un espantapájaros
    x0, x1, z0, z1 = 12, 16, 4, 14
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if (x, z) == ((x0 + x1) // 2, (z0 + z1) // 2):
                t.set(x, 0, z, "water[level=0]")
            else:
                t.set(x, 0, z, "farmland[moisture=7]")
                t.set(x, 1, z, p["cultivos"][(x + z) % len(p["cultivos"])])
    t.set(x1 + 1, 1, 9, f"{m}_fence")
    t.set(x1 + 1, 2, 9, "carved_pumpkin[facing=west]")
    t.set(x0 - 1, 1, z0, "composter[level=0]")
    return t


_CULT = ["wheat[age=7]", "wheat[age=7]", "beetroots[age=3]"]
ESTILOS = {
    "llanura": dict(biomas=["plains", "sunflower_plains"], convencionales=["c:is_plains"],
                    paleta=dict(madera="oak", tronco="oak_log", muro="white_terracotta", zocalo="cobblestone",
                                pretil="stone_bricks", teja="spruce_stairs", cumbrera="spruce_planks",
                                peldano="cobblestone_stairs", lona="white_wool", cama="yellow", aldeano="plains",
                                cultivos=_CULT,
                                patio=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:dirt_path",
                                       "minecraft:gravel"]),
                    variantes={"a": agua, "b": viento}),
    "pantano": dict(biomas=["swamp"],
                    paleta=dict(madera="mangrove", tronco="mangrove_log", muro="mud_bricks", zocalo="cobblestone",
                                pretil="mud_bricks", teja="dark_oak_stairs", cumbrera="dark_oak_planks",
                                peldano="mud_brick_stairs", lona="light_gray_wool", cama="green", aldeano="swamp",
                                cultivos=["wheat[age=7]", "potatoes[age=7]", "carrots[age=7]"],
                                patio=["minecraft:packed_mud", "minecraft:dirt_path", "minecraft:mud_bricks"]),
                    variantes={"a": agua, "b": viento}),
}
