"""Prueba con Terralith (mod de biomas) en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/terralith_biomas.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Descarga de Modrinth versiones fijadas de Terralith y Lithostitched (comprobadas con su sha512) y la pone junto a Heraldia y Fabric API.
Comprueba: el servidor arranca sin errores de registro y con todas las estructuras; los biomas de Terralith que añaden
sus etiquetas convencionales (#c:...) entran en las etiquetas de Heraldia (/locate biome + execute if biome) y los que
no deben, no; y /locate sigue encontrando las únicas cuyo bioma comparte Terralith.
"""
import argparse, hashlib, os, queue, shutil, subprocess, sys, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

# Mods de Modrinth fijados (nombre, url, sha512): Terralith y su dependencia Lithostitched (las dos piden Fabric API).
MODS = [
    ("Terralith_26.3_v2.6.5+26.3.jar",
     "https://cdn.modrinth.com/data/8oi3bsk5/versions/aGE3hYAA/Terralith_26.3_v2.6.5%2B26.3.jar",
     "918b232df7a855bae89c7fa85affb5ce134e236c4726fa14a5bdaa179eb1e010f040a9fa981f006a0e26e421a2a961bc29a75e99a4500fd18361a8ba81478071"),
    ("lithostitched-2.0.6-fabric-26.3.jar",
     "https://cdn.modrinth.com/data/XaDC71GB/versions/pZgI6b2t/lithostitched-2.0.6-fabric-26.3.jar",
     "d7ffe9bb3ea653ae70317f8621c546e3331369c0dd3cd6cadb374cc71283ca1fae1e7de7d2d16eb5724e96f7159c8b043e15a618f32dad88c8e70a7d8d1db4ee"),
]
# (bioma de Terralith, etiqueta de Heraldia, ¿debe entrar?). Los positivos llegan por las #c: de biomas.CONVENCIONALES.
EXPECTED = [
    ("terralith:steppe", "llanuras", True), ("terralith:highlands", "unicas/castillo", True),
    ("terralith:lavender_forest", "unicas/catedral", True), ("terralith:birch_taiga", "bosque", True),
    ("terralith:desert_oasis", "desierto", True), ("terralith:sandstone_valley", "unicas/acueducto", True),
    ("terralith:white_mesa", "badlands", True), ("terralith:tropical_jungle", "jungla", True),
    ("terralith:orchid_swamp", "pantano", True), ("terralith:gravel_beach", "unicas/faro", True),
    ("terralith:steppe", "bosque", False), ("terralith:desert_oasis", "unicas/piramide", False),
    ("terralith:lavender_forest", "oscuro", False),
]
LOCATE = ["castillo", "catedral", "acueducto"]


def fetch(work, name, url, sha):
    path = os.path.join(work, name)
    s.download(url, path)
    with open(path, "rb") as f:
        got = hashlib.sha512(f.read()).hexdigest()
    if got != sha:
        os.remove(path)
        raise SystemExit(f"{name}: sha512 distinto ({got[:16]}...); descarga incorrecta")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-terralith"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    expected = sum(f.endswith(".json") for _, _, fs in os.walk(os.path.join(s.GENERATED_DATA, "worldgen", "structure")) for f in fs)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    for mod in MODS:
        shutil.copy(fetch(a.work, *mod), os.path.join(a.work, "mods"))
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen, fails, ok = queue.Queue(), [], [], 0
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    try:
        m = s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        if int(m.group(1)) != expected:
            fails.append(f"estructuras registradas {m.group(1)}, esperadas {expected}")
        where = {}
        for biome, tag, inside in EXPECTED:
            if biome not in where:
                m = s.run(proc, lines, seen, f"locate biome {biome}", r"nearest.*?\[(-?\d+), (-?\d+), (-?\d+)\]|Could not find")
                where[biome] = tuple(int(m.group(i)) for i in (1, 2, 3)) if m.group(1) else None
            if where[biome] is None:
                fails.append(f"no se encuentra {biome}")
                continue
            x, y, z = where[biome]
            m = s.run(proc, lines, seen, f"execute if biome {x} {y} {z} #heraldia:{tag}", r"Test passed|Test failed")
            if ("passed" in m.group(0)) != inside:
                fails.append(f"{biome} {'debería' if inside else 'no debería'} estar en #heraldia:{tag}")
            else:
                ok += 1
        for sid in LOCATE:
            m = s.run(proc, lines, seen, f"locate structure heraldia:unicas/{sid}", r"nearest.*?\[(-?\d+), ~?(-?\d+|~), (-?\d+)\]|Could not find")
            if not m.group(1):
                fails.append(f"/locate no encuentra heraldia:unicas/{sid} con Terralith")
            else:
                ok += 1
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    log = os.path.join(a.work, "logs", "latest.log")
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else "".join(seen)
    for bad in ("Registry loading errors", "Failed to load datapacks", "Couldn't load", "Failed to parse"):
        if bad in text:
            fails.append(f"el log contiene {bad!r}")
    print("TERRALITH:", f"OK ({ok} comprobaciones)" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
