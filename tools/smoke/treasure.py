"""Búsqueda del tesoro encadenada (T40) en un servidor dedicado 26.3 real, con un jugador simulado (Carpet).

Uso: python3 tools/smoke/treasure.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Comprueba, con la semilla de las pruebas (heraldia) y la configuración por defecto salvo tesoro.*:
  - botín: con tesoro.probabilidad = 100 una tabla de mina y una de mediana dan el fragmento; tras cambiar el fichero a 0
    y /heraldia reload (sin reiniciar), ya no;
  - /heraldia treasure give da el fragmento (papel con la marca heraldia_busqueda) y el logro tesoro/fragmento;
  - al usarlo (player ... use once, un clic derecho) la cadena se elige fuera del hilo del servidor y el fragmento pasa a
    ser un mapa vanilla (filled_map) con la cadena entera; los destinos son estructuras de Heraldia reales (mediana o
    mina), a menos de tesoro.radio_max uno de otro, sin repetir, y la búsqueda no ha cargado sus chunks;
  - lejos de la marca el mapa no cambia; teletransportado a cada marca (donde /locate encuentra su estructura a menos
    de 48 bloques: es real), pasa a la siguiente;
  - REINICIO a mitad de la cadena: el mapa conserva su paso y sus destinos y se sigue desde ahí;
  - en el tesoro, con una «casa» de tablones justo en la marca, el cofre se entierra fuera de ella y de su margen, en suelo,
    un bloque bajo la cima, con la tabla heraldia:tesoro/cofre; al abrirlo (cavando el bloque de encima), su botín trae la
    Brújula de Ysolda y se concede el logro tesoro/cofre;
  - la cadena se completa una sola vez: volver a usar el mapa no entierra otro cofre, tampoco tras otro reinicio.
Mide cuánto tarda en elegirse la cadena y en buscarse el sitio del cofre (líneas del log).
"""
import argparse, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guide import Server
from terralith_biomes import fetch
from trophies import CARPET

P = "Buscador"
X, Y, Z = 0, 101, 0
RADIUS = 2500
CONFIG = {"tesoro": {"activado": True, "probabilidad": 100, "radio_max": RADIUS}}
MARK = "heraldia_busqueda"
CHOSEN = re.compile(r"tesoro: cadena de (\w+) elegida en (\d+) ms \((\d+) casillas")
INFO = re.compile(r"Heraldia: tesoro: info (\{.*\})")
SITE = re.compile(r"tesoro: sitio del cofre de \w+ en \((-?\d+), (-?\d+)\): (.*) en (\d+) µs")
COFRE = re.compile(r"tesoro: cofre de \w+ enterrado en (-?\d+) (-?\d+) (-?\d+)")
HOUSE = 2   # medio lado de la «casa» de tablones que se pone en la marca del tesoro
MARGIN = 6   # Sitio.MARGEN


def write_config(work, extra):
    with open(os.path.join(work, "config", "heraldia.json"), "w", encoding="utf-8") as f:
        json.dump(extra, f)


def chain(srv):
    """La cadena del mapa en la mano: {paso, destinos: [{tipo, estructura, x, z, generada}], cofre, movido} (de la línea
    «tesoro: info» del log que deja /heraldia treasure info); None si no lleva un mapa con cadena."""
    m = srv.ctx.run(f"execute as {P} run heraldia treasure info", INFO.pattern + r"|Undeciphered|sin descifrar|not holding|No llevas")
    return parse(m.group(1)) if m.group(1) else None


def parse(snbt):
    out = {"paso": int(re.search(r"\bpaso:(\d+)", snbt).group(1)), "destinos": [],
           "movido": int((re.search(r"\bmovido:(\d+)", snbt) or [0, 0])[1])}
    m = re.search(r"cofre:\[I;(-?\d+),(-?\d+),(-?\d+)\]", snbt)
    out["cofre"] = tuple(int(v) for v in m.groups()) if m else None
    lst = snbt[snbt.index("destinos:[") + len("destinos:["):]
    for obj in re.findall(r"\{([^{}]*)\}", lst):
        d = {"tipo": re.search(r'tipo:"(\w+)"', obj).group(1), "x": int(re.search(r"\bx:(-?\d+)", obj).group(1)),
             "z": int(re.search(r"\bz:(-?\d+)", obj).group(1)), "generada": "generada:1b" in obj}
        e = re.search(r'estructura:"([^"]+)"', obj)
        d["estructura"] = e.group(1) if e else ""
        out["destinos"].append(d)
    return out


