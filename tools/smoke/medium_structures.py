"""Estructuras medianas (tools/gen/mediums) en un servidor dedicado 26.3 real, con la configuración por defecto.

Uso: python3 tools/smoke/medium_structures.py --jar build/libs/heraldia-X.jar [--work build/smoke-estructuras-medianas]
Comprueba:
- el log: la regla de las medianas y la rejilla de cada tipo con su separación por defecto, su búsqueda de bioma y, en los
  de biomas en franja (pescador), los vecinos que pide (bioma_vecinos);
- /locate de cada tipo (#heraldia:medianas/<tipo>) desde varios puntos, a una distancia razonable, y desde cada una
  /heraldia info nearby: ninguna aldea ni única a menos de medianas.distancia_aldeas_unicas_bloques ni otra mediana de
  otro tipo a menos de medianas.distancia_minima.bloques (info nearby da la más cercana de cada rejilla con las reglas de
  la generación); luego se genera de verdad (forceload) y la estructura está donde dijo /locate;
- /place template de cada variante (sobre una losa): cada contenedor con su tabla (también las vasijas del templete), las
  entidades esperadas (etiqueta heraldia_mediana.<tipo>), el agua quieta (caz del molino, acequias, pozo del templete:
  sigue siendo fuente y no corre) y los aldeanos (posadero, molinero, pescador, cazador) quietos y con sus tratos;
- /place structure de cada estilo (el pool y la estructura cargan) y su tiempo;
- loot spawn de cada tabla (el diario de la ermita es un libro escrito) y /heraldia info con su resumen.
Código 0 si todo pasa.
"""
import argparse, json, math, os, queue, re, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

sys.path.insert(0, os.path.join(s.ROOT, "tools", "gen"))
import mediums                      # noqa: E402  (el generador: tipos, plantillas y botín)
from pack import Registry           # noqa: E402

POINTS = [(0, 0), (3000, -2000), (-4000, 3500)]
LOCATE_MAX = 4000                    # bloques: con la separación por defecto (700-900 por tipo) sobra
ZONE, DISTANCE = 256, 192           # valores por defecto (opciones.py)
PLACE_X, PLACE_Z, STEP = 30000, 30000, 48


def templates():
    reg = Registry()
    for mid, _ in mediums.modules():
        mediums.build(reg, mid)
    assert not reg.warnings, reg.warnings
    return {n: t for n, t in reg.templates.items() if n.startswith("medianas/")}


def forceload(ctx, x0, z0, x1, z1, remove=False):
    ctx.run(f"forceload {'remove' if remove else 'add'} {x0} {z0} {x1} {z1}", r"Marked|[Aa]dded|[Rr]emoved|force|already|[Uu]nmarked")


def info_cerca(ctx, x, z, radius):
    """{id: (distancia, x, z)} de /heraldia info nearby desde x, z."""
    m = ctx.run(f"execute positioned {x} 64 {z} run heraldia info nearby {radius}",
                r"info nearby \d+ en [^:]+: \d+ estructuras en (\d+) ms")
    if not m.lastindex:
        return None
    return {g[0]: (int(g[1]), int(g[2]), int(g[3])) for g in s.INFO_LINE.findall("".join(s.drain(ctx)))}


