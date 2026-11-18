"""Real-server test of the wizard tower's mechanisms (placed with /place template, unrotated).

Usage: python3 tools/gen/uniques/wizard_tower/smoke_redstone.py --jar build/libs/heraldia-X.jar
Checks: that everything stays still when placed (doors closed, torch lit, TNT and arrows in place),
that the chiseled bookshelf only opens the secret door with the sixth slot, that the cauldron only opens the
iron door when completely full, and that the tripwire in the west wing fires. Exit code 0 if everything passes.
"""
import argparse, os, queue, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(ROOT, "tools", "smoke"))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import server_smoke as sm
from uniques.wizard_tower import OX, OZ, FEET

Y0 = 100      # height of the template base


def P(x, y, z):
    return f"{x + OX} {y + Y0} {z + OZ}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke_torre"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = sm.prepare(a.work, os.path.abspath(a.jar), sm.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []

    def rd():
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)
    threading.Thread(target=rd, daemon=True).start()
    ctx = sm.Context(proc, lines, seen)

    def cmd(c, ok=r"."):
        return sm.run(proc, lines, seen, c, ok)

    def check(label, pos, block, want=True):
        got = ctx.block(pos, block)
        print(("OK   " if got == want else "FALLO"), label)
        if got != want:
            fails.append(label)

    def wait(t):
        ctx.ticks(20 * t)       # in game ticks: with a lagging server, the wall clock is not enough
    try:
        sm.wait_for(lines, r"Heraldia: \d+ estructuras registradas", sm.START_TIMEOUT_S, seen)
        cmd("forceload add -16 -16 48 48", r"Marked|Added|force")
        wait(5)
        for _ in range(20):
            m = cmd(f"place template heraldia:unicas/torre_mago/torre {OX - OX} {Y0} 0", r"Loaded template|placed|Failed|not loaded|Unable")
            if "loaded template" in m.group(0).lower() or "placed" in m.group(0).lower():
                break
            wait(3)
        else:
            fails.append("place template")
        wait(4)
        f2, b1 = FEET["f2"], FEET["B1"]
        # reposo
        for yy in (f2, f2 + 1):
            check(f"puerta secreta cerrada y={yy}", P(-9, yy, 0), "minecraft:bookshelf")
            check(f"pistón extendido y={yy}", P(-9, yy, -2), "minecraft:sticky_piston[extended=true]")
        check("antorcha encendida", P(-10, f2 + 1, -2), "minecraft:redstone_wall_torch[lit=true]")
        check("puerta de hierro cerrada", P(4, b1, 5), "minecraft:iron_door[open=false]")
        check("TNT en su sitio", P(0, 0, 11), "minecraft:tnt")
        # chiseled bookshelf: a slot other than the sixth does not open it
        cmd(f"item replace block {P(-8, f2 + 1, -1)} container.4 with minecraft:book", r"Replaced|Unable|No ")
        wait(1)
        check("hueco 5 no abre", P(-9, f2, 0), "minecraft:bookshelf")
        cmd(f"item replace block {P(-8, f2 + 1, -1)} container.5 with minecraft:book", r"Replaced|Unable|No ")
        wait(1)
        check("hueco 6 apaga la antorcha", P(-10, f2 + 1, -2), "minecraft:redstone_wall_torch[lit=false]")
        for yy in (f2, f2 + 1):
            check(f"puerta secreta abierta y={yy}", P(-9, yy, 0), "minecraft:air")
            check(f"estantería retirada y={yy}", P(-9, yy, -1), "minecraft:bookshelf")
        # caldero
        cmd(f"setblock {P(-1, b1, 5)} minecraft:water_cauldron[level=2]", r"Changed|Could not")
        wait(1)
        check("caldero a 2/3 no abre", P(4, b1, 5), "minecraft:iron_door[open=false]")
        cmd(f"setblock {P(-1, b1, 5)} minecraft:water_cauldron[level=3]", r"Changed|Could not")
        wait(1)
        check("caldero lleno abre la puerta de hierro", P(4, b1, 5), "minecraft:iron_door[open=true]")
        # tripwire in the west wing
        # without AI, the chicken stays on the tripwire: if it leaves, the hook turns off and the dispenser stops being "triggered"
        cmd(f"summon minecraft:chicken {P(-6, b1, 0)} {{NoAI:1b,Silent:1b}}", r"Summoned|Unable")
        wait(1)
        check("el hilo acciona el gancho", P(-6, b1, -4), "minecraft:tripwire_hook[powered=true]")
        check("el dispensador ha disparado", P(-6, b1 + 1, -5), "minecraft:dispenser[triggered=true]")
        check("el guardián está", P(-5, FEET["B2"], 6), "minecraft:purple_carpet")
        ok = ctx.wait_entity("@e[type=minecraft:evoker,tag=heraldia_guardian.torre_mago]")
        print("OK   " if ok else "FALLO", "evocador presente")
        if not ok:
            fails.append("evocador")
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            proc.wait(timeout=120)
    print("REDSTONE TEST", "FALLIDA: " + ", ".join(fails) if fails else "OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
