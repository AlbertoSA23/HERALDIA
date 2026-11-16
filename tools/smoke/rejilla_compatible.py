"""unicas.rejilla_compatible en un servidor dedicado 26.3 real (complementa server_smoke.py y RejillaCompatibleTest).

Uso: python3 tools/smoke/rejilla_compatible.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Con la opción activada, /locate de varias únicas que ya estaban en la 0.1.0 (rama main) da exactamente las coordenadas
que daba el .jar de main con la misma semilla (level-seed=heraldia de server_smoke.prepare) y la configuración por
defecto: así las ya generadas en un mundo de esa versión se vuelven a encontrar. También comprueba el log de la rejilla
antigua, la línea de /heraldia info y que una única nueva (rejilla nueva) no sale a menos de la distancia mínima de las
antiguas localizadas.

Las coordenadas de MAIN se sacaron con el .jar de main (commit 3248f74, heraldia-0.1.0.jar compilado con ./gradlew build
en un worktree) y este mismo script: python3 tools/smoke/rejilla_compatible.py --jar <jar de main> --sacar.
Código 0 si todo pasa.
"""
import argparse, json, math, os, queue, subprocess, sys, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

CONFIG = {"unicas": {"rejilla_compatible": True}}    # el .jar de main no la conoce: avisa y la ignora
POINTS = [(0, 0), (7000, -5000)]
OLD = ["castillo", "catedral", "coliseo", "fortaleza_hielo", "acueducto", "faro", "piramide", "observatorio"]
NEW = ["santuario", "salon_jarl"]
MIN_DISTANCE = 1000     # unicas.distancia_minima.bloques por defecto
# {"<id> <x>,<z>": [x, z] o None}: /locate desde (x, z) con el .jar de main (ver la cabecera).
MAIN = {
    "castillo 0,0": [-7840, -8000],
    "castillo 7000,-5000": [12640, -11584],
    "catedral 0,0": [4512, 912],
    "catedral 7000,-5000": [48, -7984],
    "coliseo 0,0": [4912, -3296],
    "coliseo 7000,-5000": [4912, -3296],
    "fortaleza_hielo 0,0": [528, 4896],
    "fortaleza_hielo 7000,-5000": [4160, -7200],
    "acueducto 0,0": [4400, 8688],
    "acueducto 7000,-5000": [12624, -15328],
    "faro 0,0": [272, -3200],
    "faro 7000,-5000": [272, -3200],
    "piramide 0,0": [352, -11744],
    "piramide 7000,-5000": [352, -11744],
    "observatorio 0,0": [-23792, 8944],
    "observatorio 7000,-5000": [-23792, 8944],
}


def key(sid, x, z):
    return f"{sid} {x},{z}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-rejilla"))
    ap.add_argument("--sacar", action="store_true", help="solo imprime las coordenadas (para fijar MAIN con el .jar de main)")
    ap.add_argument("--sin-opcion", action="store_true", help="con --sacar: la opción desactivada (para ver que cambian)")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    with open(os.path.join(a.work, "config", "heraldia.json"), "w") as f:
        json.dump({} if a.sin_opcion else CONFIG, f)
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails, got = queue.Queue(), [], [], {}
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        ctx = s.Context(proc, lines, seen)
        for sid in OLD + ([] if a.sacar else NEW):
            for x, z in POINTS:
                p = s.locate(ctx, sid, x, z)
                got[key(sid, x, z)] = list(p[:2]) if p else None
                print(f"/locate {sid} desde {x},{z}: {got[key(sid, x, z)]} ({p[2]:.1f} s)" if p else f"/locate {sid} desde {x},{z}: nada")
        if a.sacar:
            print("MAIN =", json.dumps({k: got[k] for k in got}, indent=4))
            return 0
        for k, want in MAIN.items():
            if got.get(k) != want:
                fails.append(f"/locate {k}: {got.get(k)}, con el .jar de main {want}")
        old = [tuple(v) for k, v in got.items() if v and k.split()[0] in OLD]
        for k, v in got.items():
            if v and k.split()[0] in NEW:
                close = [o for o in old if math.dist(o, v) < MIN_DISTANCE]
                if close:
                    fails.append(f"{k} en {v} a menos de {MIN_DISTANCE} bloques de una antigua: {close}")
        log = ctx.log()
        if "rejilla unicas/castillo: activada, cada 250 chunks (separación mínima 190, rejilla antigua)" not in log:
            fails.append("falta en el log la rejilla antigua del castillo")
        if "rejilla unicas/santuario: activada, cada 250 chunks (separación mínima 63, origen desplazado)" not in log:
            fails.append("falta en el log la rejilla nueva del santuario")
        m = ctx.run("heraldia info", r"(?:Old unique-structure grid|Rejilla antigua de las únicas)[^:]*: (\S+)")
        if m.group(1) not in ("enabled", "activada"):
            fails.append(f"/heraldia info no muestra la rejilla antigua activada: {m.string.strip()}")
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("REJILLA COMPATIBLE:", f"OK ({len(MAIN)} /locate iguales a main)" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
