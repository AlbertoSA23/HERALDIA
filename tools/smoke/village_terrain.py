"""Aldeas y terreno en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/village_terrain.py --jar build/libs/heraldia-X.jar --work build/smoke [--measure]
Comprueba:
- Puerto que busca el agua: /place de una aldea de la costa en varias playas (/locate biome) pone la caseta y el muelle
  en la orilla libre más cercana (línea «muelle en ... punta x z» del log): en la punta hay tablas a nivel del mar con
  agua debajo y los pilotes bajan por el agua hasta el fondo. Tierra adentro, la misma aldea sale sin puerto o, si hay
  agua al alcance, con el muelle sobre ella.
- Puerto en generación natural: con solo la familia de la costa activa y la rejilla mínima, /locate encuentra N aldeas de
  la costa de verdad (se generan como en un mundo normal, no con /place). Leyendo el inicio guardado de cada una (sus
  piezas y cajas) se cuenta cuántas tienen muelle; para cada muelle, en la punta y a su mitad hay tablas a nivel del mar
  con agua debajo y su caja no pisa ninguna otra pieza (calles en planta, edificios en 3D; solo la caseta). Al menos
  NATURAL_RATE de las aldeas deben tener muelle. Con -Dheraldia.depurar.puerto el mod escribe además el tiempo de la
  búsqueda de cada aldea, que se resume.
- Laderas: /place de una aldea de los cerezos (en ladera; /place no ajusta el terreno, el peor caso) deja muy pocos
  bloques de cimiento al aire: los cimientos de los edificios bajan hasta el suelo con el material del estilo.
  Se cuentan leyendo las regiones guardadas (save-all) con un lector mínimo del formato Anvil.
--measure: solo imprime las cifras (para comparar con un .jar anterior), sin dar por fallado nada.
--only-natural: solo la fase de generación natural (la más lenta de medir con un .jar anterior).
"""
import argparse, glob, io, json, os, queue, re, struct, subprocess, sys, threading, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
import server_smoke as s
import nbtlib
from themes import FAMILIES

SEA = 63
COAST = "heraldia:costa_pescadores"
SLOPE = ("heraldia:cerezos_japonesa", "minecraft:cherry_grove", "minecraft:stone_bricks")
RADIUS = 112            # caja forzada y leída alrededor de cada aldea (radio de la estándar + margen; forceload: <= 256 chunks)
MAX_FLOATING = 0.05     # como mucho un 5 %: aleros y arcos de diseño, y cimientos que llegan al tope (16) en un risco
# Generación natural: aldeas de la costa que se buscan (en las 100 casillas de una rejilla de 1.000 bloques más cercanas
# al 0,0) y fracción mínima que debe tener muelle. En un mundo solo 0-5 de esas casillas caen en una playa: hacen falta
# varias semillas (estas tres dan 2 + 3 + 5). Medido con 12 semillas (21 aldeas): antes del T23, 0 de 21 con muelle;
# después, 21 de 21 (--seeds heraldia costa1 ... costa11 --measure).
NATURAL_N, NATURAL_RATE, NATURAL_GRID = 10, 0.8, 1000
NATURAL_SEEDS = ["heraldia", "costa1", "costa2"]
NATURAL_CONFIG = {"aldeas": {"separacion_bloques": NATURAL_GRID, "maximo": 100,
                             "familias": {f: f == "costa" for f in FAMILIES}}}
AIR_BLOCK = {"minecraft:air", "minecraft:cave_air", "minecraft:water", "minecraft:short_grass", "minecraft:tall_grass",
        "minecraft:fern", "minecraft:large_fern", "minecraft:pink_petals", "minecraft:snow"}


def place(ctx, sid, x, z):
    ctx.run(f"forceload add {x - RADIUS} {z - RADIUS} {x + RADIUS} {z + RADIUS}", r"Marked|Added|force|already")
    for _ in range(s.PLACE_ATTEMPTS):
        m = ctx.run(f"place structure {sid} {x} ~ {z}", r"Generated structure")
        if "not loaded" not in m.group(0):
            return "Generated" in m.group(0)
        time.sleep(s.PLACE_RETRY_S)
    return False


