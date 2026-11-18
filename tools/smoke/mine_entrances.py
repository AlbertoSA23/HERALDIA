"""Entradas a mina (tools/gen/mines) y minas vanilla multiplicadas en un servidor dedicado 26.3 real (determinista: semilla
fija de server_smoke y zonas elegidas de antemano).

Uso: python3 tools/smoke/mine_entrances.py --jar build/libs/heraldia-X.jar [--work build/smoke-entradas-mina]
Dos arranques del mismo mundo:
1. minas.vanilla.multiplicador = 1 (la colocación vanilla exacta):
   - el log: la rejilla de cada tamaño (separación, búsqueda de bioma), la regla de las minas y la frecuencia vanilla;
   - /place structure de un estilo de cada tamaño: la boca (vía bajo el dintel y postes), la vía entera del patio al
     último cruce del tronco (cada raíl de la plantilla en su sitio con el giro elegido), los cruces de la galería bajo
     tierra (aire a la altura de la cabeza y casco encima, por debajo del suelo de la boca), cada cofre con su tabla
     heraldia:minas/<tabla>, la vagoneta de carga, las arañas de la mediana y el generador de la grande;
   - loot spawn de cada tabla;
   - /locate de cada tamaño desde el 0,0, que la genera de verdad (forceload) donde dijo /locate, y /heraldia info nearby
     desde allí: ninguna aldea ni única a menos de medianas.distancia_aldeas_unicas_bloques, ni otra mina de otro tamaño
     ni una mediana a menos de medianas.distancia_minima.bloques;
   - /locate lejos (desde 8000, -8000, como tools/smoke/generation_cost.py) de #heraldia:minas y de cada tamaño: lo que
     tarda (el juego lo dice en el log; con la caché compartida de alturas y el cálculo adelantado en paralelo de T36,
     por debajo de LOCATE_LEJOS_MS) y que encuentra las mismas minas que la 0.1.0 (LOCATE_LEJOS, medido con su .jar);
   - /heraldia info: la línea de las minas y las 30 entradas registradas;
   - genera la zona A (12 x 12 chunks) y guarda sus inicios de mina vanilla: todos están entre los que predice el
     sorteo vanilla (legacy_type_3) con la frecuencia de 26.3.
2. minas.vanilla.multiplicador = 5: la zona A (ya generada) conserva exactamente sus minas, y en la zona B (nueva) salen
   minas que con la frecuencia vanilla no saldrían (y ninguna fuera de las que predice x5).
Código 0 si todo pasa.
"""
import argparse, glob, io, json, math, os, queue, re, struct, subprocess, sys, threading, time, zlib
import nbtlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

sys.path.insert(0, os.path.join(s.ROOT, "tools", "gen"))
import mines                                    # noqa: E402  (el generador: plantillas, botín y su vía)
from uniques.lost_mine.tracks import traverse  # noqa: E402

PLACE_X, PLACE_Z, STEP = 40000, 40000, 320      # /place de cada tamaño, lejos de todo
STYLE = "montana"
LOCATE_MAX = {"pequena": 6000, "mediana": 9000, "grande": 20000}   # bloques desde el 0,0 (cada 768, 1.152 y 1.920, en laderas)
ZONE, DISTANCE = 256, 192                       # opciones.py, por defecto
SIDE = 12                                        # chunks de lado de las zonas A y B
TURNS = {"NONE": lambda x, z: (x, z), "CLOCKWISE_90": lambda x, z: (-z, x), "CLOCKWISE_180": lambda x, z: (-x, -z),
         "COUNTERCLOCKWISE_90": lambda x, z: (z, -x)}
ENTRANCE = re.compile(r"entrada a mina en (-?\d+) (-?\d+) (-?\d+) \(giro (\w+)")
# /locate lejos: desde dónde, qué encuentra con la semilla de prueba (el mismo resultado que la 0.1.0, antes de T36: lo
# que cambió es solo cuánto tarda) y el tope de lo que puede tardar el primero (la 0.1.0 tardaba unos 5 s en local).
LOCATE_FROM = (8000, -8000)
LOCATE_FAR = {"#heraldia:minas": (14560, -5664), "#heraldia:minas/pequena": (3888, -7296),
                "#heraldia:minas/mediana": (-4080, -16512), "#heraldia:minas/grande": (14560, -5664)}
