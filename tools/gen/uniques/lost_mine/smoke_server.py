"""Test on a real 26.3 server of the Lost Mine (complements tools/smoke/server_smoke.py).

1. Natural generation: /locate from 0,0 (each cell's candidate is sought in the lush or dripstone caves
   at the cavern's height, GridPlacement with "biome" and "biome_y"), measures the distance and time, loads
   those chunks and checks that the structure was really generated (its guardian is there, in its cave biome and at the
   cavern's height) and that the headframe pokes out at the surface (the shaft chain rises up to open air).
2. Places the whole structure with /place structure, measures how long it takes and counts its entities (Tizón, the loading dock
   minecart and the jetty boat).
3. Places the unrotated templates at known spots and checks chests, generators, water and tracks; operates the
   needle puzzle with the real minecart (only "needle 1 north, needle 2 east" takes it to the weighbridge and opens the
   hatch; the other combinations leave it at the dump or on the dead-end track), the foreman's secret office and
   the two traps (trap wire and plate over the dynamite).
   /setblock of a lever does not notify the block it is attached to: the click is emulated by changing that block and restoring it.
Usage (from the root): python3 tools/gen/uniques/lost_mine/smoke_server.py --jar build/libs/heraldia-X.jar [--work DIR]
"""
import argparse, math, os, subprocess, sys, threading, queue, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import server_smoke as sm                      # noqa: E402

