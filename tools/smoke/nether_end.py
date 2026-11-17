"""Contenido de Heraldia en el Nether y el End (T44) en un servidor dedicado 26.3 real, con la configuración por defecto.

Uso: python3 tools/smoke/nether_end.py --jar build/libs/heraldia-X.jar [--work build/smoke-nether-end]
Comprueba:
- el log: la rejilla de cada mediana y única del Nether y el End con su separación por defecto, sin búsqueda de bioma
  (solo lee el ruido del mundo principal) ni zona de exclusión de las aldeas vanilla;
- /locate (con /execute in) de cada tipo en su dimensión, a una distancia razonable, y que en el mundo principal no
  hay ninguna (sus rejillas no están allí);
- que de verdad se generan donde dice /locate: se fuerza la carga alrededor y /heraldia info here, a la altura de la
  pieza, dice que se está dentro; el guardián de cada única sale bajo el techo de bedrock (Nether) o sobre su isla (End),
  con la tabla de su trofeo;
- /place structure de cada estilo y de cada única en su dimensión (con sus guardianes);
- /heraldia info nearby desde el Nether y el End: las de su dimensión;
- loot spawn de cada tabla nueva, varias veces, sin nada de la lista prohibida (netherita, élitros, lo del dragón).
Código 0 si todo pasa.
"""
import argparse, json, math, os, queue, re, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

sys.path.insert(0, os.path.join(s.ROOT, "tools", "gen"))
import dimensiones                   # noqa: E402  (el generador: qué es de cada dimensión)
import medianas                      # noqa: E402
import unicas                        # noqa: E402

DIM = {"nether": "minecraft:the_nether", "end": "minecraft:the_end"}
# Desde dónde se busca: en el End, fuera de la isla central (las islas exteriores empiezan a ~1.000 bloques)
ORIGEN = {"nether": [(0, 0), (1500, -1200)], "end": [(2000, 0), (-1800, 1800)]}
LOCATE_MAX = 4000
PLACE = {"nether": (4000, 4000), "end": (6000, 6000)}
PASO = 64
TIRADAS = 3


def tipos():
    med = [(mid, m) for mid, m in medianas.modules() if dimensiones.de(m) != dimensiones.PRINCIPAL]
    uni = [(sid, m) for sid, m in unicas.modules() if dimensiones.de(m) != dimensiones.PRINCIPAL]
    return med, uni


def en(dim, cmd):
    return f"execute in {DIM[dim]} {cmd}"


def forceload(ctx, dim, x0, z0, x1, z1, quitar=False):
    ctx.run(en(dim, f"run forceload {'remove' if quitar else 'add'} {x0} {z0} {x1} {z1}"),
            r"Marked|[Aa]dded|[Rr]emoved|force|already|[Uu]nmarked")


