"""Prueba en un servidor 26.3 real de la Mina perdida (complementa tools/smoke/server_smoke.py).

1. Generación natural: /locate desde el 0,0 (la candidata de cada casilla se busca en las cuevas exuberantes o de
   espeleotemas a la altura de la caverna, GridPlacement con «bioma» y «bioma_y»), mide la distancia y el tiempo, carga
   esos chunks y comprueba que la estructura se ha generado de verdad (su guardián está allí, en su bioma de cueva y a la
   altura de la caverna) y que el castillete asoma en la superficie (la cadena del pozo sube hasta el aire libre).
2. Coloca la estructura entera con /place structure, mide cuánto tarda y cuenta sus entidades (Tizón, la vagoneta del
   cargadero y la barca del embarcadero).
3. Coloca las plantillas sin girar en sitios conocidos y comprueba cofres, generadores, agua y vías; acciona el puzle de
   las agujas con la vagoneta de verdad (solo «aguja 1 al norte, aguja 2 al este» la lleva a la báscula y abre la
   compuerta; las otras combinaciones la dejan en la escombrera o en la vía muerta), el despacho secreto del capataz y
   las dos trampas (cable trampa y placa sobre la dinamita).
   /setblock de una palanca no avisa al bloque al que está sujeta: se emula el clic cambiando ese bloque y devolviéndolo.
Uso (desde la raíz): python3 tools/gen/unicas/mina_perdida/prueba_servidor.py --jar build/libs/heraldia-X.jar [--work DIR]
"""
import argparse, math, os, subprocess, sys, threading, queue, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "smoke"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import server_smoke as sm                      # noqa: E402

