"""Roads between villages on a real 26.3 dedicated server (complements the JUnit tests of caminos/Trazado).

Usage: python3 tools/smoke/roads.py --jar build/libs/heraldia-X.jar --work build/smoke
Three starts with the same seed and the minimum village grid (1,000 blocks):
1. Roads enabled: a village is located and the chunks of its plaza are generated; the mod writes to the log the routes that
   cross them ("camino entre las aldeas de ..."). One is chosen to another village.
2. New world with roads disabled (aldeas.caminos.activado = false): the feature is not added to the biomes (there is no
   cost line on stop). The first half of the route's corridor is generated and what belongs to the road is counted
   (dirt path, sandstone slabs, packed mud, lanterns, torches and signs, with a block tag from a test
   data pack) chunk by chunk with `clone ... filtered`.
3. The same world with roads enabled: the whole corridor is generated. In the chunks of the first half (already
   generated) nothing changes; in the new ones there is a road, lamp posts and the destination village's sign, with its name and the
   distance. The feature's cost per chunk (measured by the mod with System.nanoTime) appears in the log on stop.
"""
import argparse, json, math, os, queue, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import village_terrain as at

GRID = 1000
CONFIG = {"aldeas": {"separacion_bloques": GRID, "maximo": 100}}
PACK, TAG = "prueba_caminos", "prueba_caminos:camino"
MATERIALS = ["minecraft:dirt_path", "minecraft:smooth_sandstone", "minecraft:smooth_red_sandstone", "minecraft:packed_mud",
              "minecraft:mud_bricks", "minecraft:lantern", "minecraft:torch", "#minecraft:standing_signs"]
CORRIDOR = 3            # chunks on each side of the line (meander of 40 blocks at most, plus the width)
Y0, HEIGHT = 40, 128     # band of heights that is counted (clone: at most 32,768 blocks per command)
DESTINATION = (-4000, -4000)
ROUTE = re.compile(r"camino entre las aldeas de (-?\d+) (-?\d+) y (-?\d+) (-?\d+): (\d+) bloques")
SIGN = re.compile(r"cartel de camino en (-?\d+) (-?\d+) (-?\d+): «([^»]+)», (\d+) bloques")
COST = re.compile(r"caminos: (\d+) chunks, (\d+) junto a una ruta \((\d+) columnas puestas\); media ([\d.]+) µs por chunk, ([\d.]+) µs "
                   r"en los que están junto a una ruta; percentiles 50/90/99 por debajo de (\d+)/(\d+)/(\d+) µs")
WATER = ["#minecraft:is_ocean", "#minecraft:is_deep_ocean", "#minecraft:is_river", "#minecraft:is_beach"]
# Maximum cost of the feature (mean per chunk). Generous for CI; the measured figures go in the PR and in LESSONS.
MAX_MEAN_US, MAX_ROAD_US = 3000, 30000


def configure(work, switched_on, seed="heraldia"):
    cfg = json.loads(json.dumps(CONFIG))
    cfg["aldeas"]["caminos"] = {"activado": switched_on}
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)
    props = os.path.join(work, "server.properties")
    with open(props) as f:
        text = re.sub(r"level-seed=.*", f"level-seed={seed}", f.read())
    with open(props, "w") as f:
        f.write(text)


def package(work):
    """Block tag with what only the road places on the surface (world/datapacks: enabled when the world is created)."""
    root = os.path.join(work, "world", "datapacks", PACK)
    os.makedirs(os.path.join(root, "data", "prueba_caminos", "tags", "block"), exist_ok=True)
    with open(os.path.join(root, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"description": "Heraldia: prueba de caminos", "min_format": 121, "max_format": 121}}, f)
    with open(os.path.join(root, "data", "prueba_caminos", "tags", "block", "camino.json"), "w") as f:
        json.dump({"values": MATERIALS}, f)


