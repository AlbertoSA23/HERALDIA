"""Coste de generación de Heraldia: la misma zona del mismo mundo generada con el mod y sin él, y su comparación con la
referencia guardada en el repositorio (tools/smoke/coste_referencia.json).

Uso:
  python3 tools/smoke/coste_generacion.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
  python3 tools/smoke/coste_generacion.py ... --actualizar-referencia     # mide y guarda la referencia nueva
  python3 tools/smoke/coste_generacion.py --desde build/coste/coste_generacion.json [--actualizar-referencia]
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
Las funciones puras se prueban en tools/gen/tests/test_coste_generacion.py.
"""
import argparse, json, math, os, queue, re, shutil, statistics, subprocess, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import modrinth

REFERENCIA = os.path.join(s.ROOT, "tools", "smoke", "coste_referencia.json")
SEMILLA = "heraldia"
# (nombre, x, z, medio lado en bloques): cuadrados de chunks enteros que Chunky genera. Lejos entre sí (más de
# MARGEN_CHUNKS chunks) para que cada evento caiga en una sola zona. «aldea»: la aldea más cercana al 0,0 con la
# configuración por defecto (pantano, 32 -1344) y el arranque de sus caminos; «origen»: el 0,0 (sin aldea de Heraldia).
ZONAS = [("aldea", 32, -1344, 160), ("origen", 0, 0, 160)]
CALENTAMIENTO = ("calentamiento", 6000, 6000, 64)
MARGEN_CHUNKS = 12         # chunks alrededor de una zona que genera de paso (pasos previos de los vecinos)
# Pasos de luz: su duración es sobre todo la espera en la cola del motor de luz (un solo hilo), no trabajo de la
# generación, y es lo más ruidoso (±15 % entre pasadas iguales). No cuentan en el ms por chunk; se informan aparte.
PASOS_LUZ = {"minecraft:initialize_light", "minecraft:light"}
# Pasos donde trabaja el código de estructuras (reglas de colocación, inicios, piezas y rasgos como los caminos).
PASOS_ESTRUCTURAS = {"minecraft:structure_starts", "minecraft:structure_references", "minecraft:features"}
# /locate medidos al final de cada pasada, desde LOCATE_DESDE: (nombre, objetivo, solo con Heraldia)
LOCATE_DESDE = (8000, -8000)
LOCATES = [("aldea", "#heraldia:aldeas", True), ("unica", "heraldia:unicas/castillo", True),
           ("mediana", "#heraldia:medianas", True), ("mina", "#heraldia:minas", True),
           ("aldea_vanilla", "#minecraft:village", False)]
PASADAS = 3
# Configuración de Heraldia: la de por defecto (la del servidor de verdad), salvo la arena de oleadas, que en un mundo
# nuevo se construye sola junto al spawn (una obra de un chunk por tick, en el hilo del servidor, justo mientras se
# mide): no es coste de generación y en el mundo ya existente del servidor no se genera.
CONFIG = {"arena": {"generar_en_mundos_nuevos": False}}
XMX = "3G"
CHUNKY_TIMEOUT_S = 900
_CHUNKY_FIN = re.compile(r"Task finished for (\S+)\. Processed: (\d+) chunks")
_LOCATE = re.compile(r"Locating element (\S+) .*?took (\d+) ms")
_PERFIL = re.compile(r"Heraldia: perfil: (\{.*\})\s*$")
_JFR_FIN = re.compile(r"Dumped flight recorder profiling to (\S+\.jfr)")
_JFR_RESUMEN = re.compile(r"Dumped recording summary to (\S+\.json)")


# ---------------------------------------------------------------- funciones puras (tests en test_coste_generacion.py)