def locate(ctx, dim, objetivo, x, z):
    m = ctx.run(en(dim, f"positioned {x} 64 {z} run locate structure {objetivo}"), r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
    return (int(m.group(1)), int(m.group(2))) if m.group(1) else None


def dentro(ctx, dim, x, z, ruta, ys):
    """/heraldia info here en (x, y, z) para alguna y de `ys` y alrededor del inicio: ¿dice que se está en `ruta`?"""
    # /locate da la esquina NO del chunk; el inicio va en su centro o a medio chunk de él (DimensionStructure.PUNTOS)
    for dx, dz in ((8, 8), (16, 8), (0, 8), (8, 16), (8, 0)):
        for y in ys:
            m = ctx.run(en(dim, f"positioned {x + dx} {y} {z + dz} run heraldia info here"),
                        r"\((heraldia:[^)]+)\)|no hay ninguna|no Heraldia|not loaded|no está cargada")
            if m.group(1) and ruta in m.group(1):
                return True
    return False


def alturas(dim):
    # En el Nether, a ojo entre el mar de lava y el techo; en el End, cerca de la superficie de las islas
    return range(36, 118, 5) if dim == "nether" else range(46, 90, 5)


def comprobar_log(ctx, med, uni):
    fails, log = [], ctx.log()
    for mid, mod in med:
        sp = round(mod.SEPARACION / 16)
        m = re.search(rf"rejilla medianas/{mid}: activada, cada {sp} chunks \([^)]*origen desplazado\), sin máximo, exclusión ninguna([^\n]*)", log)
        if not m or "candidata en el bioma" in m.group(1):
            fails.append(f"falta en el log la rejilla de medianas/{mid} (cada {sp} chunks, sin bioma ni exclusión)")
    for sid, mod in uni:
        sp = round(mod.STRUCTURE["spacing"])
        if not re.search(rf"rejilla unicas/{sid}: activada, cada {sp} chunks", log):
            fails.append(f"falta en el log la rejilla de unicas/{sid} (cada {sp} chunks)")
    return fails


def comprobar_locate(ctx, med, uni):
    fails, generar = [], []
    for kind, lista in (("medianas", med), ("unicas", uni)):
        for i, mod in lista:
            dim = dimensiones.de(mod)
            objetivo = f"#heraldia:medianas/{i}" if kind == "medianas" else f"heraldia:unicas/{i}"
            for k, (x, z) in enumerate(ORIGEN[dim]):
                t0 = time.monotonic()
                p = locate(ctx, dim, objetivo, x, z)
                dt = time.monotonic() - t0
                if p is None:
                    fails.append(f"/locate no encuentra {objetivo} en {dim} desde {x}, {z}")
                    continue
                d = math.dist((x, z), p)
                print(f"{objetivo} ({dim}) desde {x}, {z}: en {p[0]}, {p[1]} a {d:.0f} bloques ({dt:.2f} s)")
                if d > LOCATE_MAX * (2 if kind == "unicas" else 1):
                    fails.append(f"{objetivo} en {dim} desde {x}, {z} a {d:.0f} bloques")
                if dim == "end" and math.hypot(*p) < 1000:
                    fails.append(f"{objetivo}: en la isla central del End ({p})")
                if k == 0:
                    generar.append((kind, i, dim, p))
            # en el mundo principal no hay ninguna (la búsqueda acaba enseguida: no hay rejilla allí)
            m = ctx.run(f"execute positioned 0 64 0 run locate structure {objetivo}", r"is at \[|Could not find|no structure|There is no")
            if m.group(0).startswith("is at"):
                fails.append(f"{objetivo} aparece en el mundo principal")
    return fails, generar


def comprobar_generadas(ctx, generar):
    """Genera de verdad la primera de cada tipo (forceload alrededor de lo que dijo /locate) y mira que está allí."""
    fails = []
    for kind, i, dim, (x, z) in generar:
        forceload(ctx, dim, x - 24, z - 24, x + 24, z + 24)
        ruta = f"medianas/{i}/" if kind == "medianas" else f"unicas/{i}"
        ok = False
        fin = time.monotonic() + s.UNTIL_S
        while time.monotonic() < fin and not ok:
            ok = dentro(ctx, dim, x, z, ruta, alturas(dim))
            if not ok:
                time.sleep(3)
        if not ok:
            fails.append(f"{ruta} ({dim}) no está donde dijo /locate ({x}, {z})")
        elif kind == "unicas":
            fails += guardian(ctx, i, dim)
        forceload(ctx, dim, x - 24, z - 24, x + 24, z + 24, quitar=True)
    return fails


def guardian(ctx, sid, dim):
    sel = f"@e[tag=heraldia_guardian.{sid},limit=1]"          # sin posición: busca en todas las dimensiones
    if not ctx.wait_entity(sel):
        return [f"{sid}: no aparece su guardián"]
    fails = []
    p = ctx.pos(sel)
    if p and dim == "nether" and not (dimensiones_y_min() <= p[1] < 123):
        fails.append(f"{sid}: guardián a y = {p[1]:.0f}, fuera del Nether jugable (sobre la lava y bajo el techo)")
    if p and dim == "end" and p[1] < 45:
        fails.append(f"{sid}: guardián a y = {p[1]:.0f} (sobre el vacío)")
    m = ctx.run(f"data get entity {sel} DeathLootTable", r'has the following entity data: "([^"]+)"|No entity')
    if not (m.group(1) or "").startswith(f"heraldia:guardianes/{sid}/"):
        fails.append(f"{sid}: el guardián no tiene la tabla del trofeo: {m.string.strip()}")
    m = ctx.run(f"data get entity {sel} Tags", r"has the following entity data: \[([^\]]*)\]|No entity")
    if "heraldia_guardian" not in (m.group(1) or ""):
        fails.append(f"{sid}: el guardián sin la etiqueta de los logros")
    return fails


def dimensiones_y_min():
    return 32


def comprobar_place(ctx, med, uni):
    fails, k = [], 0
    for mid, mod in med:
        dim = dimensiones.de(mod)
        for estilo in mod.ESTILOS:
            fails += place(ctx, dim, f"heraldia:medianas/{mid}/{estilo}", PLACE[dim][0] + k * PASO, PLACE[dim][1])
            k += 1
    for sid, mod in uni:
        dim = dimensiones.de(mod)
        x, z = PLACE[dim][0] + k * PASO, PLACE[dim][1] + 400
        k += 1
        ctx.run(f"kill @e[tag=heraldia_guardian.{sid}]", r"Killed|No entity")       # el de la generada, si sigue cargado
        fails += place(ctx, dim, f"heraldia:unicas/{sid}", x, z, quitar=False)       # sus entidades, con el chunk cargado
        if not ctx.wait_entity(f"@e[tag=heraldia_guardian.{sid}]"):
            fails.append(f"{sid}: /place sin guardián")
        ctx.run(f"kill @e[tag=heraldia_guardian.{sid}]", r"Killed|No entity")
        forceload(ctx, dim, x - 24, z - 24, x + 48, z + 48, quitar=True)
    return fails


def place(ctx, dim, sid, x, z, quitar=True):
    forceload(ctx, dim, x - 24, z - 24, x + 48, z + 48)
    m = None
    for _ in range(s.PLACE_ATTEMPTS):
        t0 = time.monotonic()
        m = ctx.run(en(dim, f"run place structure {sid} {x} 64 {z}"), r"Generated structure")
        print(f"/place {sid} en {dim}: {time.monotonic() - t0:.2f} s")
        if "not loaded" not in m.group(0):
            break
        time.sleep(s.PLACE_RETRY_S)
    if quitar:
        forceload(ctx, dim, x - 24, z - 24, x + 48, z + 48, quitar=True)
    return [] if "Generated" in m.group(0) else [f"place structure {sid} en {dim}: {m.string.strip()}"]


def comprobar_info(ctx, med, uni):
    fails = []
    for dim, (x, z) in (("nether", (0, 0)), ("end", (2000, 0))):
        m = ctx.run(en(dim, f"positioned {x} 64 {z} run heraldia info nearby 4000"),
                    r"info nearby \d+ en [^:]+: \d+ estructuras en (\d+) ms")
        texto = "".join(s.drain(ctx))
        vistos = {g[0] for g in s.INFO_LINE.findall(texto)}
        propios = {f"heraldia:medianas/{mid}" for mid, mod in med if dimensiones.de(mod) == dim}
        if not m.lastindex:
            fails.append(f"/heraldia info nearby en {dim} no responde")
            continue
        if not any(v.startswith("heraldia:medianas/") or v.startswith("heraldia:unicas/") for v in vistos):
            fails.append(f"/heraldia info nearby en {dim} no da ninguna de Heraldia: {sorted(vistos)}")
        ajenas = {v for v in vistos if v.startswith("heraldia:aldeas") or v.startswith("heraldia:minas/")}
        if ajenas:
            fails.append(f"/heraldia info nearby en {dim} da estructuras del mundo principal: {sorted(ajenas)}")
        print(f"info nearby en {dim}: {sorted(vistos)} (propias esperadas {sorted(propios)})")
    return fails


def comprobar_botin(ctx, med, uni):
    fails = []
    ctx.run("forceload add 0 0 0 0", r"Marked|[Aa]dded|force|already")
    tablas = [f"heraldia:medianas/{mid}/{t}" for mid, m in med for t in m.LOOT] + \
             [f"heraldia:unicas/{sid}/{t}" for sid, m in uni for t in m.LOOT]
    for t in tablas:
        for _ in range(TIRADAS):
            m = ctx.run(f"loot spawn 0 200 0 loot {t}", r"Dropped \d+|No items")
            if not m.group(0).startswith(("Dropped", "No items")):
                fails.append(f"loot {t}: {m.string.strip()}")
                break
    for o in dimensiones.PROHIBIDO:
        if ctx.test(f'execute if entity @e[type=minecraft:item,nbt={{Item:{{id:"minecraft:{o}"}}}}]'):
            fails.append(f"el botín del Nether o el End da {o}")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    ctx.run("forceload remove 0 0 0 0", r"[Uu]nmarked|[Rr]emoved|force")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-nether-end"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    med, uni = tipos()
    assert med and uni
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
        ctx.run("gamerule spawn_mobs false", r"Gamerule|set to|now")
        fails += comprobar_log(ctx, med, uni)
        f, generar = comprobar_locate(ctx, med, uni)
        fails += f
        fails += comprobar_generadas(ctx, generar)
        fails += comprobar_place(ctx, med, uni)
        fails += comprobar_info(ctx, med, uni)
        fails += comprobar_botin(ctx, med, uni)
        if re.search(r"Registry loading errors|Failed to load structure|Missing data pack", ctx.log()):
            fails.append("errores de carga en el log")
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            proc.wait(timeout=120)
    print("NETHER Y END:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