LOCATE_FAR_MS = 2500
_LOCATE_MS = re.compile(r"Locating element (\S+) .*?took (\d+) ms")


# ------------------------------------------------------------------ sorteo vanilla de las minas (legacy_type_3)
class Lcg:
    """java.util.Random (LegacyRandomSource de 26.3)."""
    M = (1 << 48) - 1

    def __init__(self, seed):
        self.set(seed)

    def set(self, seed):
        self.s = (seed ^ 0x5DEECE66D) & self.M

    def next(self, bits):
        self.s = (self.s * 0x5DEECE66D + 0xB) & self.M
        v = self.s >> (48 - bits)                    # (int) de Java: solo con 32 bits puede salir negativo
        return v - (1 << 32) if bits == 32 and v >= 1 << 31 else v

    def next_long(self):
        v = (self.next(32) << 32) + self.next(32)
        return (v + (1 << 63)) % (1 << 64) - (1 << 63)

    def next_double(self):
        return ((self.next(26) << 27) + self.next(27)) * 2.0 ** -53       # BitRandomSource.nextDouble


def s64(v):
    return (v + (1 << 63)) % (1 << 64) - (1 << 63)


def sale_vanilla(seed, x, z, frequency):
    """legacyProbabilityReducerWithDouble: setLargeFeatureSeed(seed, x, z) y nextDouble() < frecuencia (float)."""
    r = Lcg(seed)
    a, b = r.next_long(), r.next_long()
    r.set(s64(s64(x * a) ^ s64(z * b) ^ seed))
    return r.next_double() < frequency


def f32(v):
    return struct.unpack("f", struct.pack("f", v))[0]


def float_str(v):
    """Float.toString de Java: los menos dígitos que vuelven al mismo float."""
    for d in range(1, 10):
        t = f"{v:.{d}g}"
        if f32(float(t)) == v:
            return t if "." in t or "e" in t else t + ".0"
    return repr(v)


def prediction(seed, cx0, cz0, frequency):
    return {(x, z) for x in range(cx0, cx0 + SIDE) for z in range(cz0, cz0 + SIDE) if sale_vanilla(seed, x, z, frequency)}


def choose_zones(seed):
    """Zona A (con alguna mina vanilla y alguna que solo saldría con x5) y zona B (con al menos 3 de x5 de más)."""
    f1, f5 = f32(0.004), f32(f32(0.004) * 5.0)
    zones = []
    for k in range(60):
        cx0, cz0 = 1500 + k * (SIDE + 4), -1500
        p1, p5 = prediction(seed, cx0, cz0, f1), prediction(seed, cx0, cz0, f5)
        zones.append((cx0, cz0, p1, p5))
    a = next(z for z in zones if len(z[2]) >= 1 and len(z[3] - z[2]) >= 2)
    b = next(z for z in zones if z is not a and len(z[3] - z[2]) >= 3)
    return a, b


# ------------------------------------------------------------------ regiones guardadas
def chunk_nbt(world, cx, cz):
    rx, rz = cx >> 5, cz >> 5
    path = os.path.join(world, "dimensions", "minecraft", "overworld", "region", f"r.{rx}.{rz}.mca")
    if not os.path.isfile(path):
        path = os.path.join(world, "region", f"r.{rx}.{rz}.mca")
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


def saved_mines(world, cx0, cz0):
    """Chunks de la zona con un inicio de mina vanilla guardado, y los que no están generados del todo."""
    out, missing = set(), []
    for x in range(cx0, cx0 + SIDE):
        for z in range(cz0, cz0 + SIDE):
            n = chunk_nbt(world, x, z)
            if n is None or str(n.get("Status", "")) not in ("minecraft:full", "full"):
                missing.append((x, z))
                continue
            starts = (n.get("structures") or {}).get("starts") or {}
            for sid in ("minecraft:mineshaft", "minecraft:mineshaft_mesa"):
                st = starts.get(sid)
                if st is not None and str(st.get("id", "INVALID")) != "INVALID":
                    out.add((x, z))
    return out, missing


