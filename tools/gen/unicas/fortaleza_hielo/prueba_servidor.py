"""Prueba en servidor real de los mecanismos de la fortaleza de hielo (complementa tools/smoke/server_smoke.py).

Coloca la plantilla sin rotar en (0, 100, 0) y comprueba: puertas secretas cerradas y estables, que al bajar cada palanca
se abren, que la placa y el cable trampa disparan sus dispensadores, el guardián, los lobos y los generadores.
Uso: python3 tools/gen/unicas/fortaleza_hielo/prueba_servidor.py --jar build/libs/heraldia-<versión>.jar
"""
import argparse, os, queue, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "smoke"))
import server_smoke as S                      # noqa: E402

Y = 100
ARROWS = "{Items:[{Slot:0b,count:16},{Slot:1b,count:16},{Slot:2b,count:16}]}"


def p(x, y, z):
    return f"{x} {y + Y} {z}"


CHECKS = [  # (descripción, orden, debe pasar)
    ("puerta de la cripta cerrada", f"execute if block {p(15, 6, 51)} minecraft:chiseled_stone_bricks", True),
    ("pistón de la cripta extendido", f"execute if block {p(15, 7, 53)} minecraft:sticky_piston[extended=true]", True),
    ("puerta del salón cerrada", f"execute if block {p(29, 12, 55)} minecraft:chiseled_stone_bricks", True),
    ("guardián", "execute if entity @e[type=minecraft:stray,nbt={PersistenceRequired:1b}]", True),
    ("guardián con arco", "execute if entity @e[type=minecraft:stray,nbt={equipment:{mainhand:{id:\"minecraft:bow\"}}}]", True),
    ("tres lobos de las nieves", "execute if entity @e[type=minecraft:wolf,nbt={variant:\"minecraft:snowy\"}]", True),
    ("generador de strays", f"execute if data block {p(34, 6, 45)} SpawnData.entity{{id:\"minecraft:stray\"}}", True),
    ("cofre premium con botín", f"execute if data block {p(6, 1, 62)} LootTable", True),
]
ACTIONS = [
    ("abrir la cripta", f"setblock {p(17, 7, 54)} minecraft:lever[face=wall,facing=east,powered=false]",
     [(f"execute if block {p(15, 6, 51)} minecraft:air", True), (f"execute if block {p(15, 7, 51)} minecraft:air", True)]),
    ("abrir el salón", f"setblock {p(32, 12, 53)} minecraft:lever[face=wall,facing=north,powered=false]",
     [(f"execute if block {p(29, 11, 55)} minecraft:air", True), (f"execute if block {p(29, 12, 55)} minecraft:air", True)]),
    ("pisar la placa del tesoro", f"summon minecraft:zombie 6.5 {1 + Y} 55.5 {{NoAI:1b,Silent:1b}}",
     [(f"execute if data block {p(5, 1, 55)} {ARROWS}", False), (f"execute if data block {p(7, 1, 55)} {ARROWS}", False)]),
    ("cruzar el cable trampa", f"summon minecraft:zombie 35.5 {6 + Y} 51.5 {{NoAI:1b,Silent:1b}}",
     [(f"execute if data block {p(34, 6, 49)} {ARROWS}", False), (f"execute if data block {p(36, 6, 53)} {ARROWS}", False)]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke_fortaleza"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = S.prepare(a.work, os.path.abspath(a.jar), S.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=S.reader, args=(proc, lines), daemon=True).start()

    def test(desc, cmd, want):
        m = S.run(proc, lines, seen, cmd, r"Test passed|Test failed")
        ok = m.group(0).startswith("Test passed") == want
        print(("OK   " if ok else "FALLO") + " " + desc)
        if not ok:
            fails.append(desc)
    try:
        S.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", S.START_TIMEOUT_S, seen)
        S.send(proc, "forceload add -16 -16 80 96")
        S.wait_for(lines, r"Marked|Added|chunks? .*force", S.COMMAND_TIMEOUT_S, seen)
        for _ in range(S.PLACE_ATTEMPTS):
            m = S.run(proc, lines, seen, f"place template heraldia:unicas/fortaleza_hielo/fortaleza {p(0, 0, 0)}",
                      r"Loaded template|[Pp]laced|Failed|not loaded|Invalid")
            if "not loaded" not in m.group(0):
                break
            time.sleep(S.PLACE_RETRY_S)
        time.sleep(3)
        for desc, cmd, want in CHECKS:
            test(desc, cmd, want)
        for desc, cmd, expects in ACTIONS:
            S.send(proc, cmd)
            time.sleep(2)
            for k, (c, want) in enumerate(expects):
                test(f"{desc} ({k + 1})", c, want)
    finally:
        if proc.poll() is None:
            S.send(proc, "stop")
            proc.wait(timeout=120)
    print("PRUEBA DE MECANISMOS " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
