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
from trofeos import CARPET
from modrinth import fetch

OPERADOR, INVITADO = "Operador", "Invitado"
RUTA = "/repos/AlbertoSA23/HERALDIA"
NUEVA = "99.0.0"
DESCARGA = f"https://github.com/AlbertoSA23/HERALDIA/releases/tag/v{NUEVA}"
ARRANQUE = r"Heraldia: (\d+) estructuras registradas"


def publicaciones():
    jar = [{"name": f"heraldia-{NUEVA}.jar"}]
    return [
        {"tag_name": "v99.1.0-beta.1", "name": "Beta", "draft": False, "prerelease": True,
         "html_url": f"https://github.com/AlbertoSA23/HERALDIA/releases/tag/v99.1.0-beta.1", "assets": jar},
        {"tag_name": "v99.0.5", "name": "Borrador", "draft": True, "prerelease": False,
         "html_url": f"https://github.com/AlbertoSA23/HERALDIA/releases/tag/v99.0.5", "assets": jar},
        {"tag_name": f"v{NUEVA}", "name": f"Heraldia {NUEVA}", "draft": False, "prerelease": False, "html_url": DESCARGA,
         "assets": jar, "body": "## [99.0.0]"},
        {"tag_name": "v0.0.1", "name": "Vieja", "draft": False, "prerelease": False,
         "html_url": "https://github.com/AlbertoSA23/HERALDIA/releases/tag/v0.0.1", "assets": jar},
    ]


class Api(http.server.BaseHTTPRequestHandler):
    """La API de GitHub de mentira: la lista de publicaciones y el gradle.properties de cada etiqueta."""
    peticiones = []
    mc = "26.3"

    def do_GET(self):
        Api.peticiones.append((self.path, dict(self.headers)))
        if self.path.startswith(RUTA + "/releases"):
            cuerpo, tipo = json.dumps(publicaciones()), "application/json"
        elif self.path == f"{RUTA}/contents/gradle.properties?ref=v{NUEVA}":
            cuerpo, tipo = f"mod_version={NUEVA}\nminecraft_version={Api.mc}\n", "text/plain"
        else:
            self.send_response(404)
            self.end_headers()
            return
        b = cuerpo.encode()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


def agujero():
    """Un puerto que acepta conexiones y nunca responde (como una red que se cuelga). Devuelve (puerto, socket)."""
    so = socket.socket()
    so.bind(("127.0.0.1", 0))
    so.listen(16)
    abiertas = []

    def aceptar():
        while True:
            try:
                c, _ = so.accept()
                abiertas.append(c)
            except OSError:
                return
    threading.Thread(target=aceptar, daemon=True).start()
    return so.getsockname()[1], so


