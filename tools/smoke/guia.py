"""Guía del Heraldo en un servidor dedicado 26.3 real, con jugadores simulados (Carpet, como trofeos.py).

Uso: python3 tools/smoke/guia.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Lee del .jar heraldia/guia.json, las únicas y los textos en_us, y comprueba:
  - al entrar por primera vez, el jugador recibe un solo libro (written_book con la marca heraldia_guia_libro = versión
    del mod), con el título, el autor, sus páginas traducibles con el respaldo en inglés (el idioma del jugador simulado),
    tantas páginas como dice guia.json para 0 únicas descubiertas, y la pista de cada única;
  - al salir y volver a entrar (y tras reiniciar el servidor) no se le da otra: «ya entregada» se guarda en el jugador;
  - /heraldia guide da una copia al día: con una única descubierta (/advancement grant) sale su nombre en el diario y no
    su pista; pedida otra vez, cambia la del inventario en vez de sumar otra;
  - con guia.entregar_al_entrar = false, un jugador nuevo no la recibe al entrar, pero sí al pedirla.
Mide lo que tarda en armarse y entregarse (línea «Guía del Heraldo ... entregada a ... en N µs» del log).
"""
import argparse, json, math, os, queue, re, shutil, subprocess, sys, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomas import fetch
from trofeos import CARPET

PLAYER, NUEVO = "Testigo", "Aprendiz"
X, Y, Z = 0, 101, 0
DESCUBIERTA = "castillo"
ENTREGA = re.compile(r"Guía del Heraldo \(([^,]+), ([^)]+)\) entregada a (\w+) en (\d+) µs")


def jar_data(jar):
    with zipfile.ZipFile(jar) as z:
        datos = json.loads(z.read("heraldia/guia.json"))
        lang = json.loads(z.read("assets/heraldia/lang/en_us.json"))
        pre = "data/heraldia/worldgen/structure/unicas/"
        unicas = sorted(n[len(pre):-5] for n in z.namelist() if n.startswith(pre) and n.endswith(".json"))
    return datos, lang, unicas


class Server:
    def __init__(self, work, launcher):
        self.proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=work, text=True,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lines, self.seen = queue.Queue(), []
        threading.Thread(target=s.reader, args=(self.proc, lines), daemon=True).start()
        self.ctx = s.Context(self.proc, lines, self.seen)
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, self.seen)

    def stop(self):
        if self.proc.poll() is None:
            s.send(self.proc, "stop")
            try:
                self.proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def spawn(self, name):
        self.ctx.run(f"player {name} spawn at {X} {Y} {Z}", r"joined the game|Player .* spawn|Unknown|Incorrect")
        if not self.ctx.until(f"execute if entity @a[name={name}]"):
            raise SystemExit(f"no aparece el jugador simulado {name} (Carpet)")

    def leave(self, name):
        self.ctx.run(f"player {name} kill", r"left the game|Unknown|Incorrect")
        self.ctx.until(f"execute if entity @a[name={name}]", want=False)

    def books(self, name, version=None):
        """Cuántas guías lleva (con la marca de `version`, o cualquier libro escrito si es None)."""
        pred = "minecraft:written_book" + (f'[minecraft:custom_data={{heraldia_guia_libro:"{version}"}}]' if version else "")
        m = self.ctx.run(f"execute if items entity {name} container.* {pred}", r"Test passed\. Count: (\d+)|Test failed")
        return int(m.group(1) or 0)

    def inventory(self, name):
        m = self.ctx.run(f"data get entity {name} Inventory", r"has the following entity data: (.*)|No entity")
        return (m.group(1) or "").replace("\\", "")


