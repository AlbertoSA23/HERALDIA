"""Prueba en un servidor 26.3 real del Salón del Jarl (complementa tools/smoke/server_smoke.py).

1. Coloca la estructura entera con /place structure, mide cuánto tarda y cuenta sus entidades (guardián, guerreros de
   piedra) tras unos segundos, y comprueba que el túmulo está bajo la casa larga (generadores, cofres, guardián).
2. Coloca las plantillas sin girar en sitios conocidos y acciona los mecanismos: la combinación de las runas (con una
   runa falsa se vuelve a cerrar), la puerta secreta del escaldo, el cable trampa y la placa de la dinamita.
   /setblock de una palanca no avisa al bloque al que está sujeta: se emula el clic cambiando ese bloque y devolviéndolo.
Uso (desde la raíz): python3 tools/gen/unicas/salon_jarl/prueba_servidor.py --jar build/libs/heraldia-X.jar [--work DIR]
"""
import argparse, os, queue, re, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
import server_smoke as sm                      # noqa: E402

SALON, TUM = (2000, 100, 0), (2200, 100, 0)       # origen de cada plantilla colocada sin girar
TUM_MIN = (14, -15, 30)                           # esquina mínima del túmulo en coordenadas de la obra (obra.CRYPT)
ARROWS = "{Items:[{Slot:0b,count:16},{Slot:1b,count:16},{Slot:2b,count:16}]}"


