"""Test on a real 26.3 server of the Mycologist's laboratory (complements tools/smoke/server_smoke.py).

1. Natural generation: /locate from 0,0 (each cell's candidate is searched in the mushroom fields,
   GridPlacement with "biome"), measures the distance and the time, loads those chunks and checks that the site is mushroom
   fields and that the structure has really generated (its guardian is there).
2. Places the whole structure with /place structure, measures how long it takes and counts its entities after a few seconds
   (the guardian, Maese Ambrosio, a bogged skeleton, and the three mooshrooms of the pen).
3. Places the unrotated templates at known spots and checks chests, spawners, crops and water; operates the
   mechanisms: the reagent mix (with a false flask it closes again), the secret panel of the strain vault, the
   trap wire and the plates of the reagent cabinet.
   /setblock of a lever does not notify the block it is attached to: the click is emulated by changing that block and restoring it.
Usage (from the root): python3 tools/gen/uniques/mycelium_lab/smoke_server.py --jar build/libs/heraldia-X.jar
                     [--work DIR]
"""
import argparse, os, re, subprocess, sys, threading, queue, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
import server_smoke as sm                      # noqa: E402

SID = "laboratorio_micelio"
GARDEN, TUNNELS = (3000, 100, 0), (3200, 100, 0)  # origin of each template placed unrotated
TUNNELS_MIN = (4, -14, 6)                         # minimum corner of the underground in build coordinates (construction.TUNNELS)
THREE = "{Items:[{Slot:0b,count:16},{Slot:1b,count:16},{Slot:2b,count:16}]}"   # wire dispenser (tripwire_trap)
SINGLE = "{Items:[{Slot:0b,count:16}]}"                                          # plate dispenser (plate_trap)
GUARDIAN = f"@e[type=minecraft:bogged,tag=heraldia_guardian.{SID}]"
MAX_LOCATE = 12000                                 # blocks: farther than this is no longer "a reasonable distance"


