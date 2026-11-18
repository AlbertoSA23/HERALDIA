"""Caravanas por los caminos entre aldeas en un servidor dedicado 26.3 real (T39; complementa los tests JUnit de caravanas/).

Uso: python3 tools/smoke/caravans.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-caravanas"
Determinista: la semilla y la rejilla mínima de las aldeas de caminos.py (la misma ruta en tierra firme), el sorteo de las
caravanas apagado (caravanas.frecuencia = 0: solo salen con el comando) y un jugador simulado de Carpet. Se generan los
chunks del tramo central de la ruta (forceload) y el jugador se pone junto al camino.
Primer arranque:
  1. /heraldia caravan spawn raid: sale una caravana (mercader, de 1 a 3 llamas, quizá un guardia) que avanza por el
     camino hacia la aldea de destino; /heraldia caravan raid fuerza el asalto: salen de 2 a 4 bandidos con las
     etiquetas de los mobs anclados; el jugador los mata, la caravana sigue y, llevada de vértice en vértice hasta el
     final, llega: el jugador cobra las esmeraldas y el objeto, la reputación con la aldea de destino sube 15 (la API de
     los encargos) y se concede el logro; no queda ninguna entidad de la caravana.
  2. Otra caravana: el jugador mata al mercader; la caravana se pierde, sin premio y sin nada en el suelo.
  3. Otra: el jugador se aleja 400 bloques; a los 30 s se despide y se quitan sus entidades.
  4. Una entidad con la etiqueta de las caravanas que no es de ninguna activa se quita al cargarse (lo que pasa con las
     de antes de un reinicio). Y otra caravana se queda en camino al parar el servidor: se quita al parar.
Segundo arranque (mismo mundo, el pasillo sigue con forceload): ninguna entidad de caravana; sale una nueva (una sola,
sin duplicados); /heraldia status la cuenta; con caravanas.activado = false y /heraldia reload se va la que había, el
comando dice que están desactivadas y /heraldia status también.
"""
import argparse, json, math, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import village_terrain as at
import importlib.util
from terralith_biomes import fetch
from trophies import CARPET

# la prueba de los caminos por su ruta: «caminos» a secas es el módulo del generador (tools/gen, en sys.path)
_spec = importlib.util.spec_from_file_location("roads_smoke", os.path.join(os.path.dirname(os.path.abspath(__file__)), "roads.py"))
cabin_adv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cabin_adv)

PLAYER = "Testigo"
TAG, MERCHANT, FLAME, SENTRY, BANDIT = ("heraldia_caravana", "heraldia_caravana.mercader", "heraldia_caravana.llama",
                                          "heraldia_caravana.guardia", "heraldia_caravana.bandido")
DEPARTS = re.compile(r"sale la caravana (\d+) de (.+?) hacia (.+?): (\d+) vértices \((\d+) bloques\) desde (-?\d+) (-?\d+) (-?\d+) "
                  r"hasta (-?\d+) (-?\d+), asalto (no|en el vértice \d+), (\d) llamas, (con|sin) guardia")
VERTICES = re.compile(r"vértices de la caravana (\d+): (.*)")
NO_ROAD = r"There is no Heraldia road|No hay ningún camino"
ITEM_LIST = re.compile(r"waypoint (\d+) of (\d+)|vértice (\d+) de (\d+)")
SEGMENT = (0.3, 0.7)          # parte central de la ruta que se genera (la salida busca a 80 bloques del jugador)


def configure(work, extra=None):
    cfg = {"aldeas": {"separacion_bloques": cabin_adv.GRID, "maximo": 100}, "caravanas": {"frecuencia": 0}}
    for k, v in (extra or {}).items():
        cfg.setdefault(k, {}).update(v)
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def wait(ctx, pattern, start):
    """La primera línea desde `desde` (índice en ctx.seen) que casa con `patron`: ya leída (una orden posterior pasa a
    ctx.seen lo que hubiera en la cola) o la que llegue."""
    s.pending(ctx.lines, ctx.seen)
    for line in ctx.seen[start:]:
        m = re.search(pattern, line)
        if m:
            return m
    return s.wait_for(ctx.lines, pattern, s.COMMAND_TIMEOUT_S, ctx.seen)


