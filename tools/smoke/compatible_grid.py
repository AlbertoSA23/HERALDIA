"""uniques.rejilla_compatible on a real 26.3 dedicated server (complements server_smoke.py and RejillaCompatibleTest).

Usage: python3 tools/smoke/compatible_grid.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
With the option enabled, /locate of several unique structures that were already in 0.1.0 (branch main) gives exactly the coordinates
that main's .jar gave with the same seed (level-seed=heraldia from server_smoke.prepare) and the default
configuration: so those already generated in a world of that version are found again. It also checks the old grid's
log, the /heraldia info line and that a new unique structure (new grid) does not appear closer than the minimum distance to the
located old ones.

MAIN's coordinates were taken with main's .jar (commit 3248f74, heraldia-0.1.0.jar built with ./gradlew build
in a worktree) and this same script: python3 tools/smoke/compatible_grid.py --jar <main's jar> --extract.
Exit code 0 if everything passes.
"""
import argparse, json, math, os, queue, subprocess, sys, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

CONFIG = {"unicas": {"rejilla_compatible": True}}    # main's .jar does not know it: it warns and ignores it
POINTS = [(0, 0), (7000, -5000)]
OLD = ["castillo", "catedral", "coliseo", "fortaleza_hielo", "acueducto", "faro", "piramide", "observatorio"]
NEW = ["santuario", "salon_jarl"]
MIN_DISTANCE = 1000     # uniques.distancia_minima.bloques by default
# {"<id> <x>,<z>": [x, z] or None}: /locate from (x, z) with main's .jar (see the header).
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
    ap.add_argument("--extract", action="store_true", help="only prints the coordinates (to pin MAIN with main's .jar)")
    ap.add_argument("--no-option", action="store_true", help="with --extract: the option disabled (to see that they change)")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    with open(os.path.join(a.work, "config", "heraldia.json"), "w") as f:
        json.dump({} if a.no_option else CONFIG, f)
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails, got = queue.Queue(), [], [], {}
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        ctx = s.Context(proc, lines, seen)
        for sid in OLD + ([] if a.extract else NEW):
            for x, z in POINTS:
                p = s.locate(ctx, sid, x, z)
                got[key(sid, x, z)] = list(p[:2]) if p else None
                print(f"/locate {sid} from {x},{z}: {got[key(sid, x, z)]} ({p[2]:.1f} s)" if p else f"/locate {sid} from {x},{z}: nothing")
        if a.extract:
            print("MAIN =", json.dumps({k: got[k] for k in got}, indent=4))
            return 0
        for k, want in MAIN.items():
            if got.get(k) != want:
                fails.append(f"/locate {k}: {got.get(k)}, with main's .jar {want}")
        old = [tuple(v) for k, v in got.items() if v and k.split()[0] in OLD]
        for k, v in got.items():
            if v and k.split()[0] in NEW:
                close = [o for o in old if math.dist(o, v) < MIN_DISTANCE]
                if close:
                    fails.append(f"{k} at {v} within {MIN_DISTANCE} blocks of an old one: {close}")
        log = ctx.log()
        if "rejilla unicas/castillo: activada, cada 250 chunks (separación mínima 190, rejilla antigua)" not in log:
            fails.append("the castle's old grid is missing from the log")
        if "rejilla unicas/santuario: activada, cada 250 chunks (separación mínima 63, origen desplazado)" not in log:
            fails.append("the sanctuary's new grid is missing from the log")
        m = ctx.run("heraldia info", r"(?:Old unique-structure grid|Rejilla antigua de las únicas)[^:]*: (\S+)")
        if m.group(1) not in ("enabled", "activada"):
            fails.append(f"/heraldia info does not show the old grid as enabled: {m.string.strip()}")
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
