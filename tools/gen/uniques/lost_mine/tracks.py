"""Vías del cargadero de la Mina perdida: el puzle de las agujas (diseño en docs/unicas/mina_perdida.md).

Una vagoneta espera en la rampa de salida (un raíl propulsor apagado contra el muro: con la palanca de arranque sale
disparada hacia el oeste). La vía pasa por dos agujas (cruces en T) con su palanca; según cómo estén, la vagoneta acaba
en la escombrera, en la vía muerta de la fundición o, por una rendija de 1 x 1 del muro norte (por la que no cabe una
persona), en la báscula: un raíl detector cuyo bloque de apoyo apaga la antorcha inversora que sostiene la compuerta del
filón madre (dos pistones pegajosos extendidos, como `piezas.lever_door`). Solo «aguja 1 al norte, aguja 2 al este»
llega a la báscula; la pista está en el despacho oculto del capataz.

Regla de las agujas (26.3, `RailState.place`, leída en el bytecode): un raíl normal con tres vecinos que pueden unirse a
él (cruce en T) toma la curva según la señal: sin señal gana la última de NO, NE, SO, SE que tenga sus dos vecinos; con
señal, la última de SE, SO, NE, NO. Una T norte-sur con rama al este queda SE sin señal y NE con ella; una T este-oeste
con rama al sur, SE sin señal y SO con ella. `forma_aguja` lo calcula y `recorrer` sigue a la vagoneta.
"""
from core import parse_state

DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
# forma -> {lado: dy} (dy = 1 si por ese lado la vía sube un bloque)
SHAPES = {"north_south": {"north": 0, "south": 0}, "east_west": {"east": 0, "west": 0},
          "ascending_east": {"west": 0, "east": 1}, "ascending_west": {"east": 0, "west": 1},
          "ascending_north": {"south": 0, "north": 1}, "ascending_south": {"north": 0, "south": 1},
          "south_east": {"south": 0, "east": 0}, "south_west": {"south": 0, "west": 0},
          "north_west": {"north": 0, "west": 0}, "north_east": {"north": 0, "east": 0}}
RAILS = ("rail", "powered_rail", "detector_rail", "activator_rail")
Y = 1                                    # pies del cargadero

# trazado (x, z) del cargadero; las agujas y las palancas
OUTPUT, CAP = (100, 36), (101, 36)      # rampa de salida (propulsor contra el muro este)
START = (100, 35)                     # palanca de suelo junto a la salida
SWITCH1, LEVER1 = (89, 36), (88, 36)    # T norte-sur con rama al este (por donde llega la vagoneta)
SWITCH2, LEVER2 = (89, 30), (89, 29)    # T este-oeste con rama al sur (por donde llega)
SPOIL_HEAP, SMELTER = (89, 44), (83, 30)
PUERTA = (92, 24)                        # compuerta del filón madre (bloque inferior a y = 1), en el muro norte
SEESAW = (96, 2, 24)                    # raíl detector, dentro del muro
SOLUTION = (True, False)                 # aguja 1 con señal (norte), aguja 2 sin señal (este)


def spire_shape(neighbors, with_signal):
    """Forma que el juego da a un raíl con esos vecinos ({'north', ...}) y esa señal (RailState.place)."""
    n, s, w, e = ("north" in neighbors, "south" in neighbors, "west" in neighbors, "east" in neighbors)
    form = None
    if (n or s) and not w and not e:
        form = "north_south"
    if (w or e) and not n and not s:
        form = "east_west"
    se, sw, ne, nw = s and e, s and w, n and e, n and w
    if se and not n and not w:
        form = "south_east"
    if sw and not n and not e:
        form = "south_west"
    if nw and not s and not e:
        form = "north_west"
    if ne and not s and not w:
        form = "north_east"
    if form is None:
        order = ((se, "south_east"), (sw, "south_west"), (ne, "north_east"), (nw, "north_west")) if with_signal else \
                ((nw, "north_west"), (ne, "north_east"), (sw, "south_west"), (se, "south_east"))
        for ok, f in order:
            if ok:
                form = f
    return form


def is_rail(st):
    return st is not None and parse_state(st)[0].replace("minecraft:", "") in RAILS


def form(st):
    return parse_state(st)[1]["shape"]


