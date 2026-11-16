"""Superficie de las entradas a mina: patio sobre su cimiento, boca con su entibado y lo que hay delante según el tamaño
(pequeña: boca con vías, vagoneta y faroles; mediana: campamento con la cabaña del capataz, el montón de mineral, la
vagoneta de carga y la fundición; grande: complejo con la torre de extracción y su polea sobre el pozo, vías y oficina).

Todo se escribe con `Espejo`, que refleja el patio en x en la variante b (los estados con lado este u oeste también),
así la misma obra sale con los edificios a un lado o al otro. La boca y las vías del centro (x = 0) no cambian."""
from unicas._comun import piezas

FLIP = {"east": "west", "west": "east"}


def _flip_estado(st):
    if "[" not in st:
        return st
    base, props = st[:-1].split("[", 1)
    out = []
    for kv in props.split(","):
        k, v = kv.split("=")
        if k == "facing":
            v = FLIP.get(v, v)
        elif k == "shape" and ("east" in v or "west" in v) and v != "east_west":
            v = "_".join(FLIP.get(w, w) for w in v.split("_"))
        elif k == "hinge":
            v = {"left": "right", "right": "left"}[v]
        elif k in ("east", "west"):
            k = FLIP[k]
        out.append(f"{k}={v}")
    return f"{base}[{','.join(out)}]"


class Espejo:
    """Escritura del patio (todo va a la superficie de la obra) con reflejo en x si m = -1."""

    def __init__(self, o, m):
        self.o, self.m = o, m

    def s(self, x, y, z, st, nbt=None):
        p = (self.m * x, y, z)
        self.o.s(*p, st if self.m == 1 else _flip_estado(st), nbt)
        self.o.superficie.add(p)

    def x(self, x):
        return self.m * x

    def cara(self, f):
        return f if self.m == 1 else FLIP.get(f, f)


def patio(o, x0, x1, z0, z1, aire=6, cimiento=4):
    """Suelo del patio en y = 0 sobre `cimiento` capas de obra (en ladera asoma como un muro de contención) y aire
    explícito encima (lo que hubiera en el terreno no asoma)."""
    p = o.p
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            borde = x in (x0, x1) or z in (z0, z1)
            o.s(x, 0, z, o.mat(p["cimiento"] if borde else p["patio"], x, 0, z))
            for y in range(-cimiento, 0):
                o.s(x, y, z, o.mat(p["cimiento"], x, y, z, 3))
            for y in range(1, aire + 1):
                o.s(x, y, z, "air")
            for y in range(-cimiento, aire + 1):
                o.superficie.add((x, y, z))


def boca(o):
    """Fachada de la boca en z = 0: muro de obra de 7 x 5 con el hueco del túnel (3 x 3), postes y dintel de tronco y
    remates de escalón; los faroles a los lados sobre postes de valla."""
    p = o.p
    for x in range(-3, 4):
        for y in range(1, 6):
            if abs(x) <= 1 and y <= 3:
                continue
            if abs(x) == 2 and y <= 3:
                st = o.tronco("y")
            elif y == 4:
                st = o.tronco("x")
            else:
                st = o.mat(p["muro"], x, y, 0)
            o.s(x, y, 0, st)
            o.superficie.add((x, y, 0))
    for x, f in ((-3, "east"), (3, "west")):
        o.s(x, 5, -1, f"{p['madera']}_stairs[facing={f},half=bottom,shape=straight,waterlogged=false]")
    for x in (-4, 4):
        poste(o, x, -1)


def poste(o, x, z, alto=2):
    """Poste de valla con un farol de pie encima."""
    for y in range(1, alto + 1):
        o.s(x, y, z, f"{o.p['madera']}_fence")
    o.farol(x, alto + 1, z, colgado=False)


def vias(o, z0, z1, x=0):
    """Vía recta de norte a sur por x de z0 a z1 (incluidos), a ras del patio."""
    for z in range(min(z0, z1), max(z0, z1) + 1):
        rail(o.s, o, x, z, "north_south")


