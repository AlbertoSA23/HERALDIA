"""Piezas de las únicas del Nether y el End (T44: Ciudadela de Ceniza y Sagrario del Vacío): el torreón con la trampa
de la entrada, el salón del guardián, la cámara del tesoro tras una puerta de hierro con botones y la planta alta con la
biblioteca; las torres (o capillas) de las esquinas y la sala oculta tras una puerta de pistones con palanca. Cada
única pone lo de fuera (murallas y patio, o la plataforma y sus pilares) y su paleta. No es una única (empieza por «_»:
unicas.modules() no la descubre).

Coordenadas de plantilla: y = 0 es el suelo; todo en x, z >= 0 (Registry.add no desplaza nada, así que las posiciones
de la puerta abierta, lint_open, siguen valiendo)."""
from uniques._common import pieces

SIDE = 15          # torreón de 15 x 15
HEIGHT = 11          # remate de las almenas del torreón (suelo en 0, forjado en 5, cubierta en 10)


def _put(t):
    return lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt)


def box(t, x0, y0, z0, x1, y1, z1, wall, corner_block=None):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge_block = x in (x0, x1) or z in (z0, z1)
                if edge_block:
                    t.set(x, y, z, corner_block if corner_block and x in (x0, x1) and z in (z0, z1) else wall)
                else:
                    t.set(x, y, z, "air")


def battlements(t, x0, z0, x1, z1, y, merlon):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if (x in (x0, x1) or z in (z0, z1)) and (x + z) % 2 == 0:
                t.set(x, y, z, merlon)


def lantern(t, x, y, z, hanging=True):
    t.set(x, y, z, f"soul_lantern[hanging={'true' if hanging else 'false'},waterlogged=false]")


def great_tower(t, p, kx, kz, cofre, guardian):
    """Torreón de 15 x 15 con su NO en (kx, kz): portada al norte (3 de ancho), pasillo con la trampa de placa y
    flechas, salón del guardián, tabique con la puerta de hierro (botones a los dos lados) y la cámara del tesoro con el
    cofre premium al sur; escalera de mano a la planta alta (biblioteca y cuartel). `cofre(t, x, y, z, facing, tabla,
    kind)` pone un contenedor de la única; `guardian` es el NBT de su guardián."""
    put = _put(t)
    x1, z1 = kx + SIDE - 1, kz + SIDE - 1
    cx = kx + 7
    t.fill(kx, 0, kz, x1, 0, z1, p["piso"])
    box(t, kx, 1, kz, x1, 9, z1, p["muro"], p["esquina"])
    t.fill(kx + 1, 5, kz + 1, x1 - 1, 5, z1 - 1, p["forjado"])
    t.fill(kx, 10, kz, x1, 10, z1, p["forjado"])
    battlements(t, kx, kz, x1, z1, HEIGHT, p["almena"])
    for x in (kx, x1):
        for z in (kz, z1):
            lantern(t, x, HEIGHT + 1, z, hanging=False) if (x + z) % 2 == 0 else None
    # portada
    for x in range(cx - 1, cx + 2):
        for y in (1, 2, 3):
            t.set(x, y, kz, "air")
    # pasillo con la trampa (dispensadores a los lados de la placa) y las salas de guardia a los lados
    for z in range(kz + 1, kz + 5):
        for y in range(1, 5):
            t.set(cx - 2, y, z, p["muro"])
            t.set(cx + 2, y, z, p["muro"])
    pieces.plate_trap(put, [(cx, 1, kz + 3)], "east", plate="polished_blackstone_pressure_plate")
    for x in range(kx + 1, x1):
        if not cx - 1 <= x <= cx + 1:
            for y in range(1, 5):
                t.set(x, y, kz + 5, p["muro"])
    for x in (kx + 3, x1 - 3):
        pieces.door(put, x, 1, kz + 5, "north", p["puerta"])
    cofre(t, kx + 1, 1, kz + 1, "south", "cuartel", "barrel")
    cofre(t, x1 - 1, 1, kz + 1, "south", "cuartel", "chest")
    lantern(t, kx + 3, 4, kz + 2)
    lantern(t, x1 - 3, 4, kz + 2)
    # salón del guardián
    t.entity(cx, 1, kz + 8, guardian)
    for x in (kx + 3, x1 - 3):
        t.set(x, 1, kz + 8, p["columna"])
        for y in (2, 3, 4):
            t.set(x, y, kz + 8, p["columna"])
        lantern(t, x, 4, kz + 7)
    # tabique, puerta de hierro con botones y cámara del tesoro
    for x in range(kx + 1, x1):
        for y in range(1, 5):
            t.set(x, y, kz + 11, p["muro"])
    pieces.door(put, cx, 1, kz + 11, "south", "iron_door")
    t.set(cx - 1, 2, kz + 10, "stone_button[face=wall,facing=north,powered=false]")
    t.set(cx - 1, 2, kz + 12, "stone_button[face=wall,facing=south,powered=false]")
    cofre(t, cx, 1, z1 - 1, "north", "premium", "chest")
    for x in (cx - 2, cx + 2):
        t.set(x, 1, z1 - 1, p["tesoro"])
    lantern(t, cx, 4, kz + 12)
    # escalera de mano a la planta alta, pegada al muro oeste del salón
    for y in range(1, 6):
        t.set(kx + 1, y, kz + 8, "ladder[facing=east,waterlogged=false]")
    # planta alta: biblioteca al sur (estanterías y el cofre), cuartel al norte; saeteras
    for x in range(kx + 1, x1):
        if x not in (cx,):
            t.set(x, 6, z1 - 1, "bookshelf")
            t.set(x, 7, z1 - 1, "bookshelf")
    cofre(t, cx, 6, z1 - 1, "north", "biblioteca", "chest")
    t.set(x1 - 1, 6, kz + 8, "lectern[facing=west,has_book=false,powered=false]")
    cofre(t, x1 - 1, 6, kz + 1, "south", "cuartel", "barrel")
    for x in range(kx + 3, x1 - 2, 4):
        lantern(t, x, 9, kz + 4)
        lantern(t, x, 9, z1 - 4)
    for z in range(kz + 3, z1 - 1, 4):
        t.set(kx, 7, z, "iron_bars")
        t.set(x1, 7, z, "iron_bars")
    return {"centro": (cx, kz + 8)}