def at(base, p, crypt=False):
    x, y, z = p
    if crypt:
        x, y, z = x - TUM_MIN[0], y - TUM_MIN[1], z - TUM_MIN[2]
    return f"{base[0] + x} {base[1] + y} {base[2] + z}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_salon_jarl"))
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

    def lever(base, lp, bp, facing, on, crypt=True):
        cmd(f"setblock {at(base, lp, crypt)} minecraft:lever[face=wall,facing={facing},powered={str(on).lower()}]")
        cmd(f"setblock {at(base, bp, crypt)} minecraft:bedrock")
        cmd(f"setblock {at(base, bp, crypt)} {blocks_at[bp]}")

    blocks_at = {}

    def diagnostico_trampa():
        """Qué hay junto al cable trampa cuando sus dispensadores ya han disparado (fallo intermitente, ver APRENDIZAJES)."""
        x, y, z = (int(c) for c in at(TUM, (55, -6, 58), True).split())
        for d in ((54, -5, 58), (57, -5, 58)):
            cmd(f"data get block {at(TUM, d, True)} Items", r"has the following block data|not a block entity|Items")
        cmd(f"execute if entity @e[type=!minecraft:player,x={x},y={y},z={z},distance=..24]")
        for _ in range(6):
            m = cmd(f"data get entity @e[type=!minecraft:player,x={x},y={y},z={z},distance=..24,limit=1,sort=nearest]",
                    r"has the following entity data|No entity was found")
            if "No entity" in m.group(0):
                break
            print("DIAG trampa:", [l for l in seen[-3:]])
            cmd(f"kill @e[type=!minecraft:player,x={x},y={y},z={z},distance=..24,limit=1,sort=nearest]", r"Killed|No entity")
    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        for c in ("forceload add -96 -96 95 95", "forceload add 1990 -10 2080 80", "forceload add 2190 -10 2260 60"):
            sm.send(proc, c)
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 300, seen)
        # 1. estructura entera
        for _ in range(sm.PLACE_ATTEMPTS):
            t0 = time.monotonic()
            m = cmd("place structure heraldia:unicas/salon_jarl 0 ~ 0", r"Generated structure|not loaded|Failed|error")
            dt = time.monotonic() - t0
            if "not loaded" not in m.group(0):
                break
            time.sleep(sm.PLACE_RETRY_S)
        if "Generated" not in m.group(0):
            fails.append("place structure")
        print(f"TIEMPO de /place structure del Salón del Jarl: {dt * 1000:.0f} ms")
        ctx.wait_entity("@e[type=minecraft:zombie,tag=heraldia_guardian.salon_jarl]")   # aparecen tras los bloques
        ctx.wait_entity("@e[type=minecraft:armor_stand,distance=..120,x=0,y=0,z=0]")
        for desc, sel in (("guardián con su etiqueta", "@e[type=minecraft:zombie,tag=heraldia_guardian.salon_jarl]"),
                          ("dos guerreros de piedra (soportes de armadura)", "@e[type=minecraft:armor_stand,distance=..120,x=0,y=0,z=0]")):
            m = check(desc, f"execute if entity {sel}")
            print("  cuenta:", m.group(1))
        check("el guardián lleva su hacha",
              "execute if entity @e[type=minecraft:zombie,tag=heraldia_guardian.salon_jarl,nbt={equipment:{mainhand:{id:\"minecraft:iron_axe\"}}}]")
        check("el guardián es adulto", "execute if entity @e[type=minecraft:zombie,tag=heraldia_guardian.salon_jarl,nbt={IsBaby:0b}]")
        # 2. plantillas sin girar
        for name, base in (("salon", SALON), ("tumulo", TUM)):
            m = cmd(f"place template heraldia:unicas/salon_jarl/{name} {base[0]} {base[1]} {base[2]}",
                    r"Loaded template|Failed|not loaded|error|Could not")
            if "Loaded" not in m.group(0):
                fails.append("place template " + name)
        ctx.ticks(60)
        check("cofre de la alcoba del jarl", f"execute if data block {at(SALON, (40, 2, 62))} LootTable")
        check("tapiz ante el paso a la alcoba", f"execute if block {at(SALON, (34, 4, 57))} minecraft:black_wall_banner")
        check("paso tras el tapiz abierto", f"execute if block {at(SALON, (34, 2, 58))} minecraft:air")
        for p, mob in (((49, -6, 50), "zombie"), ((55, -6, 37), "skeleton"), ((57, -6, 50), "spider")):
            check(f"generador de {mob}", f"execute if data block {at(TUM, p, True)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        check("cofre premium", f"execute if data block {at(TUM, (19, -12, 46), True)} LootTable")
        check("cofre de las ofrendas (pliego)", f"execute if data block {at(TUM, (59, -6, 68), True)} LootTable")
        door = [(31, -6, 59), (31, -5, 59)]
        for p in door:
            check(f"puerta de las runas cerrada al generarse {p}", f"execute if block {at(TUM, p, True)} minecraft:polished_tuff")
        check("pistón de las runas extendido", f"execute if block {at(TUM, (31, -5, 61), True)} minecraft:sticky_piston[extended=true]")
        # puzle 1: runas (x 33 = piedra rúnica, x 34 = palanca; z 63 serpiente, 65 cuervo, 67 oso, 69 lobo)
        for z in (63, 65, 67, 69):
            blocks_at[(33, -5, z)] = "minecraft:chiseled_tuff"
        lever(TUM, (34, -5, 65), (33, -5, 65), "east", True)
        ctx.ticks(40)
        check("solo con el cuervo la puerta sigue cerrada", f"execute if block {at(TUM, door[0], True)} minecraft:polished_tuff")
        lever(TUM, (34, -5, 69), (33, -5, 69), "east", True)
        ctx.ticks(60)
        for p in door:
            check(f"cuervo y lobo abren la puerta {p}", f"execute if block {at(TUM, p, True)} minecraft:air")
        lever(TUM, (34, -5, 63), (33, -5, 63), "east", True)
        ctx.ticks(60)
        check("con la serpiente despierta se vuelve a cerrar", f"execute if block {at(TUM, door[0], True)} minecraft:polished_tuff")
        lever(TUM, (34, -5, 63), (33, -5, 63), "east", False)
        ctx.ticks(60)
        check("y al dormirla se abre otra vez", f"execute if block {at(TUM, door[0], True)} minecraft:air")
        # puzle 2: puerta secreta del escaldo
        sec = [(41, -6, 46), (41, -5, 46)]
        for p in sec:
            check(f"puerta del escaldo cerrada {p}", f"execute if block {at(TUM, p, True)} minecraft:chiseled_stone_bricks")
        blocks_at[(44, -6, 47)] = "minecraft:cobblestone"
        lever(TUM, (44, -6, 48), (44, -6, 47), "south", True)
        ctx.ticks(60)
        for p in sec:
            check(f"la palanca abre la puerta del escaldo {p}", f"execute if block {at(TUM, p, True)} minecraft:air")
        # trampas
        m = check("dispensadores del cable trampa cargados", f"execute if data block {at(TUM, (54, -5, 58), True)} {ARROWS}")
        if "failed" in m.group(0):
            diagnostico_trampa()
        x, y, z = (int(c) for c in at(TUM, (55, -6, 58), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        ctx.ticks(60)
        check("el cable trampa dispara (oeste)", f"execute if data block {at(TUM, (54, -5, 58), True)} {ARROWS}", want=False)
        check("el cable trampa dispara (este)", f"execute if data block {at(TUM, (57, -5, 58), True)} {ARROWS}", want=False)
        check("dinamita bajo la placa", f"execute if block {at(TUM, (50, -8, 65), True)} minecraft:tnt")
        x, y, z = (int(c) for c in at(TUM, (50, -6, 65), True).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        ctx.ticks(40)
        check("la placa ceba la dinamita", f"execute if block {at(TUM, (50, -8, 65), True)} minecraft:tnt", want=False)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("PRUEBA SALÓN DEL JARL " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