def as_player(ctx, cmd, ok):
    """La orden ejecutada por el jugador simulado (la respuesta sale en la consola: «execute as» conserva la fuente)."""
    return ctx.run(f"execute as {PLAYER} at @s run {cmd}", ok)


def on_floor(ctx, sel, x, z):
    ctx.run(f"execute positioned {x} 300 {z} positioned over motion_blocking_no_leaves run tp {sel} ~ ~ ~", r"Teleported|No entity")


def point(a, b, t):
    return int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t)


def new_one(ctx, fails, route, mode):
    """Pone al jugador junto al camino y saca una caravana con /heraldia caravan spawn <modo>: su línea del log y sus vértices."""
    a, b, _ = route
    for t in (0.5, 0.44, 0.56, 0.38, 0.62):
        x, z = point(a, b, t)
        on_floor(ctx, PLAYER, x, z)
        ctx.ticks(10)
        m = as_player(ctx, f"heraldia caravan spawn {mode}".strip(), rf"{DEPARTS.pattern}|{NO_ROAD}|already \d+ caravans|Ya hay \d+")
        if m.group(1):
            v = s.wait_for(ctx.lines, rf"vértices de la caravana {m.group(1)}: (.*)", s.COMMAND_TIMEOUT_S, ctx.seen)
            vert = [tuple(int(n) for n in p.split()) for p in v.group(1).strip().split("; ")]
            c = {"id": m.group(1), "origen": m.group(2), "destino": m.group(3), "n": int(m.group(4)), "largo": int(m.group(5)),
                 "salida": (int(m.group(6)), int(m.group(7)), int(m.group(8))), "asalto": m.group(11), "llamas": int(m.group(12)),
                 "guardia": m.group(13) == "con", "vertices": vert}
            print(f"caravana {c['id']}: de {c['origen']} a {c['destino']}, {c['n']} vértices ({c['largo']} bloques) desde "
                  f"{c['salida']}, asalto {c['asalto']}, {c['llamas']} llamas, {'con' if c['guardia'] else 'sin'} guardia")
            return c
        print(f"sin caravana junto a {x} {z} (t = {t}): {m.group(0).strip()[-90:]}")
    fails.append(f"/heraldia caravan spawn {mode}: no sale ninguna caravana junto al camino")
    return None


def following(ctx):
    m = as_player(ctx, "heraldia caravan list", ITEM_LIST.pattern + r"|There are no caravans|No hay ninguna caravana")
    return (int(m.group(1) or m.group(3)), int(m.group(2) or m.group(4))) if (m.group(1) or m.group(3)) else None


def emeralds(ctx):
    m = ctx.run(f"clear {PLAYER} minecraft:emerald 0", r"Found (\d+) matching|No items")
    return int(m.group(1) or 0)


def state(ctx, pattern):
    """La primera línea de /heraldia status (recorre sus páginas) que casa con `patron`, o None."""
    pat = re.compile(pattern)
    for page in range(1, 8):
        m = as_player(ctx, f"heraldia status {page}", r"server status \(page (\d+) of (\d+)\)|estado del servidor \(página (\d+) de (\d+)\)")
        for line in s.drain(ctx):
            if pat.search(line):
                return pat.search(line)
        if (m.group(1) or m.group(3)) == (m.group(2) or m.group(4)):
            return None
    return None


