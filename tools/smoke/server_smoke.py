"""Prueba de humo: arranca un servidor dedicado Fabric 26.3 real con el .jar del mod y comprueba la carga.

Uso: python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-X.jar --work build/smoke
Comprueba: el servidor arranca sin errores de registro, están las 72 estructuras del mod,
/place structure coloca una aldea con aldeanos, todas las tablas de botín se leen, los mapas del tesoro
responden en menos de 30 s (con o sin destino), el filtro de los tratos de cartógrafo funciona y las funciones existen.
También la configuración (config/heraldia.json): se migra un fichero sin versión, un valor fuera de rango se corrige al de
por defecto, los valores válidos llegan a la rejilla y a los gólems, y /locate solo encuentra aldeas en las casillas permitidas.
Las estructuras únicas que comparten bioma, localizadas con /locate, quedan a la distancia mínima configurada.
/heraldia info: el resumen cuenta las estructuras registradas y refleja la opción del cofre por jugador; «nearby» da para
cada única una posición igual o más cercana que /locate (y dentro del radio), con su tiempo medido.
Código 0 si todo pasa.
"""
import argparse, json, math, os, queue, re, shutil, socket, subprocess, sys, threading, time, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GENERATED_DATA = os.path.join(ROOT, "build", "generated", "heraldia", "data", "heraldia")
START_TIMEOUT_S, COMMAND_TIMEOUT_S = 600, 300
PLACE_ATTEMPTS, PLACE_RETRY_S = 30, 5
PLACE_TARGET = "heraldia:llanuras_castellana"
# /place structure exige cargados todos los chunks de la caja de la aldea (radio <= 116): se fuerza 16 x 16 chunks.
FORCELOAD = "forceload add -128 -128 127 127"
LOOT_TABLES = sorted(
    "heraldia:" + os.path.relpath(os.path.join(r, f), os.path.join(GENERATED_DATA, "loot_table"))[:-5].replace(os.sep, "/")
    for r, _, fs in os.walk(os.path.join(GENERATED_DATA, "loot_table")) for f in fs if f.endswith(".json"))
UNIQUE_STRUCTURES = sorted(
    "heraldia:unicas/" + f[:-5] for f in (os.listdir(os.path.join(GENERATED_DATA, "worldgen", "structure", "unicas"))
                                          if os.path.isdir(os.path.join(GENERATED_DATA, "worldgen", "structure", "unicas")) else [])
    if f.endswith(".json"))
# Un mapa del tesoro busca su estructura al generarse el botín, en el hilo del servidor: debe responder pronto.
MAP_TIMEOUT_S, EPIC_ROLLS = 30, 20
# Configuración de prueba: sin versión (migración), separación fuera de rango, máximo de 12 casillas, familia pantano
# desactivada (sin ella, la aldea más cercana a la semilla de prueba es heraldia:pantano_brujas) y opción desconocida.
# Las parejas de estructuras únicas que comparten bioma van en la rejilla mínima (1.000 bloques) para que compitan de
# verdad por el sitio, con una distancia mínima distinta de la de por defecto.
SEPARATION_PAIRS = [("castillo", "monasterio"), ("faro", "galeon")]
UNIQUE_MIN_DISTANCE = 1200
LOCATE_POINTS = [(0, 0), (6000, 0), (0, -6000), (-6000, 6000)]
TEST_CONFIG = {"aldeas": {"separacion_bloques": 50, "maximo": 12, "familias": {"pantano": False}}, "golems": {"limite_estandar": 7},
               "unicas": {"distancia_minima": {"bloques": UNIQUE_MIN_DISTANCE},
                          "atlantida": {"cofre_unico_por_jugador": True},
                          **{sid: {"separacion_bloques": 1000} for pair in SEPARATION_PAIRS for sid in pair}},
               # la arena de oleadas no se genera sola en los mundos nuevos de las pruebas (tools/smoke/arena.py la prueba)
               "arena": {"generar_en_mundos_nuevos": False},
               # sin preguntar a GitHub por versiones nuevas: las pruebas no dependen de la red (update_check.py lo prueba)
               "update_check": {"activado": False},
               "inventada": 1}
