"""Caminos entre aldeas en un servidor dedicado 26.3 real (complementa los tests JUnit de caminos/Trazado).

Uso: python3 tools/smoke/caminos.py --jar build/libs/heraldia-X.jar --work build/smoke
Tres arranques con la misma semilla y la rejilla mínima de las aldeas (1.000 bloques):
1. Caminos activados: se localiza una aldea y se generan los chunks de su plaza; el mod escribe en el log las rutas que
   los cruzan («camino entre las aldeas de ...»). Se elige una hasta otra aldea.
2. Mundo nuevo con los caminos desactivados (aldeas.caminos.activado = false): el rasgo no se añade a los biomas (no hay
   línea de coste al parar). Se genera la primera mitad del pasillo de la ruta y se cuenta lo que es del camino
   (camino de tierra, losas de arenisca, barro compacto, faroles, antorchas y carteles, con una etiqueta de bloques de un
   paquete de datos de prueba) chunk a chunk con `clone ... filtered`.
3. El mismo mundo con los caminos activados: se genera el pasillo entero. En los chunks de la primera mitad (ya
   generados) nada cambia; en los nuevos hay camino, farolas y el cartel de la aldea de destino, con su nombre y la
   distancia. El coste por chunk del rasgo (medido por el mod con System.nanoTime) sale en el log al parar.
"""
import argparse, json, math, os, queue, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import aldeas_terreno as at

GRID = 1000
CONFIG = {"aldeas": {"separacion_bloques": GRID, "maximo": 100}}
PACK, TAG = "prueba_caminos", "prueba_caminos:camino"
MATERIALES = ["minecraft:dirt_path", "minecraft:smooth_sandstone", "minecraft:smooth_red_sandstone", "minecraft:packed_mud",
              "minecraft:mud_bricks", "minecraft:lantern", "minecraft:torch", "#minecraft:standing_signs"]
PASILLO = 3            # chunks a cada lado de la recta (serpenteo de 40 bloques como mucho, más el ancho)
Y0, ALTO = 40, 128     # franja de alturas que se cuenta (clone: como mucho 32.768 bloques por orden)
DESTINO = (-4000, -4000)
RUTA = re.compile(r"camino entre las aldeas de (-?\d+) (-?\d+) y (-?\d+) (-?\d+): (\d+) bloques")
CARTEL = re.compile(r"cartel de camino en (-?\d+) (-?\d+) (-?\d+): «([^»]+)», (\d+) bloques")
COSTE = re.compile(r"caminos: (\d+) chunks, (\d+) junto a una ruta \((\d+) columnas puestas\); media ([\d.]+) µs por chunk, ([\d.]+) µs "
                   r"en los que están junto a una ruta; percentiles 50/90/99 por debajo de (\d+)/(\d+)/(\d+) µs")
AGUA = ["#minecraft:is_ocean", "#minecraft:is_deep_ocean", "#minecraft:is_river", "#minecraft:is_beach"]
# Coste máximo del rasgo (media por chunk). Holgado para la CI; las cifras medidas van en el PR y en LESSONS.
MAX_MEDIA_US, MAX_CAMINO_US = 3000, 30000


def configurar(work, activado, semilla="heraldia"):
    cfg = json.loads(json.dumps(CONFIG))
    cfg["aldeas"]["caminos"] = {"activado": activado}
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)
    props = os.path.join(work, "server.properties")
    with open(props) as f:
        text = re.sub(r"level-seed=.*", f"level-seed={semilla}", f.read())
    with open(props, "w") as f:
        f.write(text)


def paquete(work):
    """Etiqueta de bloques con lo que solo pone el camino en la superficie (world/datapacks: se activa al crear el mundo)."""
    root = os.path.join(work, "world", "datapacks", PACK)
    os.makedirs(os.path.join(root, "data", "prueba_caminos", "tags", "block"), exist_ok=True)
    with open(os.path.join(root, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"description": "Heraldia: prueba de caminos", "min_format": 121, "max_format": 121}}, f)
    with open(os.path.join(root, "data", "prueba_caminos", "tags", "block", "camino.json"), "w") as f:
        json.dump({"values": MATERIALES}, f)


