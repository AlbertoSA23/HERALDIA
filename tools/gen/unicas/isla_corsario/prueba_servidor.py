"""Prueba en un servidor 26.3 real de la Isla del corsario (complementa tools/smoke/server_smoke.py).

1. Generación natural: /locate desde el 0,0 (la candidata de cada casilla se busca en los océanos templados y cálidos,
   GridPlacement con «bioma»; el tipo heraldia:isla exige mar abierto con el fondo a profundidad media), mide la
   distancia y el tiempo, carga esos chunks y comprueba que el sitio es uno de sus océanos, que la estructura se ha
   generado de verdad (el corsario está en la cámara del tesoro, bajo el nivel del mar y en seco), que queda lejos de
   la Atlántida (fuera de su zona de exclusión) y que ningún naufragio ni ruina oceánica nace dentro de ella (IslaZona).
2. Coloca la estructura entera con /place structure, mide cuánto tarda y cuenta sus entidades (el corsario y la barca
   de la ensenada).
3. Coloca la plantilla sin girar en un sitio conocido y comprueba cofres, generadores, agua de la ensenada y salas
   secas; acciona los mecanismos: la rosa de los vientos (norte y poniente abren; con levante se vuelve a cerrar), la
   santabárbara secreta, el cable trampa y las placas de la antecámara.
   /setblock de una palanca no avisa al bloque al que está sujeta: se emula el clic cambiando ese bloque y devolviéndolo.
Uso (desde la raíz): python3 tools/gen/unicas/isla_corsario/prueba_servidor.py --jar build/libs/heraldia-X.jar [--work DIR]
"""
import argparse, math, os, subprocess, sys, threading, queue, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import server_smoke as sm                      # noqa: E402