CONFIG_LOG = [
    r"configuración migrada de la versión 0 a la 1",
    r"valor no válido aldeas\.separacion_bloques=50 .*se usa el valor por defecto 1500",
    r"opción desconocida inventada",
    r"rejilla aldeas: activada, cada 94 chunks \(separación mínima 62\), máximo 12 casillas, exclusión 10 chunks",
    r"aldeas: 33 estilos activados, 25 % grandes; gólems: limpieza true, límites 7/9",
]
# Con 12 casillas (las 4 que tocan el 0,0 y sus 8 vecinas en cruz, de 94 chunks), toda aldea queda a menos de 2 x 94 x 16 bloques.
LOCATE_LIMIT = 2 * 94 * 16
DESCARGA_INTENTOS = 4         # una descarga cortada por la red (se ha visto con Fabric API) se repite
ERROR_PATTERN = r"Unknown|Incorrect|Failed|Invalid|error|not loaded"
# /heraldia info nearby: (punto, radio); el último, con el radio máximo, mide el peor caso. La búsqueda va fuera del hilo
# del servidor; en él solo se confirma (INFO_MAIN_MS como mucho). INFO_MAX_MS es el tope de la respuesta completa.
INFO_POINTS = [((0, 0), None), ((6000, 0), 6000), ((0, -6000), 10000)]
INFO_DEFAULT_RADIUS, INFO_MAX_MS, INFO_MAIN_MS = 3000, 20000, 20
INFO_LINE = re.compile(r" - .+? \((heraldia:[^)]+)\): (\d+) (?:blocks|bloques) .*?\[(-?\d+), ~, (-?\d+)\]")


