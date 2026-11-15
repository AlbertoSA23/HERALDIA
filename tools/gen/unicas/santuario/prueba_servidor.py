"""Prueba en un servidor 26.3 real del Santuario druídico (complementa tools/smoke/server_smoke.py).

1. Coloca la estructura entera con /place structure, mide cuánto tarda y cuenta sus entidades tras unos segundos
   (solo el guardián: el archidruida Cadoc, un evocador).
2. Coloca las plantillas sin girar en sitios conocidos y comprueba cofres, generadores, agua y colmenas; acciona los
   mecanismos: la combinación de las piedras de las estaciones (con una piedra falsa se vuelve a cerrar), la estantería
   secreta del archivo, el cable trampa y las placas del nicho de las ofrendas.
   /setblock de una palanca no avisa al bloque al que está sujeta: se emula el clic cambiando ese bloque y devolviéndolo.
Uso (desde la raíz): python3 tools/gen/unicas/santuario/prueba_servidor.py --jar build/libs/heraldia-X.jar [--work DIR]
"""
import argparse, os, queue, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
import server_smoke as sm                      # noqa: E402

CLARO, RAICES = (3000, 100, 0), (3200, 100, 0)     # origen de cada plantilla colocada sin girar
RAICES_MIN = (12, -14, 4)                          # esquina mínima del subsuelo en coordenadas de la obra (obra.CRYPT)
TRES = "{Items:[{Slot:0b,count:16},{Slot:1b,count:16},{Slot:2b,count:16}]}"   # dispensador del cable (tripwire_trap)
UNA = "{Items:[{Slot:0b,count:16}]}"                                          # dispensador de las placas (plate_trap)
GUARDIAN = "@e[type=minecraft:evoker,tag=heraldia_guardian.santuario]"


