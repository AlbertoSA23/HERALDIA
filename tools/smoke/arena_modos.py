"""Modos de la arena, clasificación semanal y salón de la fama (T41, Java: arena/Fama, Temporada, Semana, Modo) en un
servidor dedicado 26.3 real, con un jugador simulado (Carpet).

Uso: python3 tools/smoke/arena_modos.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-arena-modos"
Primer arranque (mundo nuevo con la arena desactivada, como un mundo de antes con récords en el marcador):
  1. migración: con la arena desactivada se crea el marcador vanilla heraldia_arena con récords (como lo dejaba la
     arena de antes de T41); al activarla con /heraldia reload, el mejor pasa a ser el récord del cooperativo;
  2. /heraldia arena place y confirm: los tres carteles del salón de la fama (madera carmesí) en su sitio del plano, con
     «sin campeón»; se quita uno y se pone piedra en otro (como una arena colocada antes de T41 y un sitio ocupado);
  3. la campana ofrece los tres modos; contrarreloj corto (arena.modos.oleadas_contrarreloj = 2): acaba solo al superar
     la segunda oleada, apunta la marca (puesto 1 y récord del modo, anunciado) y no da el logro (pide 10 oleadas);
  4. supervivencia corta: la oleada siguiente empieza sin pausa; el jugador cae en la tercera y su marca (2 oleadas)
     queda apuntada;
  5. /heraldia arena leaderboard: cada modo con su marca y el récord migrado; una semana que no se guarda falla;
  6. /heraldia arena season reset: cierra la semana, anuncia los campeones, les da su logro, el cartel quitado vuelve,
     el ocupado no se toca y los demás dicen el campeón; la semana pasada se consulta con leaderboard <modo> 1; la
     Guía trae el salón de la fama; otro contrarreloj para la semana nueva.
Segundo arranque (el mismo mundo, con el día de reinicio cambiado a hoy: el reinicio pasó con el servidor apagado):
  la semana se cierra al arrancar con su campeón, el histórico tiene las dos semanas, el récord migrado sigue, el cartel
  dice el campeón y los logros siguen.
Lo que el servidor escribe en la consola sale en inglés (el servidor dedicado carga el en_us del mod).
"""
import argparse, datetime, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guia import Server
from trofeos import CARPET
from modrinth import fetch
from arena import Prueba, plano, rel, wait_count, ARENA

P = "Testigo"
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
HACE_DOS = DIAS[(datetime.date.today() - datetime.timedelta(days=2)).weekday()]
HOY = DIAS[datetime.date.today().weekday()]
SIGN = r"has the following block data: (.*)|is not a block entity|Found no elements|not a block"


def config(work, activado, dia):
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    cfg["arena"] = {"generar_en_mundos_nuevos": False, "activado": activado,
                    "modos": {"oleadas_contrarreloj": 2},
                    "temporada": {"dia_reinicio": dia, "hora_reinicio": 0, "historico": 3}}
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-arena-modos"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    pl = plano(a.jar)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    config(a.work, False, HACE_DOS)
    fails, textos, caja = [], [], None
    srv = Server(a.work, launcher)
    try:
        caja = primer_arranque(Prueba(srv.ctx, fails), pl, a.work)
    finally:
        srv.stop()
        textos.append(srv.ctx.log())
    if caja:
        config(a.work, True, HOY)              # el día de reinicio pasa a ser hoy: el reinicio «pasó» con el servidor apagado
        srv = Server(a.work, launcher)
        try:
            segundo_arranque(Prueba(srv.ctx, fails), pl, caja)
        finally:
            srv.stop()
            textos.append(srv.ctx.log())
    for bad in ("Registry loading errors", "Failed to load datapacks", "at io.github.albertosa23", "arena: mob "):
        if any(bad in t for t in textos):
            fails.append(f"el log contiene {bad!r}")
    print("ARENA MODOS:", "OK" if not fails else fails)
    return 1 if fails else 0


def cartel(ctx, pos, linea):
    """El texto (SNBT) de la línea `linea` (0-3) del cartel de `pos`, o None si no es un cartel."""
    m = ctx.run(f"data get block {pos[0]} {pos[1]} {pos[2]} front_text.messages[{linea}]", SIGN)
    return m.group(1) if m.lastindex and m.group(1) else None


