"""Heraldia generation cost: the same area of the same world generated with the mod and without it, and its comparison with the
reference stored in the repository (tools/smoke/cost_reference.json).

Usage:
  python3 tools/smoke/generation_cost.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
  python3 tools/smoke/generation_cost.py ... --update-reference     # measures and saves the new reference
  python3 tools/smoke/generation_cost.py --from-json build/coste/generation_cost.json [--update-reference]
      # rebuilds the summary (or the reference) from a measurement already taken, e.g. the CI artifact "coste-generacion"

Each pass starts a fresh 26.3 dedicated server (world deleted, fixed seed SEED, Fabric API and Chunky), once
with the Heraldia .jar (default configuration and -Dheraldia.perfil=true) and once without it, alternating. In each
one: Chunky generates a warm-up area (not counted), then the ZONES with the Minecraft profiler active
(/jfr start ... /jfr stop) and finally /locate is timed for LOCATES. From the .jfr we get, per chunk of the zones, the sum of the
time of each generation step (minecraft.ChunkGeneration event): ms per chunk (mean, p50, p90, p99, max) and per
step; from the /jfr summary, the MSPT (ms per tick) and memory; from the log, the time of each /locate and Heraldia's own
profile (comun/Perfil.java: roads, hillside, shore, medium structures, mines, foreign-structure zone...).

Overhead = median of the passes with Heraldia / median without it - 1, in server-process CPU per chunk
(/proc/<pid>/stat while Chunky generates the zones: it does not grow with the wait between threads, which does inflate the duration of the
JFR steps, ±15 % between identical passes). Without /proc (outside Linux), with the sum of the JFR steps per chunk without
the light ones (which are mostly waiting in the light engine queue). The ratio removes the machine's speed.
Fails if it exceeds reference × (1 + umbral_relativo) + margen_absoluto (both in the reference). If it fails, it repeats
one round of passes and decides with all of them (CI noise). Writes <output>/generation_cost.json and
<output>/generation_cost.md, and the Markdown also to $GITHUB_STEP_SUMMARY if it exists. Exit code 0 if it passes.
The pure functions are tested in tools/gen/tests/test_generation_cost.py.
"""
import argparse, json, math, os, queue, re, shutil, statistics, subprocess, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import modrinth

REFERENCE = os.path.join(s.ROOT, "tools", "smoke", "cost_reference.json")
SEED = "heraldia"
# (name, x, z, half side in blocks): squares of whole chunks that Chunky generates. Far from each other (more than
# MARGIN_CHUNKS chunks) so that each event falls in a single zone. "aldea": the village closest to 0,0 with the
# default configuration (swamp, 32 -1344) and the start of its roads; "origen": 0,0 (no Heraldia village).
ZONES = [("aldea", 32, -1344, 160), ("origen", 0, 0, 160)]
WARMUP = ("calentamiento", 6000, 6000, 64)
MARGIN_CHUNKS = 12         # chunks around a zone that it generates along the way (earlier steps of the neighbours)
# Light steps: their duration is mostly waiting in the light engine queue (a single thread), not generation
# work, and it is the noisiest (±15 % between identical passes). They do not count in ms per chunk; they are reported separately.
LIGHT_STEPS = {"minecraft:initialize_light", "minecraft:light"}
# Steps where the structure code works (placement rules, starts, pieces and features such as roads).
STRUCTURE_STEPS = {"minecraft:structure_starts", "minecraft:structure_references", "minecraft:features"}
# /locate timed at the end of each pass, from LOCATE_FROM: (name, target, only with Heraldia)
LOCATE_FROM = (8000, -8000)
LOCATES = [("aldea", "#heraldia:aldeas", True), ("unica", "heraldia:unicas/castillo", True),
           ("mediana", "#heraldia:medianas", True), ("mina", "#heraldia:minas", True),
           ("aldea_vanilla", "#minecraft:village", False)]