def at(p, sub=False):
    x, y, z = p
    base = RAICES if sub else CLARO
    if sub:
        x, y, z = x - RAICES_MIN[0], y - RAICES_MIN[1], z - RAICES_MIN[2]
    return f"{base[0] + x} {base[1] + y} {base[2] + z}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_santuario"))
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
        for c in ("forceload add -96 -96 95 95", "forceload add 2990 -10 3080 80", "forceload add 3190 -10 3260 70"):
            sm.send(proc, c)
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 300, seen)
        # 1. estructura entera
        for _ in range(sm.PLACE_ATTEMPTS):
            t0 = time.monotonic()
            m = cmd("place structure heraldia:unicas/santuario 0 ~ 0", r"Generated structure|not loaded|Failed|error")
            dt = time.monotonic() - t0
            if "not loaded" not in m.group(0):
                break
            time.sleep(sm.PLACE_RETRY_S)
        if "Generated" not in m.group(0):
            fails.append("place structure")
        print(f"TIEMPO de /place structure del Santuario druídico: {dt * 1000:.0f} ms")
        time.sleep(10)
        m = check("guardián con su etiqueta", f"execute if entity {GUARDIAN}")
        print("  cuenta:", m.group(1))
        if m.group(1) != "1":
            fails.append("un solo guardián")
        m = check("un solo evocador en la zona (la plantilla solo trae al guardián)",
                  "execute if entity @e[type=minecraft:evoker,x=0,y=0,z=0,distance=..200]")
        print("  EVOCADORES:", m.group(1))
        check("el guardián es persistente", f"execute if entity {GUARDIAN.replace(']', ',nbt={PersistenceRequired:1b}]')}")
        # 2. plantillas sin girar
        for name, base in (("claro", CLARO), ("raices", RAICES)):
            m = cmd(f"place template heraldia:unicas/santuario/{name} {base[0]} {base[1]} {base[2]}",
                    r"Loaded template|Failed|not loaded|error|Could not")
            if "Loaded" not in m.group(0):
                fails.append("place template " + name)
        time.sleep(5)
        # el claro
        has_loot("cofre de la alcoba del archidruida", (61, 1, 21))
        is_block("tapiz ante el paso a la alcoba", (58, 3, 21), "minecraft:green_wall_banner")
        is_block("paso tras el tapiz abierto", (59, 1, 21), "minecraft:air")
        has_loot("cofre de la plataforma de la copa", (41, 19, 36))
        is_block("hojas de la copa persistentes", (36, 28, 40), "minecraft:birch_leaves[persistent=true]")
        is_block("colmena con miel", (22, 1, 55), "minecraft:beehive[honey_level=5]")
        is_block("agua de la acequia quieta en su sitio", (21, 0, 58), "minecraft:water[level=0]")
        is_block("bancal regado", (21, 0, 57), "minecraft:farmland[moisture=7]")
        is_block("estanque", (48, 1, 54), "minecraft:water[level=0]")
        is_block("el agua no se sale del estanque", (48, 2, 54), "minecraft:air")
        # las raíces
        for p, mob in (((32, -5, 21), "spider"), ((37, -5, 9), "zombie"), ((47, -11, 32), "skeleton")):
            check(f"generador de {mob}", f"execute if data block {at(p, True)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        has_loot("cofre premium", (29, -11, 64), True)
        has_loot("cofre de la biblioteca (pliego)", (25, -5, 30), True)
        door = [(37, -11, 48), (37, -10, 48)]
        for p in door:
            is_block(f"puerta del sol cerrada al generarse {p}", p, "minecraft:mossy_stone_bricks", True)
        is_block("pistón del sol extendido", (37, -10, 50), "minecraft:sticky_piston[extended=true]", True)
        # puzle 1: piedras de las estaciones (x 39 = piedra, x 40 = palanca; z 52 primavera, 54 verano, 56 otoño,
        # 58 invierno). Solución: verano e invierno.
        for z in (52, 54, 56, 58):
            blocks_at[(39, -10, z)] = "minecraft:chiseled_stone_bricks"
        lever((40, -10, 54), (39, -10, 54), "east", True)
        time.sleep(2)
        is_block("solo con el verano la puerta sigue cerrada", door[0], "minecraft:mossy_stone_bricks", True)
        lever((40, -10, 58), (39, -10, 58), "east", True)
        time.sleep(3)
        for p in door:
            is_block(f"verano e invierno abren la puerta {p}", p, "minecraft:air", True)
        lever((40, -10, 52), (39, -10, 52), "east", True)
        time.sleep(3)
        is_block("con la primavera encendida se vuelve a cerrar", door[0], "minecraft:mossy_stone_bricks", True)
        lever((40, -10, 52), (39, -10, 52), "east", False)
        time.sleep(3)
        is_block("y al apagarla se abre otra vez", door[0], "minecraft:air", True)
        # puzle 2: estantería secreta del archivo
        sec = [(20, -5, 18), (20, -4, 18)]
        for p in sec:
            is_block(f"estantería del archivo cerrada {p}", p, "minecraft:bookshelf", True)
        blocks_at[(23, -5, 19)] = "minecraft:birch_planks"
        lever((23, -5, 20), (23, -5, 19), "south", True)
        time.sleep(3)
        for p in sec:
            is_block(f"la palanca abre el archivo {p}", p, "minecraft:air", True)
        # trampas
        check("dispensadores del cable trampa cargados", f"execute if data block {at((35, -4, 16), True)} {TRES}")
        x, y, z = (int(c) for c in at((36, -5, 16), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        time.sleep(3)
        check("el cable trampa dispara (oeste)", f"execute if data block {at((35, -4, 16), True)} {TRES}", want=False)
        check("el cable trampa dispara (este)", f"execute if data block {at((38, -4, 16), True)} {TRES}", want=False)
        check("dispensadores de las placas cargados", f"execute if data block {at((55, -11, 34), True)} {UNA}")
        x, y, z = (int(c) for c in at((55, -11, 35), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        time.sleep(3)
        check("la placa dispara (norte)", f"execute if data block {at((55, -11, 34), True)} {UNA}", want=False)
        check("la placa dispara (sur)", f"execute if data block {at((55, -11, 36), True)} {UNA}", want=False)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("PRUEBA SANTUARIO DRUÍDICO " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
