"""Arena de oleadas (T31): la plantilla del coliseo, los datos que lee el Java (arena/), su botín, sus logros y sus textos.

La arena no es una estructura de la generación del mundo: la coloca el mod cerca del spawn (/heraldia arena place, o
sola en un mundo nuevo) con esta plantilla (heraldia:arena/arena). Es un coliseo de 57 x 14 x 57 bloques con el ruedo
hundido bajo el terreno:
  - el ruedo (radio 14, suelo a y = 0) con 7 puntos de aparición de mobs (ante una celda con rejas en el muro), la
    campana para empezar junto a la entrada y luz suficiente para que no aparezcan monstruos solos;
  - el muro del ruedo (radio 14-16, 3 bloques) con cristal encima hasta y = 10 y un techo de barreras en y = 11: ni
    flechas ni mobs llegan a las gradas, nadie trepa fuera y las arañas no salen;
  - las gradas (4 escalones de asientos, radio 16-24) y el paseo exterior a ras de suelo (y = 7) con pilares, arcos
    y faroles, abierto por todos lados para los espectadores;
  - la entrada al ruedo, al sur: una rampa que baja del paseo al ruedo y una puerta de rejas que el mod cierra mientras
    dura una partida (en la plantilla está abierta).
Materiales: solo los de PALETA (ninguno arde, ninguno lo puede coger un enderman): el fuego y los endermen no pueden con
ella por diseño; las explosiones, los pistones, los jugadores y los endermen que dejan bloques los para el Java.

heraldia/arena.json (dentro del .jar) da al Java las posiciones (relativas a la esquina de la plantilla): ruedo,
puntos de aparición, campana, puerta, sitio de reaparición, y el nivel del suelo; errores() comprueba que la plantilla
cumple lo que dice (falla la generación).

Modos y salón de la fama (T41): tres carteles de pie (madera carmesí: no arde) en el paseo, junto a la entrada, uno por
modo (cooperativo, contrarreloj, supervivencia), con el campeón de la semana anterior que escribe el Java (arena/Fama).
Su sitio va en arena.json («fama»): en una arena colocada antes de T41, el Java los pone solo si ese sitio está libre.
Aquí van también los textos de los modos, la clasificación y la temporada, sus logros (LOGROS_MODOS) y
errores_textos(), que comprueba que las líneas del cartel caben (90 px) en cada idioma con el peor caso.
"""
import math

from core import Template
from loot import item
from unicas._comun import botin

NS = "heraldia"
PLANTILLA = "arena/arena"
VERSION = 1
N = 57                    # lado de la plantilla (cuadrada)
C = N // 2                # columna del centro (28)
ALTO = 14                 # y = 0 .. 13
SUELO = 7                 # y del suelo exterior: esta capa de la plantilla va a la altura del terreno
R_RUEDO, R_MURO, R_GRADAS, R_PASEO = 14, 16, 24, 28.5
TECHO = 11                # techo de barreras sobre el ruedo y el cristal
CRISTAL = (4, 10)         # cristal sobre el muro del ruedo
MURO_ALTO = 3             # el muro del ruedo, de y = 1 a 3
PUNTOS_RADIO = 11
PUERTA_X = (C - 1, C + 1)                 # ancho de la entrada (3)
PUERTA_Z = (C + 14, C + 15)               # la puerta corta el muro del ruedo
PUERTA_Y = (1, 3)
CAMPANA = (C, 1, C + 11)
REAPARICION = (C, SUELO + 1, N - 3)       # arriba de la rampa, mirando al ruedo
RAMPA_Z0 = C + 16                         # primer peldaño: z = C + 17 en y = 1; z = C + 23 en y = 7
# T41: los carteles del salón de la fama, uno por modo (Java: arena/Modo, en ese orden), en el paseo al este de la
# rampa, mirando al sur (rotación 0: los lee quien llega a la entrada desde fuera).
FAMA = [(C + 3, SUELO + 1, N - 5), (C + 4, SUELO + 1, N - 5), (C + 5, SUELO + 1, N - 5)]
FAMA_ROTACION = 0
MODOS = ("coop", "timeattack", "survival")
# Materiales permitidos: no arden (FireBlock) ni están en #minecraft:enderman_holdable.
PALETA = frozenset({
    "air", "barrier", "glass", "iron_bars", "bell", "lantern", "soul_lantern", "sea_lantern",
    "stone", "stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks", "chiseled_stone_bricks",
    "stone_brick_stairs", "stone_brick_slab", "stone_brick_wall", "polished_andesite",
    "smooth_sandstone", "cut_sandstone", "chiseled_sandstone", "red_sandstone", "cut_red_sandstone",
    "chiseled_red_sandstone", "smooth_red_sandstone",
    "crimson_sign",                         # T41: los carteles del salón de la fama (madera del Nether: no arde)
})
# Comprobación aparte (no se usan; por si alguien amplía la PALETA): lo que arde y lo que coge un enderman.
# (por palabras del id: «sandstone» no es «sand» ni «mossy» es «moss»)
PROHIBIDOS = ("planks", "log", "wood", "wool", "leaves", "carpet", "fence", "hay", "bookshelf", "tnt", "dirt", "grass",
              "sand", "gravel", "clay", "mud", "moss", "pumpkin", "melon", "mushroom", "cactus", "nylium", "podzol",
              "mycelium", "roots", "fungus", "flower", "scaffolding", "campfire")
