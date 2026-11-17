"""Marcadores de Heraldia en los mapas web, en un servidor dedicado 26.3 real (complementa server_smoke.py).

Uso: python3 tools/smoke/mapas_web.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"

1. Sin ningún mapa web: el mod no registra nada (no sale «Heraldia: mapas web» en el log ni se escribe su fichero en el
   mundo) y /heraldia webmap refresh contesta que no hay ningún mapa.
2. Con squaremap (versión fijada de Modrinth, comprobada con su sha512) y Carpet (jugador simulado):
   - con /locate se buscan una estructura mediana y una aldea y se generan sus chunks con /forceload: las dos entran en
     el registro (heraldia_mapas_web.json del mundo) al cargarse esos chunks;
   - con mapas_web.solo_descubiertas (por defecto) squaremap no enseña ninguna: sus capas están, vacías;
   - el jugador simulado entra en la mediana: consigue su logro y, sin hacer nada más, su marcador aparece en
     squaremap (capa, posición, icono y nombre en el idioma de mapas_web.idioma); la aldea sigue sin salir;
   - con mapas_web.solo_descubiertas = false y /heraldia reload sale también la aldea; con la capa de las aldeas
     apagada, su capa desaparece del mapa;
   - tras reiniciar, los marcadores vuelven a salir sin cargar esos chunks (del fichero del mundo).
squaremap sirve las capas en http://127.0.0.1:<puerto>/tiles/minecraft_overworld/markers.json (las rehace cada 5 s).
"""
import argparse, json, os, queue, shutil, subprocess, sys, threading, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from modrinth import MODS, Mod, fetch

# squaremap (mapa web de servidor) fijado para esta prueba (python3 tools/smoke/modrinth.py --buscar squaremap); no va
# en modrinth.MODS para no tocar las pruebas de compatibilidad (COMPAT_RUTAS de tools/test.py).
SQUAREMAP = Mod("squaremap", "1.4.3", "squaremap-fabric-mc26.3-1.4.3.jar",
                "https://cdn.modrinth.com/data/PFb7ZqK6/versions/YPMtDS9D/squaremap-fabric-mc26.3-1.4.3.jar",
                "c20e76d91a1c3a26d1985240c4199b6955180a6fbaf2f13bef25e06dd9c2c01df22d51a845f4bd2d36aa953559c29532ec8c3390432fb3faa34e73bff00d8533")
CARPET = MODS["carpet"]
PLAYER = "Cartografa"
CAPAS = ["unicas", "aldeas", "medianas", "minas", "arena"]
REGISTRO = "heraldia_mapas_web.json"
_LOCATE = r"is at \[(-?\d+), [~\d-]+, (-?\d+)\]|Could not find|There is no structure"


class Servidor:
    def __init__(self, work, launcher):
        self.work = work
        self.proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=work, text=True,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.lines, self.seen = queue.Queue(), []
        threading.Thread(target=s.reader, args=(self.proc, self.lines), daemon=True).start()
        self.ctx = s.Context(self.proc, self.lines, self.seen)

    def esperar(self, patron, timeout=s.START_TIMEOUT_S):
        return s.wait_for(self.lines, patron, timeout, self.seen)

    def run(self, cmd, ok):
        return self.ctx.run(cmd, ok)

    def log(self):
        return "".join(self.seen)

    def parar(self):
        if self.proc.poll() is None:
            s.send(self.proc, "stop")
            try:
                self.proc.wait(timeout=180)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        s.pending(self.lines, self.seen)


def config(work, **mapas_web):
    """config/heraldia.json de las pruebas con las opciones mapas_web dadas (las capas, en «capas»)."""
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    cfg.pop("inventada", None)
    cfg["mapas_web"] = {"idioma": "es_es", **mapas_web}
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def squaremap_config(work):
    """config.yml de squaremap con su servidor web en un puerto libre (así se pueden lanzar varias pruebas a la vez) y sin
    buscar versiones nuevas; squaremap completa el resto. Devuelve el puerto."""
    port = s.free_port()
    os.makedirs(os.path.join(work, "squaremap"), exist_ok=True)
    with open(os.path.join(work, "squaremap", "config.yml"), "w") as f:
        f.write("config-version: 3\nsettings:\n    update-checker: false\n    internal-webserver:\n        enabled: true\n"
                f"        bind: 127.0.0.1\n        port: {port}\n")
    return port


