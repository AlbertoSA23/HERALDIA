"""Trazado procedimental de la Atlántida: el mismo que coloca BasePiece.java (cambia los dos a la vez).

Coordenadas del plano: x, z relativas al centro de la ciudad; y absoluta.
"""
import math

RADIUS, FLOOR, BASE, ROOF = 372, 31, 24, 62          # muralla exterior, pavimento, fondo del zócalo, agua despejada hasta
WALL, WALL_HEIGHT, PUERTA, DOOR_HEIGHT, AVENUE, ROUND = 4, 13, 4, 8, 6, 10
SIDE = 384                                            # la ciudad ocupa [-384, 384) en x y z: 3 x 3 distritos de 256
TILE = 32                                           # las plantillas son teselas de 32 x 32 alineadas con los distritos


def _i32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def dispersion(x, z, salt):
    """Idéntica a BasePiece.hash (aritmética de 32 bits de Java)."""
    h = _i32(x * 374761393 + z * 668265263 + salt * 1013904223)
    h = _i32((h ^ ((h & 0xFFFFFFFF) >> 13)) * 1274126177)
    return (h ^ ((h & 0xFFFFFFFF) >> 16)) & 0x7FFFFFFF


def wall_height(x, z):
    sector = math.floor(math.atan2(z, x) * 24 / math.pi)
    if dispersion(sector, 7, 1) % 100 < 18:
        return 3 + dispersion(x >> 1, z >> 1, 2) % 5
    return WALL_HEIGHT


def pavement(x, z, r):
    ax, az = abs(x), abs(z)
    if ax <= AVENUE or az <= AVENUE:
        # Java: z % 8 == 0 con resto con signo; múltiplos de 8 en ambos lenguajes
        if (ax == 0 and z % 8 == 0) or (az == 0 and x % 8 == 0):
            return "minecraft:sea_lantern"
        return "minecraft:prismarine_bricks" if ax == AVENUE or az == AVENUE else "minecraft:dark_prismarine"
    if r > RADIUS - WALL - ROUND:
        return "minecraft:prismarine_bricks"
    roll = dispersion(x, z, 4) % 100
    return "minecraft:gravel" if roll < 8 else "minecraft:prismarine_bricks" if roll < 30 else "minecraft:prismarine"


def base(x, y, z):
    """Estado que deja la pieza base en una celda del plano, o None fuera de la ciudad (terreno natural, desconocido)."""
    d2 = x * x + z * z
    if d2 > RADIUS * RADIUS or y > ROOF:
        return None
    r = math.sqrt(d2)
    if y > FLOOR:
        wall = r > RADIUS - WALL
        if wall:
            door = abs(x) <= PUERTA or abs(z) <= PUERTA
            height = FLOOR + (WALL_HEIGHT if door else wall_height(x, z))
            if not door and height == FLOOR + WALL_HEIGHT and r > RADIUS - 1.5 and dispersion(x, z, 3) & 1 == 0:
                height += 1
            if y <= height and not (door and y <= FLOOR + DOOR_HEIGHT):
                return "minecraft:dark_prismarine" if y == height or (y - FLOOR) % 5 == 0 else "minecraft:prismarine_bricks"
        return "minecraft:water"
    if y == FLOOR:
        return pavement(x, z, r)
    return "minecraft:prismarine_bricks" if y >= BASE and r > RADIUS - WALL - 2 else "minecraft:stone"
