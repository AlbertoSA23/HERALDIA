"""The world's search memory (common/SearchCaches, attachment heraldia:busquedas) on a real 26.3 dedicated server.

Usage: python3 tools/smoke/search_cache.py --jar build/libs/heraldia-X.jar [--work build/smoke-busquedas]
Three starts (seed heraldia, default configuration except the arena and the update check):
1. a new world with the default configuration: the searches of SEARCHES (the four of tools/smoke/generation_cost.py, one that
   finds nothing and /heraldia info nearby), their answers and their time; the memory computes answers and saves them;
2. the same world again: the same answers, exactly; the log says how many answers it read and served, and the searches
   do not compute again what they already knew (at most 1 %: the cells around spawn, computed while the spawn was being
   prepared in start 1, before the memory was ready); the mines' /locate, the most expensive one, takes much less;
3. the same world with medianas.frecuencia_porcentaje = 100: the log says that the memory is discarded (another
   configuration) and the medium structures' /locate gives what a new world with that value gives (DENSE_MEDIUM, measured
   with the .jar from before the memory), not the remembered answer.
Exit code 0 if everything passes.
"""
import argparse, json, os, queue, re, subprocess, sys, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

LOCATE_FROM = (8000, -8000)
NOTHING_FROM = (200000, 200000)          # the 100 allowed village cells are near 0,0: out of /locate's 100 rings
SEARCHES = [("aldea", "#heraldia:aldeas", LOCATE_FROM), ("unica", "heraldia:unicas/castillo", LOCATE_FROM),
            ("mediana", "#heraldia:medianas", LOCATE_FROM), ("mina", "#heraldia:minas", LOCATE_FROM),
            ("nada", "#heraldia:aldeas", NOTHING_FROM)]
INFO_FROM, INFO_RADIUS = (3000, 3000), 2000
BASE_CONFIG = {"arena": {"generar_en_mundos_nuevos": False}, "update_check": {"activado": False}}
DENSE = {"medianas": {"frecuencia_porcentaje": 100}}
# /locate #heraldia:medianas from LOCATE_FROM in a new world with DENSE, measured with the .jar from before the memory
DENSE_MEDIUM = (7936, -7936)
_LOCATE_MS = re.compile(r"Locating element (\S+) .*?took (\d+) ms")
_ANSWER = r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find"
_READ = re.compile(r"Heraldia: búsquedas: (\d+) respuestas guardadas en la memoria")
_SERVED = re.compile(r"Heraldia: búsquedas: (\d+) respuestas servidas de la memoria y (\d+) calculadas en esta sesión; (\d+) guardadas")
_DISCARDED = "Heraldia: búsquedas: la memoria guardada"
_INFO = re.compile(r"Heraldia: /heraldia info nearby \d+ en -?\d+, -?\d+: (\d+) estructuras en")


def config(work, extra):
    cfg = json.loads(json.dumps(BASE_CONFIG))
    for k, v in extra.items():
        cfg.setdefault(k, {}).update(v)
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def locate(ctx, target, at):
    """(answer, ms): the answer is (x, z) or None if nothing is found; ms as the game says it."""
    s.pending(ctx.lines, ctx.seen)
    s.send(ctx.proc, f"execute positioned {at[0]} 64 {at[1]} run locate structure {target}")
    ms, answer, done = None, None, False
    while ms is None or not done:
        m = s.wait_for(ctx.lines, _LOCATE_MS.pattern + "|" + _ANSWER + "|" + s.ERROR_PATTERN, s.COMMAND_TIMEOUT_S, ctx.seen)
        g = m.group(0)
        if g.startswith("Locating element"):
            ms = int(m.group(2))
        elif g.startswith("is at"):
            answer, done = (int(m.group(3)), int(m.group(4))), True
        elif g.startswith("Could not find"):
            done = True
            ms = -1 if ms is None else ms          # the game does not time a search that finds nothing
        else:
            raise SystemExit(f"/locate {target}: {m.string.strip()}")
    return answer, ms