def check_locate(ctx, kinds):
    fails, timings = [], []
    for mid in kinds:
        found_count = 0
        for x, z in POINTS:
            t0 = time.monotonic()
            m = ctx.run(f"execute positioned {x} 64 {z} run locate structure #heraldia:medianas/{mid}",
                        r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
            timings.append(time.monotonic() - t0)
            if not m.group(1):
                fails.append(f"/locate no encuentra {mid} desde {x}, {z}")
                continue
            px, pz = int(m.group(1)), int(m.group(2))
            d = math.dist((x, z), (px, pz))
            print(f"{mid} desde {x}, {z}: en {px}, {pz} a {d:.0f} bloques ({timings[-1]:.2f} s)")
            if d > LOCATE_MAX:
                fails.append(f"{mid} desde {x}, {z} a {d:.0f} bloques (> {LOCATE_MAX})")
            found_count += 1
            nearby_flag = info_cerca(ctx, px, pz, 600)
            if nearby_flag is None:
                fails.append(f"/heraldia info nearby desde {mid} en {px}, {pz} no responde")
                continue
            for sid, (dist, *_) in nearby_flag.items():
                if ":minas/" in sid:                          # entradas a mina: ceden a las medianas a esta distancia
                    if dist < DISTANCE:
                        fails.append(f"{mid} en {px}, {pz} a {dist} bloques de la mina {sid} (< {DISTANCE})")
                elif ":medianas/" not in sid:                 # aldeas (heraldia:aldeas o su estilo) y únicas
                    if dist < ZONE:
                        fails.append(f"{mid} en {px}, {pz} a {dist} bloques de {sid} (< {ZONE})")
                elif f"medianas/{mid}" not in sid and dist < DISTANCE:
                    fails.append(f"{mid} en {px}, {pz} a {dist} bloques de {sid} (< {DISTANCE})")
            if (x, z) == POINTS[0]:      # la primera se genera de verdad: el inicio está donde dijo /locate
                forceload(ctx, px - 32, pz - 32, px + 31, pz + 31)
                if not wait_generated(ctx, px, pz, mid):
                    fails.append(f"{mid}: /locate da {px}, {pz} pero ahí no se ha generado")
        if not found_count:
            fails.append(f"ningún {mid}")
    if timings:
        print(f"/locate de medianas: {len(timings)} búsquedas, media {sum(timings) / len(timings):.2f} s, máxima {max(timings):.2f} s")
    return fails


def wait_generated(ctx, x, z, mid):
    """/heraldia info here junto al inicio (la pieza sale hacia un cuadrante u otro según su giro), a la altura del
    terreno (dentro de la caja de la pieza), dice que estás en la mediana. Solo mira chunks ya cargados."""
    end = time.monotonic() + s.UNTIL_S
    while time.monotonic() < end:
        for dx, dz in ((6, 6), (-6, 6), (6, -6), (-6, -6)):
            m = ctx.run(f"execute positioned {x + dx} 0 {z + dz} positioned over world_surface positioned ~ ~-2 ~ "
                        f"run heraldia info here",
                        r"\((heraldia:[^)]+)\)|no hay ninguna|no Heraldia|not loaded|no está cargada")
            if m.group(1) and f"medianas/{mid}/" in m.group(1):
                return True
        time.sleep(2)
    return False


def check_templates(ctx, ts):
    fails = []
    for k, (name, t) in enumerate(sorted(ts.items())):
        x, z = PLACE_X + (k % 5) * STEP, PLACE_Z + (k // 5) * STEP
        y = 100
        forceload(ctx, x - 8, z - 8, x + 47, z + 47)
        sx, _, sz = t.size()       # losa debajo: el agua de la fila y = 0 (caces, acequias, pozos) se apoya como en el suelo
        ctx.run(f"fill {x} {y - 1} {z} {x + sx - 1} {y - 1} {z + sz - 1} minecraft:stone", r"Successfully filled|No blocks")
        m = ctx.run(f"place template heraldia:{name} {x} {y} {z}", r"Loaded template|Failed")
        if "Loaded" not in m.group(0):
            fails.append(f"{name}: place template: {m.string.strip()}")
            continue
        for (bx, by, bz), (st, nbt) in t.blocks.items():
            lt = nbt and nbt.get("LootTable")
            if lt and not ctx.block((x + bx, y + by, z + bz), f"{st.split('[')[0]}{{LootTable:\"{lt}\"}}"):
                fails.append(f"{name}: falta el contenedor {lt} en {bx, by, bz}")
        n = len(t.entities)
        if n:
            sel = f"@e[tag=heraldia_mediana.{name.split('/')[1]},x={x},y={y},z={z},dx=40,dy=30,dz=40]"
            if not ctx.until(f"execute if entity {sel}"):
                fails.append(f"{name}: no aparecen sus entidades")
            elif ctx.count(sel) != n:
                fails.append(f"{name}: {ctx.count(sel)} entidades, esperadas {n}")
        fails += check_water(ctx, name, t, (x, y, z))
        fails += check_villagers(ctx, name, t, (x, y, z))
        forceload(ctx, x - 8, z - 8, x + 47, z + 47, remove=True)
    return fails


def check_water(ctx, name, t, origin):
    """El agua de la plantilla (todo fuentes, entre bloques) no corre: unos ticks después, cada celda de agua sigue siendo
    una fuente y las de aire de alrededor siguen vacías."""
    water = [p for p, (st, _) in t.blocks.items() if st.split("[")[0] == "minecraft:water"]   # no los calderos
    if not water:
        return []
    time.sleep(2)                         # el agua se extiende cada 5 ticks
    x0, y0, z0 = origin
    fails = []
    for (x, y, z) in water:
        if not ctx.block((x0 + x, y0 + y, z0 + z), "minecraft:water[level=0]"):
            fails.append(f"{name}: el agua de {x, y, z} ya no es una fuente")
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)):
            v = t.get(x + dx, y + dy, z + dz)
            if v in (None, "minecraft:air") and not ctx.block((x0 + x + dx, y0 + y + dy, z0 + z + dz), "minecraft:air"):
                fails.append(f"{name}: el agua de {x, y, z} corre hacia {x + dx, y + dy, z + dz}")
    return fails


