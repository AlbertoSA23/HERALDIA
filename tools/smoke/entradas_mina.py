"""Entradas a mina (tools/gen/minas) y minas vanilla multiplicadas en un servidor dedicado 26.3 real (determinista: semilla
fija de server_smoke y zonas elegidas de antemano).

Uso: python3 tools/smoke/entradas_mina.py --jar build/libs/heraldia-X.jar [--work build/smoke-entradas-mina]
Dos arranques del mismo mundo:
1. minas.vanilla.multiplicador = 1 (la colocación vanilla exacta):
   - el log: la rejilla de cada tamaño (separación, búsqueda de bioma), la regla de las minas y la frecuencia vanilla;
   - /place structure de un estilo de cada tamaño: la boca (vía bajo el dintel y postes), la vía entera del patio al
     último cruce del tronco (cada raíl de la plantilla en su sitio con el giro elegido), los cruces de la galería bajo
     tierra (aire a la altura de la cabeza y casco encima, por debajo del suelo de la boca), cada cofre con su tabla
     heraldia:minas/<tabla>, la vagoneta de carga, las arañas de la mediana y el generador de la grande;
   - loot spawn de cada tabla;
   - /locate de cada tamaño desde el 0,0, que la genera de verdad (forceload) donde dijo /locate, y /heraldia info cerca
     desde allí: ninguna aldea ni única a menos de medianas.distancia_aldeas_unicas_bloques, ni otra mina de otro tamaño
     ni una mediana a menos de medianas.distancia_minima.bloques;
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
import minas                                    # noqa: E402  (el generador: plantillas, botín y su vía)
from unicas.mina_perdida.vias import recorrer  # noqa: E402

PLACE_X, PLACE_Z, PASO = 40000, 40000, 320      # /place de cada tamaño, lejos de todo
ESTILO = "montana"
LOCATE_MAX = {"pequena": 6000, "mediana": 9000, "grande": 20000}   # bloques desde el 0,0 (cada 768, 1.152 y 1.920, en laderas)
ZONA, DISTANCIA = 256, 192                       # opciones.py, por defecto
LADO = 12                                        # chunks de lado de las zonas A y B
GIROS = {"NONE": lambda x, z: (x, z), "CLOCKWISE_90": lambda x, z: (-z, x), "CLOCKWISE_180": lambda x, z: (-x, -z),
         "COUNTERCLOCKWISE_90": lambda x, z: (z, -x)}
ENTRADA = re.compile(r"entrada a mina en (-?\d+) (-?\d+) (-?\d+) \(giro (\w+)")


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


def sale_vanilla(seed, x, z, frecuencia):
    """legacyProbabilityReducerWithDouble: setLargeFeatureSeed(seed, x, z) y nextDouble() < frecuencia (float)."""
    r = Lcg(seed)
    a, b = r.next_long(), r.next_long()
    r.set(s64(s64(x * a) ^ s64(z * b) ^ seed))
    return r.next_double() < frecuencia


def f32(v):
    return struct.unpack("f", struct.pack("f", v))[0]


def float_str(v):
    """Float.toString de Java: los menos dígitos que vuelven al mismo float."""
    for d in range(1, 10):
        t = f"{v:.{d}g}"
        if f32(float(t)) == v:
            return t if "." in t or "e" in t else t + ".0"
    return repr(v)


def prediccion(seed, cx0, cz0, frecuencia):
    return {(x, z) for x in range(cx0, cx0 + LADO) for z in range(cz0, cz0 + LADO) if sale_vanilla(seed, x, z, frecuencia)}


def elegir_zonas(seed):
    """Zona A (con alguna mina vanilla y alguna que solo saldría con x5) y zona B (con al menos 3 de x5 de más)."""
    f1, f5 = f32(0.004), f32(f32(0.004) * 5.0)
    zonas = []
    for k in range(60):
        cx0, cz0 = 1500 + k * (LADO + 4), -1500
        p1, p5 = prediccion(seed, cx0, cz0, f1), prediccion(seed, cx0, cz0, f5)
        zonas.append((cx0, cz0, p1, p5))
    a = next(z for z in zonas if len(z[2]) >= 1 and len(z[3] - z[2]) >= 2)
    b = next(z for z in zonas if z is not a and len(z[3] - z[2]) >= 3)
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


def minas_guardadas(world, cx0, cz0):
    """Chunks de la zona con un inicio de mina vanilla guardado, y los que no están generados del todo."""
    out, faltan = set(), []
    for x in range(cx0, cx0 + LADO):
        for z in range(cz0, cz0 + LADO):
            n = chunk_nbt(world, x, z)
            if n is None or str(n.get("Status", "")) not in ("minecraft:full", "full"):
                faltan.append((x, z))
                continue
            starts = (n.get("structures") or {}).get("starts") or {}
            for sid in ("minecraft:mineshaft", "minecraft:mineshaft_mesa"):
                st = starts.get(sid)
                if st is not None and str(st.get("id", "INVALID")) != "INVALID":
                    out.add((x, z))
    return out, faltan


# ------------------------------------------------------------------ servidor
def arrancar(work, jar, cfg, limpiar):
    launcher = s.prepare(work, jar, s.gradle_properties()) if limpiar else os.path.join(work, glob.glob(
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


def parar(proc):
    if proc.poll() is None:
        s.send(proc, "stop")
        proc.wait(timeout=180)


def forceload(ctx, x0, z0, x1, z1, quitar=False):
    ctx.run(f"forceload {'remove' if quitar else 'add'} {x0} {z0} {x1} {z1}", r"Marked|[Aa]dded|[Rr]emoved|force|already|[Uu]nmarked")


def generar_zona(ctx, cx0, cz0):
    x0, z0, x1, z1 = cx0 * 16, cz0 * 16, (cx0 + LADO) * 16 - 1, (cz0 + LADO) * 16 - 1
    forceload(ctx, x0, z0, x1, z1)
    for x, z in ((x0, z0), (x1, z1), (x0, z1), (x1, z0)):
        if not ctx.until(f"execute if loaded {x} 64 {z}", timeout=300):
            return False
    ctx.ticks(40)
    forceload(ctx, x0, z0, x1, z1, quitar=True)
    ctx.run("save-all flush", r"Saved the game|saved")
    return True


# ------------------------------------------------------------------ entradas colocadas
def comprobar_colocadas(ctx):
    fails, tiempos = [], []
    for k, tam in enumerate(minas.TAMANOS):
        o, _, _ = minas.obra(tam, ESTILO, "a")
        sid = minas.plantilla(tam, ESTILO, "a")
        px, pz = PLACE_X + k * PASO, PLACE_Z
        forceload(ctx, px - 112, pz - 112, px + 111, pz + 111)
        antes = len(ctx.seen)
        t0 = time.monotonic()
        m = ctx.run(f"place structure heraldia:{sid} {px} 100 {pz}", r"Generated structure|Failed to place")
        tiempos.append(time.monotonic() - t0)
        if not m.group(0).startswith("Generated"):
            fails.append(f"{sid}: /place: {m.string.strip()}")
            continue
        e = ENTRADA.search("".join(ctx.seen[antes:]))
        if not e:
            fails.append(f"{sid}: no está en el log dónde quedó la boca")
            continue
        bx, pies, bz, giro = int(e.group(1)), int(e.group(2)), int(e.group(3)), e.group(4)
        rot = GIROS[giro]

        def mundo(p):
            dx, dz = rot(p[0], p[2])
            return bx + dx, pies - 1 + p[1], bz + dz
        print(f"{sid}: boca en {bx} {pies} {bz}, giro {giro}, /place en {tiempos[-1]:.1f} s")
        if not ctx.until(f"execute if block {' '.join(map(str, mundo((0, 1, 0))))} #minecraft:rails", timeout=60):
            fails.append(f"{sid}: sin vía bajo el dintel")
            continue
        for p in ((2, 1, 0), (-2, 1, 0)):
            if not ctx.block(mundo(p), "#minecraft:logs"):
                fails.append(f"{sid}: falta el poste de la boca {p}")
        # la vía, raíl a raíl, del patio al final del tronco
        get = lambda x, y, z: o.t.get(x, y, z)
        for ini, sentido, _ in o.vias:
            _, camino = recorrer(get, ini, sentido, pasos=2000)
            malos = [p for p in camino if not ctx.block(mundo(p), "#minecraft:rails")]
            if malos:
                fails.append(f"{sid}: {len(malos)} raíles de {len(camino)} no están, p. ej. {malos[0]}")
            fondo = min(p[1] for p in camino)
            print(f"{sid}: vía de {len(camino)} raíles, del patio a {fondo - 1} bajo el suelo de la boca")
        # la galería: aire a la altura de la cabeza, casco encima y bajo el suelo de la boca
        for (x, y, z) in o.nodos:
            cabeza, casco = mundo((x, y + 2, z)), mundo((x, y + 6, z))
            if not ctx.block(cabeza, "minecraft:air") or ctx.block(casco, "minecraft:air") or cabeza[1] > pies - 8:
                fails.append(f"{sid}: el cruce {x, y, z} no está excavado bajo tierra ({cabeza})")
                break
        for (x, y, z), tabla in o.cofres:
            st = o.t.get(x, y, z).split("[")[0]
            if not ctx.block(mundo((x, y, z)), f"{st}{{LootTable:\"heraldia:minas/{tabla}\"}}"):
                if not ctx.test(f"execute if entity @e[type=minecraft:chest_minecart,x={mundo((x, y, z))[0]},"
                                f"y={mundo((x, y, z))[1]},z={mundo((x, y, z))[2]},distance=..2]"):
                    fails.append(f"{sid}: falta el cofre {tabla} en {(x, y, z)}")
        caja = f"x={bx - 110},y={pies - 50},z={bz - 110},dx=220,dy=80,dz=220"
        esperadas = {"minecraft:minecart": 0, "minecraft:chest_minecart": 0, "minecraft:cave_spider": 0}
        for *_, n in o.t.entities:
            esperadas[n["id"]] += 1
        for tipo, n in esperadas.items():
            if n and not ctx.until(f"execute if entity @e[type={tipo},{caja}]", timeout=30):
                fails.append(f"{sid}: no aparece {tipo}")
            elif n and ctx.count(f"@e[type={tipo},{caja}]") < n:
                fails.append(f"{sid}: {ctx.count(f'@e[type={tipo},{caja}]')} {tipo}, esperadas {n}")
        for g in o.generadores:
            if not ctx.block(mundo(g), "minecraft:spawner"):
                fails.append(f"{sid}: falta el generador de arañas en {g}")
        forceload(ctx, px - 112, pz - 112, px + 111, pz + 111, quitar=True)
    print(f"/place de las entradas: {', '.join(f'{t:.1f} s' for t in tiempos)}")
    return fails


def comprobar_botin(ctx):
    fails = []
    forceload(ctx, PLACE_X, PLACE_Z - 600, PLACE_X, PLACE_Z - 600)
    for tabla in minas.LOOT:
        m = ctx.run(f"loot spawn {PLACE_X} 120 {PLACE_Z - 600} loot heraldia:minas/{tabla}", r"Dropped \d+|No items")
        if not m.group(0).startswith("Dropped"):
            fails.append(f"loot heraldia:minas/{tabla}: {m.string.strip()}")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    forceload(ctx, PLACE_X, PLACE_Z - 600, PLACE_X, PLACE_Z - 600, quitar=True)
    return fails


def info_cerca(ctx, x, z, radio):
    m = ctx.run(f"execute positioned {x} 64 {z} run heraldia info cerca {radio}", r"info cerca \d+ en [^:]+: \d+ estructuras en (\d+) ms")
    if not m.lastindex:
        return None
    return {g[0]: (int(g[1]), int(g[2]), int(g[3])) for g in s.INFO_LINE.findall("".join(s.drain(ctx)))}


def generada(ctx, x, z, tam):
    end = time.monotonic() + s.UNTIL_S
    while time.monotonic() < end:
        for dx, dz in ((0, 0), (8, 8), (-8, 8), (8, -8), (-8, -8)):
            for dy in (-2, -8, -14):
                m = ctx.run(f"execute positioned {x + dx} 0 {z + dz} positioned over world_surface positioned ~ ~{dy} ~ "
                            f"run heraldia info aqui", r"\((heraldia:[^)]+)\)|no hay ninguna|no Heraldia|not loaded|no está cargada")
                if m.group(1) and f"minas/{tam}/" in m.group(1):
                    return m.group(1)
        time.sleep(2)
    return None


def comprobar_locate(ctx):
    fails, tiempos = [], []
    for tam in minas.TAMANOS:
        t0 = time.monotonic()
        m = ctx.run(f"execute positioned 0 64 0 run locate structure #heraldia:minas/{tam}",
                    r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
        tiempos.append(time.monotonic() - t0)
        if not m.group(1):
            fails.append(f"/locate no encuentra ninguna mina {tam}")
            continue
        x, z = int(m.group(1)), int(m.group(2))
        d = math.hypot(x, z)
        print(f"mina {tam}: /locate en {x}, {z} a {d:.0f} bloques ({tiempos[-1]:.1f} s)")
        if d > LOCATE_MAX[tam]:
            fails.append(f"mina {tam} a {d:.0f} bloques (> {LOCATE_MAX[tam]})")
        cerca = info_cerca(ctx, x, z, 600) or {}
        for sid, (dist, *_) in cerca.items():
            if ":minas/" in sid:                       # prevista: heraldia:minas/<tamaño>; generada, con su estilo
                if not (sid.endswith(f"minas/{tam}") or f"minas/{tam}/" in sid) and dist < DISTANCIA:
                    fails.append(f"mina {tam} en {x}, {z} a {dist} bloques de {sid} (< {DISTANCIA})")
            elif ":medianas/" in sid:
                if dist < DISTANCIA:
                    fails.append(f"mina {tam} en {x}, {z} a {dist} bloques de la mediana {sid} (< {DISTANCIA})")
            elif dist < ZONA:
                fails.append(f"mina {tam} en {x}, {z} a {dist} bloques de {sid} (< {ZONA})")
        forceload(ctx, x - 48, z - 48, x + 47, z + 47)
        sid = generada(ctx, x, z, tam)
        if not sid:
            fails.append(f"mina {tam}: /locate da {x}, {z} pero ahí no se ha generado")
        else:
            print(f"mina {tam}: generada de verdad ({sid})")
        forceload(ctx, x - 48, z - 48, x + 47, z + 47, quitar=True)
    if tiempos:
        print(f"/locate de minas: media {sum(tiempos) / len(tiempos):.1f} s, máxima {max(tiempos):.1f} s")
    return fails


def comprobar_log(ctx, multiplicador):
    fails, log = [], ctx.log()
    for tam in minas.TAMANOS:
        sp = round(minas.SEPARACION[tam] / 16)
        if not re.search(rf"rejilla minas/{tam}: activada, cada {sp} chunks \(separación mínima {(DISTANCIA + 15) // 16}, "
                         r"origen desplazado\)[^\n]*candidata en el bioma #heraldia:minas", log):
            fails.append(f"falta en el log la rejilla de minas/{tam} (cada {sp} chunks)")
    frec = float_str(f32(f32(0.004) * multiplicador) if multiplicador != 1 else f32(0.004))
    if not re.search(rf"minas abandonadas vanilla: frecuencia {re.escape(frec)} ", log):
        fails.append(f"falta en el log la frecuencia de las minas vanilla ({frec})")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-minas"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    jar, world = os.path.abspath(a.jar), os.path.join(a.work, "world")
    fails = []
    proc, ctx = arrancar(a.work, jar, {"minas": {"vanilla": {"multiplicador": 1}}}, True)
    try:
        seed = int(ctx.run("seed", r"Seed: \[(-?\d+)\]").group(1))
        (ax, az, a1, a5), (bx, bz, b1, b5) = elegir_zonas(seed)
        print(f"semilla {seed}; zona A en el chunk {ax}, {az} ({len(a1)} minas vanilla, {len(a5)} con x5); "
              f"zona B en {bx}, {bz} ({len(b1)} y {len(b5)})")
        fails += comprobar_log(ctx, 1)
        fails += comprobar_colocadas(ctx)
        fails += comprobar_botin(ctx)
        fails += comprobar_locate(ctx)
        if not re.search(r"entradas a mina: activadas, 3 tamaños, cada 768 bloques las pequeñas, a 256 bloques de aldeas y "
                         r"únicas y a 192 de las medianas y entre ellas", ctx.log()):
            fails.append("falta en el log la regla de las entradas a mina")
        m = ctx.run("heraldia info", r"Registered structures: \d+ \(\d+ villages, \d+ unique, \d+ medium and (\d+) mine|"
                                     r"Estructuras registradas: \d+ \(\d+ de aldeas, \d+ únicas, \d+ medianas y (\d+) ")
        n = (m.group(1) or m.group(2)) if m.lastindex else None
        if n is None or int(n) != len(minas.estructuras()):
            fails.append(f"/heraldia info: {n} entradas a mina registradas, esperadas {len(minas.estructuras())}")
        if not re.search(r"Mine entrances: enabled, every 768 blocks|Entradas a mina: activada, cada 768", "".join(ctx.seen[-40:])):
            fails.append("/heraldia info no resume las minas")
        t0 = time.monotonic()
        if not generar_zona(ctx, ax, az):
            fails.append("la zona A no se genera")
        print(f"zona A generada en {time.monotonic() - t0:.0f} s")
    finally:
        parar(proc)
    guardadas_a, faltan = minas_guardadas(world, ax, az)
    if faltan:
        fails.append(f"zona A: {len(faltan)} chunks sin generar del todo")
    if not guardadas_a <= a1:
        fails.append(f"zona A con x1: minas fuera del sorteo vanilla: {sorted(guardadas_a - a1)}")
    if not guardadas_a:
        fails.append("zona A sin ninguna mina vanilla (se esperaban las del sorteo)")
    print(f"zona A (x1): {len(guardadas_a)} minas {sorted(guardadas_a)}")
    # segundo arranque, x5: lo generado no cambia; lo nuevo, con más minas
    proc, ctx = arrancar(a.work, jar, {"minas": {"vanilla": {"multiplicador": 5}}}, False)
    try:
        fails += comprobar_log(ctx, 5)
        t0 = time.monotonic()
        if not generar_zona(ctx, bx, bz):
            fails.append("la zona B no se genera")
        print(f"zona B generada en {time.monotonic() - t0:.0f} s")
    finally:
        parar(proc)
    guardadas_a2, _ = minas_guardadas(world, ax, az)
    if guardadas_a2 != guardadas_a:
        fails.append(f"la zona A ya generada cambió con x5: {sorted(guardadas_a)} -> {sorted(guardadas_a2)}")
    guardadas_b, faltan = minas_guardadas(world, bx, bz)
    if faltan:
        fails.append(f"zona B: {len(faltan)} chunks sin generar del todo")
    nuevas = guardadas_b - b1
    print(f"zona B (x5): {len(guardadas_b)} minas, {len(nuevas)} que con x1 no saldrían")
    if not guardadas_b <= b5:
        fails.append(f"zona B con x5: minas fuera del sorteo: {sorted(guardadas_b - b5)}")
    if not nuevas:
        fails.append("zona B con x5: ninguna mina de más")
    print("MINAS:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