SID = "mina_perdida"
COLONY, HEADFRAME = (3000, 40, 0), (3200, 100, 0)   # origin (minimum corner) of each unrotated placed template
GUARDIAN = f"@e[type=minecraft:vindicator,tag=heraldia_guardian.{SID}]"
MAX_LOCATE = 12000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_mina"))
    a = ap.parse_args()
    import uniques.lost_mine as M            # build coordinates (computed as when generating)
    from uniques.lost_mine import tracks
    tpls, meta, _, _, rep = M.dataset()
    construction, cast = rep["obra"], rep["castillete"]
    sx, sy, sz = rep["desplazamiento"]
    cx0, cy0, cz0 = rep["desplazamiento_castillete"]
    m, v = construction.mech, construction.mech["vias"]

    def at(p):
        return f"{COLONY[0] + p[0] - sx} {COLONY[1] + p[1] - sy} {COLONY[2] + p[2] - sz}"

    def at_c(p):
        return f"{HEADFRAME[0] + p[0] - cx0} {HEADFRAME[1] + p[1] - cy0} {HEADFRAME[2] + p[2] - cz0}"

    os.makedirs(a.work, exist_ok=True)
    launcher = sm.prepare(a.work, os.path.abspath(a.jar), sm.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=sm.reader, args=(proc, lines), daemon=True).start()
    ctx = sm.Context(proc, lines, seen)
    fails = []

    def cmd(c, ok=r"Test passed|Test failed|Generated|Changed|Loaded template|Marked|Added|Set the block|Could not|"
                  r"Summoned|has the following|No entity|Successfully|Killed|No block"):
        return sm.run(proc, lines, seen, c, ok)

    def check(desc, c, want=True, quiet=False):
        mm = cmd(c, r"Test passed(?:\. Count: (\d+))?|Test failed")
        ok = ("passed" in mm.group(0)) == want
        if not quiet:
            print(f"[{'OK' if ok else 'FALLO'}] {desc}")
            if not ok:
                fails.append(desc)
        return ok, mm

    def until(desc, c, want=True, secs=sm.UNTIL_S):
        """Repeats the check until it holds (or time runs out, generously: CI is slow): the minecarts and
        pistons take a while."""
        end = time.monotonic() + secs
        while True:
            ok, _ = check(desc, c, want, quiet=True)
            if ok or time.monotonic() > end:
                break
            time.sleep(1)
        print(f"[{'OK' if ok else 'FALLO'}] {desc}")
        if not ok:
            fails.append(desc)

    def is_block(desc, p, block, want=True):
        return check(desc, f"execute if block {at(p)} {block}", want)

    def touch(p, st):
        cmd(f"setblock {at(p)} minecraft:bedrock")
        cmd(f"setblock {at(p)} {st}")

    def lever(p, on, face="floor", facing="east"):
        cmd(f"setblock {at(p)} minecraft:lever[face={face},facing={facing},powered={str(on).lower()}]")

    def launch(combo):
        """New minecart at the exit, needles according to combo and start."""
        cmd(f"kill @e[type=minecraft:minecart,x={COLONY[0]},y={COLONY[1] - 30},z={COLONY[2]},dx=120,dy=80,dz=90]")
        for lp, on in zip(v["palancas"], combo):
            lever(lp, on)
        lever(v["arranque"], False)
        ctx.ticks(20)
        x, y, z = (int(c) for c in at(v["salida"]).split())
        cmd(f"summon minecraft:minecart {x + 0.5} {y + 0.1} {z + 0.5}")
        ctx.ticks(20)
        lever(v["arranque"], True)

    def cart_at(p, r=1):
        x, y, z = (int(c) for c in at(p).split())
        return f"execute if entity @e[type=minecraft:minecart,x={x - r},y={y - 1},z={z - r},dx={2 * r},dy=2,dz={2 * r}]"

    def well_ok(x, z):
        """Looks in the registry for the line of the nearest mine's shaft axis to (x, z) and checks the shaft chain
        from the colony to the headframe and the open air above it."""
        import re
        best = None
        for line in seen:
            mm = re.search(r"mina perdida en el chunk .*eje del pozo en (-?\d+), (-?\d+), pozo de (\d+) bloques de "
                           r"y = (-?\d+) a (-?\d+), suelo del castillete a y = (-?\d+)", line)
            if mm:
                ax, az = int(mm.group(1)), int(mm.group(2))
                d = abs(ax - x) + abs(az - z)
                if best is None or d < best[0]:
                    best = (d, ax, az, int(mm.group(4)), int(mm.group(5)), int(mm.group(6)), int(mm.group(3)))
        if best is None or best[0] > 200:
            print("[FAIL] the shaft axis is not found in the registry")
            fails.append("shaft axis")
            return
        _, ax, az, y0, y1, floor, length = best
        print(f"  SHAFT at {ax}, {az}: {length} blocks (y {y0}-{y1}), headframe at y = {floor}")
        for yy in (y0 - 3, (y0 + y1) // 2, y1, floor + 5):
            check(f"cadena del pozo en y = {yy}", f"execute if block {ax} {yy} {az} minecraft:iron_chain")
        check("la cubeta en el fondo del pozo", f"execute if block {ax} {y0 - M.YTOP} {az} minecraft:cauldron")
        check("aire libre sobre el castillete", f"execute if block {ax} {floor + 12} {az} minecraft:air")
        check("la viga maestra del castillete", f"execute if block {ax} {floor + 10} {az} minecraft:spruce_log")

    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        for line in seen:
            if "rejilla unicas/mina_perdida" in line:
                print("  ", line.split("]: ", 1)[-1].strip())
        # 1. natural generation
        t0 = time.monotonic()
        mm = cmd(f"locate structure heraldia:unicas/{SID}",
                 r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
        dt = time.monotonic() - t0
        if "Could not" in mm.group(0):
            fails.append("locate")
            print(f"[FAIL] /locate does not find the mine ({dt:.1f} s)")
        else:
            lx, lz, far = int(mm.group(1)), int(mm.group(2)), int(mm.group(3))
            print(f"LOCATE from 0, 0: mine at {lx}, {lz}, {far} blocks away ({dt * 1000:.0f} ms)")
            if far > MAX_LOCATE:
                fails.append(f"locate at {far} blocks")
            t0 = time.monotonic()
            sm.send(proc, f"forceload add {lx - 104} {lz - 104} {lx + 103} {lz + 103}")
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 600, seen)
            box = f"x={lx - 104},y=-64,z={lz - 104},dx=208,dy=400,dz=208"
            deadline, found = time.monotonic() + 240, False
            while time.monotonic() < deadline and not found:
                found, _ = check("guardián", f"execute if entity {GUARDIAN.replace(']', ',' + box + ']')}", quiet=True)
                if not found:
                    time.sleep(3)
            print(f"[{'OK' if found else 'FALLO'}] natural generation: the guardian is in the mine at {lx}, {lz} "
                  f"({time.monotonic() - t0:.0f} s en cargar)")
            if not found:
                fails.append("natural generation")
            else:
                g = GUARDIAN.replace("]", "," + box + "]")
                # without "execute as/at <selector>": they fork the command and a "Test failed" on one branch gets no reply
                pm = cmd(f"data get entity {g.replace(']', ',limit=1]')} Pos",
                         r"has the following entity data: \[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]")
                gx, gy, gz = (math.floor(float(v)) for v in pm.groups())
                ok = 0 <= gy <= 20
                print(f"[{'OK' if ok else 'FALLO'}] the guardian is at the mother lode's height (y 0-20: {gy})")
                if not ok:
                    fails.append("guardian at the mother lode's height")
                check("la caverna está en las cuevas exuberantes o de espeleotemas",
                      f"execute if biome {gx} {gy + 16} {gz} #heraldia:unicas/{SID}")
                well_ok(lx, lz)
                for line in seen:
                    if "búsqueda del bioma" in line and SID in line:
                        print("  ", line.split("]: ", 1)[-1].strip())
            sm.send(proc, f"forceload remove {lx - 104} {lz - 104} {lx + 103} {lz + 103}")
            sm.wait_for(lines, r"Unmarked|Removed|chunks? .*force|No chunks", 120, seen)
        for c in ("forceload add -96 -96 95 95", f"forceload add {COLONY[0] - 8} -8 {COLONY[0] + 120} 90",
                  f"forceload add {HEADFRAME[0] - 4} -4 {HEADFRAME[0] + 20} 16"):
            sm.send(proc, c)
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 300, seen)
        # 2. estructura entera
        for _ in range(sm.PLACE_ATTEMPTS):
            t0 = time.monotonic()
            mm = cmd(f"place structure heraldia:unicas/{SID} 0 ~ 0", r"Generated structure|not loaded|Failed|error")
            dt = time.monotonic() - t0
            if "not loaded" not in mm.group(0):
                break
            time.sleep(sm.PLACE_RETRY_S)
        if "Generated" not in mm.group(0):
            fails.append("place structure")
        print(f"TIME of /place structure for the Lost Mine: {dt * 1000:.0f} ms")
        time.sleep(10)
        well_ok(0, 0)
        nearby_flag = GUARDIAN.replace("]", ",x=0,y=0,z=0,distance=..200]")
        until("guardián con su etiqueta", f"execute if entity {nearby_flag}")
        _, mm = check("un solo guardián", f"execute if entity {nearby_flag}")
        print("  cuenta:", mm.group(1))
        if mm.group(1) != "1":
            fails.append("a single guardian")
        check("el guardián es persistente", f"execute if entity {nearby_flag.replace(']', ',nbt={PersistenceRequired:1b}]')}")
        check("el guardián lleva su casco de minero",
              f"execute if entity {nearby_flag.replace(']', ',nbt={equipment:{head:{id:\"minecraft:iron_helmet\"}}}]')}")
        _, mm = check("la vagoneta del cargadero", "execute if entity @e[type=minecraft:minecart,x=0,y=0,z=0,distance=..200]")
        print("  VAGONETAS:", mm.group(1))
        _, mm = check("la barca del embarcadero", "execute if entity @e[type=minecraft:oak_boat,x=0,y=0,z=0,distance=..200]")
        print("  BARCAS:", mm.group(1))
        _, mm = check("entidades de la estructura",
                      "execute if entity @e[type=!minecraft:item,type=!minecraft:experience_orb,type=!minecraft:player,"
                      "x=0,y=0,z=0,distance=..200]")
        print("  ENTIDADES:", mm.group(1))
        # 3. unrotated templates
        for name, base in (("colonia", COLONY), ("castillete", HEADFRAME)):
            mm = cmd(f"place template heraldia:unicas/{SID}/{name} {base[0]} {base[1]} {base[2]}",
                     r"Loaded template|Failed|not loaded|error|Could not")
            if "Loaded" not in mm.group(0):
                fails.append("place template " + name)
        ctx.ticks(100)
        # cofres, generadores, agua
        for p, tbl in construction.chests:
            check(f"cofre {tbl}", f"execute if data block {at(p)} LootTable", quiet=False) if tbl in (
                "premium", "despacho", "inundada", "alijo", "sima") else None
        for p, tbl in cast.chests:
            check(f"cofre {tbl} del castillete", f"execute if data block {at_c(p)} LootTable")
        check("la escalera del pozo en el castillete", f"execute if block {at_c((-1, 0, 0))} minecraft:ladder")
        for p, mob in construction.spawners:
            check(f"generador de {mob}", f"execute if data block {at(p)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        is_block("agua del lago", (44, -2, 50), "minecraft:water")
        is_block("cofre anegado del sector inundado", [p for p, t in construction.chests if t == "inundada"][0],
                 "minecraft:chest[waterlogged=true]")
        is_block("aire seco en la caverna junto al lago", (44, 1, 50), "minecraft:air")
        # puzzle 1: the needles with the real minecart
        door = v["puerta"]
        for p in door:
            is_block(f"compuerta cerrada al generarse {p}", p, "minecraft:air", want=False)
        until("la vagoneta de la plantilla espera en la salida", cart_at(v["salida"]))
        a1, a2 = v["agujas"]
        is_block("aguja 1 sin señal: hacia la escombrera", a1, "minecraft:rail[shape=south_east]")
        is_block("aguja 2 sin señal: hacia la báscula", a2, "minecraft:rail[shape=south_east]")
        launch((False, False))
        until("sin tocar las agujas la vagoneta acaba en la escombrera", cart_at(v["destinos"]["escombrera"]))
        is_block("y la compuerta sigue cerrada", door[0], "minecraft:air", want=False)
        launch((True, True))
        is_block("aguja 1 con señal: hacia el norte", a1, "minecraft:rail[shape=north_east]")
        is_block("aguja 2 con señal: hacia la fundición", a2, "minecraft:rail[shape=south_west]")
        until("con las dos agujas la vagoneta acaba en la vía muerta", cart_at(v["destinos"]["fundicion"]))
        is_block("y la compuerta sigue cerrada", door[0], "minecraft:air", want=False)
        launch(v["solucion"])
        until("aguja 1 al norte y aguja 2 al este: la vagoneta llega a la báscula", cart_at(v["bascula"], 0))
        until("la báscula se activa", f"execute if block {at(v['bascula'])} minecraft:detector_rail[powered=true]")
        for p in door:
            until(f"la compuerta del filón se abre {p}", f"execute if block {at(p)} minecraft:air")
        cmd(f"kill @e[type=minecraft:minecart,x={COLONY[0]},y={COLONY[1] - 30},z={COLONY[2]},dx=120,dy=80,dz=90]")
        until("sin la vagoneta la compuerta se vuelve a cerrar", f"execute if block {at(door[0])} minecraft:air",
              want=False)
        # puzzle 2: the foreman's office
        desc_es = m["puerta_despacho"]
        d0, d1 = desc_es["door"], (desc_es["door"][0], desc_es["door"][1] + 1, desc_es["door"][2])
        is_block("panel del despacho cerrado", d0, "minecraft:air", want=False)
        lp = desc_es["lever"]
        cmd(f"setblock {at(lp)} minecraft:lever[face=wall,facing=east,powered=true]")
        touch((lp[0] - 1, lp[1], lp[2]), "minecraft:bookshelf")
        for p in (d0, d1):
            until(f"la estantería abre el despacho {p}", f"execute if block {at(p)} minecraft:air")
        # trap 1: the trap wire at the loading dock mouth
        three = "{Items:[{Slot:0b,count:16},{Slot:1b,count:16},{Slot:2b,count:16}]}"
        for p in m["dispensadores"]:
            check(f"dispensador del cable cargado {p}", f"execute if data block {at(p)} {three}")
        x, y, z = (int(c) for c in at((81, 1, 36)).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        for p in m["dispensadores"]:
            until(f"el cable trampa dispara {p}", f"execute if data block {at(p)} {three}", want=False)
        # trap 2: the plate over the dynamite (the last one: it explodes)
        is_block("la dinamita bajo la placa", m["tnt"], "minecraft:tnt")
        x, y, z = (int(c) for c in at(m["placa_tnt"]).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        until("la placa prende la dinamita", f"execute if block {at(m['tnt'])} minecraft:tnt", want=False)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("LOST MINE TEST " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
