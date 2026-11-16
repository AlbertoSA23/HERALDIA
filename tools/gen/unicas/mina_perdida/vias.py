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
FORMAS = {"north_south": {"north": 0, "south": 0}, "east_west": {"east": 0, "west": 0},
          "ascending_east": {"west": 0, "east": 1}, "ascending_west": {"east": 0, "west": 1},
          "ascending_north": {"south": 0, "north": 1}, "ascending_south": {"north": 0, "south": 1},
          "south_east": {"south": 0, "east": 0}, "south_west": {"south": 0, "west": 0},
          "north_west": {"north": 0, "west": 0}, "north_east": {"north": 0, "east": 0}}
RAILES = ("rail", "powered_rail", "detector_rail", "activator_rail")
Y = 1                                    # pies del cargadero

# trazado (x, z) del cargadero; las agujas y las palancas
SALIDA, TOPE = (100, 36), (101, 36)      # rampa de salida (propulsor contra el muro este)
ARRANQUE = (100, 35)                     # palanca de suelo junto a la salida
AGUJA1, PALANCA1 = (89, 36), (88, 36)    # T norte-sur con rama al este (por donde llega la vagoneta)
AGUJA2, PALANCA2 = (89, 30), (89, 29)    # T este-oeste con rama al sur (por donde llega)
ESCOMBRERA, FUNDICION = (89, 44), (83, 30)
PUERTA = (92, 24)                        # compuerta del filón madre (bloque inferior a y = 1), en el muro norte
BASCULA = (96, 2, 24)                    # raíl detector, dentro del muro
SOLUCION = (True, False)                 # aguja 1 con señal (norte), aguja 2 sin señal (este)


def forma_aguja(vecinos, con_senal):
    """Forma que el juego da a un raíl con esos vecinos ({'north', ...}) y esa señal (RailState.place)."""
    n, s, w, e = ("north" in vecinos, "south" in vecinos, "west" in vecinos, "east" in vecinos)
    forma = None
    if (n or s) and not w and not e:
        forma = "north_south"
    if (w or e) and not n and not s:
        forma = "east_west"
    se, sw, ne, nw = s and e, s and w, n and e, n and w
    if se and not n and not w:
        forma = "south_east"
    if sw and not n and not e:
        forma = "south_west"
    if nw and not s and not e:
        forma = "north_west"
    if ne and not s and not w:
        forma = "north_east"
    if forma is None:
        orden = ((se, "south_east"), (sw, "south_west"), (ne, "north_east"), (nw, "north_west")) if con_senal else \
                ((nw, "north_west"), (ne, "north_east"), (sw, "south_west"), (se, "south_east"))
        for ok, f in orden:
            if ok:
                forma = f
    return forma


def es_rail(st):
    return st is not None and parse_state(st)[0].replace("minecraft:", "") in RAILES


def forma(st):
    return parse_state(st)[1]["shape"]


def recorrer(get, inicio, sentido, agujas=None, pasos=200):
    """Sigue a una vagoneta desde `inicio` (x, y, z) moviéndose hacia `sentido`. `agujas` {pos: forma} sustituye la
    forma de las agujas. Devuelve (última posición, camino) o lanza ValueError si descarrila."""
    agujas = agujas or {}
    p, d, camino = inicio, sentido, [inicio]
    for _ in range(pasos):
        st = get(*p)
        f = agujas.get(p) or forma(st)
        lados = FORMAS[f]
        entrada = OPP[d]
        if p != inicio and entrada not in lados:
            raise ValueError(f"la vagoneta descarrila en {p} (forma {f}, entra por {entrada})")
        salida = [l for l in lados if l != entrada][0] if p != inicio else d
        dx, dz = DV[salida]
        sig = None
        for dy in (lados.get(salida, 0), 0, -1):
            q = (p[0] + dx, p[1] + dy, p[2] + dz)
            if es_rail(get(*q)):
                sig = q
                break
        if sig is None:
            return p, camino
        p, d = sig, salida
        camino.append(p)
    raise ValueError("la vagoneta no se para")