SWEEPS = 3
# Heraldia configuration: the default one (the real server's), except the wave arena, which in a new world
# builds itself next to spawn (one chunk of work per tick, on the server thread, right while it is
# being measured): it is not generation cost and in the server's existing world it is not generated.
CONFIG = {"arena": {"generar_en_mundos_nuevos": False}}
XMX = "3G"
CHUNKY_TIMEOUT_S = 900
_CHUNKY_END = re.compile(r"Task finished for (\S+)\. Processed: (\d+) chunks")
_LOCATE = re.compile(r"Locating element (\S+) .*?took (\d+) ms")
_PROFILE = re.compile(r"Heraldia: perfil: (\{.*\})\s*$")
_JFR_END = re.compile(r"Dumped flight recorder profiling to (\S+\.jfr)")
_JFR_SUMMARY = re.compile(r"Dumped recording summary to (\S+\.json)")


# ---------------------------------------------------------------- funciones puras (tests en test_generation_cost.py)

def percentile(values, p):
    """Percentile p (0-100) with linear interpolation between ranks (like numpy "linear"); None if there are no values."""
    v = sorted(values)
    if not v:
        return None
    k = (len(v) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def duration_ms(text):
    """Duration from `jfr print --json` ("PT0.000610953S", "PT1M2.5S", "PT0S") in ms."""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", text)
    if not m:
        raise ValueError(f"unrecognized JFR duration: {text!r}")
    h, mi, se = (float(g) if g else 0.0 for g in m.groups())
    return (h * 3600 + mi * 60 + se) * 1000


def chunks_of_zone(x, z, r):
    """(cx0, cz0, cx1, cz1) of the chunks that Chunky generates in the square of half side r centered on (x, z): those from
    x - r to x + r, both included (center 0,0 and radius 128: 17 × 17 = 289 chunks, what "Processed" says)."""
    return ((x - r) >> 4, (z - r) >> 4, (x + r) >> 4, (z + r) >> 4)


def side(c, r):
    return ((c + r) >> 4) - ((c - r) >> 4) + 1


def inside(c, box, margin=0):
    cx, cz = c
    return box[0] - margin <= cx <= box[2] + margin and box[1] - margin <= cz <= box[3] + margin


def chunks_summary(events, box, margin=MARGIN_CHUNKS):
    """From the events [(cx, cz, step, ms)], those of the zone (chunk box and its margin), without the LIGHT_STEPS: per chunk of
    the box, the sum of its steps (p50, p90, p99, max); the mean spreads over the chunks of the box everything in the zone and
    its margin (the neighbours generate earlier steps for it). `pasos_ms`, the same per step (with the light ones);
    `estructuras_ms`, the STRUCTURE_STEPS part; `con_luz_ms`, the mean counting light."""
    per_chunk, steps = {}, {}
    for cx, cz, step, ms in events:
        if not inside((cx, cz), box, margin):
            continue
        steps[step] = steps.get(step, 0.0) + ms
        if step not in LIGHT_STEPS and inside((cx, cz), box):
            per_chunk[(cx, cz)] = per_chunk.get((cx, cz), 0.0) + ms
    n = (box[2] - box[0] + 1) * (box[3] - box[1] + 1)
    v = list(per_chunk.values())
    return {"chunks": n, "chunks_medidos": len(v), "media_ms": sum(ms for k, ms in steps.items() if k not in LIGHT_STEPS) / n,
            "p50_ms": percentile(v, 50), "p90_ms": percentile(v, 90), "p99_ms": percentile(v, 99), "max_ms": max(v, default=None),
            "estructuras_ms": sum(ms for k, ms in steps.items() if k in STRUCTURE_STEPS) / n,
            "con_luz_ms": sum(steps.values()) / n, "pasos_ms": {k: steps[k] / n for k in sorted(steps)}}


def join_zones(events, zones):
    """ms per chunk of all the zones together: means weighted by chunks and percentiles over all chunks (without light)."""
    total = sum(v["chunks"] for v in zones.values())
    def pond(field):
        return sum(z[field] * z["chunks"] for z in zones.values()) / total
    steps = {}
    for z in zones.values():
        for k, ms in z["pasos_ms"].items():
            steps[k] = steps.get(k, 0.0) + ms * z["chunks"] / total
    boxes = [chunks_of_zone(x, zz, r) for n, x, zz, r in ZONES if n in zones]
    per_chunk = {}
    for cx, cz, step, ms in events:
        if step not in LIGHT_STEPS and any(inside((cx, cz), c) for c in boxes):
            per_chunk[(cx, cz)] = per_chunk.get((cx, cz), 0.0) + ms
    pc = list(per_chunk.values())
    return {"media_ms": pond("media_ms"), "p50_ms": percentile(pc, 50), "p90_ms": percentile(pc, 90), "p99_ms": percentile(pc, 99),
            "max_ms": max(pc, default=None), "estructuras_ms": pond("estructuras_ms"), "con_luz_ms": pond("con_luz_ms"),
            "pasos_ms": steps}


def cpu_of_stat(line, hz=100):
    """CPU seconds (user + system) from a /proc/<pid>/stat line (the process name is in parentheses
    and may contain spaces: it is cut after the last ")")."""
    fields = line.rpartition(")")[2].split()
    return (int(fields[11]) + int(fields[12])) / hz


def process_cpu(pid):
    """CPU (s) the process has used so far, or None if there is no /proc (outside Linux)."""
    try:
        with open(f"/proc/{pid}/stat", encoding="ascii") as f:
            return cpu_of_stat(f.read(), os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        return None


def jfr_chunk_events(dataset):
    """[(cx, cz, step, ms)] from the minecraft.ChunkGeneration events of `jfr print --json` (already read)."""
    out = []
    for e in dataset["recording"]["events"]:
        v = e["values"]
        if e.get("type", "minecraft.ChunkGeneration") == "minecraft.ChunkGeneration" and v.get("level", "minecraft:overworld") == "minecraft:overworld":
            out.append((v["chunkPosX"], v["chunkPosZ"], v["status"], duration_ms(v["duration"])))
    return out


def medium(values):
    v = [x for x in values if x is not None]
    return statistics.median(v) if v else None


def add_entry(sweeps):
    """Median of the passes of a configuration (each one a dict of pasada() measurements), field by field."""
    if not sweeps:
        return None
    def median(f):
        return medium([f(p) for p in sweeps])
    out = {"pasadas": len(sweeps),
           "ms_por_chunk": {k: median(lambda p, k=k: p["ms_por_chunk"].get(k)) for k in
                            ("media_ms", "p50_ms", "p90_ms", "p99_ms", "max_ms", "estructuras_ms", "con_luz_ms")},
           "segundos": median(lambda p: p["segundos"]), "chunks": sweeps[0]["chunks"],
           "cpu_ms_por_chunk": median(lambda p: p.get("cpu_ms_por_chunk")),
           "chunks_por_s": median(lambda p: p["chunks"] / p["segundos"] if p["segundos"] else None),
           "mspt": {k: median(lambda p, k=k: (p.get("mspt") or {}).get(k)) for k in ("media", "p50", "p90", "p99", "max")},
           "memoria_mb": median(lambda p: p.get("memoria_mb")),
           "locate_ms": {k: median(lambda p, k=k: p["locate_ms"].get(k)) for k in sorted({k for p in sweeps for k in p["locate_ms"]})}}
    steps = sorted({k for p in sweeps for k in p["ms_por_chunk"]["pasos_ms"]})
    out["pasos_ms"] = {k: median(lambda p, k=k: p["ms_por_chunk"]["pasos_ms"].get(k, 0.0)) for k in steps}
    zones = sorted({k for p in sweeps for k in p["zonas"]})
    out["zonas_ms"] = {k: median(lambda p, k=k: p["zonas"][k]["media_ms"] if k in p["zonas"] else None) for k in zones}
    return out


def metric(aggregate):
    """The deciding measurement: process CPU per chunk if it could be read (the most stable: it does not grow with the wait between
    threads), otherwise the sum of the JFR steps per chunk (without light)."""
    return aggregate.get("cpu_ms_por_chunk") or aggregate["ms_por_chunk"]["media_ms"]


def overcost(with_it, sin):
    """Relative overhead of Heraldia (0.12 = 12 % more than without it) in the same measurement for both (metrica());
    None if something is missing."""
    if not with_it or not sin:
        return None
    if with_it.get("cpu_ms_por_chunk") and sin.get("cpu_ms_por_chunk"):
        return with_it["cpu_ms_por_chunk"] / sin["cpu_ms_por_chunk"] - 1
    if not sin["ms_por_chunk"]["media_ms"]:
        return None
    return with_it["ms_por_chunk"]["media_ms"] / sin["ms_por_chunk"]["media_ms"] - 1


def compare(current, reference):
    """(ok, limit, text) of the current overhead against the reference: fails if it exceeds
    ref × (1 + umbral_relativo) + margen_absoluto. With no reference (or no measurement) it passes, and says so."""
    if current is None:
        return False, None, "no se pudo medir el sobrecoste"
    if not reference or reference.get("sobrecoste") is None:
        return True, None, f"sobrecoste {current:+.1%} (sin referencia guardada: no se compara)"
    ref = reference["sobrecoste"]
    limit = max(ref, 0.0) * (1 + reference.get("umbral_relativo", 0.25)) + reference.get("margen_absoluto", 0.08)
    ok = current <= limit
    return ok, limit, (f"sobrecoste {current:+.1%} frente a la referencia {ref:+.1%} (límite {limit:+.1%}): "
                        + ("dentro del margen" if ok else "REGRESIÓN"))


def new_reference(result, previous=None):
    """The reference that is saved from a measurement (keeps the threshold and margin of the previous one)."""
    previous = previous or {}
    return {"sobrecoste": round(result["sobrecoste"], 4),
            "umbral_relativo": previous.get("umbral_relativo", 0.25), "margen_absoluto": previous.get("margen_absoluto", 0.08),
            "ms_por_chunk_con": round(metric(result["con"]), 2), "ms_por_chunk_sin": round(metric(result["sin"]), 2),
            "medida": "cpu" if result["con"].get("cpu_ms_por_chunk") and result["sin"].get("cpu_ms_por_chunk") else "jfr",
            "pasadas": result["con"]["pasadas"], "maquina": result.get("maquina", ""), "fecha": result.get("fecha", ""),
            "commit": result.get("commit", "")}


def _f(v, fmt="{:.1f}"):
    return "—" if v is None else fmt.format(v)


def markdown(result, comparison):
    """Markdown summary (for the CI job and the artifact)."""
    with_it, sin = result["con"], result["sin"]
    ok, limit, text = comparison
    L = [f"## Coste de generación de Heraldia {'✅' if ok else '❌'}", "", f"**{text}**", "",
         f"Semilla `{result['semilla']}`, {with_it['chunks']} chunks por pasada ({', '.join(result['zonas'])}), "
         f"mediana de {with_it['pasadas']} pasadas por configuración; {result.get('maquina', '')}.", "",
         "| | sin Heraldia | con Heraldia | diferencia |", "|---|---:|---:|---:|"]
    def row(name, a, b, fmt="{:.1f}"):
        d = "—" if a is None or b is None or not a else f"{b / a - 1:+.0%}"
        L.append(f"| {name} | {_f(a, fmt)} | {_f(b, fmt)} | {d} |")
    row("CPU del servidor, ms por chunk", sin.get("cpu_ms_por_chunk"), with_it.get("cpu_ms_por_chunk"))
    for k, n in (("media_ms", "ms por chunk (media, sin luz)"), ("p50_ms", "ms por chunk p50"), ("p90_ms", "ms por chunk p90"),
                 ("p99_ms", "ms por chunk p99"), ("max_ms", "ms por chunk máx.")):
        row(n, sin["ms_por_chunk"][k], with_it["ms_por_chunk"][k])
    row("pasos de estructuras, ms por chunk", sin["ms_por_chunk"].get("estructuras_ms"), with_it["ms_por_chunk"].get("estructuras_ms"), "{:.2f}")
    row("contando la luz, ms por chunk", sin["ms_por_chunk"].get("con_luz_ms"), with_it["ms_por_chunk"].get("con_luz_ms"))
    row("tiempo de generación (s)", sin["segundos"], with_it["segundos"])
    row("chunks/s", sin["chunks_por_s"], with_it["chunks_por_s"])
    for k in ("media", "p90", "p99", "max"):
        row(f"MSPT {k} (ms)", sin["mspt"].get(k), with_it["mspt"].get(k))
    row("memoria tras GC, máx. (MB)", sin["memoria_mb"], with_it["memoria_mb"], "{:.0f}")
    L += ["", "**Por paso de generación** (ms por chunk)", "", "| paso | sin | con | diferencia |", "|---|---:|---:|---:|"]
    for k in sorted(set(sin["pasos_ms"]) | set(with_it["pasos_ms"]), key=lambda k: -(with_it["pasos_ms"].get(k) or 0)):
        row(k.replace("minecraft:", ""), sin["pasos_ms"].get(k), with_it["pasos_ms"].get(k), "{:.2f}")
    L += ["", "**Por zona** (ms por chunk, media)", "", "| zona | sin | con | diferencia |", "|---|---:|---:|---:|"]
    for k in with_it["zonas_ms"]:
        row(k, sin["zonas_ms"].get(k), with_it["zonas_ms"].get(k))
    L += ["", "**/locate** (ms, desde " + ", ".join(map(str, result.get("locate_desde", LOCATE_FROM))) + ")", "",
          "| estructura | sin | con |", "|---|---:|---:|"]
    for k in sorted(set(sin["locate_ms"]) | set(with_it["locate_ms"])):
        L.append(f"| {k} | {_f(sin['locate_ms'].get(k), '{:.0f}')} | {_f(with_it['locate_ms'].get(k), '{:.0f}')} |")
    profile = result.get("perfil") or {}
    if profile:
        L += ["", "**Perfil de Heraldia** (`-Dheraldia.perfil=true`, mediana de las pasadas; incluye las búsquedas de /locate). "
              "Los tramos se solapan: `reglas` y `reglas_locate` contienen `medianas`, `minas`, `zona_ajenas` y "
              "`separacion_unicas`, y la regla de las minas mira si salen las vecinas (con su `ladera`).", "",
              "| tramo | veces | total (ms) | media (µs) | máx. (µs) |", "|---|---:|---:|---:|---:|"]
        for k, v in sorted(profile.items(), key=lambda kv: -kv[1]["total_ms"]):
            L.append(f"| {k} | {v['n']:.0f} | {v['total_ms']:.1f} | {v['media_us']:.1f} | {v['max_us']:.0f} |")
    L += ["", "Referencia: `tools/smoke/cost_reference.json` (cómo actualizarla: docs/DEVELOPMENT.md, «Coste de generación»)."]
    return "\n".join(L) + "\n"


def medium_profile(profiles):
    """Field-by-field median of the Heraldia profiles from several passes ({section: {n, total_ms, media_us, max_us}})."""
    out = {}
    for t in sorted({t for p in profiles for t in p}):
        vs = [p[t] for p in profiles if t in p]
        out[t] = {k: medium([v[k] for v in vs]) for k in ("n", "total_ms", "media_us", "max_us")}
    return out


def last_profile(text):
    m = None
    for line in text.splitlines():
        m = _PROFILE.search(line) or m
    return json.loads(m.group(1)) if m else None


def mspt_of(summary):
    """MSPT from the /jfr summary (serverTick): mean, p50, p90, p99 and max in ms."""
    t = (summary or {}).get("serverTick") or {}
    return {"media": t.get("averageMs"), "p50": t.get("p50"), "p90": t.get("p90"), "p99": t.get("p99"), "max": t.get("maxMs")}


def memory_of(heap_events):
    """Maximum heapUsed (MB) after each GC from the jdk.GCHeapSummary events of `jfr print --json`."""
    v = [e["values"]["heapUsed"] for e in heap_events if e["values"].get("when") == "After GC"]
    return max(v) / 2 ** 20 if v else None


# ---------------------------------------------------------------- servidor

def jfr_cli():
    home = os.environ.get("JAVA_HOME")
    for c in ([os.path.join(home, "bin", "jfr")] if home else []) + [shutil.which("jfr")]:
        if c and os.path.isfile(c):
            return c
    java = shutil.which("java")
    c = os.path.join(os.path.dirname(os.path.realpath(java)), "jfr") if java else None
    if c and os.path.isfile(c):
        return c
    raise SystemExit("could not find the JDK's jfr tool (JAVA_HOME/bin/jfr)")


def read_jfr_events(fname, kind):
    out = subprocess.run([jfr_cli(), "print", "--json", "--events", kind, fname], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def chunky(ctx, name, x, z, r):
    """Generates with Chunky the square of half side r at (x, z): (chunks reported by Chunky, wall-clock seconds)."""
    ctx.run(f"chunky center {x} {z}", r"[Cc]enter|Chunky")
    ctx.run(f"chunky radius {r}", r"[Rr]adius|Chunky")
    s.pending(ctx.lines, ctx.seen)
    t0 = time.monotonic()
    s.send(ctx.proc, "chunky start")
    m = s.wait_for(ctx.lines, _CHUNKY_END.pattern + r"|Task (?:already|not) |[Cc]onfirm", CHUNKY_TIMEOUT_S, ctx.seen)
    if not m.group(0).startswith("Task finished"):
        if "onfirm" in m.group(0):
            s.send(ctx.proc, "chunky confirm")
            m = s.wait_for(ctx.lines, _CHUNKY_END.pattern, CHUNKY_TIMEOUT_S, ctx.seen)
        else:
            raise SystemExit(f"Chunky did not start at {name}: {m.string.strip()}")
    return int(m.group(2)), time.monotonic() - t0


def locate(ctx, target):
    """ms that /locate takes (as reported by the game itself: "Locating element ... took N ms"), or None if it finds nothing.
    The timing line and the reply may arrive in either order."""
    s.pending(ctx.lines, ctx.seen)
    s.send(ctx.proc, f"execute positioned {LOCATE_FROM[0]} 64 {LOCATE_FROM[1]} run locate structure {target}")
    ms, answer = None, None
    while ms is None or answer is None:
        m = s.wait_for(ctx.lines, _LOCATE.pattern + r"|is at \[|Could not find|" + s.ERROR_PATTERN, s.COMMAND_TIMEOUT_S, ctx.seen)
        if m.group(0).startswith("Locating element"):
            ms = int(m.group(2))
        elif m.group(0).startswith("is at"):
            answer = True
        else:
            return None
    return ms


def sweep(work, jar, with_it, launcher):
    """One pass in a new world (with or without Heraldia): dict with the measurements."""
    for d in ("world", "logs", "debug"):
        shutil.rmtree(os.path.join(work, d), ignore_errors=True)
    mods = os.path.join(work, "mods")
    own_item = os.path.join(mods, os.path.basename(jar))
    if with_it and not os.path.isfile(own_item):
        shutil.copy(jar, mods)
    if not with_it and os.path.isfile(own_item):
        os.remove(own_item)
    jvm = ["java", f"-Xmx{XMX}", f"-Xms{XMX}"] + (["-Dheraldia.perfil=true"] if with_it else [])
    proc = subprocess.Popen(jvm + ["-jar", launcher, "nogui"], cwd=work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    measurements = {"con": with_it}
    try:
        s.wait_for(lines, r"Done \([\d.,]+s\)!", s.START_TIMEOUT_S, seen)
        if with_it and "Heraldia: perfil de la generación activado" not in ctx.log():
            raise SystemExit("with Heraldia but without its profile: was the mod not loaded?")
        if not with_it and re.search(r"Heraldia: \d+ estructuras registradas", ctx.log()):
            raise SystemExit("the pass without Heraldia loaded Heraldia")
        chunky(ctx, *WARMUP)
        ctx.run("jfr start", r"[Ss]tarted flight recorder|JFR profiling started|already")
        seconds, cpu = 0.0, 0.0
        for name, x, z, r in ZONES:
            c0 = process_cpu(proc.pid)
            n, t = chunky(ctx, name, x, z, r)
            c1 = process_cpu(proc.pid)
            cpu = None if c0 is None or c1 is None or cpu is None else cpu + c1 - c0
            c = chunks_of_zone(x, z, r)
            if n != (c[2] - c[0] + 1) * (c[3] - c[1] + 1):
                raise SystemExit(f"Chunky generated {n} chunks at {name}; the measured zone has {(c[2] - c[0] + 1) * (c[3] - c[1] + 1)}")
            seconds += t
        m = ctx.run("jfr stop", _JFR_END.pattern)
        fname = os.path.join(work, m.group(1))
        summary = s.wait_for(lines, _JFR_SUMMARY.pattern, 120, seen)
        with open(os.path.join(work, summary.group(1)), encoding="utf-8") as f:
            measurements["mspt"] = mspt_of(json.load(f))
        measurements["locate_ms"] = {}
        for name, target, only_with in LOCATES:
            if only_with and not with_it:
                continue
            ms = locate(ctx, target)
            if ms is None:
                print(f"WARNING: /locate {target} finds nothing from {LOCATE_FROM}")
            else:
                measurements["locate_ms"][name] = ms
    finally:
        if proc.poll() is None:
            try:
                s.send(proc, "stop")
                proc.wait(timeout=180)
            except (subprocess.TimeoutExpired, BrokenPipeError):
                proc.kill()
    s.pending(lines, seen)       # what the server wrote when stopping (Heraldia's profile is in there)
    log = os.path.join(work, "logs", "latest.log")
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else "".join(seen)
    measurements["perfil"] = last_profile(text) if with_it else None
    if with_it and measurements["perfil"] is None:
        raise SystemExit("with Heraldia, 'Heraldia: perfil: {...}' does not appear in the log on stop")
    events = jfr_chunk_events(read_jfr_events(fname, "minecraft.ChunkGeneration"))
    measurements["memoria_mb"] = memory_of(read_jfr_events(fname, "jdk.GCHeapSummary")["recording"]["events"])
    zones = {n: chunks_summary(events, chunks_of_zone(x, z, r)) for n, x, z, r in ZONES}
    # the keys are those of generation_cost.json and cost_reference.json: they stay as they are
    measurements.update(chunks=sum(v["chunks"] for v in zones.values()), segundos=seconds, zonas=zones,
                        ms_por_chunk=join_zones(events, zones))
    total, v = measurements["chunks"], [measurements["ms_por_chunk"]["media_ms"]]
    measurements["cpu_ms_por_chunk"] = cpu * 1000 / total if cpu is not None else None
    print(f"PASADA {'con' if with_it else 'sin'} Heraldia: {total} chunks en {seconds:.1f} s, "
          f"CPU {_f(measurements['cpu_ms_por_chunk'])} ms por chunk, {v[0]:.1f} ms por chunk en los pasos "
          f"(p50 {_f(measurements['ms_por_chunk']['p50_ms'])}, p99 {_f(measurements['ms_por_chunk']['p99_ms'])}), "
          f"MSPT medio {_f(measurements['mspt']['media'])}, locate {measurements['locate_ms']}", flush=True)
    return measurements


def measure(jar, work, sweeps):
    """Alternating passes (without, with, without, with...) in `work`: (list without, list with)."""
    os.makedirs(work, exist_ok=True)
    launcher = s.prepare(work, jar, s.gradle_properties())
    with open(os.path.join(work, "server.properties"), encoding="utf-8") as f:
        props = re.sub(r"level-seed=.*", f"level-seed={SEED}", f.read())
    with open(os.path.join(work, "server.properties"), "w", encoding="utf-8") as f:
        f.write(props)
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(CONFIG, f)
    modrinth.install(work, ["chunky"])
    sin, with_it = [], []
    for i in range(sweeps):
        sin.append(sweep(work, jar, False, launcher))
        with_it.append(sweep(work, jar, True, launcher))
    return sin, with_it


def result_of(sin, with_it):
    import platform
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=s.ROOT, capture_output=True, text=True).stdout.strip()
    r = {"semilla": SEED, "zonas": [f"{n} ({x}, {z}) {side(x, r)}×{side(z, r)} chunks" for n, x, z, r in ZONES],
         "locate_desde": list(LOCATE_FROM), "fecha": time.strftime("%Y-%m-%d"), "commit": commit,
         "maquina": f"{os.cpu_count()} núcleos, {platform.system()}" + (" (CI)" if os.environ.get("GITHUB_ACTIONS") else ""),
         "sin": add_entry(sin), "con": add_entry(with_it), "perfil": medium_profile([p["perfil"] for p in with_it if p.get("perfil")]),
         "crudo": {"sin": sin, "con": with_it}}
    r["sobrecoste"] = overcost(r["con"], r["sin"])
    return r


def read_reference(route=REFERENCE):
    if not os.path.isfile(route):
        return None
    with open(route, encoding="utf-8") as f:
        return json.load(f)


def write(result, comparison, output):
    os.makedirs(output, exist_ok=True)
    result = dict(result, comparacion={"ok": comparison[0], "limite": comparison[1], "texto": comparison[2]})
    with open(os.path.join(output, "coste_generacion.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, default=list)
    md = markdown(result, comparison)
    with open(os.path.join(output, "coste_generacion.md"), "w", encoding="utf-8") as f:
        f.write(md)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(md)
    return md


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jar")
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-coste"))
    ap.add_argument("--sweeps", type=int, default=SWEEPS, help=f"passes per configuration (default {SWEEPS})")
    ap.add_argument("--output", default=os.path.join(s.ROOT, "build", "coste"), help="folder for the JSON and the Markdown")
    ap.add_argument("--reference", default=REFERENCE)
    ap.add_argument("--update-reference", action="store_true", help="saves the measurement as the new reference")
    ap.add_argument("--no-threshold", action="store_true", help="measures and reports, but does not fail on the threshold")
    ap.add_argument("--no-retry", action="store_true", help="if it exceeds the threshold, does not repeat another round of passes")
    ap.add_argument("--from-json", help="does not measure: uses this coste_generacion.json (e.g. the CI artifact)")
    a = ap.parse_args(argv)
    ref = read_reference(a.reference)
    if a.from_json:
        with open(a.from_json, encoding="utf-8") as f:
            res = json.load(f)
    else:
        if not a.jar:
            ap.error("--jar is required (or --from-json)")
        jar, work = os.path.abspath(a.jar), os.path.abspath(a.work)
        sin, with_it = measure(jar, work, a.sweeps)
        res = result_of(sin, with_it)
        comp = compare(res["sobrecoste"], ref)
        if not comp[0] and ref and not a.no_retry and not a.update_reference:
            print(f"{comp[2]}: a round of {a.sweeps} passes is repeated and the decision is made with all of them", flush=True)
            without_it2, with_it2 = measure(jar, work, a.sweeps)
            res = result_of(sin + without_it2, with_it + with_it2)
    comp = compare(res["sobrecoste"], ref)
    if a.update_reference:
        new_one = new_reference(res, ref)
        with open(a.reference, "w", encoding="utf-8") as f:
            json.dump(new_one, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"referencia guardada en {a.reference}: sobrecoste {new_one['sobrecoste']:+.1%}")
        comp = compare(res["sobrecoste"], new_one)
    md = write(res, comp, a.output)
    print(md)
    print("COSTE:", comp[2])
    return 0 if comp[0] or a.no_threshold else 1


if __name__ == "__main__":
    sys.exit(main())