def info(ctx):
    """The lines of /heraldia info nearby (without the time of its title)."""
    s.pending(ctx.lines, ctx.seen)
    s.send(ctx.proc, f"execute positioned {INFO_FROM[0]} 64 {INFO_FROM[1]} run heraldia info nearby {INFO_RADIUS}")
    n = int(s.wait_for(ctx.lines, _INFO.pattern + "|" + s.ERROR_PATTERN, s.COMMAND_TIMEOUT_S, ctx.seen).group(1) or 0)
    out = []
    while len(out) < n + 1:
        line = ctx.lines.get(timeout=s.COMMAND_TIMEOUT_S)
        if line is None:
            raise SystemExit("the server shut down early")
        ctx.seen.append(line)
        if "]: " in line and "Heraldia:" not in line:
            out.append(re.sub(r"\d+ ms", "N ms", line.split("]: ", 1)[1].strip()))
    return out


def start(work, launcher, searches=True, only=None):
    """One start: {name: (answer, ms)}, the lines of info nearby and the log."""
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    out, lines_info = {}, []
    try:
        s.wait_for(lines, r"Heraldia: \d+ estructuras registradas", s.START_TIMEOUT_S, seen)
        # the memory is ready a moment after the start (its stamp is computed on another thread): its line says so
        s.wait_for(lines, _READ.pattern + "|" + _DISCARDED, s.COMMAND_TIMEOUT_S, seen)
        for name, target, at in SEARCHES:
            if only is None or name in only:
                out[name] = locate(ctx, target, at)
        if searches:
            lines_info = info(ctx)
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            proc.wait(timeout=300)
    s.pending(lines, seen)
    return out, lines_info, "".join(seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-busquedas"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    launcher = s.prepare(args.work, os.path.abspath(args.jar), s.gradle_properties())
    failures = []

    # 1) a new world, default configuration: the memory computes and saves
    config(args.work, {})
    first, info1, log1 = start(args.work, launcher)
    m = _SERVED.search(log1)
    if not m or int(m.group(2)) == 0 or int(m.group(3)) == 0:
        failures.append(f"start 1: the memory computed or saved nothing: {m.group(0) if m else 'no line'}")
    if first["nada"][0] is not None:
        failures.append(f"the search from {NOTHING_FROM} should find nothing: {first['nada']}")

    # 2) the same world: the same answers, served from the memory
    second, info2, log2 = start(args.work, launcher)
    m_read, m = _READ.search(log2), _SERVED.search(log2)
    if not m_read or int(m_read.group(1)) == 0:
        failures.append("start 2: the saved memory was not read")
    if not m or int(m.group(1)) == 0:
        failures.append(f"start 2: nothing was served from the memory: {m.group(0) if m else 'no line'}")
    elif int(m.group(2)) * 100 > int(m.group(1)):
        # a handful is expected: the biome candidates of the cells around spawn, computed in start 1 while the spawn was
        # prepared, before the memory was ready (its stamp is computed on another thread), so they were not stored
        failures.append(f"start 2: the same searches computed again {m.group(2)} answers ({m.group(1)} served)")
    for name in first:
        if first[name][0] != second[name][0]:
            failures.append(f"{name}: start 1 found {first[name][0]}, start 2 {second[name][0]}")
    if info1 != info2:
        failures.append(f"/heraldia info nearby changed:\n  {info1}\n  {info2}")
    if not info1:
        failures.append("/heraldia info nearby found nothing")
    if second["mina"][1] * 2 > first["mina"][1]:
        failures.append(f"the mines' /locate does not save time with the memory: {first['mina'][1]} -> {second['mina'][1]} ms")

    # 3) another configuration: the memory is discarded and the answer is that of the new configuration
    config(args.work, DENSE)
    third, _, log3 = start(args.work, launcher, searches=False, only={"mediana"})
    if _DISCARDED not in log3:
        failures.append("start 3: another configuration and the memory was not discarded")
    if third["mediana"][0] != DENSE_MEDIUM:
        failures.append(f"start 3: the medium structure found is {third['mediana'][0]}; a new world with that configuration "
                        f"gives {DENSE_MEDIUM}")
    if DENSE_MEDIUM == first["mediana"][0]:
        failures.append("the reference does not tell the two configurations apart: choose another LOCATE_FROM")

    print("search_cache: " + ", ".join(f"{k} {first[k][1]} -> {second[k][1]} ms ({first[k][0]})" for k in first)
          + f"; mediana al 100 %: {third['mediana'][0]}")
    if failures:
        print("FAILURES:\n- " + "\n- ".join(failures))
        sys.exit(1)
    print("OK: search memory (same answers after a restart, served without computing; discarded with another configuration)")


if __name__ == "__main__":
    main()
