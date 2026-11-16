"""Estructuras medianas (tools/gen/medianas) en un servidor dedicado 26.3 real, con la configuración por defecto.

Uso: python3 tools/smoke/estructuras_medianas.py --jar build/libs/heraldia-X.jar [--work build/smoke-estructuras-medianas]
Comprueba:
- el log: la regla de las medianas y la rejilla de cada tipo con su separación por defecto;
- /locate de cada tipo (#heraldia:medianas/<tipo>) desde varios puntos, a una distancia razonable, y desde cada una
  /heraldia info cerca: ninguna aldea ni única a menos de medianas.distancia_aldeas_unicas_bloques ni otra mediana de
  otro tipo a menos de medianas.distancia_minima.bloques (info cerca da la más cercana de cada rejilla con las reglas de
  la generación); luego se genera de verdad (forceload) y la estructura está donde dijo /locate;
- /place template de cada variante: cada contenedor con su tabla y las entidades esperadas (etiqueta heraldia_mediana.<tipo>);
- /place structure de cada estilo (el pool y la estructura cargan) y su tiempo;
- loot spawn de cada tabla (el diario de la ermita es un libro escrito) y /heraldia info con su resumen.
Código 0 si todo pasa.
"""
import argparse, json, math, os, queue, re, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

sys.path.insert(0, os.path.join(s.ROOT, "tools", "gen"))
import medianas                      # noqa: E402  (el generador: tipos, plantillas y botín)
from pack import Registry           # noqa: E402

PUNTOS = [(0, 0), (3000, -2000), (-4000, 3500)]
LOCATE_MAX = 4000                    # bloques: con la separación por defecto (700-900 por tipo) sobra
ZONA, DISTANCIA = 256, 192           # valores por defecto (opciones.py)
PLACE_X, PLACE_Z, PASO = 30000, 30000, 48


def plantillas():
    reg = Registry()
    for mid, _ in medianas.modules():
        medianas.build(reg, mid)
    assert not reg.warnings, reg.warnings
    return {n: t for n, t in reg.templates.items() if n.startswith("medianas/")}


def forceload(ctx, x0, z0, x1, z1, quitar=False):
    ctx.run(f"forceload {'remove' if quitar else 'add'} {x0} {z0} {x1} {z1}", r"Marked|[Aa]dded|[Rr]emoved|force|already|[Uu]nmarked")


def info_cerca(ctx, x, z, radio):
    """{id: (distancia, x, z)} de /heraldia info cerca desde x, z."""
    m = ctx.run(f"execute positioned {x} 64 {z} run heraldia info cerca {radio}",
                r"info cerca \d+ en [^:]+: \d+ estructuras en (\d+) ms")
    if not m.lastindex:
        return None
    return {g[0]: (int(g[1]), int(g[2]), int(g[3])) for g in s.INFO_LINE.findall("".join(s.drain(ctx)))}


