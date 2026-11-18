"""Piezas propias de las estructuras medianas (lo de las únicas, en unicas/_comun: cofres, carteles, puertas...).

Todas trabajan sobre un core.Template con y = 0 a ras de suelo y la entrada en la cara norte (z = 0)."""
from core import B, F, NS, anchored
from uniques._common import pieces

STAIR_FACING = {"north", "south", "east", "west"}


def put(t):
    """Adaptador para las piezas comunes (piezas.chest, piezas.sign, piezas.door...): put(x, y, z, estado, nbt)."""
    return lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt)


def courtyard(t, x0, z0, x1, z1, floor, air_block=2, edge_block=None, inside=None):
    """Suelo del recinto en y = 0 (sin tierra fértil: no nacen árboles dentro) y aire explícito encima (lo que hubiera
    en el terreno, hierba o nieve, no asoma). `suelo` es un estado o una función (x, z) -> estado; `borde` el del
    anillo exterior, si se quiere distinto; `dentro` (x, z) -> bool da otra forma (un claro redondo): fuera se queda el
    terreno natural."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if inside and not inside(x, z):
                continue
            edge = x in (x0, x1) or z in (z0, z1)
            st = edge_block if edge and edge_block else floor(x, z) if callable(floor) else floor
            t.set(x, 0, z, st)
            for y in range(1, air_block + 1):
                t.set(x, y, z, "air", keep=True)


def entrance(t, x, stair_step):
    """Entrada de la mediana en (x, 0, 0): el jigsaw heraldia:entrance (que la auditoría usa para el recorrido a pie y
    que al generarse se convierte en `peldano`, el escalón desde el terreno) en la cara norte de la caja."""
    t.jigsaw(x, 0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state=stair_step)


def box(t, x0, y0, z0, x1, y1, z1, wall, corner_block=None, floor=None, air_block=True):
    """Muros de x0..x1 por z0..z1 desde y0 hasta y1 (incluidos), con esquinas de `esquina`, suelo en y0 - 1 y aire
    explícito dentro."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge_block = x in (x0, x1) or z in (z0, z1)
                if edge_block:
                    corner = x in (x0, x1) and z in (z0, z1)
                    t.set(x, y, z, corner_block if corner and corner_block else wall)
                elif air_block:
                    t.set(x, y, z, "air")
    if floor:
        t.fill(x0, y0 - 1, z0, x1, y0 - 1, z1, floor)


def roof_tiles(t, x0, z0, x1, z1, y, stairs, ridge, gable_end, overhang=1):
    """Tejado a dos aguas con la cumbrera a lo largo de x sobre los muros x0..x1, z0..z1 (cuya última fila es y - 1):
    hiladas de escalones desde el alero (vuelo bloques fuera de los muros, a la altura y) hasta la cumbrera, y los
    hastiales (las caras de x0 y x1) rellenos de `hastial`. Devuelve la altura de la cumbrera."""
    xs = range(x0 - overhang, x1 + overhang + 1)
    za, zb, yy = z0 - overhang, z1 + overhang, y
    while True:
        if za == zb:                     # anchura impar: una fila de cumbrera
            for x in xs:
                t.set(x, yy, za, ridge)
            return yy
        for x in xs:
            t.set(x, yy, za, f"{stairs}[facing=south,half=bottom,shape=straight,waterlogged=false]")
            t.set(x, yy, zb, f"{stairs}[facing=north,half=bottom,shape=straight,waterlogged=false]")
        for x in (x0, x1):
            for z in range(max(za + 1, z0), min(zb - 1, z1) + 1):
                t.set(x, yy, z, gable_end)
        if za + 1 == zb:                 # anchura par: las dos aguas se juntan y la cumbrera va encima
            for x in xs:
                t.set(x, yy + 1, za, ridge)
                t.set(x, yy + 1, zb, ridge)
            return yy + 1
        za, zb, yy = za + 1, zb - 1, yy + 1


def door(t, x, y, z, facing, kind):
    pieces.door(put(t), x, y, z, facing, kind)


def window(t, x, y, z, glass="glass_pane"):
    t.set(x, y, z, glass)


def lantern(t, x, y, z, hanging=True):
    """Farol colgado del techo (Registry.add le pone cadena hasta el techo si hace falta) o de pie."""
    t.set(x, y, z, f"lantern[hanging={'true' if hanging else 'false'},waterlogged=false]")


def table_top(t, x, z, wood, chairs=("east", "west")):
    """Mesa (poste de valla y placa) con sillas de escalón a los lados, con el respaldo hacia fuera."""
    t.set(x, 1, z, f"{wood}_fence")
    t.set(x, 2, z, f"{wood}_pressure_plate[powered=false]")
    for side in chairs:
        dx, dz = pieces.DIRV[side]
        t.set(x + dx, 1, z + dz, f"{wood}_stairs[facing={side},half=bottom,shape=straight,waterlogged=false]")


def bed(t, x, z, facing, color="white", y=1):
    """Cama con la cabecera en (x, y, z) hacia `facing` y los pies detrás."""
    dx, dz = pieces.DIRV[facing]
    t.set(x, y, z, f"{color}_bed[facing={facing},occupied=false,part=head]")
    t.set(x - dx, y, z - dz, f"{color}_bed[facing={facing},occupied=false,part=foot]")


def ladder(t, x, z, y0, y1, facing):
    for y in range(y0, y1 + 1):
        t.set(x, y, z, f"ladder[facing={facing},waterlogged=false]")


def text(mid, key, fallback):
    return pieces.text(f"{NS}.medianas.{mid}.{key}", fallback)


def mob(kind, mid, key=None, fallback=None, rot=0.0, **extra):
    """NBT de un mob de una mediana: persistente (si no, desaparece antes de que llegue nadie), anclado en su sitio
    hasta que lo atacan y sin recoger objetos (core.anclado) y, con `clave`, con nombre traducible."""
    n = {"id": f"minecraft:{kind}", "PersistenceRequired": B(1), "Rotation": [F(rot), F(0.0)]}
    if key:
        n["CustomName"] = text(mid, key, fallback)
    n.update(extra)
    return anchored(n, always=True)


def offer(buy, sell, uses, buy_b=None):
    """Trato fijo de un aldeano de plantilla (el mismo formato que el alguacil del tablón)."""
    from board import _offer
    return _offer(buy, sell, uses, buy_b)


def villager(mid, key, fallback, profession, kind, offers, rot=0.0):
    """Aldeano quieto con tratos fijos (como el alguacil del tablón): sin IA, invulnerable, con nombre."""
    return {"id": "minecraft:villager", "PersistenceRequired": B(1), "NoAI": B(1), "Invulnerable": B(1),
            "CustomName": text(mid, key, fallback), "CustomNameVisible": B(1),
            "VillagerData": {"profession": f"minecraft:{profession}", "level": 2, "type": f"minecraft:{kind}"},
            "Xp": 10, "Rotation": [F(rot), F(0.0)], "Offers": {"Recipes": offers}}


def cofre(t, x, y, z, facing, mid, tbl, kind="chest"):
    pieces.chest(put(t), x, y, z, facing, f"{NS}:medianas/{mid}/{tbl}", kind=kind)