def chunks_of(a, b):
    """Chunks of the corridor of the line a-b, ordered by progress from a: [(t, cx, cz)]."""
    (ax, az), (bx, bz) = a, b
    L = math.dist(a, b)
    out = set()
    for k in range(int(L / 8) + 1):
        t = k * 8 / L
        x, z = ax + (bx - ax) * t, az + (bz - az) * t
        for dx in range(-CORRIDOR, CORRIDOR + 1):
            for dz in range(-CORRIDOR, CORRIDOR + 1):
                out.add((int(x) // 16 + dx, int(z) // 16 + dz))
    def progress(c):
        cx, cz = c[0] * 16 + 8, c[1] * 16 + 8
        return ((cx - ax) * (bx - ax) + (cz - az) * (bz - az)) / (L * L)
    return sorted(((progress(c), c[0], c[1]) for c in out))


def generate(ctx, chunks):
    for _, cx, cz in chunks:
        ctx.run(f"forceload add {cx * 16} {cz * 16}", r"Marked|Added|force|already")
    for _, cx, cz in chunks:
        if not ctx.until(f"execute if loaded {cx * 16} 0 {cz * 16}", timeout=600):
            raise SystemExit(f"chunk {cx}, {cz} does not load")


def count(ctx, chunks):
    """{(cx, cz): tag blocks} in the band of heights of each chunk."""
    dx, dz = DESTINATION
    out = {}
    for _, cx, cz in chunks:
        x, z = cx * 16, cz * 16
        m = ctx.run(f"clone {x} {Y0} {z} {x + 15} {Y0 + HEIGHT - 1} {z + 15} {dx} {320 - HEIGHT} {dz} filtered #{TAG} force",
                    r"Successfully cloned (\d+) block|No blocks")
        out[(cx, cz)] = int(m.group(1)) if m.lastindex and m.group(1) else 0
    return out


def destination_ready(ctx):
    dx, dz = DESTINATION
    ctx.run(f"forceload add {dx} {dz} {dx + 15} {dz + 15}", r"Marked|Added|force|already")
    ctx.until(f"execute if loaded {dx} 0 {dz}", timeout=300)


def land(ctx, a, b):
    """How many of 7 points of the line a-b do not fall in the sea, a river or a beach (loads one chunk per point)."""
    n = 0
    for k in range(1, 8):
        x, z = int(a[0] + (b[0] - a[0]) * k / 8), int(a[1] + (b[1] - a[1]) * k / 8)
        ctx.run(f"forceload add {x} {z}", r"Marked|Added|force|already")
        ctx.until(f"execute if loaded {x} 0 {z}", timeout=300)
        n += not any(ctx.test(f"execute if biome {x} 64 {z} {t}") for t in WATER)
    return n


def find_path(ctx):
    """The route most over dry land among those leaving a located village (the mod writes them to the log when generating
    the chunks of its plaza): (a, b, length)."""
    for x, z in [(0, 0), (GRID, 0), (0, GRID), (-GRID, 0), (0, -GRID), (GRID, GRID)]:
        m = ctx.run(f"execute positioned {x} 100 {z} run locate structure #heraldia:aldeas", r"is at \[(-?\d+), ~, (-?\d+)\]|Could not find")
        if not m.group(1):
            continue
        vx, vz = int(m.group(1)) + 8, int(m.group(2)) + 8
        ctx.run(f"forceload add {vx - 16} {vz - 16} {vx + 16} {vz + 16}", r"Marked|Added|force|already")
        ctx.until(f"execute if loaded {vx} 0 {vz}", timeout=300)
        routes = []
        for r in ROUTE.finditer(ctx.log()):
            a, b, L = (int(r.group(1)), int(r.group(2))), (int(r.group(3)), int(r.group(4))), int(r.group(5))
            if math.dist(a, (vx, vz)) < 2 or math.dist(b, (vx, vz)) < 2:
                routes.append((a, b, L) if math.dist(a, (vx, vz)) < 2 else (b, a, L))
        if routes:
            points = {r: land(ctx, r[0], r[1]) for r in routes}
            print("routes from", (vx, vz), {f"{r[1]} ({r[2]} blocks)": f"{p}/7 en tierra" for r, p in points.items()})
            best = max(routes, key=lambda r: (points[r], -r[2]))
            if points[best] >= 5:
                return best
    return None


def halt(proc, ctx):
    """Stops the server and passes to ctx.seen what it wrote on stop (the feature's cost line)."""
    at.stop(proc)
    while True:   # until the end of the output (the reader puts None when it closes)
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

    # 1) which route to test
    launcher = s.prepare(a.work, jar, s.gradle_properties())
    configure(a.work, True)
    proc, ctx = at.start_server(a.work, launcher)
    try:
        route = find_path(ctx)
    finally:
        halt(proc, ctx)
    if route is None:
        print("CAMINOS:", ["no route from the located villages"])
        return 1
    va, vb, L = route
    print(f"route from {va} to {vb}: {L} blocks")
    corridor = chunks_of(va, vb)
    old = [c for c in corridor if c[0] < 0.5]
    new_items = [c for c in corridor if c[0] >= 0.5]

    # 2) new world without roads: the first half
    launcher = s.prepare(a.work, jar, s.gradle_properties())
    configure(a.work, False)
    package(a.work)
    proc, ctx = at.start_server(a.work, launcher)
    try:
        if not re.search(r"caminos entre aldeas desactivados", ctx.log()):
            fails.append("without the 'caminos entre aldeas desactivados' line in the log")
        destination_ready(ctx)
        generate(ctx, old)
        before = count(ctx, old)
        ctx.run("save-all flush", r"Saved the game|saved")
    finally:
        halt(proc, ctx)
    log2 = "".join(ctx.seen)
    if COST.search(log2) or ROUTE.search(log2):
        fails.append("with aldeas.caminos.activado = false the feature has run")

    # 3) the same world with roads: the whole corridor
    configure(a.work, True)
    proc, ctx = at.start_server(a.work, launcher)
    try:
        destination_ready(ctx)
        generate(ctx, corridor)
        after = count(ctx, old)
        new_item = count(ctx, new_items)
        changed_list = {c: (before[c], after[c]) for c in before if before[c] != after[c]}
        if changed_list:
            fails.append(f"already generated chunks changed when enabling the roads: {dict(list(changed_list.items())[:8])}")
        total = sum(new_item.values())
        with_it = sum(1 for v in new_item.values() if v)
        print(f"corridor: {len(old)} old chunks ({sum(before.values())} road blocks, unchanged: {not changed_list}), "
              f"{len(new_items)} nuevos con {total} bloques de camino en {with_it} chunks")
        if total < 0.3 * L:
            fails.append(f"only {total} road blocks in the {len(new_items)} new chunks of the corridor")
        signs = [m for m in SIGN.finditer(ctx.log())]
        toward = [m for m in signs if (int(m.group(1)) // 16, int(m.group(3)) // 16) in {(c[1], c[2]) for c in new_items}]
        print(f"signs in the log: {len(signs)} ({len(toward)} in the new corridor)")
        for m in toward[:3]:
            x, y, z = m.group(1), m.group(2), m.group(3)
            r = ctx.run(f"data get block {x} {y} {z} front_text", r"has the following block data: (.*)|not a block entity|Found no")
            text = r.group(1) or ""
            first = m.group(4).split(" ")[0]
            if first not in text or "heraldia.camino.cartel." not in text:
                fails.append(f"sign at {x} {y} {z} without the name '{m.group(4)}' or the distance: {r.string.strip()}")
        if not toward:
            fails.append("no sign in the new corridor (the destination village's)")
    finally:
        halt(proc, ctx)
    m = COST.search("".join(ctx.seen))
    if not m:
        fails.append("without the feature's cost line on stop")
    else:
        n, c, cols, mean, road = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5))
        print(f"feature cost: {n} chunks, {c} next to a route ({cols} columns placed); mean {mean} µs per chunk, {road} µs next to a route; "
              f"percentiles 50/90/99 < {m.group(6)}/{m.group(7)}/{m.group(8)} µs")
        if mean > MAX_MEAN_US or road > MAX_ROAD_US:
            fails.append(f"feature cost: mean {mean} µs per chunk and {road} µs with road (maximum {MAX_MEAN_US} and {MAX_ROAD_US})")
    print("CAMINOS:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
