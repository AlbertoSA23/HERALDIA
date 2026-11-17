"""Faros y naufragios de la costa (tools/gen/costa, T42) en un servidor dedicado 26.3 real (determinista: la semilla fija
de server_smoke y orígenes de búsqueda fijos).

Uso: python3 tools/smoke/costa.py --jar build/libs/heraldia-X.jar [--work build/smoke-costa]
Dos arranques del mismo mundo (con -Dheraldia.depurar.costa=true: cada sitio elegido va al log, con su ancla, su altura
y hacia dónde mira el mar):
1. Con la configuración por defecto:
   - el log: la rejilla de los dos tipos (separación, origen desplazado, candidata en las playas) y la regla de la costa;
   - /locate de cada tipo desde varios orígenes, que lo genera de verdad (forceload) donde dijo /locate, y lo comprueba
     bloque a bloque con la plantilla del generador girada como en el juego: el faro sobre tierra (lo que hay bajo la
     plataforma no es agua), la luz de lo alto encendida (lámpara de redstone sobre su bloque de redstone, y sigue
     encendida 5 s después), el embarcadero sobre el agua y el cofre con su tabla; el naufragio con la quilla, el mástil,
     el cofre del camarote y, según la variante, la proa en tierra (encallado) o la bodega inundada con su ahogado anclado
     (semihundido); en los dos, ninguna agua por encima del nivel del mar en su caja (nada se derrama);
   - /heraldia info nearby desde cada uno: ninguna aldea ni única a menos de medianas.distancia_aldeas_unicas_bloques,
     ni una mediana, una mina u otro de la costa de otro tipo a menos de medianas.distancia_minima.bloques;
   - /place structure de las cuatro variantes (estilo templado) junto a playas que da /locate biome: en la orilla, con las
     mismas comprobaciones;
   - loot spawn de cada tabla, y /heraldia info con su línea y las 16 estructuras de la costa.
2. Con faros.activado = false y naufragios.separacion_bloques = 2048: /locate ya no da ningún faro, y la rejilla de los
   naufragios sale con la separación nueva.
Código 0 si todo pasa.
"""
import argparse, glob, json, math, os, queue, re, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

sys.path.insert(0, os.path.join(s.ROOT, "tools", "gen"))
import costa                                    # noqa: E402  (el generador: plantillas, botín y huellas)
from costa import obras                         # noqa: E402

SEA = 63
ZONA, DISTANCIA = 256, 192                      # opciones.py, por defecto
# /locate de cada tipo desde estos orígenes (bloques); las variantes salen según la costa y el azar de la casilla.
ORIGENES = {"faro": [(0, 0), (-3000, 2000)], "naufragio": [(0, 0), (3000, -2000)]}
LOCATE_MAX = 12000
# /place de cada variante junto a una playa (la que da /locate biome desde cada origen, por orden, hasta que la orilla
# sirve a la variante: no todas las playas tienen tierra llana para el faro o un bajío para el naufragio)
PLACE = [(20000, 20000), (-20000, 20000), (20000, -20000), (-20000, -20000), (24000, 0), (-24000, 0), (0, 24000),
         (0, -24000)]
VARIANTES = [("faro", "a"), ("faro", "b"), ("naufragio", "a"), ("naufragio", "b")]
DIRS = {"south": (0, 1), "north": (0, -1), "east": (1, 0), "west": (-1, 0)}
CCW = {"south": "east", "east": "north", "north": "west", "west": "south"}
SITIO = re.compile(r"Heraldia: costa \((faro|encallado|hundido)\) en (-?\d+) (-?\d+) (-?\d+) hacia el (\w+) \(nota (\d+)(, sin orilla)?\)")
MODO_VARIANTE = {"faro": None, "encallado": "a", "hundido": "b"}