# ------------------------------------------------------------------ servidor
def start_up(work, jar, cfg, clean_up):
    launcher = s.prepare(work, jar, s.gradle_properties()) if clean_up else os.path.join(work, glob.glob(
        os.path.join(work, "fabric-server-*.jar"))[0])
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
    ctx = s.Context(proc, lines, seen)
    ctx.run("gamerule spawn_mobs false", r"Gamerule|set to|now")
    return proc, ctx


def halt(proc):
    if proc.poll() is None:
        s.send(proc, "stop")
        proc.wait(timeout=180)


def forceload(ctx, x0, z0, x1, z1, remove=False):
    ctx.run(f"forceload {'remove' if remove else 'add'} {x0} {z0} {x1} {z1}", r"Marked|[Aa]dded|[Rr]emoved|force|already|[Uu]nmarked")


def generate_zone(ctx, cx0, cz0):
    x0, z0, x1, z1 = cx0 * 16, cz0 * 16, (cx0 + SIDE) * 16 - 1, (cz0 + SIDE) * 16 - 1
    forceload(ctx, x0, z0, x1, z1)
    for x, z in ((x0, z0), (x1, z1), (x0, z1), (x1, z0)):
        if not ctx.until(f"execute if loaded {x} 64 {z}", timeout=300):
            return False
    ctx.ticks(40)
    forceload(ctx, x0, z0, x1, z1, remove=True)
    ctx.run("save-all flush", r"Saved the game|saved")
    return True


# ------------------------------------------------------------------ entradas colocadas
def check_placed(ctx):
    fails, timings = [], []
    for k, size in enumerate(mines.SIZES):
        o, _, _ = mines.construction(size, STYLE, "a")
        sid = mines.template(size, STYLE, "a")
        px, pz = PLACE_X + k * STEP, PLACE_Z
        forceload(ctx, px - 112, pz - 112, px + 111, pz + 111)
        before = len(ctx.seen)
        t0 = time.monotonic()
        m = ctx.run(f"place structure heraldia:{sid} {px} 100 {pz}", r"Generated structure|Failed to place")
        timings.append(time.monotonic() - t0)
        if not m.group(0).startswith("Generated"):
            fails.append(f"{sid}: /place: {m.string.strip()}")
            continue
        e = ENTRANCE.search("".join(ctx.seen[before:]))
        if not e:
            fails.append(f"{sid}: no está en el log dónde quedó la boca")
            continue
        bx, feet, bz, turn = int(e.group(1)), int(e.group(2)), int(e.group(3)), e.group(4)
        rot = TURNS[turn]

        def world(p):
            dx, dz = rot(p[0], p[2])
            return bx + dx, feet - 1 + p[1], bz + dz
        print(f"{sid}: boca en {bx} {feet} {bz}, giro {turn}, /place en {timings[-1]:.1f} s")
        if not ctx.until(f"execute if block {' '.join(map(str, world((0, 1, 0))))} #minecraft:rails", timeout=60):
            fails.append(f"{sid}: sin vía bajo el dintel")
            continue
        for p in ((2, 1, 0), (-2, 1, 0)):
            if not ctx.block(world(p), "#minecraft:logs"):
                fails.append(f"{sid}: falta el poste de la boca {p}")
        # la vía, raíl a raíl, del patio al final del tronco
        get = lambda x, y, z: o.t.get(x, y, z)
        for ini, direction, _ in o.tracks:
            _, road = traverse(get, ini, direction, steps=2000)
            bad_many = [p for p in road if not ctx.block(world(p), "#minecraft:rails")]
            if bad_many:
                fails.append(f"{sid}: {len(bad_many)} raíles de {len(road)} no están, p. ej. {bad_many[0]}")
            back = min(p[1] for p in road)
            print(f"{sid}: vía de {len(road)} raíles, del patio a {back - 1} bajo el suelo de la boca")
        # la galería: aire a la altura de la cabeza, casco encima y bajo el suelo de la boca
        for (x, y, z) in o.nodes:
            head, shell = world((x, y + 2, z)), world((x, y + 6, z))
            if not ctx.block(head, "minecraft:air") or ctx.block(shell, "minecraft:air") or head[1] > feet - 8:
                fails.append(f"{sid}: el cruce {x, y, z} no está excavado bajo tierra ({head})")
                break
        for (x, y, z), tbl in o.cofres:
            st = o.t.get(x, y, z).split("[")[0]
            if not ctx.block(world((x, y, z)), f"{st}{{LootTable:\"heraldia:minas/{tbl}\"}}"):
                if not ctx.test(f"execute if entity @e[type=minecraft:chest_minecart,x={world((x, y, z))[0]},"
                                f"y={world((x, y, z))[1]},z={world((x, y, z))[2]},distance=..2]"):
                    fails.append(f"{sid}: falta el cofre {tbl} en {(x, y, z)}")
        box = f"x={bx - 110},y={feet - 50},z={bz - 110},dx=220,dy=80,dz=220"
        expected_counts = {"minecraft:minecart": 0, "minecraft:chest_minecart": 0, "minecraft:cave_spider": 0}
        for *_, n in o.t.entities:
            expected_counts[n["id"]] += 1
        for kind, n in expected_counts.items():
            if n and not ctx.until(f"execute if entity @e[type={kind},{box}]", timeout=30):
                fails.append(f"{sid}: no aparece {kind}")
            elif n and ctx.count(f"@e[type={kind},{box}]") < n:
                fails.append(f"{sid}: {ctx.count(f'@e[type={kind},{box}]')} {kind}, esperadas {n}")
        for g in o.generators:
            if not ctx.block(world(g), "minecraft:spawner"):
                fails.append(f"{sid}: falta el generador de arañas en {g}")
        forceload(ctx, px - 112, pz - 112, px + 111, pz + 111, remove=True)
    print(f"/place de las entradas: {', '.join(f'{t:.1f} s' for t in timings)}")
    return fails


