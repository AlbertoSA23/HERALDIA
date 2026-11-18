"""Real-server test of the Oriental Palace mechanisms (piston doors and traps).

Usage: python3 tools/smoke/palace_redstone.py --jar build/libs/heraldia-X.jar  (after ./gradlew build)
Places the template unrotated at (0, 100, 0), removes each lever (removing it updates the neighbours of the supporting
block, as when operating it) and checks that the doors open; triggers the tripwires with an item and the pressure plate with
a pig, and checks that the dispensers use up an arrow (the tripwire ones hold 3 × 6 arrows, the plate ones 8). Exit code 0 if everything passes.
"""
import argparse, os, queue, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server_smoke import prepare, gradle_properties, reader, wait_for, run, send, Context, ROOT, START_TIMEOUT_S

OY = 100
CHECKS = []


def at(x, y, z):
    return f"{x} {y + OY} {z}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke-palacio"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    launcher = prepare(args.work, os.path.abspath(args.jar), gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=reader, args=(proc, lines), daemon=True).start()
    ctx = Context(proc, lines, seen)

    def test(cond, what):
        if not ctx.test(f"execute if {cond}"):
            fails.append(what)

    def cmd(c, pause=1.5):
        send(proc, c)
        ctx.ticks(int(pause * 20))      # in game ticks: with the server lagging, the clock is not enough

    try:
        wait_for(lines, r"Heraldia: (\d+) estructuras registradas", START_TIMEOUT_S, seen)
        cmd("forceload add -16 -16 96 140", 8)
        for _ in range(20):
            m = run(proc, lines, seen, f"place template heraldia:unicas/palacio/palacio 0 {OY} 0",
                    r"Loaded template|Failed|not loaded|Unknown|Invalid")
            if "Loaded template" in m.group(0):
                break
            time.sleep(3)
        else:
            fails.append("the template could not be placed")
        ctx.ticks(40)
        test(f"block {at(9, 3, 41)} minecraft:bookshelf", "biblioteca: puerta cerrada al colocar")
        test(f"block {at(7, 3, 41)} minecraft:sticky_piston[extended=true]", "biblioteca: pistón extendido al colocar")
        test(f"block {at(40, 2, 48)} minecraft:deepslate_bricks", "cámara: puerta cerrada al colocar")
        # puertas
        cmd(f"setblock {at(7, 4, 43)} minecraft:air", 2)
        test(f"block {at(9, 3, 41)} minecraft:air", "biblioteca: hueco bajo abierto")
        test(f"block {at(9, 4, 41)} minecraft:air", "biblioteca: hueco alto abierto")
        test(f"block {at(8, 4, 41)} minecraft:bookshelf", "biblioteca: estantería recogida tras la columna")
        cmd(f"setblock {at(38, 9, 61)} minecraft:air", 2)
        test(f"block {at(40, 8, 63)} minecraft:air", "trono: hueco bajo abierto")
        test(f"block {at(40, 9, 63)} minecraft:air", "trono: hueco alto abierto")
        cmd(f"setblock {at(37, 2, 47)} minecraft:air", 2)
        test(f"block {at(40, 2, 48)} minecraft:air", "cámara: una palanca abre el bloque bajo")
        test(f"block {at(40, 3, 48)} minecraft:deepslate_bricks", "cámara: con una palanca el bloque alto sigue")
        cmd(f"setblock {at(43, 3, 47)} minecraft:air", 2)
        test(f"block {at(40, 3, 48)} minecraft:air", "cámara: las dos palancas abren la puerta")
        # trampas
        for z in (56, 50):
            cmd(f"summon minecraft:item {30.5} {2.1 + OY} {z + 0.5} {{Item:{{id:\"minecraft:stick\",count:1}},PickupDelay:32767}}", 2)
            for x in (28, 32):
                test(f"block {at(x, 3, z)} minecraft:dispenser", f"cable z={z}: dispensador {x}")
                test(f"data block {at(x, 3, z)} Items[{{count:5}}]", f"cable z={z}: el dispensador {x} no disparó")
        cmd(f"summon minecraft:pig 71.5 {3 + OY} 38.5 {{NoAI:1b}}", 2)
        for x in (70, 72):
            test(f"data block {at(x, 3, 38)} Items[{{count:7}}]", f"placa: el dispensador {x} no disparó")
        send(proc, "stop")
        proc.wait(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
    if fails:
        print("PALACE TEST FAILED:\n  " + "\n  ".join(fails))
        return 1
    print("PALACE TEST OK: library, throne and chamber doors (two levers), two tripwires and the plate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