def creative(srv):
    """Modo creativo (sin daño de caída al teletransportarse); si ya lo está, el comando no responde."""
    s.send(srv.proc, f"gamemode creative {P}")
    if not srv.ctx.until(f"execute if entity @a[name={P},gamemode=creative]", timeout=20):
        raise SystemExit("el jugador simulado no pasa a creativo")


def use(srv):
    s.send(srv.proc, f"player {P} use once")   # no responde nada en la consola
    srv.ctx.ticks(10)


def tp(srv, x, z, y=200):
    srv.ctx.run(f"tp {P} {x} {y} {z}", r"Teleported|Teletransportado")
    srv.ctx.ticks(5)


def real_structure(srv, d, fails):
    """Con el jugador ya en la marca (chunks cargados): /locate de su estructura desde ahí la da a menos de 48 bloques."""
    srv.ctx.ticks(20)
    m = srv.ctx.run(f"execute positioned {d['x']} 64 {d['z']} run locate structure {d['estructura']}",
                    r"is at \[(-?\d+), ~, (-?\d+)\] \((\d+) blocks? away\)|Could not find|Unknown|Incorrect")
    if not m.group(3) or int(m.group(3)) > 48:
        fails.append(f"en la marca {d} no está {d['estructura']}: {m.group(0)}")
    else:
        print(f"{d['estructura']} en {m.group(1)}, {m.group(2)} (a {m.group(3)} bloques de la marca)")


def in_hand(srv, pred):
    return srv.ctx.test(f"execute if items entity {P} weapon.mainhand {pred}")


def advancement(srv, path):
    return srv.ctx.test(f"execute if entity @a[name={P},advancements={{heraldia:{path}=true}}]")


def wait_loaded(srv, x, z, timeout=60):
    return srv.ctx.until(f"execute if loaded {x} 64 {z}", timeout=timeout)


