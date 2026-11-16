"""Planos de las entradas a mina: cada tamaño (pequeña, mediana, grande) junta la superficie, la boca, la bajada y su
galería en una sola plantilla por estilo y variante (ver obra.py para las coordenadas).

  pequeña  bajada de 14 a la galería (3 x 2 cruces, almacén y filón).
  mediana  bajada de 16 a una galería de 5 x 3 cruces (almacén, filón, comedor y la sala de las arañas).
  grande   bajada de 20 y el pozo de la torre (escalera de caracol) a una red de 7 x 4 cruces (almacén, polvorín,
           comedor, filón) y, por otra rampa de 12, al nivel hondo (3 x 2): la sala del filón rico y la de las arañas
           con su generador pequeño.
"""
import random
from core import Template, B
from unicas._comun import piezas
from . import superficie as sup
from .obra import Obra, PASO, ALTO, mob

# tamaño -> (profundidad de la bajada, cruces a cada lado, filas, salas, patio (x, z), aire sobre el patio)
TAMANOS = {
    "pequena": dict(hondo=14, ni=1, nj=2, salas=("filon", "almacen"), patio=(6, 8)),
    "mediana": dict(hondo=16, ni=2, nj=3, salas=("aranas", "filon", "almacen", "comedor"), patio=(11, 16)),
    "grande": dict(hondo=20, ni=3, nj=4, salas=("filon", "almacen", "polvorin", "comedor"), patio=(15, 22),
                   hondo2=12, salas2=("aranas", "tesoro")),
}
POZO = (8, -12)                  # eje del pozo de la torre (grande), sin reflejar


def construir(tam, estilo, variante, pal, nombre):
    """Obra completa; devuelve la obra (con su plantilla en o.t, sin normalizar)."""
    d = TAMANOS[tam]
    m = 1 if variante == "a" else -1
    rng = random.Random(f"heraldia:minas/{tam}/{estilo}/{variante}")
    o = Obra(Template(nombre), pal, rng)
    e = sup.Espejo(o, m)
    px, pz = d["patio"]
    sup.patio(o, -px, px, -pz, -1)
    sup.boca(o)
    sup.cartel(o, -3, -1, tam)
    # bajada: tramo llano bajo la boca, rampa y tramo llano hasta el primer cruce
    o.corredor((0, 0), (0, 2), 1, vias=True, marcos=False)
    zf, pies = o.rampa(0, 2, 1, d["hondo"])
    z0 = zf + 5
    o.corredor((0, zf + 1), (0, z0 - 1), pies, vias=True, marcos=False)
    pos, salas = o.red(0, z0, pies, d["ni"], d["nj"], d["salas"], extra=0.25 if tam != "pequena" else 0.15)
    for tipo, (cx, cz) in salas.items():
        amueblar(o, tipo, cx, cz, pies, tam)
    fin = pos[(0, d["nj"] - 1)]
    if tam == "pequena":
        patio_pequena(o, e)
    elif tam == "mediana":
        patio_mediana(o, e)
        o.t.entity(0, pies, zf + 3, {"id": "minecraft:minecart"})
    else:
        patio_grande(o, e)
        pozo(o, m, pies, z0)
        o.t.entity(0, pies, zf + 3, {"id": "minecraft:minecart"})
        # nivel hondo: la vía del tronco sigue por otra rampa desde su último cruce
        nx, nz = fin
        zf2, pies2 = o.rampa(nx, nz, pies, d["hondo2"])
        z2 = zf2 + 5
        o.corredor((nx, zf2 + 1), (nx, z2 - 1), pies2, vias=True, marcos=False)
        pos2, salas2 = o.red(nx, z2, pies2, 1, 2, d["salas2"], extra=0.3)
        for tipo, (cx, cz) in salas2.items():
            amueblar(o, tipo, cx, cz, pies2, tam)
    o.forro()
    o.vetas(0.05)
    for tipo, x0, x1, z0_, z1, p in o.salas:
        if tipo in ("filon", "tesoro"):
            vetas_sala(o, x0, x1, z0_, z1, p)
    o.casco()
    return o


