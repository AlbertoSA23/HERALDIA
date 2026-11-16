"""Prueba con Terralith (mod de biomas) en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/terralith_biomas.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Descarga de Modrinth versiones fijadas de Terralith y Lithostitched (comprobadas con su sha512) y la pone junto a Heraldia y Fabric API.
Comprueba: el servidor arranca sin errores de registro y con todas las estructuras; los biomas de Terralith que añaden
sus etiquetas convencionales (#c:...) entran en las etiquetas de Heraldia (/locate biome + execute if biome) y los que
no deben, no; y /locate sigue encontrando las únicas cuyo bioma comparte Terralith.
"""
import argparse, os, queue, shutil, subprocess, sys, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import modrinth
from modrinth import fetch     # la importan otras pruebas desde aquí

# Mods de Modrinth fijados en modrinth.py: Terralith y su dependencia Lithostitched (las dos piden Fabric API).
MODS = [(m.file, m.url, m.sha512) for m in (modrinth.MODS["terralith"], modrinth.MODS["lithostitched"])]
# (bioma de Terralith, etiqueta de Heraldia, ¿debe entrar?). Los positivos llegan por las #c: de biomas.CONVENCIONALES.
EXPECTED = [
    ("terralith:steppe", "llanuras", True), ("terralith:highlands", "unicas/castillo", True),
    ("terralith:lavender_forest", "unicas/catedral", True), ("terralith:birch_taiga", "bosque", True),
    ("terralith:birch_taiga", "unicas/santuario", True),
    ("terralith:desert_oasis", "desierto", True), ("terralith:desert_oasis", "unicas/acueducto", True),
    ("terralith:white_mesa", "badlands", True), ("terralith:tropical_jungle", "jungla", True),
    ("terralith:orchid_swamp", "pantano", True), ("terralith:gravel_beach", "unicas/faro", True),
    ("terralith:steppe", "bosque", False), ("terralith:desert_oasis", "unicas/piramide", False),
    ("terralith:lavender_forest", "oscuro", False),
]
LOCATE = ["castillo", "catedral", "acueducto"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-terralith"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    # en la CI este job solo tiene el .jar: las estructuras se cuentan dentro de él
    with zipfile.ZipFile(a.jar) as z:
        expected = sum(n.startswith("data/heraldia/worldgen/structure/") and n.endswith(".json") for n in z.namelist())
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
            s.run(proc, lines, seen, f"forceload add {x} {z}", r"Marked|force|already")
            for _ in range(s.PLACE_ATTEMPTS):     # el chunk tarda en cargarse: «That position is not loaded»
                m = s.run(proc, lines, seen, f"execute if biome {x} {y} {z} #heraldia:{tag}", r"Test passed|Test failed")
                if "not loaded" not in m.string:
                    break
                time.sleep(s.PLACE_RETRY_S)
            s.run(proc, lines, seen, f"forceload remove {x} {z}", r"Unmarked|force|not")
            if "Test " not in m.group(0) or ("passed" in m.group(0)) != inside:
                fails.append(f"{biome} {'debería' if inside else 'no debería'} estar en #heraldia:{tag}: {m.string.strip()}")
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