def check_villagers(ctx, name, t, origin):
    """Los aldeanos de las medianas (posadero, molinero, pescador, cazador): quietos, invulnerables y con sus tratos."""
    fails = []
    x0, y0, z0 = origin
    mid = name.split("/")[1]
    for *_, n in t.entities:
        if n["id"] != "minecraft:villager":
            continue
        depth = n["VillagerData"]["profession"]
        sel = (f"@e[type=minecraft:villager,tag=heraldia_mediana.{mid},x={x0},y={y0},z={z0},dx=40,dy=30,dz=40,"
               f"nbt={{NoAI:1b,Invulnerable:1b,VillagerData:{{profession:\"{depth}\"}}}}]")
        if not ctx.until(f"execute if entity {sel}"):
            fails.append(f"{name}: falta el aldeano {depth} quieto e invulnerable")
            continue
        first_item = n["Offers"]["Recipes"][0]["sell"]["id"]
        if not ctx.test(f"execute if entity {sel[:-1]},nbt={{Offers:{{Recipes:[{{sell:{{id:\"{first_item}\"}}}}]}}}}]"):
            fails.append(f"{name}: el aldeano {depth} no tiene sus tratos (vende {first_item})")
    return fails


def check_structures(ctx):
    fails, timings = [], {}
    k = 0
    for mid, mod in mediums.modules():
        if mediums.dimension(mod) != "overworld":
            continue                                       # en su dimensión: tools/smoke/nether_end.py
        for style in mod.STYLES:
            x, z = PLACE_X + k * STEP, PLACE_Z - 400
            k += 1
            forceload(ctx, x - 8, z - 8, x + 47, z + 47)
            for _ in range(s.PLACE_ATTEMPTS):
                t0 = time.monotonic()
                m = ctx.run(f"place structure heraldia:medianas/{mid}/{style} {x} ~ {z}", r"Generated structure")
                timings[f"{mid}/{style}"] = time.monotonic() - t0
                if "not loaded" not in m.group(0):
                    break
                time.sleep(s.PLACE_RETRY_S)
            if "Generated" not in m.group(0):
                fails.append(f"place structure {mid}/{style}: {m.string.strip()}")
            forceload(ctx, x - 8, z - 8, x + 47, z + 47, remove=True)
    if timings:
        print("/place structure de medianas (s): " + ", ".join(f"{k} {v:.2f}" for k, v in timings.items()))
    return fails


