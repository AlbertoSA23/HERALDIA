"""Mobs de plantilla que podrían salir bebés, en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/guardianes_adultos.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke" [--veces N]
Los mobs de una plantilla pasan por finalizeSpawn al colocarse como pieza de estructura, y el de los zombis (zombi,
husk, ahogado, zombi aldeano, piglin zombificado) sortea un bebé (5 %, a veces en una gallina) sin mirar el IsBaby del
NBT, cambia a veces el arma (ahogado: tridente o caña el 10 %) y monta en un nautilo zombi a la mitad de los ahogados con
tridente. El mod lo evita en los que llevan la etiqueta heraldia_adulto (core.ADULTO_TAG; validate.py exige que la
lleve todo mob de ese tipo). Para cada mob distinto de ese tipo en las plantillas del .jar (los guardianes del
castillo, el Salón del Jarl, el galeón, la pirámide, el coliseo, el faro, el acueducto y los ahogados de la Atlántida)
escribe un paquete de datos con una plantilla mínima (un bloque de piedra y encima un jigsaw que se borra) con ese mob
tal cual y su pool, lo coloca --veces veces con /place jigsaw (pieza de pool: mismo camino que al generar, con
finalizeSpawn; /place template no lo llama) y comprueba que aparecen todos, que ninguno es bebé, que no hay monturas
ni otras entidades nuevas y que todos conservan el arma de su plantilla.
"""
import argparse, gzip, io, json, os, queue, subprocess, sys, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
import nbtlib
from nbtlib.tag import Compound
import core

BEBES = ("zombie", "husk", "drowned", "zombie_villager", "zombified_piglin")
PACK, NS, ANCLA = "heraldia_prueba_adultos", "heraldia_prueba", "heraldia_prueba:ancla"
X0, Y, Z0 = 0, 150, 0           # rejilla de colocaciones sobre una plataforma en el aire (chunks forzados)
COLS, PASO = 20, 3


def mobs(jar):
    """[(nombre, nbt)]: un mob de cada NBT distinto (sin posición) de los tipos con bebé en las plantillas del .jar."""
    out, seen = [], set()
    with zipfile.ZipFile(jar) as z:
        for n in sorted(z.namelist()):
            if not (n.startswith("data/heraldia/structure/") and n.endswith(".nbt")):
                continue
            t = nbtlib.File.parse(io.BytesIO(gzip.decompress(z.read(n))))
            for e in t.get("entities", []):
                nbt = Compound(e["nbt"])
                mob = str(nbt["id"]).split(":")[-1]
                if mob not in BEBES:
                    continue
                nbt.pop("Pos", None)
                nbt.pop("UUID", None)
                key = nbt.snbt()
                if key not in seen:
                    seen.add(key)
                    out.append((f"{n[len('data/heraldia/structure/'):-4]} ({mob})", nbt))
    return out


