"""Prueba de humo: arranca un servidor dedicado Fabric 26.3 real con el .jar del mod y comprueba la carga.

Uso: python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-X.jar --work build/smoke
Comprueba: el servidor arranca sin errores de registro, están las 72 estructuras del mod,
/place structure coloca una aldea con aldeanos, todas las tablas de botín se leen, los mapas del tesoro\nresponden en menos de 30 s (con o sin destino), el filtro de los tratos de cartógrafo funciona y las funciones existen. Código 0 si todo pasa.
"""
import argparse, json, os, queue, re, shutil, subprocess, sys, threading, time, urllib.request

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
ERROR_PATTERN = r"Unknown|Incorrect|Failed|Invalid|error|not loaded"


def gradle_properties():
    props = {}
    with open(os.path.join(ROOT, "gradle.properties"), encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
    return props


def download(url, dest):
    if not os.path.isfile(dest):
        print("descargando", url)
        with urllib.request.urlopen(url) as r, open(dest + ".part", "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(dest + ".part", dest)


def latest_installer():
    with urllib.request.urlopen("https://meta.fabricmc.net/v2/versions/installer") as r:
        return next(v["version"] for v in json.load(r) if v["stable"])


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
    with open(os.path.join(work, "server.properties"), "w") as f:
        f.write("online-mode=false\nview-distance=4\nsimulation-distance=4\nspawn-protection=0\npause-when-empty-seconds=0\nlevel-seed=heraldia\n")
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


def run(proc, lines, seen, cmd, ok):
    """Envía una orden y devuelve la primera respuesta de éxito o error."""
    send(proc, cmd)
    return wait_for(lines, f"{ok}|{ERROR_PATTERN}", COMMAND_TIMEOUT_S, seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    expected = sum(f.endswith(".json") for _, _, fs in os.walk(os.path.join(GENERATED_DATA, "worldgen", "structure")) for f in fs)
    launcher = prepare(args.work, os.path.abspath(args.jar), gradle_properties())

    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=args.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=reader, args=(proc, lines), daemon=True).start()
    failures, villagers = [], 0
    try:
        # El mod lo escribe en SERVER_STARTED, después de "Done": el servidor ya acepta órdenes.
        m = wait_for(lines, r"Heraldia: (\d+) estructuras registradas", START_TIMEOUT_S, seen)
        if int(m.group(1)) != expected:
            failures.append(f"estructuras registradas {m.group(1)}, esperadas {expected}")
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
            m = run(proc, lines, seen, f"place structure {sid} 0 ~ 0", r"Generated structure")
            if not m.group(0).startswith("Generated"):
                failures.append(f"place structure {sid} falló: {m.string.strip()}")
        # Las tablas de botín se leen (y la condición heraldia:sin_lootr está registrada si alguna la usa).
        maps_found = []
        for table in LOOT_TABLES:
            t0 = time.monotonic()
            m = run(proc, lines, seen, f"loot spawn 0 200 0 loot {table}", r"Dropped \d+|No items")
            found = bool(re.match(r"Dropped [1-9]", m.group(0)))
            took = time.monotonic() - t0
            if not m.group(0).startswith(("Dropped", "No items")) or ("No items" in m.group(0) and ":mapas/" not in table):
                failures.append(f"botín {table} falló: {m.string.strip()}")
            if ":mapas/" in table:
                # Sin estructura alcanzable el mapa se descarta ("No items"), pero nunca debe colgar el servidor.
                print(f"mapa {table}: {'con destino' if found else 'sin destino'} en {took:.1f} s")
                if found:
                    maps_found.append(table)
                if took > MAP_TIMEOUT_S:
                    failures.append(f"mapa {table} tardó {took:.0f} s (> {MAP_TIMEOUT_S} s)")
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
    for bad in ("Registry loading errors", "Failed to load datapacks", "Couldn't load", "Failed to parse"):
        if bad in text:
            failures.append(f"el log contiene {bad!r}")
    if failures:
        print("PRUEBA DE HUMO FALLIDA:\n  " + "\n  ".join(failures))
        return 1
    sys.stdout.flush()
    print(f"PRUEBA DE HUMO OK: {expected} estructuras registradas, {PLACE_TARGET} colocada con {villagers} aldeanos, botín, {len(maps_found)} mapas con destino y funciones correctos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