def rail(put, o, x, z, shape):
    """Raíl del patio sobre un bloque macizo de cimiento (un raíl no se sostiene sobre un camino de tierra o una losa:
    al primer aviso de un vecino saltaría)."""
    put(x, 0, z, o.mat(o.p["cimiento"], x, 0, z, 5))
    put(x, 1, z, f"rail[shape={shape},waterlogged=false]")


def monton(e, x0, z0, ancho, fondo):
    """Montón de mineral en el patio: capas cada vez más estrechas de grava, piedra y menas."""
    o = e.o
    for capa in range(3):
        for x in range(x0 + capa, x0 + ancho - capa):
            for z in range(z0 + capa, z0 + fondo - capa):
                esquina = x in (x0 + capa, x0 + ancho - capa - 1) and z in (z0 + capa, z0 + fondo - capa - 1)
                if capa < 2 and esquina:
                    continue
                e.s(x, 1 + capa, z, o.mat(o.p["mineral"], x, capa, z, 11))


def caseta(e, x0, z0, x1, z1, puerta, tabla, cama=True):
    """Cabaña de tablas con esquinas de tronco, tejado a dos aguas (cumbrera de este a oeste), puerta en el muro
    `puerta` (west o east, en coordenadas sin reflejar) y dentro una cama, una mesa, un banco de trabajo, un farol y el
    cofre `tabla`."""
    o, p = e.o, e.o.p
    for y in range(1, 4):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                borde = x in (x0, x1) or z in (z0, z1)
                esquina = x in (x0, x1) and z in (z0, z1)
                e.s(x, y, z, o.tronco("y") if esquina else p["tablas"] if borde else "air")
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            e.s(x, 0, z, p["tablas"])
    cz = (z0 + z1) // 2
    px = x0 if puerta == "west" else x1
    piezas.door(e.s, px, 1, cz, puerta, kind=f"{p['madera']}_door")
    e.s(px + (-1 if puerta == "west" else 1), 0, cz, p["tablas"])
    for x in ((x0 + x1) // 2,):
        e.s(x, 2, z0, "glass_pane[north=false,south=false,east=true,west=true,waterlogged=false]")
        e.s(x, 2, z1, "glass_pane[north=false,south=false,east=true,west=true,waterlogged=false]")
    otro = x1 - 1 if puerta == "west" else x0 + 1
    if cama:
        e.s(otro, 1, z0 + 1, f"{p['cama']}_bed[facing=north,occupied=false,part=head]")
        e.s(otro, 1, z0 + 2, f"{p['cama']}_bed[facing=north,occupied=false,part=foot]")
    e.s(otro, 1, z1 - 1, "crafting_table")
    lado = "east" if puerta == "west" else "west"
    cx = (x0 + x1) // 2
    piezas.chest(e.s, cx, 1, z0 + 1, "south", f"heraldia:minas/{tabla}")
    o.cofres.append(((e.x(cx), 1, z0 + 1), tabla))
    e.s(cx, 1, z1 - 1, f"{p['madera']}_fence")
    e.s(cx, 2, z1 - 1, f"{p['madera']}_pressure_plate[powered=false]")
    e.s(cx + (1 if lado == "east" else -1), 1, z1 - 1, f"{p['madera']}_stairs[facing={lado},half=bottom,shape=straight,waterlogged=false]")
    e.s(cx, 3, cz, "lantern[hanging=true,waterlogged=false]")
    # tejado a dos aguas a lo largo de x, con un bloque de vuelo
    za, zb, y = z0 - 1, z1 + 1, 4
    while za <= zb:
        for x in range(x0 - 1, x1 + 2):
            if za == zb:
                e.s(x, y, za, f"{p['madera']}_slab[type=bottom,waterlogged=false]")
            else:
                e.s(x, y, za, f"{p['madera']}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
                e.s(x, y, zb, f"{p['madera']}_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
        for x in (x0, x1):
            for z in range(max(za + 1, z0), min(zb - 1, z1) + 1):
                e.s(x, y, z, p["tablas"])
        for x in range(x0 + 1, x1):
            for z in range(max(za + 1, z0), min(zb - 1, z1) + 1):
                e.s(x, y, z, "air")
        za, zb, y = za + 1, zb - 1, y + 1


def fundicion(e, x0, z0, tabla):
    """Fundición pequeña: banco de ladrillo con el alto horno y el horno, chimenea con su fogata humeante, yunque, un
    caldero y el tonel con lo fundido."""
    o = e.o
    for x in (x0, x0 + 1):
        for z in range(z0, z0 + 4):
            for y in (1, 2):
                e.s(x, y, z, "bricks")
    e.s(x0 + 1, 1, z0 + 1, "blast_furnace[facing=east,lit=false]")
    e.s(x0 + 1, 1, z0 + 2, "furnace[facing=east,lit=false]")
    for y in range(3, 6):
        e.s(x0, y, z0 + 1, "bricks")
    e.s(x0, 6, z0 + 1, "campfire[facing=east,lit=true,signal_fire=false,waterlogged=false]")
    e.s(x0 + 3, 1, z0, "anvil[facing=north]")
    e.s(x0 + 3, 1, z0 + 3, "cauldron")
    piezas.chest(e.s, x0 + 2, 1, z0 + 3, "up", f"heraldia:minas/{tabla}", kind="barrel")
    o.cofres.append(((e.x(x0 + 2), 1, z0 + 3), tabla))


def cartel(o, x, z, tam):
    """Cartel de la mina en la fachada (pegado al muro de la boca, mirando al patio)."""
    piezas.sign(o.s, x, 2, z, "north", [piezas.text(f"heraldia.minas.cartel.{tam}.{i}", fb)
                                       for i, fb in ((1, CARTELES[tam][0][0]), (2, CARTELES[tam][1][0]))], wood=o.p["madera"])


CARTELES = {"pequena": (("Boca de mina", "Mine adit"), ("Ojo con el grisú", "Mind the firedamp")),
            "mediana": (("Campamento minero", "Mining camp"), ("Solo personal", "Staff only")),
            "grande": (("Minas reales", "Royal mines"), ("Pozo y galerías", "Shaft and galleries"))}


def torre(e, cx, cz, alto=14):
    """Torre de extracción de tronco sobre el pozo (5 x 5 con el eje en cx, cz): cuatro patas, dos anillos de vigas,
    el marco de arriba, la viga del eje y la polea (una rueda vertical de tronco con sus radios de valla) y la cadena
    que baja por el pozo."""
    o, p = e.o, e.o.p
    xs, zs = (cx - 2, cx + 2), (cz - 2, cz + 2)
    for x in xs:
        for z in zs:
            for y in range(1, alto + 1):
                e.s(x, y, z, o.tronco("y"))
    for y in (6, 11, alto + 1):
        for x in range(cx - 2, cx + 3):
            for z in zs:
                e.s(x, y, z, o.tronco("x"))
        for z in range(cz - 1, cz + 2):
            for x in xs:
                e.s(x, y, z, o.tronco("z"))
    for x in range(cx - 1, cx + 2):
        e.s(x, alto + 1, cz, o.tronco("x"))
    hub = alto + 4
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            r2 = dx * dx + dy * dy
            if 4 <= r2 <= 6:
                e.s(cx + dx, hub + dy, cz, o.tronco("z"))
            elif r2 in (1, 2) and (dx == 0 or dy == 0):
                e.s(cx + dx, hub + dy, cz, f"{p['madera']}_fence")
    e.s(cx, hub, cz, o.tronco("z"))
    for y in range(hub - 3 + 1, alto + 1):      # apoyo de la rueda sobre la viga del eje
        e.s(cx, y, cz, o.tronco("y"))
    for y in range(2, alto + 1):
        e.s(cx + 1, y, cz, "iron_chain[axis=y,waterlogged=false]")