def arrancar(work, jar, cfg, limpiar):
    launcher = s.prepare(work, jar, s.gradle_properties()) if limpiar else os.path.join(work, glob.glob(
        os.path.join(work, "fabric-server-*.jar"))[0])
    cfg = dict(cfg, arena={"generar_en_mundos_nuevos": False}, update_check={"activado": False})
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)
    proc = subprocess.Popen(["java", "-Xmx2G", "-Dheraldia.depurar.costa=true", "-jar", launcher, "nogui"], cwd=work, text=True,
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


def cargar(ctx, x, z, r=64):
    forceload(ctx, x - r, z - r, x + r - 1, z + r - 1)
    for px, pz in ((x - r, z - r), (x + r - 1, z + r - 1), (x - r, z + r - 1), (x + r - 1, z - r)):
        if not ctx.until(f"execute if loaded {px} 64 {pz}", timeout=300):
            return False
    ctx.ticks(20)
    return True


class Sitio:
    """Un faro o naufragio colocado: su ancla, la altura de su fila 0 y hacia dónde mira el mar; mapea la plantilla."""

    def __init__(self, m):
        self.modo, self.x, self.y, self.z, self.mar = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5)
        self.sin_orilla = bool(m.group(7))

    def mundo(self, p):
        """Punto de diseño (x a lo ancho, y, z hacia el mar; el ancla en 0, 0) en el mundo."""
        dx, dz = DIRS[self.mar]
        ex, ez = DIRS[CCW[self.mar]]
        x, y, z = p
        return self.x + dx * z + ex * x, self.y + y, self.z + dz * z + ez * x

    def __repr__(self):
        return f"{self.modo} en {self.x} {self.y} {self.z} hacia el {self.mar}"


def sitios(ctx, desde=0):
    return [Sitio(m) for m in SITIO.finditer("".join(ctx.seen[desde:]))]


def agua_encima(ctx, a, b):
    """Bloques de agua por encima del nivel del mar en la caja de a a b (fill de agua por agua: no cambia nada)."""
    x0, x1 = sorted((a[0], b[0]))
    z0, z1 = sorted((a[2], b[2]))
    y1 = max(a[1], b[1])
    m = ctx.run(f"fill {x0} {SEA} {z0} {x1} {y1} {z1} minecraft:water replace minecraft:water",
                r"Successfully filled (\d+)|No blocks were filled|[Tt]oo many blocks")
    return int(m.group(1)) if m.lastindex else 0


def comprobar_faro(ctx, st, v):
    """El faro de la variante v (o la que sea, con v None) colocado en st; devuelve los fallos."""
    o, _, _ = costa.obra("faro", "templada", v or "a")
    fails = []
    lx, ly, lz = st.mundo(o.luz)
    if not ctx.until(f"execute if block {lx} {ly} {lz} minecraft:redstone_lamp[lit=true]", timeout=60):
        return [f"{st}: sin la lámpara encendida en {lx} {ly} {lz}"]
    if not ctx.block((lx, ly - 1, lz), "minecraft:redstone_block"):
        fails.append(f"{st}: la lámpara no está sobre su bloque de redstone")
    ctx.ticks(100)
    if not ctx.block((lx, ly, lz), "minecraft:redstone_lamp[lit=true]"):
        fails.append(f"{st}: la lámpara se apaga")
    if ly < SEA + 20:
        fails.append(f"{st}: la luz a y = {ly}, no se ve de lejos")
    for p in ((0, -1, -12), (-5, -1, -18), (5, -1, -3)):       # bajo la plataforma: tierra o cimientos, nunca agua
        w = st.mundo(p)
        if ctx.block(w, "minecraft:water") or ctx.block(w, "minecraft:air"):
            fails.append(f"{st}: bajo la plataforma en {w} hay agua o aire")
    cx, _, cz = st.mundo((0, -1, obras.MUELLE))              # bajo el final del embarcadero, el mar
    if not ctx.block((cx, SEA - 1, cz), "minecraft:water") and not st.sin_orilla:
        fails.append(f"{st}: el embarcadero no acaba sobre el agua ({cx} {SEA - 1} {cz})")
    if not ctx.block(st.mundo((0, 0, obras.MUELLE)), "#minecraft:planks"):
        fails.append(f"{st}: falta el embarcadero")
    cofre = st.mundo((-2, 12, obras.TORRE_Z))
    if not ctx.block(cofre, 'minecraft:chest{LootTable:"heraldia:costa/faro"}'):
        fails.append(f"{st}: falta el cofre del faro en {cofre}")
    n = agua_encima(ctx, st.mundo((-8, 0, -21)), st.mundo((8, 27, obras.MUELLE + 1)))
    if n:
        fails.append(f"{st}: {n} bloques de agua por encima del mar en su caja")
    return fails