# ------------------------------------------------------------------ patios
def patio_pequena(o, e):
    sup.vias(o, -6, -1)
    o.s(0, 1, -7, "barrel[facing=north,open=false]", {"id": "minecraft:barrel"})
    o.t.entity(0, 1, -4, {"id": "minecraft:minecart"})
    piezas.chest(e.s, -4, 1, -5, "up", "heraldia:minas/boca", kind="barrel")
    o.cofres.append(((e.x(-4), 1, -5), "boca"))
    sup.monton(e, 3, -7, 3, 3)
    sup.poste(o, e.x(-4), -7)
    e.s(-3, 1, -7, "grindstone[face=floor,facing=north]")
    o.vias.append(((0, 1, -6), "south", None))


def patio_mediana(o, e):
    sup.vias(o, -12, -1)
    o.s(0, 1, -13, "barrel[facing=north,open=false]", {"id": "minecraft:barrel"})
    o.t.entity(0, 1, -9, {"id": "minecraft:chest_minecart", "LootTable": "heraldia:minas/vagoneta"})
    o.cofres.append(((0, 1, -9), "vagoneta"))
    sup.caseta(e, 4, -14, 9, -8, "west", "capataz")
    sup.monton(e, -9, -14, 5, 5)
    sup.fundicion(e, -9, -7, "fundicion")
    for x, z in ((-3, -12), (3, -12), (-10, -15), (10, -2)):
        sup.poste(o, e.x(x), z)
    o.vias.append(((0, 1, -12), "south", None))


def patio_grande(o, e):
    # vía principal hasta la curva, ramal hacia la torre y el cargadero con su tope
    sup.vias(o, -16, -1)
    sup.rail(o.s, o, 0, -17, "south_east" if e.m == 1 else "south_west")
    for x in range(1, 12):
        sup.rail(e.s, o, x, -17, "east_west")
    e.s(12, 1, -17, "barrel[facing=north,open=false]", {"id": "minecraft:barrel"})
    o.t.entity(e.x(5), 1, -17, {"id": "minecraft:chest_minecart", "LootTable": "heraldia:minas/vagoneta"})
    o.cofres.append(((e.x(5), 1, -17), "vagoneta"))
    o.t.entity(0, 1, -8, {"id": "minecraft:minecart"})
    sup.torre(e, *POZO)
    sup.caseta(e, -13, -20, -7, -14, "east", "capataz")
    sup.fundicion(e, -13, -9, "fundicion")
    sup.monton(e, 11, -22 + 1, 4, 3)
    for x, z in ((-3, -14), (3, -14), (-14, -2), (14, -2), (-5, -20), (5, -20)):
        sup.poste(o, e.x(x), z)
    o.vias.append(((0, 1, -16), "south", None))


def pozo(o, m, pies, z0):
    """Pozo vertical de la torre: hueco de 3 x 3 alrededor de un machón de tronco con una escalera de caracol desde el
    patio (el último peldaño en y = 0, a ras) hasta la galería, barandilla en el brocal (salvo la salida al norte) y,
    abajo, un túnel hasta el cruce (m, 0) de la red."""
    cx, cz = m * POZO[0], POZO[1]
    ring = [(cx + dx, cz + dz) for dx, dz in piezas.RING8]
    n = 1 - pies                         # peldaños de los pies de la galería (pies) a y = 0
    for (x, z) in ring:
        for y in range(pies, 1):
            o.hueco(x, y, z)
    for y in range(pies - 1, 1):
        o.s(cx, y, cz, o.tronco("y"))
    piezas.spiral_continuous(o.s, ring, pies, n, f"{o.p['escalon_piedra']}", start=6, under=True)
    for (x, z) in ring:                  # el brocal: los peldaños de arriba en el patio son de la obra, no del patio
        o.superficie.discard((x, 0, z))
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if max(abs(dx), abs(dz)) == 2 and (dx, dz) != (0, -2) and abs(dx) + abs(dz) != 4:
                o.s(cx + dx, 1, cz + dz, f"{o.p['madera']}_fence")
    o.bajada = (cx, pies, cz)
    # salida al sur por la celda (0, 1) del anillo y túnel hasta la red
    o.corredor((cx, cz + 2), (cx, z0), pies, marcos=True)