def capas(port):
    """{id de capa de Heraldia: capa} del markers.json del Overworld que sirve squaremap (vacío si aún no lo tiene).
    squaremap 1.4 no lo escribe en disco: lo sirve desde memoria con su servidor web."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/tiles/minecraft_overworld/markers.json", timeout=5) as r:
            datos = json.load(r)
    except (OSError, ValueError):
        return {}
    return {c["id"][len("heraldia_"):]: c for c in datos if str(c.get("id", "")).startswith("heraldia_")}


def esperar_capas(port, cond, timeout=120):
    """Espera a que markers.json cumpla `cond` (squaremap lo rehace cada pocos segundos); devuelve sus capas."""
    end = time.monotonic() + timeout
    while True:
        c = capas(port)
        if cond(c):
            return c
        if time.monotonic() > end:
            return c
        time.sleep(1)


def ids(capa):
    return sorted(m.get("tooltip", "") for m in capa.get("markers", []))


def registro(work):
    f = os.path.join(work, "world", REGISTRO)
    if not os.path.isfile(f):
        return []
    with open(f, encoding="utf-8") as fh:
        return json.load(fh)["sitios"]


def esperar_registro(work, cond, timeout=120):
    end = time.monotonic() + timeout
    while True:
        r = registro(work)
        if cond(r) or time.monotonic() > end:
            return r
        time.sleep(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-mapas-web"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    jar = os.path.abspath(a.jar)
    fails = []

    def check(desc, ok, detalle=""):
        print(f"[{'OK' if ok else 'FALLO'}] {desc}" + (f": {detalle}" if detalle and not ok else ""))
        if not ok:
            fails.append(desc)
        return ok

    es = lang_del_jar(jar)

    # --- 1. sin mapas web ---
    print("== sin mapas web")
    launcher = s.prepare(a.work, jar, s.gradle_properties())
    config(a.work)
    srv = Servidor(a.work, launcher)
    try:
        srv.esperar(r"Heraldia: (\d+) estructuras registradas")
        m = srv.run("heraldia webmap refresh", r"mapa web|web map|Unknown|Incorrect")
        check("sin mapas, /heraldia webmap refresh dice que no hay ninguno", "web" in m.group(0) and "Unknown" not in m.group(0),
              m.group(0))
        srv.run("forceload add 0 0 47 47", r"Marked|Added|chunks? .*force")
        srv.ctx.ticks(40)
    finally:
        srv.parar()
    check("sin mapas, nada en el log de los mapas web", "Heraldia: mapas web" not in srv.log())
    check("sin mapas, no escribe su fichero en el mundo", not os.path.exists(os.path.join(a.work, "world", REGISTRO)))

    # --- 2. con squaremap ---
    print("== con squaremap")
    launcher = s.prepare(a.work, jar, s.gradle_properties())
    shutil.rmtree(os.path.join(a.work, "squaremap"), ignore_errors=True)
    port = squaremap_config(a.work)
    for m in (SQUAREMAP, CARPET):
        shutil.copy(fetch(a.work, m.file, m.url, m.sha512), os.path.join(a.work, "mods"))
    config(a.work)
    srv = Servidor(a.work, launcher)
    sitios = {}
    try:
        srv.esperar(r"Heraldia: mapas web: squaremap")
        srv.esperar(r"Heraldia: (\d+) estructuras registradas")
        for clase, sel in (("medianas", "#heraldia:medianas"), ("aldeas", "#heraldia:aldeas")):
            m = srv.run(f"locate structure {sel}", _LOCATE)
            if not check(f"/locate encuentra una {clase}", m.group(1) is not None, m.group(0)):
                continue
            x, z = int(m.group(1)), int(m.group(2))
            srv.run(f"forceload add {x - 16} {z - 16} {x + 16} {z + 16}", r"Marked|Added|chunks? .*force")
            sitios[clase] = (x, z)
        reg = esperar_registro(a.work, lambda r: {e["capa"] for e in r} >= set(sitios))
        check("las estructuras generadas entran en el registro del mundo", {e["capa"] for e in reg} >= set(sitios),
              json.dumps(reg)[:400])
        c = esperar_capas(port, lambda c: set(c) >= set(CAPAS))
        check("squaremap tiene las 5 capas de Heraldia", set(c) >= set(CAPAS), sorted(c))
        check("las capas llevan su nombre traducido", c.get("unicas", {}).get("name") == es.get("heraldia.mapas_web.capa.unicas"),
              str(c.get("unicas", {}).get("name")))
        check("con solo_descubiertas, nada sin descubrir", all(not v.get("markers") for v in c.values()),
              {k: len(v.get("markers", [])) for k, v in c.items()})
        mediana = next((e for e in reg if e["capa"] == "medianas"), None)
        if mediana:
            srv.run(f"player {PLAYER} spawn at {mediana['x']} {mediana['y']} {mediana['z']}", r"joined the game|already|Unknown|Incorrect")
            srv.run(f"gamemode creative {PLAYER}", r"Set .* game mode|Unknown|No player")
            c = esperar_capas(port, lambda c: c.get("medianas", {}).get("markers"))
            marcas = c.get("medianas", {}).get("markers", [])
            check("al descubrir la mediana sale su marcador sin hacer nada más", len(marcas) == 1, marcas)
            if marcas:
                mk = marcas[0]
                nombre = es.get(f"heraldia.medianas.{mediana['sub']}.nombre")
                check("el marcador está en la estructura", abs(mk["point"]["x"] - mediana["x"]) <= 1 and
                      abs(mk["point"]["z"] - mediana["z"]) <= 1, mk)
                check("el marcador lleva el icono de su capa", mk.get("icon") == "heraldia_medianas", mk.get("icon"))
                check("el marcador lleva su nombre en español", nombre and nombre in mk.get("tooltip", "") and
                      nombre in mk.get("popup", ""), mk)
                check("y su descripción", es.get("heraldia.mapas_web.descripcion.medianas") in mk.get("popup", ""), mk)
            check("la aldea, sin descubrir, sigue sin salir", not c.get("aldeas", {}).get("markers"))
        # sin solo_descubiertas: también la aldea
        config(a.work, solo_descubiertas=False)
        srv.run("heraldia reload", r"[Rr]ecarg|[Rr]eload|aplicad|applied")
        c = esperar_capas(port, lambda c: c.get("aldeas", {}).get("markers"))
        check("sin solo_descubiertas sale también la aldea", bool(c.get("aldeas", {}).get("markers")), c.get("aldeas"))
        aldea = next((e for e in reg if e["capa"] == "aldeas"), None)
        if aldea and c.get("aldeas", {}).get("markers"):
            mk = c["aldeas"]["markers"][0]
            fam = es.get(f"heraldia.familia.{aldea['sub']}", "?")
            check("la aldea se llama «Aldea: <familia>»", f"Aldea: {fam}" in mk.get("tooltip", ""), mk.get("tooltip"))
        # una capa apagada desaparece
        config(a.work, solo_descubiertas=False, capas={"aldeas": False})
        srv.run("heraldia reload", r"[Rr]ecarg|[Rr]eload|aplicad|applied")
        c = esperar_capas(port, lambda c: "aldeas" not in c and c.get("medianas", {}).get("markers"))
        check("con su capa apagada, la de las aldeas no sale", "aldeas" not in c and bool(c.get("medianas")), sorted(c))
        # la consola contesta en el idioma del servidor (en_us) o, sin él, con el respaldo en español
        m = srv.run("heraldia webmap refresh", r"(?:Mapas web actualizados|Web maps updated): (\d+) (?:marcadores en|markers on) "
                                              r"([^(]+) \((\d+)|Unknown|Incorrect")
        check("/heraldia webmap refresh publica y cuenta", m.group(1) is not None and "squaremap" in (m.group(2) or ""), m.group(0))
        srv.run("forceload remove all", r"Removed|No force|Unmarked|chunks")
    finally:
        srv.parar()
    log = srv.log()
    check("sin errores de los mapas web en el log", "no aceptó los marcadores" not in log and "no se pudo usar" not in log,
          "\n".join(l for l in srv.seen if "mapas web" in l)[:600])

    # --- 3. tras reiniciar: del fichero del mundo, sin volver a cargar esos chunks ---
    print("== reinicio")
    antes = len(registro(a.work))
    shutil.rmtree(os.path.join(a.work, "logs"), ignore_errors=True)
    config(a.work, solo_descubiertas=False)
    srv = Servidor(a.work, launcher)
    try:
        m = srv.esperar(r"Heraldia: mapas web: (\d+) estructuras conocidas \((\d+) del fichero\)")
        check("al arrancar lee el registro del mundo", int(m.group(2)) == antes and antes >= 2, m.group(0))
        c = esperar_capas(port, lambda c: c.get("aldeas", {}).get("markers") and c.get("medianas", {}).get("markers"))
        check("tras reiniciar vuelven a salir los marcadores", bool(c.get("aldeas", {}).get("markers")) and
              bool(c.get("medianas", {}).get("markers")), {k: len(v.get("markers", [])) for k, v in c.items()})
    finally:
        srv.parar()
    print("PRUEBA MAPAS WEB " + ("OK" if not fails else "FALLIDA: " + ", ".join(fails)))
    return 1 if fails else 0


def lang_del_jar(jar):
    import zipfile
    with zipfile.ZipFile(jar) as z:
        return json.loads(z.read("assets/heraldia/lang/es_es.json"))


if __name__ == "__main__":
    sys.exit(main())