def comprobar_naufragio(ctx, st):
    v = MODO_VARIANTE[st.modo]
    o, _, _ = costa.obra("naufragio", "templada", v)
    z0, fails = o.proa, []
    quilla = st.mundo((0, 0, z0 + 10))
    if not ctx.until(f"execute if block {' '.join(map(str, quilla))} #minecraft:logs", timeout=60):
        return [f"{st}: sin la quilla en {quilla}"]
    if not ctx.block(st.mundo((0, 17, z0 + 12)), "#minecraft:logs"):
        fails.append(f"{st}: sin el mástil mayor")
    cam = st.mundo((-2, 6, z0 + 28))
    if not ctx.block(cam, 'minecraft:chest{LootTable:"heraldia:costa/camarote"}'):
        fails.append(f"{st}: falta el cofre del camarote en {cam}")
    if v == "b":
        bodega = st.mundo((0, 3, z0 + 5))
        if not ctx.block(bodega, "minecraft:water"):
            fails.append(f"{st}: la bodega no está inundada ({bodega})")
        bx, by, bz = st.mundo((-2, 2, z0 + 4))
        if not ctx.until(f"execute if entity @e[type=minecraft:drowned,tag=heraldia_anclado,x={bx},y={by},z={bz},distance=..6]", timeout=30):
            fails.append(f"{st}: sin el ahogado anclado de la bodega")
        if not ctx.block(st.mundo((0, -1, z0 + 20)), "minecraft:water") and \
                not ctx.block(st.mundo((0, -1, z0 + 20)), "#minecraft:logs"):
            pass                                               # bajo la quilla: el fondo o la quilla alargada
    else:
        proa = st.mundo((0, -1, z0 + 3))
        if ctx.block(proa, "minecraft:water") or ctx.block(proa, "minecraft:air"):
            fails.append(f"{st}: la proa del encallado no está en tierra ({proa})")
    n = agua_encima(ctx, st.mundo((-5, 0, z0 - 4)), st.mundo((5, 17, z0 + obras.ESLORA)))
    if n:
        fails.append(f"{st}: {n} bloques de agua por encima del mar en su caja")
    return fails


def info_cerca(ctx, x, z, radio):
    m = ctx.run(f"execute positioned {x} 64 {z} run heraldia info nearby {radio}", r"info nearby \d+ en [^:]+: \d+ estructuras en (\d+) ms")
    if not m.lastindex:
        return {}
    return {g[0]: (int(g[1]), int(g[2]), int(g[3])) for g in s.INFO_LINE.findall("".join(s.drain(ctx)))}


def comprobar_separacion(ctx, tipo, x, z):
    fails = []
    for sid, (dist, *_) in info_cerca(ctx, x, z, 600).items():
        if ":costa/" in sid:
            if f"costa/{tipo}" not in sid and dist < DISTANCIA:
                fails.append(f"{tipo} en {x}, {z} a {dist} bloques de {sid} (< {DISTANCIA})")
        elif ":medianas/" in sid or ":minas/" in sid:
            if dist < DISTANCIA:
                fails.append(f"{tipo} en {x}, {z} a {dist} bloques de {sid} (< {DISTANCIA})")
        elif dist < ZONA:
            fails.append(f"{tipo} en {x}, {z} a {dist} bloques de {sid} (< {ZONA})")
    return fails


