"""Coste de generación de Heraldia: la misma zona del mismo mundo generada con el mod y sin él, y su comparación con la
referencia guardada en el repositorio (tools/smoke/cost_reference.json).

Uso:
  python3 tools/smoke/generation_cost.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
  python3 tools/smoke/generation_cost.py ... --update-reference     # mide y guarda la referencia nueva
  python3 tools/smoke/generation_cost.py --from-json build/coste/coste_generacion.json [--update-reference]
      # rehace el resumen (o la referencia) de una medición ya hecha, p. ej. el artefacto «coste-generacion» de la CI

Cada pasada arranca un servidor dedicado 26.3 nuevo (mundo borrado, semilla fija SEMILLA, Fabric API y Chunky), una
vez con el .jar de Heraldia (configuración por defecto y -Dheraldia.perfil=true) y otra sin él, alternando. En cada
una: Chunky genera una zona de calentamiento (no cuenta), luego las ZONAS con el perfilador de Minecraft activo
(/jfr start ... /jfr stop) y al final se mide /locate de LOCATES. Del .jfr salen, por chunk de las zonas, la suma del
tiempo de cada paso de generación (evento minecraft.ChunkGeneration): ms por chunk (media, p50, p90, p99, máx.) y por
paso; del resumen de /jfr, el MSPT (ms por tick) y la memoria; del log, el tiempo de cada /locate y el perfil propio de
Heraldia (comun/Perfil.java: caminos, ladera, orilla, medianas, minas, zona de ajenas...).

Sobrecoste = mediana de las pasadas con Heraldia / mediana sin ella - 1, en CPU del proceso del servidor por chunk
(/proc/<pid>/stat mientras Chunky genera las zonas: no crece con la espera entre hilos, que sí infla la duración de los
pasos de JFR, ±15 % entre pasadas iguales). Sin /proc (fuera de Linux), con la suma de los pasos de JFR por chunk sin
los de luz (que son sobre todo espera en la cola del motor de luz). El cociente quita la velocidad de la máquina.
Falla si pasa de referencia × (1 + umbral_relativo) + margen_absoluto (los dos en la referencia). Si falla, repite
una ronda de pasadas y decide con todas (el ruido de la CI). Escribe <salida>/coste_generacion.json y
<salida>/coste_generacion.md, y el Markdown también en $GITHUB_STEP_SUMMARY si existe. Código 0 si pasa.
Las funciones puras se prueban en tools/gen/tests/test_generation_cost.py.
"""
import argparse, json, math, os, queue, re, shutil, statistics, subprocess, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import modrinth

REFERENCE = os.path.join(s.ROOT, "tools", "smoke", "cost_reference.json")
SEED = "heraldia"
# (nombre, x, z, medio lado en bloques): cuadrados de chunks enteros que Chunky genera. Lejos entre sí (más de
# MARGEN_CHUNKS chunks) para que cada evento caiga en una sola zona. «aldea»: la aldea más cercana al 0,0 con la
# configuración por defecto (pantano, 32 -1344) y el arranque de sus caminos; «origen»: el 0,0 (sin aldea de Heraldia).
ZONES = [("aldea", 32, -1344, 160), ("origen", 0, 0, 160)]
WARMUP = ("calentamiento", 6000, 6000, 64)
MARGIN_CHUNKS = 12         # chunks alrededor de una zona que genera de paso (pasos previos de los vecinos)
# Pasos de luz: su duración es sobre todo la espera en la cola del motor de luz (un solo hilo), no trabajo de la
# generación, y es lo más ruidoso (±15 % entre pasadas iguales). No cuentan en el ms por chunk; se informan aparte.
LIGHT_STEPS = {"minecraft:initialize_light", "minecraft:light"}
# Pasos donde trabaja el código de estructuras (reglas de colocación, inicios, piezas y rasgos como los caminos).
STRUCTURE_STEPS = {"minecraft:structure_starts", "minecraft:structure_references", "minecraft:features"}
# /locate medidos al final de cada pasada, desde LOCATE_DESDE: (nombre, objetivo, solo con Heraldia)
LOCATE_FROM = (8000, -8000)
LOCATES = [("aldea", "#heraldia:aldeas", True), ("unica", "heraldia:unicas/castillo", True),
           ("mediana", "#heraldia:medianas", True), ("mina", "#heraldia:minas", True),
           ("aldea_vanilla", "#minecraft:village", False)]
SWEEPS = 3
# Configuración de Heraldia: la de por defecto (la del servidor de verdad), salvo la arena de oleadas, que en un mundo
# nuevo se construye sola junto al spawn (una obra de un chunk por tick, en el hilo del servidor, justo mientras se
# mide): no es coste de generación y en el mundo ya existente del servidor no se genera.
CONFIG = {"arena": {"generar_en_mundos_nuevos": False}}
XMX = "3G"
CHUNKY_TIMEOUT_S = 900
_CHUNKY_END = re.compile(r"Task finished for (\S+)\. Processed: (\d+) chunks")
_LOCATE = re.compile(r"Locating element (\S+) .*?took (\d+) ms")
_PROFILE = re.compile(r"Heraldia: perfil: (\{.*\})\s*$")
_JFR_END = re.compile(r"Dumped flight recorder profiling to (\S+\.jfr)")
_JFR_SUMMARY = re.compile(r"Dumped recording summary to (\S+\.json)")