def gradle_properties():
    props = {}
    with open(os.path.join(ROOT, "gradle.properties"), encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
    return props


def jar_valido(path):
    """¿Es un .jar (zip) entero? Una descarga cortada por la red no tiene el directorio central del final."""
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False


def download(url, dest, intentos=DESCARGA_INTENTOS):
    """Descarga `url` en `dest` si no está ya (entero). Una descarga cortada (menos bytes que Content-Length o un .jar
    sin su final) se repite hasta `intentos` veces en vez de quedarse en la caché y romper las pruebas siguientes."""
    if os.path.isfile(dest) and (not dest.endswith(".jar") or jar_valido(dest)):
        return
    for i in range(1, intentos + 1):
        print("descargando", url, f"(intento {i})" if i > 1 else "")
        try:
            with urllib.request.urlopen(url) as r, open(dest + ".part", "wb") as f:
                shutil.copyfileobj(r, f)
                esperado = r.headers.get("Content-Length")
            ok = (esperado is None or os.path.getsize(dest + ".part") == int(esperado)) and \
                (not dest.endswith(".jar") or jar_valido(dest + ".part"))
        except OSError as e:
            print("descarga fallida:", e)
            ok = False
        if ok:
            os.replace(dest + ".part", dest)
            return
        time.sleep(2 * i)
    raise SystemExit(f"no se pudo descargar entero {url} en {intentos} intentos")


def latest_installer():
    with urllib.request.urlopen("https://meta.fabricmc.net/v2/versions/installer") as r:
        return next(v["version"] for v in json.load(r) if v["stable"])


def free_port():
    with socket.socket() as so:
        so.bind(("", 0))
        return so.getsockname()[1]


def prepare(work, jar, p):
    mods = os.path.join(work, "mods")
    shutil.rmtree(mods, ignore_errors=True)
    for d in ("world", "logs"):
        shutil.rmtree(os.path.join(work, d), ignore_errors=True)
    os.makedirs(mods)
    mc, loader, fapi = p["minecraft_version"], p["loader_version"], p["fabric_api_version"]
    launcher = os.path.join(work, f"fabric-server-{mc}-{loader}.jar")
    download(f"https://meta.fabricmc.net/v2/versions/loader/{mc}/{loader}/{latest_installer()}/server/jar", launcher)
    cache = os.path.join(work, f"fabric-api-{fapi}.jar")
    download(f"https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/{fapi}/fabric-api-{fapi}.jar", cache)
    shutil.copy(cache, mods)
    shutil.copy(jar, mods)
    with open(os.path.join(work, "eula.txt"), "w") as f:
        f.write("eula=true\n")
    os.makedirs(os.path.join(work, "config"), exist_ok=True)
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(TEST_CONFIG, f)
    with open(os.path.join(work, "server.properties"), "w") as f:
        # Puerto libre (no el 25565 fijo): así se pueden lanzar varias pruebas a la vez en la misma máquina. Sin vigilante
        # de ticks (max-tick-time=-1): en una máquina muy cargada, forzar 256 chunks puede ocupar un tick más de 60 s y
        # el vigilante cerraba el servidor («A single server tick took 60 s»); la prueba ya tiene sus propios límites.
        f.write("online-mode=false\nview-distance=4\nsimulation-distance=4\nspawn-protection=0\npause-when-empty-seconds=0\n"
                f"level-seed=heraldia\nserver-port={free_port()}\nmax-tick-time=-1\n")
    return launcher


def reader(proc, lines):
    for line in proc.stdout:
        sys.stdout.write(line)
        lines.put(line)
    lines.put(None)


def wait_for(lines, pattern, timeout, seen):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            line = lines.get(timeout=max(0.1, end - time.monotonic()))
        except queue.Empty:
            break
        if line is None:
            raise SystemExit("el servidor se cerró antes de tiempo")
        seen.append(line)
        m = re.search(pattern, line)
        if m:
            return m
    raise SystemExit(f"tiempo agotado esperando: {pattern}")


def send(proc, cmd):
    proc.stdin.write(cmd + "\n")
    proc.stdin.flush()


def pending(lines, seen):
    """Pasa a `seen` las líneas que ya hay en la cola sin esperar a ninguna (respuestas de más de una orden anterior)."""
    while True:
        try:
            line = lines.get_nowait()
        except queue.Empty:
            return
        if line is None:
            lines.put(None)
            return
        seen.append(line)


def run(proc, lines, seen, cmd, ok):
    """Envía una orden y devuelve la primera respuesta de éxito o error. Antes descarta (a `seen`) lo que quedara en la
    cola: la línea de más de una orden anterior (p. ej. dos «Test passed») no se toma por la respuesta de esta."""
    pending(lines, seen)
    send(proc, cmd)
    return wait_for(lines, f"{ok}|{ERROR_PATTERN}", COMMAND_TIMEOUT_S, seen)


# Esperas por condición de las pruebas de servidor: se repite la comprobación hasta UNTIL_S segundos (holgado: la CI va
# lenta y escribe «Can't keep up!») y se pasa en cuanto se cumple. Las esperas «a que pase el tiempo» (que un circuito
# NO reaccione, que una trampa ya haya disparado) se cuentan en ticks del juego con /time query gametime, no en segundos:
# con el servidor atrasado, 2 s de reloj pueden ser muy pocos ticks.
UNTIL_S, POLL_S, TICK_TIMEOUT_S = 120, 1, 300
_TEST = r"Test passed(?:\. Count: (\d+))?|Test failed"
_NUM = r"(-?[\d.]+(?:E-?\d+)?)d"
_POS = rf"has the following entity data: \[{_NUM}, {_NUM}, {_NUM}\]|No entity was found"


def _top_tokens(cmd):
    """Las palabras de una orden fuera de corchetes, llaves y comillas (las de un selector o un NBT no cuentan)."""
    toks, cur, depth, quote = [], "", 0, None
    for ch in cmd:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == " " and depth == 0:
            if cur:
                toks.append(cur)
            cur = ""
        else:
            cur += ch
    return toks + ([cur] if cur else [])


def silent_reason(cmd):
    """Por qué una comprobación `execute ...` podría no responder nada en la consola (y colgar la prueba hasta
    COMMAND_TIMEOUT_S), o None si siempre responde «Test passed|Test failed». Ver docs/APRENDIZAJES.md: `as`/`at`
    (y `positioned as`, `facing entity`...) bifurcan la orden y el «Test failed» de una rama no llega; sin nadie en el
    selector no hay ni rama; en una cadena `if A if B` la condición intermedia que falla no responde."""
    toks = _top_tokens(cmd)
    if not toks or toks[0] != "execute":
        return None
    if "run" in toks:
        return "lleva «run»: la respuesta es la de la orden de después"
    if {"as", "at", "on"} & set(toks[1:]) or any(a == "facing" and b == "entity" for a, b in zip(toks, toks[1:])):
        return "bifurca por entidades (as/at/on/facing entity): si no hay nadie o falla en una rama, no responde"
    if sum(t in ("if", "unless") for t in toks) != 1:
        return "más de una condición: si falla una intermedia, no responde"
    return None


class Context:
    """Lo que necesita un módulo de estructura única para sus comprobaciones propias (tools/gen/unicas/<id>/humo.py),
    y las utilidades comunes de las pruebas de servidor: comprobar, esperar por condición, contar ticks, leer `Pos`."""

    def __init__(self, proc, lines, seen):
        self.proc, self.lines, self.seen = proc, lines, seen

    def run(self, cmd, ok):
        return run(self.proc, self.lines, self.seen, cmd, ok)

    def log(self):
        return "".join(self.seen)

    def test(self, cmd):
        """True/False de una comprobación de una sola condición sin bifurcar (siempre responde; si no, ValueError)."""
        why = silent_reason(cmd)
        if why:
            raise ValueError(f"comprobación que puede no responder ({why}): {cmd}")
        return self.run(cmd, _TEST).group(0).startswith("Test passed")

    def count(self, sel):
        """Cuántas entidades da el selector (0 si ninguna)."""
        m = self.run(f"execute if entity {sel}", _TEST)
        return int(m.group(1) or 0) if m.group(0).startswith("Test passed") else 0

    def block(self, pos, state):
        """¿Hay `state` en las coordenadas `pos` ("x y z" o tupla)?"""
        p = pos if isinstance(pos, str) else " ".join(str(c) for c in pos)
        return self.test(f"execute if block {p} {state}")

    def until(self, cmd, want=True, timeout=UNTIL_S):
        """Repite la comprobación hasta que dé `want` (True) o pasen `timeout` segundos (False)."""
        end = time.monotonic() + timeout
        while True:
            if self.test(cmd) == want:
                return True
            if time.monotonic() > end:
                return False
            time.sleep(POLL_S)

    def gametime(self):
        return int(self.run("time query gametime", r"[Tt]ime is (\d+)").group(1))

    def ticks(self, n):
        """Espera a que el servidor haya ejecutado `n` ticks más (lo que tarde en reloj, sin pasar de TICK_TIMEOUT_S)."""
        end, target = time.monotonic() + TICK_TIMEOUT_S, self.gametime() + n
        time.sleep(n / 20)
        while self.gametime() < target:
            if time.monotonic() > end:
                raise SystemExit(f"el servidor no avanza {n} ticks en {TICK_TIMEOUT_S} s")
            time.sleep(0.25)

    def pos(self, sel):
        """(x, y, z) de la primera entidad del selector, con `data get entity ... Pos`; None si no hay ninguna."""
        one = sel if "limit=" in sel else (sel[:-1] + ",limit=1]" if sel.endswith("]") else sel + "[limit=1]")
        m = self.run(f"data get entity {one} Pos", _POS)
        return tuple(float(v) for v in m.groups()) if m.group(1) else None

    def wait_entity(self, sel, timeout=UNTIL_S):
        """Espera a que el selector dé alguna entidad (las de una plantilla aparecen unos segundos después que los
        bloques). Si no llega, imprime un diagnóstico (cuántas hay del mismo tipo o etiqueta en todo el mundo y dónde)."""
        if self.until(f"execute if entity {sel}", timeout=timeout):
            return True
        print(f"DIAG: ninguna entidad {sel} en {timeout} s; {self.diagnose(sel)}")
        return False

    def diagnose(self, sel):
        """Texto con las entidades del mismo tipo/etiqueta que `sel`, sin sus límites de zona, y su posición."""
        inner = sel[sel.index("[") + 1:-1] if "[" in sel else ""
        keep = [f for f in _top_tokens(inner.replace(",", " ")) if f.split("=")[0] in ("type", "tag")]
        wide = f"@e[{','.join(keep)}]"
        return f"{wide}: {self.count(wide)} en el mundo, la primera en {self.pos(wide)}"


def unique_hook(sid):
    """Función comprobar(ctx) -> lista de fallos del módulo unicas.<id>.humo, si existe."""
    import importlib, importlib.util
    gen = os.path.join(ROOT, "tools", "gen")
    if gen not in sys.path:
        sys.path.insert(0, gen)
    name = f"unicas.{sid.split('/')[-1]}.humo"
    try:
        if importlib.util.find_spec(name) is None:
            return None
    except ModuleNotFoundError:
        return None
    return importlib.import_module(name).comprobar


def locate(ctx, sid, x, z):
    """(x, z, segundos) de la estructura sid más cercana a x, z, o None si /locate no la encuentra."""
    t0 = time.monotonic()
    m = ctx.run(f"execute positioned {x} 64 {z} run locate structure heraldia:unicas/{sid}",
                r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
    return (int(m.group(1)), int(m.group(2)), time.monotonic() - t0) if m.group(1) else None


def check_separation(ctx):
    """Las parejas que comparten bioma, localizadas desde varios puntos y una desde la otra, quedan a >= N bloques."""
    failures, found, took = [], {sid: set() for pair in SEPARATION_PAIRS for sid in pair}, []
    for a, b in SEPARATION_PAIRS:
        measured = 0
        for first, second in ((a, b), (b, a)):
            for x, z in LOCATE_POINTS:
                p = locate(ctx, first, x, z)
                if not p:
                    continue
                q = locate(ctx, second, p[0], p[1])
                took += [p[2]] + ([q[2]] if q else [])
                found[first].add(p[:2])
                if q:
                    found[second].add(q[:2])
                    measured += 1
        pairs = [(p, q) for p in found[a] for q in found[b]]
        close = [(p, q) for p, q in pairs if math.dist(p, q) < UNIQUE_MIN_DISTANCE]
        if measured == 0:
            failures.append(f"/locate no encontró ninguna pareja {a}/{b} para medir la separación")
        for p, q in close:
            failures.append(f"{a} en {p} y {b} en {q} a {math.dist(p, q):.0f} bloques (< {UNIQUE_MIN_DISTANCE})")
        print(f"separación {a}/{b}: {len(pairs)} parejas medidas, mínima "
              f"{min((math.dist(p, q) for p, q in pairs), default=0):.0f} bloques")
    if took:
        print(f"/locate de estructuras únicas: {len(took)} búsquedas, media {sum(took) / len(took):.2f} s, máxima {max(took):.2f} s")
    if not re.search(rf"distancia mínima entre estructuras únicas: activada, {UNIQUE_MIN_DISTANCE} bloques", ctx.log()):
        failures.append("falta en el log la distancia mínima entre estructuras únicas configurada")
    return failures


def drain(ctx, wait=1.5):
    """Las líneas que el servidor haya escrito en los próximos segundos (las de una orden que responde con varias)."""
    time.sleep(wait)
    out = []
    while True:
        try:
            line = ctx.lines.get_nowait()
        except queue.Empty:
            return out
        if line is None:
            raise SystemExit("el servidor se cerró antes de tiempo")
        ctx.seen.append(line)
        out.append(line)


def check_info(ctx, expected):
    """/heraldia info: resumen (estructuras registradas, opción del cofre por jugador) y «nearby» comparado con /locate."""
    fails = []
    m = ctx.run("heraldia info", r"Registered structures: (\d+)|Estructuras registradas: (\d+)")
    n = m.group(1) or m.group(2) if m.lastindex else None
    if n is None or int(n) != expected:
        fails.append(f"/heraldia info: estructuras registradas {n}, esperadas {expected}: {m.string.strip()}")
    text = "".join(ctx.seen[-40:])
    if not re.search(r"Per-player Atlantis premium chest: yes|Cofre premium de la Atlántida por jugador: sí", text):
        fails.append("/heraldia info no refleja unicas.atlantida.cofre_unico_por_jugador = true")
    for (x, z), radius in INFO_POINTS:
        r = radius or INFO_DEFAULT_RADIUS
        cmd = f"execute positioned {x} 64 {z} run heraldia info nearby" + (f" {radius}" if radius else "")
        m = ctx.run(cmd, r"info nearby \d+ en [^:]+: \d+ estructuras en (\d+) ms \((\d+) ms en el hilo del servidor\)")
        if not m.lastindex:
            fails.append(f"{cmd}: {m.string.strip()}")
            continue
        ms, main_ms = int(m.group(1)), int(m.group(2))
        found = {g[0]: (int(g[1]), int(g[2]), int(g[3])) for g in INFO_LINE.findall("".join(drain(ctx)))}
        print(f"/heraldia info nearby {r} desde {x}, {z}: {len(found)} estructuras en {ms} ms ({main_ms} ms en el hilo del servidor)")
        if ms > INFO_MAX_MS or main_ms > INFO_MAIN_MS:
            fails.append(f"{cmd}: {ms} ms, {main_ms} ms en el hilo del servidor (máximo {INFO_MAX_MS} y {INFO_MAIN_MS})")
        if any(d > r for d, _, _ in found.values()):
            fails.append(f"{cmd}: da estructuras fuera del radio: {found}")
        for sid in sorted({sid for pair in SEPARATION_PAIRS for sid in pair} | {"atlantida"}):
            p = locate(ctx, sid, x, z)
            if not p or math.dist(p[:2], (x, z)) > r:
                continue
            ours = found.get(f"heraldia:unicas/{sid}")
            if ours is None or ours[0] > math.dist(p[:2], (x, z)) + 1:
                fails.append(f"{cmd}: /locate da {sid} en {p[:2]}, pero info nearby da {ours}")
        if (x, z) == (0, 0) and "heraldia:aldeas" not in found and not any(":unicas/" not in k and ":medianas/" not in k and ":minas/" not in k for k in found):
            fails.append(f"{cmd}: no da ninguna aldea cerca del 0,0 (12 casillas permitidas): {found}")
    m = ctx.run("execute positioned 5000 64 5000 run heraldia info here", r"not loaded|no está cargada")
    if m.group(0) not in ("not loaded", "no está cargada"):
        fails.append(f"/heraldia info here en un chunk sin cargar: {m.string.strip()}")
    return fails


def guardian_placed(ctx, sid):
    """El guardián de la única conserva en el mundo la etiqueta heraldia_guardian.<id> con la que lo reconoce su logro
    (logros.py). Las entidades de una plantilla tardan unos segundos más que los bloques: se reintenta."""
    return ctx.wait_entity(f"@e[tag=heraldia_guardian.{sid.split('/')[-1]}]")


def guardian_trophy(ctx, sid):
    """El guardián colocado conserva su DeathLootTable (la del trofeo, heraldia:guardianes/<id>/<mob>) y, muerto sin
    jugador (/loot ... kill desde la consola), no suelta el trofeo (condición killed_by_player). Que lo suelte al
    matarlo un jugador lo prueba tools/smoke/trofeos.py con un jugador simulado."""
    sid = sid.split("/")[-1]
    g = f"@e[tag=heraldia_guardian.{sid},limit=1]"
    m = ctx.run(f"data get entity {g} DeathLootTable", r'has the following entity data: "([^"]+)"|No entity')
    if not (m.group(1) or "").startswith(f"heraldia:guardianes/{sid}/"):
        return [f"el guardián no tiene la tabla del trofeo: {m.string.strip()}"]
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    # Sin «execute at <guardián>»: si el guardián ya no estuviera, la orden no respondería nada (5 min colgada). Se lee
    # su posición y se suelta el botín ahí.
    p = ctx.pos(g)
    if p is None:
        return [f"el guardián ha desaparecido antes de soltar su botín; {ctx.diagnose(g)}"]
    m = ctx.run(f"loot spawn {p[0]:.2f} {p[1] + 1:.2f} {p[2]:.2f} kill {g}", r"Dropped \d+|No items|No entity was found")
    if not m.group(0).startswith(("Dropped", "No items")):
        return [f"/loot kill del guardián falló: {m.string.strip()}"]
    m = ctx.run(f'execute if entity @e[type=minecraft:item,nbt={{Item:{{components:{{"minecraft:custom_data":{{heraldia_trofeo:"{sid}"}}}}}}}}]',
                r"Test passed|Test failed")
    return [] if "failed" in m.group(0) else ["suelta el trofeo sin que lo mate un jugador"]


def snbt(v):
    if isinstance(v, dict):
        return "{" + ",".join(f"{k}:{snbt(x)}" for k, x in v.items()) + "}"
    return json.dumps(v) if isinstance(v, str) else str(v)


def check_keys(ctx):
    """/heraldia key: registrado (pide jugadores y rechaza una llave inventada) y cada tabla de llave da un objeto que
    cumple la cerradura de sus cofres. Sin cliente no hay jugadores: el reparto al inventario no se prueba aquí."""
    fails = []
    with open(os.path.join(ROOT, "build", "generated", "heraldia", "heraldia", "llaves.json"), encoding="utf-8") as f:
        keys = json.load(f)["llaves"]
    if not keys:
        return ["heraldia/llaves.json sin llaves"]
    m = ctx.run("heraldia key @a inventada", r"No hay ninguna llave|There is no key")   # el servidor traduce (en_us)
    if not m.group(0).startswith(("No hay", "There is no")):
        fails.append(f"/heraldia key no rechaza una llave inventada: {m.string.strip()}")
    m = ctx.run("heraldia key @a all", r"No player was found")
    if not m.group(0).startswith("No player"):
        fails.append(f"/heraldia key @a all sin jugadores: {m.string.strip()}")
    for kid, d in keys.items():
        lock = d["cerradura"]
        pred = lock["items"] + "[" + ",".join(f"{k}~{snbt(v)}" for k, v in lock["predicates"].items()) + "]"
        ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
        m = ctx.run(f"loot spawn 0 200 0 loot {d['tabla']}", r"Dropped \d+")
        if not m.group(0).startswith("Dropped 1"):
            fails.append(f"llave {kid}: {m.string.strip()}")
            continue
        m = ctx.run(f"execute positioned 0 200 0 if items entity @e[type=minecraft:item,distance=..4] contents {pred}",
                    r"Test passed|Test failed")
        if "passed" not in m.group(0):
            fails.append(f"llave {kid}: el objeto no abre su cerradura ({pred}): {m.string.strip()}")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
    print(f"llaves: {len(keys)} comprobadas con su cerradura")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    expected = sum(f.endswith(".json") for _, _, fs in os.walk(os.path.join(GENERATED_DATA, "worldgen", "structure")) for f in fs)
    expected_advancements = sum(f.endswith(".json") for _, _, fs in os.walk(os.path.join(GENERATED_DATA, "advancement")) for f in fs)
    launcher = prepare(args.work, os.path.abspath(args.jar), gradle_properties())

    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=reader, args=(proc, lines), daemon=True).start()
    failures, villagers, located, maps_found = [], 0, "/locate sin comprobar", []
    try:
        # El mod lo escribe en SERVER_STARTED, después de "Done": el servidor ya acepta órdenes.
        m = wait_for(lines, r"Heraldia: (\d+) estructuras registradas", START_TIMEOUT_S, seen)
        if int(m.group(1)) != expected:
            failures.append(f"estructuras registradas {m.group(1)}, esperadas {expected}")
        # Logros (logros.py): en 26.3 son un registro; se cargan todos los generados y sin avisos de validación.
        m = wait_for(lines, r"Heraldia: (\d+) logros cargados", COMMAND_TIMEOUT_S, seen)
        if int(m.group(1)) != expected_advancements:
            failures.append(f"logros cargados {m.group(1)}, esperados {expected_advancements}")
        with open(os.path.join(args.work, "config", "heraldia.json"), encoding="utf-8") as f:
            written = json.load(f)
        if (written.get("version"), written["aldeas"]["separacion_bloques"], written["aldeas"]["maximo"]) != (1, 1500, 12):
            failures.append(f"config/heraldia.json reescrito mal: {written.get('version')} {written['aldeas']}")
        if "inventada" in written or "es_es" not in written.get("_ayuda", {}):
            failures.append("config/heraldia.json sin ayuda o con la opción desconocida")
        if written["unicas"]["atlantida"].get("cofre_unico_por_jugador") is not True or not all(
                "unicas.atlantida.cofre_unico_por_jugador" in written["_ayuda"][lang] for lang in ("es_es", "en_us")):
            failures.append("config/heraldia.json: unicas.atlantida.cofre_unico_por_jugador sin conservar o sin ayuda")
        m = run(proc, lines, seen, "scoreboard players get #limite_estandar heraldia_cfg", r"has (\d+)")
        log_so_far = "".join(seen)   # la línea de gólems se escribe en SERVER_STARTED, ya antes de esta respuesta
        for pat in CONFIG_LOG:
            if not re.search(pat, log_so_far):
                failures.append(f"falta en el log de configuración: {pat}")
        if not m.group(0).startswith("has") or m.group(1) != "7":
            failures.append(f"#limite_estandar heraldia_cfg no es 7: {m.string.strip()}")
        m = run(proc, lines, seen, "execute positioned 20000 64 20000 run locate structure #heraldia:aldeas",
                r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
        if m.group(1) is None:
            failures.append(f"/locate no encontró aldeas en las 12 casillas permitidas: {m.string.strip()}")
        elif "pantano" in m.group(0):
            failures.append(f"/locate encontró una aldea de una familia desactivada: {m.string.strip()}")
        elif max(abs(int(m.group(1))), abs(int(m.group(2)))) > LOCATE_LIMIT:
            failures.append(f"/locate encontró una aldea fuera de las casillas permitidas: {m.string.strip()}")
        else:
            located = f"/locate en {m.group(1)}, {m.group(2)}"
        failures += check_separation(Context(proc, lines, seen))
        failures += check_info(Context(proc, lines, seen), expected)
        send(proc, FORCELOAD)
        wait_for(lines, r"Marked|Added|chunks? .*force", COMMAND_TIMEOUT_S, seen)
        for _ in range(PLACE_ATTEMPTS):
            m = run(proc, lines, seen, f"place structure {PLACE_TARGET} 0 ~ 0", r"Generated structure")
            if "not loaded" not in m.group(0):
                break
            time.sleep(PLACE_RETRY_S)   # los chunks forzados se cargan en los ticks siguientes
        if "Generated structure" not in m.group(0):
            failures.append(f"place structure falló: {m.string.strip()}")
        # Si el ensamblado jigsaw funciona hay casas con aldeanos, no solo la plaza.
        m = run(proc, lines, seen, "execute if entity @e[type=minecraft:villager]", r"Test passed\. Count: (\d+)|Test failed")
        villagers = int(m.group(1)) if m.group(1) else 0
        if villagers == 0:
            failures.append("la aldea colocada no tiene aldeanos")
        # Cada estructura única se coloca (se superponen en el mismo sitio: solo importa que se generen).
        for sid in UNIQUE_STRUCTURES:
            hook = unique_hook(sid)
            if hook:    # estructuras que no se colocan con /place (tipo propio): su módulo trae sus comprobaciones
                failures += [f"{sid}: {f}" for f in hook(Context(proc, lines, seen))]
                continue
            m = run(proc, lines, seen, f"place structure {sid} 0 ~ 0", r"Generated structure")
            if not m.group(0).startswith("Generated"):
                failures.append(f"place structure {sid} falló: {m.string.strip()}")
            elif not guardian_placed(Context(proc, lines, seen), sid):
                failures.append(f"{sid}: no aparece su guardián con la etiqueta del logro")
            else:
                failures += [f"{sid}: {f}" for f in guardian_trophy(Context(proc, lines, seen), sid)]
        # Las tablas de botín se leen (y la condición heraldia:sin_lootr está registrada si alguna la usa).
        for table in LOOT_TABLES:
            t0 = time.monotonic()
            m = run(proc, lines, seen, f"loot spawn 0 200 0 loot {table}", r"Dropped \d+|No items")
            found = bool(re.match(r"Dropped [1-9]", m.group(0)))
            took = time.monotonic() - t0
            # mapas sin destino y tablas de muerte de los guardianes (sin el mob, su botín vanilla puede salir vacío)
            if not m.group(0).startswith(("Dropped", "No items")) or ("No items" in m.group(0) and not
                                                                   re.search(":(mapas|guardianes)/", table)):
                failures.append(f"botín {table} falló: {m.string.strip()}")
            if ":mapas/" in table:
                # Sin estructura alcanzable el mapa se descarta ("No items"), pero nunca debe colgar el servidor.
                print(f"mapa {table}: {'con destino' if found else 'sin destino'} en {took:.1f} s")
                if found:
                    maps_found.append(table)
                if took > MAP_TIMEOUT_S:
                    failures.append(f"mapa {table} tardó {took:.0f} s (> {MAP_TIMEOUT_S} s)")
        failures += check_keys(Context(proc, lines, seen))
        # El cofre épico (con su grupo de mapas) se tira varias veces seguidas.
        t0 = time.monotonic()
        for _ in range(EPIC_ROLLS):
            m = run(proc, lines, seen, "loot spawn 0 200 0 loot heraldia:cofres/epico", r"Dropped \d+")
            if not m.group(0).startswith("Dropped"):
                failures.append(f"cofre épico falló: {m.string.strip()}")
                break
        if time.monotonic() - t0 > MAP_TIMEOUT_S:
            failures.append(f"{EPIC_ROLLS} cofres épicos tardaron {time.monotonic() - t0:.0f} s")
        # Tratos de mapas: el registro villager_trade se carga (o el log muestra errores) y el filtro de cartógrafos
        # de Heraldia reconoce a los aldeanos de la aldea colocada y rechaza a uno vanilla.
        m = run(proc, lines, seen, "execute if entity @e[type=minecraft:villager,tag=heraldia,predicate=heraldia:aldeano_heraldia]",
                r"Test passed|Test failed")
        if "passed" not in m.group(0):
            failures.append("los aldeanos de Heraldia no cumplen heraldia:aldeano_heraldia")
        run(proc, lines, seen, "summon minecraft:villager 0 200 0 {Tags:[\"heraldia_vanilla\"],NoAI:1b}", r"Summoned")
        m = run(proc, lines, seen, "execute if entity @e[type=minecraft:villager,tag=heraldia_vanilla,predicate=heraldia:aldeano_heraldia]",
                r"Test passed|Test failed")
        if "failed" not in m.group(0):
            failures.append("un aldeano vanilla cumple heraldia:aldeano_heraldia")
        m = run(proc, lines, seen, "function heraldia:golems", r"Running function|Ran \d+ command")
        if not m.group(0).startswith(("Running", "Ran")):
            failures.append(f"function heraldia:golems falló: {m.string.strip()}")
    finally:
        if proc.poll() is None:
            send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    log = os.path.join(args.work, "logs", "latest.log")
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else "".join(seen)
    for bad in ("Registry loading errors", "Failed to load datapacks", "Couldn't load", "Failed to parse",
                "Found validation problems in advancement heraldia:"):
        if bad in text:
            failures.append(f"el log contiene {bad!r}")
    if failures:
        print("PRUEBA DE HUMO FALLIDA:\n  " + "\n  ".join(failures))
        return 1
    sys.stdout.flush()
    print(f"PRUEBA DE HUMO OK: {expected} estructuras registradas, {expected_advancements} logros, {PLACE_TARGET} colocada con {villagers} aldeanos, botín, {len(maps_found)} mapas con destino, funciones y configuración correctos ({located})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
