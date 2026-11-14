"""Prueba en un servidor dedicado 26.3 real de lo que la auditoría estática no ve: coloca las dos piezas de la
catedral con /place template, comprueba que los mecanismos siguen en su estado de reposo después de las
actualizaciones de forma, los acciona y mira el resultado (puertas de pistones, trampilla, trampas), y revisa
generadores, cofres, carteles y el guardián.

Uso (desde la raíz): python3 tools/gen/unicas/catedral/prueba_juego.py --jar build/libs/heraldia-X.jar
Las palancas se simulan poniendo un bloque de redstone en el bloque al que están fijadas (misma señal fuerte)."""
import argparse, os, subprocess, sys, threading, queue, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(ROOT, "tools", "smoke"))
sys.path.insert(0, os.path.join(ROOT, "tools", "gen"))
import server_smoke as sm
from unicas.catedral import model, pieces

BASE = (1000, 150, 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "prueba_catedral"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    c = model()
    top, low = pieces(c)
    offs = {}
    for t in (top, low):
        x0, y0, z0, *_ = t.bounds()
        offs[t.name] = (x0, y0, z0)
    w = lambda p: (BASE[0] + p[0], BASE[1] + p[1], BASE[2] + p[2])
    launcher = sm.prepare(a.work, os.path.abspath(a.jar), sm.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx3G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails, oks = queue.Queue(), [], [], 0
    threading.Thread(target=sm.reader, args=(proc, lines), daemon=True).start()

    def cmd(s, ok=r"Test passed|Test failed"):
        return sm.run(proc, lines, seen, s, ok)

    def check(desc, pos, state):
        nonlocal oks
        x, y, z = w(pos)
        m = cmd(f"execute if block {x} {y} {z} {state}")
        if "passed" in m.group(0):
            oks += 1
        else:
            fails.append(f"{desc}: {state} en {pos}")

    def setb(pos, st):
        x, y, z = w(pos)
        cmd(f"setblock {x} {y} {z} {st}", r"Changed the block|Could not set|error|Unknown")

    def wait(t=20):
        time.sleep(t / 20 + 0.5)

    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        bx, by, bz = BASE
        cmd(f"forceload add {bx - 16} {bz - 16} {bx + 130} {bz + 100}", r"Marked|Added|force|chunks")
        time.sleep(15)
        for t in (top, low):
            ox, oy, oz = w(offs[t.name])
            for _ in range(20):
                m = cmd(f"place template heraldia:{t.name} {ox} {oy} {oz}", r"Loaded template|not loaded|Failed|Invalid|Unknown|Couldn't")
                if "not loaded" not in m.group(0):
                    break
                time.sleep(5)
            if "Loaded" not in m.group(0):
                fails.append(f"place template {t.name}: {m.string.strip()}")
        wait(40)
        g = c.t.get
        # 1) reposo estable tras colocarse (incluidas las actualizaciones de forma de /place template)
        for mch in c.mech:
            ps = [p for k in ("pistones", "cabezas", "antorchas", "puerta", "ganchos", "cable", "dispensadores") for p in mch.get(k, [])]
            ps += [p for (p, _) in mch.get("polvo", [])] + [lp for (lp, _) in mch.get("palancas", []) + mch.get("falsas", [])]
            for k in ("trampilla", "palanca", "placa"):
                if k in mch:
                    ps.append(mch[k])
            for p in ps:
                check(f"reposo {mch['sitio']}", p, g(*p).replace("minecraft:", ""))
        # 2) generadores, cofres y guardián (antes de abrir puertas: el guardián podría salir)
        for (pos, mob) in c.spawners:
            check("generador", pos, f'spawner{{SpawnData:{{entity:{{id:"minecraft:{mob}"}}}}}}')
        for (pos, tabla, sitio) in c.chests:
            check(f"cofre {sitio}", pos, f'{g(*pos).split("[")[0].replace("minecraft:", "")}{{LootTable:"heraldia:unicas/catedral/{tabla}"}}')
        for (x, y, z, n) in c.entities:
            px, py, pz = w((x, y, z))
            for _ in range(15):            # las entidades de la plantilla se cargan unos ticks después que los bloques
                m = cmd(f"execute if entity @e[type=minecraft:skeleton,x={px},y={py},z={pz},distance=..8,nbt={{PersistenceRequired:1b,equipment:{{mainhand:{{id:\"minecraft:bow\"}}}}}}]")
                if "passed" in m.group(0):
                    break
                time.sleep(2)
            if "passed" in m.group(0):
                oks += 1
            else:
                fails.append("guardián ausente o sin equipo")
            cmd(f"data get entity @e[type=minecraft:skeleton,x={px},y={py},z={pz},distance=..8,limit=1] CustomName", r"has the following|No entity|Found no")
        # 2) puertas de pistones: solución abre, la palanca falsa vuelve a cerrar
        for mch in [m for m in c.mech if m["tipo"] == "puerta de pistones"]:
            for (lp, bp) in mch["palancas"]:
                setb(bp, "redstone_block")
            wait()
            for p in mch["puerta"]:
                check(f"abre {mch['sitio']}", p, "air")
            for p in mch["cabezas"]:
                check(f"puerta recogida {mch['sitio']}", p, g(*mch["puerta"][0]).replace("minecraft:", ""))
            for (lp, bp) in mch["falsas"]:
                setb(bp, "redstone_block")
                wait()
                for p in mch["puerta"]:
                    check(f"la palanca falsa cierra {mch['sitio']}", p, g(*p).replace("minecraft:", ""))
                setb(bp, g(*bp).replace("minecraft:", ""))
                wait()
                for p in mch["puerta"]:
                    check(f"reabre {mch['sitio']}", p, "air")
            for (lp, bp) in mch["palancas"]:
                setb(bp, g(*bp).replace("minecraft:", ""))
            wait()
            for p in mch["puerta"]:
                check(f"vuelve a cerrar {mch['sitio']}", p, g(*p).replace("minecraft:", ""))
        # 3) trampilla del altar y trampas
        for mch in c.mech:
            if mch["tipo"] == "trampilla":
                setb(mch["apoyo"], "redstone_block")
                wait()
                check("trampilla del altar abierta", mch["trampilla"], "iron_trapdoor[open=true]")
                setb(mch["apoyo"], g(*mch["apoyo"]).replace("minecraft:", ""))
            elif mch["tipo"] in ("cable trampa", "placa de presión"):
                p = mch["cable"][1] if "cable" in mch else mch["placa"]
                x, y, z = w(p)
                cmd(f"summon minecraft:zombie {x}.5 {y} {z}.5 {{NoAI:1b,PersistenceRequired:1b,Tags:[\"prueba\"]}}", r"Summoned|Unable|error")
                wait(30)
                m = cmd(f"execute if entity @e[type=minecraft:arrow,x={x},y={y},z={z},distance=..8]")
                if "passed" in m.group(0):
                    oks += 1
                else:
                    fails.append(f"la trampa {mch['sitio']} no dispara")
                cmd("kill @e[tag=prueba]", r"Killed|No entity|error")
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    if fails:
        print("PRUEBA DE LA CATEDRAL FALLIDA:\n  " + "\n  ".join(fails[:60]))
        return 1
    print(f"PRUEBA DE LA CATEDRAL OK: {oks} comprobaciones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