def check_loot(ctx):
    fails = []
    forceload(ctx, PLACE_X, PLACE_Z - 600, PLACE_X, PLACE_Z - 600)
    for tbl in mines.LOOT:
        m = ctx.run(f"loot spawn {PLACE_X} 120 {PLACE_Z - 600} loot heraldia:minas/{tbl}", r"Dropped \d+|No items")
        if not m.group(0).startswith("Dropped"):
            fails.append(f"loot heraldia:minas/{tbl}: {m.string.strip()}")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    forceload(ctx, PLACE_X, PLACE_Z - 600, PLACE_X, PLACE_Z - 600, remove=True)
    return fails


def info_cerca(ctx, x, z, radius):
    m = ctx.run(f"execute positioned {x} 64 {z} run heraldia info nearby {radius}", r"info nearby \d+ en [^:]+: \d+ estructuras en (\d+) ms")
    if not m.lastindex:
        return None
    return {g[0]: (int(g[1]), int(g[2]), int(g[3])) for g in s.INFO_LINE.findall("".join(s.drain(ctx)))}


def generated(ctx, x, z, size):
    end = time.monotonic() + s.UNTIL_S
    while time.monotonic() < end:
        for dx, dz in ((0, 0), (8, 8), (-8, 8), (8, -8), (-8, -8)):
            for dy in (-2, -8, -14):
                m = ctx.run(f"execute positioned {x + dx} 0 {z + dz} positioned over world_surface positioned ~ ~{dy} ~ "
                            f"run heraldia info here", r"\((heraldia:[^)]+)\)|no hay ninguna|no Heraldia|not loaded|no está cargada")
                if m.group(1) and f"minas/{size}/" in m.group(1):
                    return m.group(1)
        time.sleep(2)
    return None