# ------------------------------------------------------------------ salas
def amueblar(o, tipo, cx, cz, pies, tam):
    """Sala de su tipo en el cruce (cx, cz): muebles en los cuatro huecos junto a los muros norte y sur (cx ± 2), que
    nunca tapan la llegada de un túnel (por el centro de cada lado)."""
    o.sala(tipo, cx, cz, pies)
    huecos = [(cx - 2, cz - 2, "south"), (cx + 2, cz - 2, "south"), (cx - 2, cz + 2, "north"), (cx + 2, cz + 2, "north")]
    tabla = {"tesoro": "filon"}.get(tipo, "galeria")
    x, z, f = huecos[0]
    o.cofre(x, pies, z, f, tabla)
    resto = huecos[1:]
    if tipo == "almacen":
        for x, z, f in resto:
            o.s(x, pies, z, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
            o.s(x, pies + 1, z, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    elif tipo == "comedor":
        x, z, f = resto[0]
        o.s(x, pies, z, "crafting_table")
        x, z, f = resto[1]
        o.s(x, pies, z, f"{o.p['madera']}_fence")
        o.s(x, pies + 1, z, f"{o.p['madera']}_pressure_plate[powered=false]")
        x, z, f = resto[2]
        o.s(x, pies, z, "furnace[facing=north,lit=false]")
    elif tipo == "polvorin":
        for x, z, f in resto:
            o.s(x, pies, z, "tnt[unstable=false]")
        o.s(cx + 2, pies + 1, cz - 2, "tnt[unstable=false]")
    elif tipo in ("filon", "tesoro"):
        x, z, f = resto[0]
        o.s(x, pies, z, "grindstone[face=floor,facing=south]")
        x, z, f = resto[2]
        o.s(x, pies, z, f"{o.p['madera']}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    elif tipo == "aranas":
        o.telarañas(cx - 3, cx + 3, cz - 2, cz + 2, pies, 6, alto=4)
        if tam == "grande":
            o.s(cx, pies, cz + 2, o.mat(o.p["muro"], cx, pies, cz))
            piezas.spawner(o.s, cx, pies + 1, cz + 2, "cave_spider", potentials=True, luz=11)
            st, nbt = o.t.blocks[(cx, pies + 1, cz + 2)]
            nbt.update({"SpawnCount": 2, "MaxNearbyEntities": 3, "RequiredPlayerRange": 12, "SpawnRange": 3,
                        "MinSpawnDelay": 300, "MaxSpawnDelay": 700, "Delay": 20})
            o.generadores.append((cx, pies + 1, cz + 2))
        else:
            for x, z, f in resto[:2]:
                o.t.entity(x, pies, z + (1 if f == "south" else -1), mob("cave_spider"))


def vetas_sala(o, x0, x1, z0, z1, pies):
    """Muros de la sala del filón cuajados de mineral (más que las vetas de los túneles)."""
    from .obra import h
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            for y in range(pies, pies + 4):
                st = o.t.get(x, y, z)
                if (x, y, z) in o.carved or st is None or st.split("[")[0].replace("minecraft:", "") not in o.p["muro"]:
                    continue
                if h(x, y, z, 33) < 0.35:
                    o.s(x, y, z, o.mat(o.p["vetas_ricas"], x, y, z, 7))