def tower(t, p, x0, z0, height, door, merlon=True):
    """Torre (o capilla) de 5 x 5 con su NO en (x0, z0): muros hasta `alto`, cubierta y almenas; `puerta` (x, z,
    facing) en uno de sus muros; saeteras de barrotes."""
    put = _put(t)
    x1, z1 = x0 + 4, z0 + 4
    t.fill(x0, 0, z0, x1, 0, z1, p["piso"])
    box(t, x0, 1, z0, x1, height, z1, p["muro"], p["esquina"])
    t.fill(x0, height + 1, z0, x1, height + 1, z1, p["forjado"])
    if merlon:
        battlements(t, x0, z0, x1, z1, height + 2, p["almena"])
    for x, z in ((x0 + 2, z0), (x0 + 2, z1), (x0, z0 + 2), (x1, z0 + 2)):
        if (x, z) != (door[0], door[1]):
            t.set(x, 3, z, "iron_bars")
    lantern(t, x0 + 2, height, z0 + 2)
    if door[2]:
        pieces.door(put, door[0], 1, door[1], door[2], p["puerta"])


def hidden(t, p, x0, z0):
    """Torre de 5 x 5 (NO en (x0, z0)) sin puerta a la vista: se entra por su muro oeste con una puerta de pistones que
    abre la palanca del contrafuerte de fuera (piezas.lever_door). Devuelve el estado con la puerta abierta."""
    tower(t, p, x0, z0, 7, (x0, z0 + 2, None))
    # contrafuerte al norte de la esquina NO (por fuera), donde va la antorcha y la palanca
    for y in (1, 2, 3):
        t.set(x0, y, z0 - 1, p["muro"])
        t.set(x0 - 1, y, z0 - 1, p["muro"])
    rec = pieces.lever_door(_put(t), (x0, 1, z0 + 2), "north", "west", p["muro"], p["muro"])
    return rec["opened"]
