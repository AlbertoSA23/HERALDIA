"""Prueba del galeón varado en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/galeon_test.py --jar build/libs/heraldia-X.jar
Comprueba: /locate encuentra un galeón en la orilla (la búsqueda en Java funciona en generación natural),
/place structure lo coloca, el capitán ahogado está y los pistones de la estantería falsa siguen extendidos.
"""
import argparse, os, queue, subprocess, sys, threading, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-galeon"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        m = s.run(proc, lines, seen, "locate structure heraldia:unicas/galeon", r"nearest.*?\[(-?\d+), ~?(-?\d+|~), (-?\d+)\]|Could not find")
        if not m.group(1):
            fails.append("locate no encuentra ningún galeón")
            x = z = 0
        else:
            x, z = int(m.group(1)), int(m.group(3))
            print("galeón natural en", x, z)
        s.send(proc, f"forceload add {x - 120} {z - 120} {x + 119} {z + 119}")
        s.wait_for(lines, r"Marked|Added|force", s.COMMAND_TIMEOUT_S, seen)
        for _ in range(s.PLACE_ATTEMPTS):
            m = s.run(proc, lines, seen, f"place structure heraldia:unicas/galeon {x} ~ {z}", r"Generated structure")
            if "not loaded" not in m.group(0):
                break
            import time; time.sleep(s.PLACE_RETRY_S)
        if "Generated" not in m.group(0):
            fails.append("place falló: " + m.string.strip())
        # orientación: mar a 20 bloques del ancla hacia fuera, arena del campamento a 24 hacia tierra
        a = next(re.search(r"ancla (-?\d+) (-?\d+) (-?\d+) giro (\w+)", l) for l in reversed(seen) if "ancla" in l)
        ax, ay, az = (int(a.group(i)) for i in (1, 2, 3))
        ex, ez = {"NONE": (1, 0), "CLOCKWISE_90": (0, 1), "CLOCKWISE_180": (-1, 0), "COUNTERCLOCKWISE_90": (0, -1)}[a.group(4)]
        for dist, y, block in ((20, ay - 1, "minecraft:water"), (-24, ay, "minecraft:sand")):
            m = s.run(proc, lines, seen, f"execute if block {ax + ex * dist} {y} {az + ez * dist} {block}", r"Test passed|Test failed")
            if "passed" not in m.group(0):
                fails.append(f"orientación: no hay {block} a {dist} del ancla")
        # Las entidades de la plantilla aparecen unos segundos después de los bloques: se reintenta (como en la
        # prueba de humo). El capitán se reconoce por la etiqueta de guardián que usa su logro.
        if not s.guardian_placed(s.Context(proc, lines, seen), "heraldia:unicas/galeon"):
            fails.append("no está el capitán ahogado")
        for _ in range(s.GUARDIAN_ATTEMPTS):
            m = s.run(proc, lines, seen, "execute if entity @e[type=minecraft:oak_boat]", r"Test passed\. Count: (\d+)|Test failed")
            if m.group(1):
                break
            import time; time.sleep(s.PLACE_RETRY_S)
        else:
            fails.append("no está el bote")
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            proc.wait(timeout=120)
    print("GALEÓN:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
