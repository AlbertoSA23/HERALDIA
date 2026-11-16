"""Piezas propias de las estructuras medianas (lo de las únicas, en unicas/_comun: cofres, carteles, puertas...).

Todas trabajan sobre un core.Template con y = 0 a ras de suelo y la entrada en la cara norte (z = 0)."""
from core import B, F, NS, anclado
from unicas._comun import piezas

STAIR_FACING = {"north", "south", "east", "west"}


def put(t):
    """Adaptador para las piezas comunes (piezas.chest, piezas.sign, piezas.door...): put(x, y, z, estado, nbt)."""
    return lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt)


def patio(t, x0, z0, x1, z1, suelo, aire=2, borde=None, dentro=None):
    """Suelo del recinto en y = 0 (sin tierra fértil: no nacen árboles dentro) y aire explícito encima (lo que hubiera
    en el terreno, hierba o nieve, no asoma). `suelo` es un estado o una función (x, z) -> estado; `borde` el del
    anillo exterior, si se quiere distinto; `dentro` (x, z) -> bool da otra forma (un claro redondo): fuera se queda el
    terreno natural."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if dentro and not dentro(x, z):
                continue
            edge = x in (x0, x1) or z in (z0, z1)
            st = borde if edge and borde else suelo(x, z) if callable(suelo) else suelo
            t.set(x, 0, z, st)
            for y in range(1, aire + 1):
                t.set(x, y, z, "air", keep=True)


def entrada(t, x, peldano):
    """Entrada de la mediana en (x, 0, 0): el jigsaw heraldia:entrance (que la auditoría usa para el recorrido a pie y
    que al generarse se convierte en `peldano`, el escalón desde el terreno) en la cara norte de la caja."""
    t.jigsaw(x, 0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state=peldano)


def caja(t, x0, y0, z0, x1, y1, z1, muro, esquina=None, suelo=None, aire=True):
    """Muros de x0..x1 por z0..z1 desde y0 hasta y1 (incluidos), con esquinas de `esquina`, suelo en y0 - 1 y aire
    explícito dentro."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                borde = x in (x0, x1) or z in (z0, z1)
                if borde:
                    corner = x in (x0, x1) and z in (z0, z1)
                    t.set(x, y, z, esquina if corner and esquina else muro)
                elif aire:
                    t.set(x, y, z, "air")
    if suelo:
        t.fill(x0, y0 - 1, z0, x1, y0 - 1, z1, suelo)


def tejado(t, x0, z0, x1, z1, y, escalera, cumbrera, hastial, vuelo=1):
    """Tejado a dos aguas con la cumbrera a lo largo de x sobre los muros x0..x1, z0..z1 (cuya última fila es y - 1):
    hiladas de escalones desde el alero (vuelo bloques fuera de los muros, a la altura y) hasta la cumbrera, y los
    hastiales (las caras de x0 y x1) rellenos de `hastial`. Devuelve la altura de la cumbrera."""
    xs = range(x0 - vuelo, x1 + vuelo + 1)
    za, zb, yy = z0 - vuelo, z1 + vuelo, y
    while True:
        if za == zb:                     # anchura impar: una fila de cumbrera
            for x in xs:
                t.set(x, yy, za, cumbrera)
            return yy
        for x in xs:
            t.set(x, yy, za, f"{escalera}[facing=south,half=bottom,shape=straight,waterlogged=false]")
            t.set(x, yy, zb, f"{escalera}[facing=north,half=bottom,shape=straight,waterlogged=false]")
        for x in (x0, x1):
            for z in range(max(za + 1, z0), min(zb - 1, z1) + 1):
                t.set(x, yy, z, hastial)
        if za + 1 == zb:                 # anchura par: las dos aguas se juntan y la cumbrera va encima
            for x in xs:
                t.set(x, yy + 1, za, cumbrera)
                t.set(x, yy + 1, zb, cumbrera)
            return yy + 1
        za, zb, yy = za + 1, zb - 1, yy + 1


def door(t, x, y, z, facing, kind):
    piezas.door(put(t), x, y, z, facing, kind)


def ventana(t, x, y, z, cristal="glass_pane"):
    t.set(x, y, z, cristal)


def farol(t, x, y, z, colgado=True):
    """Farol colgado del techo (Registry.add le pone cadena hasta el techo si hace falta) o de pie."""
    t.set(x, y, z, f"lantern[hanging={'true' if colgado else 'false'},waterlogged=false]")


def mesa(t, x, z, madera, sillas=("east", "west")):
    """Mesa (poste de valla y placa) con sillas de escalón a los lados, con el respaldo hacia fuera."""
    t.set(x, 1, z, f"{madera}_fence")
    t.set(x, 2, z, f"{madera}_pressure_plate[powered=false]")
    for lado in sillas:
        dx, dz = piezas.DIRV[lado]
        t.set(x + dx, 1, z + dz, f"{madera}_stairs[facing={lado},half=bottom,shape=straight,waterlogged=false]")


def cama(t, x, z, facing, color="white", y=1):
    """Cama con la cabecera en (x, y, z) hacia `facing` y los pies detrás."""
    dx, dz = piezas.DIRV[facing]
    t.set(x, y, z, f"{color}_bed[facing={facing},occupied=false,part=head]")
    t.set(x - dx, y, z - dz, f"{color}_bed[facing={facing},occupied=false,part=foot]")


def escalera_mano(t, x, z, y0, y1, facing):
    for y in range(y0, y1 + 1):
        t.set(x, y, z, f"ladder[facing={facing},waterlogged=false]")


def texto(mid, clave, fallback):
    return piezas.text(f"{NS}.medianas.{mid}.{clave}", fallback)


def mob(tipo, mid, clave=None, fallback=None, rot=0.0, **extra):
    """NBT de un mob de una mediana: persistente (si no, desaparece antes de que llegue nadie), anclado en su sitio
    hasta que lo atacan y sin recoger objetos (core.anclado) y, con `clave`, con nombre traducible."""
    n = {"id": f"minecraft:{tipo}", "PersistenceRequired": B(1), "Rotation": [F(rot), F(0.0)]}
    if clave:
        n["CustomName"] = texto(mid, clave, fallback)
    n.update(extra)
    return anclado(n, siempre=True)


def oferta(buy, sell, usos, buy_b=None):
    """Trato fijo de un aldeano de plantilla (el mismo formato que el alguacil del tablón)."""
    from tablon import _oferta
    return _oferta(buy, sell, usos, buy_b)


def aldeano(mid, clave, fallback, profesion, tipo, ofertas, rot=0.0):
    """Aldeano quieto con tratos fijos (como el alguacil del tablón): sin IA, invulnerable, con nombre."""
    return {"id": "minecraft:villager", "PersistenceRequired": B(1), "NoAI": B(1), "Invulnerable": B(1),
            "CustomName": texto(mid, clave, fallback), "CustomNameVisible": B(1),
            "VillagerData": {"profession": f"minecraft:{profesion}", "level": 2, "type": f"minecraft:{tipo}"},
            "Xp": 10, "Rotation": [F(rot), F(0.0)], "Offers": {"Recipes": ofertas}}


def cofre(t, x, y, z, facing, mid, tabla, kind="chest"):
    piezas.chest(put(t), x, y, z, facing, f"{NS}:medianas/{mid}/{tabla}", kind=kind)