def traverse(get, start, direction, switches=None, steps=200):
    """Sigue a una vagoneta desde `inicio` (x, y, z) moviéndose hacia `sentido`. `agujas` {pos: forma} sustituye la
    forma de las agujas. Devuelve (última posición, camino) o lanza ValueError si descarrila."""
    switches = switches or {}
    p, d, road = start, direction, [start]
    for _ in range(steps):
        st = get(*p)
        f = switches.get(p) or form(st)
        sides = SHAPES[f]
        entrance = OPP[d]
        if p != start and entrance not in sides:
            raise ValueError(f"la vagoneta descarrila en {p} (forma {f}, entra por {entrance})")
        output = [l for l in sides if l != entrance][0] if p != start else d
        dx, dz = DV[output]
        next_unique = None
        for dy in (sides.get(output, 0), 0, -1):
            q = (p[0] + dx, p[1] + dy, p[2] + dz)
            if is_rail(get(*q)):
                next_unique = q
                break
        if next_unique is None:
            return p, road
        p, d = next_unique, output
        road.append(p)
    raise ValueError("la vagoneta no se para")


def trace(o):
    """Pone las vías, las palancas, los carteles, la vagoneta y la compuerta en la obra `o`; devuelve los mecanismos."""
    s, y = o.s, Y
    rail = o.rail
    # salida: propulsor apagado contra el muro (tope), un raíl normal de aislamiento y dos propulsores con bloque de
    # redstone debajo (siempre encendidos) para que la vagoneta vacía llegue lejos
    rail(*_p(OUTPUT), "east_west", "powered_rail", False)
    s(START[0], y, START[1], "lever[face=floor,facing=west,powered=false]")
    for x in range(SWITCH1[0] + 1, OUTPUT[0]):
        if x in (97, 98, 93):
            rail(x, y, 36, "east_west", "powered_rail", True)
            s(x, y - 1, 36, "redstone_block")
        else:
            rail(x, y, 36, "east_west")
    # aguja 1 (T norte-sur con rama al este) y su palanca de suelo al oeste
    rail(*_p(SWITCH1), spire_shape({"north", "south", "east"}, False))
    s(LEVER1[0], y, LEVER1[1], "lever[face=floor,facing=east,powered=false]")
    # ramal sur, a la escombrera
    for z in range(SWITCH1[1] + 1, SPOIL_HEAP[1] + 1):
        if z == 40:
            rail(89, y, z, "north_south", "powered_rail", True)
            s(89, y - 1, z, "redstone_block")
        else:
            rail(89, y, z, "north_south")
    s(SPOIL_HEAP[0], y, SPOIL_HEAP[1] + 1, "gravel")                    # el montón de la escombrera hace de tope
    s(SPOIL_HEAP[0] + 1, y, SPOIL_HEAP[1] + 1, "gravel")
    s(SPOIL_HEAP[0], y + 1, SPOIL_HEAP[1] + 1, "gravel")
    # ramal norte, a la aguja 2
    for z in range(SWITCH2[1] + 1, SWITCH1[1]):
        if z == 33:
            rail(89, y, z, "north_south", "powered_rail", True)
            s(89, y - 1, z, "redstone_block")
        else:
            rail(89, y, z, "north_south")
    rail(*_p(SWITCH2), spire_shape({"east", "west", "south"}, False))
    s(LEVER2[0], y, LEVER2[1], "lever[face=floor,facing=south,powered=false]")
    # vía muerta de la fundición (al oeste), con un tonel de tope
    for x in range(SMELTER[0], SWITCH2[0]):
        if x == 86:
            rail(x, y, 30, "east_west", "powered_rail", True)
            s(x, y - 1, 30, "redstone_block")
        else:
            rail(x, y, 30, "east_west")
    o.barrel(SMELTER[0] - 1, y, 30, "east")
    # a la báscula: al este, curva al norte, rampa y rendija del muro norte
    for x in range(SWITCH2[0] + 1, 96):
        if x == 92:
            rail(x, y, 30, "east_west", "powered_rail", True)
            s(x, y - 1, 30, "redstone_block")
        else:
            rail(x, y, 30, "east_west")
    rail(96, y, 30, "north_west")
    rail(96, y, 29, "north_south", "powered_rail", True)
    s(96, y - 1, 29, "redstone_block")
    rail(96, y, 28, "north_south")
    rail(96, y, 27, "ascending_north")
    s(96, y, 26, "cobblestone")                                         # apoyo de la vía alta
    rail(96, y + 1, 26, "north_south")
    rail(96, y + 1, 25, "north_south")                                  # en la rendija (muro por encima y por debajo)
    rail(*SEESAW, "north_south", "detector_rail", False)
    # la compuerta: piston_door hacia el este, antorcha inversora en el apoyo de la báscula
    px, pz = PUERTA
    from .._common import pieces
    door = [(px, y, pz), (px, y + 1, pz)]
    pieces.piston_door(s, door, (1, 0), "west", "cobblestone")
    torch = (px + 3, y, pz)
    support = (SEESAW[0], SEESAW[1] - 1, SEESAW[2])
    assert support == (torch[0] + 1, y, pz)
    s(*torch, "redstone_wall_torch[facing=west,lit=true]")
    s(torch[0], y + 1, pz, "cobblestone")                            # lo carga la antorcha: pistón de arriba
    s(*support, "cobblestone")
    for p in door:                                                     # hornacina delante de la compuerta
        o.carve(p[0], p[1], p[2] + 1, ("roca", "roca", "roca"))
    o.carved.pop((96, y, 26), None)
    o.carved.pop((96, y + 1, 26), None)
    # carteles en pilares junto a las palancas y al final de cada ramal
    for (x, z, f, pillar, key, lines) in (
            (87, 36, "east", True, "aguja1", [("Aguja 1", "Switch 1")]),
            (89, 28, "south", True, "aguja2", [("Aguja 2", "Switch 2")]),
            (100, 35, "west", False, "arranque", [("Arranque", "Start")]),        # en el muro este
            (90, 45, "west", True, "escombrera", [("Escombrera", "Spoil heap")]),
            (82, 31, "east", False, "via_muerta", [("A la fundición", "To the foundry"), ("(vía muerta)", "(dead end)")])):
        dx, dz = DV[f]
        if pillar:                                    # pilar de ladrillo de 2 de alto que sostiene el cartel
            for dy in (0, 1):
                s(x - dx, y + dy, z - dz, "stone_bricks")
                o.carved.pop((x - dx, y + dy, z - dz), None)
        o.sign(x, y + 1, z, f, key, lines)
    o.sign(px, y + 3, pz + 1, "south", "compuerta", [("Cámara del", "Lode"), ("filón: se abre", "chamber: opens"),
                                                     ("con el peso", "with the weight"), ("del mineral", "of the ore")])
    o.t.entity(OUTPUT[0], y, OUTPUT[1], {"id": "minecraft:minecart"})
    for pos in door:
        o.carved.pop(pos, None)
    return {"salida": _p(OUTPUT), "arranque": (START[0], y, START[1]), "agujas": [_p(SWITCH1), _p(SWITCH2)],
            "palancas": [(LEVER1[0], y, LEVER1[1]), (LEVER2[0], y, LEVER2[1])], "bascula": SEESAW,
            "apoyo": support, "antorcha": torch, "puerta": door,
            "pistones": [(px + 2, y, pz), (px + 2, y + 1, pz)], "solucion": SOLUTION,
            "destinos": {"escombrera": _p(SPOIL_HEAP), "fundicion": _p(SMELTER), "bascula": SEESAW}}