def check_loot(ctx):
    fails = []
    forceload(ctx, PLACE_X, PLACE_Z, PLACE_X, PLACE_Z)      # los objetos sueltos solo se ven en un chunk cargado
    for mid, mod in mediums.modules():
        for tbl in mod.LOOT:
            m = ctx.run(f"loot spawn {PLACE_X} 120 {PLACE_Z} loot heraldia:medianas/{mid}/{tbl}", r"Dropped \d+|No items")
            if not m.group(0).startswith("Dropped"):
                fails.append(f"loot heraldia:medianas/{mid}/{tbl}: {m.string.strip()}")
    if not ctx.until(f"execute if entity @e[type=minecraft:item,nbt={{Item:{{id:\"minecraft:written_book\"}}}}]") \
            and not _diary(ctx):
        fails.append("el cofre de la celda de la ermita no da el diario (libro escrito)")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    forceload(ctx, PLACE_X, PLACE_Z, PLACE_X, PLACE_Z, remove=True)
    return fails


def _diary(ctx):
    ctx.run(f"loot spawn {PLACE_X} 120 {PLACE_Z} loot heraldia:medianas/ermita/celda", r"Dropped \d+|No items")
    return ctx.until(f"execute if entity @e[type=minecraft:item,nbt={{Item:{{id:\"minecraft:written_book\"}}}}]", timeout=10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-estructuras-medianas"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    ts = templates()
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    with open(os.path.join(a.work, "config", "heraldia.json"), "w") as f:
        json.dump({}, f)                 # configuración por defecto
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        log = ctx.log()
        kinds = [mid for mid, _ in mediums.modules()]
        overworld_ids = [mid for mid, mod in mediums.modules() if mediums.dimension(mod) == "overworld"]
        for mid, mod in mediums.modules():
            if mid not in overworld_ids:
                continue                                   # las del Nether y el End: tools/smoke/nether_end.py
            sp = round(mod.SEPARATION / 16)
            vec = getattr(mod, "BIOME_NEIGHBORS", None)    # biomas en franja (playas): la búsqueda pide menos vecinos
            m = re.search(rf"rejilla medianas/{mid}: activada, cada {sp} chunks \(separación mínima {(DISTANCE + 15) // 16}, "
                          r"origen desplazado\)([^\n]*)", log)
            remainder = m.group(1) if m else ""
            neighbors = re.search(r", (\d) de 9 vecinos", remainder)
            if not m or f"candidata en el bioma #heraldia:medianas/{mid}" not in remainder \
                    or (int(neighbors.group(1)) if neighbors else None) != (vec if vec and vec != 6 else None):
                fails.append(f"falta en el log la rejilla de medianas/{mid} (cada {sp} chunks, bioma_vecinos {vec}): {remainder}")
        ctx.run("gamerule spawn_mobs false", r"Gamerule|set to|now")
        fails += check_templates(ctx, ts)
        fails += check_structures(ctx)
        fails += check_loot(ctx)
        fails += check_locate(ctx, overworld_ids)
        if not re.search(rf"estructuras medianas: activadas, {len(kinds)} tipos, frecuencia 100 %, a {ZONE} bloques de aldeas "
                         rf"y únicas y a {DISTANCE} entre ellas", ctx.log()):
            fails.append("falta en el log la regla de las medianas con su configuración por defecto")
        m = ctx.run("heraldia info", r"Registered structures: \d+ \(\d+ villages, \d+ unique, (\d+) medium and \d+ mine|"
                                     r"Estructuras registradas: \d+ \(\d+ de aldeas, \d+ únicas, (\d+) medianas y \d+ ")
        n = m.group(1) or m.group(2) if m.lastindex else None
        expected_counts = sum(len(mod.STYLES) for _, mod in mediums.modules())
        if n is None or int(n) != expected_counts:
            fails.append(f"/heraldia info: {n} medianas registradas, esperadas {expected_counts}: {m.string.strip()}")
        text = "".join(ctx.seen[-40:])
        n = len(kinds)
        if not re.search(rf"Medium structures: enabled; {n} of {n} types enabled|Estructuras medianas: activada; {n} de {n} tipos", text):
            fails.append("/heraldia info no resume las medianas")
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            proc.wait(timeout=120)
    print("MEDIANAS:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