def at(p, sub=False):
    x, y, z = p
    base = TUNNELS if sub else GARDEN
    if sub:
        x, y, z = x - TUNNELS_MIN[0], y - TUNNELS_MIN[1], z - TUNNELS_MIN[2]
    return f"{base[0] + x} {base[1] + y} {base[2] + z}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_laboratorio"))
    a = ap.parse_args()
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

    def check(desc, c, want=True):
        m = cmd(c, r"Test passed(?:\. Count: (\d+))?|Test failed")
        ok = ("passed" in m.group(0)) == want
        print(f"[{'OK' if ok else 'FALLO'}] {desc}")
        if not ok:
            fails.append(desc)
        return m

    def lever(lp, bp, facing, on, sub=True):
        cmd(f"setblock {at(lp, sub)} minecraft:lever[face=wall,facing={facing},powered={str(on).lower()}]")
        cmd(f"setblock {at(bp, sub)} minecraft:bedrock")
        cmd(f"setblock {at(bp, sub)} {blocks_at[bp]}")

    def is_block(desc, p, block, sub=False, want=True):
        return check(desc, f"execute if block {at(p, sub)} {block}", want)

    def has_loot(desc, p, sub=False):
        return check(desc, f"execute if data block {at(p, sub)} LootTable")

    blocks_at = {}
    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        # 1. natural generation
        t0 = time.monotonic()
        m = cmd(f"locate structure heraldia:unicas/{SID}",
                r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
        dt = time.monotonic() - t0
        if "Could not" in m.group(0):
            fails.append("locate")
            print(f"[FAIL] /locate does not find the laboratory ({dt:.1f} s)")
        else:
            lx, lz, far = int(m.group(1)), int(m.group(2)), int(m.group(3))
            print(f"LOCATE from 0, 0: laboratory at {lx}, {lz}, {far} blocks away ({dt * 1000:.0f} ms)")
            if far > MAX_LOCATE:
                fails.append(f"locate at {far} blocks")
            sm.send(proc, f"forceload add {lx - 48} {lz - 48} {lx + 112} {lz + 112}")
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 600, seen)
            for _ in range(30):                     # the forced chunks load in the following ticks
                mm = cmd(f"execute if biome {lx} 64 {lz} minecraft:mushroom_fields", r"Test passed|Test failed")
                if "not loaded" not in mm.group(0):
                    break
                ctx.ticks(40)
            ok = "passed" in mm.group(0)
            print(f"[{'OK' if ok else 'FALLO'}] the /locate site is mushroom fields")
            if not ok:
                fails.append("biome of the /locate site")
            deadline, found = time.monotonic() + 120, False
            while time.monotonic() < deadline and not found:
                mm = cmd(f"execute if entity {GUARDIAN.replace(']', f',x={lx - 64},y=-64,z={lz - 64},dx=200,dy=400,dz=200]')}",
                         r"Test passed|Test failed")
                found = "passed" in mm.group(0)
                if not found:
                    ctx.ticks(60)
            print(f"[{'OK' if found else 'FALLO'}] natural generation: the guardian is in the laboratory at {lx}, {lz}")
            if not found:
                fails.append("natural generation")
            for line in seen:
                if "búsqueda del bioma" in line:
                    print("  ", line.split("]: ", 1)[-1])
        for c in ("forceload add -96 -96 95 95", "forceload add 2990 -10 3070 70", "forceload add 3190 -10 3260 70"):
            sm.send(proc, c)
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 300, seen)
        # 2. estructura entera
        for _ in range(sm.PLACE_ATTEMPTS):
            t0 = time.monotonic()
            m = cmd(f"place structure heraldia:unicas/{SID} 0 ~ 0", r"Generated structure|not loaded|Failed|error")
            dt = time.monotonic() - t0
            if "not loaded" not in m.group(0):
                break
            time.sleep(sm.PLACE_RETRY_S)
        if "Generated" not in m.group(0):
            fails.append("place structure")
        print(f"TIME of /place structure of the Mycologist's laboratory: {dt * 1000:.0f} ms")
        nearby_flag = GUARDIAN.replace("]", ",x=0,y=0,z=0,distance=..200]")   # the one from the natural laboratory is still loaded
        # the structure's entities appear a few seconds after the blocks: wait on a condition
        ctx.wait_entity(nearby_flag)
        end = time.monotonic() + sm.UNTIL_S
        while ctx.count("@e[type=minecraft:mooshroom,x=0,y=0,z=0,distance=..120,nbt={PersistenceRequired:1b}]") < 3 \
                and time.monotonic() < end:
            time.sleep(sm.POLL_S)
        m = check("guardián con su etiqueta", f"execute if entity {nearby_flag}")
        print("  cuenta:", m.group(1))
        if m.group(1) != "1":
            fails.append("a single guardian")
        check("el guardián es persistente", f"execute if entity {nearby_flag.replace(']', ',nbt={PersistenceRequired:1b}]')}")
        check("el guardián lleva su sombrero de champiñón",
              f"execute if entity {nearby_flag.replace(']', ',nbt={equipment:{head:{id:\"minecraft:red_mushroom_block\"}}}]')}")
        m = check("los champiñocas del corral",
                  "execute if entity @e[type=minecraft:mooshroom,x=0,y=0,z=0,distance=..120,nbt={PersistenceRequired:1b}]")
        print("  MOOSHROOMS:", m.group(1))
        if m.group(1) != "3":
            fails.append("three mooshrooms")
        m = check("entidades de la estructura (guardián y champiñocas)",
                  "execute if entity @e[type=!minecraft:item,type=!minecraft:experience_orb,x=0,y=0,z=0,distance=..120,"
                  "nbt={PersistenceRequired:1b}]")
        print("  ENTIDADES:", m.group(1))
        # 3. unrotated templates
        for name, base in (("jardin", GARDEN), ("galerias", TUNNELS)):
            m = cmd(f"place template heraldia:unicas/{SID}/{name} {base[0]} {base[1]} {base[2]}",
                    r"Loaded template|Failed|not loaded|error|Could not")
            if "Loaded" not in m.group(0):
                fails.append("place template " + name)
        ctx.ticks(100)
        # the garden
        has_loot("cofre de la alcoba del micólogo", (34, 13, 41))
        is_block("tapiz ante el paso a la alcoba", (32, 15, 38), "minecraft:red_wall_banner")
        is_block("paso tras el tapiz abierto", (32, 13, 39), "minecraft:air")
        has_loot("cofre de la biblioteca de esporas (pliego)", (50, 1, 12))
        has_loot("tonel del secadero", (56, 13, 15))
        has_loot("cofre del dormitorio de los ayudantes", (12, 7, 27))
        is_block("verruga del Nether madura en el invernadero", (12, 1, 42), "minecraft:nether_wart[age=3]")
        is_block("agua de la acequia del invernadero", (12, 0, 44), "minecraft:water[level=0]")
        is_block("bancal regado", (12, 0, 43), "minecraft:farmland[moisture=7]")
        is_block("coro sobre piedra del End", (10, 1, 52), "minecraft:chorus_flower")
        is_block("cacao en el tronco de jungla", (11, 2, 50), "minecraft:cocoa")
        # the galleries
        for p, mob in (((57, -5, 25), "spider"), ((13, -11, 21), "cave_spider"), ((52, -11, 21), "zombie")):
            check(f"generador de {mob}", f"execute if data block {at(p, True)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        has_loot("cofre premium", (25, -11, 59), True)
        has_loot("cofre de la cepa madre", (19, -11, 51), True)
        door = [(34, -11, 40), (34, -10, 40)]
        for p in door:
            is_block(f"puerta de los reactivos cerrada al generarse {p}", p, "minecraft:chiseled_stone_bricks", True)
        is_block("pistón de los reactivos extendido", (34, -10, 42), "minecraft:sticky_piston[extended=true]", True)
        # puzzle 1: the reagents (x 36 = flask, x 37 = lever; z 44 spider eye, 46 spore, 48 gunpowder,
        # 50 wart, 52 glowstone dust). Solution: spore, wart and light.
        for z in (44, 46, 48, 50, 52):
            blocks_at[(36, -10, z)] = "minecraft:polished_andesite"
        lever((37, -10, 46), (36, -10, 46), "east", True)
        lever((37, -10, 50), (36, -10, 50), "east", True)
        ctx.ticks(40)
        is_block("con espora y verruga la puerta sigue cerrada", door[0], "minecraft:chiseled_stone_bricks", True)
        lever((37, -10, 52), (36, -10, 52), "east", True)
        ctx.ticks(60)
        for p in door:
            is_block(f"espora, verruga y luz abren la puerta {p}", p, "minecraft:air", True)
        lever((37, -10, 44), (36, -10, 44), "east", True)
        ctx.ticks(60)
        is_block("con el ojo de araña se vuelve a cerrar", door[0], "minecraft:chiseled_stone_bricks", True)
        lever((37, -10, 44), (36, -10, 44), "east", False)
        ctx.ticks(60)
        is_block("y al quitarlo se abre otra vez", door[0], "minecraft:air", True)
        # puzzle 2: the stem panel of the strain vault
        sec = [(13, -5, 16), (13, -4, 16)]
        for p in sec:
            is_block(f"panel del cepario cerrado {p}", p, "minecraft:mushroom_stem", True)
        blocks_at[(16, -5, 17)] = "minecraft:stone_bricks"
        lever((16, -5, 18), (16, -5, 17), "south", True)
        ctx.ticks(60)
        for p in sec:
            is_block(f"la palanca abre el cepario {p}", p, "minecraft:air", True)
        # trampas
        check("dispensadores del cable trampa cargados", f"execute if data block {at((48, -4, 21), True)} {THREE}")
        x, y, z = (int(c) for c in at((48, -5, 22), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        ctx.ticks(60)
        check("el cable trampa dispara (norte)", f"execute if data block {at((48, -4, 21), True)} {THREE}", want=False)
        check("el cable trampa dispara (sur)", f"execute if data block {at((48, -4, 24), True)} {THREE}", want=False)
        check("dispensadores de las placas cargados", f"execute if data block {at((44, -11, 37), True)} {SINGLE}")
        x, y, z = (int(c) for c in at((44, -11, 38), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        ctx.ticks(60)
        check("la placa dispara (norte)", f"execute if data block {at((44, -11, 37), True)} {SINGLE}", want=False)
        check("la placa dispara (sur)", f"execute if data block {at((44, -11, 39), True)} {SINGLE}", want=False)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("MYCOLOGIST'S LABORATORY TEST " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
