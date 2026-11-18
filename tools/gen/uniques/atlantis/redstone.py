"""Mecanismos de redstone de la Atlántida (siempre en seco: el agua arranca el polvo y las antorchas)."""
from . import buildings as E

SOLID = "prismarine_bricks"


def combination(v, u0, y, vm, pattern, name, solid=SOLID):
    """Puerta de combinación. Palancas en la cara norte del muro v = vm, a la altura y (los pies van en y - 1).

    patron = lista de 4 booleanos (True = la palanca debe quedar accionada). Tras el muro hay una cavidad sellada:
    cada palanca que debe estar accionada lleva detrás una antorcha (encendida mientras la palanca está suelta) y cada
    una que debe quedar suelta, polvo; todo vierte a una línea común que es «algo está mal». Una antorcha inversora al
    final se enciende solo si nada está mal y abre la puerta de hierro, retranqueada un bloque tras el hueco del muro
    en u0 + 9. Estados iniciales coherentes con todas las palancas sueltas (en la generación no hay actualizaciones).
    Ocupa u0 - 1 .. u0 + 10, v = vm .. vm + 3, y - 2 .. y + 2. Devuelve la celda (u, y - 1, v) tras la puerta.
    """
    assert len(pattern) == 4 and any(pattern)
    v.fill(u0 - 1, y - 2, vm, u0 + 10, y + 2, vm + 3, solid)
    for i, required in enumerate(pattern):
        u = u0 + 2 * i
        v.set(u, y, vm - 1, "lever[face=wall,facing=north,powered=false]")
        if required:
            v.set(u, y, vm + 1, "redstone_wall_torch[facing=south,lit=true]")
        else:
            v.set(u, y, vm + 1, "redstone_wire[north=side,south=side,east=none,west=none,power=0]")
    for u in range(u0, u0 + 8):
        branch = (u - u0) % 2 == 0
        v.set(u, y, vm + 2, f"redstone_wire[east=side,west={'none' if u == u0 else 'side'},north={'side' if branch else 'none'},south=none,power=0]")
    v.set(u0 + 8, y, vm + 1, "redstone_wall_torch[facing=north,lit=false]")       # inversora, sobre el bloque (u0 + 8, y, vm + 2)
    pu = u0 + 9
    v.air(pu, y - 1, vm, pu, y, vm)                                               # hueco en el muro
    v.set(pu, y - 1, vm + 1, "iron_door[facing=north,half=lower,hinge=left,open=false,powered=false]")
    v.set(pu, y, vm + 1, "iron_door[facing=north,half=upper,hinge=left,open=false,powered=false]")
    v.air(pu, y - 1, vm + 2, pu, y, vm + 3)                                       # paso tras la puerta
    v.mark("puerta_" + name, pu, y, vm + 1)
    for i in range(4):
        v.mark("palanca_" + name, u0 + 2 * i, y, vm - 1)
    for u in range(u0, u0 + 9):                                                   # bloques macizos sobre cada componente:
        for w in (vm + 1, vm + 2):                                                # la prueba de humo los «toca» para propagar
            v.mark("toque_" + name, u, y + 1, w)                               # como lo haría un jugador al accionar
    return pu, y - 1, vm + 3


def arrow_trap(v, u, y, w, side):
    """Placa de presión junto a un dispensador de flechas empotrado en el muro (lado = 'east' u 'west' del pasillo)."""
    du = 1 if side == "east" else -1
    from . import things as C
    C.dispenser(v, u + du, y, w, "west" if side == "east" else "east", "arrow", 24)
    v.set(u, y, w, "stone_pressure_plate[powered=false]")
    v.mark("trampa", u, y, w)


def water_trap(v, u, y, w, side):
    """Como la de flechas, pero el dispensador vierte un cubo de agua: el pasillo se encharca."""
    du = 1 if side == "east" else -1
    from . import things as C
    C.dispenser(v, u + du, y, w, "west" if side == "east" else "east", "water_bucket", 1)
    v.set(u, y, w, "stone_pressure_plate[powered=false]")
    v.mark("trampa", u, y, w)


def bomb_chest(v, u, y, w, facing, tbl):
    """Cofre trampa sobre TNT: abrirlo la enciende."""
    from . import things as C
    v.set(u, y - 1, w, "tnt[unstable=false]")
    C.place_chest(v, u, y, w, facing, tbl, kind="trapped_chest")
    v.mark("trampa", u, y, w)
