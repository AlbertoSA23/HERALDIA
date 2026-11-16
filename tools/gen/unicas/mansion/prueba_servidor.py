"""Prueba en un servidor 26.3 real: entidades de la mansión y mecanismos accionados en el juego.

Uso (desde la raíz): python3 tools/gen/unicas/mansion/prueba_servidor.py --jar build/libs/heraldia-X.jar
Coloca la estructura con /place structure y cuenta cuadros, guardián y gato tras 15 s (los colgantes se caen si no tienen
pared). Coloca las plantillas sin girar en sitios conocidos y acciona la palanca de la biblioteca y la combinación:
como /setblock no actualiza los vecinos de la palanca, se fuerza la actualización tocando un bloque junto a la antorcha.
"""
import argparse, os, queue, subprocess, sys, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "smoke"))
import server_smoke as sm

CASA, SOT = (2000, 100, 0), (2100, 100, 0)          # origen de cada plantilla colocada sin girar
CELLAR_MIN = (12, -7, 14)                           # esquina mínima del sótano en coordenadas de la obra


def at(base, p, cellar=False):
    x, y, z = p
    if cellar:
        x, y, z = x - CELLAR_MIN[0], y - CELLAR_MIN[1], z - CELLAR_MIN[2]
    return f"{base[0] + x} {base[1] + y} {base[2] + z}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_mansion"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = sm.prepare(a.work, os.path.abspath(a.jar), sm.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=sm.reader, args=(proc, lines), daemon=True).start()
    ctx = sm.Context(proc, lines, seen)
    fails = []

    def cmd(c, ok=r"Test passed|Test failed|Generated|Changed|Loaded template|Marked|Added|Set the block|Could not|Dropped|Running|has the following"):
        return sm.run(proc, lines, seen, c, ok)

    def check(desc, c, until=False):
        ok = ctx.until(c) if until else ctx.test(c)
        print(f"[{'OK' if ok else 'FALLO'}] {desc}")
        if not ok:
            fails.append(desc)
    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        for c in ("forceload add -128 -128 127 127", "forceload add 1990 -10 2200 120"):
            sm.send(proc, c); sm.wait_for(lines, r"Marked|Added|chunks? .*force", 300, seen)
        for _ in range(30):
            m = cmd("place structure heraldia:unicas/mansion 0 ~ 0", r"Generated structure|not loaded|Failed|error")
            if "not loaded" not in m.group(0):
                break
            time.sleep(5)
        if "Generated" not in m.group(0):
            fails.append("place structure")
        # las entidades de la estructura aparecen unos segundos después que los bloques: se espera por condición
        check("los cuadros de la galería siguen colgados", "execute if entity @e[type=minecraft:painting]", until=True)
        print("cuadros:", ctx.count("@e[type=minecraft:painting]"))
        check("guardián con nombre", "execute if entity @e[type=minecraft:wither_skeleton,tag=heraldia_mansion_guardian]", until=True)
        check("gato negro", "execute if entity @e[type=minecraft:cat]", until=True)
        cmd("data get entity @e[type=minecraft:wither_skeleton,limit=1] equipment", r"has the following|No entity|error")
        # plantillas sin girar en sitios conocidos
        for name, base in (("casa", CASA), ("sotano", SOT)):
            m = cmd(f"place template heraldia:unicas/mansion/{name} {base[0]} {base[1]} {base[2]}", r"Loaded template|Failed|not loaded|error|Could not")
            if "Loaded" not in m.group(0):
                fails.append("place template " + name)
        ctx.ticks(40)
        door = [(22, 2, 27), (22, 3, 27)]
        check("estantería cerrada al generarse", f"execute if block {at(CASA, door[0])} minecraft:bookshelf")
        cmd(f"setblock {at(CASA, (18, 3, 26))} minecraft:lever[face=wall,facing=north,powered=true]")
        cmd(f"setblock {at(CASA, (19, 3, 28))} minecraft:air"); cmd(f"setblock {at(CASA, (19, 3, 28))} minecraft:cobbled_deepslate")
        ctx.ticks(60)
        for p in door:
            check(f"la palanca abre la estantería {p}", f"execute if block {at(CASA, p)} minecraft:air")
        check("puerta de la cámara cerrada al generarse", f"execute if block {at(SOT, (47, -5, 28), True)} minecraft:iron_door[open=false]")
        for x in (39, 45):
            cmd(f"setblock {at(SOT, (x, -4, 27), True)} minecraft:lever[face=wall,facing=north,powered=true]")
            cmd(f"setblock {at(SOT, (x, -3, 29), True)} minecraft:stone"); cmd(f"setblock {at(SOT, (x, -3, 29), True)} minecraft:air")
        ctx.ticks(60)
        check("la combinación 1-4 abre la cámara", f"execute if block {at(SOT, (47, -5, 28), True)} minecraft:iron_door[open=true]")
        cmd(f"setblock {at(SOT, (41, -4, 27), True)} minecraft:lever[face=wall,facing=north,powered=true]")
        cmd(f"setblock {at(SOT, (42, -4, 29), True)} minecraft:stone"); cmd(f"setblock {at(SOT, (42, -4, 29), True)} minecraft:tuff")
        ctx.ticks(60)
        check("con la 2.ª palanca se vuelve a cerrar", f"execute if block {at(SOT, (47, -5, 28), True)} minecraft:iron_door[open=false]")
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("PRUEBA MANSIÓN " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
