"""Mobs anclados (heraldia_anclado) en un servidor dedicado 26.3 real, con un jugador simulado (complementa server_smoke.py).

Uso: python3 tools/smoke/guardianes_anclados.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke" [--veces N]
Un mob persistente con IA pasea hasta 10 bloques en los 100 primeros ticks de cada carga (RandomStrollGoal exige
noActionTime < 100, que no se guarda) y a veces salía de su sala; y el finalizeSpawn de zombis y esqueletos sortea
CanPickUpLoot sin mirar el NBT. El mod (comun/Anclaje.java) lo evita en los que llevan core.ANCLADO_TAG. Con cada mob
distinto con la etiqueta en las plantillas del .jar (los guardianes y los ahogados de la Atlántida):
  1) lo coloca --veces veces como pieza de pool (/place jigsaw: finalizeSpawn, como al generar) en su casilla de una
     plataforma, de noche y en difícil; ninguno puede recoger objetos y, tras 200 ticks, todos siguen en su casilla
     (±1,8 bloques; el guardián anciano, en una piscina, ±6: deriva en el agua y vuelve a su casa de 16 bloques). Un lote de control sin la etiqueta (el mismo esqueleto y el mismo zombi) debe pasear y recoger
     objetos alguna vez: si no, la prueba no comprobaría nada;
  2) descarga y vuelve a cargar los chunks (noActionTime vuelve a 0) y, tras otros 200 ticks, siguen en su casilla;
  3) con un jugador simulado (Carpet) a 8 bloques, cada uno lo ataca (le quita vida): anclado no quiere decir tonto;
  4) coloca de día la plantilla real de cada guardián (/place template) y, tras 200 ticks, sigue donde apareció.
"""
import argparse, gzip, io, json, os, queue, shutil, subprocess, sys, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomas import fetch
from trofeos import CARPET
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
import nbtlib
from nbtlib.tag import Compound, List, String
import core

PACK, NS, ANCLA = "heraldia_prueba_anclados", "heraldia_prueba", "heraldia_prueba:ancla"
ACUATICOS = {"minecraft:guardian", "minecraft:elder_guardian"}    # fuera del agua coletean: van en una piscina
Y = 150
X1, Z1, PASO, COLS = 2000, 0, 4, 10                  # fases 1 y 2: un bloque de COLS x filas casillas por mob
X3, Z3 = 4000, 0                                     # fase 3: jugador y mob
X4, Z4, Y4 = 6000, 0, 120                            # fase 4: plantillas reales
PLAYER, DIST = "Testigo", 8
CONTROL = "heraldia_prueba_control"


def mobs(jar):
    """[(nombre, nbt)]: un mob de cada NBT distinto (sin posición) con core.ANCLADO_TAG en las plantillas del .jar, y
    [(plantilla, id, tamaño, nbt)] de las plantillas que tienen un guardián final."""
    out, seen, rooms = [], set(), []
    with zipfile.ZipFile(jar) as z:
        for n in sorted(z.namelist()):
            if not (n.startswith("data/heraldia/structure/") and n.endswith(".nbt")):
                continue
            t = nbtlib.File.parse(io.BytesIO(gzip.decompress(z.read(n))))
            name = n[len("data/heraldia/structure/"):-4]
            for e in t.get("entities", []):
                nbt = Compound(e["nbt"])
                tags = [str(x) for x in nbt.get("Tags", [])]
                if core.ANCLADO_TAG not in tags:
                    continue
                if "heraldia_guardian" in tags:
                    rooms.append((name, next(x for x in tags if x.startswith("heraldia_guardian.")),
                                  [int(v) for v in t["size"]], str(nbt["id"])))
                nbt.pop("Pos", None)
                nbt.pop("UUID", None)
                key = nbt.snbt()
                if key not in seen:
                    seen.add(key)
                    out.append((f"{name} ({str(nbt['id']).split(':')[-1]})", nbt))
    return out, rooms


