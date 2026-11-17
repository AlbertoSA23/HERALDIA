"""Encargos del tablón y reputación por aldea en un servidor dedicado 26.3 real (T38).

Uso: python3 tools/smoke/encargos.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-encargos"
Con Carpet (jugador simulado) y una aldea generada de verdad (la más cercana al 0,0, como aldeas_vida.py: el tablón se
reconoce por la estructura y el alguacil, y /place structure no guarda el inicio en el chunk). Determinista: la semilla
de las pruebas, la misma aldea y el mismo periodo dan siempre el mismo tablón (el primero, de traer; el segundo, de
guardián, porque hay únicas a menos de 4.000 bloques).
Primer arranque:
  - el jugador toca el atril del tablón: el servidor lo apunta («mira el tablón») y saca el tablón de 2 a 4 encargos;
  - /heraldia quest accept 1 (traer) y 2 (guardián); traer sin los objetos no se entrega; con ellos, sí: quita los
    objetos, paga las esmeraldas y sube la reputación;
  - guardián: un mob con las etiquetas del guardián de esa única, junto al sitio del encargo, muerto con /damage por
    el jugador, cumple el encargo; al entregarlo, sus esmeraldas y la reputación llegan a «conocido»;
  - un aldeano de la plaza con un trato fijo de 10 esmeraldas: sin reputación el precio no cambia; con «conocido», baja
    a 9 (10 %);
  - golpear a ese aldeano baja la reputación; se acepta y abandona otro; /heraldia status cuenta los encargos.
Segundo arranque (mismo mundo): el tablón es el mismo, el jugador conserva lo entregado (no puede volver a aceptar el 1),
su reputación y el precio rebajado; con encargos.activado y reputacion.activado a false y /heraldia reload, los
encargos dicen que están desactivados y el precio vuelve a 10.
"""
import argparse, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomas import fetch
from trofeos import CARPET
from aldeas_vida import Server, plaza, RADIUS, BOT, SPOT, ATTEMPTS, RETRY_S

PLAYER = "Testigo"
PRECIO = 10
TABLON = re.compile(r"Heraldia: encargos: tablón de (.+?) \((-?\d+), (-?\d+)\), periodo (\d+): (.*)")
ENCARGO = re.compile(r"(\d)=(\w+):(\S*?):(\d+)@(-?\d+),(-?\d+)")
VILLAGER = ('summon minecraft:villager {x} {y} {z} {{NoAI:1b,PersistenceRequired:1b,Invulnerable:0b,Tags:["heraldia_prueba"],'
            'VillagerData:{{profession:"minecraft:librarian",level:2,type:"minecraft:plains"}},Xp:20,'
            'Offers:{{Recipes:[{{buy:{{id:"minecraft:emerald",count:%d}},sell:{{id:"minecraft:book",count:1}},maxUses:99,'
            'uses:0,xp:1,priceMultiplier:0.0f,specialPrice:0,demand:0}}]}}}}' % PRECIO)


def write_config(work, extra=None):
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    for k, v in (extra or {}).items():
        cfg.setdefault(k, {}).update(v)
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def como(srv, cmd, ok, at=True):
    """La orden ejecutada por el jugador simulado (respuesta en la consola: «execute as» conserva la fuente)."""
    return srv.run(f"execute as {PLAYER} {'at @s ' if at else ''}run {cmd}", ok)


def tablon(srv, fails, accion):
    """Hace `accion` (que pide el tablón) y devuelve (nombre, encargos) de la línea del log del tablón."""
    m = accion()
    if m is None or not m.group(0).startswith("Heraldia: encargos: tablón"):
        m = s.wait_for(srv.ctx.lines, TABLON.pattern, s.COMMAND_TIMEOUT_S, srv.seen)
    g = TABLON.search(m.group(0))
    encargos = [(int(a), t, o, int(c), int(x), int(z)) for a, t, o, c, x, z in ENCARGO.findall(g.group(5))]
    print(f"tablón de {g.group(1)} ({g.group(2)}, {g.group(3)}), periodo {g.group(4)}: {encargos}")
    if not 2 <= len(encargos) <= 4:
        fails.append(f"el tablón tiene {len(encargos)} encargos (deben ser de 2 a 4)")
    return g.group(1), g.group(4), encargos


def esmeraldas(srv):
    m = srv.run(f"clear {PLAYER} minecraft:emerald 0", r"Found (\d+) matching|No items")
    return int(m.group(1) or 0)


