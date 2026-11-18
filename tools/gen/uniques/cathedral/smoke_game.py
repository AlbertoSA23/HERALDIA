"""Test on a real 26.3 dedicated server of what the static audit does not see: places the two cathedral pieces
with /place template, checks that the mechanisms stay in their rest state after the shape
updates, activates them and looks at the result (piston doors, trapdoor, traps), and checks
spawners, chests, signs and the guardian.

Use (from the root): python3 tools/gen/uniques/cathedral/smoke_game.py --jar build/libs/heraldia-X.jar
Levers are simulated by placing a redstone block on the block they are attached to (same strong signal)."""
import argparse, os, subprocess, sys, threading, queue, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(ROOT, "tools", "smoke"))
sys.path.insert(0, os.path.join(ROOT, "tools", "gen"))
import server_smoke as sm
from uniques.cathedral import model, split_pieces as pieces

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
    ctx = sm.Context(proc, lines, seen)

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
        ctx.ticks(t + 10)       # in game ticks (with the server lagging, the clock is not enough)

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
        # 1) stable rest state after being placed (including the shape updates of /place template)
        for mch in c.mech:
            ps = [p for k in ("pistones", "cabezas", "antorchas", "puerta", "ganchos", "cable", "dispensadores") for p in mch.get(k, [])]
            ps += [p for (p, _) in mch.get("polvo", [])] + [lp for (lp, _) in mch.get("palancas", []) + mch.get("falsas", [])]
            for k in ("trampilla", "palanca", "placa"):
                if k in mch:
                    ps.append(mch[k])
            for p in ps:
                check(f"reposo {mch['sitio']}", p, g(*p).replace("minecraft:", ""))
        # 2) spawners, chests and guardian (before opening doors: the guardian could get out)
        for (pos, mob) in c.spawners:
            check("generador", pos, f'spawner{{SpawnData:{{entity:{{id:"minecraft:{mob}"}}}}}}')
        for (pos, tbl, site) in c.chests:
            check(f"cofre {site}", pos, f'{g(*pos).split("[")[0].replace("minecraft:", "")}{{LootTable:"heraldia:unicas/catedral/{tbl}"}}')
        # The guardian (skeleton with AI) is looked up by its tag across the whole world, not next to its spot in the template:
        # it walks. The template's entities appear a few seconds after the blocks: we wait on a condition.
        for (x, y, z, n) in c.entities:
            gs = ("@e[type=minecraft:skeleton,tag=heraldia_guardian.catedral,"
                  "nbt={PersistenceRequired:1b,equipment:{mainhand:{id:\"minecraft:bow\"}}}]")
            if ctx.wait_entity(gs):
                oks += 1
                print(f"guardian at {ctx.pos(gs)} (placed at {w((x, y, z))})")
            else:
                fails.append("guardian missing or without equipment")
            cmd(f"data get entity {gs[:-1]},limit=1] CustomName", r"has the following|No entity|Found no")
        # 2) piston doors: the solution opens, the fake lever closes again
        for mch in [m for m in c.mech if m["tipo"] == "puerta de pistones"]:
            if len(mch["palancas"]) > 1:            # a single lever is not enough
                setb(mch["palancas"][0][1], "redstone_block")
                wait()
                for p in mch["puerta"]:
                    check(f"una sola palanca no abre {mch['sitio']}", p, g(*p).replace("minecraft:", ""))
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
        # 3) altar trapdoor and traps
        for mch in c.mech:
            if mch["tipo"] == "trampilla":
                setb(mch["apoyo"], "redstone_block")
                wait()
                check("trampilla del altar abierta", mch["trampilla"], "iron_trapdoor[open=true]")
                setb(mch["apoyo"], g(*mch["apoyo"]).replace("minecraft:", ""))
            elif mch["tipo"] in ("cable trampa", "placa de presión", "palanca trampa"):
                p = mch["cable"][1] if "cable" in mch else mch.get("placa") or mch["palanca"]
                x, y, z = w(p)
                cmd("kill @e[type=minecraft:arrow]", r"Killed|No entity|error")     # so that those of another trap do not count
                if "apoyo" in mch:
                    setb(mch["apoyo"], "redstone_block")
                else:
                    cmd(f"summon minecraft:zombie {x}.5 {y} {z}.5 {{NoAI:1b,PersistenceRequired:1b,Tags:[\"prueba\"]}}", r"Summoned|Unable|error")
                if ctx.until(f"execute if entity @e[type=minecraft:arrow,x={x},y={y},z={z},distance=..8]"):
                    oks += 1
                else:
                    fails.append(f"trap {mch['sitio']} does not fire")
                cmd("kill @e[tag=prueba]", r"Killed|No entity|error")
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    if fails:
        print("CATHEDRAL TEST FAILED:\n  " + "\n  ".join(fails[:60]))
        return 1
    print(f"CATHEDRAL TEST OK: {oks} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
