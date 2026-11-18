"""Test on a real 26.3 server of the Corsair's island (complements tools/smoke/server_smoke.py).

1. Natural generation: /locate from 0,0 (each cell's candidate is sought in the temperate and warm oceans,
   GridPlacement with "biome"; the heraldia:isla type requires open sea with the floor at medium depth), measures the
   distance and time, loads those chunks and checks that the site is one of its oceans, that the structure was
   really generated (the corsair is in the treasure chamber, below sea level and dry), that it is far from
   Atlantis (outside its exclusion zone) and that no shipwreck or ocean ruin spawns inside it (IslaZona).
2. Places the whole structure with /place structure, measures how long it takes and counts its entities (the corsair and the cove
   boat).
3. Places the unrotated template at a known spot and checks chests, generators, cove water and dry
   rooms; operates the mechanisms: the compass rose (north and west open; with east it closes again), the
   secret powder magazine, the trap wire and the antechamber plates.
   /setblock of a lever does not notify the block it is attached to: the click is emulated by changing that block and restoring it.
Usage (from the root): python3 tools/gen/uniques/corsair_island/smoke_server.py --jar build/libs/heraldia-X.jar [--work DIR]
"""
import argparse, math, os, subprocess, sys, threading, queue, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import server_smoke as sm                      # noqa: E402