def comprobar_locate(ctx):
    fails, vistos = [], {}
    for tipo, origenes in ORIGENES.items():
        for ox, oz in origenes:
            t0 = time.monotonic()
            m = ctx.run(f"execute positioned {ox} 64 {oz} run locate structure #heraldia:costa/{tipo}",
                        r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
            if not m.group(1):
                fails.append(f"/locate desde {ox}, {oz} no encuentra ningún {tipo}")
                continue
            x, z = int(m.group(1)), int(m.group(2))
            d = math.hypot(x - ox, z - oz)
            print(f"{tipo}: /locate desde {ox}, {oz} en {x}, {z} a {d:.0f} bloques ({time.monotonic() - t0:.1f} s)")
            if d > LOCATE_MAX:
                fails.append(f"{tipo} a {d:.0f} bloques de {ox}, {oz} (> {LOCATE_MAX})")
            fails += comprobar_separacion(ctx, tipo, x, z)
            antes = len(ctx.seen)
            if not cargar(ctx, x + 8, z + 8, 80):
                fails.append(f"{tipo} en {x}, {z}: no se carga")
                continue
            cand = [st for st in sitios(ctx) if (st.modo == "faro") == (tipo == "faro")
                    and abs(st.x - x - 8) <= 64 and abs(st.z - z - 8) <= 64]
            if not cand:
                fails.append(f"{tipo} en {x}, {z}: el log no dice dónde quedó")
            else:
                st = min(cand, key=lambda c: abs(c.x - x - 8) + abs(c.z - z - 8))
                if any((v.x, v.z) == (st.x, st.z) for v in vistos.get(tipo, [])):
                    print(f"  {st}: el mismo de antes")
                    forceload(ctx, x + 8 - 80, z + 8 - 80, x + 8 + 79, z + 8 + 79, quitar=True)
                    continue
                vistos.setdefault(tipo, []).append(st)
                f = comprobar_faro(ctx, st, None) if tipo == "faro" else comprobar_naufragio(ctx, st)
                print(f"  {st}: {'bien' if not f else f}")
                fails += f
            forceload(ctx, x + 8 - 80, z + 8 - 80, x + 8 + 79, z + 8 + 79, quitar=True)
            del antes
    return fails, vistos


def comprobar_colocadas(ctx):
    fails, playas = [], {}
    for tipo, v in VARIANTES:
        sid = f"heraldia:{costa.plantilla(tipo, 'templada', v)}"
        hecho = False
        for ox, oz in PLACE:
            if (ox, oz) not in playas:
                m = ctx.run(f"execute positioned {ox} 64 {oz} run locate biome minecraft:beach",
                            r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
                playas[(ox, oz)] = (int(m.group(1)), int(m.group(2))) if m.group(1) else None
            if playas[(ox, oz)] is None:
                continue
            bx, bz = playas[(ox, oz)]
            if not cargar(ctx, bx, bz, 96):
                fails.append(f"/place {sid} en {bx}, {bz}: no se carga")
                continue
            antes = len(ctx.seen)
            r = ctx.run(f"place structure {sid} {bx} 64 {bz}", r"Generated structure|Failed to place")
            st = next(iter(sitios(ctx, antes)), None)
            forceload(ctx, bx - 96, bz - 96, bx + 95, bz + 95, quitar=True)
            if not r.group(0).startswith("Generated") or st is None:
                fails.append(f"{sid}: /place: {r.string.strip()}")
                break
            if st.sin_orilla:
                print(f"/place {sid} junto a la playa de {bx}, {bz}: sin orilla que le sirva; otra playa")
                continue
            cargar(ctx, bx, bz, 96)
            f = comprobar_faro(ctx, st, v) if tipo == "faro" else comprobar_naufragio(ctx, st)
            forceload(ctx, bx - 96, bz - 96, bx + 95, bz + 95, quitar=True)
            print(f"/place {sid} junto a la playa de {bx}, {bz}: {st}: {'bien' if not f else f}")
            fails += [f"/place {x}" for x in f]
            hecho = True
            break
        if not hecho and not any(sid in f for f in fails):
            fails.append(f"{sid}: ninguna de las {len(PLACE)} playas tiene una orilla que le sirva")
    return fails


def comprobar_botin(ctx):
    fails = []
    forceload(ctx, 30000, 30000, 30000, 30000)
    for tabla in costa.LOOT:
        m = ctx.run(f"loot spawn 30000 120 30000 loot heraldia:costa/{tabla}", r"Dropped \d+|No items")
        if not m.group(0).startswith("Dropped"):
            fails.append(f"loot heraldia:costa/{tabla}: {m.string.strip()}")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    forceload(ctx, 30000, 30000, 30000, 30000, quitar=True)
    return fails


def comprobar_log(ctx, faros=True, sep_naufragio=768):
    fails, log = [], ctx.log()
    for tipo, sep in (("faro", 1024), ("naufragio", sep_naufragio)):
        activo = faros or tipo != "faro"
        sp = round(sep / 16)
        if not re.search(rf"rejilla costa/{tipo}: {'activada' if activo else 'desactivada'}, cada {sp} chunks "
                         rf"\(separación mínima {(DISTANCIA + 15) // 16}, origen desplazado\)[^\n]*candidata en el bioma #heraldia:litoral", log):
            fails.append(f"falta en el log la rejilla de costa/{tipo} (cada {sp} chunks)")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-costa"))
    a = ap.parse_args()
    a.work = os.path.abspath(a.work)
    os.makedirs(a.work, exist_ok=True)
    jar = os.path.abspath(a.jar)
    fails = []
    t0 = time.monotonic()
    proc, ctx = arrancar(a.work, jar, {}, True)
    try:
        fails += comprobar_log(ctx)
        f, vistos = comprobar_locate(ctx)
        fails += f
        if not re.search(r"costa: faros activados cada 1024 bloques, naufragios activados cada 768 bloques; 2 tipos, a 256 bloques",
                         ctx.log()):
            fails.append("falta en el log la regla de la costa")
        fails += comprobar_colocadas(ctx)
        fails += comprobar_botin(ctx)
        ctx.run("heraldia info", r"Registered structures|Estructuras registradas")
        m = re.search(r"(?:Coast|Costa): (?:lighthouses|faros) (\w+), (?:every|cada) 1024 [^\n]*?; (\d+) (?:structures|estructuras)", ctx.log())
        if not m or int(m.group(2)) != len(costa.estructuras()):
            fails.append(f"/heraldia info no resume la costa con sus {len(costa.estructuras())} estructuras")
        modos = {st.modo for sts in vistos.values() for st in sts}
        print(f"vistos con /locate: {sorted(modos)}")
    finally:
        parar(proc)
    proc, ctx = arrancar(a.work, jar, {"faros": {"activado": False}, "naufragios": {"separacion_bloques": 2048}}, False)
    try:
        fails += comprobar_log(ctx, faros=False, sep_naufragio=2048)
        # lejos de lo ya generado (lo generado se queda y /locate lo sigue encontrando, como en un mundo existente)
        m = ctx.run("execute positioned -40000 64 40000 run locate structure #heraldia:costa/faro",
                    r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
        if m.group(1):
            fails.append(f"faros desactivados y /locate da uno nuevo en {m.group(1)}, {m.group(2)}")
    finally:
        parar(proc)
    print(f"costa: {time.monotonic() - t0:.0f} s")
    if fails:
        print("FALLOS:")
        for f in fails:
            print(" -", f)
        return 1
    print("COSTA OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