def chest_loot(srv, fails, with_it):
    """Una tabla de mina y una de mediana dan (o no) el fragmento con la probabilidad al 100 % (o al 0 %)."""
    ctx = srv.ctx
    for tbl in ("heraldia:minas/boca", "heraldia:medianas/posada/cuarto"):
        ctx.run(f"clear {P} minecraft:paper", r"Removed|No items")
        ctx.run(f"loot give {P} loot {tbl}", r"Dropped|Gave|No items|Unknown")
        has = ctx.test(f"execute if items entity {P} container.* minecraft:paper[minecraft:custom_data~{{{MARK}:{{}}}}]")
        if has != with_it:
            fails.append(f"botín: {tbl} {'no da' if with_it else 'da'} el fragmento con tesoro.probabilidad = {100 if with_it else 0}")
    ctx.run(f"clear {P}", r"Removed|No items")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-tesoro"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    fails = []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    write_config(a.work, CONFIG)
    srv = Server(a.work, launcher)
    c = None
    try:
        ctx = srv.ctx
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        for _ in range(s.PLACE_ATTEMPTS):
            m = ctx.run(f"fill {X - 3} {Y - 1} {Z - 3} {X + 3} {Y - 1} {Z + 3} minecraft:stone", r"Successfully filled|No blocks")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        for rule in ("spawn_mobs", "advance_time", "advance_weather"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}|Unknown|Incorrect")
        srv.spawn(P)
        creative(srv)
        # 1) botín con la probabilidad al 100 % y, recargada, al 0 %
        chest_loot(srv, fails, True)
        write_config(a.work, dict(CONFIG, tesoro=dict(CONFIG["tesoro"], probabilidad=0)))
        ctx.run("heraldia reload", r"(?:Configuration reloaded from|Configuración recargada de) heraldia\.json")
        chest_loot(srv, fails, False)
        write_config(a.work, CONFIG)
        ctx.run("heraldia reload", r"(?:Configuration reloaded from|Configuración recargada de) heraldia\.json")
        # 2) la primera pista
        ctx.run(f"heraldia treasure give {P}", r"given to|dado a|Unknown|Incorrect")
        if not in_hand(srv, f"minecraft:paper[minecraft:custom_data~{{{MARK}:{{v:1}}}}]"):
            m = ctx.run(f"data get entity {P} SelectedItem", r"has the following entity data: (.*)|No entity|found no")
            fails.append(f"/heraldia treasure give no da el fragmento en la mano: {m.group(0)[:300]}")
        if not ctx.until(f"execute if entity @a[name={P},advancements={{heraldia:tesoro/fragmento=true}}]", timeout=10):
            fails.append("sin el logro tesoro/fragmento al recibir el fragmento")
        # 3) descifrarlo: un mapa con la cadena
        use(srv)
        if not ctx.until(f"execute if items entity {P} weapon.mainhand minecraft:filled_map[minecraft:custom_data~{{{MARK}:{{paso:0}}}}]",
                         timeout=120):
            raise SystemExit(f"el fragmento no se descifra en un mapa; log: {ctx.log()[-1500:]}")
        m = CHOSEN.search(ctx.log())
        print(f"cadena elegida en {m.group(2)} ms ({m.group(3)} casillas), fuera del hilo del servidor" if m else "sin línea de tiempo")
        c = chain(srv)
        print("cadena:", c)
        if not c or len(c["destinos"]) not in (2, 3) or c["destinos"][-1]["tipo"] != "tesoro":
            raise SystemExit(f"cadena no válida: {c}")
        ant = (X, Z)
        for i, d in enumerate(c["destinos"][:-1]):
            if d["tipo"] not in ("mediana", "mina") or not d["estructura"].startswith(("heraldia:medianas/", "heraldia:minas/")):
                fails.append(f"marca {i + 1}: no es una mediana ni una mina de Heraldia: {d}")
            dist = ((d["x"] - ant[0]) ** 2 + (d["z"] - ant[1]) ** 2) ** 0.5
            if not 96 <= dist <= RADIUS:
                fails.append(f"marca {i + 1} a {dist:.0f} bloques de la anterior (96-{RADIUS})")
            ant = (d["x"], d["z"])
        if len({(d["x"], d["z"]) for d in c["destinos"]}) != len(c["destinos"]):
            fails.append(f"destinos repetidos: {c['destinos']}")
        first = c["destinos"][0]
        if abs(first["x"]) > 128 or abs(first["z"]) > 128:
            if ctx.test(f"execute if loaded {first['x']} 64 {first['z']}"):
                fails.append("la búsqueda ha cargado el chunk del primer destino (no debe cargar ni generar nada)")
        # 4) lejos: el mapa no cambia
        use(srv)
        if chain(srv)["paso"] != 0:
            fails.append("usado lejos de la marca, el mapa avanza")
        # 5) primera marca
        tp(srv, first["x"], first["z"])
        wait_loaded(srv, first["x"], first["z"])
        real_structure(srv, first, fails)
        use(srv)
        c1 = chain(srv)
        if c1["paso"] != 1:
            fails.append(f"en la primera marca el mapa no pasa a la siguiente: {c1}")
    finally:
        srv.stop()
    # 6) reinicio a mitad de la cadena: el mapa conserva el paso y los destinos
    srv = Server(a.work, launcher)
    try:
        ctx = srv.ctx
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        srv.spawn(P)
        creative(srv)
        if not ctx.until(f"execute if items entity {P} weapon.mainhand minecraft:filled_map", timeout=20):
            raise SystemExit("tras reiniciar, el jugador no lleva el mapa")
        c2 = chain(srv)
        if not c2 or c2["paso"] != 1 or c2["destinos"] != c["destinos"]:
            fails.append(f"tras reiniciar el mapa no conserva la cadena: {c2} (antes {c})")
        c = c2 or c
        while c["destinos"][c["paso"]]["tipo"] != "tesoro":
            d = c["destinos"][c["paso"]]
            tp(srv, d["x"], d["z"])
            wait_loaded(srv, d["x"], d["z"])
            real_structure(srv, d, fails)
            use(srv)
            n = chain(srv)
            if n["paso"] != c["paso"] + 1:
                raise SystemExit(f"en la marca {c['paso'] + 1} el mapa no avanza: {n}")
            c = n
        # 7) el tesoro: una «casa» en la marca; el cofre va fuera de ella y de su margen
        for attempt in range(5):
            t = c["destinos"][-1]
            tp(srv, t["x"], t["z"])
            for dx in (-48, 48):
                for dz in (-48, 48):
                    wait_loaded(srv, t["x"] + dx, t["z"] + dz)
            if attempt == 0:
                ctx.run(f"execute positioned {t['x']} 0 {t['z']} positioned over motion_blocking_no_leaves run "
                        f"fill ~-{HOUSE} ~ ~-{HOUSE} ~{HOUSE} ~2 ~{HOUSE} minecraft:oak_planks hollow", r"Successfully filled|No blocks|Unknown|Incorrect")
            before = len(COFRE.findall(ctx.log()))
            use(srv)
            n = chain(srv)
            if n["cofre"]:
                c = n
                break
            if n["movido"] > c["movido"]:
                print(f"el sitio del tesoro no era seguro: la marca se ha movido ({n['destinos'][-1]})")
                c = n
                continue
            m = SITE.findall(ctx.log())
            raise SystemExit(f"en el tesoro no se entierra el cofre: {n}; sitio: {m[-1] if m else '?'}")
        else:
            raise SystemExit("el tesoro se ha movido 5 veces sin encontrar sitio")
        m = SITE.findall(ctx.log())
        if m:
            print(f"sitio del cofre buscado en {m[-1][3]} µs ({m[-1][2]})")
        cx, cy, cz = c["cofre"]
        t = c["destinos"][-1]
        if not ctx.block((cx, cy, cz), "minecraft:chest"):
            fails.append(f"no hay cofre en {c['cofre']}")
        if max(abs(cx - t["x"]), abs(cz - t["z"])) <= HOUSE + MARGIN and c["movido"] == 0:
            fails.append(f"el cofre ({cx}, {cz}) está en la casa de tablones o en su margen (marca {t['x']}, {t['z']})")
        if ctx.block((cx, cy + 1, cz), "minecraft:air") or ctx.block((cx, cy + 1, cz), "minecraft:oak_planks"):
            fails.append("el cofre no está enterrado (al aire o bajo tablones)")
        if not ctx.test(f'execute if data block {cx} {cy} {cz} {{LootTable:"heraldia:tesoro/cofre"}}'):
            fails.append("el cofre no tiene la tabla heraldia:tesoro/cofre")
        # 8) cavar y abrirlo: botín, recuerdo y logro
        ctx.run(f"setblock {cx} {cy + 1} {cz} minecraft:air", r"Changed the block|Could not set")
        ctx.run(f"tp {P} {cx + 0.5} {cy + 1} {cz + 0.5}", r"Teleported|Teletransportado")
        ctx.ticks(5)
        s.send(srv.proc, f"player {P} look at {cx + 0.5} {cy + 0.5} {cz + 0.5}")
        ctx.ticks(2)
        for _ in range(3):
            use(srv)
            if advancement(srv, "tesoro/cofre"):
                break
        if not advancement(srv, "tesoro/cofre"):
            fails.append("al abrir el cofre no se concede el logro tesoro/cofre")
        if not ctx.test(f"execute if items block {cx} {cy} {cz} container.* minecraft:compass[minecraft:custom_data~{{heraldia_recuerdo_tesoro:1b}}]"):
            fails.append("el cofre no trae la Brújula de Ysolda")
        # 9) una sola vez: el mapa ya no entierra otro
        ctx.run(f"tp {P} {t['x']} 200 {t['z']}", r"Teleported|Teletransportado")
        ctx.ticks(5)
        use(srv)
        if len(COFRE.findall(ctx.log())) != 1:
            fails.append(f"se ha enterrado más de un cofre: {COFRE.findall(ctx.log())}")
    finally:
        srv.stop()
    # 10) otro reinicio: la cadena sigue completada y no da otro cofre
    srv = Server(a.work, launcher)
    try:
        ctx = srv.ctx
        srv.spawn(P)
        creative(srv)
        ctx.until(f"execute if items entity {P} weapon.mainhand minecraft:filled_map", timeout=20)
        c3 = chain(srv)
        if not c3 or c3["cofre"] != c["cofre"]:
            fails.append(f"tras reiniciar, el mapa no recuerda el cofre: {c3}")
        t = c["destinos"][-1]
        tp(srv, t["x"], t["z"])
        wait_loaded(srv, t["x"], t["z"])
        use(srv)
        if COFRE.search(ctx.log()):
            fails.append("tras reiniciar, el mapa completado entierra otro cofre")
    finally:
        srv.stop()
    log = os.path.join(a.work, "logs", "latest.log")
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else ""
    for bad in ("Registry loading errors", "Failed to load datapacks", "Couldn't load", "Failed to parse",
                "Found validation problems", "no se pudo descifrar"):
        if bad in text:
            fails.append(f"el log contiene {bad!r}")
    print("TESORO:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