def defended(ctx, fails, route):
    c = new_one(ctx, fails, route, "raid")
    if c is None:
        return
    if ctx.count(f"@e[tag={MERCHANT}]") != 1:
        fails.append(f"caravana {c['id']}: {ctx.count(f'@e[tag={MERCHANT}]')} mercaderes (debe haber 1)")
    if ctx.count(f"@e[tag={FLAME},type=minecraft:trader_llama]") != c["llamas"]:
        fails.append(f"caravana {c['id']}: {ctx.count(f'@e[tag={FLAME}]')} llamas (dice {c['llamas']})")
    if ctx.count(f"@e[tag={SENTRY}]") != (1 if c["guardia"] else 0):
        fails.append(f"caravana {c['id']}: guardia que no cuadra")
    if c["asalto"] == "no":
        fails.append("spawn raid: la caravana sale sin asalto previsto")
    # avanza por el camino: se acerca al final
    finish = c["vertices"][-1]
    p0 = ctx.pos(f"@e[tag={MERCHANT}]")
    ctx.ticks(300)
    p1 = ctx.pos(f"@e[tag={MERCHANT}]")
    d0, d1 = math.dist((p0[0], p0[2]), finish), math.dist((p1[0], p1[2]), finish)
    print(f"el mercader avanza: de {d0:.0f} a {d1:.0f} bloques del final en 15 s; {following(ctx)}")
    if d1 > d0 - 4:
        fails.append(f"el mercader no avanza por el camino: de {d0:.1f} a {d1:.1f} bloques del final en 15 s")
    line = state(ctx, r"(?:Caravans on the road|Caravanas en camino): (\d+)")
    if line is None or line.group(1) != "1":
        fails.append(f"/heraldia status no cuenta la caravana en camino: {line and line.group(0)}")
    # asalto forzado
    m = as_player(ctx, "heraldia caravan raid", r"asalto a la caravana (\d+): (\d+) bandidos")
    n = int(m.group(2))
    print(f"asalto: {n} bandidos")
    if not 2 <= n <= 4:
        fails.append(f"asalto con {n} bandidos (de 2 a 4)")
    if ctx.count(f"@e[tag={BANDIT},tag=heraldia_anclado]") != n:
        fails.append("los bandidos no tienen las etiquetas de los mobs anclados (y de la dificultad)")
    as_player(ctx, "heraldia caravan raid", r"no caravan on the road that can be ambushed|ninguna caravana en camino que se pueda asaltar")
    mark = len(ctx.seen)
    ctx.run(f"execute as @e[tag={BANDIT}] run damage @s 1000 minecraft:player_attack by {PLAYER}", r"Applied|damage|No entity")
    wait(ctx, rf"la caravana {c['id']} supera el asalto", mark)
    # que llegue: el mercader (y el jugador) de vértice en vértice hasta el final
    e0 = emeralds(ctx)
    next_unique = following(ctx)
    mark = len(ctx.seen)
    arrives = re.compile(rf"la caravana {c['id']} llega a (.+?)( tras superar el asalto)? con (\d+) jugadores")
    for k in range(next_unique[0] if next_unique else 1, len(c["vertices"])):
        x, z = c["vertices"][k]
        on_floor(ctx, f"@e[tag={MERCHANT}]", x, z)
        on_floor(ctx, PLAYER, x + 3, z)
        ctx.ticks(30)
        if arrives.search("".join(ctx.seen[mark:])):
            break
    m = wait(ctx, arrives.pattern, mark)
    if m.group(1) != c["destino"] or not m.group(2) or m.group(3) != "1":
        fails.append(f"llegada: {m.group(0)}")
    payout = re.search(rf"{PLAYER} cobra (\d+) esmeraldas(?: y (\d+) × (\S+))? y \+(\d+) de reputación con (.+?) \(ahora (-?\d+)\)", ctx.log())
    rep = re.search(rf"Heraldia: encargos: {PLAYER} defiende la caravana de (.+?): reputación (-?\d+)", ctx.log())
    if not payout:
        fails.append("al llegar, el jugador no cobra")
        return
    paid = emeralds(ctx) - e0
    print(f"llega a {m.group(1)}: {payout.group(0)}; {paid} esmeraldas en el inventario; {rep and rep.group(0)}")
    if paid != int(payout.group(1)) or paid != 2 + c["n"] // 4 + 4:
        fails.append(f"esmeraldas: {paid} en el inventario, {payout.group(1)} en el log, deben ser {2 + c['n'] // 4 + 4}")
    if not payout.group(3) or ctx.count(f"@a[name={PLAYER},nbt={{Inventory:[{{id:\"{payout.group(3)}\"}}]}}]") != 1:
        fails.append(f"el objeto de la caravana defendida no está en el inventario ({payout.group(3)})")
    if payout.group(4) != "15" or payout.group(5) != c["destino"] or not rep or rep.group(1) != c["destino"] or rep.group(2) != "15":
        fails.append(f"reputación con la aldea de destino {c['destino']}: {payout.group(0)} / {rep and rep.group(0)} (debe subir 15)")
    if not ctx.test(f"execute if entity @a[name={PLAYER},advancements={{heraldia:caravanas/defensa=true}}]"):
        fails.append("logro caravanas/defensa sin conceder")
    ctx.ticks(10)
    if ctx.count(f"@e[tag={TAG}]"):
        fails.append(f"tras llegar quedan {ctx.count(f'@e[tag={TAG}]')} entidades de la caravana")