def limpiar(p, n, veces, timeout=180):
    """Mata (a nombre del jugador) a los enemigos de la oleada n hasta que se supere por `veces`-ésima vez en el log."""
    ctx = p.ctx
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if p.veces(rf"arena: oleada {n} superada") >= veces:
            return True
        if ctx.count(ARENA):
            ctx.run(f"damage {ARENA[:-1]},limit=1,sort=random] 1000 minecraft:player_attack by {P}", r"Applied|damage|No entity")
        else:
            ctx.ticks(5)
    p.check(False, f"no se supera la oleada {n} (vez {veces})")
    return False


def hora(log, patron, veces=1):
    """Segundos del día de la `veces`-ésima línea del log con `patron` ([HH:MM:SS] de su principio), o None."""
    ls = [l for l in log.splitlines() if re.search(patron, l)]
    if len(ls) < veces:
        return None
    m = re.match(r"\[(\d+):(\d+):(\d+)", ls[veces - 1])
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None


def empezar(p, modo, en_ruedo):
    ctx = p.ctx
    ctx.run(f"tp {P} {en_ruedo[0] + 0.5} {en_ruedo[1]} {en_ruedo[2] + 0.5}", r"Teleported")
    ctx.run(f"effect give {P} minecraft:resistance infinite 255 true", r"Applied effect|Gave|Unable to apply")
    ctx.run(f"execute as {P} run heraldia arena start {modo}", r"Prepárate|Get ready")
    return p.esperar_log(rf"arena: cuenta atrás \(la empieza {P}, modo {modo}", timeout=60)


