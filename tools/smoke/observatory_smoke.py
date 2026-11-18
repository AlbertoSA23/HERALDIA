"""Real-server test of the Observatory: circuits, traps, doors and guardian as they end up when placed.

Usage: python3 tools/smoke/observatory_smoke.py --jar build/libs/heraldia-X.jar [--work build/smoke_observatorio]
Places the underground piece with /place template (no rotation) and checks with /execute if block:
- resting state: puzzle door closed, torches as computed by the generator, pistons extended;
- phases puzzle: it opens with a new and a full moon; with one extra crescent it closes;
- the study's piston door: when the torch's support is powered they retract and open the way;
- traps: the hook and the pressure plates activate their dispensers; the treasure chamber door opens;
- guardian: a persistent skeleton with 40 health; and /place structure also places the underground part (second guardian).
Levers are simulated with redstone blocks on their support (equivalent to the lever's strong power).
"""
import argparse, os, queue, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import server_smoke as S                      # noqa: E402
from uniques import observatory as O          # noqa: E402

BASE = (0, 120, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(S.ROOT, "build", "smoke_observatorio"))
    args = ap.parse_args()
    _, b = O.split(O.build_full())
    bx, by, bz, *_ = b.bounds()

    def at(x, y, z):
        return f"{BASE[0] + x - bx} {BASE[1] + y - by} {BASE[2] + z - bz}"

    os.makedirs(args.work, exist_ok=True)
    launcher = S.prepare(args.work, os.path.abspath(args.jar), S.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=S.reader, args=(proc, lines), daemon=True).start()
    ctx = S.Context(proc, lines, seen)
    fails = []

    def check(desc, pos, state):
        if not ctx.block(at(*pos), state):
            fails.append(desc)

    def put(pos, state):
        S.run(proc, lines, seen, f"setblock {at(*pos)} {state}", r"Changed the block|Could not set")
        ctx.ticks(80)           # in game ticks: with the server lagging, the clock is not enough

    def count_until(sel, n):
        """Counts the selector until it gives `n` (a template's entities appear after the blocks)."""
        end = time.monotonic() + S.UNTIL_S
        while (got := ctx.count(sel)) != n and time.monotonic() < end:
            time.sleep(S.POLL_S)
        return got

    try:
        S.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", S.START_TIMEOUT_S, seen)
        S.send(proc, S.FORCELOAD)
        S.wait_for(lines, r"Marked|Added|chunks? .*force", S.COMMAND_TIMEOUT_S, seen)
        for _ in range(S.PLACE_ATTEMPTS):
            m = S.run(proc, lines, seen, f"place template heraldia:unicas/observatorio/subsuelo {BASE[0]} {BASE[1]} {BASE[2]}",
                      r"Loaded template|[Pp]laced|not loaded|Failed")
            if "not loaded" not in m.group(0):
                break
            time.sleep(S.PLACE_RETRY_S)
        ctx.ticks(200)
        door, vault = (27, -6, 21), (7, -13, 10)
        check("puerta del puzle cerrada en reposo", door, "minecraft:iron_door[open=false]")
        check("antorcha de salida apagada", (27, -5, 22), "minecraft:redstone_wall_torch[lit=false]")
        for z in (25, 29):
            check(f"antorcha de la fase {z} encendida", (28, -5, z), "minecraft:redstone_wall_torch[lit=true]")
        check("pistón extendido", (18, -6, 18), "minecraft:sticky_piston[extended=true]")
        check("sello en su sitio", (20, -6, 18), "minecraft:bookshelf")
        # puzle
        put((27, -5, 25), "minecraft:redstone_block")
        put((27, -5, 29), "minecraft:redstone_block")
        for z in (25, 29):
            check(f"antorcha de la fase {z} apagada al resolver", (28, -5, z), "minecraft:redstone_wall_torch[lit=false]")
        for p in ((29, -5, 25), (30, -5, 25), (30, -5, 22), (29, -5, 22)):
            check(f"polvo {p} sin potencia al resolver", p, "minecraft:redstone_wire[power=0]")
        check("antorcha de salida encendida al resolver", (27, -5, 22), "minecraft:redstone_wall_torch[lit=true]")
        check("puzle resuelto abre la puerta", door, "minecraft:iron_door[open=true]")
        put((27, -5, 27), "minecraft:redstone_block")
        check("fase de más cierra la puerta", door, "minecraft:iron_door[open=false]")
        put((27, -5, 27), "minecraft:" + O.WALLB)
        check("al quitarla se vuelve a abrir", door, "minecraft:iron_door[open=true]")
        # puerta de pistones
        put((17, -5, 19), "minecraft:redstone_block")
        for y in (-6, -5):
            check(f"paso abierto a y={y}", (20, y, 18), "minecraft:air")
            check(f"estantería retirada a y={y}", (19, y, 18), "minecraft:bookshelf")
        # traps and treasure chamber
        put((11, -6, 30), "minecraft:tripwire_hook[attached=true,facing=south,powered=true]")
        check("gancho dispara su dispensador", (11, -5, 30), "minecraft:dispenser[triggered=true]")
        put((20, -13, 10), "minecraft:stone_pressure_plate[powered=true]")
        for z in (9, 11):
            check(f"placa activa el dispensador z={z}", (20, -13, z), "minecraft:dispenser[triggered=true]")
        put((7, -12, 11), "minecraft:redstone_block")
        check("puerta de la cámara del tesoro", vault, "minecraft:iron_door[open=true]")
        # The guardian is searched by its tag and its maximum health (attribute), not by its current health: with AI it may step on
        # a trap and get hurt. We wait for it to appear (a template's entities take longer than the blocks).
        sel = "@e[type=minecraft:skeleton,tag=heraldia_guardian.observatorio,nbt={PersistenceRequired:1b}]"
        n = count_until(sel, 1)
        if n != 1:
            fails.append(f"guardian missing or without its attributes ({n}; {ctx.diagnose(sel)})")
        else:
            m = S.run(proc, lines, seen, f"attribute {sel[:-1]},limit=1] minecraft:max_health base get",
                      r"[Bb]ase value of attribute .* is (-?[\d.]+)|No entity")
            if m.group(1) is None or float(m.group(1)) != 40.0:
                fails.append(f"guardian without 40 maximum health: {m.string.strip()}")
        S.run(proc, lines, seen, f"data get entity {sel[:-1]},limit=1] CustomName", r"has the following|No entity|found")
        S.run(proc, lines, seen, "place structure heraldia:unicas/observatorio 64 ~ 64", r"Generated structure")
        if count_until(sel, 2) != 2:
            fails.append("/place structure does not place the underground part (the second guardian is missing)")
    finally:
        if proc.poll() is None:
            S.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    text = "".join(seen)
    for bad in ("Registry loading errors", "Failed to load", "Couldn't load", "Failed to parse"):
        if bad in text:
            fails.append(f"the log contains {bad!r}")
    if fails:
        print("OBSERVATORIO: FALLOS:", fails)
        return 1
    print("OBSERVATORY OK: consistent resting state, puzzle, pistons, traps, chamber and guardian")
    return 0


if __name__ == "__main__":
    sys.exit(main())