def lost(ctx, fails, route):
    c = new_one(ctx, fails, route, "peaceful")
    if c is None:
        return
    p = ctx.pos(f"@e[tag={MERCHANT}]")
    before = len(re.findall(r" cobra \d+ esmeraldas", ctx.log()))
    mark = len(ctx.seen)
    ctx.run(f"damage @e[tag={MERCHANT},limit=1] 1000 minecraft:player_attack by {PLAYER}", r"Applied|damage")
    m = wait(ctx, rf"termina la caravana {c['id']}: (\w+)", mark)
    ctx.ticks(40)
    floor = ctx.count(f"@e[type=minecraft:item,x={p[0]:.0f},y={p[1]:.0f},z={p[2]:.0f},distance=..24]")
    print(f"mercader muerto: {m.group(0)}; {floor} objetos en el suelo; {ctx.count(f'@e[tag={TAG}]')} entidades de caravana")
    if m.group(1) != "perdida":
        fails.append(f"al matar al mercader la caravana termina como «{m.group(1)}» (debe perderse)")
    if floor:
        fails.append(f"al perderse la caravana quedan {floor} objetos en el suelo (sin botín de explotación)")
    if ctx.count(f"@e[tag={TAG}]"):
        fails.append("al perderse quedan entidades de la caravana")
    if len(re.findall(r" cobra \d+ esmeraldas", ctx.log())) != before:
        fails.append("una caravana perdida ha pagado")


def far(ctx, fails, route):
    c = new_one(ctx, fails, route, "peaceful")
    if c is None:
        return
    x, _, z = c["salida"]
    mark = len(ctx.seen)
    on_floor(ctx, PLAYER, x + 400, z)
    m = wait(ctx, rf"termina la caravana {c['id']}: (\w+) \((\d+) entidades quitadas", mark)
    print(f"el jugador se aleja: {m.group(0)}")
    if m.group(1) != "lejos":
        fails.append(f"al alejarse el jugador, la caravana termina como «{m.group(1)}» (debe despedirse)")
    if int(m.group(2)) != 1 + c["llamas"] + c["guardia"]:
        fails.append(f"al despedirse quita {m.group(2)} entidades (son {1 + c['llamas'] + c['guardia']})")
    if ctx.count(f"@e[tag={TAG}]"):
        fails.append("tras despedirse quedan entidades de la caravana")