def primer_arranque(p, pl, work):
    ctx = p.ctx
    # 1. migración del marcador vanilla de antes de T41
    p.check(p.esperar_log(r"arena: desactivada", timeout=60), "la arena no arranca desactivada")
    ctx.run("scoreboard objectives add heraldia_arena dummy", r"Created new objective|already exists")
    for nombre, n in (("Veterano", 7), ("Otra", 3), ("-servidor-", 7)):
        ctx.run(f"scoreboard players set {nombre} heraldia_arena {n}", r"Set \[heraldia_arena\]|Set score")
    config(work, True, HACE_DOS)
    ctx.run("heraldia reload", r"[Rr]eload|[Rr]ecarg|[Cc]onfig")
    p.check(p.esperar_log(r"arena: récords migrados del marcador \(3 jugadores; cooperativo: Veterano 7\)", timeout=60),
            "no se migra el récord del marcador vanilla")
    for rule in ("spawn_mobs", "advance_time"):
        ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
    ctx.run("difficulty normal", r"difficulty|Difficulty")
    # 2. la arena con sus carteles
    ctx.run("heraldia arena place", r"arena: sitio propuesto en")
    ctx.run("heraldia arena place confirm", r"Colocando la arena en|Building the arena at")
    m = p.esperar_log(r"arena: colocada en (-?\d+) (-?\d+) (-?\d+) \(caja (-?\d+) (-?\d+) (-?\d+) a (-?\d+) (-?\d+) (-?\d+)\)")
    if not p.check(m, "no se coloca la arena"):
        return None
    caja = tuple(int(g) for g in m.groups())[3:]
    minx, miny, minz, maxx, maxy, maxz = caja
    ctx.run(f"forceload add {minx - 16} {minz - 16} {maxx + 16} {maxz + 16}", r"Marked|force|already")
    fama = [tuple(caja[i] + f[i] for i in range(3)) for f in pl["fama"]]
    p.check(len(fama) == 3, f"el plano trae {len(fama)} carteles del salón de la fama")
    p.check(p.esperar_log(r"arena: carteles del salón de la fama al día \(0 campeones\)"), "no se escriben los carteles")
    for f in fama:
        p.check(ctx.block(f, "minecraft:crimson_sign"), f"no hay cartel del salón de la fama en {f}")
    p.check("heraldia.arena.cartel.nadie" in (cartel(ctx, fama[0], 2) or ""), "el cartel no dice «sin campeón»")
    p.check("heraldia.arena.modo.coop" in (cartel(ctx, fama[0], 1) or ""), "el primer cartel no es el del cooperativo")
    p.check("heraldia.arena.modo.timeattack" in (cartel(ctx, fama[1], 1) or ""), "el segundo cartel no es el del contrarreloj")
    # como una arena de antes de T41 (sin su cartel) y un sitio ocupado
    ctx.run(f"setblock {fama[0][0]} {fama[0][1]} {fama[0][2]} minecraft:air", r"Changed the block")
    ctx.run(f"setblock {fama[2][0]} {fama[2][1]} {fama[2][2]} minecraft:stone", r"Changed the block")
    m = ctx.run("heraldia arena leaderboard", r"Arena leaderboard, week of ([\d/]+) \(current\)|Clasificación de la arena")
    p.check(p.esperar_log(r"Record: Veterano, wave 7"), "la clasificación no enseña el récord migrado")
    p.check(p.esperar_log(r"No results yet"), "la clasificación vacía no lo dice")

    # 3. contrarreloj corto: la campana ofrece los modos
    reap, bell = rel(caja, pl, "reaparicion"), rel(caja, pl, "campana")
    ctx.run(f"player {P} spawn at {reap[0] + 0.5} {reap[1]} {reap[2] + 0.5}", r"joined the game|Player .* spawn|Unknown|Incorrect")
    if not ctx.until(f"execute if entity @a[name={P}]"):
        raise SystemExit(f"no aparece el jugador simulado {P} (Carpet)")
    ctx.run(f"gamemode survival {P}", r"Set .* game mode|game mode")
    ctx.run(f"tp {P} {bell[0] + 0.5} {bell[1]} {bell[2] - 1.5}", r"Teleported")
    s.send(ctx.proc, f"player {P} look at {bell[0] + 0.5} {bell[1] + 0.4} {bell[2] + 0.5}")
    ctx.ticks(5)
    s.send(ctx.proc, f"player {P} use once")
    p.check(p.esperar_log(rf"arena: {P} elige modo \(coop, timeattack, survival\)", timeout=60), "la campana no ofrece los modos")
    p.check(not re.search(r"arena: cuenta atrás", ctx.log()), "la campana empieza una partida sin elegir modo")
    centro = (caja[0] + pl["centro"][0], caja[1] + pl["centro"][1], caja[2] + pl["centro"][2] - 3)
    if not p.check(empezar(p, "timeattack", centro) and p.esperar_log(r"modo timeattack, 2 oleadas\)"),
                   "no empieza el contrarreloj de 2 oleadas"):
        return caja
    puerta = tuple(caja[i] + pl["puerta"][0][i] for i in range(3))
    p.check(p.esperar_log(r"partida empieza con 1 participantes \(modo timeattack\)"), "el contrarreloj no empieza con el jugador")
    limpiar(p, 1, 1)
    p.check(p.esperar_log(r"arena: oleada 2: 6 enemigos", timeout=60), "el contrarreloj no pasa a la oleada 2")
    limpiar(p, 2, 1)
    m = p.esperar_log(r"arena: contrarreloj completado: 2 oleadas en (\d+) ticks")
    p.check(m, "el contrarreloj no se completa tras la última oleada")
    p.check(p.esperar_log(r"partida terminada \(contrarreloj completado\) con 2 oleadas superadas \(modo timeattack"),
            "el contrarreloj no acaba solo")
    p.check(p.esperar_log(rf"arena: marca de {P} en timeattack: 2 oleadas en \d+ ticks \(puesto 1 de la semana, récord\)"),
            "sin marca del contrarreloj")
    p.check(p.esperar_log(r"has set a new arena record in Time attack|bate el récord de la arena en Contrarreloj"),
            "sin anuncio del récord del contrarreloj")
    p.check(not p.veces(r"arena: oleada 3:"), "el contrarreloj sigue tras su última oleada")
    p.check(ctx.until(f"execute if entity {ARENA}", want=False, timeout=30), "quedan mobs tras el contrarreloj")
    p.check(ctx.block(puerta, "minecraft:air"), "la puerta no se abre tras el contrarreloj")
    p.check(ctx.test(f"execute if entity @a[name={P},advancements={{heraldia:arena/contrarreloj=false}}]"),
            "un contrarreloj de 2 oleadas da el logro (pide 10)")

    # 4. supervivencia corta: sin pausa entre oleadas; cae en la tercera
    if not p.check(empezar(p, "survival", centro), "no empieza la supervivencia"):
        return caja
    p.check(p.esperar_veces(r"arena: oleada 1: 4 enemigos", 2, timeout=60), "la supervivencia no empieza")
    limpiar(p, 1, 2)
    p.check(p.esperar_veces(r"arena: oleada 2: 6 enemigos", 2, timeout=60), "la supervivencia no pasa a la oleada 2")
    limpiar(p, 2, 2)
    p.check(p.esperar_log(r"arena: oleada 3: \d+ enemigos", timeout=60), "la supervivencia no pasa a la oleada 3")
    log = ctx.log()
    t0, t1 = hora(log, r"arena: oleada 1 superada", 2), hora(log, r"arena: oleada 2: 6 enemigos", 2)
    p.check(t0 is not None and t1 is not None and 0 <= t1 - t0 <= 3,
            f"supervivencia: la oleada 2 no empieza sin pausa ({t0} -> {t1}; el cooperativo espera 10 s)")
    ctx.run(f"effect clear {P}", r"Removed|effect")
    ctx.run(f"damage {P} 1000 minecraft:generic", r"Applied|damage")
    p.check(p.esperar_log(r"partida terminada \(sin participantes\) con 2 oleadas superadas \(modo survival", timeout=60),
            "la supervivencia no acaba al caer el jugador")
    p.check(p.esperar_log(rf"arena: marca de {P} en survival: 2 oleadas en \d+ ticks \(puesto 1"), "sin marca de la supervivencia")
    ctx.until(f"execute if entity @a[name={P}]", want=False, timeout=30)
    ctx.run(f"player {P} spawn at {reap[0] + 0.5} {reap[1]} {reap[2] + 0.5}", r"joined the game|Player .* spawn|Unknown|Incorrect")
    ctx.until(f"execute if entity @a[name={P}]")

    # 5. la clasificación
    antes = len(ctx.log())
    ctx.run("heraldia arena leaderboard timeattack", r"Arena leaderboard, week of")
    ctx.run("heraldia arena leaderboard survival", r"Arena leaderboard, week of")
    ctx.ticks(5)
    nuevo = ctx.log()[antes:]
    p.check(re.search(rf"1\. {P}: \d+:\d\d \(2 waves\)", nuevo), "la clasificación del contrarreloj no da el tiempo")
    p.check(re.search(rf"1\. {P}: wave 2", nuevo), "la clasificación de la supervivencia no da la oleada")
    p.check(re.search(rf"Record: {P}, wave 2", nuevo), "sin el récord de la supervivencia")
    ctx.run("heraldia arena leaderboard coop 1", r"That week is not kept: the history has 0|No se guarda esa semana")

    # 6. reinicio de semana forzado
    ctx.run("heraldia arena season reset", r"Arena week of .* closed by hand|cerrada a mano")
    p.check(p.esperar_log(rf"arena: semana del [\d/]+ cerrada; campeones: timeattack={P}, survival={P}"),
            "el reinicio no cierra la semana con sus campeones")
    p.check(p.esperar_log(rf"(?:Time attack|Contrarreloj) champion: {P}|Campeón de Contrarreloj: {P}"), "sin anuncio de los campeones")
    for logro in ("campeon_timeattack", "campeon_survival"):
        p.check(p.esperar_log(rf"arena: logro arena/{logro} para {P}"), f"sin el logro {logro}")
        p.check(ctx.test(f"execute if entity @a[name={P},advancements={{heraldia:arena/{logro}=true}}]"), f"no tiene {logro}")
    p.check(ctx.test(f"execute if entity @a[name={P},advancements={{heraldia:arena/campeon_coop=false}}]"),
            "tiene el logro del cooperativo sin haberlo ganado")
    p.check(p.esperar_log(r"arena: cartel del salón de la fama puesto en"), "no vuelve el cartel quitado")
    p.check(ctx.block(fama[0], "minecraft:crimson_sign"), "no vuelve el cartel quitado (bloque)")
    p.check(p.esperar_log(r"el sitio del cartel del salón de la fama \(.*\) está ocupado: no se toca"), "no avisa del sitio ocupado")
    p.check(ctx.block(fama[2], "minecraft:stone"), "el cartel pisa lo que ocupaba su sitio")
    p.check(P in (cartel(ctx, fama[1], 2) or ""), "el cartel del contrarreloj no dice el campeón")
    p.check("heraldia.arena.cartel.nadie" in (cartel(ctx, fama[0], 2) or ""), "el cartel del cooperativo no dice «sin campeón»")
    antes = len(ctx.log())
    ctx.run("heraldia arena leaderboard timeattack 1", r"Arena leaderboard, week of")
    ctx.run("heraldia arena leaderboard timeattack", r"Arena leaderboard, week of")
    ctx.ticks(5)
    nuevo = ctx.log()[antes:]
    p.check(re.search(rf"1\. {P}: \d+:\d\d", nuevo) and "No results yet" in nuevo,
            "la semana cerrada no tiene la marca o la nueva no está vacía")
    # la Guía con el salón de la fama
    ctx.run(f"execute as {P} run heraldia guide", r"Guide|Guía|guide")
    inv = ctx.run(f"data get entity {P} Inventory", r"has the following entity data: (.*)|No entity").group(1) or ""
    p.check("heraldia.guia.fama.titulo" in inv and "heraldia.guia.fama.semana" in inv and P in inv,
            "la Guía no trae el salón de la fama con el campeón")
    # otro contrarreloj para la semana nueva (la que cerrará el segundo arranque)
    if p.check(empezar(p, "timeattack", centro), "no empieza el segundo contrarreloj"):
        p.check(p.esperar_veces(r"arena: oleada 1: 4 enemigos", 3, timeout=60), "el segundo contrarreloj no empieza")
        limpiar(p, 1, 3)
        limpiar(p, 2, 3)
        p.check(p.esperar_veces(rf"arena: marca de {P} en timeattack: 2 oleadas en \d+ ticks \(puesto 1 de la semana", 2),
                "sin marca del segundo contrarreloj")
    ctx.run("heraldia arena season", r"Arena week of .*next reset|Semana de la arena del")
    ctx.run("save-all flush", r"Saved the game")
    return caja


