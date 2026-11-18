"""Variantes de los edificios especiales de las aldeas en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/village_variants.py --jar build/libs/heraldia-X.jar --work build/smoke [--estilo E] [--medir]
Coloca con /place varias aldeas del mismo estilo en sitios distintos, guarda el mundo y, leyendo las regiones, busca en
cada aldea cada edificio especial (iglesia, cementerio, ayuntamiento, mercado, taberna, herrería, biblioteca, granja,
molino y posada) comparando los bloques del mundo con las plantillas de todas sus variantes, que se leen del .jar:
- cada especial de cada aldea coincide con una sola de sus variantes (las variantes se colocan bien en el juego);
- entre todas las aldeas salen variantes distintas de la mayoría de los especiales (los pools sortean de verdad).
Además mide lo que tarda cada /place (ensamblado y colocación); --medir solo imprime las cifras (para comparar con
un .jar anterior, que no tiene variantes), sin dar nada por fallado.
"""
import argparse, io, math, os, queue, subprocess, sys, threading, time, zipfile
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import village_terrain as at
import nbtlib

KINDS = ("church", "cemetery", "townhall", "market", "tavern", "blacksmith", "library", "farm", "mill", "inn")
SITES = ((0, 0), (450, 0), (0, 450), (450, 450), (-450, 0), (0, -450))
YMIN = 40               # por debajo solo hay terreno: no se lee
MATCH = 0.85            # fracción de bloques de la plantilla que deben estar en el mundo
TIE = 0.03              # con varias por encima de MATCH, empatan las que quedan a menos de esto de la mejor
# Bloques del terreno (y de lo que el terreno puede cambiar) que no cuentan al comparar: el mundo los tiene por todas
# partes y la plantilla puede quedar en parte bajo tierra
NATURAL = {"stone", "deepslate", "dirt", "grass_block", "gravel", "sand", "water", "andesite", "diorite", "granite",
           "tuff", "coarse_dirt", "podzol", "short_grass", "tall_grass", "snow", "farmland", "dirt_path", "clay",
           "calcite", "cave_air", "bedrock", "lava", "moss_block", "rooted_dirt", "mud"}
# El procesador de los edificios cambia al azar algunos bloques de piedra por su versión musgosa o agrietada
SAME = {"mossy_cobblestone": "cobblestone", "mossy_stone_bricks": "stone_bricks", "cracked_stone_bricks": "stone_bricks"}


def norm(name):
    b = name.replace("minecraft:", "").split("[")[0]
    return SAME.get(b, b)


def templates(jar, style):
    """{(tipo, variante): [(x, y, z, bloque)]} de las plantillas de especiales del estilo, sin aire, jigsaws ni lo que
    ellos colocan encima (camas y aldeanos), ni bloques naturales."""
    out = {}
    with zipfile.ZipFile(jar) as z:
        for n in z.namelist():
            pre = f"data/heraldia/structure/{style}/specials/"
            if not n.startswith(pre) or not n.endswith(".nbt"):
                continue
            name = n[len(pre):-4]
            kind, _, var = name.partition("_")
            if kind not in KINDS:
                continue
            nbt = nbtlib.File.parse(io.BytesIO(__import__("gzip").decompress(z.read(n))))
            pal = [norm(str(p.get("Name", p.get("id")))) for p in nbt["palette"]]
            jig = {tuple(int(v) for v in b["pos"]) for b in nbt["blocks"] if pal[int(b["state"])] == "jigsaw"}
            skip = jig | {(x, y + k, z) for (x, y, z) in jig for k in (1, 2)}
            out[(kind, var or "a")] = [(int(b["pos"][0]), int(b["pos"][1]), int(b["pos"][2]), pal[int(b["state"])])
                                       for b in nbt["blocks"]
                                       if pal[int(b["state"])] not in NATURAL | {"air", "structure_void", "jigsaw"}
                                       and tuple(int(v) for v in b["pos"]) not in skip]
    return out


ROT = (lambda x, z: (x, z), lambda x, z: (-z, x), lambda x, z: (-x, -z), lambda x, z: (z, -x))


def anchor(blocks):
    """Bloque más raro de la plantilla (el que menos se repite): desde él se prueba a encajarla en el mundo."""
    c = Counter(b for *_, b in blocks)
    name = min(sorted(c), key=lambda b: c[b])
    return name, [(x, y, z) for x, y, z, b in blocks if b == name]