def comprobar_locate(ctx, tipos):
    fails, tiempos = [], []
    for mid in tipos:
        encontradas = 0
        for x, z in PUNTOS:
            t0 = time.monotonic()
            m = ctx.run(f"execute positioned {x} 64 {z} run locate structure #heraldia:medianas/{mid}",
                        r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
            tiempos.append(time.monotonic() - t0)
            if not m.group(1):
                fails.append(f"/locate no encuentra {mid} desde {x}, {z}")
                continue
            px, pz = int(m.group(1)), int(m.group(2))
            d = math.dist((x, z), (px, pz))
            print(f"{mid} desde {x}, {z}: en {px}, {pz} a {d:.0f} bloques ({tiempos[-1]:.2f} s)")
            if d > LOCATE_MAX:
                fails.append(f"{mid} desde {x}, {z} a {d:.0f} bloques (> {LOCATE_MAX})")
            encontradas += 1
            cerca = info_cerca(ctx, px, pz, 600)
            if cerca is None:
                fails.append(f"/heraldia info cerca desde {mid} en {px}, {pz} no responde")
                continue
            for sid, (dist, *_) in cerca.items():
                if ":medianas/" not in sid:                   # aldeas (heraldia:aldeas o su estilo) y únicas
                    if dist < ZONA:
                        fails.append(f"{mid} en {px}, {pz} a {dist} bloques de {sid} (< {ZONA})")
                elif f"medianas/{mid}" not in sid and dist < DISTANCIA:
                    fails.append(f"{mid} en {px}, {pz} a {dist} bloques de {sid} (< {DISTANCIA})")
            if (x, z) == PUNTOS[0]:      # la primera se genera de verdad: el inicio está donde dijo /locate
                forceload(ctx, px - 32, pz - 32, px + 31, pz + 31)
                if not wait_generated(ctx, px, pz, mid):
                    fails.append(f"{mid}: /locate da {px}, {pz} pero ahí no se ha generado")
        if not encontradas:
            fails.append(f"ningún {mid}")
    if tiempos:
        print(f"/locate de medianas: {len(tiempos)} búsquedas, media {sum(tiempos) / len(tiempos):.2f} s, máxima {max(tiempos):.2f} s")
    return fails


def wait_generated(ctx, x, z, mid):
    """/heraldia info aqui junto al inicio (la pieza sale hacia un cuadrante u otro según su giro), a la altura del
    terreno (dentro de la caja de la pieza), dice que estás en la mediana. Solo mira chunks ya cargados."""
    end = time.monotonic() + s.UNTIL_S
    while time.monotonic() < end:
        for dx, dz in ((6, 6), (-6, 6), (6, -6), (-6, -6)):
            m = ctx.run(f"execute positioned {x + dx} 0 {z + dz} positioned over world_surface positioned ~ ~-2 ~ "
                        f"run heraldia info aqui",
                        r"\((heraldia:[^)]+)\)|no hay ninguna|no Heraldia|not loaded|no está cargada")
            if m.group(1) and f"medianas/{mid}/" in m.group(1):
                return True
        time.sleep(2)
    return False


def comprobar_plantillas(ctx, ts):
    fails = []
    for k, (name, t) in enumerate(sorted(ts.items())):
        x, z = PLACE_X + (k % 5) * PASO, PLACE_Z + (k // 5) * PASO
        y = 100
        forceload(ctx, x - 8, z - 8, x + 47, z + 47)
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
        forceload(ctx, x - 8, z - 8, x + 47, z + 47, quitar=True)
    return fails


def comprobar_estructuras(ctx):
    fails, tiempos = [], {}
    k = 0
    for mid, mod in medianas.modules():
        for estilo in mod.ESTILOS:
            x, z = PLACE_X + k * PASO, PLACE_Z - 400
            k += 1
            forceload(ctx, x - 8, z - 8, x + 47, z + 47)
            for _ in range(s.PLACE_ATTEMPTS):
                t0 = time.monotonic()
                m = ctx.run(f"place structure heraldia:medianas/{mid}/{estilo} {x} ~ {z}", r"Generated structure")
                tiempos[f"{mid}/{estilo}"] = time.monotonic() - t0
                if "not loaded" not in m.group(0):
                    break
                time.sleep(s.PLACE_RETRY_S)
            if "Generated" not in m.group(0):
                fails.append(f"place structure {mid}/{estilo}: {m.string.strip()}")
            forceload(ctx, x - 8, z - 8, x + 47, z + 47, quitar=True)
    if tiempos:
        print("/place structure de medianas (s): " + ", ".join(f"{k} {v:.2f}" for k, v in tiempos.items()))
    return fails


def comprobar_botin(ctx):
    fails = []
    forceload(ctx, PLACE_X, PLACE_Z, PLACE_X, PLACE_Z)      # los objetos sueltos solo se ven en un chunk cargado
    for mid, mod in medianas.modules():
        for tabla in mod.LOOT:
            m = ctx.run(f"loot spawn {PLACE_X} 120 {PLACE_Z} loot heraldia:medianas/{mid}/{tabla}", r"Dropped \d+|No items")
            if not m.group(0).startswith("Dropped"):
                fails.append(f"loot heraldia:medianas/{mid}/{tabla}: {m.string.strip()}")
    if not ctx.until(f"execute if entity @e[type=minecraft:item,nbt={{Item:{{id:\"minecraft:written_book\"}}}}]") \
            and not _diario(ctx):
        fails.append("el cofre de la celda de la ermita no da el diario (libro escrito)")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    forceload(ctx, PLACE_X, PLACE_Z, PLACE_X, PLACE_Z, quitar=True)
    return fails


def _diario(ctx):
    ctx.run(f"loot spawn {PLACE_X} 120 {PLACE_Z} loot heraldia:medianas/ermita/celda", r"Dropped \d+|No items")
    return ctx.until(f"execute if entity @e[type=minecraft:item,nbt={{Item:{{id:\"minecraft:written_book\"}}}}]", timeout=10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-estructuras-medianas"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    ts = plantillas()
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
        tipos = [mid for mid, _ in medianas.modules()]
        for mid, mod in medianas.modules():
            sp = round(mod.SEPARACION / 16)
            if not re.search(rf"rejilla medianas/{mid}: activada, cada {sp} chunks \(separación mínima {(DISTANCIA + 15) // 16}, "
                             r"origen desplazado\)", log):
                fails.append(f"falta en el log la rejilla de medianas/{mid} (cada {sp} chunks)")
        ctx.run("gamerule spawn_mobs false", r"Gamerule|set to|now")
        fails += comprobar_plantillas(ctx, ts)
        fails += comprobar_estructuras(ctx)
        fails += comprobar_botin(ctx)
        fails += comprobar_locate(ctx, tipos)
        if not re.search(rf"estructuras medianas: activadas, {len(tipos)} tipos, frecuencia 100 %, a {ZONA} bloques de aldeas "
                         rf"y únicas y a {DISTANCIA} entre ellas", ctx.log()):
            fails.append("falta en el log la regla de las medianas con su configuración por defecto")
        m = ctx.run("heraldia info", r"Registered structures: \d+ \(\d+ villages, \d+ unique and (\d+) medium\)|"
                                     r"Estructuras registradas: \d+ \(\d+ de aldeas, \d+ únicas y (\d+) medianas\)")
        n = m.group(1) or m.group(2) if m.lastindex else None
        esperadas = sum(len(mod.ESTILOS) for _, mod in medianas.modules())
        if n is None or int(n) != esperadas:
            fails.append(f"/heraldia info: {n} medianas registradas, esperadas {esperadas}: {m.string.strip()}")
        texto = "".join(ctx.seen[-40:])
        if not re.search(r"Medium structures: enabled; 4 of 4 types enabled|Estructuras medianas: activada; 4 de 4 tipos", texto):
            fails.append("/heraldia info no resume las medianas")
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            proc.wait(timeout=120)
    print("MEDIANAS:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