# ---------------------------------------------------------------- funciones puras (tests en test_coste_generacion.py)

def percentile(values, p):
    """Percentil p (0-100) con interpolación lineal entre rangos (como numpy «linear»); None si no hay valores."""
    v = sorted(values)
    if not v:
        return None
    k = (len(v) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def duration_ms(text):
    """Duración de `jfr print --json` («PT0.000610953S», «PT1M2.5S», «PT0S») en ms."""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", text)
    if not m:
        raise ValueError(f"duración de JFR no reconocida: {text!r}")
    h, mi, se = (float(g) if g else 0.0 for g in m.groups())
    return (h * 3600 + mi * 60 + se) * 1000


def chunks_of_zone(x, z, r):
    """(cx0, cz0, cx1, cz1) de los chunks que Chunky genera en el cuadrado de medio lado r centrado en (x, z): los de
    x - r a x + r, ambos incluidos (centro 0,0 y radio 128: 17 × 17 = 289 chunks, lo que dice «Processed»)."""
    return ((x - r) >> 4, (z - r) >> 4, (x + r) >> 4, (z + r) >> 4)


def side(c, r):
    return ((c + r) >> 4) - ((c - r) >> 4) + 1


def inside(c, box, margin=0):
    cx, cz = c
    return box[0] - margin <= cx <= box[2] + margin and box[1] - margin <= cz <= box[3] + margin


def chunks_summary(events, box, margin=MARGIN_CHUNKS):
    """De los eventos [(cx, cz, paso, ms)], los de la zona (caja de chunks y su margen), sin los PASOS_LUZ: por chunk de
    la caja, la suma de sus pasos (p50, p90, p99, máx.); la media reparte entre los chunks de la caja todo lo de la zona y
    su margen (los vecinos generan pasos previos por ella). `pasos_ms`, lo mismo por paso (con los de luz);
    `estructuras_ms`, la parte de PASOS_ESTRUCTURAS; `con_luz_ms`, la media contando la luz."""
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
    """ms por chunk de todas las zonas juntas: medias ponderadas por chunks y percentiles sobre todos los chunks (sin luz)."""
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
    """Segundos de CPU (usuario + sistema) de una línea de /proc/<pid>/stat (el nombre del proceso va entre paréntesis
    y puede llevar espacios: se corta tras el último «)»)."""
    fields = line.rpartition(")")[2].split()
    return (int(fields[11]) + int(fields[12])) / hz


def process_cpu(pid):
    """CPU (s) que lleva gastada el proceso, o None si no hay /proc (fuera de Linux)."""
    try:
        with open(f"/proc/{pid}/stat", encoding="ascii") as f:
            return cpu_of_stat(f.read(), os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        return None


def jfr_chunk_events(dataset):
    """[(cx, cz, paso, ms)] de los minecraft.ChunkGeneration de `jfr print --json` (ya leído)."""
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
    """Mediana de las pasadas de una configuración (cada una, un dict de medidas de pasada()) campo a campo."""
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
    """La medida que decide: la CPU del proceso por chunk si se pudo leer (lo más estable: no crece con la espera entre
    hilos), si no la suma de los pasos de JFR por chunk (sin luz)."""
    return aggregate.get("cpu_ms_por_chunk") or aggregate["ms_por_chunk"]["media_ms"]


def overcost(with_it, sin):
    """Sobrecoste relativo de Heraldia (0,12 = un 12 % más que sin ella) en la misma medida para las dos (metrica());
    None si falta algo."""
    if not with_it or not sin:
        return None
    if with_it.get("cpu_ms_por_chunk") and sin.get("cpu_ms_por_chunk"):
        return with_it["cpu_ms_por_chunk"] / sin["cpu_ms_por_chunk"] - 1
    if not sin["ms_por_chunk"]["media_ms"]:
        return None
    return with_it["ms_por_chunk"]["media_ms"] / sin["ms_por_chunk"]["media_ms"] - 1


def compare(current, reference):
    """(ok, límite, texto) del sobrecoste actual frente a la referencia: falla si pasa de
    ref × (1 + umbral_relativo) + margen_absoluto. Sin referencia (o sin medida) pasa, y lo dice."""
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
    """La referencia que se guarda a partir de una medición (conserva umbral y margen de la anterior)."""
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
    """Resumen en Markdown (para el job de la CI y el artefacto)."""
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
    """Mediana campo a campo de los perfiles de Heraldia de varias pasadas ({tramo: {n, total_ms, media_us, max_us}})."""
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
    """MSPT del resumen de /jfr (serverTick): media, p50, p90, p99 y máx. en ms."""
    t = (summary or {}).get("serverTick") or {}
    return {"media": t.get("averageMs"), "p50": t.get("p50"), "p90": t.get("p90"), "p99": t.get("p99"), "max": t.get("maxMs")}


def memory_of(heap_events):
    """Máximo de heapUsed (MB) tras cada GC de los jdk.GCHeapSummary de `jfr print --json`."""
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
    raise SystemExit("no encuentro la herramienta jfr del JDK (JAVA_HOME/bin/jfr)")


def read_jfr_events(fname, kind):
    out = subprocess.run([jfr_cli(), "print", "--json", "--events", kind, fname], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def chunky(ctx, name, x, z, r):
    """Genera con Chunky el cuadrado de medio lado r en (x, z): (chunks que dice Chunky, segundos de reloj)."""
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
            raise SystemExit(f"Chunky no empezó en {name}: {m.string.strip()}")
    return int(m.group(2)), time.monotonic() - t0


def locate(ctx, target):
    """ms que tarda /locate (lo que dice el propio juego: «Locating element ... took N ms»), o None si no encuentra nada.
    La línea del tiempo y la respuesta pueden llegar en cualquier orden."""
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
    """Una pasada en un mundo nuevo (con o sin Heraldia): dict con las medidas."""
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
            raise SystemExit("con Heraldia y sin su perfil: ¿no se cargó el mod?")
        if not with_it and re.search(r"Heraldia: \d+ estructuras registradas", ctx.log()):
            raise SystemExit("la pasada sin Heraldia ha cargado Heraldia")
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
                raise SystemExit(f"Chunky generó {n} chunks en {name}; la zona medida tiene {(c[2] - c[0] + 1) * (c[3] - c[1] + 1)}")
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
                print(f"AVISO: /locate {target} no encuentra nada desde {LOCATE_FROM}")
            else:
                measurements["locate_ms"][name] = ms
    finally:
        if proc.poll() is None:
            try:
                s.send(proc, "stop")
                proc.wait(timeout=180)
            except (subprocess.TimeoutExpired, BrokenPipeError):
                proc.kill()
    s.pending(lines, seen)       # lo que el servidor escribió al parar (el perfil de Heraldia va ahí)
    log = os.path.join(work, "logs", "latest.log")
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else "".join(seen)
    measurements["perfil"] = last_profile(text) if with_it else None
    if with_it and measurements["perfil"] is None:
        raise SystemExit("con Heraldia no aparece «Heraldia: perfil: {...}» en el log al parar")
    events = jfr_chunk_events(read_jfr_events(fname, "minecraft.ChunkGeneration"))
    measurements["memoria_mb"] = memory_of(read_jfr_events(fname, "jdk.GCHeapSummary")["recording"]["events"])
    zones = {n: chunks_summary(events, chunks_of_zone(x, z, r)) for n, x, z, r in ZONES}
    measurements.update(chunks=sum(v["chunks"] for v in zones.values()), seconds=seconds, zones=zones,
                   ms_per_chunk=join_zones(events, zones))
    total, v = measurements["chunks"], [measurements["ms_por_chunk"]["media_ms"]]
    measurements["cpu_ms_por_chunk"] = cpu * 1000 / total if cpu is not None else None
    print(f"PASADA {'con' if with_it else 'sin'} Heraldia: {total} chunks en {seconds:.1f} s, "
          f"CPU {_f(measurements['cpu_ms_por_chunk'])} ms por chunk, {v[0]:.1f} ms por chunk en los pasos "
          f"(p50 {_f(measurements['ms_por_chunk']['p50_ms'])}, p99 {_f(measurements['ms_por_chunk']['p99_ms'])}), "
          f"MSPT medio {_f(measurements['mspt']['media'])}, locate {measurements['locate_ms']}", flush=True)
    return measurements


def measure(jar, work, sweeps):
    """Pasadas alternas (sin, con, sin, con...) en `work`: (lista sin, lista con)."""
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
    ap.add_argument("--sweeps", type=int, default=SWEEPS, help=f"pasadas por configuración (por defecto {SWEEPS})")
    ap.add_argument("--output", default=os.path.join(s.ROOT, "build", "coste"), help="carpeta del JSON y el Markdown")
    ap.add_argument("--reference", default=REFERENCE)
    ap.add_argument("--update-reference", action="store_true", help="guarda la medición como referencia nueva")
    ap.add_argument("--no-threshold", action="store_true", help="mide e informa, pero no falla por el umbral")
    ap.add_argument("--no-retry", action="store_true", help="si pasa del umbral, no repite otra ronda de pasadas")
    ap.add_argument("--from-json", help="no mide: usa este coste_generacion.json (p. ej. el artefacto de la CI)")
    a = ap.parse_args(argv)
    ref = read_reference(a.reference)
    if a.from_json:
        with open(a.from_json, encoding="utf-8") as f:
            res = json.load(f)
    else:
        if not a.jar:
            ap.error("--jar es obligatorio (o --from-json)")
        jar, work = os.path.abspath(a.jar), os.path.abspath(a.work)
        sin, with_it = measure(jar, work, a.sweeps)
        res = result_of(sin, with_it)
        comp = compare(res["sobrecoste"], ref)
        if not comp[0] and ref and not a.no_retry and not a.update_reference:
            print(f"{comp[2]}: se repite una ronda de {a.sweeps} pasadas y se decide con todas", flush=True)
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