def find(world, by_name, blocks):
    """Mejor fracción de bloques de la plantilla que coinciden con el mundo, en cualquier giro y posición."""
    name, anchors = anchor(blocks)
    best = 0.0
    ax, ay, az = anchors[0]
    allowed = len(blocks) * (1 - MATCH)
    for (wx, wy, wz) in by_name.get(name, ()):
        for r in ROT:
            hit = miss = 0
            for (x, y, z, b) in blocks:
                dx, dz = r(x - ax, z - az)
                if world.get((wx + dx, wy + y - ay, wz + dz)) == b:
                    hit += 1
                else:
                    miss += 1
                    if miss > allowed and best >= MATCH:
                        break           # ya no supera a la que coincide
            best = max(best, hit / len(blocks))
    return best


def place_timed(ctx, sid, x, z):
    ctx.run(f"forceload add {x - at.RADIUS} {z - at.RADIUS} {x + at.RADIUS} {z + at.RADIUS}", r"Marked|Added|force|already")
    for _ in range(s.PLACE_ATTEMPTS):
        t0 = time.monotonic()
        m = ctx.run(f"place structure {sid} {x} ~ {z}", r"Generated structure")
        dt = time.monotonic() - t0
        if "not loaded" not in m.group(0):
            return ("Generated" in m.group(0)), dt
        time.sleep(s.PLACE_RETRY_S)
    return False, 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-variantes"))
    ap.add_argument("--style", default="llanuras_castellana")
    ap.add_argument("--villages", type=int, default=6)
    ap.add_argument("--measure", action="store_true")
    a = ap.parse_args()
    jar = os.path.abspath(a.jar)
    tpls = templates(jar, a.style)
    variants = defaultdict(list)
    for (k, v) in sorted(tpls):
        variants[k].append(v)
    print("variantes en el .jar:", dict(variants))
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, jar, s.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    found, times = defaultdict(Counter), []
    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        sid = f"heraldia:{a.style}"
        placed = []
        for (x, z) in SITES[:a.villages]:
            ok, dt = place_timed(ctx, sid, x, z)
            print(f"place {sid} en {x} {z}: {'ok' if ok else 'FALLO'} en {dt * 1000:.0f} ms")
            if not ok:
                fails.append(f"place {sid} en {x} {z} falló")
                continue
            times.append(dt)
            placed.append((x, z))
        if times:
            print(f"place: media {sum(times) / len(times) * 1000:.0f} ms, máximo {max(times) * 1000:.0f} ms "
                  f"({len(times)} aldeas)")
        if a.measure:
            return 0
        time.sleep(3)
        ctx.run("save-all flush", r"Saved the game|saved")
        world_dir = os.path.join(a.work, "world")
        for (x, z) in placed:
            raw = at.read_blocks(world_dir, x - at.RADIUS, z - at.RADIUS, x + at.RADIUS, z + at.RADIUS)
            world, by_name = {}, defaultdict(list)
            for p, n in raw.items():
                b = norm(n)
                if p[1] >= YMIN and b not in NATURAL:
                    world[p] = b
                    by_name[b].append(p)
            row = []
            for k in KINDS:
                scores = {v: find(world, by_name, tpls[(k, v)]) for v in variants[k]}
                hits = [v for v, sc in scores.items() if sc >= MATCH]
                # una variante puede contener casi entera a otra (ayuntamiento c de llanuras_castellana: con c colocada,
                # a coincide al 94 %): si una destaca sobre las demás (TIE), cuenta solo esa
                if len(hits) > 1:
                    top = max(scores[v] for v in hits)
                    hits = [v for v in hits if scores[v] >= top - TIE]
                row.append(f"{k}={'/'.join(hits) or '?'}")
                if len(hits) != 1:
                    fails.append(f"aldea en {x} {z}: {k} coincide con {hits or 'ninguna'} "
                                 f"({', '.join(f'{v} {sc:.2f}' for v, sc in scores.items())})")
                else:
                    found[k][hits[0]] += 1
            print(f"aldea en {x} {z}:", " ".join(row))
        varied = [k for k in KINDS if len(found[k]) >= 2]
        new = sum(n for k in KINDS for v, n in found[k].items() if v != "a")
        print("variantes vistas:", {k: dict(found[k]) for k in KINDS})
        if len(placed) >= 3 and len(varied) < len(KINDS) // 2:
            fails.append(f"solo {len(varied)} de {len(KINDS)} especiales salen con más de una variante")
        if placed and not new:
            fails.append("no ha salido ninguna variante nueva")
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            proc.wait(timeout=120)
    print("VARIANTES DE LOS ESPECIALES:", "OK" if not fails else fails)
    return 1 if fails and not a.measure else 0


if __name__ == "__main__":
    sys.exit(main())