def trazar(o):
    """Pone las vías, las palancas, los carteles, la vagoneta y la compuerta en la obra `o`; devuelve los mecanismos."""
    s, y = o.s, Y
    rail = o.rail
    # salida: propulsor apagado contra el muro (tope), un raíl normal de aislamiento y dos propulsores con bloque de
    # redstone debajo (siempre encendidos) para que la vagoneta vacía llegue lejos
    rail(*_p(SALIDA), "east_west", "powered_rail", False)
    s(ARRANQUE[0], y, ARRANQUE[1], "lever[face=floor,facing=west,powered=false]")
    for x in range(AGUJA1[0] + 1, SALIDA[0]):
        if x in (97, 98, 93):
            rail(x, y, 36, "east_west", "powered_rail", True)
            s(x, y - 1, 36, "redstone_block")
        else:
            rail(x, y, 36, "east_west")
    # aguja 1 (T norte-sur con rama al este) y su palanca de suelo al oeste
    rail(*_p(AGUJA1), forma_aguja({"north", "south", "east"}, False))
    s(PALANCA1[0], y, PALANCA1[1], "lever[face=floor,facing=east,powered=false]")
    # ramal sur, a la escombrera
    for z in range(AGUJA1[1] + 1, ESCOMBRERA[1] + 1):
        if z == 40:
            rail(89, y, z, "north_south", "powered_rail", True)
            s(89, y - 1, z, "redstone_block")
        else:
            rail(89, y, z, "north_south")
    s(ESCOMBRERA[0], y, ESCOMBRERA[1] + 1, "gravel")                    # el montón de la escombrera hace de tope
    s(ESCOMBRERA[0] + 1, y, ESCOMBRERA[1] + 1, "gravel")
    s(ESCOMBRERA[0], y + 1, ESCOMBRERA[1] + 1, "gravel")
    # ramal norte, a la aguja 2
    for z in range(AGUJA2[1] + 1, AGUJA1[1]):
        if z == 33:
            rail(89, y, z, "north_south", "powered_rail", True)
            s(89, y - 1, z, "redstone_block")
        else:
            rail(89, y, z, "north_south")
    rail(*_p(AGUJA2), forma_aguja({"east", "west", "south"}, False))
    s(PALANCA2[0], y, PALANCA2[1], "lever[face=floor,facing=south,powered=false]")
    # vía muerta de la fundición (al oeste), con un tonel de tope
    for x in range(FUNDICION[0], AGUJA2[0]):
        if x == 86:
            rail(x, y, 30, "east_west", "powered_rail", True)
            s(x, y - 1, 30, "redstone_block")
        else:
            rail(x, y, 30, "east_west")
    o.barrel(FUNDICION[0] - 1, y, 30, "east")
    # a la báscula: al este, curva al norte, rampa y rendija del muro norte
    for x in range(AGUJA2[0] + 1, 96):
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
    rail(*BASCULA, "north_south", "detector_rail", False)
    # la compuerta: piston_door hacia el este, antorcha inversora en el apoyo de la báscula
    px, pz = PUERTA
    from .._comun import piezas
    puerta = [(px, y, pz), (px, y + 1, pz)]
    piezas.piston_door(s, puerta, (1, 0), "west", "cobblestone")
    antorcha = (px + 3, y, pz)
    apoyo = (BASCULA[0], BASCULA[1] - 1, BASCULA[2])
    assert apoyo == (antorcha[0] + 1, y, pz)
    s(*antorcha, "redstone_wall_torch[facing=west,lit=true]")
    s(antorcha[0], y + 1, pz, "cobblestone")                            # lo carga la antorcha: pistón de arriba
    s(*apoyo, "cobblestone")
    for p in puerta:                                                     # hornacina delante de la compuerta
        o.carve(p[0], p[1], p[2] + 1, ("roca", "roca", "roca"))
    o.carved.pop((96, y, 26), None)
    o.carved.pop((96, y + 1, 26), None)
    # carteles en pilares junto a las palancas y al final de cada ramal
    for (x, z, f, pilar, key, lines) in (
            (87, 36, "east", True, "aguja1", [("Aguja 1", "Switch 1")]),
            (89, 28, "south", True, "aguja2", [("Aguja 2", "Switch 2")]),
            (100, 35, "west", False, "arranque", [("Arranque", "Start")]),        # en el muro este
            (90, 45, "west", True, "escombrera", [("Escombrera", "Spoil heap")]),
            (82, 31, "east", False, "via_muerta", [("A la fundición", "To the foundry"), ("(vía muerta)", "(dead end)")])):
        dx, dz = DV[f]
        if pilar:                                    # pilar de ladrillo de 2 de alto que sostiene el cartel
            for dy in (0, 1):
                s(x - dx, y + dy, z - dz, "stone_bricks")
                o.carved.pop((x - dx, y + dy, z - dz), None)
        o.sign(x, y + 1, z, f, key, lines)
    o.sign(px, y + 3, pz + 1, "south", "compuerta", [("Cámara del", "Lode"), ("filón: se abre", "chamber: opens"),
                                                     ("con el peso", "with the weight"), ("del mineral", "of the ore")])
    o.t.entity(SALIDA[0], y, SALIDA[1], {"id": "minecraft:minecart"})
    for pos in puerta:
        o.carved.pop(pos, None)
    return {"salida": _p(SALIDA), "arranque": (ARRANQUE[0], y, ARRANQUE[1]), "agujas": [_p(AGUJA1), _p(AGUJA2)],
            "palancas": [(PALANCA1[0], y, PALANCA1[1]), (PALANCA2[0], y, PALANCA2[1])], "bascula": BASCULA,
            "apoyo": apoyo, "antorcha": antorcha, "puerta": puerta,
            "pistones": [(px + 2, y, pz), (px + 2, y + 1, pz)], "solucion": SOLUCION,
            "destinos": {"escombrera": _p(ESCOMBRERA), "fundicion": _p(FUNDICION), "bascula": BASCULA}}