def check_book(data, lang, datos, unicas, descubiertas, fails, cuando):
    """Comprueba el libro del inventario (SNBT de data get): título, autor, páginas y diario."""
    n = len(unicas) - len(descubiertas)
    pages = len(datos["paginas"]) + 1 + math.ceil(len(descubiertas) / datos["nombres_por_pagina"]) + \
        math.ceil(n / datos["pistas_por_pagina"])
    want = ['id: "minecraft:written_book"', f'author: "{datos["autor"]}"', lang["heraldia.guia.nombre"],
            '"heraldia.guia.pagina.bienvenida"', lang["heraldia.guia.pagina.bienvenida"][:40], '"heraldia.guia.resumen"']
    want += [f'"heraldia.historia.{sid}.pista"' for sid in unicas if sid not in descubiertas]
    want += [f'"heraldia.unicas.{sid}.nombre"' for sid in descubiertas]
    missing = [w for w in want if w not in data]
    if missing:
        fails.append(f"{cuando}: al libro le falta {missing[:5]}: {data[:400]}")
    for sid in descubiertas:
        if f'"heraldia.historia.{sid}.pista"' in data:
            fails.append(f"{cuando}: el diario da la pista de {sid}, que ya está descubierta")
    titles = {k: len(re.findall(rf'"heraldia\.guia\.{k}"', data)) for k in
              ("pistas", "descubiertas", "resumen.titulo")}
    got = len(datos["paginas"]) + titles["resumen.titulo"] + titles["descubiertas"] + titles["pistas"]
    if got != pages:
        fails.append(f"{cuando}: {got} páginas ({titles}), deberían ser {pages}")
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-guia"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    datos, lang, unicas = jar_data(a.jar)
    version = s.gradle_properties()["mod_version"]
    fails, tiempos = [], []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    srv = Server(a.work, launcher)
    try:
        ctx = srv.ctx
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        for _ in range(s.PLACE_ATTEMPTS):
            m = ctx.run(f"fill {X - 3} {Y - 1} {Z - 3} {X + 3} {Y - 1} {Z + 3} minecraft:stone", r"Successfully filled|No blocks")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        for rule in ("spawn_mobs", "advance_time"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
        # 1) primera vez: un solo libro, con todo el diario por descubrir
        srv.spawn(PLAYER)
        ctx.run(f"gamemode survival {PLAYER}", r"Set .* game mode|game mode")
        if not ctx.until(f"execute if items entity {PLAYER} container.* minecraft:written_book"):
            fails.append("al entrar por primera vez no recibe la guía")
        elif srv.books(PLAYER, version) != 1:
            fails.append(f"al entrar recibe {srv.books(PLAYER)} libros, no 1 con la marca de la versión {version}")
        else:
            pages = check_book(srv.inventory(PLAYER), lang, datos, unicas, [], fails, "al entrar")
            print(f"guía al entrar: {pages} páginas, {len(unicas)} únicas por descubrir")
        # 2) volver a entrar: no se da otra
        ctx.run(f"clear {PLAYER} minecraft:written_book", r"Removed|No items")
        srv.leave(PLAYER)
        antes = len(ENTREGA.findall("".join(srv.seen)))
        srv.spawn(PLAYER)
        if srv.books(PLAYER) or len(ENTREGA.findall("".join(srv.seen))) != antes:
            fails.append("al volver a entrar recibe otra guía")
        # 3) /heraldia guide con una única descubierta; pedida dos veces, sigue habiendo una
        ctx.run(f"advancement grant {PLAYER} only heraldia:unicas/{DESCUBIERTA}/descubrir", r"Granted|granted|Couldn't")
        for _ in range(2):
            ctx.run(f"execute as {PLAYER} run heraldia guide", r"entregada a \w+ en \d+ µs|Unknown|Incorrect")
        if srv.books(PLAYER, version) != 1:
            fails.append(f"tras pedirla dos veces lleva {srv.books(PLAYER)} guías, no 1")
        else:
            check_book(srv.inventory(PLAYER), lang, datos, unicas, [DESCUBIERTA], fails, "pedida")
        srv.leave(PLAYER)
    finally:
        srv.stop()
    tiempos += [int(m.group(4)) for m in ENTREGA.finditer("".join(srv.seen))]
    # 4) tras reiniciar: lo entregado sigue guardado; con la opción desactivada, un jugador nuevo no la recibe al entrar
    cfg_path = os.path.join(a.work, "config", "heraldia.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("guia", {}).get("entregar_al_entrar") is not True:
        fails.append(f"config/heraldia.json no trae guia.entregar_al_entrar = true: {cfg.get('guia')}")
    srv = Server(a.work, launcher)
    try:
        ctx = srv.ctx
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        srv.spawn(PLAYER)
        if srv.books(PLAYER, version) != 1 or ENTREGA.search("".join(srv.seen)):
            fails.append(f"tras reiniciar el servidor recibe otra guía al entrar (no se guardó que ya la tenía): "
                         f"{srv.books(PLAYER)} libros")
        srv.leave(PLAYER)
    finally:
        srv.stop()
    tiempos += [int(m.group(4)) for m in ENTREGA.finditer("".join(srv.seen))]
    cfg.setdefault("guia", {})["entregar_al_entrar"] = False
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    srv = Server(a.work, launcher)
    try:
        ctx = srv.ctx
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        srv.spawn(NUEVO)
        if srv.books(NUEVO):
            fails.append("con guia.entregar_al_entrar = false, un jugador nuevo la recibe al entrar")
        ctx.run(f"execute as {NUEVO} run heraldia guide", r"entregada a \w+ en \d+ µs|Unknown|Incorrect")
        if srv.books(NUEVO, version) != 1:
            fails.append("con la opción desactivada, /heraldia guide no da la guía")
        srv.leave(NUEVO)
    finally:
        srv.stop()
    seen = "".join(srv.seen)
    tiempos += [int(m.group(4)) for m in ENTREGA.finditer(seen)]
    log = os.path.join(a.work, "logs", "latest.log")
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else seen
    for bad in ("Registry loading errors", "Failed to load datapacks", "Couldn't load", "Failed to parse",
                "Found validation problems"):
        if bad in text:
            fails.append(f"el log contiene {bad!r}")
    if tiempos:
        print(f"guía armada y entregada {len(tiempos)} veces: {min(tiempos)}-{max(tiempos)} µs (mediana "
              f"{sorted(tiempos)[len(tiempos) // 2]} µs)")
    print("GUÍA:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
