"""Prueba en un servidor 26.3 real del Laboratorio del micólogo (complementa tools/smoke/server_smoke.py).

1. Generación natural: /locate desde el 0,0 (la candidata de cada casilla se busca en los campos de champiñones,
   GridPlacement con «bioma»), mide la distancia y el tiempo, carga esos chunks y comprueba que el sitio es campo de
   champiñones y que la estructura se ha generado de verdad (su guardián está allí).
2. Coloca la estructura entera con /place structure, mide cuánto tarda y cuenta sus entidades tras unos segundos
   (el guardián, Maese Ambrosio, un esqueleto pantanoso, y los tres champiñocas del corral).
3. Coloca las plantillas sin girar en sitios conocidos y comprueba cofres, generadores, cultivos y agua; acciona los
   mecanismos: la mezcla de los reactivos (con un frasco falso se vuelve a cerrar), el panel secreto del cepario, el
   cable trampa y las placas del armario de reactivos.
   /setblock de una palanca no avisa al bloque al que está sujeta: se emula el clic cambiando ese bloque y devolviéndolo.
Uso (desde la raíz): python3 tools/gen/unicas/laboratorio_micelio/prueba_servidor.py --jar build/libs/heraldia-X.jar
                     [--work DIR]
"""
import argparse, os, re, subprocess, sys, threading, queue, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
import server_smoke as sm                      # noqa: E402

SID = "laboratorio_micelio"
JARDIN, GALERIAS = (3000, 100, 0), (3200, 100, 0)  # origen de cada plantilla colocada sin girar
GALERIAS_MIN = (4, -14, 6)                         # esquina mínima del subsuelo en coordenadas de la obra (obra.GALERIAS)
TRES = "{Items:[{Slot:0b,count:16},{Slot:1b,count:16},{Slot:2b,count:16}]}"   # dispensador del cable (tripwire_trap)
UNA = "{Items:[{Slot:0b,count:16}]}"                                          # dispensador de las placas (plate_trap)
GUARDIAN = f"@e[type=minecraft:bogged,tag=heraldia_guardian.{SID}]"
MAX_LOCATE = 12000                                 # bloques: más lejos ya no es «una distancia razonable»