def orphan(ctx, fails, route):
    x, z = point(route[0], route[1], 0.5)
    on_floor(ctx, PLAYER, x, z)
    ctx.ticks(10)
    mark = len(ctx.seen)
    ctx.run(f'execute at {PLAYER} run summon minecraft:trader_llama ~2 ~ ~ {{Tags:["{TAG}","{FLAME}"]}}', r"Summoned|Unable")
    m = wait(ctx, r"quitada una entidad de una caravana que ya no está en camino \((\w+)", mark)
    ctx.ticks(5)
    if m.group(1) != "trader_llama" or ctx.count(f"@e[tag={TAG}]"):
        fails.append(f"una llama de caravana suelta no se quita al cargarse: {m.group(0)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-caravanas"))
    a = ap.parse_args()
    a.work = os.path.abspath(a.work)
    os.makedirs(a.work, exist_ok=True)
    fails = []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    configure(a.work)
    proc, ctx = at.start_server(a.work, launcher)
    route = c = None
    try:
        route = cabin_adv.find_path(ctx)
        if route is None:
            raise SystemExit("ninguna ruta en tierra firme desde las aldeas localizadas")
        va, vb, L = route
        print(f"ruta de {va} a {vb}: {L} bloques")
        corridor = [c for c in cabin_adv.chunks_of(va, vb) if SEGMENT[0] <= c[0] <= SEGMENT[1]]
        cabin_adv.generar(ctx, corridor)
        print(f"pasillo generado: {len(corridor)} chunks")
        x, z = point(va, vb, 0.5)
        ctx.run(f"player {PLAYER} spawn at {x} 200 {z}", r"joined the game")
        if not ctx.until(f"execute if entity @a[name={PLAYER}]"):
            raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
        s.send(ctx.proc, f"gamemode creative {PLAYER}")   # no responde en la consola
        ctx.run(f"clear {PLAYER}", r"Removed|No items")
        defended(ctx, fails, route)
        lost(ctx, fails, route)
        far(ctx, fails, route)
        orphan(ctx, fails, route)
        c = new_one(ctx, fails, route, "peaceful")      # se queda en camino al parar
    finally:
        cabin_adv.halt(proc, ctx)
    if c is not None:
        m = re.search(rf"termina la caravana {c['id']}: (\w+) \((\d+) entidades quitadas", ctx.log())
        print(f"al parar: {m and m.group(0)}")
        if not m or m.group(1) != "limpieza" or int(m.group(2)) != 1 + c["llamas"] + c["guardia"]:
            fails.append(f"al parar el servidor no se quita la caravana en camino: {m and m.group(0)}")
    # segundo arranque
    proc, ctx = at.start_server(a.work, launcher)
    try:
        va, vb, _ = route
        x, z = point(va, vb, 0.5)
        ctx.run(f"player {PLAYER} spawn at {x} 200 {z}", r"joined the game")
        ctx.until(f"execute if entity @a[name={PLAYER}]")
        s.send(ctx.proc, f"gamemode creative {PLAYER}")   # no responde en la consola
        ctx.ticks(40)
        surplus = ctx.count(f"@e[tag={TAG}]")
        loaded = len(re.findall(r"quitada una entidad de una caravana", ctx.log()))
        print(f"tras reiniciar: {surplus} entidades de caravana ({loaded} quitadas al cargarse)")
        if surplus:
            fails.append(f"tras reiniciar quedan {surplus} entidades de caravana")
        c = new_one(ctx, fails, route, "peaceful")
        if c is not None:
            if c["id"] != "1" or ctx.count(f"@e[tag={MERCHANT}]") != 1:
                fails.append(f"tras reiniciar: caravana {c['id']} con {ctx.count(f'@e[tag={MERCHANT}]')} mercaderes (debe ser la 1, con 1)")
            as_player(ctx, "heraldia caravan spawn", r"already 1 caravans|Ya hay 1 caravanas")
        # desactivadas y recargadas sin reiniciar
        configure(a.work, {"caravanas": {"activado": False}})
        mark = len(ctx.seen)
        ctx.run("heraldia reload", r"Heraldia: configuración recargada")
        if c is not None:
            m = wait(ctx, rf"termina la caravana {c['id']}: (\w+)", mark)
            if m.group(1) != "limpieza":
                fails.append(f"al desactivarlas, la caravana en camino termina como «{m.group(1)}»")
        ctx.ticks(10)
        if ctx.count(f"@e[tag={TAG}]"):
            fails.append("desactivadas, quedan entidades de caravana")
        as_player(ctx, "heraldia caravan spawn", r"Caravans are disabled|caravanas están desactivadas")
        if state(ctx, r"Caravans: disabled|Caravanas: desactivadas") is None:
            fails.append("/heraldia status no dice que las caravanas están desactivadas")
        ctx.run(f"player {PLAYER} kill", r"left the game")
    finally:
        cabin_adv.halt(proc, ctx)
    if fails:
        print("FALLOS:")
        for f in fails:
            print(" -", f)
        return 1
    print("OK: caravana que avanza, asalto defendido con premio, reputación y logro, mercader muerto, despedida al "
          "alejarse, entidades sueltas quitadas, reinicio limpio y caravanas desactivadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
