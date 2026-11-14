"""Prueba de humo: arranca un servidor dedicado Fabric 26.3 real con el .jar del mod y comprueba la carga.

Uso: python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-X.jar --work build/smoke
Comprueba: el servidor arranca sin errores de registro, están las 72 estructuras del mod,
/place structure coloca una aldea y las funciones del mod existen. Código 0 si todo pasa.
"""
import argparse, json, os, queue, re, shutil, subprocess, sys, threading, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GENERATED_STRUCTURES = os.path.join(ROOT, "build", "generated", "heraldia", "data", "heraldia", "worldgen", "structure")
START_TIMEOUT_S, COMMAND_TIMEOUT_S = 600, 300
PLACE_ATTEMPTS, PLACE_RETRY_S = 30, 5
PLACE_TARGET = "heraldia:llanuras_castellana"
# /place structure exige cargados todos los chunks de la caja de la aldea (radio <= 116): se fuerza 16 x 16 chunks.
FORCELOAD = "forceload add -128 -128 127 127"
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
    expected = len([f for f in os.listdir(GENERATED_STRUCTURES) if f.endswith(".json")])
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
    print(f"PRUEBA DE HUMO OK: {expected} estructuras registradas, {PLACE_TARGET} colocada con {villagers} aldeanos, funciones presentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