def control(found, mob):
    """El primer mob anclado de ese tipo sin la etiqueta (ni la de guardián): se comporta como uno vanilla."""
    for name, nbt in found:
        if str(nbt["id"]) == mob:
            c = Compound(nbt)
            c["Tags"] = List[String]([String(CONTROL)] + [String(t) for t in nbt["Tags"]
                                     if not str(t).startswith(("heraldia_guardian", core.ANCLADO_TAG))])
            return (f"control sin anclar ({mob.split(':')[-1]})", c)
    return None


def write_pack(work, lotes):
    """Paquete de datos en world/datapacks (el servidor lo activa al crear el mundo): por lote, una plantilla (jigsaw +
    el mob encima, con la etiqueta heraldia_prueba_m<i>), su pool y una función con sus colocaciones."""
    root = os.path.join(work, "world", "datapacks", PACK)
    with open(os.path.join(os.makedirs(root, exist_ok=True) or root, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"description": "Heraldia: prueba de mobs anclados", "min_format": 121, "max_format": 121}}, f)
    data = os.path.join(root, "data", NS)
    for d in ("structure", "worldgen/template_pool", "function"):
        os.makedirs(os.path.join(data, d), exist_ok=True)
    for i, lote in enumerate(lotes):
        nbt = Compound(lote["nbt"])
        nbt["Tags"] = List[String]([String(t) for t in nbt.get("Tags", [])] + [String(f"heraldia_prueba_m{i}")])
        t = core.Template(f"m{i}")
        t.set(0, 0, 0, "minecraft:stone")
        t.jigsaw(0, 1, 0, "up_north", ANCLA, "minecraft:empty", "minecraft:empty", joint="rollable")
        t.entity(0, 1, 0, nbt)
        nbtlib.File(t.to_nbt(), gzipped=True).save(os.path.join(data, "structure", f"m{i}.nbt"))
        with open(os.path.join(data, "worldgen", "template_pool", f"m{i}.json"), "w") as f:
            json.dump({"fallback": "minecraft:empty", "elements": [{"weight": 1, "element": {
                "element_type": "minecraft:single_pool_element", "location": f"{NS}:m{i}",
                "projection": "rigid", "processors": "minecraft:empty"}}]}, f)
        with open(os.path.join(data, "function", f"m{i}.mcfunction"), "w") as f:
            for (x, z) in lote["celdas"]:
                f.write(f"place jigsaw {NS}:m{i} {ANCLA} 1 {x} {Y} {z}\n")
        with open(os.path.join(data, "function", f"j{i}.mcfunction"), "w") as f:
            f.write(f"place jigsaw {NS}:m{i} {ANCLA} 1 {X3} {Y} {Z3 + DIST}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke"))
    ap.add_argument("--veces", type=int, default=30)
    ap.add_argument("--solo", default="", help="solo los mobs y plantillas cuyo nombre contenga esto (depurar)")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    found, rooms = mobs(a.jar)
    found = [f for f in found if a.solo in f[0]]
    rooms = [r for r in rooms if a.solo in r[0]]
    lotes = [{"nombre": n, "nbt": nbt, "control": False} for n, nbt in found]
    for mob in ("minecraft:skeleton", "minecraft:zombie"):
        c = control(found, mob)
        if c:
            lotes.append({"nombre": c[0], "nbt": c[1], "control": True})
    rows = -(-a.veces // COLS)
    z = Z1
    for lote in lotes:
        if str(lote["nbt"]["id"]) in ACUATICOS:
            # En el agua derivan unos bloques (no es el paseo, que también tienen bloqueado), y el guardián anciano se
            # pone él solo una casa de 16 bloques adonde vuelve: ±6 bloques bastan para seguir en su sala (la del
            # Guardián de Poseidón mide 25 x 25). Casillas a 20 bloques y menos colocaciones (el agua cuesta).
            paso, cols, veces, lote["tol"] = 20, 5, min(a.veces, 10), 6
        else:
            paso, cols, veces, lote["tol"] = PASO, COLS, a.veces * (4 if lote["control"] else 1), 1
        lote["celdas"] = [(X1 + (k % cols) * paso, z + (k // cols) * paso) for k in range(veces)]
        lote["caja"] = (X1 - 2, z - 2, X1 + cols * paso + 2, z + (-(-veces // cols)) * paso + 2)
        z = lote["caja"][3] + 4
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    write_pack(a.work, lotes)
    proc = subprocess.Popen(["java", "-Xmx3G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    fails = []
    x_max = max(l["caja"][2] for l in lotes)

    def forceload(x0, z0, x1, z1, add=True):
        ctx.run(f"forceload {'add' if add else 'remove'} {x0} {z0} {x1} {z1}", r"Marked|Added|Removed|force|already|Unmarked")

    def fill(x0, y0, z0, x1, y1, z1, block, mode=""):
        for _ in range(s.PLACE_ATTEMPTS):   # los chunks forzados tardan en cargarse
            m = ctx.run(f"fill {x0} {y0} {z0} {x1} {y1} {z1} {block} {mode}".strip(), r"Successfully filled|No blocks|not loaded|too many")
            if "not loaded" not in m.string:
                return m
            time.sleep(s.PLACE_RETRY_S)
        raise SystemExit(f"no se cargan los chunks de {x0} {z0}")

    def sel(i, extra=""):
        return f"@e[tag=heraldia_prueba_m{i}{extra}]"

    def vacias(i, lote):
        """Casillas del lote sin su mob (a más de tol + 0,8 bloques en horizontal: el selector mira la caja de colisión)."""
        t = lote["tol"]
        return [(x, z) for (x, z) in lote["celdas"]
                if ctx.count(sel(i, f",x={x - t},y={Y - 1},z={z - t},dx={2 * t},dy=6,dz={2 * t}")) < 1]

    def comprobar(fase):
        for i, lote in enumerate(lotes):
            v, total = vacias(i, lote), ctx.count(sel(i))
            fuera = len(v)
            print(f"anclados: {fase}: {lote['nombre']}: {total} en el mundo, {fuera} de {len(lote['celdas'])} fuera de su casilla")
            for (x, z) in v[:3]:        # dónde está el más cercano a la casilla vacía
                print(f"anclados:   casilla ({x + 0.5}, {Y}, {z + 0.5}): el más cercano en "
                      f"{ctx.pos(sel(i, f',x={x + 0.5},y={Y},z={z + 0.5},sort=nearest,limit=1'))}")
            if lote["control"]:
                lote.setdefault("fuera", []).append(fuera)
            elif total != len(lote["celdas"]) or fuera:
                fails.append(f"{fase}: {lote['nombre']}: {fuera} de {len(lote['celdas'])} fuera de su casilla ({total} en el mundo)")

    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        m = ctx.run("datapack list enabled", r"data pack\(s\) enabled: (.*)|no data packs")
        if PACK not in m.group(0):
            raise SystemExit(f"el paquete de prueba {PACK} no está activado: {m.string.strip()}")
        # De noche, sin que avance el tiempo, sin monstruos naturales y en difícil (CanPickUpLoot sale con más
        # probabilidad cuanto más difícil: el control debe sacar alguno).
        ctx.run("time set midnight", r"Set .*time")
        for rule in ("advance_time", "spawn_mobs"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
        ctx.run("difficulty hard", r"difficulty|Difficulty")

        # 1) colocación: en su casilla tras 200 ticks y sin recoger objetos
        for lote in lotes:
            x0, z0, x1, z1 = lote["caja"]
            forceload(x0 - 1, z0 - 1, x1 + 1, z1 + 1)
            fill(x0, Y - 1, z0, x1, Y - 1, z1, "minecraft:stone")
            fill(x0 - 1, Y - 1, z0 - 1, x1 + 1, Y + 6, z1 + 1, "minecraft:barrier", "outline")
            if str(lote["nbt"]["id"]) in ACUATICOS:
                fill(x0, Y, z0, x1, Y + 5, z1, "minecraft:water")
        print(f"anclados: {len(found)} mobs distintos con {core.ANCLADO_TAG}; {len(rooms)} plantillas con guardián")
        for i, lote in enumerate(lotes):
            ctx.run(f"function {NS}:m{i}", r"Running function|Ran \d+ command")
        for i, lote in enumerate(lotes):
            end = time.monotonic() + s.UNTIL_S
            while ctx.count(sel(i)) < len(lote["celdas"]) and time.monotonic() < end:
                time.sleep(s.POLL_S)
            recogen = ctx.count(sel(i, ",nbt={CanPickUpLoot:1b}"))
            print(f"anclados: {lote['nombre']}: {ctx.count(sel(i))} colocados, {recogen} pueden recoger objetos")
            if lote["control"]:
                lote["recogen"] = recogen
            elif recogen:
                fails.append(f"{lote['nombre']}: {recogen} de {len(lote['celdas'])} pueden recoger objetos")
        ctx.ticks(200)
        comprobar("al colocarse")

        # 2) descarga y recarga de los chunks: noActionTime vuelve a 0 y el juego los dejaría pasear otra vez
        ctx.run("forceload remove all", r"Unmarked|Removed|No force|force")
        if not ctx.until(f"execute if entity @e[tag={core.ANCLADO_TAG}]", want=False):
            fails.append("los chunks de la prueba no se descargan")
        for lote in lotes:
            x0, z0, x1, z1 = lote["caja"]
            forceload(x0 - 1, z0 - 1, x1 + 1, z1 + 1)
        for i, lote in enumerate(lotes):
            if not ctx.until(f"execute if entity {sel(i)}"):
                fails.append(f"{lote['nombre']}: no vuelve a cargarse")
        ctx.ticks(200)
        comprobar("tras recargar")
        for lote in lotes:
            if lote["control"]:
                if not any(lote["fuera"]):
                    fails.append(f"{lote['nombre']}: ninguno ha paseado; la prueba no comprueba el anclaje")
                if lote["nombre"].endswith("(zombie)") and not lote["recogen"]:
                    fails.append(f"{lote['nombre']}: ninguno puede recoger objetos; la prueba no comprueba CanPickUpLoot")
        ctx.run(f"kill @e[type=!minecraft:player,x={X1 - 4},y={Y - 4},z={Z1 - 4},dx={x_max - X1 + 8},dy=14,dz={z - Z1 + 8}]",
                r"Killed|No entity was found")
        ctx.run("forceload remove all", r"Unmarked|Removed|No force|force")

        # 3) con un jugador a DIST bloques, lo ataca
        forceload(X3 - 4, Z3 - 4, X3 + 4, Z3 + DIST + 4)
        fill(X3 - 4, Y - 1, Z3 - 4, X3 + 4, Y - 1, Z3 + DIST + 4, "minecraft:stone")
        fill(X3 - 5, Y - 1, Z3 - 5, X3 + 5, Y + 6, Z3 + DIST + 5, "minecraft:barrier", "outline")
        zona = f"x={X3 - 4},y={Y - 1},z={Z3 - 4},dx=8,dy=8,dz={DIST + 8}"
        sano = f"execute if entity @a[name={PLAYER},nbt={{Health:20.0f}}]"

        def jugador():
            """El jugador, vivo (si murió, otra vez), en su sitio y con toda la vida."""
            for _ in range(3):
                if not ctx.test(f"execute if entity @a[name={PLAYER}]"):
                    ctx.run(f"player {PLAYER} spawn at {X3 + 0.5} {Y} {Z3 + 0.5}", r"joined the game|Player .* spawn|Unknown|Incorrect")
                    if not ctx.until(f"execute if entity @a[name={PLAYER}]"):
                        raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
                    ctx.run(f"gamemode survival {PLAYER}", r"Set .* game mode|game mode")
                ctx.run(f"tp {PLAYER} {X3 + 0.5} {Y} {Z3 + 0.5}", r"Teleported|No entity")
                ctx.run(f"effect give {PLAYER} minecraft:instant_health 1 10", r"Applied|Gave|effect|Unable|No entity")
                ctx.run(f"effect clear {PLAYER}", r"Removed|effect|Unable|No entity")
                if ctx.until(sano, timeout=15):
                    return True
            return False

        for i, lote in enumerate(lotes):
            if lote["control"] or str(lote["nbt"]["id"]) in ACUATICOS:
                continue
            if not jugador():
                fails.append(f"ataque: el jugador no recupera la vida antes de {lote['nombre']}")
                continue
            ctx.run(f"function {NS}:j{i}", r"Running function|Ran \d+ command")
            if not ctx.wait_entity(sel(i)):
                fails.append(f"ataque: {lote['nombre']}: no aparece")
                continue
            t0 = time.monotonic()
            ok = ctx.until(sano, want=False)
            print(f"anclados: ataque: {lote['nombre']}: {'ataca' if ok else 'NO ataca'} ({time.monotonic() - t0:.1f} s)")
            if not ok:
                fails.append(f"ataque: {lote['nombre']} no ataca al jugador a {DIST} bloques")
            ctx.run(f"kill @e[type=!minecraft:player,{zona}]", r"Killed|No entity was found")
            for t in ("vex", "evoker_fangs", "arrow", "trident", "item"):   # los vexes atraviesan la barrera
                ctx.run(f"kill @e[type=minecraft:{t}]", r"Killed|No entity was found")
        ctx.run(f"player {PLAYER} kill", r"left the game|Killed|died|No player|Unknown|Incorrect|Can only manipulate")
        ctx.run("forceload remove all", r"Unmarked|Removed|No force|force")

        # 4) la plantilla real de cada guardián, de día: sigue donde apareció
        ctx.run("time set noon", r"Set .*time")
        for k, (name, tag, size, mob) in enumerate(rooms):
            x4 = X4 + 320 * k                        # cada plantilla en su sitio: sin restos de la anterior
            if mob in ACUATICOS:
                print(f"anclados: sala: {name}: {mob} (acuático) se omite; probado en la piscina de la fase 1")
                continue
            sx, sy, sz = size
            forceload(x4 - 1, Z4 - 1, x4 + sx, Z4 + sz)
            for _ in range(s.PLACE_ATTEMPTS):
                m = ctx.run(f"place template heraldia:{name} {x4} {Y4} {Z4}", r"Loaded template|placed|Failed|not loaded|Unknown|Invalid")
                if "not loaded" not in m.string:
                    break
                time.sleep(s.PLACE_RETRY_S)
            g = f"@e[tag={tag}]"
            if not ctx.wait_entity(g):
                fails.append(f"sala: {name}: no aparece el guardián")
                continue
            p0 = ctx.pos(g)
            ctx.ticks(200)
            p1 = ctx.pos(g)
            d = ((p1[0] - p0[0]) ** 2 + (p1[2] - p0[2]) ** 2) ** 0.5 if p0 and p1 else None
            print(f"anclados: sala: {name}: {p0} -> {p1} ({d if d is None else round(d, 2)} bloques)")
            if d is None or d > 1.5:
                fails.append(f"sala: {name}: el guardián se ha movido de {p0} a {p1}")
            ctx.run(f"kill @e[type=!minecraft:player,x={x4 - 2},y={Y4 - 2},z={Z4 - 2},dx={sx + 4},dy={sy + 4},dz={sz + 4}]",
                    r"Killed|No entity was found")
            ctx.run("forceload remove all", r"Unmarked|Removed|No force|force")
    finally:
        try:
            s.send(proc, "stop")
            proc.wait(timeout=120)
        except Exception:
            proc.kill()
    if not found or not rooms:
        fails.append("no hay mobs anclados en las plantillas: la prueba no comprueba nada")
    if fails:
        print("FALLOS:\n- " + "\n- ".join(fails))
        sys.exit(1)
    print("anclados: OK")


if __name__ == "__main__":
    main()