SID = "isla_corsario"
ORIGEN = (3000, 45, 0)                         # esquina mínima de la plantilla colocada sin girar
TRES = "{Items:[{Slot:0b,count:6},{Slot:1b,count:6},{Slot:2b,count:6}]}"     # dispensador del cable (tripwire_trap)
UNA = "{Items:[{Slot:0b,count:16}]}"                                          # dispensador de las placas (plate_trap)
GUARDIAN = f"@e[type=minecraft:skeleton,tag=heraldia_guardian.{SID}]"
OCEANOS = ("ocean", "lukewarm_ocean", "warm_ocean")
MAX_LOCATE = 12000
ATLANTIDA_EXCLUSION = 444 + 60                 # radio de exclusión de la Atlántida (AtlantisAnchor) + media isla
ISLA_RADIO = 70                                # el islote y el bergantín, desde el centro (IslaZona excluye 7 chunks)
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_isla"))
    a = ap.parse_args()
    import unicas.isla_corsario as M           # coordenadas de la obra (se calculan como al generar)
    from core import parse_state
    t, _, _, rep = M.datos()
    obra, (sx, sy, sz) = rep["obra"], rep["desplazamiento"]
    m = obra.mech

    def at(p):
        return f"{ORIGEN[0] + p[0] - sx} {ORIGEN[1] + p[1] - sy} {ORIGEN[2] + p[2] - sz}"

    def tpl(p):
        return t.get(p[0] - sx, p[1] - sy, p[2] - sz)

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

    def check(desc, c, want=True, quiet=False):
        mm = cmd(c, r"Test passed(?:\. Count: (\d+))?|Test failed")
        ok = ("passed" in mm.group(0)) == want
        if not quiet:
            print(f"[{'OK' if ok else 'FALLO'}] {desc}")
            if not ok:
                fails.append(desc)
        return ok, mm

    def until(desc, c, want=True, secs=20):
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
        """Acciona una palanca como un jugador: la cambia y «toca» el bloque al que está sujeta."""
        st = tpl(lp)
        b, props = parse_state(st)
        dx, dz = DV[props["facing"]]
        bp = (lp[0] - dx, lp[1], lp[2] - dz)
        cmd(f"setblock {at(lp)} minecraft:lever[face=wall,facing={props['facing']},powered={str(on).lower()}]")
        cmd(f"setblock {at(bp)} minecraft:bedrock")
        cmd(f"setblock {at(bp)} {tpl(bp)}")

    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        # 1. generación natural
        t0 = time.monotonic()
        mm = cmd(f"locate structure heraldia:unicas/{SID}",
                 r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
        dt = time.monotonic() - t0
        if "Could not" in mm.group(0):
            fails.append("locate")
            print(f"[FALLO] /locate no encuentra la isla ({dt:.1f} s)")
        else:
            lx, lz, far = int(mm.group(1)), int(mm.group(2)), int(mm.group(3))
            print(f"LOCATE desde 0, 0: isla del corsario en {lx}, {lz}, a {far} bloques ({dt * 1000:.0f} ms)")
            if far > MAX_LOCATE:
                fails.append(f"locate a {far} bloques")
            ma = cmd("locate structure heraldia:unicas/atlantida",
                     r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
            if "Could not" not in ma.group(0):
                d = math.hypot(int(ma.group(1)) - lx, int(ma.group(2)) - lz)
                ok = d > ATLANTIDA_EXCLUSION
                print(f"[{'OK' if ok else 'FALLO'}] la isla queda fuera de la Atlántida ({d:.0f} bloques de su centro)")
                if not ok:
                    fails.append("isla dentro de la Atlántida")
            for tag in ("shipwreck", "ocean_ruin"):   # IslaZona: nada ajeno dentro de la isla (igual en /locate)
                mm = cmd(f"execute positioned {lx} 64 {lz} run locate structure #minecraft:{tag}",
                         r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
                d = 10 ** 9 if "Could not" in mm.group(0) else int(mm.group(3))
                ok = d > ISLA_RADIO
                print(f"[{'OK' if ok else 'FALLO'}] ningún {tag} dentro de la isla (el más cercano a {d} bloques)")
                if not ok:
                    fails.append(f"{tag} dentro de la isla")
            sm.send(proc, f"forceload add {lx - 80} {lz - 80} {lx + 80} {lz + 80}")
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 600, seen)
            for _ in range(30):                     # los chunks forzados se cargan en los ticks siguientes
                mm = cmd(f"execute if biome {lx} 62 {lz} minecraft:{OCEANOS[0]}", r"Test passed|Test failed")
                if "not loaded" not in mm.group(0):
                    break
                time.sleep(2)
            ok = any(check("", f"execute if biome {lx} 62 {lz} minecraft:{b}", quiet=True)[0] for b in OCEANOS)
            print(f"[{'OK' if ok else 'FALLO'}] el sitio de /locate es océano templado o cálido")
            if not ok:
                fails.append("bioma del sitio de /locate")
            sel = GUARDIAN.replace("]", f",x={lx - 80},y=0,z={lz - 80},dx=160,dy=120,dz=160]")
            deadline, found = time.monotonic() + 120, False
            while time.monotonic() < deadline and not found:
                found = check("", f"execute if entity {sel}", quiet=True)[0]
                if not found:
                    time.sleep(3)
            print(f"[{'OK' if found else 'FALLO'}] generación natural: el corsario está en la isla de {lx}, {lz}")
            if not found:
                fails.append("generación natural")
            else:
                time.sleep(20)                      # si el mar entrase en la cámara del tesoro, ya habría entrado
                # «execute as <nadie> ...» no responde nada en la consola (la espera se agotaría): antes, que siga ahí
                if not check("el corsario sigue en la isla tras 20 s", f"execute if entity {sel}")[0]:
                    for q in (f"execute if entity {GUARDIAN}", f"data get entity {GUARDIAN.replace(']', ',limit=1]')} Pos",
                              f"data get entity {GUARDIAN.replace(']', ',limit=1]')} Health"):
                        print("  DIAG", q, "->", cmd(q, r"Test passed(?:\. Count: \d+)?|Test failed|has the following|"
                                                       r"No entity").group(0))
                else:
                    check("la cámara del tesoro sigue seca y bajo el nivel del mar",
                          f"execute as {sel} at @s if block ~ ~ ~ minecraft:air if block ~ ~1 ~ minecraft:air "
                          f"if entity @s[y=0,dy=62]")
            for line in seen:
                if "isla del corsario en" in line or "búsqueda del bioma" in line:
                    print("  ", line.split("]: ", 1)[-1])
        for c in ("forceload add -96 -96 95 95", f"forceload add {ORIGEN[0] - 8} -8 {ORIGEN[0] + 120} 120"):
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
        print(f"TIEMPO de /place structure de la Isla del corsario: {dt * 1000:.0f} ms")
        time.sleep(10)
        cerca = GUARDIAN.replace("]", ",x=0,y=0,z=0,distance=..120]")
        ok, mm = check("corsario con su etiqueta", f"execute if entity {cerca}")
        print("  cuenta:", mm.group(1))
        if mm.group(1) != "1":
            fails.append("un solo guardián")
        check("el corsario es persistente", f"execute if entity {cerca.replace(']', ',nbt={PersistenceRequired:1b}]')}")
        check("el corsario lleva su arco",
              f"execute if entity {cerca.replace(']', ',nbt={equipment:{mainhand:{id:\"minecraft:bow\"}}}]')}")
        ok, mm = check("la barca de la ensenada", "execute if entity @e[type=minecraft:oak_boat,x=0,y=0,z=0,distance=..120]")
        print("  BARCAS:", mm.group(1))
        ok, mm = check("entidades de la estructura (sin objetos sueltos)",
                       "execute if entity @e[type=!minecraft:item,type=!minecraft:experience_orb,type=!minecraft:arrow,"
                       "x=0,y=0,z=0,distance=..120]")
        print("  ENTIDADES:", mm.group(1))
        # 3. plantilla sin girar
        mm = cmd(f"place template heraldia:unicas/{SID}/isla {ORIGEN[0]} {ORIGEN[1]} {ORIGEN[2]}",
                 r"Loaded template|Failed|not loaded|error|Could not")
        if "Loaded" not in mm.group(0):
            fails.append("place template")
        time.sleep(5)
        for p, tabla in obra.chests:
            if tabla in ("premium", "cartas", "escondite", "santabarbara", "bergantin", "ensenada", "polvorin"):
                has_loot(f"cofre {tabla}", p)
        print(f"  {len(obra.chests)} cofres en la obra")
        for p, mob in obra.spawners:
            check(f"generador de {mob}", f"execute if data block {at(p)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        for p in m["canones"]:
            is_block(f"cañón {p}", p, "minecraft:dispenser")
        bx0, bx1 = m["ensenada"]["boca"]
        lx0, lx1, lz0, lz1 = m["ensenada"]["laguna"]
        time.sleep(10)
        is_block("agua quieta en la ensenada", (lx0 + 5, -1, lz0 + 2), "minecraft:water[level=0]")
        is_block("aire seco sobre la ensenada", (lx0 + 5, 0, lz0 + 2), "minecraft:air")
        is_block("el muelle de la ensenada sin agua", (lx0, 0, lz1 - 1), "minecraft:air")
        is_block("tarima del muelle del puerto", (44, 0, 85), "minecraft:spruce_planks")
        # puzle 1: la rosa de los vientos (norte y poniente; levante y sur son falsas)
        door = m["puerta_rosa"]
        n, e, s, w = m["palancas"]
        for p in door:
            is_block(f"puerta del tesoro cerrada al generarse {p}", p, "minecraft:chiseled_stone_bricks")
        lever(n, True)
        time.sleep(2)
        is_block("solo con el norte sigue cerrada", door[0], "minecraft:chiseled_stone_bricks")
        lever(w, True)
        time.sleep(1)
        for p in door:
            until(f"norte y poniente abren la puerta del tesoro {p}", f"execute if block {at(p)} minecraft:air")
        lever(e, True)
        until("con levante se vuelve a cerrar", f"execute if block {at(door[0])} minecraft:chiseled_stone_bricks")
        lever(e, False)
        until("y al bajarla se abre otra vez", f"execute if block {at(door[0])} minecraft:air")
        # puzle 2: la santabárbara
        sb = m["santabarbara"]
        sec = [sb["door"], (sb["door"][0], sb["door"][1] + 1, sb["door"][2])]
        for p in sec:
            is_block(f"santabárbara cerrada {p}", p, "minecraft:stone_bricks")
        lever(sb["lever"], True)
        for p in sec:
            until(f"la palanca del armero abre la santabárbara {p}", f"execute if block {at(p)} minecraft:air")
        # trampas
        d1, d2 = m["dispensadores_cable"]
        check("dispensadores del cable trampa cargados", f"execute if data block {at(d1)} {TRES}")
        x, y, z = (int(c) for c in at(m["cable"][0]).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        until("el cable trampa dispara (norte)", f"execute if data block {at(d1)} {TRES}", want=False)
        until("el cable trampa dispara (sur)", f"execute if data block {at(d2)} {TRES}", want=False)
        f1 = m["flechas"][0]
        check("dispensadores de las placas cargados", f"execute if data block {at(f1)} {UNA}")
        x, y, z = (int(c) for c in at(m["placas"][0]).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        until("la placa dispara", f"execute if data block {at(f1)} {UNA}", want=False)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("PRUEBA ISLA DEL CORSARIO " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
