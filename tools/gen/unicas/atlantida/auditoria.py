"""Auditoría del plano entero de la Atlántida (condición para generar).

Comprueba: estanqueidad de las zonas secas, apoyos, alcanzabilidad sin romper bloques, objetos válidos en los
cofres fijos y proporción de superficie en buen estado. Devuelve una lista de avisos; vacía = apto.
"""
from collections import deque
import validate
from . import urbanismo as U
from .mundo import nombre

VECINOS = ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0))
ACUATICAS = ("water", "bubble_column", "kelp", "kelp_plant", "seagrass", "tall_seagrass")
# Bloques que el agua arranca si entra en su celda: cuentan como aire para la estanqueidad.
LAVABLES = ("redstone_wire", "redstone_wall_torch", "redstone_torch", "lever", "stone_pressure_plate", "cyan_carpet", "azalea",
            "torch", "wall_torch")
FINOS = LAVABLES + ("ladder", "warped_wall_sign", "cyan_wall_banner", "iron_bars", "warped_fence", "dark_oak_fence", "sea_pickle")
PASO_LIBRE = ("air", "warped_door", "iron_door", "ladder", "warped_trapdoor", "warped_wall_sign", "cyan_wall_banner", "sea_pickle") + LAVABLES


def es_agua(st):
    return st is not None and (nombre(st) in ACUATICAS or "waterlogged=true" in st)


def es_seco(st):
    return st is not None and nombre(st) in ("air",) + LAVABLES


def macizo(st):
    """Bloque completo que sostiene y no deja pasar (aproximación suficiente para los materiales de la ciudad)."""
    if st is None:
        return False
    b = nombre(st)
    if b in ACUATICAS or b in PASO_LIBRE or b in FINOS:
        return False
    return not any(k in b for k in ("_stairs", "_slab", "_door", "_fence", "_sign", "_banner", "_bed", "coral_fan", "lectern",
                                    "chest", "decorated_pot", "armor", "anvil", "grindstone", "stonecutter"))


def transitable(st):
    return st is not None and (es_agua(st) or nombre(st) in PASO_LIBRE)


def estanqueidad(m, out):
    n = 0
    for (x, y, z), (st, _) in m.blocks.items():
        if not es_seco(st):
            continue
        for dx, dy, dz in VECINOS:
            v = m.get(x + dx, y + dy, z + dz)
            if v is None or (dy >= 0 and es_agua(v)):
                n += 1
                if n <= 12:
                    out.append(f"fuga: {nombre(st)} en {(x, y, z)} toca {nombre(v) if v else 'terreno natural'} en {(x + dx, y + dy, z + dz)}")
    if n > 12:
        out.append(f"fuga: {n} en total")


def apoyos(m, out):
    atras = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}
    fallos = {}
    def falla(que, pos):
        fallos.setdefault(que, []).append(pos)
    for (x, y, z), (st, _) in m.blocks.items():
        b = nombre(st)
        bajo = m.get(x, y - 1, z)
        if b in ("ladder", "warped_wall_sign", "cyan_wall_banner", "redstone_wall_torch") or b == "lever" and "face=wall" in st:
            f = st.split("facing=")[1].split(",")[0].rstrip("]")
            dx, dz = atras[f]
            if not macizo(m.get(x + dx, y, z + dz)):
                falla(b + " sin pared detrás", (x, y, z))
        elif b.endswith("_door") and "half=lower" in st or b in ("redstone_wire", "stone_pressure_plate", "cyan_carpet", "decorated_pot",
                                                                  "lectern", "azalea", "sea_pickle", "seagrass", "spawner") and b != "spawner":
            if not (macizo(bajo) or b == "cyan_carpet" and bajo and "trapdoor" in bajo or b == "stone_pressure_plate" and bajo and "dispenser" in bajo):
                falla(b + " sin apoyo", (x, y, z))
        elif b in ("sand", "gravel") and not macizo(bajo):
            falla(b + " sin suelo (caería)", (x, y, z))
        elif b in ("kelp", "kelp_plant") and not (macizo(bajo) or nombre(bajo) == "kelp_plant"):
            falla("alga sin base", (x, y, z))
        elif b == "kelp_plant" and nombre(m.get(x, y + 1, z)) not in ("kelp", "kelp_plant"):
            falla("alga cortada", (x, y, z))
        elif b.endswith("_bed") and not macizo(bajo):
            falla("cama sin suelo", (x, y, z))
        elif b in CORALES and not macizo(bajo):
            falla("coral sin apoyo", (x, y, z))
        elif b == "bubble_column":
            if nombre(bajo) not in ("bubble_column", "soul_sand", "magma_block"):
                falla("columna de burbujas sin base", (x, y, z))
    for que, ps in fallos.items():
        out.append(f"{que}: {len(ps)}, p. ej. {ps[:3]}")


