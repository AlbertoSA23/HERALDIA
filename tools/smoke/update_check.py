"""Aviso de versión nueva y nombres antiguos de los comandos en un servidor dedicado 26.3 real (T35b).

Uso: python3 tools/smoke/update_check.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Un servidor HTTP local hace de API de GitHub Releases (la propiedad del sistema heraldia.update_check.url apunta a él) y
se comprueba, con jugadores simulados (Carpet):
  1. con una versión 99.0.0 publicada para este Minecraft (más una pre-publicación más nueva y un borrador, que no
     cuentan), el servidor lo dice en la consola con el enlace y la copia de seguridad; la petición lleva el User-Agent
     genérico y ningún dato del servidor; un operador recibe el aviso al entrar, una sola vez en la sesión aunque vuelva
     a entrar, y un jugador que no es operador, nunca; /heraldia update check responde con la versión nueva;
  2. los nombres antiguos (/heraldia guia, info cerca, llave ... todas, arena parar) siguen funcionando y avisan de que
     están obsoletos con el nombre nuevo;
  3. sin red (un puerto que no responde: la conexión se queda colgada hasta el tiempo de espera), el servidor arranca
     igual, responde a los comandos mientras tanto y solo deja una línea en el log; /heraldia update check dice que no
     se pudo comprobar;
  4. con update_check.activado = false no se pregunta nada.
"""
import argparse, copy, http.server, json, os, queue, re, shutil, socket, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from trophies import CARPET
from modrinth import fetch

OPERATOR, GUEST = "Operador", "Invitado"
ROUTE = "/repos/Stufanplay/HERALDIA"
NEW_ONE = "99.0.0"
DOWNLOAD = f"https://github.com/Stufanplay/HERALDIA/releases/tag/v{NEW_ONE}"
START = r"Heraldia: (\d+) estructuras registradas"


def publications():
    jar = [{"name": f"heraldia-{NEW_ONE}.jar"}]
    return [
        {"tag_name": "v99.1.0-beta.1", "name": "Beta", "draft": False, "prerelease": True,
         "html_url": f"https://github.com/Stufanplay/HERALDIA/releases/tag/v99.1.0-beta.1", "assets": jar},
        {"tag_name": "v99.0.5", "name": "Borrador", "draft": True, "prerelease": False,
         "html_url": f"https://github.com/Stufanplay/HERALDIA/releases/tag/v99.0.5", "assets": jar},
        {"tag_name": f"v{NEW_ONE}", "name": f"Heraldia {NEW_ONE}", "draft": False, "prerelease": False, "html_url": DOWNLOAD,
         "assets": jar, "body": "## [99.0.0]"},
        {"tag_name": "v0.0.1", "name": "Vieja", "draft": False, "prerelease": False,
         "html_url": "https://github.com/Stufanplay/HERALDIA/releases/tag/v0.0.1", "assets": jar},
    ]


class Api(http.server.BaseHTTPRequestHandler):
    """La API de GitHub de mentira: la lista de publicaciones y el gradle.properties de cada etiqueta."""
    requests = []
    mc = "26.3"

    def do_GET(self):
        Api.requests.append((self.path, dict(self.headers)))
        if self.path.startswith(ROUTE + "/releases"):
            body, kind = json.dumps(publications()), "application/json"
        elif self.path == f"{ROUTE}/contents/gradle.properties?ref=v{NEW_ONE}":
            body, kind = f"mod_version={NEW_ONE}\nminecraft_version={Api.mc}\n", "text/plain"
        else:
            self.send_response(404)
            self.end_headers()
            return
        b = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


def hole():
    """Un puerto que acepta conexiones y nunca responde (como una red que se cuelga). Devuelve (puerto, socket)."""
    so = socket.socket()
    so.bind(("127.0.0.1", 0))
    so.listen(16)
    open_ones = []

    def accept():
        while True:
            try:
                c, _ = so.accept()
                open_ones.append(c)
            except OSError:
                return
    threading.Thread(target=accept, daemon=True).start()
    return so.getsockname()[1], so


