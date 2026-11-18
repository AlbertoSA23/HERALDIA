"""Prueba en servidor real de los mecanismos del Palacio oriental (puertas de pistones y trampas).

Uso: python3 tools/smoke/palace_redstone.py --jar build/libs/heraldia-X.jar  (después de ./gradlew build)
Coloca la plantilla sin rotar en (0, 100, 0), quita cada palanca (su retirada actualiza a los vecinos del bloque
de apoyo, como al accionarla) y comprueba que las puertas se abren; dispara los cables con un objeto y la placa con
un cerdo, y comprueba que los dispensadores gastan una flecha (los de cable llevan 3 × 6 flechas, los de la placa 8). Código 0 si todo pasa.
"""
import argparse, os, queue, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server_smoke import prepare, gradle_properties, reader, wait_for, run, send, Context, ROOT, START_TIMEOUT_S

OY = 100
CHECKS = []


def at(x, y, z):
    return f"{x} {y + OY} {z}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke-palacio"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    launcher = prepare(args.work, os.path.abspath(args.jar), gradle_properties())
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails = queue.Queue(), [], []
    threading.Thread(target=reader, args=(proc, lines), daemon=True).start()
    ctx = Context(proc, lines, seen)

    def test(cond, what):
        if not ctx.test(f"execute if {cond}"):
            fails.append(what)

    def cmd(c, pause=1.5):
        send(proc, c)
        ctx.ticks(int(pause * 20))      # en ticks del juego: con el servidor atrasado, el reloj no basta

    try:
        wait_for(lines, r"Heraldia: (\d+) estructuras registradas", START_TIMEOUT_S, seen)
        cmd("forceload add -16 -16 96 140", 8)
        for _ in range(20):
            m = run(proc, lines, seen, f"place template heraldia:unicas/palacio/palacio 0 {OY} 0",
                    r"Loaded template|Failed|not loaded|Unknown|Invalid")
            if "Loaded template" in m.group(0):
                break
            time.sleep(3)
        else:
            fails.append("no se pudo colocar la plantilla")
        ctx.ticks(40)
        test(f"block {at(9, 3, 41)} minecraft:bookshelf", "biblioteca: puerta cerrada al colocar")
        test(f"block {at(7, 3, 41)} minecraft:sticky_piston[extended=true]", "biblioteca: pistón extendido al colocar")
        test(f"block {at(40, 2, 48)} minecraft:deepslate_bricks", "cámara: puerta cerrada al colocar")
        # puertas
        cmd(f"setblock {at(7, 4, 43)} minecraft:air", 2)
        test(f"block {at(9, 3, 41)} minecraft:air", "biblioteca: hueco bajo abierto")
        test(f"block {at(9, 4, 41)} minecraft:air", "biblioteca: hueco alto abierto")
        test(f"block {at(8, 4, 41)} minecraft:bookshelf", "biblioteca: estantería recogida tras la columna")
        cmd(f"setblock {at(38, 9, 61)} minecraft:air", 2)
        test(f"block {at(40, 8, 63)} minecraft:air", "trono: hueco bajo abierto")
        test(f"block {at(40, 9, 63)} minecraft:air", "trono: hueco alto abierto")
        cmd(f"setblock {at(37, 2, 47)} minecraft:air", 2)
        test(f"block {at(40, 2, 48)} minecraft:air", "cámara: una palanca abre el bloque bajo")
        test(f"block {at(40, 3, 48)} minecraft:deepslate_bricks", "cámara: con una palanca el bloque alto sigue")
        cmd(f"setblock {at(43, 3, 47)} minecraft:air", 2)
        test(f"block {at(40, 3, 48)} minecraft:air", "cámara: las dos palancas abren la puerta")
        # trampas
        for z in (56, 50):
            cmd(f"summon minecraft:item {30.5} {2.1 + OY} {z + 0.5} {{Item:{{id:\"minecraft:stick\",count:1}},PickupDelay:32767}}", 2)
            for x in (28, 32):
                test(f"block {at(x, 3, z)} minecraft:dispenser", f"cable z={z}: dispensador {x}")
                test(f"data block {at(x, 3, z)} Items[{{count:5}}]", f"cable z={z}: el dispensador {x} no disparó")
        cmd(f"summon minecraft:pig 71.5 {3 + OY} 38.5 {{NoAI:1b}}", 2)
        for x in (70, 72):
            test(f"data block {at(x, 3, 38)} Items[{{count:7}}]", f"placa: el dispensador {x} no disparó")
        send(proc, "stop")
        proc.wait(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
    if fails:
        print("PRUEBA DEL PALACIO FALLIDA:\n  " + "\n  ".join(fails))
        return 1
    print("PRUEBA DEL PALACIO OK: puertas de la biblioteca, del trono y de la cámara (dos palancas), dos cables y la placa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