class Servidor:
    def __init__(self, work, launcher, url):
        self.t0 = time.monotonic()
        self.proc = subprocess.Popen(["java", "-Xmx2G", f"-Dheraldia.update_check.url={url}", "-jar", launcher, "nogui"],
                                     cwd=work, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.lines, self.seen = queue.Queue(), []
        threading.Thread(target=s.reader, args=(self.proc, self.lines), daemon=True).start()
        self.ctx = s.Context(self.proc, self.lines, self.seen)
        s.wait_for(self.lines, ARRANQUE, s.START_TIMEOUT_S, self.seen)
        self.arranque_s = time.monotonic() - self.t0

    def esperar(self, patron, timeout=s.COMMAND_TIMEOUT_S):
        return s.wait_for(self.lines, patron, timeout, self.seen)

    def jugador(self, nombre):
        self.ctx.run(f"player {nombre} spawn at 0 100 0", r"joined the game|Player .* spawn|Unknown|Incorrect")
        if not self.ctx.until(f"execute if entity @a[name={nombre}]"):
            raise SystemExit(f"no aparece el jugador simulado {nombre} (Carpet)")

    def sale(self, nombre):
        self.ctx.run(f"player {nombre} kill", r"left the game|Unknown|Incorrect")
        self.ctx.until(f"execute if entity @a[name={nombre}]", want=False)

    def stop(self):
        if self.proc.poll() is None:
            s.send(self.proc, "stop")
            try:
                self.proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def escribir(work, activado):
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
    api = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Api)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{api.server_address[1]}{RUTA}/releases?per_page=20"
    fails, ok = [], 0

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)
            print("FALLA:", msg)

    def avisos(srv, nombre):
        return len(re.findall(rf"Heraldia: aviso de la versión {re.escape(NUEVA)} a {nombre}\b", "".join(srv.seen)))

    srv = None
    try:
        # ---------- 1 y 2: con una versión nueva publicada ----------
        escribir(a.work, True)
        srv = Servidor(a.work, launcher, url)
        ctx = srv.ctx
        m = srv.esperar(r"comprobación de versión nueva \(([^ ]+) para Minecraft ([^)]+)\): (\S+) en (\d+) ms")
        check(m.group(3) == NUEVA, f"la comprobación encuentra {m.group(3)}, se esperaba {NUEVA}")
        print(f"comprobación: {m.group(1)} -> {m.group(3)} para Minecraft {m.group(2)} en {m.group(4)} ms")
        m = srv.esperar(r"A new version of Heraldia is available: (\S+) .*")
        linea = m.group(0)
        check(NUEVA in linea and DESCARGA in linea and "back up" in linea,
              f"la consola no da la versión, el enlace y la copia de seguridad: {linea.strip()}")
        rutas = [p for p, _ in Api.peticiones]
        check(any(p.startswith(RUTA + "/releases") for p in rutas), f"no se pidió la lista de publicaciones: {rutas}")
        check(f"{RUTA}/contents/gradle.properties?ref=v{NUEVA}" in rutas, f"no se miró el Minecraft de la v{NUEVA}: {rutas}")
        check(not any("beta" in p or "99.0.5" in p for p in rutas), f"se miró una pre-publicación o un borrador: {rutas}")
        for p, cab in Api.peticiones:
            agente = {k.lower(): v for k, v in cab.items()}.get("user-agent", "")
            check(agente == "Heraldia-update-check", f"User-Agent «{agente}» en {p}")
            sobran = {k.lower() for k in cab} - {"user-agent", "accept", "host", "connection", "content-length", "upgrade",
                                                 "http2-settings", "accept-encoding"}
            check(not sobran, f"cabeceras de más en {p}: {sobran}")
            check("?" not in p or p.split("?", 1)[1] in ("per_page=20", f"ref=v{NUEVA}"), f"datos en la petición: {p}")

        # el operador, al entrar (una vez por sesión); el invitado, nunca
        srv.jugador(OPERADOR)
        srv.jugador(INVITADO)
        ctx.run(f"op {OPERADOR}", r"Made .* a server operator|Nothing changed|Unknown|Incorrect")
        s.drain(ctx, 3)
        check(avisos(srv, OPERADOR) == 0, "entró sin ser operador: no debía recibir el aviso")
        srv.sale(OPERADOR)
        srv.jugador(OPERADOR)
        try:
            srv.esperar(rf"Heraldia: aviso de la versión {re.escape(NUEVA)} a {OPERADOR}\b", 30)
        except SystemExit:
            pass
        check(avisos(srv, OPERADOR) == 1, f"el operador debía recibir el aviso una vez al entrar: {avisos(srv, OPERADOR)}")
        srv.sale(OPERADOR)
        srv.jugador(OPERADOR)
        s.drain(ctx, 3)
        check(avisos(srv, OPERADOR) == 1, f"al volver a entrar en la misma sesión no se repite: {avisos(srv, OPERADOR)}")
        check(avisos(srv, INVITADO) == 0, "un jugador que no es operador no debe recibir el aviso")

        # /heraldia update check desde la consola
        ctx.run("heraldia update check", r"Checking for a new version|Comprobando si hay")
        m = srv.esperar(rf"(?:A new version of Heraldia is available|Hay una versión nueva de Heraldia): {re.escape(NUEVA)}|"
                        r"Could not check|No se pudo comprobar|up to date|está al día")
        check(NUEVA in m.group(0), f"/heraldia update check: {m.string.strip()}")
        # un jugador sin permisos no lo tiene
        m = ctx.run(f"execute as {INVITADO} run heraldia update check", r"Checking for a new version|Comprobando si hay|"
                                                                         r"Unknown or incomplete|Incorrect|Unknown command")
        check(not m.group(0).startswith(("Checking", "Comprobando")), "un jugador sin permisos puede usar /heraldia update check")

        # ---------- 2: nombres antiguos ----------
        obsoleto = r"(?:“|«)([^”»]+)(?:”|») (?:is deprecated|está obsoleto)[^:]*: (?:use|usa) (/heraldia [\w ]+|\w+)"
        for antigua, nueva, sigue in [
                ("heraldia guia", "/heraldia guide", r"player is required|jugador"),
                ("heraldia info cerca 64", "/heraldia info nearby", r"info nearby 64 en|estructuras en"),
                ("heraldia arena parar", "/heraldia arena stop", r"arena|Arena"),
                ("heraldia llave @a todas", "all", r"llaves|keys|Entregadas|Given")]:
            m = ctx.run(antigua, obsoleto)
            check(m.lastindex and m.group(2).strip() == nueva, f"{antigua}: aviso de obsoleto {m.string.strip()}")
            s.drain(ctx, 3)
        # hace lo mismo que el nombre nuevo: la guía al jugador
        for orden in ("heraldia guia", "heraldia guide"):
            m = ctx.run(f"execute as {OPERADOR} run {orden}", r"entregada a (\w+) en \d+ µs|Unknown|Incorrect")
            check(m.lastindex and m.group(1) == OPERADOR, f"/{orden} no da la guía: {m.string.strip()}")
        srv.stop()
        srv = None

        # ---------- 3: sin red (la conexión se queda colgada) ----------
        puerto, hueco = agujero()
        Api.peticiones.clear()
        srv = Servidor(a.work, launcher, f"http://127.0.0.1:{puerto}{RUTA}/releases?per_page=20")
        ctx = srv.ctx
        print(f"sin red: arrancado en {srv.arranque_s:.1f} s")
        t0 = time.monotonic()
        m = ctx.run("heraldia status", r"Heraldia \S+: (?:server status|estado del servidor)")
        check(m.group(0).startswith("Heraldia"), f"el servidor no responde mientras espera a la red: {m.string.strip()}")
        check(time.monotonic() - t0 < 10, "el servidor tarda en responder mientras espera a la red")
        m = srv.esperar(r"no se pudo comprobar si hay una versión nueva \(([^:]+): ", 60)
        print(f"sin red: {m.group(0).strip()}")
        ctx.run("heraldia update check", r"Checking for a new version|Comprobando si hay")
        m = srv.esperar(r"Could not check for a new version|No se pudo comprobar si hay una versión nueva \(sin red|"
                        r"A new version of Heraldia", 60)
        check(m.group(0).startswith(("Could not", "No se pudo")), f"sin red, /heraldia update check: {m.string.strip()}")
        log = "".join(srv.seen)
        check("A new version of Heraldia" not in log, "sin red no puede haber aviso")
        malas = [l.strip() for l in log.splitlines() if "Exception" in l and "heraldia" in l.lower() and "no se pudo comprobar" not in l]
        check(not malas, f"excepciones en el log: {malas[:3]}")
        srv.stop()
        srv = None
        hueco.close()

        # ---------- 4: desactivado ----------
        escribir(a.work, False)
        Api.peticiones.clear()
        srv = Servidor(a.work, launcher, url)
        srv.esperar(r"aviso de versión nueva desactivado", 30)
        s.drain(srv.ctx, 3)
        check(not Api.peticiones, f"con update_check.activado = false se preguntó: {Api.peticiones}")
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