def segundo_arranque(p, pl, caja):
    ctx = p.ctx
    p.check(p.esperar_log(r"arena: en (-?\d+) (-?\d+) (-?\d+)", timeout=60), "tras reiniciar no se recuerda la arena")
    p.check(p.esperar_log(rf"arena: semana del [\d/]+ cerrada; campeones: timeattack={P}", timeout=60),
            "el reinicio que pasó con el servidor apagado no cierra la semana al arrancar")
    p.check(not re.search(r"récords migrados", ctx.log()), "la migración se repite")
    ctx.run("heraldia arena leaderboard coop 3", r"That week is not kept: the history has 2|No se guarda esa semana")
    antes = len(ctx.log())
    ctx.run("heraldia arena leaderboard timeattack 2", r"Arena leaderboard, week of")
    ctx.run("heraldia arena leaderboard coop", r"Arena leaderboard, week of")
    ctx.ticks(5)
    nuevo = ctx.log()[antes:]
    p.check(re.search(rf"1\. {P}: \d+:\d\d", nuevo), "tras reiniciar no se guarda la primera semana")
    p.check("Record: Veterano, wave 7" in nuevo, "tras reiniciar no sigue el récord migrado")
    fama = [tuple(caja[i] + f[i] for i in range(3)) for f in pl["fama"]]
    ctx.run(f"forceload add {fama[1][0]} {fama[1][2]}", r"Marked|force|already")
    p.check(ctx.until(f"execute if block {fama[1][0]} {fama[1][1]} {fama[1][2]} minecraft:crimson_sign", timeout=60),
            "tras reiniciar no está el cartel")
    ok = False
    for _ in range(90):                           # los carteles se ponen al día cuando su chunk está cargado (cada minuto)
        if P in (cartel(ctx, fama[1], 2) or ""):
            ok = True
            break
        ctx.ticks(20)
    p.check(ok, "tras reiniciar el cartel del contrarreloj no dice el campeón")
    reap = rel(caja, pl, "reaparicion")
    ctx.run(f"player {P} spawn at {reap[0] + 0.5} {reap[1]} {reap[2] + 0.5}", r"joined the game|Player .* spawn|Unknown|Incorrect")
    if ctx.until(f"execute if entity @a[name={P}]"):
        p.check(ctx.test(f"execute if entity @a[name={P},advancements={{heraldia:arena/campeon_timeattack=true}}]"),
                "tras reiniciar no conserva el logro de campeón")


if __name__ == "__main__":
    sys.exit(main())