def write_pack(work, found, veces):
    """Paquete de datos en world/datapacks (el servidor lo activa al crear el mundo): por mob, una plantilla
    (jigsaw + el mob encima), su pool y una función con las colocaciones."""
    root = os.path.join(work, "world", "datapacks", PACK)
    with open(os.path.join(os.makedirs(root, exist_ok=True) or root, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"description": "Heraldia: prueba de mobs adultos", "min_format": 121, "max_format": 121}}, f)
    data = os.path.join(root, "data", NS)
    for d in ("structure", "worldgen/template_pool", "function"):
        os.makedirs(os.path.join(data, d), exist_ok=True)
    for i, (_, nbt) in enumerate(found):
        t = core.Template(f"m{i}")
        t.set(0, 0, 0, "minecraft:stone")       # su propio suelo: no depende de la plataforma
        t.jigsaw(0, 1, 0, "up_north", ANCLA, "minecraft:empty", "minecraft:empty", joint="rollable")
        t.entity(0, 1, 0, nbt)
        nbtlib.File(t.to_nbt(), gzipped=True).save(os.path.join(data, "structure", f"m{i}.nbt"))
        with open(os.path.join(data, "worldgen", "template_pool", f"m{i}.json"), "w") as f:
            json.dump({"fallback": "minecraft:empty", "elements": [{"weight": 1, "element": {
                "element_type": "minecraft:single_pool_element", "location": f"{NS}:m{i}",
                "projection": "rigid", "processors": "minecraft:empty"}}]}, f)
        with open(os.path.join(data, "function", f"m{i}.mcfunction"), "w") as f:
            for k in range(veces):
                f.write(f"place jigsaw {NS}:m{i} {ANCLA} 1 {X0 + (k % COLS) * PASO} {Y} {Z0 + (k // COLS) * PASO}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke"))
    ap.add_argument("--veces", type=int, default=200)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    found = mobs(a.jar)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    write_pack(a.work, found, a.veces)
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    fails = []
    x1, z1 = X0 + COLS * PASO, Z0 + (a.veces // COLS + 1) * PASO
    area = f"x={X0 - 2},y={Y - 4},z={Z0 - 2},dx={x1 - X0 + 4},dy=12,dz={z1 - Z0 + 4}"

    def count(sel):
        m = ctx.run(f"execute if entity {sel}", r"Test passed\. Count: (\d+)|Test failed")
        return int(m.group(1) or 0)

    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        m = ctx.run("datapack list enabled", r"data pack\(s\) enabled: (.*)|no data packs")
        if PACK not in m.group(0):
            raise SystemExit(f"el paquete de prueba {PACK} no está activado: {m.string.strip()}")
        ctx.run(f"forceload add {X0 - 2} {Z0 - 2} {x1 + 2} {z1 + 2}", r"Marked|Added|force|already")
        for _ in range(s.PLACE_ATTEMPTS):   # los chunks forzados tardan en cargarse
            m = ctx.run(f"fill {X0 - 2} {Y - 1} {Z0 - 2} {x1 + 2} {Y - 1} {z1 + 2} minecraft:stone", r"Successfully filled|No blocks")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        ctx.run("time set midnight", r"Set .*time")
        print(f"adultos: {len(found)} mobs distintos con posible bebé en las plantillas")
        for i, (name, nbt) in enumerate(found):
            mob = str(nbt["id"])
            adulto = "heraldia_adulto" in [str(t) for t in nbt.get("Tags", [])]
            t0 = time.monotonic()
            ctx.run(f"function {NS}:m{i}", r"Running function|Ran \d+ command")
            sel = f"@e[type={mob},{area}]"
            total = 0
            for _ in range(30):             # las entidades de la pieza tardan algo más que los bloques
                total = count(sel)
                if total >= a.veces:
                    break
                time.sleep(1)
            babies = count(f"@e[type={mob},{area},nbt={{IsBaby:1b}}]")
            mounts = count(f"@e[type=!{mob},type=!minecraft:item,{area}]")     # gallinas, nautilos zombis...
            hand = str(nbt.get("equipment", {}).get("mainhand", {}).get("id", ""))
            swapped = total - count(f'@e[type={mob},{area},nbt={{equipment:{{mainhand:{{id:"{hand}"}}}}}}]') if hand else 0
            print(f"adultos: {name}: {total} colocados, {babies} bebés, {mounts} monturas, {swapped} con otra arma "
                  f"(heraldia_adulto: {'sí' if adulto else 'no'}, {time.monotonic() - t0:.1f} s)")
            if total != a.veces:
                fails.append(f"{name}: {total} de {a.veces} colocados")
            if babies or mounts or swapped:
                fails.append(f"{name}: {babies} bebés, {mounts} monturas y {swapped} sin su arma ({hand}) en {total}")
            ctx.run(f"kill @e[type=!minecraft:player,{area}]", r"Killed|No entity was found")
            ctx.run(f"kill @e[type=minecraft:item,{area}]", r"Killed|No entity was found")
    finally:
        try:
            s.send(proc, "stop")
            proc.wait(timeout=120)
        except Exception:
            proc.kill()
    if not found:
        fails.append("no hay mobs con posible bebé en las plantillas: la prueba no comprueba nada")
    if fails:
        print("FALLOS:\n- " + "\n- ".join(fails))
        sys.exit(1)
    print("adultos: OK")


if __name__ == "__main__":
    main()