def mirar_y_usar(srv, pos, desde, y):
    srv.run(f"tp {PLAYER} {desde[0]} {y} {desde[1]}", r"Teleported")
    s.send(srv.proc, f"player {PLAYER} look at {pos[0]} {pos[1]} {pos[2]}")
    srv.ctx.ticks(2)
    s.send(srv.proc, f"player {PLAYER} use once")   # no responde nada en la consola


def precio(srv, spot, y, bot):
    """Invoca el aldeano del trato fijo, el jugador abre sus tratos y devuelve el specialPrice que queda (o None)."""
    srv.run("kill @e[tag=heraldia_prueba]", r"Killed|No entity was found")
    for _ in range(ATTEMPTS):
        m = srv.run(VILLAGER.format(x=spot[0], y=y, z=spot[1]), r"Summoned")
        if "Summoned" in m.group(0):
            break
        time.sleep(RETRY_S)
    for _ in range(10):
        mirar_y_usar(srv, (spot[0], y + 1.2, spot[1]), bot, y)
        srv.ctx.ticks(4)
        m = srv.run("data get entity @e[tag=heraldia_prueba,limit=1] Offers.Recipes[0].specialPrice",
                    r"has the following entity data: (-?\d+)|Found no elements|No entity")
        if m.group(1) is not None and m.group(1) != "0":
            return int(m.group(1))
    return int(m.group(1)) if m.group(1) is not None else None


def cerrar(srv):
    """Cierra los tratos (vanilla quita entonces la rebaja): el jugador se va lejos un instante."""
    srv.run(f"tp {PLAYER} ~ ~ ~100", r"Teleported")
    srv.ctx.ticks(4)


