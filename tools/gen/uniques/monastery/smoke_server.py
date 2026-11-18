"""Prueba a mano en un servidor dedicado 26.3: coloca la plantilla del monasterio sin rotar y comprueba que la redstone
queda estable al colocarse y que los dos puzles se resuelven (y solo con su solución).

Uso (desde la raíz, con el .jar compilado): python3 tools/gen/uniques/monastery/smoke_server.py --jar build/libs/heraldia-0.1.0.jar
Las palancas se accionan con /setblock y luego se «toca» el bloque al que van fijadas (otro bloque y vuelta), que es la
actualización de vecinos que hace la palanca de verdad al pulsarla.
"""
import argparse, os, queue, subprocess, sys, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "smoke"))
import server_smoke as S

O = (0, 100, 0)
MONASTERY = (59, 71, 92)        # tamaño de la plantilla (x, y, z): el guardián no debe salir de ella


def w(p):
    return f"{p[0] + O[0]} {p[1] + O[1]} {p[2] + O[2]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(S.ROOT, "build", "smoke_monasterio"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    launcher = S.prepare(args.work, os.path.abspath(args.jar), S.gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=S.reader, args=(proc, lines), daemon=True).start()
    ctx = S.Context(proc, lines, seen)

    def cmd(c, ok=r"Changed|Successfully|placed|Test passed|Test failed|Marked|Added|Set|Could not"):
        return S.run(proc, lines, seen, c, ok).group(0)

    def check(p, state, what):
        if not ctx.block(w(p), state):
            fails.append(what)

    def lever(p, on, attach, mat):
        cmd(f"setblock {w(p)} minecraft:lever[face=wall,facing={'south' if p[2] == 74 else 'north'},powered={'true' if on else 'false'}]")
        cmd(f"setblock {w(attach)} minecraft:polished_andesite")
        cmd(f"setblock {w(attach)} minecraft:{mat}")
        ctx.ticks(30)          # 1,5 s de juego: de sobra para pistones (2 ticks) y antorchas (2 ticks por paso)

    try:
        S.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", S.START_TIMEOUT_S, seen)
        cmd(S.FORCELOAD)
        for _ in range(S.PLACE_ATTEMPTS):
            r = cmd(f"place template heraldia:unicas/monasterio/monasterio {w((0, 0, 0))}", r"Loaded template|placed|Failed|not loaded|Unknown|Invalid")
            if "not loaded" not in r:
                break
            time.sleep(S.PLACE_RETRY_S)
        ctx.ticks(60)
        # estado estable al colocarse
        for y in (30, 31):
            check((43, y, 72), "minecraft:sticky_piston[extended=true]", f"pistón de la cripta y={y} recogido al colocarse")
        for x in (45, 47):
            check((x, 32, 73), "minecraft:redstone_lamp[lit=true]", f"lámpara {x} apagada al colocarse")
        check((43, 14, 48), "minecraft:redstone_wall_torch[lit=true]", "antorcha 1 del osario apagada")
        check((52, 14, 49), "minecraft:redstone_wall_torch[lit=false]", "antorcha final del osario encendida")
        check((53, 14, 49), "minecraft:iron_door[open=false]", "puerta del archivo abierta al colocarse")
        check((46, 30, 82), "minecraft:spawner", "falta el generador de la cripta")
        # El guardián (esqueleto con IA) se busca por su etiqueta en todo el mundo, no en una caja junto al relicario:
        # anda, y desde el relicario sale por la antecámara de las losas hacia las catacumbas. La CI falló así («falta
        # el guardián» 30 s seguidos con la caja de 18 x 10 x 12). Se comprueba que siga dentro del monasterio.
        g = "@e[type=minecraft:skeleton,tag=heraldia_guardian.monasterio]"
        if not ctx.wait_entity(g):
            fails.append("falta el guardián")
        else:
            gp = ctx.pos(g)
            print(f"guardián en {gp}")
            if gp is None or not all(O[i] + lo <= v <= O[i] + hi for i, (v, lo, hi) in enumerate(zip(gp, (0, 0, 0), MONASTERY))):
                fails.append(f"el guardián ha salido del monasterio: {gp}")
        # puzle 1: apagar una palanca no basta; las dos, sí
        lever((45, 31, 74), False, (45, 31, 73), "deepslate_bricks")
        check((41, 30, 72), "minecraft:chiseled_deepslate", "la lápida se abre con una sola palanca")
        lever((47, 31, 74), False, (47, 31, 73), "deepslate_bricks")
        check((41, 30, 72), "minecraft:air", "la lápida no se abre con las dos palancas apagadas")
        check((42, 30, 72), "minecraft:chiseled_deepslate", "la lápida no ha quedado recogida junto al pistón")
        check((45, 32, 73), "minecraft:redstone_lamp[lit=false]", "lámpara encendida con la palanca apagada")
        # puzle 2: 1 y 3 arriba abre; con la 2 también arriba, cierra
        lever((43, 14, 46), True, (43, 14, 47), "stone_bricks")
        check((53, 14, 49), "minecraft:iron_door[open=false]", "la puerta del archivo se abre solo con la palanca 1")
        lever((47, 14, 46), True, (47, 14, 47), "stone_bricks")
        check((53, 14, 49), "minecraft:iron_door[open=true]", "la puerta del archivo no se abre con 1 y 3")
        lever((45, 14, 46), True, (45, 14, 47), "stone_bricks")
        check((53, 14, 49), "minecraft:iron_door[open=false]", "la puerta del archivo sigue abierta con las tres palancas")
    finally:
        if proc.poll() is None:
            S.send(proc, "stop")
            proc.wait(timeout=120)
    if fails:
        print("PRUEBA DEL MONASTERIO FALLIDA:\n  " + "\n  ".join(fails))
        return 1
    print("PRUEBA DEL MONASTERIO OK: redstone estable al colocarse y puzles resueltos solo con su solución")
    return 0


if __name__ == "__main__":
    sys.exit(main())