def alcanzables(m):
    """Celdas a las que llega un jugador desde el mar abierto nadando, andando, saltando un bloque y por escaleras de
    mano, abriendo puertas y trampillas, sin romper nada. Se explora solo dentro de las cajas de los sitios (+1)."""
    cubo = {}
    for (_, x1, y1, z1, x2, y2, z2, _) in m.sitios:
        caja = (x1 - 1, y1 - 1, z1 - 1, x2 + 1, y2 + 1, z2 + 1)
        for cx in range(caja[0] >> 4, (caja[3] >> 4) + 1):
            for cz in range(caja[2] >> 4, (caja[5] >> 4) + 1):
                cubo.setdefault((cx, cz), []).append(caja)

    def dentro(x, y, z):
        for c in cubo.get((x >> 4, z >> 4), ()):
            if c[0] <= x <= c[3] and c[1] <= y <= c[4] and c[2] <= z <= c[5]:
                return True
        return False

    visto, cola = set(), deque()
    for (_, x1, y1, z1, x2, y2, z2, _) in m.sitios:           # semillas: agua abierta en la capa exterior de cada caja
        if y2 <= U.SUELO:
            continue
        for x in range(x1 - 1, x2 + 2):
            for z in range(z1 - 1, z2 + 2):
                borde = x in (x1 - 1, x2 + 1) or z in (z1 - 1, z2 + 1)
                for y in ((range(max(y1, U.SUELO + 1), y2 + 2)) if borde else (y2 + 1,)):
                    if y > U.TECHO:
                        continue
                    if (x, y, z) not in m.blocks and U.base(x, y, z) == "minecraft:water" and (x, y, z) not in visto:
                        visto.add((x, y, z))
                        cola.append((x, y, z))
    get = m.get
    while cola:
        x, y, z = cola.popleft()
        st = get(x, y, z)
        nada = es_agua(st) or nombre(st) == "ladder"
        pasos = list(VECINOS[:4]) + [(0, -1, 0)]
        for dx, dy, dz in pasos + ([(0, 1, 0)] if nada else []):
            p = (x + dx, y + dy, z + dz)
            if p not in visto and dentro(*p) and transitable(get(*p)):
                visto.add(p)
                cola.append(p)
        if not nada:
            arriba = get(x, y + 1, z)
            if transitable(arriba):
                if es_agua(arriba) or nombre(arriba) == "ladder" or nombre(arriba) == "warped_trapdoor":
                    p = (x, y + 1, z)
                    if p not in visto and dentro(*p):
                        visto.add(p)
                        cola.append(p)
                for dx, _, dz in VECINOS[:4]:                 # salto de un bloque
                    p = (x + dx, y + 1, z + dz)
                    if p not in visto and dentro(*p) and transitable(get(*p)) and not transitable(get(x + dx, y, z + dz)):
                        visto.add(p)
                        cola.append(p)
    return visto


def accesos(m, out, visto):
    for marca in ("seca", "cofre", "premium", "vestibulo", "jefe", "camara_academia", "camara_arsenal", "arena", "oculta", "generador"):
        mal = []
        for (x, y, z) in m.marcas.get(marca, ()):
            cerca = [(x, y, z)] + [(x + a, y + b, z + c) for a, b, c in VECINOS]
            if not any(p in visto for p in cerca):
                mal.append((x, y, z))
        if mal:
            out.append(f"{marca} inaccesible: {len(mal)}, p. ej. {mal[:4]}")


CORALES = ("brain_coral", "bubble_coral", "fire_coral", "horn_coral", "tube_coral")
# lo mismo que lint.access_issues exige en las demás plantillas: nada de esto puede quedar fuera del recorrido
ACCESIBLES = ("ladder", "cyan_bed", "chest", "trapped_chest", "barrel", "lectern", "lever")


def bloques_accesibles(m, out, visto):
    """Escaleras de mano, camas, cofres, barriles, atriles y palancas, y las dos caras de cada puerta, alcanzables."""
    mal = {}
    for (x, y, z), (st, _) in m.blocks.items():
        b = nombre(st)
        if b.endswith("_door") and "half=lower" in st:
            f = st.split("facing=")[1].split(",")[0].rstrip("]")
            dx, dz = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[f]
            if (x + dx, y, z + dz) not in visto or (x - dx, y, z - dz) not in visto:
                mal.setdefault("puerta sin salida o sin acceso", []).append((x, y, z))
        elif b in ACCESIBLES and not any(p in visto for p in [(x, y, z)] + [(x + a, y + c, z + d) for a, c, d in VECINOS]):
            mal.setdefault(b + " inaccesible", []).append((x, y, z))
    for que, ps in mal.items():
        out.append(f"{que}: {len(ps)}, p. ej. {ps[:3]}")


def jigsaws(teselas, out):
    """Ningún bloque posterior ha sobrescrito un jigsaw (la misma comprobación que lint.support_issues)."""
    for t in teselas:
        for j in t.jigsaws:
            if nombre(t.get(*j["pos"]) or "air") != "jigsaw":
                out.append(f"jigsaw sobrescrito en {t.name} {j['pos']}")


def objetos(m, out):
    for (x, y, z), (st, nbt) in m.blocks.items():
        for it in (nbt or {}).get("Items", ()):
            if it["id"].replace("minecraft:", "") not in validate.ITEMS:
                out.append(f"objeto inexistente {it['id']} en {(x, y, z)}")
            if not 0 <= int(it["Slot"]) < 27:
                out.append(f"hueco de cofre fuera de rango en {(x, y, z)}")


def estado(m):
    """Porcentaje de la superficie construida a ras de calle que está en ruinas (solares, distritos y muralla)."""
    ruina = total = 0
    for (n, x1, y1, z1, x2, y2, z2, r) in m.sitios:
        if y2 <= U.SUELO or n in ("nudo", "barco"):
            continue
        a = (x2 - x1 + 1) * (z2 - z1 + 1)
        total += a
        ruina += a if r else 0
    return 100.0 * ruina / max(total, 1)


def auditar(m):
    out = []
    estanqueidad(m, out)
    apoyos(m, out)
    visto = alcanzables(m)
    accesos(m, out, visto)
    bloques_accesibles(m, out, visto)
    objetos(m, out)
    pct = estado(m)
    if not 15.0 <= pct <= 20.0:
        out.append(f"superficie en ruinas {pct:.1f} % (debe quedar entre 15 y 20)")
    m.alcanzables = visto
    m.pct_ruina = pct
    return out