SID = "mina_perdida"
COLONIA, CASTILLETE = (3000, 40, 0), (3200, 100, 0)   # origen (esquina mínima) de cada plantilla colocada sin girar
GUARDIAN = f"@e[type=minecraft:vindicator,tag=heraldia_guardian.{SID}]"
MAX_LOCATE = 12000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(sm.ROOT, "build", "smoke_mina"))
    a = ap.parse_args()
    import unicas.mina_perdida as M            # coordenadas de la obra (se calculan como al generar)
    from unicas.mina_perdida import vias
    tpls, meta, _, _, rep = M.datos()
    obra, cast = rep["obra"], rep["castillete"]
    sx, sy, sz = rep["desplazamiento"]
    cx0, cy0, cz0 = rep["desplazamiento_castillete"]
    m, v = obra.mech, obra.mech["vias"]

    def at(p):
        return f"{COLONIA[0] + p[0] - sx} {COLONIA[1] + p[1] - sy} {COLONIA[2] + p[2] - sz}"

    def at_c(p):
        return f"{CASTILLETE[0] + p[0] - cx0} {CASTILLETE[1] + p[1] - cy0} {CASTILLETE[2] + p[2] - cz0}"

    os.makedirs(a.work, exist_ok=True)
    launcher = sm.prepare(a.work, os.path.abspath(a.jar), sm.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=sm.reader, args=(proc, lines), daemon=True).start()
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

    def until(desc, c, want=True, secs=20):
        """Repite la comprobación hasta que se cumpla (o se acabe el tiempo): las vagonetas y los pistones tardan."""
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

    def toque(p, st):
        cmd(f"setblock {at(p)} minecraft:bedrock")
        cmd(f"setblock {at(p)} {st}")

    def palanca(p, on, cara="floor", facing="east"):
        cmd(f"setblock {at(p)} minecraft:lever[face={cara},facing={facing},powered={str(on).lower()}]")

    def lanzar(combo):
        """Vagoneta nueva en la salida, agujas según combo y arranque."""
        cmd(f"kill @e[type=minecraft:minecart,x={COLONIA[0]},y={COLONIA[1] - 30},z={COLONIA[2]},dx=120,dy=80,dz=90]")
        for lp, on in zip(v["palancas"], combo):
            palanca(lp, on)
        palanca(v["arranque"], False)
        time.sleep(1)
        x, y, z = (int(c) for c in at(v["salida"]).split())
        cmd(f"summon minecraft:minecart {x + 0.5} {y + 0.1} {z + 0.5}")
        time.sleep(1)
        palanca(v["arranque"], True)

    def carro_en(p, r=1):
        x, y, z = (int(c) for c in at(p).split())
        return f"execute if entity @e[type=minecraft:minecart,x={x - r},y={y - 1},z={z - r},dx={2 * r},dy=2,dz={2 * r}]"

    def pozo_ok(x, z):
        """Busca en el registro la línea del eje del pozo de la mina más cercana a (x, z) y comprueba la cadena del pozo
        de la colonia al castillete y el aire libre sobre él."""
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
            print("[FALLO] no se encuentra en el registro el eje del pozo")
            fails.append("eje del pozo")
            return
        _, ax, az, y0, y1, suelo, largo = best
        print(f"  POZO en {ax}, {az}: {largo} bloques (y {y0}-{y1}), castillete a y = {suelo}")
        for yy in (y0 - 3, (y0 + y1) // 2, y1, suelo + 5):
            check(f"cadena del pozo en y = {yy}", f"execute if block {ax} {yy} {az} minecraft:iron_chain")
        check("la cubeta en el fondo del pozo", f"execute if block {ax} {y0 - M.YTOP} {az} minecraft:cauldron")
        check("aire libre sobre el castillete", f"execute if block {ax} {suelo + 12} {az} minecraft:air")
        check("la viga maestra del castillete", f"execute if block {ax} {suelo + 10} {az} minecraft:spruce_log")

    try:
        sm.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", sm.START_TIMEOUT_S, seen)
        for line in seen:
            if "rejilla unicas/mina_perdida" in line:
                print("  ", line.split("]: ", 1)[-1].strip())
        # 1. generación natural
        t0 = time.monotonic()
        mm = cmd(f"locate structure heraldia:unicas/{SID}",
                 r"The nearest .* is at \[(-?\d+), [^,]+, (-?\d+)\] \((\d+) blocks away\)|Could not find")
        dt = time.monotonic() - t0
        if "Could not" in mm.group(0):
            fails.append("locate")
            print(f"[FALLO] /locate no encuentra la mina ({dt:.1f} s)")
        else:
            lx, lz, far = int(mm.group(1)), int(mm.group(2)), int(mm.group(3))
            print(f"LOCATE desde 0, 0: mina en {lx}, {lz}, a {far} bloques ({dt * 1000:.0f} ms)")
            if far > MAX_LOCATE:
                fails.append(f"locate a {far} bloques")
            t0 = time.monotonic()
            sm.send(proc, f"forceload add {lx - 104} {lz - 104} {lx + 103} {lz + 103}")
            sm.wait_for(lines, r"Marked|Added|chunks? .*force", 600, seen)
            caja = f"x={lx - 104},y=-64,z={lz - 104},dx=208,dy=400,dz=208"
            deadline, found = time.monotonic() + 240, False
            while time.monotonic() < deadline and not found:
                found, _ = check("guardián", f"execute if entity {GUARDIAN.replace(']', ',' + caja + ']')}", quiet=True)
                if not found:
                    time.sleep(3)
            print(f"[{'OK' if found else 'FALLO'}] generación natural: el guardián está en la mina de {lx}, {lz} "
                  f"({time.monotonic() - t0:.0f} s en cargar)")
            if not found:
                fails.append("generación natural")
            else:
                g = GUARDIAN.replace("]", "," + caja + "]")
                # sin «execute as/at <selector>»: bifurcan la orden y un «Test failed» en una rama no responde nada
                pm = cmd(f"data get entity {g.replace(']', ',limit=1]')} Pos",
                         r"has the following entity data: \[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]")
                gx, gy, gz = (math.floor(float(v)) for v in pm.groups())
                ok = 0 <= gy <= 20
                print(f"[{'OK' if ok else 'FALLO'}] el guardián está a la altura del filón madre (y 0-20: {gy})")
                if not ok:
                    fails.append("guardián a la altura del filón madre")
                check("la caverna está en las cuevas exuberantes o de espeleotemas",
                      f"execute if biome {gx} {gy + 16} {gz} #heraldia:unicas/{SID}")
                pozo_ok(lx, lz)
                for line in seen:
                    if "búsqueda del bioma" in line and SID in line:
                        print("  ", line.split("]: ", 1)[-1].strip())
            sm.send(proc, f"forceload remove {lx - 104} {lz - 104} {lx + 103} {lz + 103}")
            sm.wait_for(lines, r"Unmarked|Removed|chunks? .*force|No chunks", 120, seen)
        for c in ("forceload add -96 -96 95 95", f"forceload add {COLONIA[0] - 8} -8 {COLONIA[0] + 120} 90",
                  f"forceload add {CASTILLETE[0] - 4} -4 {CASTILLETE[0] + 20} 16"):
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
        print(f"TIEMPO de /place structure de la Mina perdida: {dt * 1000:.0f} ms")
        time.sleep(10)
        pozo_ok(0, 0)
        cerca = GUARDIAN.replace("]", ",x=0,y=0,z=0,distance=..200]")
        until("guardián con su etiqueta", f"execute if entity {cerca}")
        _, mm = check("un solo guardián", f"execute if entity {cerca}")
        print("  cuenta:", mm.group(1))
        if mm.group(1) != "1":
            fails.append("un solo guardián")
        check("el guardián es persistente", f"execute if entity {cerca.replace(']', ',nbt={PersistenceRequired:1b}]')}")
        check("el guardián lleva su casco de minero",
              f"execute if entity {cerca.replace(']', ',nbt={equipment:{head:{id:\"minecraft:iron_helmet\"}}}]')}")
        _, mm = check("la vagoneta del cargadero", "execute if entity @e[type=minecraft:minecart,x=0,y=0,z=0,distance=..200]")
        print("  VAGONETAS:", mm.group(1))
        _, mm = check("la barca del embarcadero", "execute if entity @e[type=minecraft:oak_boat,x=0,y=0,z=0,distance=..200]")
        print("  BARCAS:", mm.group(1))
        _, mm = check("entidades de la estructura",
                      "execute if entity @e[type=!minecraft:item,type=!minecraft:experience_orb,type=!minecraft:player,"
                      "x=0,y=0,z=0,distance=..200]")
        print("  ENTIDADES:", mm.group(1))
        # 3. plantillas sin girar
        for name, base in (("colonia", COLONIA), ("castillete", CASTILLETE)):
            mm = cmd(f"place template heraldia:unicas/{SID}/{name} {base[0]} {base[1]} {base[2]}",
                     r"Loaded template|Failed|not loaded|error|Could not")
            if "Loaded" not in mm.group(0):
                fails.append("place template " + name)
        time.sleep(5)
        # cofres, generadores, agua
        for p, tabla in obra.chests:
            check(f"cofre {tabla}", f"execute if data block {at(p)} LootTable", quiet=False) if tabla in (
                "premium", "despacho", "inundada", "alijo", "sima") else None
        for p, tabla in cast.chests:
            check(f"cofre {tabla} del castillete", f"execute if data block {at_c(p)} LootTable")
        check("la escalera del pozo en el castillete", f"execute if block {at_c((-1, 0, 0))} minecraft:ladder")
        for p, mob in obra.spawners:
            check(f"generador de {mob}", f"execute if data block {at(p)} SpawnData.entity{{id:\"minecraft:{mob}\"}}")
        is_block("agua del lago", (44, -2, 50), "minecraft:water")
        is_block("cofre anegado del sector inundado", [p for p, t in obra.chests if t == "inundada"][0],
                 "minecraft:chest[waterlogged=true]")
        is_block("aire seco en la caverna junto al lago", (44, 1, 50), "minecraft:air")
        # puzle 1: las agujas con la vagoneta de verdad
        puerta = v["puerta"]
        for p in puerta:
            is_block(f"compuerta cerrada al generarse {p}", p, "minecraft:air", want=False)
        until("la vagoneta de la plantilla espera en la salida", carro_en(v["salida"]))
        a1, a2 = v["agujas"]
        is_block("aguja 1 sin señal: hacia la escombrera", a1, "minecraft:rail[shape=south_east]")
        is_block("aguja 2 sin señal: hacia la báscula", a2, "minecraft:rail[shape=south_east]")
        lanzar((False, False))
        until("sin tocar las agujas la vagoneta acaba en la escombrera", carro_en(v["destinos"]["escombrera"]))
        is_block("y la compuerta sigue cerrada", puerta[0], "minecraft:air", want=False)
        lanzar((True, True))
        is_block("aguja 1 con señal: hacia el norte", a1, "minecraft:rail[shape=north_east]")
        is_block("aguja 2 con señal: hacia la fundición", a2, "minecraft:rail[shape=south_west]")
        until("con las dos agujas la vagoneta acaba en la vía muerta", carro_en(v["destinos"]["fundicion"]))
        is_block("y la compuerta sigue cerrada", puerta[0], "minecraft:air", want=False)
        lanzar(v["solucion"])
        until("aguja 1 al norte y aguja 2 al este: la vagoneta llega a la báscula", carro_en(v["bascula"], 0))
        until("la báscula se activa", f"execute if block {at(v['bascula'])} minecraft:detector_rail[powered=true]")
        for p in puerta:
            until(f"la compuerta del filón se abre {p}", f"execute if block {at(p)} minecraft:air")
        cmd(f"kill @e[type=minecraft:minecart,x={COLONIA[0]},y={COLONIA[1] - 30},z={COLONIA[2]},dx=120,dy=80,dz=90]")
        until("sin la vagoneta la compuerta se vuelve a cerrar", f"execute if block {at(puerta[0])} minecraft:air",
              want=False)
        # puzle 2: el despacho del capataz
        des = m["puerta_despacho"]
        d0, d1 = des["door"], (des["door"][0], des["door"][1] + 1, des["door"][2])
        is_block("panel del despacho cerrado", d0, "minecraft:air", want=False)
        lp = des["lever"]
        cmd(f"setblock {at(lp)} minecraft:lever[face=wall,facing=east,powered=true]")
        toque((lp[0] - 1, lp[1], lp[2]), "minecraft:bookshelf")
        for p in (d0, d1):
            until(f"la estantería abre el despacho {p}", f"execute if block {at(p)} minecraft:air")
        # trampa 1: el cable trampa de la boca del cargadero
        tres = "{Items:[{Slot:0b,count:16},{Slot:1b,count:16},{Slot:2b,count:16}]}"
        for p in m["dispensadores"]:
            check(f"dispensador del cable cargado {p}", f"execute if data block {at(p)} {tres}")
        x, y, z = (int(c) for c in at((81, 1, 36)).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        for p in m["dispensadores"]:
            until(f"el cable trampa dispara {p}", f"execute if data block {at(p)} {tres}", want=False, secs=8)
        # trampa 2: la placa sobre la dinamita (la última: explota)
        is_block("la dinamita bajo la placa", m["tnt"], "minecraft:tnt")
        x, y, z = (int(c) for c in at(m["placa_tnt"]).split())
        cmd(f"summon minecraft:zombie {x + 0.5} {y} {z + 0.5} {{NoAI:1b,Silent:1b,PersistenceRequired:1b}}")
        until("la placa prende la dinamita", f"execute if block {at(m['tnt'])} minecraft:tnt", want=False, secs=8)
    finally:
        if proc.poll() is None:
            sm.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("PRUEBA MINA PERDIDA " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