def check_locate(ctx):
    fails, timings = [], []
    for size in mines.SIZES:
        t0 = time.monotonic()
        m = ctx.run(f"execute positioned 0 64 0 run locate structure #heraldia:minas/{size}",
                    r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
        timings.append(time.monotonic() - t0)
        if not m.group(1):
            fails.append(f"/locate no encuentra ninguna mina {size}")
            continue
        x, z = int(m.group(1)), int(m.group(2))
        d = math.hypot(x, z)
        print(f"mina {size}: /locate en {x}, {z} a {d:.0f} bloques ({timings[-1]:.1f} s)")
        if d > LOCATE_MAX[size]:
            fails.append(f"mina {size} a {d:.0f} bloques (> {LOCATE_MAX[size]})")
        nearby_flag = info_cerca(ctx, x, z, 600) or {}
        for sid, (dist, *_) in nearby_flag.items():
            if ":minas/" in sid:                       # prevista: heraldia:minas/<tamaño>; generada, con su estilo
                if not (sid.endswith(f"minas/{size}") or f"minas/{size}/" in sid) and dist < DISTANCE:
                    fails.append(f"mina {size} en {x}, {z} a {dist} bloques de {sid} (< {DISTANCE})")
            elif ":medianas/" in sid:
                if dist < DISTANCE:
                    fails.append(f"mina {size} en {x}, {z} a {dist} bloques de la mediana {sid} (< {DISTANCE})")
            elif dist < ZONE:
                fails.append(f"mina {size} en {x}, {z} a {dist} bloques de {sid} (< {ZONE})")
        forceload(ctx, x - 48, z - 48, x + 47, z + 47)
        sid = generated(ctx, x, z, size)
        if not sid:
            fails.append(f"mina {size}: /locate da {x}, {z} pero ahí no se ha generado")
        else:
            print(f"mina {size}: generada de verdad ({sid})")
        forceload(ctx, x - 48, z - 48, x + 47, z + 47, remove=True)
    if timings:
        print(f"/locate de minas: media {sum(timings) / len(timings):.1f} s, máxima {max(timings):.1f} s")
    return fails


def check_locate_far(ctx):
    """/locate desde LOCATE_DESDE: el tiempo que dice el juego y que encuentra lo mismo que la 0.1.0."""
    fails, (x0, z0) = [], LOCATE_FROM
    for target, expected in LOCATE_FAR.items():
        s.pending(ctx.lines, ctx.seen)
        s.send(ctx.proc, f"execute positioned {x0} 64 {z0} run locate structure {target}")
        ms, pos = None, None
        while ms is None or pos is None:
            m = s.wait_for(ctx.lines, _LOCATE_MS.pattern + r"|is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find|" + s.ERROR_PATTERN,
                           s.COMMAND_TIMEOUT_S, ctx.seen)
            if m.group(0).startswith("Locating element"):
                ms = int(m.group(2))
            elif m.group(0).startswith("is at"):
                pos = (int(m.group(3)), int(m.group(4)))
            else:
                pos, ms = "nada", ms if ms is not None else -1
        print(f"/locate {target} desde {x0}, {z0}: {ms} ms -> {pos}")
        if pos != expected:
            fails.append(f"/locate {target} desde {x0}, {z0}: {pos}, la 0.1.0 daba {expected}")
        if target == "#heraldia:minas" and ms > LOCATE_FAR_MS:
            fails.append(f"/locate {target} desde {x0}, {z0} tarda {ms} ms (> {LOCATE_FAR_MS})")
    return fails


def check_log(ctx, multiplier):
    fails, log = [], ctx.log()
    for size in mines.SIZES:
        sp = round(mines.SEPARATION[size] / 16)
        if not re.search(rf"rejilla minas/{size}: activada, cada {sp} chunks \(separación mínima {(DISTANCE + 15) // 16}, "
                         r"origen desplazado\)[^\n]*candidata en el bioma #heraldia:minas", log):
            fails.append(f"falta en el log la rejilla de minas/{size} (cada {sp} chunks)")
    freq = float_str(f32(f32(0.004) * multiplier) if multiplier != 1 else f32(0.004))
    if not re.search(rf"minas abandonadas vanilla: frecuencia {re.escape(freq)} ", log):
        fails.append(f"falta en el log la frecuencia de las minas vanilla ({freq})")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-minas"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    jar, world = os.path.abspath(a.jar), os.path.join(a.work, "world")
    fails = []
    proc, ctx = start_up(a.work, jar, {"minas": {"vanilla": {"multiplicador": 1}}}, True)
    try:
        seed = int(ctx.run("seed", r"Seed: \[(-?\d+)\]").group(1))
        (ax, az, a1, a5), (bx, bz, b1, b5) = choose_zones(seed)
        print(f"semilla {seed}; zona A en el chunk {ax}, {az} ({len(a1)} minas vanilla, {len(a5)} con x5); "
              f"zona B en {bx}, {bz} ({len(b1)} y {len(b5)})")
        fails += check_log(ctx, 1)
        fails += check_locate_far(ctx)          # lo primero: el /locate con el servidor recién arrancado
        fails += check_placed(ctx)
        fails += check_loot(ctx)
        fails += check_locate(ctx)
        if not re.search(r"entradas a mina: activadas, 3 tamaños, cada 768 bloques las pequeñas, a 256 bloques de aldeas y "
                         r"únicas y a 192 de las medianas y entre ellas", ctx.log()):
            fails.append("falta en el log la regla de las entradas a mina")
        m = ctx.run("heraldia info", r"Registered structures: \d+ \(\d+ villages, \d+ unique, \d+ medium and (\d+) mine|"
                                     r"Estructuras registradas: \d+ \(\d+ de aldeas, \d+ únicas, \d+ medianas y (\d+) ")
        n = (m.group(1) or m.group(2)) if m.lastindex else None
        if n is None or int(n) != len(mines.structures()):
            fails.append(f"/heraldia info: {n} entradas a mina registradas, esperadas {len(mines.structures())}")
        if not re.search(r"Mine entrances: enabled, every 768 blocks|Entradas a mina: activada, cada 768", "".join(ctx.seen[-40:])):
            fails.append("/heraldia info no resume las minas")
        t0 = time.monotonic()
        if not generate_zone(ctx, ax, az):
            fails.append("la zona A no se genera")
        print(f"zona A generada en {time.monotonic() - t0:.0f} s")
    finally:
        halt(proc)
    saved_to, missing = saved_mines(world, ax, az)
    if missing:
        fails.append(f"zona A: {len(missing)} chunks sin generar del todo")
    if not saved_to <= a1:
        fails.append(f"zona A con x1: minas fuera del sorteo vanilla: {sorted(saved_to - a1)}")
    if not saved_to:
        fails.append("zona A sin ninguna mina vanilla (se esperaban las del sorteo)")
    print(f"zona A (x1): {len(saved_to)} minas {sorted(saved_to)}")
    # segundo arranque, x5: lo generado no cambia; lo nuevo, con más minas
    proc, ctx = start_up(a.work, jar, {"minas": {"vanilla": {"multiplicador": 5}}}, False)
    try:
        fails += check_log(ctx, 5)
        t0 = time.monotonic()
        if not generate_zone(ctx, bx, bz):
            fails.append("la zona B no se genera")
        print(f"zona B generada en {time.monotonic() - t0:.0f} s")
    finally:
        halt(proc)
    saved_to2, _ = saved_mines(world, ax, az)
    if saved_to2 != saved_to:
        fails.append(f"la zona A ya generada cambió con x5: {sorted(saved_to)} -> {sorted(saved_to2)}")
    saved_to_b, missing = saved_mines(world, bx, bz)
    if missing:
        fails.append(f"zona B: {len(missing)} chunks sin generar del todo")
    new_ones = saved_to_b - b1
    print(f"zona B (x5): {len(saved_to_b)} minas, {len(new_ones)} que con x1 no saldrían")
    if not saved_to_b <= b5:
        fails.append(f"zona B con x5: minas fuera del sorteo: {sorted(saved_to_b - b5)}")
    if not new_ones:
        fails.append("zona B con x5: ninguna mina de más")
    print("MINAS:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
