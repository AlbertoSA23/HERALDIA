"""Prueba en un servidor dedicado 26.3 real: circuitos, guardián y agua del Templo-pirámide.

Uso: python3 tools/gen/uniques/pyramid/smoke_server.py --jar build/libs/heraldia-<versión>.jar
Coloca las dos plantillas sin rotación con /place template (sin procesadores) y comprueba:
el guardián existe con 40 de vida; la puerta secreta está cerrada en reposo, se abre al cargar el bloque de la
antorcha (lo que hace la palanca) y se cierra al quitarlo; el cable trampa, las placas del foso y las losas de
dardos disparan con una entidad encima; el agua no se sale. Código 0 si todo pasa.
"""
import argparse, os, queue, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.join(ROOT, "tools", "smoke"))
sys.path.insert(0, os.path.join(ROOT, "tools", "gen"))
import server_smoke as S                         # noqa: E402
from uniques.pyramid import construction                 # noqa: E402

O = (-40, 150, -35)


def w(p):
    return f"{O[0] + p[0]} {O[1] + p[1]} {O[2] + p[2]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke_piramide"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    o = construction.build_all()
    launcher = S.prepare(args.work, os.path.abspath(args.jar), S.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=S.reader, args=(proc, lines), daemon=True).start()
    ctx = S.Context(proc, lines, seen)

    def cmd(c, ok=r"Test passed|Test failed|Changed the block|Could not|Summoned|Marked|Added|chunk|[Pp]laced|Loaded template|Unable|failed|Failed|has the following|No |Invalid"):
        return S.run(proc, lines, seen, c, ok).group(0)

    def check(name, c, until=False):
        ok = ctx.until(c) if until else ctx.test(c)
        print(("OK   " if ok else "FALLA ") + name)
        if not ok:
            fails.append(name)

    try:
        S.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", S.START_TIMEOUT_S, seen)
        cmd("forceload add -48 -48 47 47")
        for name, off in (("superficie", (0, 0, 0)), ("subsuelo", (8, -27, 0))):
            for _ in range(30):
                r = cmd(f"place template heraldia:unicas/piramide/{name} {w(off)}")
                if "not loaded" not in r and "Unable" not in r:
                    break
                time.sleep(5)
            print("colocada", name, r)
        ctx.ticks(60)
        check("guardián con 40 de vida", "execute if entity @e[type=minecraft:zombie,tag=heraldia_piramide_guardian,nbt={Health:40.0f}]", until=True)
        d = o.door
        check("puerta secreta cerrada en reposo", f"execute if block {w(d['D'][0])} minecraft:deepslate_tiles")
        check("pistones extendidos en reposo", f"execute if block {w(d['pistons'][1])} minecraft:sticky_piston[extended=true]")
        cmd(f"setblock {w(d['X'])} minecraft:redstone_block")
        ctx.ticks(40)
        check("la palanca abre la puerta (abajo)", f"execute if block {w(d['D'][0])} minecraft:air")
        check("la palanca abre la puerta (arriba)", f"execute if block {w(d['D'][1])} minecraft:air")
        cmd(f"setblock {w(d['X'])} minecraft:deepslate_tiles")
        ctx.ticks(40)
        check("la puerta se cierra otra vez", f"execute if block {w(d['D'][0])} minecraft:deepslate_tiles")
        # trampas con una entidad encima
        tx, ty, tz = o.marks["trampa:cable"][0]
        cmd(f"summon minecraft:armor_stand {O[0] + tx + 0.5} {O[1] + ty} {O[2] + tz + 0.5}")
        disp = w((tx, ty + 1, tz - 2))
        end = time.monotonic() + S.UNTIL_S
        while True:               # 3 ranuras de 6 flechas (piezas.tripwire_trap): alguna debe haber bajado
            fired = any(ctx.test(f"execute unless data block {disp} Items[{{Slot:{i}b,count:6}}]") for i in range(3))
            if fired or time.monotonic() > end:
                break
            time.sleep(S.POLL_S)
        print(("OK   " if fired else "FALLA ") + "cable trampa dispara")
        if not fired:
            fails.append("cable trampa dispara")
        px, py, pz = o.marks["trampa:foso"][0]
        cmd(f"summon minecraft:armor_stand {O[0] + px + 0.5} {O[1] + py} {O[2] + pz + 0.5}")
        check("el foso se abre", f"execute if block {w((px, py - 1, pz - 1))} minecraft:iron_trapdoor[open=true]", until=True)
        dx, dy, dz = o.marks["trampa:dardos"][1]
        cmd(f"summon minecraft:armor_stand {O[0] + dx + 0.5} {O[1] + dy} {O[2] + dz + 0.5}")
        check("losa de dardos dispara", f"execute unless data block {w((dx, dy - 1, dz))} Items[{{count:8}}]", until=True)
        ctx.ticks(60)
        check("el agua no entra en la cámara sumergida", f"execute if block {w((construction.CX + 14, -14, construction.CZ + 11))} minecraft:air")
        check("el cenote sigue lleno", f"execute if block {w((construction.CX, -15, construction.CZ + 11))} minecraft:water")
        treasure = o.marks["cofre:tesoro"][0]
        check("cofre premium con su tabla", f"execute if data block {w(treasure)} {{LootTable:\"heraldia:unicas/piramide/premium\"}}")
    finally:
        if proc.poll() is None:
            S.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("PRUEBA DE LA PIRÁMIDE " + ("FALLIDA: " + ", ".join(fails) if fails else "OK"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