LUCES = ("lantern", "soul_lantern", "sea_lantern")


def dist(x, z):
    """Distancia al centro del ruedo desde el centro de la columna (x, z)."""
    return math.hypot(x - C, z - C)


def en_entrada(x, z):
    return PUERTA_X[0] <= x <= PUERTA_X[1] and z >= PUERTA_Z[0]


def en_puerta(x, y, z):
    return PUERTA_X[0] <= x <= PUERTA_X[1] and PUERTA_Z[0] <= z <= PUERTA_Z[1] and PUERTA_Y[0] <= y <= PUERTA_Y[1]


def hacia_fuera(x, z):
    """Dirección dominante desde el centro (para las escaleras: `facing` es el lado alto, el respaldo)."""
    dx, dz = x - C, z - C
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def angulos_puntos():
    """Ángulos (grados, desde +x hacia +z) de los puntos de aparición: cada 45° menos el sur (90°), la entrada."""
    return [a for a in range(0, 360, 45) if a != 90]


def puntos():
    out = []
    for a in angulos_puntos():
        r = math.radians(a)
        out.append((C + round(PUNTOS_RADIO * math.cos(r)), 1, C + round(PUNTOS_RADIO * math.sin(r))))
    return out


def celda_tras(p, radio):
    """La columna en la misma dirección que el punto p, a `radio` del centro (las rejas y el farol de su celda)."""
    a = math.atan2(p[2] - C, p[0] - C)
    return C + round(radio * math.cos(a)), C + round(radio * math.sin(a))