def _p(xz):
    return (xz[0], Y, xz[1])


def check(t, v):
    """Errores del puzle: cada combinación de palancas lleva la vagoneta a su destino y solo la buena a la báscula."""
    import itertools
    errs = []
    get = t.get
    neighbors = {}
    for a in v["agujas"]:
        neighbors[a] = {d for d, (dx, dz) in DV.items() if is_rail(get(a[0] + dx, a[1], a[2] + dz))}
        if len(neighbors[a]) != 3:
            errs.append(f"la aguja {a} no es un cruce en T ({sorted(neighbors[a])})")
        if form(get(*a)) != spire_shape(neighbors[a], False):
            errs.append(f"la aguja {a} no está en su forma sin señal")
    for p in v["palancas"]:
        nearby_flag = [a for a in v["agujas"] if abs(a[0] - p[0]) + abs(a[2] - p[2]) == 1]
        if len(nearby_flag) != 1:
            errs.append(f"la palanca {p} no está junto a una sola aguja")
    arrive = []
    for combo in itertools.product((False, True), repeat=2):
        switches = {a: spire_shape(neighbors[a], c) for a, c in zip(v["agujas"], combo)}
        try:
            finish, _ = traverse(get, v["salida"], "west", switches)
        except ValueError as e:
            errs.append(f"agujas {combo}: {e}")
            continue
        if finish == v["bascula"]:
            arrive.append(combo)
        elif finish not in v["destinos"].values():
            errs.append(f"agujas {combo}: la vagoneta acaba en {finish}, fuera de los destinos")
    if arrive != [v["solucion"]]:
        errs.append(f"llegan a la báscula las combinaciones {arrive} (se esperaba solo {v['solucion']})")
    return errs