def biome(ctx, b, x=0, z=0):
    m = ctx.run(f"execute positioned {x} 100 {z} run locate biome {b}", r"nearest.*?\[(-?\d+), ~?(-?\d+|~), (-?\d+)\]|Could not find")
    return (int(m.group(1)), int(m.group(3))) if m.group(1) else None


def test(ctx, cmd):
    return "passed" in ctx.run(cmd, r"Test passed|Test failed").group(0)


def count(ctx, x0, y0, z0, x1, y1, z1, block, dest):
    """Bloques de un tipo en una caja, sin tocarla: clone filtrado a una zona vacía (cuenta lo copiado)."""
    m = ctx.run(f"clone {x0} {y0} {z0} {x1} {y1} {z1} {dest[0]} {dest[1]} {dest[2]} filtered {block}",
                r"[Ss]uccessfully cloned (\d+)|No blocks|cloned 0")
    return int(m.group(1)) if m.group(1) else 0


def coast_line(ctx, n):
    return next((l for l in ctx.seen[n:] if "aldea de costa en" in l), "")


def pier_ok(ctx, fails, tx, tz):
    """Punta del muelle (de la línea del log): tablas a nivel del mar con agua debajo y pilotes hasta el fondo."""
    if not test(ctx, f"execute if block {tx} {SEA} {tz} #minecraft:planks"):
        fails.append(f"puerto: no hay tablas en la punta del muelle ({tx} {SEA} {tz})")
    if not test(ctx, f"execute if block {tx} {SEA - 1} {tz} minecraft:water"):
        # una calle que llega al mar (tablas sobre el agua por su procesador) bajo el muelle dejaría aquí sus tablas:
        # AldeaStructure descarta esas orillas
        under = "tablas de una calle" if test(ctx, f"execute if block {tx} {SEA - 1} {tz} #minecraft:planks") else "otra cosa"
        fails.append(f"puerto: no hay agua bajo la punta del muelle ({tx} {SEA - 1} {tz}): {under}")
    # pilotes: troncos bajo la fila de la superficie del agua junto a la punta
    logs = count(ctx, tx - 6, SEA - 24, tz - 6, tx + 6, SEA - 2, tz + 6, "#minecraft:logs", (tx - 6, 250, tz - 6))
    print("costa: troncos de pilote bajo el agua en la punta:", logs)
    if logs == 0:
        fails.append("puerto: los pilotes no bajan hasta el fondo")


def coast(ctx, fails, measure):
    beach = [biome(ctx, "minecraft:beach", *p) for p in ((0, 0), (1500, 0), (0, 1500), (-1500, 0), (0, -1500))]
    done = 0
    for b in [p for p in beach if p]:
        n = len(ctx.seen)
        if not place(ctx, COAST, *b):
            fails.append(f"place {COAST} en {b} falló")
            continue
        time.sleep(1)
        line = coast_line(ctx, n)
        print("costa:", b, line.strip())
        m = re.search(r"punta (-?\d+) (-?\d+)", line)
        if not m:
            continue
        pier_ok(ctx, fails, int(m.group(1)), int(m.group(2)))
        done += 1
    total = len([p for p in beach if p])
    print(f"costa: {done} de {total} playas con muelle")
    if done < NATURAL_RATE * total:
        fails.append(f"solo {done} de {total} playas cercanas dieron un sitio con agua para el puerto")


def inland(ctx, fails, p):
    """Tierra adentro (el monte de cerezos de la prueba de ladera): la aldea de la costa sale sin puerto o, si encuentra
    agua al alcance (con la semilla de prueba, a unos 80 bloques), con el muelle sobre ella, nunca en tierra."""
    n = len(ctx.seen)
    if not place(ctx, COAST, *p):
        fails.append(f"place {COAST} en {p} falló")
        return
    time.sleep(1)
    line = coast_line(ctx, n)
    print("costa tierra adentro:", line.strip())
    m = re.search(r"punta (-?\d+) (-?\d+)", line)
    if m:
        pier_ok(ctx, fails, int(m.group(1)), int(m.group(2)))
    elif "sin orilla" not in line:
        fails.append("tierra adentro: falta la línea del puerto en el registro")