def at(p, sub=False):
    x, y, z = p
    base = GALERIAS if sub else JARDIN
    if sub:
        x, y, z = x - GALERIAS_MIN[0], y - GALERIAS_MIN[1], z - GALERIAS_MIN[2]
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
        # 1. generación natural
        t0 = time.monotonic()
        m = cmd(f"locate structure heraldia:unicas/{SID}",
                r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
        dt = time.monotonic() - t0
        if "Could not" in m.group(0):
            fails.append("locate")
            print(f"[FALLO] /locate no encuentra el laboratorio ({dt:.1f} s)")
        else:
            lx, lz, far = int(m.group(1)), int(m.group(2)), int(m.group(3))
            print(f"LOCATE desde 0, 0: laboratorio en {lx}, {lz}, a {far} bloques ({dt * 1000:.0f} ms)")
            if far > MAX_LOCATE:
                fails.append(f"locate a {far} bloques")
            sm.send(proc, f"forceload add {lx - 48} {lz - 48} {lx + 112} {lz + 112}")
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 600, seen)
            for _ in range(30):                     # los chunks forzados se cargan en los ticks siguientes
                mm = cmd(f"execute if biome {lx} 64 {lz} minecraft:mushroom_fields", r"Test passed|Test failed")
                if "not loaded" not in mm.group(0):
                    break
                time.sleep(2)
            ok = "passed" in mm.group(0)
            print(f"[{'OK' if ok else 'FALLO'}] el sitio de /locate es campo de champiñones")
            if not ok:
                fails.append("bioma del sitio de /locate")
            deadline, found = time.monotonic() + 120, False
            while time.monotonic() < deadline and not found:
                mm = cmd(f"execute if entity {GUARDIAN.replace(']', f',x={lx - 64},y=-64,z={lz - 64},dx=200,dy=400,dz=200]')}",
                         r"Test passed|Test failed")
                found = "passed" in mm.group(0)
                if not found:
                    time.sleep(3)
            print(f"[{'OK' if found else 'FALLO'}] generación natural: el guardián está en el laboratorio de {lx}, {lz}")
            if not found:
                fails.append("generación natural")
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
        print(f"TIEMPO de /place structure del Laboratorio del micólogo: {dt * 1000:.0f} ms")
        time.sleep(10)
        cerca = GUARDIAN.replace("]", ",x=0,y=0,z=0,distance=..200]")   # el del laboratorio natural sigue cargado
        m = check("guardián con su etiqueta", f"execute if entity {cerca}")
        print("  cuenta:", m.group(1))
        if m.group(1) != "1":
            fails.append("un solo guardián")
        check("el guardián es persistente", f"execute if entity {cerca.replace(']', ',nbt={PersistenceRequired:1b}]')}")
        check("el guardián lleva su sombrero de champiñón",
              f"execute if entity {cerca.replace(']', ',nbt={equipment:{head:{id:\"minecraft:red_mushroom_block\"}}}]')}")
        m = check("los champiñocas del corral",
                  "execute if entity @e[type=minecraft:mooshroom,x=0,y=0,z=0,distance=..120,nbt={PersistenceRequired:1b}]")
        print("  CHAMPIÑOCAS:", m.group(1))
        if m.group(1) != "3":
            fails.append("tres champiñocas")
        m = check("entidades de la estructura (guardián y champiñocas)",
                  "execute if entity @e[type=!minecraft:item,type=!minecraft:experience_orb,x=0,y=0,z=0,distance=..120,"
                  "nbt={PersistenceRequired:1b}]")
        print("  ENTIDADES:", m.group(1))
        # 3. plantillas sin girar
        for name, base in (("jardin", JARDIN), ("galerias", GALERIAS)):
            m = cmd(f"place template heraldia:unicas/{SID}/{name} {base[0]} {base[1]} {base[2]}",
                    r"Loaded template|Failed|not loaded|error|Could not")
            if "Loaded" not in m.group(0):
                fails.append("place template " + name)
        time.sleep(5)
        # el jardín
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
        # las galerías
        for p, mob in (((57, -5, 25), "spider"), ((13, -11, 21), "cave_spider"), ((52, -11, 21), "zombie")):
            check(f"generador de {mob}", f"execute if data block {at(p, True)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        has_loot("cofre premium", (25, -11, 59), True)
        has_loot("cofre de la cepa madre", (19, -11, 51), True)
        door = [(34, -11, 40), (34, -10, 40)]
        for p in door:
            is_block(f"puerta de los reactivos cerrada al generarse {p}", p, "minecraft:chiseled_stone_bricks", True)
        is_block("pistón de los reactivos extendido", (34, -10, 42), "minecraft:sticky_piston[extended=true]", True)
        # puzle 1: los reactivos (x 36 = frasco, x 37 = palanca; z 44 ojo de araña, 46 espora, 48 pólvora,
        # 50 verruga, 52 polvo de piedra luminosa). Solución: espora, verruga y luz.
        for z in (44, 46, 48, 50, 52):
            blocks_at[(36, -10, z)] = "minecraft:polished_andesite"
        lever((37, -10, 46), (36, -10, 46), "east", True)
        lever((37, -10, 50), (36, -10, 50), "east", True)
        time.sleep(2)
        is_block("con espora y verruga la puerta sigue cerrada", door[0], "minecraft:chiseled_stone_bricks", True)
        lever((37, -10, 52), (36, -10, 52), "east", True)
        time.sleep(3)
        for p in door:
            is_block(f"espora, verruga y luz abren la puerta {p}", p, "minecraft:air", True)
        lever((37, -10, 44), (36, -10, 44), "east", True)
        time.sleep(3)
        is_block("con el ojo de araña se vuelve a cerrar", door[0], "minecraft:chiseled_stone_bricks", True)
        lever((37, -10, 44), (36, -10, 44), "east", False)
        time.sleep(3)
        is_block("y al quitarlo se abre otra vez", door[0], "minecraft:air", True)
        # puzle 2: el panel de tallo del cepario
        sec = [(13, -5, 16), (13, -4, 16)]
        for p in sec:
            is_block(f"panel del cepario cerrado {p}", p, "minecraft:mushroom_stem", True)
        blocks_at[(16, -5, 17)] = "minecraft:stone_bricks"
        lever((16, -5, 18), (16, -5, 17), "south", True)
        time.sleep(3)
        for p in sec:
            is_block(f"la palanca abre el cepario {p}", p, "minecraft:air", True)
        # trampas
        check("dispensadores del cable trampa cargados", f"execute if data block {at((48, -4, 21), True)} {TRES}")
        x, y, z = (int(c) for c in at((48, -5, 22), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        time.sleep(3)
        check("el cable trampa dispara (norte)", f"execute if data block {at((48, -4, 21), True)} {TRES}", want=False)
        check("el cable trampa dispara (sur)", f"execute if data block {at((48, -4, 24), True)} {TRES}", want=False)
        check("dispensadores de las placas cargados", f"execute if data block {at((44, -11, 37), True)} {UNA}")
        x, y, z = (int(c) for c in at((44, -11, 38), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        time.sleep(3)
        check("la placa dispara (norte)", f"execute if data block {at((44, -11, 37), True)} {UNA}", want=False)
        check("la placa dispara (sur)", f"execute if data block {at((44, -11, 39), True)} {UNA}", want=False)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("PRUEBA LABORATORIO DEL MICÓLOGO " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