def chunks_de(a, b):
    """Chunks del pasillo de la recta a-b, ordenados por avance desde a: [(t, cx, cz)]."""
    (ax, az), (bx, bz) = a, b
    L = math.dist(a, b)
    out = set()
    for k in range(int(L / 8) + 1):
        t = k * 8 / L
        x, z = ax + (bx - ax) * t, az + (bz - az) * t
        for dx in range(-PASILLO, PASILLO + 1):
            for dz in range(-PASILLO, PASILLO + 1):
                out.add((int(x) // 16 + dx, int(z) // 16 + dz))
    def avance(c):
        cx, cz = c[0] * 16 + 8, c[1] * 16 + 8
        return ((cx - ax) * (bx - ax) + (cz - az) * (bz - az)) / (L * L)
    return sorted(((avance(c), c[0], c[1]) for c in out))


def generar(ctx, chunks):
    for _, cx, cz in chunks:
        ctx.run(f"forceload add {cx * 16} {cz * 16}", r"Marked|Added|force|already")
    for _, cx, cz in chunks:
        if not ctx.until(f"execute if loaded {cx * 16} 0 {cz * 16}", timeout=600):
            raise SystemExit(f"el chunk {cx}, {cz} no se carga")


def contar(ctx, chunks):
    """{(cx, cz): bloques de la etiqueta} en la franja de alturas de cada chunk."""
    dx, dz = DESTINO
    out = {}
    for _, cx, cz in chunks:
        x, z = cx * 16, cz * 16
        m = ctx.run(f"clone {x} {Y0} {z} {x + 15} {Y0 + ALTO - 1} {z + 15} {dx} {320 - ALTO} {dz} filtered #{TAG} force",
                    r"Successfully cloned (\d+) block|No blocks")
        out[(cx, cz)] = int(m.group(1)) if m.lastindex and m.group(1) else 0
    return out


def destino_listo(ctx):
    dx, dz = DESTINO
    ctx.run(f"forceload add {dx} {dz} {dx + 15} {dz + 15}", r"Marked|Added|force|already")
    ctx.until(f"execute if loaded {dx} 0 {dz}", timeout=300)


def tierra(ctx, a, b):
    """Cuántos de 7 puntos de la recta a-b no caen en el mar, un río o una playa (carga un chunk por punto)."""
    n = 0
    for k in range(1, 8):
        x, z = int(a[0] + (b[0] - a[0]) * k / 8), int(a[1] + (b[1] - a[1]) * k / 8)
        ctx.run(f"forceload add {x} {z}", r"Marked|Added|force|already")
        ctx.until(f"execute if loaded {x} 0 {z}", timeout=300)
        n += not any(ctx.test(f"execute if biome {x} 64 {z} {t}") for t in AGUA)
    return n


def buscar_ruta(ctx):
    """La ruta más en tierra firme de las que salen de una aldea localizada (las escribe el mod en el log al generar
    los chunks de su plaza): (a, b, longitud)."""
    for x, z in [(0, 0), (GRID, 0), (0, GRID), (-GRID, 0), (0, -GRID), (GRID, GRID)]:
        m = ctx.run(f"execute positioned {x} 100 {z} run locate structure #heraldia:aldeas", r"is at \[(-?\d+), ~, (-?\d+)\]|Could not find")
        if not m.group(1):
            continue
        vx, vz = int(m.group(1)) + 8, int(m.group(2)) + 8
        ctx.run(f"forceload add {vx - 16} {vz - 16} {vx + 16} {vz + 16}", r"Marked|Added|force|already")
        ctx.until(f"execute if loaded {vx} 0 {vz}", timeout=300)
        rutas = []
        for r in RUTA.finditer(ctx.log()):
            a, b, L = (int(r.group(1)), int(r.group(2))), (int(r.group(3)), int(r.group(4))), int(r.group(5))
            if math.dist(a, (vx, vz)) < 2 or math.dist(b, (vx, vz)) < 2:
                rutas.append((a, b, L) if math.dist(a, (vx, vz)) < 2 else (b, a, L))
        if rutas:
            puntos = {r: tierra(ctx, r[0], r[1]) for r in rutas}
            print("rutas desde", (vx, vz), {f"{r[1]} ({r[2]} bloques)": f"{p}/7 en tierra" for r, p in puntos.items()})
            mejor = max(rutas, key=lambda r: (puntos[r], -r[2]))
            if puntos[mejor] >= 5:
                return mejor
    return None


def parar(proc, ctx):
    """Para el servidor y pasa a ctx.seen lo que escribió al parar (la línea de coste del rasgo)."""
    at.stop(proc)
    while True:   # hasta el final de la salida (el lector pone None al cerrarse)
        try:
            line = ctx.lines.get(timeout=30)
        except queue.Empty:
            return
        if line is None:
            return
        ctx.seen.append(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-caminos"))
    a = ap.parse_args()
    a.work = os.path.abspath(a.work)
    os.makedirs(a.work, exist_ok=True)
    jar = os.path.abspath(a.jar)
    fails = []

    # 1) qué ruta probar
    launcher = s.prepare(a.work, jar, s.gradle_properties())
    configurar(a.work, True)
    proc, ctx = at.start_server(a.work, launcher)
    try:
        ruta = buscar_ruta(ctx)
    finally:
        parar(proc, ctx)
    if ruta is None:
        print("CAMINOS:", ["ninguna ruta desde las aldeas localizadas"])
        return 1
    va, vb, L = ruta
    print(f"ruta de {va} a {vb}: {L} bloques")
    pasillo = chunks_de(va, vb)
    viejos = [c for c in pasillo if c[0] < 0.5]
    nuevos = [c for c in pasillo if c[0] >= 0.5]

    # 2) mundo nuevo sin caminos: la primera mitad
    launcher = s.prepare(a.work, jar, s.gradle_properties())
    configurar(a.work, False)
    paquete(a.work)
    proc, ctx = at.start_server(a.work, launcher)
    try:
        if not re.search(r"caminos entre aldeas desactivados", ctx.log()):
            fails.append("sin la línea «caminos entre aldeas desactivados» en el log")
        destino_listo(ctx)
        generar(ctx, viejos)
        antes = contar(ctx, viejos)
        ctx.run("save-all flush", r"Saved the game|saved")
    finally:
        parar(proc, ctx)
    log2 = "".join(ctx.seen)
    if COSTE.search(log2) or RUTA.search(log2):
        fails.append("con aldeas.caminos.activado = false el rasgo se ha ejecutado")

    # 3) el mismo mundo con caminos: el pasillo entero
    configurar(a.work, True)
    proc, ctx = at.start_server(a.work, launcher)
    try:
        destino_listo(ctx)
        generar(ctx, pasillo)
        despues = contar(ctx, viejos)
        nuevo = contar(ctx, nuevos)
        cambiados = {c: (antes[c], despues[c]) for c in antes if antes[c] != despues[c]}
        if cambiados:
            fails.append(f"chunks ya generados cambiados al activar los caminos: {dict(list(cambiados.items())[:8])}")
        total = sum(nuevo.values())
        con = sum(1 for v in nuevo.values() if v)
        print(f"pasillo: {len(viejos)} chunks viejos ({sum(antes.values())} bloques de camino, sin cambios: {not cambiados}), "
              f"{len(nuevos)} nuevos con {total} bloques de camino en {con} chunks")
        if total < 0.3 * L:
            fails.append(f"solo {total} bloques de camino en los {len(nuevos)} chunks nuevos del pasillo")
        carteles = [m for m in CARTEL.finditer(ctx.log())]
        hacia = [m for m in carteles if (int(m.group(1)) // 16, int(m.group(3)) // 16) in {(c[1], c[2]) for c in nuevos}]
        print(f"carteles en el log: {len(carteles)} ({len(hacia)} en el pasillo nuevo)")
        for m in hacia[:3]:
            x, y, z = m.group(1), m.group(2), m.group(3)
            r = ctx.run(f"data get block {x} {y} {z} front_text", r"has the following block data: (.*)|not a block entity|Found no")
            texto = r.group(1) or ""
            primera = m.group(4).split(" ")[0]
            if primera not in texto or "heraldia.camino.cartel." not in texto:
                fails.append(f"cartel en {x} {y} {z} sin el nombre «{m.group(4)}» o la distancia: {r.string.strip()}")
        if not hacia:
            fails.append("ningún cartel en el pasillo nuevo (el de la aldea de destino)")
    finally:
        parar(proc, ctx)
    m = COSTE.search("".join(ctx.seen))
    if not m:
        fails.append("sin la línea de coste del rasgo al parar")
    else:
        n, c, cols, media, camino = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5))
        print(f"coste del rasgo: {n} chunks, {c} junto a una ruta ({cols} columnas puestas); media {media} µs por chunk, {camino} µs junto a una ruta; "
              f"percentiles 50/90/99 < {m.group(6)}/{m.group(7)}/{m.group(8)} µs")
        if media > MAX_MEDIA_US or camino > MAX_CAMINO_US:
            fails.append(f"coste del rasgo: media {media} µs por chunk y {camino} µs con camino (máximo {MAX_MEDIA_US} y {MAX_CAMINO_US})")
    print("CAMINOS:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