class WebServer:
    def __init__(self, work, launcher, url):
        self.t0 = time.monotonic()
        self.proc = subprocess.Popen(["java", "-Xmx2G", f"-Dheraldia.update_check.url={url}", "-jar", launcher, "nogui"],
                                     cwd=work, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.lines, self.seen = queue.Queue(), []
        threading.Thread(target=s.reader, args=(self.proc, self.lines), daemon=True).start()
        self.ctx = s.Context(self.proc, self.lines, self.seen)
        s.wait_for(self.lines, START, s.START_TIMEOUT_S, self.seen)
        self.start_s = time.monotonic() - self.t0

    def wait(self, pattern, timeout=s.COMMAND_TIMEOUT_S):
        return s.wait_for(self.lines, pattern, timeout, self.seen)

    def player(self, name):
        self.ctx.run(f"player {name} spawn at 0 100 0", r"joined the game|Player .* spawn|Unknown|Incorrect")
        if not self.ctx.until(f"execute if entity @a[name={name}]"):
            raise SystemExit(f"no aparece el jugador simulado {name} (Carpet)")

    def hits(self, name):
        self.ctx.run(f"player {name} kill", r"left the game|Unknown|Incorrect")
        self.ctx.until(f"execute if entity @a[name={name}]", want=False)

    def stop(self):
        if self.proc.poll() is None:
            s.send(self.proc, "stop")
            try:
                self.proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def write(work, activado):
    cfg = copy.deepcopy(s.TEST_CONFIG)
    cfg["update_check"] = {"activado": activado}
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-update"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    props = s.gradle_properties()
    Api.mc = props["minecraft_version"]
    launcher = s.prepare(a.work, os.path.abspath(a.jar), props)
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    for f in ("ops.json", "usercache.json"):     # de una pasada anterior: el operador debe entrar sin serlo
        if os.path.exists(os.path.join(a.work, f)):
            os.remove(os.path.join(a.work, f))
    api = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Api)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{api.server_address[1]}{ROUTE}/releases?per_page=20"
    fails, ok = [], 0

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)
            print("FALLA:", msg)

    def warnings(srv, name):
        return len(re.findall(rf"Heraldia: aviso de la versión {re.escape(NEW_ONE)} a {name}\b", "".join(srv.seen)))

    srv = None
    try:
        # ---------- 1 y 2: con una versión nueva publicada ----------
        write(a.work, True)
        srv = WebServer(a.work, launcher, url)
        ctx = srv.ctx
        m = srv.wait(r"comprobación de versión nueva \(([^ ]+) para Minecraft ([^)]+)\): (\S+) en (\d+) ms")
        check(m.group(3) == NEW_ONE, f"la comprobación encuentra {m.group(3)}, se esperaba {NEW_ONE}")
        print(f"comprobación: {m.group(1)} -> {m.group(3)} para Minecraft {m.group(2)} en {m.group(4)} ms")
        m = srv.wait(r"A new version of Heraldia is available: (\S+) .*")
        line = m.group(0)
        check(NEW_ONE in line and DOWNLOAD in line and "back up" in line,
              f"la consola no da la versión, el enlace y la copia de seguridad: {line.strip()}")
        routes = [p for p, _ in Api.requests]
        check(any(p.startswith(ROUTE + "/releases") for p in routes), f"no se pidió la lista de publicaciones: {routes}")
        check(f"{ROUTE}/contents/gradle.properties?ref=v{NEW_ONE}" in routes, f"no se miró el Minecraft de la v{NEW_ONE}: {routes}")
        check(not any("beta" in p or "99.0.5" in p for p in routes), f"se miró una pre-publicación o un borrador: {routes}")
        for p, header in Api.requests:
            agent = {k.lower(): v for k, v in header.items()}.get("user-agent", "")
            check(agent == "Heraldia-update-check", f"User-Agent «{agent}» en {p}")
            surplus = {k.lower() for k in header} - {"user-agent", "accept", "host", "connection", "content-length", "upgrade",
                                                 "http2-settings", "accept-encoding"}
            check(not surplus, f"cabeceras de más en {p}: {surplus}")
            check("?" not in p or p.split("?", 1)[1] in ("per_page=20", f"ref=v{NEW_ONE}"), f"datos en la petición: {p}")

        # el operador, al entrar (una vez por sesión); el invitado, nunca
        srv.player(OPERATOR)
        srv.player(GUEST)
        ctx.run(f"op {OPERATOR}", r"Made .* a server operator|Nothing changed|Unknown|Incorrect")
        s.drain(ctx, 3)
        check(warnings(srv, OPERATOR) == 0, "entró sin ser operador: no debía recibir el aviso")
        srv.hits(OPERATOR)
        srv.player(OPERATOR)
        try:
            srv.wait(rf"Heraldia: aviso de la versión {re.escape(NEW_ONE)} a {OPERATOR}\b", 30)
        except SystemExit:
            pass
        check(warnings(srv, OPERATOR) == 1, f"el operador debía recibir el aviso una vez al entrar: {warnings(srv, OPERATOR)}")
        srv.hits(OPERATOR)
        srv.player(OPERATOR)
        s.drain(ctx, 3)
        check(warnings(srv, OPERATOR) == 1, f"al volver a entrar en la misma sesión no se repite: {warnings(srv, OPERATOR)}")
        check(warnings(srv, GUEST) == 0, "un jugador que no es operador no debe recibir el aviso")

        # /heraldia update check desde la consola
        ctx.run("heraldia update check", r"Checking for a new version|Comprobando si hay")
        m = srv.wait(rf"(?:A new version of Heraldia is available|Hay una versión nueva de Heraldia): {re.escape(NEW_ONE)}|"
                        r"Could not check|No se pudo comprobar|up to date|está al día")
        check(NEW_ONE in m.group(0), f"/heraldia update check: {m.string.strip()}")
        # (que un jugador sin permisos no lo tiene lo comprueba ComandosTest: «execute as» conserva los de la consola)

        # ---------- 2: nombres antiguos ----------
        obsolete = r"(?:“|«)([^”»]+)(?:”|») (?:is deprecated|está obsoleto)[^:]*: (?:use|usa) (/heraldia [\w ]+|\w+)"
        for old, new_one, follows in [
                ("heraldia guia", "/heraldia guide", r"player is required|jugador"),
                ("heraldia info cerca 64", "/heraldia info nearby", r"info nearby 64 en|estructuras en"),
                ("heraldia arena parar", "/heraldia arena stop", r"arena|Arena"),
                ("heraldia llave @a atlantida", "/heraldia key", r"llaves|keys|Entregadas|Given"),
                ("heraldia key @a todas", "all", r"llaves|keys|Entregadas|Given")]:
            m = ctx.run(old, obsolete)
            check(m.lastindex and m.group(2).strip() == new_one, f"{old}: aviso de obsoleto {m.string.strip()}")
            s.drain(ctx, 3)
        # hace lo mismo que el nombre nuevo: la guía al jugador
        for order in ("heraldia guia", "heraldia guide"):
            m = ctx.run(f"execute as {OPERATOR} run {order}", r"entregada a (\w+) en \d+ µs|Unknown|Incorrect")
            check(m.lastindex and m.group(1) == OPERATOR, f"/{order} no da la guía: {m.string.strip()}")
        srv.stop()
        srv = None

        # ---------- 3: sin red (la conexión se queda colgada) ----------
        harbor, cavity = hole()
        Api.requests.clear()
        srv = WebServer(a.work, launcher, f"http://127.0.0.1:{harbor}{ROUTE}/releases?per_page=20")
        ctx = srv.ctx
        print(f"sin red: arrancado en {srv.start_s:.1f} s")
        t0 = time.monotonic()
        m = ctx.run("heraldia status", r"Heraldia \S+: (?:server status|estado del servidor)")
        check(m.group(0).startswith("Heraldia"), f"el servidor no responde mientras espera a la red: {m.string.strip()}")
        check(time.monotonic() - t0 < 10, "el servidor tarda en responder mientras espera a la red")
        m = srv.wait(r"no se pudo comprobar si hay una versión nueva \(([^:]+): ", 60)
        print(f"sin red: {m.group(0).strip()}")
        ctx.run("heraldia update check", r"Checking for a new version|Comprobando si hay")
        m = srv.wait(r"Could not check for a new version|No se pudo comprobar si hay una versión nueva \(sin red|"
                        r"A new version of Heraldia", 60)
        check(m.group(0).startswith(("Could not", "No se pudo")), f"sin red, /heraldia update check: {m.string.strip()}")
        log = "".join(srv.seen)
        check("A new version of Heraldia" not in log, "sin red no puede haber aviso")
        bad_all = [l.strip() for l in log.splitlines() if "Exception" in l and "heraldia" in l.lower() and "no se pudo comprobar" not in l]
        check(not bad_all, f"excepciones en el log: {bad_all[:3]}")
        srv.stop()
        srv = None
        cavity.close()

        # ---------- 4: desactivado ----------
        write(a.work, False)
        Api.requests.clear()
        srv = WebServer(a.work, launcher, url)
        s.drain(srv.ctx, 3)
        check("aviso de versión nueva desactivado" in "".join(srv.seen), "desactivado: falta la línea del log")
        check(not Api.requests, f"con update_check.activado = false se preguntó: {Api.requests}")
    finally:
        if srv:
            srv.stop()
        api.shutdown()

    print(f"\n{ok} comprobaciones correctas, {len(fails)} fallos")
    for f in fails:
        print("  -", f)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