def _p(xz):
    return (xz[0], Y, xz[1])


def comprobar(t, v):
    """Errores del puzle: cada combinación de palancas lleva la vagoneta a su destino y solo la buena a la báscula."""
    import itertools
    errs = []
    get = t.get
    vecinos = {}
    for a in v["agujas"]:
        vecinos[a] = {d for d, (dx, dz) in DV.items() if es_rail(get(a[0] + dx, a[1], a[2] + dz))}
        if len(vecinos[a]) != 3:
            errs.append(f"la aguja {a} no es un cruce en T ({sorted(vecinos[a])})")
        if forma(get(*a)) != forma_aguja(vecinos[a], False):
            errs.append(f"la aguja {a} no está en su forma sin señal")
    for p in v["palancas"]:
        cerca = [a for a in v["agujas"] if abs(a[0] - p[0]) + abs(a[2] - p[2]) == 1]
        if len(cerca) != 1:
            errs.append(f"la palanca {p} no está junto a una sola aguja")
    llegan = []
    for combo in itertools.product((False, True), repeat=2):
        agujas = {a: forma_aguja(vecinos[a], c) for a, c in zip(v["agujas"], combo)}
        try:
            fin, _ = recorrer(get, v["salida"], "west", agujas)
        except ValueError as e:
            errs.append(f"agujas {combo}: {e}")
            continue
        if fin == v["bascula"]:
            llegan.append(combo)
        elif fin not in v["destinos"].values():
            errs.append(f"agujas {combo}: la vagoneta acaba en {fin}, fuera de los destinos")
    if llegan != [v["solucion"]]:
        errs.append(f"llegan a la báscula las combinaciones {llegan} (se esperaba solo {v['solucion']})")
    return errs
