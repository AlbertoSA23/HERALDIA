"""Dedicated-server test of the castle's mechanisms (secret doors, traps and guardian).

Use: python3 tools/gen/uniques/castle/smoke_redstone.py --jar build/libs/heraldia-X.jar
Places the two unrotated templates with /place template (without block updates, as when generating), checks that the
rest state is stable even if an update is forced, and activates each mechanism as the player would: it powers the block
that the lever would power (redstone block in its place) or puts an entity on the tripwire or the plate."""
import argparse, os, queue, subprocess, sys, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "smoke"))
import server_smoke as S

C = (0, 80, 0)                      # castle origin
M = (26, 64, 14)                    # dungeon origin (castle + (26, -16, 14))


def w(o, x, y, z):
    return f"{x + o[0]} {y + o[1]} {z + o[2]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(S.ROOT, "build", "smoke_castillo"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = S.prepare(a.work, os.path.abspath(a.jar), S.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=S.reader, args=(proc, lines), daemon=True).start()
    ctx = S.Context(proc, lines, seen)

    def cmd(c, ok=r"Test passed|Incorrect|Killed|Value|value|Test failed|Changed|Placed|placed|Summoned|Forced|Set|Could not|Unable|No entity|has the following"):
        S.send(proc, c)
        return S.wait_for(lines, ok, 60, seen).string

    def check(label, c, until=False):
        ok = ctx.until(c) if until else ctx.test(c)
        print("TEST", label, "OK" if ok else "FALLO")
        if not ok:
            fails.append(label)

    try:
        S.wait_for(lines, r"Done \(", S.START_TIMEOUT_S, seen)
        cmd("forceload add -16 -16 112 112", r"Marked|forceloaded|Added|already")
        for name, base in (("castillo", C), ("mazmorra", M)):
            for _ in range(S.PLACE_ATTEMPTS):      # the forced chunks load in the following ticks
                r = cmd(f"place template heraldia:unicas/castillo/{name} {w(base, 0, 0, 0)}",
                        r"Loaded template|Failed|Unable|Invalid|Incorrect|not loaded")
                if "not loaded" not in r:
                    break
                time.sleep(S.PLACE_RETRY_S)
            if "Loaded template" not in r:
                fails.append(f"place template {name}: {r.strip()}")
        ctx.ticks(60)
        # stable rest state, even after forcing updates next to torches and pistons
        cmd(f"setblock {w(C, 34, 15, 15)} minecraft:stone")
        cmd(f"setblock {w(M, 34, 3, 40)} minecraft:stone")
        cmd(f"setblock {w(M, 37, 3, 40)} minecraft:stone")
        ctx.ticks(40)
        check("estudio: puerta cerrada en reposo", f"execute if block {w(C, 32, 15, 17)} minecraft:bookshelf")
        check("estudio: pistones extendidos", f"execute if block {w(C, 32, 16, 15)} minecraft:sticky_piston[extended=true]")
        check("tesoro: puerta cerrada en reposo", f"execute if block {w(M, 36, 4, 42)} minecraft:stone_bricks")
        check("tesoro: antorcha encendida", f"execute if block {w(M, 35, 3, 40)} minecraft:redstone_torch[lit=true]")
        # P1: the floor lever powers the block under it
        cmd(f"setblock {w(C, 33, 14, 17)} minecraft:redstone_block")
        ctx.ticks(40)
        check("estudio: la palanca abre la puerta (abajo)", f"execute if block {w(C, 32, 15, 17)} minecraft:air")
        check("estudio: la palanca abre la puerta (arriba)", f"execute if block {w(C, 32, 16, 17)} minecraft:air")
        check("estudio: las librerías quedan en el rincón", f"execute if block {w(C, 32, 16, 16)} minecraft:bookshelf")
        cmd(f"setblock {w(C, 33, 14, 17)} minecraft:stone_bricks")
        ctx.ticks(40)
        check("estudio: se vuelve a cerrar", f"execute if block {w(C, 32, 16, 17)} minecraft:bookshelf")
        # P2: fake lever (green) fires arrows; the red one opens the chamber
        cmd(f"setblock {w(M, 27, 4, 41)} minecraft:redstone_block")
        ctx.ticks(40)
        check("palanca verde: dispara", f"execute if entity @e[type=minecraft:arrow,x={M[0] + 27},y={M[1] + 3},z={M[2] + 42},distance=..8]", until=True)
        check("palanca verde: no abre", f"execute if block {w(M, 36, 4, 42)} minecraft:stone_bricks")
        cmd("kill @e[type=minecraft:arrow]", r"Killed|No entity")
        cmd(f"setblock {w(M, 30, 4, 41)} minecraft:redstone_block")
        ctx.ticks(40)
        check("palanca roja: abre la cámara del tesoro", f"execute if block {w(M, 36, 4, 42)} minecraft:air")
        check("palanca roja: no dispara", f"execute unless entity @e[type=minecraft:arrow,x={M[0] + 30},y={M[1] + 3},z={M[2] + 42},distance=..6]")
        # the tripwire trap
        cmd(f"summon minecraft:chicken {w(M, 14, 3, 40)} {{NoAI:1b}}")
        ctx.ticks(40)
        check("cable trampa: dispara saetas", f"execute if entity @e[type=minecraft:arrow,x={M[0] + 14},y={M[1] + 3},z={M[2] + 40},distance=..6]", until=True)
        # the plate trap (dynamite)
        cmd(f"summon minecraft:chicken {w(M, 39, 3, 5)} {{NoAI:1b}}")
        # lit dynamite lasts 80 ticks: it is checked every second until seen (with a fixed clock it might not have ignited)
        check("placa: prende la dinamita", f"execute if entity @e[type=minecraft:tnt,x={M[0] + 39},y={M[1] + 1},z={M[2] + 5},distance=..4]", until=True)
        # guardian
        # by its tag (it walks: not searched next to its spot) and waiting for it to appear
        g = "@e[type=minecraft:zombie,tag=heraldia_guardian.castillo,limit=1]"
        check("guardián presente y persistente", f"execute if entity {g.replace(',limit=1]', ',nbt={PersistenceRequired:1b}]')}", until=True)
        print("guardian at", ctx.pos(g))
        cmd(f"data get entity {g} equipment", r"has the following|No entity|found")
        cmd(f"data get entity {g} CustomName", r"has the following|No entity|found")
        cmd(f"attribute {g} minecraft:max_health get", r"is|No entity|Unknown")
        # chests with loot
        check("cofre premium", f"execute if block {w(M, 41, 3, 50)} minecraft:chest")
        check("cofre del pozo (anegado)", f"execute if block {w(C, 49, 1, 59)} minecraft:chest[waterlogged=true]")
        check("generador de la cripta", f"execute if block {w(M, 5, 3, 21)} minecraft:spawner")
        S.send(proc, "stop")
        proc.wait(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
    print("FALLOS:", fails if fails else "ninguno")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