def lectern_de(srv, alg):
    bx, by, bz = int(alg[0] // 1), int(alg[1] // 1), int(alg[2] // 1)
    for ex, ez in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if srv.test(f"execute if block {bx + ex} {by} {bz + ez} minecraft:lectern"):
            return (bx + ex, by, bz + ez), (bx + 3 * ex, bz + 3 * ez)   # el atril y el sitio delante (lejos del alguacil)
    return None, None


def estado(srv):
    """Los encargos entregados entre todos según /heraldia status (recorre sus páginas)."""
    pat = re.compile(r"(?:handed in by everyone|entregados entre todos): (\d+)")
    for pagina in range(1, 6):
        m = como(srv, f"heraldia status {pagina}", r"server status \(page (\d+) of (\d+)\)|estado del servidor \(página (\d+) de (\d+)\)",
                 at=False)
        for linea in s.drain(srv.ctx):
            if pat.search(linea):
                return pat.search(linea).group(1)
        if (m.group(1) or m.group(3)) == (m.group(2) or m.group(4)):
            return None
    return None


def primera_vuelta(srv, fails, found):
    style, to_world, y, alg = found
    spot, bot = to_world(SPOT), to_world(BOT)
    srv.run(f"player {PLAYER} spawn at {bot[0]} {y} {bot[1]}", r"joined the game")
    if not srv.until(f"execute if entity @a[name={PLAYER}]"):
        raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
    srv.run(f"gamemode survival {PLAYER}", r"Set .* game mode|game mode")
    srv.run(f"clear {PLAYER}", r"Removed|No items")
    lec, delante = lectern_de(srv, alg)
    if lec is None:
        fails.append("no hay atril junto al alguacil")
        return None
    # 1) tocar el atril del tablón: el tablón sale en el chat (y se apunta en el log)
    mirar_y_usar(srv, (lec[0] + 0.5, lec[1] + 0.6, lec[2] + 0.5), delante, y)
    m = s.wait_for(srv.ctx.lines, rf"Heraldia: encargos: {PLAYER} mira el tablón de (.+)", s.COMMAND_TIMEOUT_S, srv.seen)
    nombre_atril = m.group(1).strip()
    nombre, periodo, enc = tablon(srv, fails, lambda: None)
    if nombre != nombre_atril:
        fails.append(f"el atril es de {nombre_atril} y el tablón de {nombre}")
    tipos = [t for _, t, *_ in enc]
    if tipos[:2] != ["traer", "guardian"]:
        fails.append(f"el tablón empieza por {tipos[:2]} (debe ser traer y guardián: hay únicas cerca)")
        return None
    srv.run(f"tp {PLAYER} {bot[0]} {y} {bot[1]}", r"Teleported")
    # control: sin reputación con la aldea, el trato fijo no cambia de precio
    antes = precio(srv, spot, y, bot) or 0
    if antes != 0:
        fails.append(f"precio sin reputación: specialPrice {antes} (debe ser 0)")
    cerrar(srv)
    srv.run(f"tp {PLAYER} {bot[0]} {y} {bot[1]}", r"Teleported")
    # 2) aceptar el de traer y el del guardián
    _, _, item, cantidad, _, _ = enc[0]
    _, _, sid, _, gx, gz = enc[1]
    for n in (1, 2):
        como(srv, f"heraldia quest accept {n}", rf"Heraldia: encargos: {PLAYER} acepta")
    m = como(srv, "heraldia quest accept 1", r"already have that job|Ya tienes ese encargo")
    print(f"aceptados: traer {cantidad} × {item}, guardián de {sid} en {gx}, {gz}")
    # 3) traer: sin los objetos no se entrega; con ellos, sí
    como(srv, "heraldia quest turnin", r"not enough yet|aún no basta")
    srv.run(f"give {PLAYER} {item} {cantidad + 3}", r"Gave")
    m = como(srv, "heraldia quest turnin", rf"Heraldia: encargos: {PLAYER} entrega .*reputación (-?\d+) \((\w+)\)")
    rep1 = int(m.group(1))
    em1 = esmeraldas(srv)
    m = srv.run(f"clear {PLAYER} {item} 0", r"Found (\d+) matching|No items")
    if int(m.group(1) or 0) != 3:
        fails.append(f"traer: quedan {m.group(1) or 0} × {item} (deben quedar 3: se entregaron {cantidad})")
    if not 3 <= em1 <= 6:
        fails.append(f"traer: paga {em1} esmeraldas (de 3 a 6)")
    if rep1 != 10:
        fails.append(f"traer: reputación {rep1} (debe ser 10)")
    print(f"traer entregado: {em1} esmeraldas, reputación {rep1}")
    # 4) guardián: un mob con sus etiquetas junto al sitio del encargo, muerto por el jugador
    tx, tz = gx + 40, gz
    srv.run(f"forceload add {tx} {tz}", r"Marked|force|already")
    if not srv.until(f"execute if loaded {tx} 64 {tz}", attempts=480):   # con sus entidades: si no, el mob se pierde
        fails.append("guardián: el chunk del sitio del encargo no llega a cargarse")
        return None
    for _ in range(ATTEMPTS):
        m = srv.run(f'summon minecraft:zombie {tx} 200 {tz} {{NoAI:1b,PersistenceRequired:1b,NoGravity:1b,'
                    f'Tags:["heraldia_guardian","heraldia_guardian.{sid}","heraldia_adulto","heraldia_prueba_g"]}}', r"Summoned")
        if "Summoned" in m.group(0) and srv.until("execute if entity @e[tag=heraldia_prueba_g]", attempts=10):
            break
        time.sleep(RETRY_S)
    else:
        fails.append("guardián: no se pudo invocar junto al sitio del encargo")
        return None
    srv.run(f"damage @e[tag=heraldia_prueba_g,limit=1] 2000 minecraft:player_attack by {PLAYER}",
            rf"Heraldia: encargos: {PLAYER} cumple .* \(guardian\)")
    m = como(srv, "heraldia quest turnin", rf"Heraldia: encargos: {PLAYER} entrega .*reputación (-?\d+) \((\w+)\)")
    rep2, nivel = int(m.group(1)), m.group(2)
    em2 = esmeraldas(srv) - em1
    if rep2 != 40 or nivel != "conocido":
        fails.append(f"guardián: reputación {rep2} ({nivel}); debe ser 40 (conocido)")
    if em2 not in (8, 12):
        fails.append(f"guardián: paga {em2} esmeraldas (8 o 12)")
    if not srv.test(f"execute if entity @a[name={PLAYER},advancements={{heraldia:encargos/primero=true}}]"):
        fails.append("logro encargos/primero sin conceder")
    print(f"guardián entregado: {em2} esmeraldas, reputación {rep2} ({nivel})")
    # 5) precio en la plaza con «conocido»: rebaja del 10 % (antes de los encargos no había ninguna: ver arriba)
    dentro = precio(srv, spot, y, bot)
    print(f"precio en la plaza: antes {antes}, con reputación «conocido» {dentro}")
    if dentro != -1:
        fails.append(f"precio en la plaza con reputación «conocido»: specialPrice {dentro} (debe ser -1)")
    cerrar(srv)
    # 6) golpear al aldeano baja la reputación
    m = srv.run(f"damage @e[tag=heraldia_prueba,limit=1] 1 minecraft:player_attack by {PLAYER}",
                rf"Heraldia: encargos: {PLAYER} golpea a un aldeano de .*: reputación (-?\d+)")
    if m.group(1) != "35":
        fails.append(f"golpe al aldeano: reputación {m.group(1)} (debe ser 35)")
    # 7) abandonar uno aceptado
    if len(enc) >= 3:
        srv.run(f"tp {PLAYER} {bot[0]} {y} {bot[1]}", r"Teleported")
        como(srv, "heraldia quest accept 3", rf"Heraldia: encargos: {PLAYER} acepta")
        como(srv, "heraldia quest abandon 1", r"Job abandoned|Encargo abandonado")
        como(srv, "heraldia quest abandon 1", r"no job number 1|No hay encargo número 1")
    entregados = estado(srv)
    if entregados != "2":
        fails.append(f"/heraldia status: {entregados} encargos entregados (deben ser 2)")
    return nombre, periodo, enc


def segunda_vuelta(srv, fails, found, primero, work):
    style, to_world, y, alg = found
    spot, bot = to_world(SPOT), to_world(BOT)
    srv.run(f"forceload add {int(alg[0]) - RADIUS} {int(alg[2]) - RADIUS} {int(alg[0]) + RADIUS} {int(alg[2]) + RADIUS}",
            r"Marked|Added|force|already")
    srv.run(f"player {PLAYER} spawn at {bot[0]} {y} {bot[1]}", r"joined the game")
    srv.until(f"execute if entity @a[name={PLAYER}]")
    srv.ctx.ticks(10)
    nombre, periodo, enc = tablon(srv, fails, lambda: como(srv, "heraldia quest", TABLON.pattern))
    if (nombre, periodo, enc) != primero:
        fails.append(f"tras reiniciar, otro tablón: {enc} (antes {primero[2]})")
    como(srv, "heraldia quest accept 1", r"already handed in that job|Ya entregaste ese encargo")
    if not srv.until(f"execute if entity @e[tag=heraldia_prueba]"):
        fails.append("el aldeano de prueba no sigue en la plaza")
    dentro = precio_existente(srv, spot, y, bot)
    if dentro != -1:
        fails.append(f"tras reiniciar, precio en la plaza {dentro} (debe ser -1: se conserva la reputación)")
    cerrar(srv)
    # opciones desactivadas y recargadas sin reiniciar
    write_config(work, {"encargos": {"activado": False}, "reputacion": {"activado": False}})
    srv.run("heraldia reload", r"Heraldia: configuración recargada")
    como(srv, "heraldia quest", r"quests are disabled|están desactivados")
    sin = precio_existente(srv, spot, y, bot) or 0
    if sin != 0:
        fails.append(f"con la reputación desactivada, specialPrice {sin} (debe ser 0)")
    print(f"tras reiniciar: mismo tablón, entregado conservado, precio {dentro}; desactivados: precio {sin}")


def precio_existente(srv, spot, y, bot):
    for _ in range(10):
        mirar_y_usar(srv, (spot[0], y + 1.2, spot[1]), bot, y)
        srv.ctx.ticks(4)
        m = srv.run("data get entity @e[tag=heraldia_prueba,limit=1] Offers.Recipes[0].specialPrice",
                    r"has the following entity data: (-?\d+)|Found no elements|No entity")
        if m.group(1) is not None:
            return int(m.group(1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-encargos"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    fails = []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    write_config(a.work)
    srv = Server(a.work, launcher)
    primero = found = None
    try:
        found = plaza(srv, fails)
        if found:
            primero = primera_vuelta(srv, fails, found)
            srv.run(f"player {PLAYER} kill", r"left the game")
    finally:
        srv.stop()
    if found and primero:
        srv = Server(a.work, launcher)
        try:
            segunda_vuelta(srv, fails, found, primero, a.work)
            srv.run(f"player {PLAYER} kill", r"left the game")
        finally:
            srv.stop()
    if fails:
        print("FALLOS:")
        for f in fails:
            print(" -", f)
        return 1
    print("OK: tablón, aceptar, traer y guardián entregados, reputación, precio rebajado, reinicio y opciones desactivadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
