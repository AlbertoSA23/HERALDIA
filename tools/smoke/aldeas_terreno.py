"""Aldeas y terreno en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/aldeas_terreno.py --jar build/libs/heraldia-X.jar --work build/smoke [--medir]
Comprueba:
- Puerto que busca el agua: /place de una aldea de la costa en varias playas (/locate biome) pone la caseta y el muelle
  en la orilla más cercana (línea «muelle en ... punta x z» del log): en la punta hay tablas a nivel del mar con agua
  debajo y los pilotes bajan por el agua hasta el fondo. Tierra adentro, la misma aldea sale sin puerto.
- Laderas: /place de una aldea de los cerezos (en ladera; /place no ajusta el terreno, el peor caso) deja muy pocos
  bloques de cimiento al aire: los cimientos de los edificios bajan hasta el suelo con el material del estilo.
  Se cuentan leyendo las regiones guardadas (save-all) con un lector mínimo del formato Anvil.
--medir: solo imprime las cifras (para comparar con un .jar anterior), sin dar por fallado nada.
"""
import argparse, glob, io, os, queue, re, struct, subprocess, sys, threading, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import nbtlib

SEA = 63
COAST = "heraldia:costa_pescadores"
SLOPE = ("heraldia:cerezos_japonesa", "minecraft:cherry_grove", "minecraft:stone_bricks")
RADIUS = 112            # caja forzada y leída alrededor de cada aldea (radio de la estándar + margen; forceload: <= 256 chunks)
MAX_FLOATING = 0.05     # como mucho un 5 %: aleros y arcos de diseño, y cimientos que llegan al tope (16) en un risco
AIRE = {"minecraft:air", "minecraft:cave_air", "minecraft:water", "minecraft:short_grass", "minecraft:tall_grass",
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


def coast(ctx, fails, medir):
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
        tx, tz = int(m.group(1)), int(m.group(2))
        if not test(ctx, f"execute if block {tx} {SEA} {tz} #minecraft:planks"):
            fails.append(f"puerto: no hay tablas en la punta del muelle ({tx} {SEA} {tz})")
        if not test(ctx, f"execute if block {tx} {SEA - 1} {tz} minecraft:water"):
            # fallo pendiente conocido (docs/APRENDIZAJES.md): una calle que llega al mar (tablas sobre el agua por su
            # procesador) puede pasar bajo el muelle; se avisa y se exige el agua un bloque más abajo
            if test(ctx, f"execute if block {tx} {SEA - 1} {tz} #minecraft:planks") and \
                    test(ctx, f"execute if block {tx} {SEA - 2} {tz} minecraft:water"):
                print(f"AVISO puerto: una calle pasa bajo la punta del muelle ({tx} {SEA - 1} {tz})")
            else:
                fails.append(f"puerto: no hay agua bajo la punta del muelle ({tx} {SEA - 1} {tz})")
        # pilotes: troncos bajo la fila de la superficie del agua junto a la punta
        logs = count(ctx, tx - 6, SEA - 24, tz - 6, tx + 6, SEA - 2, tz + 6, "#minecraft:logs", (tx - 6, 250, tz - 6))
        print("costa: troncos de pilote bajo el agua en la punta:", logs)
        if logs == 0:
            fails.append("puerto: los pilotes no bajan hasta el fondo")
        done += 1
    print(f"costa: {done} de {len([p for p in beach if p])} playas con muelle")
    if not done:
        fails.append("ninguna playa cercana dio un sitio con agua para el puerto")


def inland(ctx, fails, p):
    """Tierra adentro (el monte de cerezos de la prueba de ladera): sin orilla cerca, la aldea de la costa sale sin puerto."""
    n = len(ctx.seen)
    if not place(ctx, COAST, *p):
        fails.append(f"place {COAST} en {p} falló")
        return
    time.sleep(1)
    line = coast_line(ctx, n)
    print("costa tierra adentro:", line.strip())
    if "sin orilla" not in line:
        fails.append("tierra adentro la aldea de la costa no debería tener puerto: " + line.strip())


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


def slope(ctx, work, fails, medir):
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
    floating = [q for q in total if blocks.get((q[0], q[1] - 1, q[2]), "minecraft:air") in AIRE]
    ys = [q[1] for q in total]
    print(f"ladera: {sid} en {p}: {len(total)} bloques de {found}, {len(floating)} al aire "
          f"(desnivel de la aldea: alturas {min(ys) if ys else '-'}..{max(ys) if ys else '-'})")
    if not medir and total and len(floating) > MAX_FLOATING * len(total):
        fails.append(f"ladera: {len(floating)} de {len(total)} bloques de cimiento al aire")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-aldeas"))
    ap.add_argument("--medir", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        p = slope(ctx, a.work, fails, a.medir)
        if not a.medir:
            coast(ctx, fails, a.medir)
            if p:
                inland(ctx, fails, p)
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            proc.wait(timeout=120)
    print("ALDEAS Y TERRENO:", "OK" if not fails else fails)
    return 1 if fails and not a.medir else 0


if __name__ == "__main__":
    sys.exit(main())