def tier(d):
    """Escalón de las gradas (0-3) de una columna a distancia d (R_MURO <= d < R_GRADAS)."""
    return int((d - R_MURO) // 2)


def construir():
    t = Template(PLANTILLA)
    pilares = 16
    for x in range(N):
        for z in range(N):
            d = dist(x, z)
            for y in range(ALTO):
                t.set(x, y, z, "air")
            if d < R_RUEDO:
                suelo = "smooth_sandstone"
                if d < 2.5:
                    suelo = "chiseled_sandstone"
                elif 6.5 <= d < 7.5:
                    suelo = "cut_sandstone"
                elif 12.5 <= d:
                    suelo = "cut_red_sandstone"
                t.set(x, 0, z, suelo)
                t.set(x, TECHO, z, "barrier")
            elif d < R_MURO:
                t.set(x, 0, z, "stone_bricks")
                t.fill(x, 1, z, x, MURO_ALTO - 1, z, "polished_andesite")
                t.set(x, MURO_ALTO, z, "chiseled_stone_bricks")
                t.fill(x, CRISTAL[0], z, x, CRISTAL[1], z, "glass")
                t.set(x, TECHO, z, "barrier")
            elif d < R_GRADAS:
                k = tier(d)
                arriba = MURO_ALTO + k
                t.fill(x, 0, z, x, arriba - 1, z, "stone_bricks")
                borde = (d - R_MURO) - 2 * k < 1          # mitad interior del escalón: el asiento
                t.set(x, arriba, z, f"stone_brick_stairs[facing={hacia_fuera(x, z)},half=bottom]" if borde
                      else "polished_andesite")
            else:
                t.fill(x, 0, z, x, SUELO - 1, z, "stone" if d >= R_PASEO else "stone_bricks")
                t.set(x, SUELO, z, "polished_andesite" if d >= R_PASEO or (x + z) % 2 else "stone_bricks")
                if 27 <= d < R_PASEO:                       # fachada: pilares, arcos y faroles
                    s = (math.atan2(z - C, x - C) % (2 * math.pi)) / (2 * math.pi) * pilares
                    if s % 1 < 0.12 or s % 1 > 0.88:
                        t.fill(x, SUELO + 1, z, x, SUELO + 4, z, "stone_bricks")
                        t.set(x, SUELO + 6, z, "lantern")
                    t.set(x, SUELO + 5, z, "chiseled_stone_bricks")
    # luz del ruedo: el centro y un anillo de 8 faroles de mar en el suelo
    t.set(C, 0, C, "sea_lantern")
    for a in range(0, 360, 45):
        r = math.radians(a + 22.5)
        t.set(C + round(7 * math.cos(r)), 0, C + round(7 * math.sin(r)), "sea_lantern")
    # luz de las gradas: faroles de mar en el respaldo de cada escalón, cada 30°
    for k in range(4):
        rr = R_MURO + 2 * k + 1.5
        for a in range(0, 360, 30):
            r = math.radians(a + 15)
            x, z = C + round(rr * math.cos(r)), C + round(rr * math.sin(r))
            if R_MURO <= dist(x, z) < R_GRADAS and not en_entrada(x, z) and not t.get(x, MURO_ALTO + tier(dist(x, z)), z).startswith("minecraft:stone_brick_stairs"):
                t.set(x, MURO_ALTO + tier(dist(x, z)), z, "sea_lantern")
    # puntos de aparición: marca en el suelo y, detrás, una celda con rejas y un farol de almas
    for p in puntos():
        t.set(p[0], 0, p[2], "chiseled_red_sandstone")
        bx, bz = celda_tras(p, R_RUEDO + 0.5)
        lx, lz = celda_tras(p, R_RUEDO + 1.5)
        t.fill(bx, 1, bz, bx, 2, bz, "iron_bars")
        t.set(lx, 1, lz, "soul_lantern")
        t.set(lx, 2, lz, "air")
    # entrada: rampa del paseo al ruedo, con pretiles a los lados y la puerta (abierta) en el muro
    for z in range(PUERTA_Z[0], N):
        piso = min(SUELO, max(0, z - RAMPA_Z0))
        for x in range(PUERTA_X[0], PUERTA_X[1] + 1):
            for y in range(1, SUELO + 5):         # el arco de la fachada (y = 12) queda sobre la entrada
                if not (CRISTAL[0] <= y <= TECHO and dist(x, z) < R_MURO):
                    t.set(x, y, z, "air")
            t.fill(x, 0, z, x, piso, z, "stone_bricks")
            if 0 < piso and z <= RAMPA_Z0 + SUELO:
                t.set(x, piso, z, "stone_brick_stairs[facing=south,half=bottom]")
            elif piso == SUELO:
                t.set(x, piso, z, "polished_andesite")
        if z >= RAMPA_Z0:
            for x in (PUERTA_X[0] - 1, PUERTA_X[1] + 1):
                d = dist(x, z)
                alto = MURO_ALTO + tier(d) if d < R_GRADAS else SUELO
                t.set(x, alto + 1, z, "stone_brick_wall")
    # faroles en el paseo (cada 30°, menos en la entrada) y en las cuatro esquinas de la plaza
    for a in range(0, 360, 30):
        r = math.radians(a + 15)
        x, z = C + round(25.5 * math.cos(r)), C + round(25.5 * math.sin(r))
        if not en_entrada(x, z) and not en_entrada(x - 1, z) and not en_entrada(x + 1, z):
            t.set(x, SUELO + 1, z, "lantern")
    for x, z in ((4, 4), (N - 5, 4), (4, N - 5), (N - 5, N - 5)):
        t.set(x, SUELO + 1, z, "lantern")
    t.set(*CAMPANA, "bell[attachment=floor,facing=north]")
    for p in FAMA:
        t.set(*p, f"crimson_sign[rotation={FAMA_ROTACION}]")
    return t


def datos():
    """Lo que lee el Java (heraldia/arena.json): posiciones relativas a la esquina (x, y, z mínimos) de la plantilla."""
    return {
        "version": VERSION,
        "plantilla": f"{NS}:{PLANTILLA}",
        "tamano": [N, ALTO, N],
        "suelo": SUELO,
        "centro": [C, 1, C],
        "radio_ruedo": R_RUEDO,
        "ruedo_y": [1, TECHO - 1],
        "puntos": [list(p) for p in puntos()],
        "campana": list(CAMPANA),
        "puerta": [[PUERTA_X[0], PUERTA_Y[0], PUERTA_Z[0]], [PUERTA_X[1], PUERTA_Y[1], PUERTA_Z[1]]],
        "reaparicion": list(REAPARICION),
        "fama": [list(p) for p in FAMA],
        "fama_rotacion": FAMA_ROTACION,
    }


def _nombre(st):
    return st.split("[")[0].removeprefix("minecraft:")


def _solido(st):
    return st is not None and _nombre(st) not in ("air", "lantern", "soul_lantern", "bell", "crimson_sign")


def errores(t, d=None):
    """[] si la plantilla cumple lo que promete arena.json: materiales, ruedo cerrado, cristal y techo, puntos, campana,
    puerta y reaparición."""
    d = d or datos()
    e = []
    malos = sorted({_nombre(st) for st, _ in t.blocks.values()} - PALETA)
    if malos:
        e.append(f"arena: materiales fuera de la PALETA: {malos}")
    for b in PALETA:
        if set(b.split("_")) & set(PROHIBIDOS):
            e.append(f"arena: {b} arde o lo coge un enderman")
    if t.size() != tuple(d["tamano"]):
        e.append(f"arena: tamaño {t.size()} distinto de {d['tamano']}")
    cx, _, cz = d["centro"]
    r = d["radio_ruedo"]
    y0, y1 = d["ruedo_y"]
    # el ruedo, cerrado con la puerta cerrada: desde el centro no se llega a ninguna celda fuera de su radio
    cerrada = {(x, y, z) for x in range(d["puerta"][0][0], d["puerta"][1][0] + 1)
               for y in range(d["puerta"][0][1], d["puerta"][1][1] + 1)
               for z in range(d["puerta"][0][2], d["puerta"][1][2] + 1)}
    vistos, cola = {(cx, 1, cz)}, [(cx, 1, cz)]
    while cola:
        x, y, z = cola.pop()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            p = (x + dx, y + dy, z + dz)
            if p in vistos or p in cerrada or not (0 <= p[0] < N and 0 <= p[1] < ALTO and 0 <= p[2] < N):
                continue
            if _solido(t.get(*p)) or _nombre(t.get(*p)) == "iron_bars":
                continue
            vistos.add(p)
            cola.append(p)
    fuera = [p for p in vistos if math.hypot(p[0] - cx, p[2] - cz) >= r or not y0 <= p[1] <= y1]
    if fuera:
        e.append(f"arena: el ruedo no está cerrado (se llega a {sorted(fuera)[:3]}...)")
    if len(vistos) < 3.14 * (r - 1) ** 2 * (y1 - y0):
        e.append(f"arena: ruedo demasiado pequeño ({len(vistos)} celdas)")
    # cristal sobre el muro y techo de barreras
    for x in range(N):
        for z in range(N):
            dd = dist(x, z)
            if dd < R_MURO and _nombre(t.get(x, TECHO, z)) != "barrier":
                e.append(f"arena: falta el techo de barreras en {x}, {TECHO}, {z}")
            if R_RUEDO <= dd < R_MURO and any(_nombre(t.get(x, y, z)) != "glass" for y in range(CRISTAL[0], CRISTAL[1] + 1)):
                e.append(f"arena: falta cristal sobre el muro en {x}, {z}")
            if dd < r and not _solido(t.get(x, 0, z)):
                e.append(f"arena: el suelo del ruedo tiene un hueco en {x}, 0, {z}")
    for p in d["puntos"]:
        if math.hypot(p[0] - cx, p[2] - cz) >= r - 1 or not _solido(t.get(p[0], p[1] - 1, p[2])) \
                or _solido(t.get(*p)) or _solido(t.get(p[0], p[1] + 1, p[2])):
            e.append(f"arena: punto de aparición {p} fuera del ruedo, sin suelo o sin sitio")
    if len(d["puntos"]) < 4:
        e.append("arena: menos de 4 puntos de aparición")
    b = d["campana"]
    if not _nombre(t.get(*b)) == "bell" or not _solido(t.get(b[0], b[1] - 1, b[2])) or tuple(b) not in vistos:
        e.append(f"arena: la campana {b} no está en el suelo del ruedo")
    if any(_solido(t.get(*p)) for p in cerrada):
        e.append("arena: la puerta no está abierta en la plantilla")
    rp = d["reaparicion"]
    if _solido(t.get(*rp)) or _solido(t.get(rp[0], rp[1] + 1, rp[2])) or not _solido(t.get(rp[0], rp[1] - 1, rp[2])) \
            or tuple(rp) in vistos:
        e.append(f"arena: la reaparición {rp} no es un sitio libre con suelo fuera del ruedo")
    # T41: los carteles del salón de la fama, uno por modo, en el paseo (fuera del ruedo y de la entrada), sobre suelo
    # macizo y con aire delante (al sur) para leerlos
    if len(d.get("fama", [])) != len(MODOS):
        e.append(f"arena: hacen falta {len(MODOS)} carteles del salón de la fama, uno por modo")
    for p in d.get("fama", []):
        x, y, z = p
        if _nombre(t.get(*p)) != "crimson_sign" or not _solido(t.get(x, y - 1, z)) or _solido(t.get(x, y, z + 1)) \
                or tuple(p) in vistos or en_entrada(x, z) or dist(x, z) < R_GRADAS or dist(x, z) >= 27:
            e.append(f"arena: el cartel del salón de la fama {p} no está en el paseo sobre suelo y con sitio delante")
    luces = sum(1 for (x, y, z), (st, _) in t.blocks.items() if _nombre(st) in LUCES and dist(x, z) < r)
    if luces < 8:
        e.append(f"arena: el ruedo tiene solo {luces} luces (aparecerían monstruos solos)")
    return e


# --- recompensas, logros y textos ---

def _tabla(*pools):
    return {"type": "minecraft:chest", "pools": [botin.pool(r, es) for r, es in pools]}


# Una recompensa por jugador cada 5 oleadas, mejor según la oleada (nivel 1: la 5; 2: la 10; 3: la 15; 4: la 20 y
# siguientes). Solo vanilla, sin netherita ni élitros (Decisiones del dueño).
RECOMPENSAS = {
    1: _tabla((3, [item("iron_ingot", 6, 2, 5), item("bread", 4, 3, 6), item("arrow", 4, 8, 16), item("emerald", 4, 2, 5),
                   item("golden_carrot", 3, 2, 4)]),
              (1, [item("golden_apple", 1), item("iron_sword", 1, ench=(5, 15))])),
    2: _tabla((3, [item("iron_ingot", 4, 4, 8), item("gold_ingot", 4, 2, 5), item("emerald", 4, 4, 8), item("arrow", 3, 16, 32),
                   item("experience_bottle", 3, 3, 6)]),
              (1, [item("diamond", 3, 1, 2), item("golden_apple", 2, 1, 2), item("iron_chestplate", 1, ench=(10, 20))])),
    3: _tabla((3, [item("diamond", 3, 1, 3), item("emerald", 4, 6, 12), item("experience_bottle", 4, 5, 10),
                   item("golden_apple", 3, 1, 2)]),
              (1, [item("diamond_sword", 1, ench=(15, 25)), item("bow", 1, ench=(15, 25)), item("diamond_helmet", 1, ench=(10, 20))])),
    4: _tabla((3, [item("diamond", 3, 2, 4), item("emerald_block", 2, 1, 2), item("experience_bottle", 4, 8, 16),
                   item("golden_apple", 3, 2, 3)]),
              (1, [item("enchanted_golden_apple", 1), item("diamond_chestplate", 2, ench=(20, 30)), item("totem_of_undying", 1),
                   item("diamond_sword", 2, ench=(25, 30))])),
}
LOGROS = {5: ("iron_sword", "task", 50), 10: ("golden_sword", "goal", 100), 20: ("diamond_sword", "challenge", 250)}
# T41: logros de los modos (los concede el Java: arena/Marcas.logros y Fama). (id, icono, marco, xp, padre,
# (título es, en), (descripción es, en)). Las cifras son las de arena/Marcas (CONTRARRELOJ_OLEADAS = 10,
# CONTRARRELOJ_RAPIDO_TICKS = 15 min, SUPERVIVENCIA_OLEADAS = 15).
CONTRARRELOJ_OLEADAS, CONTRARRELOJ_RAPIDO_MIN, SUPERVIVENCIA_OLEADAS = 10, 15, 15
LOGROS_MODOS = [
    ("contrarreloj", "clock", "goal", 100, "oleada_5", ("Contra el reloj", "Against the Clock"),
     (f"Termina un contrarreloj de {CONTRARRELOJ_OLEADAS} oleadas en la arena",
      f"Finish a {CONTRARRELOJ_OLEADAS}-wave time attack in the arena")),
    ("contrarreloj_rapido", "sugar", "challenge", 250, "contrarreloj", ("Relámpago", "Lightning"),
     (f"Termina un contrarreloj de {CONTRARRELOJ_OLEADAS} oleadas en menos de {CONTRARRELOJ_RAPIDO_MIN} minutos",
      f"Finish a {CONTRARRELOJ_OLEADAS}-wave time attack in under {CONTRARRELOJ_RAPIDO_MIN} minutes")),
    (f"supervivencia_{SUPERVIVENCIA_OLEADAS}", "shield", "goal", 150, "oleada_5", ("Incansable", "Relentless"),
     (f"Supera la oleada {SUPERVIVENCIA_OLEADAS} en supervivencia, sin pausas",
      f"Clear wave {SUPERVIVENCIA_OLEADAS} in survival mode, with no breaks")),
    ("campeon_coop", "golden_helmet", "challenge", 100, "oleada_5", ("Héroe de la semana", "Hero of the Week"),
     ("Gana una semana de la arena en el modo cooperativo", "Win an arena week in co-op mode")),
    ("campeon_timeattack", "golden_boots", "challenge", 100, "contrarreloj", ("El más rápido", "The Fastest"),
     ("Gana una semana de la arena en el contrarreloj", "Win an arena week in time attack")),
    (f"campeon_survival", "golden_chestplate", "challenge", 100, f"supervivencia_{SUPERVIVENCIA_OLEADAS}",
     ("El último en pie", "Last One Standing"),
     ("Gana una semana de la arena en supervivencia", "Win an arena week in survival mode")),
]


def recompensa_id(nivel):
    return f"{NS}:arena/recompensa_{nivel}"


def logro_id(oleada):
    return f"{NS}:arena/oleada_{oleada}"


def _clave_logro(oleada, parte):
    return f"advancements.{NS}.arena.oleada_{oleada}.{parte}"


def logros():
    """{ruta: json} de los logros de la arena (los concede el Java al superar la oleada; criterio «impossible»)."""
    out = {}
    padre = f"{NS}:raiz"
    for oleada, (icono, marco, xp) in sorted(LOGROS.items()):
        out[f"arena/oleada_{oleada}"] = {
            "parent": padre,
            "criteria": {"oleada": {"trigger": "minecraft:impossible"}},
            "display": {"icon": {"id": f"minecraft:{icono}"},
                        "title": {"translate": _clave_logro(oleada, "title"), "fallback": LANG_LOGROS[oleada][0][0]},
                        "description": {"translate": _clave_logro(oleada, "description"),
                                        "fallback": LANG_LOGROS[oleada][1][0]},
                        "frame": marco},
            "requirements": [["oleada"]],
            "rewards": {"experience": xp},
        }
        padre = logro_id(oleada)
    for lid, icono, marco, xp, padre, titulo, desc in LOGROS_MODOS:
        out[f"arena/{lid}"] = {
            "parent": f"{NS}:arena/{padre}",
            "criteria": {"logro": {"trigger": "minecraft:impossible"}},
            "display": {"icon": {"id": f"minecraft:{icono}"},
                        "title": {"translate": f"advancements.{NS}.arena.{lid}.title", "fallback": titulo[0]},
                        "description": {"translate": f"advancements.{NS}.arena.{lid}.description", "fallback": desc[0]},
                        "frame": marco},
            "requirements": [["logro"]],
            "rewards": {"experience": xp},
        }
    return out


LANG_LOGROS = {
    5: (("Gladiador", "Gladiator"), ("Supera la oleada 5 de la arena", "Survive wave 5 of the arena")),
    10: (("Campeón de la arena", "Arena Champion"), ("Supera la oleada 10 de la arena", "Survive wave 10 of the arena")),
    20: (("Leyenda del ruedo", "Legend of the Ring"), ("Supera la oleada 20 de la arena", "Survive wave 20 of the arena")),
}
# Nombres de los mini-jefes (uno cada 5 oleadas, en rotación; el Java elige por oleada).
JEFES = [("Gorbak el Rompehuesos", "Gorbak the Bonebreaker"), ("Saeta Negra", "Black Arrow"),
         ("Verdugo de la Arena", "Arena Executioner"), ("El Último Campeón", "The Last Champion")]
TEXTOS = {
    "nombre": ("Arena de oleadas", "Wave arena"),
    "propuesta": ("Sitio propuesto para la arena: %s, %s, %s (a %s bloques del spawn). Las partículas marcan sus esquinas.",
                  "Proposed arena site: %s, %s, %s (%s blocks from spawn). The particles mark its corners."),
    "propuesta.confirmar": ("Confirma con %s", "Confirm with %s"),
    "copia": ("Se despeja y nivela el terreno: conviene hacer antes una copia de seguridad del mundo.",
              "The ground will be cleared and levelled: make a backup of the world first."),
    "sin_sitio": ("No hay ningún sitio llano y sin agua a 200-300 bloques del spawn.",
                  "There is no flat, dry site 200-300 blocks from spawn."),
    "sin_propuesta": ("Primero pide un sitio con %s.", "First ask for a site with %s."),
    "ya_existe": ("Ya hay una arena en %s, %s, %s: quítala con /heraldia arena remove o muévela con /heraldia arena move.",
                  "There is already an arena at %s, %s, %s: remove it with /heraldia arena remove or move it with /heraldia arena move."),
    "no_existe": ("No hay ninguna arena en este mundo.", "There is no arena in this world."),
    "colocando": ("Colocando la arena en %s, %s, %s…", "Building the arena at %s, %s, %s…"),
    "colocada": ("La arena está lista en %s, %s, %s.", "The arena is ready at %s, %s, %s."),
    "quitar.confirmar": ("Se quitará la arena de %s, %s, %s (el terreno queda llano). Confirma con /heraldia arena remove confirm.",
                         "The arena at %s, %s, %s will be removed (the ground stays flat). Confirm with /heraldia arena remove confirm."),
    "quitada": ("Arena quitada.", "Arena removed."),
    "ocupada": ("Hay una partida en marcha: espera a que acabe o usa /heraldia arena stop.",
                "A match is in progress: wait for it to end or use /heraldia arena stop."),
    "trabajando": ("Ya se está colocando o quitando la arena.", "The arena is already being built or removed."),
    "desactivada": ("La arena está desactivada en la configuración (arena.activado).",
                    "The arena is disabled in the configuration (arena.activado)."),
    "info": ("Arena de oleadas en %s, %s, %s.", "Wave arena at %s, %s, %s."),
    "info.libre": ("Sin partida: entra en el ruedo y toca la campana.", "No match: step into the ring and ring the bell."),
    "info.partida": ("Partida en marcha: oleada %s, %s participantes.", "Match in progress: wave %s, %s players."),
    "info.record": ("Tu récord: oleada %s. Récord del servidor: oleada %s.", "Your record: wave %s. Server record: wave %s."),
    "cuenta": ("Prepárate", "Get ready"),
    "lucha": ("¡Lucha!", "Fight!"),
    "oleada": ("Oleada %s", "Wave %s"),
    "oleada.jefe": ("¡Llega %s!", "%s is coming!"),
    "oleada.mobs": ("%s enemigos", "%s enemies"),
    "oleada.superada": ("Oleada %s superada", "Wave %s cleared"),
    "oleada.siguiente": ("Siguiente oleada en %s s", "Next wave in %s s"),
    "barra": ("Arena · oleada %s · quedan %s", "Arena · wave %s · %s left"),
    "barra.pausa": ("Arena · oleada %s superada", "Arena · wave %s cleared"),
    "barra.cuenta": ("Arena · empieza en %s", "Arena · starts in %s"),
    "fin": ("La partida de la arena ha terminado: %s oleadas superadas.", "The arena match is over: %s waves cleared."),
    "sale": ("%s ha salido del ruedo.", "%s has left the ring."),
    "cae": ("%s ha caído en la oleada %s.", "%s fell in wave %s."),
    "conservado": ("Has caído en la arena: conservas tu inventario y tu experiencia.",
                   "You fell in the arena: you keep your inventory and experience."),
    "record.personal": ("Nuevo récord personal en la arena: oleada %s.", "New personal arena record: wave %s."),
    "record.servidor": ("¡%s ha batido el récord de la arena: oleada %s!", "%s has broken the arena record: wave %s!"),
    "recompensa": ("Recompensa por superar la oleada %s.", "Reward for clearing wave %s."),
    "sin_participantes": ("No hay nadie en el ruedo: entrad y tocad la campana.", "Nobody is in the ring: step in and ring the bell."),
    "en_marcha": ("Ya hay una partida en marcha.", "A match is already in progress."),
    "prohibido": ("La arena está protegida.", "The arena is protected."),
    "perla": ("No se pueden lanzar perlas de ender en el ruedo durante la partida.",
              "Ender pearls cannot be thrown in the ring during a match."),
    "salir.no": ("No estás en ninguna partida de la arena.", "You are not in an arena match."),
    "parada": ("Partida de la arena detenida.", "Arena match stopped."),
    "marcador": ("Arena: récord de oleadas", "Arena: wave records"),
    "marcador.servidor": ("Récord del servidor", "Server record"),
    # T41: modos, clasificación semanal, temporada y salón de la fama
    "modo.coop": ("Cooperativo", "Co-op"),
    "modo.timeattack": ("Contrarreloj", "Time attack"),
    "modo.survival": ("Supervivencia", "Survival"),
    "modo.coop.ayuda": ("Oleadas sin fin con pausa entre ellas: puntúa la oleada a la que llegáis.",
                        "Endless waves with a break in between: your score is the wave you reach."),
    "modo.timeattack.ayuda": ("%s oleadas contra el reloj: gana quien las supera antes.",
                              "%s waves against the clock: whoever clears them fastest wins."),
    "modo.survival.ayuda": ("Oleadas sin pausa hasta que caigáis: puntúa la oleada más alta.",
                            "Waves with no break until you fall: your score is the highest wave."),
    "modo.elige": ("Elige el modo de la partida (pulsa uno):", "Choose the match mode (click one):"),
    "modo.ninguno": ("No hay ningún modo de partida activado (arena.modos.*).", "No match mode is enabled (arena.modos.*)."),
    "modo.desactivado": ("El modo %s está desactivado en la configuración.", "The %s mode is disabled in the configuration."),
    "modo.ruedo": ("Entra en el ruedo para empezar una partida.", "Step into the ring to start a match."),
    "cuenta.modo": ("Prepárate: %s", "Get ready: %s"),
    "info.partida.modo": ("Partida en marcha (%s): oleada %s, %s participantes.", "Match in progress (%s): wave %s, %s players."),
    "oleada.de": ("Oleada %s de %s", "Wave %s of %s"),
    "sin_pausa": ("Sin respiro: llega la siguiente", "No respite: here comes the next one"),
    "tiempo": ("Tiempo: %s", "Time: %s"),
    "fin.contrarreloj": ("¡Contrarreloj completado: %s oleadas en %s!", "Time attack complete: %s waves in %s!"),
    "fin.contrarreloj.no": ("Contrarreloj sin acabar: %s de %s oleadas.", "Time attack unfinished: %s of %s waves."),
    "barra.contrarreloj": ("Contrarreloj · oleada %s/%s · quedan %s · %s", "Time attack · wave %s/%s · %s left · %s"),
    "barra.supervivencia": ("Supervivencia · oleada %s · quedan %s", "Survival · wave %s · %s left"),
    "puntos.oleadas": ("oleada %s", "wave %s"),
    "puntos.tiempo": ("%s (%s oleadas)", "%s (%s waves)"),
    "puntos.parcial": ("%s/%s oleadas", "%s/%s waves"),
    "record.modo": ("¡%s bate el récord de la arena en %s: %s!", "%s has set a new arena record in %s: %s!"),
    "semana.cerrada": ("Termina la semana de la arena (la del %s).", "The arena week of %s is over."),
    "semana.campeon": ("Campeón de %s: %s, %s.", "%s champion: %s, %s."),
    "semana.sin_campeones": ("Nadie jugó en la arena esa semana.", "Nobody played in the arena that week."),
    "clasificacion.actual": ("Clasificación de la arena, semana del %s (en curso):", "Arena leaderboard, week of %s (current):"),
    "clasificacion.pasada": ("Clasificación de la arena, semana del %s:", "Arena leaderboard, week of %s:"),
    "clasificacion.vacia": ("  Sin marcas todavía.", "  No results yet."),
    "clasificacion.linea": ("  %s. %s: %s", "  %s. %s: %s"),
    "clasificacion.record": ("  Récord: %s, %s", "  Record: %s, %s"),
    "clasificacion.sin_semana": ("No se guarda esa semana: el histórico tiene %s.",
                                 "That week is not kept: the history has %s."),
    "temporada.info": ("Semana de la arena del %s; próximo reinicio: %s (%s); %s semanas en el histórico.",
                       "Arena week of %s; next reset: %s (%s); %s weeks in the history."),
    "temporada.reiniciada": ("Semana de la arena del %s cerrada a mano.", "Arena week of %s closed by hand."),
    "cartel.titulo": ("Campeón", "Champion"),
    "cartel.nadie": ("Sin campeón", "No champion"),
}
# Líneas de los carteles del salón de la fama (Java: arena/Fama.lineas): (clave, en negrita, argumentos del peor caso).
# La del jugador es su nombre (hasta 16 caracteres de A-Z, a-z, 0-9 y _; uno de 16 «W» no cabe: el cliente lo corta).
CARTEL = [("cartel.titulo", True, []), ("modo.coop", False, []), ("modo.timeattack", False, []), ("modo.survival", False, []),
          ("cartel.nadie", False, []), ("puntos.oleadas", False, ["999"]),
          ("puntos.parcial", False, ["99", "99"])]          # el contrarreloj acabado: solo su tiempo (m:ss)
NOMBRE_TIPICO = "Steve_Builder12"       # 15 caracteres medianos: lo que debe caber en la línea del jugador



def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTOS.items():
        out["es_es"][f"{NS}.arena.{k}"], out["en_us"][f"{NS}.arena.{k}"] = es, en
    for i, (es, en) in enumerate(JEFES):
        out["es_es"][f"{NS}.arena.jefe.{i}"], out["en_us"][f"{NS}.arena.jefe.{i}"] = es, en
    for oleada, (titulo, desc) in LANG_LOGROS.items():
        for i, idioma in enumerate(("es_es", "en_us")):
            out[idioma][_clave_logro(oleada, "title")] = titulo[i]
            out[idioma][_clave_logro(oleada, "description")] = desc[i]
    for lid, _, _, _, _, titulo, desc in LOGROS_MODOS:
        for i, idioma in enumerate(("es_es", "en_us")):
            out[idioma][f"advancements.{NS}.arena.{lid}.title"] = titulo[i]
            out[idioma][f"advancements.{NS}.arena.{lid}.description"] = desc[i]
    return out


def errores_textos(traducciones=None):
    """[] si cada línea de los carteles del salón de la fama cabe (90 px, la negrita cuenta) en cada idioma, con los
    argumentos del peor caso. `traducciones`: {código: textos} de los idiomas que no son es/en."""
    import idiomas
    base = lang()
    e = []
    todos = [("es_es", base["es_es"]), ("en_us", base["en_us"])] + list((traducciones or {}).items())
    for codigo, textos in todos:
        for k, negrita, args in CARTEL:
            texto = idiomas.formatear(textos[f"{NS}.arena.{k}"], args)
            if idiomas.ancho_cartel(texto, negrita) > idiomas.CARTEL_ANCHO:
                e.append(f"arena: {codigo}: la línea del cartel {k} no cabe: «{texto}» "
                         f"({idiomas.ancho_cartel(texto, negrita)} px de {idiomas.CARTEL_ANCHO})")
    if idiomas.ancho_cartel(NOMBRE_TIPICO) > idiomas.CARTEL_ANCHO:
        e.append("arena: un nombre de jugador típico no cabe en el cartel")
    return e


def tablas():
    """{nombre: tabla} para la validación del botín."""
    return {f"arena/recompensa_{n}": t for n, t in RECOMPENSAS.items()}


def write(out, jdump):
    """Escribe la plantilla, heraldia/arena.json, las recompensas y los logros; devuelve los textos. Falla si la
    plantilla no cumple lo que promete."""
    t = construir()
    e = errores(t)
    if e:
        raise SystemExit("\n".join(e))
    t.save(out)
    jdump(out, f"{NS}/arena.json", dict(datos(), jefes=len(JEFES)))
    for n, tabla in RECOMPENSAS.items():
        jdump(out, f"data/{NS}/loot_table/arena/recompensa_{n}.json", tabla)
    for ruta, logro in logros().items():
        jdump(out, f"data/{NS}/advancement/{ruta}.json", logro)
    return lang()