def percentil(valores, p):
    """Percentil p (0-100) con interpolación lineal entre rangos (como numpy «linear»); None si no hay valores."""
    v = sorted(valores)
    if not v:
        return None
    k = (len(v) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def duracion_ms(texto):
    """Duración de `jfr print --json` («PT0.000610953S», «PT1M2.5S», «PT0S») en ms."""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", texto)
    if not m:
        raise ValueError(f"duración de JFR no reconocida: {texto!r}")
    h, mi, se = (float(g) if g else 0.0 for g in m.groups())
    return (h * 3600 + mi * 60 + se) * 1000


def chunks_de_zona(x, z, r):
    """(cx0, cz0, cx1, cz1) de los chunks que Chunky genera en el cuadrado de medio lado r centrado en (x, z): los de
    x - r a x + r, ambos incluidos (centro 0,0 y radio 128: 17 × 17 = 289 chunks, lo que dice «Processed»)."""
    return ((x - r) >> 4, (z - r) >> 4, (x + r) >> 4, (z + r) >> 4)


def lado(c, r):
    return ((c + r) >> 4) - ((c - r) >> 4) + 1


def dentro(c, caja, margen=0):
    cx, cz = c
    return caja[0] - margen <= cx <= caja[2] + margen and caja[1] - margen <= cz <= caja[3] + margen


def resumen_chunks(eventos, caja, margen=MARGEN_CHUNKS):
    """De los eventos [(cx, cz, paso, ms)], los de la zona (caja de chunks y su margen), sin los PASOS_LUZ: por chunk de
    la caja, la suma de sus pasos (p50, p90, p99, máx.); la media reparte entre los chunks de la caja todo lo de la zona y
    su margen (los vecinos generan pasos previos por ella). `pasos_ms`, lo mismo por paso (con los de luz);
    `estructuras_ms`, la parte de PASOS_ESTRUCTURAS; `con_luz_ms`, la media contando la luz."""
    por_chunk, pasos = {}, {}
    for cx, cz, paso, ms in eventos:
        if not dentro((cx, cz), caja, margen):
            continue
        pasos[paso] = pasos.get(paso, 0.0) + ms
        if paso not in PASOS_LUZ and dentro((cx, cz), caja):
            por_chunk[(cx, cz)] = por_chunk.get((cx, cz), 0.0) + ms
    n = (caja[2] - caja[0] + 1) * (caja[3] - caja[1] + 1)
    v = list(por_chunk.values())
    return {"chunks": n, "chunks_medidos": len(v), "media_ms": sum(ms for k, ms in pasos.items() if k not in PASOS_LUZ) / n,
            "p50_ms": percentil(v, 50), "p90_ms": percentil(v, 90), "p99_ms": percentil(v, 99), "max_ms": max(v, default=None),
            "estructuras_ms": sum(ms for k, ms in pasos.items() if k in PASOS_ESTRUCTURAS) / n,
            "con_luz_ms": sum(pasos.values()) / n, "pasos_ms": {k: pasos[k] / n for k in sorted(pasos)}}


def juntar_zonas(eventos, zonas):
    """ms por chunk de todas las zonas juntas: medias ponderadas por chunks y percentiles sobre todos los chunks (sin luz)."""
    total = sum(v["chunks"] for v in zonas.values())
    def pond(campo):
        return sum(z[campo] * z["chunks"] for z in zonas.values()) / total
    pasos = {}
    for z in zonas.values():
        for k, ms in z["pasos_ms"].items():
            pasos[k] = pasos.get(k, 0.0) + ms * z["chunks"] / total
    cajas = [chunks_de_zona(x, zz, r) for n, x, zz, r in ZONAS if n in zonas]
    por_chunk = {}
    for cx, cz, paso, ms in eventos:
        if paso not in PASOS_LUZ and any(dentro((cx, cz), c) for c in cajas):
            por_chunk[(cx, cz)] = por_chunk.get((cx, cz), 0.0) + ms
    pc = list(por_chunk.values())
    return {"media_ms": pond("media_ms"), "p50_ms": percentil(pc, 50), "p90_ms": percentil(pc, 90), "p99_ms": percentil(pc, 99),
            "max_ms": max(pc, default=None), "estructuras_ms": pond("estructuras_ms"), "con_luz_ms": pond("con_luz_ms"),
            "pasos_ms": pasos}


def cpu_de_stat(linea, hz=100):
    """Segundos de CPU (usuario + sistema) de una línea de /proc/<pid>/stat (el nombre del proceso va entre paréntesis
    y puede llevar espacios: se corta tras el último «)»)."""
    campos = linea.rpartition(")")[2].split()
    return (int(campos[11]) + int(campos[12])) / hz


def cpu_proceso(pid):
    """CPU (s) que lleva gastada el proceso, o None si no hay /proc (fuera de Linux)."""
    try:
        with open(f"/proc/{pid}/stat", encoding="ascii") as f:
            return cpu_de_stat(f.read(), os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        return None


def eventos_jfr(datos):
    """[(cx, cz, paso, ms)] de los minecraft.ChunkGeneration de `jfr print --json` (ya leído)."""
    out = []
    for e in datos["recording"]["events"]:
        v = e["values"]
        if e.get("type", "minecraft.ChunkGeneration") == "minecraft.ChunkGeneration" and v.get("level", "minecraft:overworld") == "minecraft:overworld":
            out.append((v["chunkPosX"], v["chunkPosZ"], v["status"], duracion_ms(v["duration"])))
    return out


def mediana(valores):
    v = [x for x in valores if x is not None]
    return statistics.median(v) if v else None


def agregar(pasadas):
    """Mediana de las pasadas de una configuración (cada una, un dict de medidas de pasada()) campo a campo."""
    if not pasadas:
        return None
    def med(f):
        return mediana([f(p) for p in pasadas])
    out = {"pasadas": len(pasadas),
           "ms_por_chunk": {k: med(lambda p, k=k: p["ms_por_chunk"].get(k)) for k in
                            ("media_ms", "p50_ms", "p90_ms", "p99_ms", "max_ms", "estructuras_ms", "con_luz_ms")},
           "segundos": med(lambda p: p["segundos"]), "chunks": pasadas[0]["chunks"],
           "cpu_ms_por_chunk": med(lambda p: p.get("cpu_ms_por_chunk")),
           "chunks_por_s": med(lambda p: p["chunks"] / p["segundos"] if p["segundos"] else None),
           "mspt": {k: med(lambda p, k=k: (p.get("mspt") or {}).get(k)) for k in ("media", "p50", "p90", "p99", "max")},
           "memoria_mb": med(lambda p: p.get("memoria_mb")),
           "locate_ms": {k: med(lambda p, k=k: p["locate_ms"].get(k)) for k in sorted({k for p in pasadas for k in p["locate_ms"]})}}
    pasos = sorted({k for p in pasadas for k in p["ms_por_chunk"]["pasos_ms"]})
    out["pasos_ms"] = {k: med(lambda p, k=k: p["ms_por_chunk"]["pasos_ms"].get(k, 0.0)) for k in pasos}
    zonas = sorted({k for p in pasadas for k in p["zonas"]})
    out["zonas_ms"] = {k: med(lambda p, k=k: p["zonas"][k]["media_ms"] if k in p["zonas"] else None) for k in zonas}
    return out


def metrica(agregado):
    """La medida que decide: la CPU del proceso por chunk si se pudo leer (lo más estable: no crece con la espera entre
    hilos), si no la suma de los pasos de JFR por chunk (sin luz)."""
    return agregado.get("cpu_ms_por_chunk") or agregado["ms_por_chunk"]["media_ms"]


def sobrecoste(con, sin):
    """Sobrecoste relativo de Heraldia (0,12 = un 12 % más que sin ella) en la misma medida para las dos (metrica());
    None si falta algo."""
    if not con or not sin:
        return None
    if con.get("cpu_ms_por_chunk") and sin.get("cpu_ms_por_chunk"):
        return con["cpu_ms_por_chunk"] / sin["cpu_ms_por_chunk"] - 1
    if not sin["ms_por_chunk"]["media_ms"]:
        return None
    return con["ms_por_chunk"]["media_ms"] / sin["ms_por_chunk"]["media_ms"] - 1


def comparar(actual, referencia):
    """(ok, límite, texto) del sobrecoste actual frente a la referencia: falla si pasa de
    ref × (1 + umbral_relativo) + margen_absoluto. Sin referencia (o sin medida) pasa, y lo dice."""
    if actual is None:
        return False, None, "no se pudo medir el sobrecoste"
    if not referencia or referencia.get("sobrecoste") is None:
        return True, None, f"sobrecoste {actual:+.1%} (sin referencia guardada: no se compara)"
    ref = referencia["sobrecoste"]
    limite = max(ref, 0.0) * (1 + referencia.get("umbral_relativo", 0.25)) + referencia.get("margen_absoluto", 0.08)
    ok = actual <= limite
    return ok, limite, (f"sobrecoste {actual:+.1%} frente a la referencia {ref:+.1%} (límite {limite:+.1%}): "
                        + ("dentro del margen" if ok else "REGRESIÓN"))


def referencia_nueva(resultado, anterior=None):
    """La referencia que se guarda a partir de una medición (conserva umbral y margen de la anterior)."""
    anterior = anterior or {}
    return {"sobrecoste": round(resultado["sobrecoste"], 4),
            "umbral_relativo": anterior.get("umbral_relativo", 0.25), "margen_absoluto": anterior.get("margen_absoluto", 0.08),
            "ms_por_chunk_con": round(metrica(resultado["con"]), 2), "ms_por_chunk_sin": round(metrica(resultado["sin"]), 2),
            "medida": "cpu" if resultado["con"].get("cpu_ms_por_chunk") and resultado["sin"].get("cpu_ms_por_chunk") else "jfr",
            "pasadas": resultado["con"]["pasadas"], "maquina": resultado.get("maquina", ""), "fecha": resultado.get("fecha", ""),
            "commit": resultado.get("commit", "")}


def _f(v, fmt="{:.1f}"):
    return "—" if v is None else fmt.format(v)


def markdown(resultado, comparacion):
    """Resumen en Markdown (para el job de la CI y el artefacto)."""
    con, sin = resultado["con"], resultado["sin"]
    ok, limite, texto = comparacion
    L = [f"## Coste de generación de Heraldia {'✅' if ok else '❌'}", "", f"**{texto}**", "",
         f"Semilla `{resultado['semilla']}`, {con['chunks']} chunks por pasada ({', '.join(resultado['zonas'])}), "
         f"mediana de {con['pasadas']} pasadas por configuración; {resultado.get('maquina', '')}.", "",
         "| | sin Heraldia | con Heraldia | diferencia |", "|---|---:|---:|---:|"]
    def fila(nombre, a, b, fmt="{:.1f}"):
        d = "—" if a is None or b is None or not a else f"{b / a - 1:+.0%}"
        L.append(f"| {nombre} | {_f(a, fmt)} | {_f(b, fmt)} | {d} |")
    fila("CPU del servidor, ms por chunk", sin.get("cpu_ms_por_chunk"), con.get("cpu_ms_por_chunk"))
    for k, n in (("media_ms", "ms por chunk (media, sin luz)"), ("p50_ms", "ms por chunk p50"), ("p90_ms", "ms por chunk p90"),
                 ("p99_ms", "ms por chunk p99"), ("max_ms", "ms por chunk máx.")):
        fila(n, sin["ms_por_chunk"][k], con["ms_por_chunk"][k])
    fila("pasos de estructuras, ms por chunk", sin["ms_por_chunk"].get("estructuras_ms"), con["ms_por_chunk"].get("estructuras_ms"), "{:.2f}")
    fila("contando la luz, ms por chunk", sin["ms_por_chunk"].get("con_luz_ms"), con["ms_por_chunk"].get("con_luz_ms"))
    fila("tiempo de generación (s)", sin["segundos"], con["segundos"])
    fila("chunks/s", sin["chunks_por_s"], con["chunks_por_s"])
    for k in ("media", "p90", "p99", "max"):
        fila(f"MSPT {k} (ms)", sin["mspt"].get(k), con["mspt"].get(k))
    fila("memoria tras GC, máx. (MB)", sin["memoria_mb"], con["memoria_mb"], "{:.0f}")
    L += ["", "**Por paso de generación** (ms por chunk)", "", "| paso | sin | con | diferencia |", "|---|---:|---:|---:|"]
    for k in sorted(set(sin["pasos_ms"]) | set(con["pasos_ms"]), key=lambda k: -(con["pasos_ms"].get(k) or 0)):
        fila(k.replace("minecraft:", ""), sin["pasos_ms"].get(k), con["pasos_ms"].get(k), "{:.2f}")
    L += ["", "**Por zona** (ms por chunk, media)", "", "| zona | sin | con | diferencia |", "|---|---:|---:|---:|"]
    for k in con["zonas_ms"]:
        fila(k, sin["zonas_ms"].get(k), con["zonas_ms"].get(k))
    L += ["", "**/locate** (ms, desde " + ", ".join(map(str, resultado.get("locate_desde", LOCATE_DESDE))) + ")", "",
          "| estructura | sin | con |", "|---|---:|---:|"]
    for k in sorted(set(sin["locate_ms"]) | set(con["locate_ms"])):
        L.append(f"| {k} | {_f(sin['locate_ms'].get(k), '{:.0f}')} | {_f(con['locate_ms'].get(k), '{:.0f}')} |")
    perfil = resultado.get("perfil") or {}
    if perfil:
        L += ["", "**Perfil de Heraldia** (`-Dheraldia.perfil=true`, mediana de las pasadas; incluye las búsquedas de /locate). "
              "Los tramos se solapan: `reglas` y `reglas_locate` contienen `medianas`, `minas`, `zona_ajenas` y "
              "`separacion_unicas`, y la regla de las minas mira si salen las vecinas (con su `ladera`).", "",
              "| tramo | veces | total (ms) | media (µs) | máx. (µs) |", "|---|---:|---:|---:|---:|"]
        for k, v in sorted(perfil.items(), key=lambda kv: -kv[1]["total_ms"]):
            L.append(f"| {k} | {v['n']:.0f} | {v['total_ms']:.1f} | {v['media_us']:.1f} | {v['max_us']:.0f} |")
    L += ["", "Referencia: `tools/smoke/coste_referencia.json` (cómo actualizarla: docs/DESARROLLO.md, «Coste de generación»)."]
    return "\n".join(L) + "\n"


def perfil_mediano(perfiles):
    """Mediana campo a campo de los perfiles de Heraldia de varias pasadas ({tramo: {n, total_ms, media_us, max_us}})."""
    out = {}
    for t in sorted({t for p in perfiles for t in p}):
        vs = [p[t] for p in perfiles if t in p]
        out[t] = {k: mediana([v[k] for v in vs]) for k in ("n", "total_ms", "media_us", "max_us")}
    return out


def ultimo_perfil(texto):
    m = None
    for linea in texto.splitlines():
        m = _PERFIL.search(linea) or m
    return json.loads(m.group(1)) if m else None


def mspt_de(resumen):
    """MSPT del resumen de /jfr (serverTick): media, p50, p90, p99 y máx. en ms."""
    t = (resumen or {}).get("serverTick") or {}
    return {"media": t.get("averageMs"), "p50": t.get("p50"), "p90": t.get("p90"), "p99": t.get("p99"), "max": t.get("maxMs")}


def memoria_de(eventos_heap):
    """Máximo de heapUsed (MB) tras cada GC de los jdk.GCHeapSummary de `jfr print --json`."""
    v = [e["values"]["heapUsed"] for e in eventos_heap if e["values"].get("when") == "After GC"]
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


def jfr_eventos(fichero, tipo):
    out = subprocess.run([jfr_cli(), "print", "--json", "--events", tipo, fichero], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def chunky(ctx, nombre, x, z, r):
    """Genera con Chunky el cuadrado de medio lado r en (x, z): (chunks que dice Chunky, segundos de reloj)."""
    ctx.run(f"chunky center {x} {z}", r"[Cc]enter|Chunky")
    ctx.run(f"chunky radius {r}", r"[Rr]adius|Chunky")
    s.pending(ctx.lines, ctx.seen)
    t0 = time.monotonic()
    s.send(ctx.proc, "chunky start")
    m = s.wait_for(ctx.lines, _CHUNKY_FIN.pattern + r"|Task (?:already|not) |[Cc]onfirm", CHUNKY_TIMEOUT_S, ctx.seen)
    if not m.group(0).startswith("Task finished"):
        if "onfirm" in m.group(0):
            s.send(ctx.proc, "chunky confirm")
            m = s.wait_for(ctx.lines, _CHUNKY_FIN.pattern, CHUNKY_TIMEOUT_S, ctx.seen)
        else:
            raise SystemExit(f"Chunky no empezó en {nombre}: {m.string.strip()}")
    return int(m.group(2)), time.monotonic() - t0


def locate(ctx, objetivo):
    """ms que tarda /locate (lo que dice el propio juego: «Locating element ... took N ms»), o None si no encuentra nada.
    La línea del tiempo y la respuesta pueden llegar en cualquier orden."""
    s.pending(ctx.lines, ctx.seen)
    s.send(ctx.proc, f"execute positioned {LOCATE_DESDE[0]} 64 {LOCATE_DESDE[1]} run locate structure {objetivo}")
    ms, respuesta = None, None
    while ms is None or respuesta is None:
        m = s.wait_for(ctx.lines, _LOCATE.pattern + r"|is at \[|Could not find|" + s.ERROR_PATTERN, s.COMMAND_TIMEOUT_S, ctx.seen)
        if m.group(0).startswith("Locating element"):
            ms = int(m.group(2))
        elif m.group(0).startswith("is at"):
            respuesta = True
        else:
            return None
    return ms


def pasada(work, jar, con, launcher):
    """Una pasada en un mundo nuevo (con o sin Heraldia): dict con las medidas."""
    for d in ("world", "logs", "debug"):
        shutil.rmtree(os.path.join(work, d), ignore_errors=True)
    mods = os.path.join(work, "mods")
    propio = os.path.join(mods, os.path.basename(jar))
    if con and not os.path.isfile(propio):
        shutil.copy(jar, mods)
    if not con and os.path.isfile(propio):
        os.remove(propio)
    jvm = ["java", f"-Xmx{XMX}", f"-Xms{XMX}"] + (["-Dheraldia.perfil=true"] if con else [])
    proc = subprocess.Popen(jvm + ["-jar", launcher, "nogui"], cwd=work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    medidas = {"con": con}
    try:
        s.wait_for(lines, r"Done \([\d.,]+s\)!", s.START_TIMEOUT_S, seen)
        if con and "Heraldia: perfil de la generación activado" not in ctx.log():
            raise SystemExit("con Heraldia y sin su perfil: ¿no se cargó el mod?")
        if not con and re.search(r"Heraldia: \d+ estructuras registradas", ctx.log()):
            raise SystemExit("la pasada sin Heraldia ha cargado Heraldia")
        chunky(ctx, *CALENTAMIENTO)
        ctx.run("jfr start", r"[Ss]tarted flight recorder|JFR profiling started|already")
        segundos, cpu = 0.0, 0.0
        for nombre, x, z, r in ZONAS:
            c0 = cpu_proceso(proc.pid)
            n, t = chunky(ctx, nombre, x, z, r)
            c1 = cpu_proceso(proc.pid)
            cpu = None if c0 is None or c1 is None or cpu is None else cpu + c1 - c0
            c = chunks_de_zona(x, z, r)
            if n != (c[2] - c[0] + 1) * (c[3] - c[1] + 1):
                raise SystemExit(f"Chunky generó {n} chunks en {nombre}; la zona medida tiene {(c[2] - c[0] + 1) * (c[3] - c[1] + 1)}")
            segundos += t
        m = ctx.run("jfr stop", _JFR_FIN.pattern)
        fichero = os.path.join(work, m.group(1))
        resumen = s.wait_for(lines, _JFR_RESUMEN.pattern, 120, seen)
        with open(os.path.join(work, resumen.group(1)), encoding="utf-8") as f:
            medidas["mspt"] = mspt_de(json.load(f))
        medidas["locate_ms"] = {}
        for nombre, objetivo, solo_con in LOCATES:
            if solo_con and not con:
                continue
            ms = locate(ctx, objetivo)
            if ms is None:
                print(f"AVISO: /locate {objetivo} no encuentra nada desde {LOCATE_DESDE}")
            else:
                medidas["locate_ms"][nombre] = ms
    finally:
        if proc.poll() is None:
            try:
                s.send(proc, "stop")
                proc.wait(timeout=180)
            except (subprocess.TimeoutExpired, BrokenPipeError):
                proc.kill()
    s.pending(lines, seen)       # lo que el servidor escribió al parar (el perfil de Heraldia va ahí)
    log = os.path.join(work, "logs", "latest.log")
    texto = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else "".join(seen)
    medidas["perfil"] = ultimo_perfil(texto) if con else None
    if con and medidas["perfil"] is None:
        raise SystemExit("con Heraldia no aparece «Heraldia: perfil: {...}» en el log al parar")
    eventos = eventos_jfr(jfr_eventos(fichero, "minecraft.ChunkGeneration"))
    medidas["memoria_mb"] = memoria_de(jfr_eventos(fichero, "jdk.GCHeapSummary")["recording"]["events"])
    zonas = {n: resumen_chunks(eventos, chunks_de_zona(x, z, r)) for n, x, z, r in ZONAS}
    medidas.update(chunks=sum(v["chunks"] for v in zonas.values()), segundos=segundos, zonas=zonas,
                   ms_por_chunk=juntar_zonas(eventos, zonas))
    total, v = medidas["chunks"], [medidas["ms_por_chunk"]["media_ms"]]
    medidas["cpu_ms_por_chunk"] = cpu * 1000 / total if cpu is not None else None
    print(f"PASADA {'con' if con else 'sin'} Heraldia: {total} chunks en {segundos:.1f} s, "
          f"CPU {_f(medidas['cpu_ms_por_chunk'])} ms por chunk, {v[0]:.1f} ms por chunk en los pasos "
          f"(p50 {_f(medidas['ms_por_chunk']['p50_ms'])}, p99 {_f(medidas['ms_por_chunk']['p99_ms'])}), "
          f"MSPT medio {_f(medidas['mspt']['media'])}, locate {medidas['locate_ms']}", flush=True)
    return medidas


def medir(jar, work, pasadas):
    """Pasadas alternas (sin, con, sin, con...) en `work`: (lista sin, lista con)."""
    os.makedirs(work, exist_ok=True)
    launcher = s.prepare(work, jar, s.gradle_properties())
    with open(os.path.join(work, "server.properties"), encoding="utf-8") as f:
        props = re.sub(r"level-seed=.*", f"level-seed={SEMILLA}", f.read())
    with open(os.path.join(work, "server.properties"), "w", encoding="utf-8") as f:
        f.write(props)
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(CONFIG, f)
    modrinth.instalar(work, ["chunky"])
    sin, con = [], []
    for i in range(pasadas):
        sin.append(pasada(work, jar, False, launcher))
        con.append(pasada(work, jar, True, launcher))
    return sin, con


def resultado_de(sin, con):
    import platform
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=s.ROOT, capture_output=True, text=True).stdout.strip()
    r = {"semilla": SEMILLA, "zonas": [f"{n} ({x}, {z}) {lado(x, r)}×{lado(z, r)} chunks" for n, x, z, r in ZONAS],
         "locate_desde": list(LOCATE_DESDE), "fecha": time.strftime("%Y-%m-%d"), "commit": commit,
         "maquina": f"{os.cpu_count()} núcleos, {platform.system()}" + (" (CI)" if os.environ.get("GITHUB_ACTIONS") else ""),
         "sin": agregar(sin), "con": agregar(con), "perfil": perfil_mediano([p["perfil"] for p in con if p.get("perfil")]),
         "crudo": {"sin": sin, "con": con}}
    r["sobrecoste"] = sobrecoste(r["con"], r["sin"])
    return r


def leer_referencia(ruta=REFERENCIA):
    if not os.path.isfile(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir(resultado, comparacion, salida):
    os.makedirs(salida, exist_ok=True)
    resultado = dict(resultado, comparacion={"ok": comparacion[0], "limite": comparacion[1], "texto": comparacion[2]})
    with open(os.path.join(salida, "coste_generacion.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1, default=list)
    md = markdown(resultado, comparacion)
    with open(os.path.join(salida, "coste_generacion.md"), "w", encoding="utf-8") as f:
        f.write(md)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(md)
    return md


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jar")
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-coste"))
    ap.add_argument("--pasadas", type=int, default=PASADAS, help=f"pasadas por configuración (por defecto {PASADAS})")
    ap.add_argument("--salida", default=os.path.join(s.ROOT, "build", "coste"), help="carpeta del JSON y el Markdown")
    ap.add_argument("--referencia", default=REFERENCIA)
    ap.add_argument("--actualizar-referencia", action="store_true", help="guarda la medición como referencia nueva")
    ap.add_argument("--sin-umbral", action="store_true", help="mide e informa, pero no falla por el umbral")
    ap.add_argument("--sin-reintento", action="store_true", help="si pasa del umbral, no repite otra ronda de pasadas")
    ap.add_argument("--desde", help="no mide: usa este coste_generacion.json (p. ej. el artefacto de la CI)")
    a = ap.parse_args(argv)
    ref = leer_referencia(a.referencia)
    if a.desde:
        with open(a.desde, encoding="utf-8") as f:
            res = json.load(f)
    else:
        if not a.jar:
            ap.error("--jar es obligatorio (o --desde)")
        jar, work = os.path.abspath(a.jar), os.path.abspath(a.work)
        sin, con = medir(jar, work, a.pasadas)
        res = resultado_de(sin, con)
        comp = comparar(res["sobrecoste"], ref)
        if not comp[0] and ref and not a.sin_reintento and not a.actualizar_referencia:
            print(f"{comp[2]}: se repite una ronda de {a.pasadas} pasadas y se decide con todas", flush=True)
            sin2, con2 = medir(jar, work, a.pasadas)
            res = resultado_de(sin + sin2, con + con2)
    comp = comparar(res["sobrecoste"], ref)
    if a.actualizar_referencia:
        nueva = referencia_nueva(res, ref)
        with open(a.referencia, "w", encoding="utf-8") as f:
            json.dump(nueva, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"referencia guardada en {a.referencia}: sobrecoste {nueva['sobrecoste']:+.1%}")
        comp = comparar(res["sobrecoste"], nueva)
    md = escribir(res, comp, a.salida)
    print(md)
    print("COSTE:", comp[2])
    return 0 if comp[0] or a.sin_umbral else 1


if __name__ == "__main__":
    sys.exit(main())