SID = "isla_corsario"
ORIGIN = (3000, 45, 0)                         # minimum corner of the unrotated placed template
THREE = "{Items:[{Slot:0b,count:6},{Slot:1b,count:6},{Slot:2b,count:6}]}"     # wire dispenser (tripwire_trap)
SINGLE = "{Items:[{Slot:0b,count:16}]}"                                          # plate dispenser (plate_trap)
GUARDIAN = f"@e[type=minecraft:skeleton,tag=heraldia_guardian.{SID}]"
OCEANS = ("ocean", "lukewarm_ocean", "warm_ocean")
MAX_LOCATE = 12000
ATLANTIS_EXCLUSION = 444 + 60                 # Atlantis exclusion radius (AtlantisAnchor) + half an island
ISLAND_RADIUS = 70                                # the islet and the brigantine, from the center (IslaZona excludes 7 chunks)
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_isla"))
    a = ap.parse_args()
    import uniques.corsair_island as M           # build coordinates (computed as when generating)
    from core import parse_state
    t, _, _, rep = M.dataset()
    construction, (sx, sy, sz) = rep["obra"], rep["desplazamiento"]
    m = construction.mech

    def at(p):
        return f"{ORIGIN[0] + p[0] - sx} {ORIGIN[1] + p[1] - sy} {ORIGIN[2] + p[2] - sz}"

    def tpl(p):
        return t.get(p[0] - sx, p[1] - sy, p[2] - sz)

    os.makedirs(a.work, exist_ok=True)
    launcher = sm.prepare(a.work, os.path.abspath(a.jar), sm.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=sm.reader, args=(proc, lines), daemon=True).start()
    ctx = sm.Context(proc, lines, seen)
    fails = []

    def cmd(c, ok=r"Test passed|Test failed|Generated|Changed|Loaded template|Marked|Added|Set the block|Could not|"
                  r"Summoned|has the following|No entity|Successfully"):
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

    def has_loot(desc, p):
        return check(desc, f"execute if data block {at(p)} LootTable")

    def lever(lp, on):
        """Operates a lever like a player: changes it and "touches" the block it is attached to."""
        st = tpl(lp)
        b, props = parse_state(st)
        dx, dz = DV[props["facing"]]
        bp = (lp[0] - dx, lp[1], lp[2] - dz)
        cmd(f"setblock {at(lp)} minecraft:lever[face=wall,facing={props['facing']},powered={str(on).lower()}]")
        cmd(f"setblock {at(bp)} minecraft:bedrock")
        cmd(f"setblock {at(bp)} {tpl(bp)}")

    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        # 1. natural generation
        t0 = time.monotonic()
        mm = cmd(f"locate structure heraldia:unicas/{SID}",
                 r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
        dt = time.monotonic() - t0
        if "Could not" in mm.group(0):
            fails.append("locate")
            print(f"[FAIL] /locate does not find the island ({dt:.1f} s)")
        else:
            lx, lz, far = int(mm.group(1)), int(mm.group(2)), int(mm.group(3))
            print(f"LOCATE from 0, 0: corsair's island at {lx}, {lz}, {far} blocks away ({dt * 1000:.0f} ms)")
            if far > MAX_LOCATE:
                fails.append(f"locate at {far} blocks")
            ma = cmd("locate structure heraldia:unicas/atlantida",
                     r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
            if "Could not" not in ma.group(0):
                d = math.hypot(int(ma.group(1)) - lx, int(ma.group(2)) - lz)
                ok = d > ATLANTIS_EXCLUSION
                print(f"[{'OK' if ok else 'FALLO'}] the island is outside Atlantis ({d:.0f} blocks from its center)")
                if not ok:
                    fails.append("island inside Atlantis")
            for tag in ("shipwreck", "ocean_ruin"):   # IslaZona: nothing foreign inside the island (same in /locate)
                mm = cmd(f"execute positioned {lx} 64 {lz} run locate structure #minecraft:{tag}",
                         r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
                d = 10 ** 9 if "Could not" in mm.group(0) else int(mm.group(3))
                ok = d > ISLAND_RADIUS
                print(f"[{'OK' if ok else 'FALLO'}] no {tag} inside the island (the nearest is {d} blocks away)")
                if not ok:
                    fails.append(f"{tag} inside the island")
            sm.send(proc, f"forceload add {lx - 80} {lz - 80} {lx + 80} {lz + 80}")
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 600, seen)
            for _ in range(30):                     # the forced chunks load over the following ticks
                mm = cmd(f"execute if biome {lx} 62 {lz} minecraft:{OCEANS[0]}", r"Test passed|Test failed")
                if "not loaded" not in mm.group(0):
                    break
                time.sleep(2)
            ok = any(check("", f"execute if biome {lx} 62 {lz} minecraft:{b}", quiet=True)[0] for b in OCEANS)
            print(f"[{'OK' if ok else 'FALLO'}] the /locate site is a temperate or warm ocean")
            if not ok:
                fails.append("biome of the /locate site")
            sel = GUARDIAN.replace("]", f",x={lx - 80},y=0,z={lz - 80},dx=160,dy=120,dz=160]")
            deadline, found = time.monotonic() + 120, False
            while time.monotonic() < deadline and not found:
                found = check("", f"execute if entity {sel}", quiet=True)[0]
                if not found:
                    time.sleep(3)
            print(f"[{'OK' if found else 'FALLO'}] natural generation: the corsair is on the island at {lx}, {lz}")
            if not found:
                fails.append("natural generation")
            else:
                time.sleep(20)                      # if the sea were to enter the treasure chamber, it would already have
                # Without "execute as/at <selector>": they fork the command and on one branch the "Test failed" gets no reply (the
                # test was left waiting). Its position is read and those coordinates are checked.
                if not check("el corsario sigue en la isla tras 20 s", f"execute if entity {sel}")[0]:
                    print("  DIAG", cmd(f"execute if entity {GUARDIAN}", r"Test passed(?:\. Count: \d+)?|Test failed").group(0))
                else:
                    lim = sel.replace("]", ",limit=1]")
                    pm = cmd(f"data get entity {lim} Pos", r"has the following entity data: \[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]")
                    gx, gy, gz = (math.floor(float(v)) for v in pm.groups())
                    # one condition per command: a failing intermediate "if" gets no reply either. The corsair walks around the
                    # chamber (it may step on a slab or a chest): what is required is that there be no water where it is
                    for y in (gy, gy + 1):
                        check(f"sin agua en la cámara del tesoro ({gx}, {y}, {gz})", f"execute unless block {gx} {y} {gz} minecraft:water")
                    ok = gy < 62
                    print(f"[{'OK' if ok else 'FALLO'}] the corsair is still below sea level (y = {gy})")
                    if not ok:
                        fails.append("corsair below sea level")
            for line in seen:
                if "isla del corsario en" in line or "búsqueda del bioma" in line:
                    print("  ", line.split("]: ", 1)[-1])
        for c in ("forceload add -96 -96 95 95", f"forceload add {ORIGIN[0] - 8} -8 {ORIGIN[0] + 120} 120"):
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
        print(f"TIME of /place structure for the Corsair's island: {dt * 1000:.0f} ms")
        nearby_flag = GUARDIAN.replace("]", ",x=0,y=0,z=0,distance=..120]")
        ctx.wait_entity(nearby_flag)              # entities appear a few seconds after the blocks
        ctx.wait_entity("@e[type=minecraft:oak_boat,x=0,y=0,z=0,distance=..120]")
        ok, mm = check("corsario con su etiqueta", f"execute if entity {nearby_flag}")
        print("  cuenta:", mm.group(1))
        if mm.group(1) != "1":
            fails.append("a single guardian")
        check("el corsario es persistente", f"execute if entity {nearby_flag.replace(']', ',nbt={PersistenceRequired:1b}]')}")
        check("el corsario lleva su arco",
              f"execute if entity {nearby_flag.replace(']', ',nbt={equipment:{mainhand:{id:\"minecraft:bow\"}}}]')}")
        ok, mm = check("la barca de la ensenada", "execute if entity @e[type=minecraft:oak_boat,x=0,y=0,z=0,distance=..120]")
        print("  BARCAS:", mm.group(1))
        ok, mm = check("entidades de la estructura (sin objetos sueltos)",
                       "execute if entity @e[type=!minecraft:item,type=!minecraft:experience_orb,type=!minecraft:arrow,"
                       "x=0,y=0,z=0,distance=..120]")
        print("  ENTIDADES:", mm.group(1))
        # 3. unrotated template
        mm = cmd(f"place template heraldia:unicas/{SID}/isla {ORIGIN[0]} {ORIGIN[1]} {ORIGIN[2]}",
                 r"Loaded template|Failed|not loaded|error|Could not")
        if "Loaded" not in mm.group(0):
            fails.append("place template")
        ctx.ticks(100)
        for p, tbl in construction.chests:
            if tbl in ("premium", "cartas", "escondite", "santabarbara", "bergantin", "ensenada", "polvorin"):
                has_loot(f"cofre {tbl}", p)
        print(f"  {len(construction.chests)} chests in the build")
        for p, mob in construction.spawners:
            check(f"generador de {mob}", f"execute if data block {at(p)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        for p in m["canones"]:
            is_block(f"cañón {p}", p, "minecraft:dispenser")
        bx0, bx1 = m["ensenada"]["boca"]
        lx0, lx1, lz0, lz1 = m["ensenada"]["laguna"]
        ctx.ticks(200)
        is_block("agua quieta en la ensenada", (lx0 + 5, -1, lz0 + 2), "minecraft:water[level=0]")
        is_block("aire seco sobre la ensenada", (lx0 + 5, 0, lz0 + 2), "minecraft:air")
        is_block("el muelle de la ensenada sin agua", (lx0, 0, lz1 - 1), "minecraft:air")
        is_block("tarima del muelle del puerto", (44, 0, 85), "minecraft:spruce_planks")
        # puzzle 1: the compass rose (north and west; east and south are fake)
        door = m["puerta_rosa"]
        n, e, s, w = m["palancas"]
        for p in door:
            is_block(f"puerta del tesoro cerrada al generarse {p}", p, "minecraft:chiseled_stone_bricks")
        lever(n, True)
        ctx.ticks(40)
        is_block("solo con el norte sigue cerrada", door[0], "minecraft:chiseled_stone_bricks")
        lever(w, True)
        ctx.ticks(20)
        for p in door:
            until(f"norte y poniente abren la puerta del tesoro {p}", f"execute if block {at(p)} minecraft:air")
        lever(e, True)
        until("con levante se vuelve a cerrar", f"execute if block {at(door[0])} minecraft:chiseled_stone_bricks")
        lever(e, False)
        until("y al bajarla se abre otra vez", f"execute if block {at(door[0])} minecraft:air")
        # puzzle 2: the powder magazine
        sb = m["santabarbara"]
        sec = [sb["door"], (sb["door"][0], sb["door"][1] + 1, sb["door"][2])]
        for p in sec:
            is_block(f"santabárbara cerrada {p}", p, "minecraft:stone_bricks")
        lever(sb["lever"], True)
        for p in sec:
            until(f"la palanca del armero abre la santabárbara {p}", f"execute if block {at(p)} minecraft:air")
        # trampas
        d1, d2 = m["dispensadores_cable"]
        check("dispensadores del cable trampa cargados", f"execute if data block {at(d1)} {THREE}")
        x, y, z = (int(c) for c in at(m["cable"][0]).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        until("el cable trampa dispara (norte)", f"execute if data block {at(d1)} {THREE}", want=False)
        until("el cable trampa dispara (sur)", f"execute if data block {at(d2)} {THREE}", want=False)
        f1 = m["flechas"][0]
        check("dispensadores de las placas cargados", f"execute if data block {at(f1)} {SINGLE}")
        x, y, z = (int(c) for c in at(m["placas"][0]).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        until("la placa dispara", f"execute if data block {at(f1)} {SINGLE}", want=False)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("CORSAIR'S ISLAND TEST " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