# ------------------------------------------------------------------ lector mínimo de regiones (Anvil)
def palette_name(p):
    """26.3 guarda la paleta como cadenas («minecraft:stone», bloques sin propiedades) o compuestos con "id" y
    "properties" (los que tienen propiedades: escaleras, troncos, faroles...); antes del 26.x, "Name"."""
    if isinstance(p, str):
        return str(p).split("[")[0]
    return str(p.get("id", p.get("Name", p.get("", "minecraft:air")))).split("[")[0]


def read_blocks(world, x0, z0, x1, z1):
    """{(x, y, z): nombre} de los bloques no aire de la caja (todas las alturas), leyendo las regiones guardadas."""
    out = {}
    # 26.x: world/dimensions/minecraft/overworld/region (antes world/region)
    paths = glob.glob(os.path.join(world, "dimensions", "minecraft", "overworld", "region", "r.*.mca")) or \
        glob.glob(os.path.join(world, "region", "r.*.mca"))
    for path in paths:
        rx, rz = (int(v) for v in os.path.basename(path).split(".")[1:3])
        with open(path, "rb") as f:
            data = f.read()
        for i in range(1024):
            cx, cz = rx * 32 + i % 32, rz * 32 + i // 32
            if cx * 16 + 15 < x0 or cx * 16 > x1 or cz * 16 + 15 < z0 or cz * 16 > z1:
                continue
            off = int.from_bytes(data[i * 4:i * 4 + 3], "big") * 4096
            if not off:
                continue
            length, comp = struct.unpack(">IB", data[off:off + 5])
            raw = data[off + 5:off + 4 + length]
            nbt = nbtlib.File.parse(io.BytesIO(zlib.decompress(raw) if comp == 2 else raw))
            for sec in nbt.get("sections", []):
                bs = sec.get("block_states")
                if not bs:
                    continue
                pal = [palette_name(p) for p in bs["palette"]]
                if pal == ["minecraft:air"]:
                    continue
                sy = int(sec["Y"]) * 16
                if len(pal) == 1:
                    vals = [0] * 4096
                else:
                    bits = max(4, (len(pal) - 1).bit_length())
                    per, mask = 64 // bits, (1 << bits) - 1
                    vals = []
                    for v in bs["data"]:
                        v = int(v) & 0xFFFFFFFFFFFFFFFF
                        for k in range(per):
                            vals.append((v >> (k * bits)) & mask)
                for idx in range(4096):
                    name = pal[vals[idx]]
                    if name == "minecraft:air":
                        continue
                    x, z = cx * 16 + idx % 16, cz * 16 + (idx // 16) % 16
                    if x0 <= x <= x1 and z0 <= z <= z1:
                        out[(x, sy + idx // 256, z)] = name
    return out


def slope(ctx, work, fails, measure):
    sid, b, found = SLOPE
    p = biome(ctx, b)
    if not p:
        fails.append(f"no hay {b} cerca")
        return None
    if not place(ctx, sid, *p):
        fails.append(f"place {sid} en {p} falló")
        return None
    time.sleep(3)
    ctx.run("save-all flush", r"Saved the game|saved")
    x, z = p
    blocks = read_blocks(os.path.join(work, "world"), x - RADIUS, z - RADIUS, x + RADIUS, z + RADIUS)
    total = [q for q, n in blocks.items() if n == found]
    floating = [q for q in total if blocks.get((q[0], q[1] - 1, q[2]), "minecraft:air") in AIR_BLOCK]
    ys = [q[1] for q in total]
    print(f"ladera: {sid} en {p}: {len(total)} bloques de {found}, {len(floating)} al aire "
          f"(desnivel de la aldea: alturas {min(ys) if ys else '-'}..{max(ys) if ys else '-'})")
    if not measure and total and len(floating) > MAX_FLOATING * len(total):
        fails.append(f"ladera: {len(floating)} de {len(total)} bloques de cimiento al aire")
    return p


# ------------------------------------------------------------------ puerto en generación natural
def region_chunk(world, cx, cz):
    """NBT del chunk guardado (cx, cz) o None."""
    rx, rz = cx >> 5, cz >> 5
    path = os.path.join(world, "dimensions", "minecraft", "overworld", "region", f"r.{rx}.{rz}.mca")
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    i = (cx & 31) + (cz & 31) * 32
    off = int.from_bytes(data[i * 4:i * 4 + 3], "big") * 4096
    if not off:
        return None
    length, comp = struct.unpack(">IB", data[off:off + 5])
    raw = data[off + 5:off + 4 + length]
    return nbtlib.File.parse(io.BytesIO(zlib.decompress(raw) if comp == 2 else raw))


def village_start(world, x, z):
    """Piezas del inicio de aldea guardado en el chunk de (x, z): [(plantilla, proyección, caja, giro)] o None."""
    nbt = region_chunk(world, x >> 4, z >> 4)
    if nbt is None:
        return None
    for sid, start in (nbt.get("structures", {}).get("starts", {}) or {}).items():
        if not str(sid).startswith("heraldia:") or "Children" not in start:
            continue
        pieces = []
        for c in start["Children"]:
            el = c.get("pool_element", {})
            pieces.append((str(el.get("location", "")), str(el.get("projection", "")), [int(v) for v in c["BB"]],
                           str(c.get("rotation", "NONE"))))
        return str(sid), pieces
    return None


# Dirección hacia el mar de cada giro del muelle (el +z de la plantilla girado): (dx, dz)
SEA_DIR = {"NONE": (0, 1), "CLOCKWISE_90": (-1, 0), "CLOCKWISE_180": (0, -1), "COUNTERCLOCKWISE_90": (1, 0)}


def pier_points(bb, rot):
    """Punta y mitad del muelle (columna central) a partir de su caja y su giro."""
    x0, _, z0, x1, _, z1 = bb
    dx, dz = SEA_DIR[rot]
    if dx:
        cz = (z0 + z1) // 2
        tip, base = (x1 if dx > 0 else x0), (x0 if dx > 0 else x1)
        return (tip, cz), ((tip + base) // 2, cz)
    cx = (x0 + x1) // 2
    tip, base = (z1 if dz > 0 else z0), (z0 if dz > 0 else z1)
    return (cx, tip), (cx, (tip + base) // 2)


def overlaps(a, b, floor_plan=False):
    return (a[0] <= b[3] and b[0] <= a[3] and a[2] <= b[5] and b[2] <= a[5]
            and (floor_plan or (a[1] <= b[4] and b[1] <= a[4])))


def start_server(work, launcher, props=()):
    proc = subprocess.Popen(["java", "-Xmx2G", *props, "-jar", launcher, "nogui"], cwd=work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
    return proc, s.Context(proc, lines, seen)


def natural_points():
    """Puntos desde los que se pide /locate: una malla del paso de la rejilla que cubre sus 100 casillas permitidas."""
    r = 5 * NATURAL_GRID
    pts = [(x, z) for x in range(-r, r + 1, NATURAL_GRID) for z in range(-r, r + 1, NATURAL_GRID)]
    return sorted(pts, key=lambda p: (p[0] ** 2 + p[1] ** 2, p))


def natural_world(ctx, work, fails, want):
    """Aldeas de la costa de este mundo (como mucho `want`): [(x, z, sid, piezas)]."""
    found = {}
    for x, z in natural_points():
        m = ctx.run(f"execute positioned {x} 100 {z} run locate structure #heraldia:aldeas",
                    r"is at \[(-?\d+), ~, (-?\d+)\]|Could not find")
        if m.group(1):
            found.setdefault((int(m.group(1)), int(m.group(2))), None)
    villages = list(found)[:want]
    # el inicio (con sus piezas) ya está creado: /locate genera el chunk de inicio hasta STRUCTURE_STARTS. Se carga del
    # todo y se guarda para leerlo.
    for x, z in villages:
        ctx.run(f"forceload add {x} {z}", r"Marked|Added|force|already")
    for x, z in villages:
        ctx.until(f"execute if loaded {x} 0 {z}")
    ctx.run("save-all flush", r"Saved the game|saved")
    out = []
    for x, z in villages:
        st = village_start(os.path.join(work, "world"), x, z)
        if st is None:
            fails.append(f"natural: no se pudo leer el inicio de la aldea de {x} {z}")
        else:
            out.append((x, z) + st)
    return out


def natural_piers(ctx, fails, villages):
    """Comprueba el muelle de cada aldea; devuelve cuántas lo tienen."""
    with_pier = 0
    for x, z, sid, pieces in villages:
        pier = [p for p in pieces if p[0].endswith("/specials/port_pier")]
        shed = [p for p in pieces if "/specials/port" in p[0] and not p[0].endswith("_pier")]
        print(f"natural: {sid} en {x} {z}: {len(pieces)} piezas, {'con' if pier else 'SIN'} muelle")
        if not pier:
            continue
        with_pier += 1
        _, _, bb, rot = pier[0]
        for other in pieces:
            if other is pier[0] or other in shed:
                continue
            street = other[1] == "terrain_matching"
            if overlaps(bb, other[2], floor_plan=street):
                fails.append(f"natural: el muelle de {x} {z} pisa {other[0]} ({'calle' if street else 'edificio'})")
        # tablas a nivel del mar y agua debajo en la punta y a la mitad: se carga solo el chunk de cada punto
        for name, (px, pz) in zip(("punta", "mitad"), pier_points(bb, rot)):
            ctx.run(f"forceload add {px} {pz}", r"Marked|Added|force|already")
            ctx.until(f"execute if loaded {px} 0 {pz}")
            if not ctx.block((px, SEA, pz), "#minecraft:planks"):
                fails.append(f"natural: no hay tablas en la {name} del muelle de {x} {z} ({px} {SEA} {pz})")
            if not ctx.block((px, SEA - 1, pz), "minecraft:water"):
                fails.append(f"natural: no hay agua bajo la {name} del muelle de {x} {z} ({px} {SEA - 1} {pz}): muelle en tierra")
    return with_pier


def natural(jar, work, fails, measure, seeds):
    """Varios mundos (semillas fijas) con solo la familia de la costa, hasta reunir NATURAL_N aldeas."""
    total, with_pier, times = 0, 0, []
    for seed in seeds:
        if total >= NATURAL_N:
            break
        launcher = s.prepare(work, jar, s.gradle_properties())
        with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
            json.dump(NATURAL_CONFIG, f)
        props = os.path.join(work, "server.properties")
        with open(props) as f:
            text = re.sub(r"level-seed=.*", f"level-seed={seed}", f.read())
        with open(props, "w") as f:
            f.write(text)
        proc, ctx = start_server(work, launcher, ["-Dheraldia.depurar.puerto=true"])
        try:
            villages = natural_world(ctx, work, fails, NATURAL_N - total)
            print(f"natural: semilla {seed}: {len(villages)} aldeas de la costa")
            with_pier += natural_piers(ctx, fails, villages)
            total += len(villages)
            times += [int(m.group(1)) for m in re.finditer(r"aldea de costa en .*? en (\d+) µs", ctx.log())]
        finally:
            stop(proc)
    if times:
        times.sort()
        print(f"natural: búsqueda del puerto en {len(times)} aldeas: mediana {times[len(times) // 2] / 1000:.1f} ms, "
              f"máximo {times[-1] / 1000:.1f} ms")
    rate = with_pier / total if total else 0
    print(f"natural: {with_pier} de {total} aldeas de la costa con muelle ({rate:.0%})")
    if total < NATURAL_N:
        fails.append(f"natural: solo {total} aldeas de la costa en las semillas de prueba (se piden {NATURAL_N})")
    if not measure and rate < NATURAL_RATE:
        fails.append(f"natural: {with_pier} de {total} aldeas de la costa con muelle (mínimo {NATURAL_RATE:.0%})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-aldeas"))
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--only-natural", action="store_true")
    ap.add_argument("--seeds", nargs="*", default=NATURAL_SEEDS)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    fails = []
    if not a.only_natural:
        launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
        proc, ctx = start_server(a.work, launcher)
        try:
            p = slope(ctx, a.work, fails, a.measure)
            if not a.measure:
                coast(ctx, fails, a.measure)
                if p:
                    inland(ctx, fails, p)
        finally:
            stop(proc)
    # mundos nuevos con solo la familia de la costa: generación natural
    natural(os.path.abspath(a.jar), a.work, fails, a.measure, a.seeds)
    print("ALDEAS Y TERRENO:", "OK" if not fails else fails)
    return 1 if fails and not a.measure else 0


def stop(proc):
    if proc.poll() is None:
        s.send(proc, "stop")
        try:
            proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
