"""Test of the Colosseum's puzzles and traps on a real 26.3 dedicated server.

Usage: python3 tools/smoke/colosseum_redstone.py --jar build/libs/heraldia-X.jar [--work build/smoke-coliseo]
Places the two templates with /place template (no rotation) and checks:
  - after a few seconds nothing has changed by itself (pistons extended, trapdoor closed, no arrows fired);
  - puzzle 2: lever on -> the piston door opens; off -> it closes;
  - puzzle 1: an item in the frame -> the iron trapdoor opens;
  - traps: an armor stand on the wire and on a plate makes arrows fire.
The lever and the frame are operated with /setblock and /data, which do not notify neighbors as a player does; so,
afterwards, a block is placed and removed next to the component (equivalent neighbor update).
"""
import argparse, os, subprocess, sys, threading, queue, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import server_smoke as S
from uniques.colosseum import blueprint

O = (0, 100, 0)


def W(dx, y, dz):
    return f"{O[0] + blueprint.CX + dx} {O[1] + y} {O[2] + blueprint.CZ + dz}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(S.ROOT, "build", "smoke-coliseo"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    _, _, _, offs = blueprint.construct()
    launcher = S.prepare(args.work, os.path.abspath(args.jar), S.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=S.reader, args=(proc, lines), daemon=True).start()
    ctx = S.Context(proc, lines, seen)
    fails = []

    def cmd(c, ok=r"."):
        return S.run(proc, lines, seen, c, ok)

    def check(desc, pos, block):
        if not ctx.block(pos, block):
            fails.append(f"{desc}: expected {block} at {pos}")
        else:
            print("OK", desc)

    def nudge(pos, orig="minecraft:air"):
        cmd(f"setblock {pos} minecraft:glass", r"Changed the block|Could not set")
        cmd(f"setblock {pos} {orig}", r"Changed the block|Could not set")

    def wait(s):
        ctx.ticks(20 * s)       # in game ticks: with a lagging server, the wall clock is not enough

    try:
        S.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", S.START_TIMEOUT_S, seen)
        cmd("forceload add -16 -16 100 90", r"Marked|Added|chunks? .*force")
        wait(5)
        for name in ("hipogeo", "coliseo"):
            ox, oy, oz = offs[f"unicas/coliseo/{name}"]
            for _ in range(20):
                m = cmd(f"place template heraldia:unicas/coliseo/{name} {O[0] + ox} {O[1] + oy} {O[2] + oz}",
                        r"Loaded template|not loaded|Failed|Invalid|Unknown")
                if "not loaded" not in m.group(0):
                    break
                wait(3)
            if "Loaded" not in m.group(0):
                fails.append(f"place template {name}: {m.string.strip()}")
        wait(4)
        a = 5
        # estado estable tras colocar
        check("pistón inferior extendido", W(-6, a, 13), "minecraft:sticky_piston[extended=true]")
        check("pistón superior extendido", W(-6, a + 1, 13), "minecraft:sticky_piston[extended=true]")
        check("puerta cerrada", W(-6, a, 15), "minecraft:chiseled_quartz_block")
        check("antorcha encendida", W(-6, a, 12), "minecraft:redstone_wall_torch[lit=true]")
        check("trampilla de hierro cerrada", W(20, -6, 7), "minecraft:iron_trapdoor[open=false]")
        m = cmd("execute if entity @e[type=minecraft:arrow]", r"Test passed|Test failed")
        if "passed" in m.group(0):
            fails.append("arrows have been fired before stepping on any trap")
        # puzle 2
        cmd(f"setblock {W(-4, a, 12)} minecraft:lever[face=wall,facing=east,powered=true]", r"Changed the block|Could not set")
        nudge(W(-6, a, 11), "minecraft:quartz_bricks")
        wait(2)
        check("puzle 2 abre (abajo)", W(-6, a, 15), "minecraft:air")
        check("puzle 2 abre (arriba)", W(-6, a + 1, 15), "minecraft:air")
        check("puzle 2 bloque recogido", W(-6, a, 14), "minecraft:chiseled_quartz_block")
        cmd(f"setblock {W(-4, a, 12)} minecraft:lever[face=wall,facing=east,powered=false]", r"Changed the block|Could not set")
        nudge(W(-6, a, 11), "minecraft:quartz_bricks")
        wait(2)
        check("puzle 2 cierra", W(-6, a, 15), "minecraft:chiseled_quartz_block")
        check("puzle 2 cierra (arriba)", W(-6, a + 1, 15), "minecraft:chiseled_quartz_block")
        # puzle 1
        fx, fy, fz = W(20, -6, 4).split()
        cmd(f"data merge entity @e[type=minecraft:item_frame,x={fx}.5,y={fy}.5,z={fz}.5,distance=..0.9,limit=1] "
            "{Item:{id:\"minecraft:iron_sword\",count:1}}", r"Modified|Found no|No entity|Unable")
        nudge(W(21, -6, 6))
        wait(2)
        check("puzle 1 abre la trampilla", W(20, -6, 7), "minecraft:iron_trapdoor[open=true]")
        # trampas
        cmd(f"summon minecraft:armor_stand {W(16, -6, 0)}", r"Summoned|Unable")
        (fails.append("trampa 1 (cable) no dispara") if not ctx.until("execute if entity @e[type=minecraft:arrow]") else print("OK trampa 1"))
        cmd("kill @e[type=minecraft:arrow]", r"Killed|No entity")
        cmd(f"summon minecraft:armor_stand {W(12, -13, 3)}", r"Summoned|Unable")
        (fails.append("trampa 2 (placas) no dispara") if not ctx.until("execute if entity @e[type=minecraft:arrow]") else print("OK trampa 2"))
        ok = ctx.wait_entity("@e[type=minecraft:husk,tag=heraldia_guardian.coliseo]")
        (fails.append("the Arena Champion is missing") if not ok else print("OK guardian"))
    finally:
        if proc.poll() is None:
            S.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    if fails:
        print("COLOSSEUM TEST FAILED:\n  " + "\n  ".join(fails))
        return 1
    print("COLOSSEUM TEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
