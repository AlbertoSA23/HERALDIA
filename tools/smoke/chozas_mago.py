"""Chozas de mago (T43) en un servidor dedicado 26.3 real (complementa DecisionTest y ChozasOpcionesTest).

Uso: python3 tools/smoke/chozas_mago.py --jar build/libs/heraldia-X.jar [--work build/smoke-chozas-mago]
Determinista: cada choza se coloca con /place template (sobre una losa, en chunks con forceload) y las probabilidades
se fijan en la configuración (chozas_mago.prob_malvado y prob_botin_premium a 0 o a 100, con /heraldia reload entre
medias); un jugador simulado de Carpet (en supervivencia, con resistencia V para que no muera).
Primer arranque (malvados 0 %, premio 0 %):
  1. Choza A (bondadosa): el mago tiene su nombre generado, la etiqueta de bondadoso y sus tratos (frascos, lapislázuli,
     pociones, libro, perla); el jugador se acerca y hasta intenta comerciar: no se revela. /heraldia wizard lo lista.
  2. Choza B: /heraldia wizard reveal (forzado): el aldeano desaparece, sale el Mago Malvado (evocador con su nombre, las
     etiquetas de jefe y su tabla de botín normal) con 3 vexes; el jugador lo vence con /damage: suelta botín (sin el
     tótem vanilla), sus vexes se deshacen, el logro se concede y el log lo cuenta. Una segunda orden no revela nada.
  3. Premio al 100 % (reload) y choza C forzada: su tabla es la del premio; al vencerlo el log dice «premio: sí».
  4. Malvados al 100 % (reload): la choza A sigue bondadosa (la decisión ya tomada no cambia); la choza D nace malvada
     sin revelar y se revela sola al acercarse el jugador.
Segundo arranque (mismo mundo, sin tocar nada): el Mago Malvado de D sigue siendo uno solo, A sigue bondadosa con su
aldeano y nadie se revela otra vez; /heraldia status da la línea de las chozas.
"""
import argparse, json, os, queue, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
import aldeas_terreno as at
from terralith_biomas import fetch
from trofeos import CARPET

PLAYER = "Testigo"
MAGO, MALVADO, VEX = "heraldia_mago", "heraldia_mago_malvado", "heraldia_mago_vex"
Y = 100
SITIOS = {"A": (30000, 30000), "B": (30200, 30000), "C": (30400, 30000), "D": (30600, 30000)}
PLANTILLA = {"A": "oscuro/a", "B": "pantano/b", "C": "taiga/a", "D": "desierto/b"}
LEJOS = (30300, 30400)            # donde espera el jugador entre prueba y prueba (a más de 100 bloques de todas)
VENCIDO = re.compile(r"Mago Malvado vencido en (-?\d+) (-?\d+) (-?\d+) \(premio: (sí|no)\)")
REVELA = re.compile(r"el mago de (-?\d+) (-?\d+) (-?\d+) se revela \((forzado|malvado); premio: (sí|no); (\d) vexes\)")


def parar(proc, ctx):
    """Para el servidor y pasa a ctx.seen lo que escribió al parar."""
    at.stop(proc)
    while True:
        try:
            line = ctx.lines.get(timeout=30)
        except queue.Empty:
            return
        if line is None:
            return
        ctx.seen.append(line)


def estado(ctx, patron):
    """La primera línea de /heraldia status (recorre sus páginas) que casa con `patron`, o None."""
    pat = re.compile(patron)
    for pagina in range(1, 8):
        m = ctx.run(f"execute as {PLAYER} at @s run heraldia status {pagina}",
                    r"server status \(page (\d+) of (\d+)\)|estado del servidor \(página (\d+) de (\d+)\)")
        for linea in s.drain(ctx):
            if pat.search(linea):
                return pat.search(linea)
        if (m.group(1) or m.group(3)) == (m.group(2) or m.group(4)):
            return None
    return None


def configurar(work, malvado, premio):
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump({"chozas_mago": {"prob_malvado": malvado, "prob_botin_premium": premio}}, f)


def caja(c, extra=0):
    x, z = SITIOS[c]
    return f"x={x - extra},y={Y - 4},z={z - extra},dx={17 + 2 * extra},dy=24,dz={17 + 2 * extra}"


def colocar(ctx, c):
    x, z = SITIOS[c]
    ctx.run(f"forceload add {x - 16} {z - 16} {x + 32} {z + 32}", r"Marked|[Aa]dded|force|already")
    ctx.until(f"execute if loaded {x} {Y} {z}")
    ctx.run(f"fill {x} {Y - 1} {z} {x + 16} {Y - 1} {z + 16} minecraft:stone", r"Successfully filled|No blocks")
    ctx.run(f"place template heraldia:medianas/choza_mago/{PLANTILLA[c]} {x} {Y} {z}", r"Loaded template|Failed")
    return ctx.wait_entity(f"@e[tag={MAGO},{caja(c)}]")


def ir(ctx, x, y, z):
    ctx.run(f"tp {PLAYER} {x} {y} {z}", r"Teleported")


def lejos(ctx):
    ctx.run(f"forceload add {LEJOS[0] - 8} {LEJOS[1] - 8} {LEJOS[0] + 8} {LEJOS[1] + 8}", r"Marked|[Aa]dded|force|already")
    ctx.run(f"fill {LEJOS[0] - 2} {Y - 1} {LEJOS[1] - 2} {LEJOS[0] + 2} {Y - 1} {LEJOS[1] + 2} minecraft:stone", r"Successfully filled|No blocks")
    ir(ctx, LEJOS[0], Y, LEJOS[1])


def junto_al_mago(ctx, c):
    """El jugador entra por la puerta de la choza (a 3 bloques del mago, en el centro de la planta baja)."""
    x, z = SITIOS[c]
    h = 3 if PLANTILLA[c].startswith("pantano") else 0
    ir(ctx, x + 6.5, Y + h + 1, z + 6.5)


def inventario(ctx, item="*"):
    """Cuántos objetos (o de cuál) lleva el jugador."""
    m = ctx.run(f"clear {PLAYER} {item} 0", r"Found (\d+) matching|No items")
    return int(m.group(1) or 0)


def tag_de(ctx, c, tag):
    return ctx.count(f"@e[tag={MAGO},tag={tag},{caja(c)}]")


def oferta(ctx, c, i, campo):
    m = ctx.run(f"data get entity @e[tag={MAGO},{caja(c)},limit=1] Offers.Recipes[{i}].{campo}",
                r'has the following entity data: "([^"]+)"|Found no elements|No entity')
    return m.group(1)


def benigna(ctx, fails):
    if not colocar(ctx, "A"):
        fails.append("choza A: no aparece el mago")
        return
    ctx.ticks(5)
    if tag_de(ctx, "A", "heraldia_mago.benigno") != 1 or tag_de(ctx, "A", "heraldia_mago.nombrado") != 1:
        fails.append("choza A: el mago no queda decidido (bondadoso) y nombrado al cargarse")
    nombre = ctx.run(f"data get entity @e[tag={MAGO},{caja('A')},limit=1] CustomName", r"entity data: (.*)").group(1)
    print(f"mago de A: {nombre.strip()[:160]}")
    if "heraldia.chozas_mago.nombre" not in nombre or "heraldia.chozas_mago.apodo." not in nombre:
        fails.append(f"choza A: el mago no lleva su nombre generado: {nombre[:120]}")
    tratos = [oferta(ctx, "A", i, "sell.id") for i in range(8)]
    print(f"tratos de A: {tratos}")
    esperados = ["minecraft:glass_bottle", "minecraft:lapis_lazuli", "minecraft:potion", "minecraft:potion",
                 "minecraft:potion", "minecraft:enchanted_book", "minecraft:ender_pearl", "minecraft:emerald"]
    if tratos != esperados:
        fails.append(f"choza A: tratos {tratos} (esperados {esperados})")
    junto_al_mago(ctx, "A")
    x, z = SITIOS["A"]
    s.send(ctx.proc, f"player {PLAYER} look at {x + 6.5} {Y + 1.6} {z + 8.5}")
    s.send(ctx.proc, f"player {PLAYER} use once")      # no responde en la consola
    ctx.ticks(60)
    if ctx.count(f"@e[tag={MAGO},{caja('A')}]") != 1 or ctx.count(f"@e[tag={MALVADO}]"):
        fails.append("choza A (bondadosa): el mago se ha revelado o ha desaparecido con el jugador al lado")
    m = ctx.run(f"execute positioned {x + 6} {Y} {z + 8} run heraldia wizard", r"(?:Wizards within|Magos a menos de) 32 (?:blocks|bloques): (\d+)")
    lista = "".join(s.drain(ctx))
    if m.group(1) != "1" or not re.search(r"benign|bondadoso", lista):
        fails.append(f"/heraldia wizard junto a A: {m.group(0)} {lista[-200:]}")
    lejos(ctx)


def vencer(ctx, fails, c, premio):
    """Revela (forzado) el mago de la choza c, comprueba el Mago Malvado y lo vence el jugador."""
    if not colocar(ctx, c):
        fails.append(f"choza {c}: no aparece el mago")
        return
    x, z = SITIOS[c]
    junto_al_mago(ctx, c)      # con el jugador cerca: los vexes no son persistentes (lejos de todos, desaparecen)
    ctx.run(f"clear {PLAYER}", r"Removed|No items")
    ctx.ticks(5)
    marca = len(ctx.seen)
    ctx.run(f"execute positioned {x + 6} {Y} {z + 8} run heraldia wizard reveal",
            r"Wizard revealed at|Mago revelado en|no unrevealed wizard|ningún mago sin revelar")
    m = s.wait_for(ctx.lines, REVELA.pattern, s.COMMAND_TIMEOUT_S, ctx.seen) if not REVELA.search("".join(ctx.seen[marca:])) \
        else REVELA.search("".join(ctx.seen[marca:]))
    print(f"choza {c}: {m.group(0)}")
    if m.group(4) != "forzado" or m.group(5) != ("sí" if premio else "no") or m.group(6) != "3":
        fails.append(f"choza {c}: revelación {m.group(0)}")
    sel = f"@e[type=minecraft:evoker,tag={MALVADO},{caja(c, 4)}]"
    if ctx.count(sel) != 1:
        fails.append(f"choza {c}: {ctx.count(sel)} Magos Malvados (debe haber 1)")
    if ctx.count(f"@e[tag={MAGO},{caja(c)}]"):
        fails.append(f"choza {c}: el aldeano sigue ahí tras revelarse")
    for t in ("heraldia_guardian", "heraldia_anclado"):
        if ctx.count(f"@e[type=minecraft:evoker,tag={MALVADO},tag={t}]") != 1:
            fails.append(f"choza {c}: el Mago Malvado sin la etiqueta {t} (fases y barra de jefe)")
    vexes = ctx.count(f"@e[type=minecraft:vex,tag={VEX}]")
    if vexes != 3:
        fails.append(f"choza {c}: {vexes} vexes de entrada (deben ser 3)")
    tabla = ctx.run(f"data get entity {sel[:-1]},limit=1] DeathLootTable", r'entity data: "([^"]+)"|No entity').group(1)
    if tabla != ("heraldia:chozas_mago/malvado_premium" if premio else "heraldia:chozas_mago/malvado"):
        fails.append(f"choza {c}: tabla de botín del Mago Malvado {tabla}")
    nombre = ctx.run(f"data get entity {sel[:-1]},limit=1] CustomName", r"entity data: (.*)|No entity").group(1) or ""
    if "heraldia.chozas_mago.malvado" not in nombre:
        fails.append(f"choza {c}: el Mago Malvado no se llama así: {nombre[:100]}")
    # otra orden no revela nada más (ya no queda mago sin revelar en 32 bloques)
    ctx.run(f"execute positioned {x + 6} {Y} {z + 8} run heraldia wizard reveal",
            r"no unrevealed wizard|ningún mago sin revelar|Wizard revealed at|Mago revelado en")
    if ctx.count(f"@e[type=minecraft:evoker,tag={MALVADO}]") != 1:
        fails.append(f"choza {c}: una segunda revelación duplica al Mago Malvado")
    # el jugador lo vence
    p = ctx.pos(sel)
    ctx.ticks(20)
    marca = len(ctx.seen)
    ctx.run(f"damage {sel[:-1]},limit=1] 2000 minecraft:player_attack by {PLAYER}", r"Applied|damage|No entity")
    v = s.wait_for(ctx.lines, VENCIDO.pattern, s.COMMAND_TIMEOUT_S, ctx.seen) if not VENCIDO.search("".join(ctx.seen[marca:])) \
        else VENCIDO.search("".join(ctx.seen[marca:]))
    ctx.ticks(20)
    cerca = f"x={p[0]:.0f},y={p[1]:.0f},z={p[2]:.0f},distance=..10"
    # lo que cae y lo que el jugador ya ha recogido
    objetos = ctx.count(f"@e[type=minecraft:item,{cerca}]") + inventario(ctx)
    totems = ctx.count(f"@e[type=minecraft:item,{cerca},nbt={{Item:{{id:\"minecraft:totem_of_undying\"}}}}]") \
        + inventario(ctx, "minecraft:totem_of_undying")
    print(f"choza {c}: {v.group(0)}; {objetos} objetos en el suelo ({totems} tótems)")
    if v.group(4) != ("sí" if premio else "no"):
        fails.append(f"choza {c}: {v.group(0)} (premio {'sí' if premio else 'no'})")
    if objetos < 2:
        fails.append(f"choza {c}: el Mago Malvado suelta {objetos} objetos")
    if not premio and totems:
        fails.append(f"choza {c}: sin premio suelta un tótem (el del evocador vanilla no debe salir)")
    if ctx.count(f"@e[type=minecraft:vex,tag={VEX}]"):
        fails.append(f"choza {c}: quedan vexes del mago tras vencerlo")
    if not ctx.test(f"execute if entity @a[name={PLAYER},advancements={{heraldia:medianas/choza_mago/malvado=true}}]"):
        fails.append("logro medianas/choza_mago/malvado sin conceder")
    ctx.run(f"kill @e[type=minecraft:item,{cerca}]", r"Killed|No entity")
    lejos(ctx)


def natural(ctx, fails):
    """Malvados al 100 %: A sigue bondadosa; D nace malvada y se revela sola al llegar el jugador."""
    junto_al_mago(ctx, "A")
    ctx.ticks(60)
    if ctx.count(f"@e[tag={MAGO},tag=heraldia_mago.benigno,{caja('A')}]") != 1 or ctx.count(f"@e[tag={MALVADO},{caja('A', 4)}]"):
        fails.append("choza A: con malvados al 100 % la choza ya decidida cambia")
    lejos(ctx)
    if not colocar(ctx, "D"):
        fails.append("choza D: no aparece el mago")
        return
    ctx.ticks(5)
    if tag_de(ctx, "D", "heraldia_mago.malvado") != 1 or ctx.count(f"@e[tag={MALVADO},{caja('D', 4)}]"):
        fails.append("choza D: no nace malvada sin revelar")
    marca = len(ctx.seen)
    junto_al_mago(ctx, "D")
    m = s.wait_for(ctx.lines, REVELA.pattern, s.COMMAND_TIMEOUT_S, ctx.seen) if not REVELA.search("".join(ctx.seen[marca:])) \
        else REVELA.search("".join(ctx.seen[marca:]))
    print(f"choza D: {m.group(0)}")
    if m.group(4) != "malvado":
        fails.append(f"choza D: {m.group(0)}")
    ctx.ticks(10)
    if ctx.count(f"@e[type=minecraft:evoker,tag={MALVADO},{caja('D', 4)}]") != 1 or ctx.count(f"@e[tag={MAGO},{caja('D')}]"):
        fails.append("choza D: al acercarse el jugador no se convierte en el Mago Malvado")
    lejos(ctx)


def jugador(ctx):
    lejos_x, lejos_z = LEJOS
    ctx.run(f"forceload add {lejos_x - 8} {lejos_z - 8} {lejos_x + 8} {lejos_z + 8}", r"Marked|[Aa]dded|force|already")
    ctx.run(f"player {PLAYER} spawn at {lejos_x} {Y + 2} {lejos_z}", r"joined the game")
    if not ctx.until(f"execute if entity @a[name={PLAYER}]"):
        raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
    s.send(ctx.proc, f"gamemode survival {PLAYER}")      # puede no responder si ya lo está
    ctx.until(f"execute if entity @a[name={PLAYER},gamemode=survival]")
    ctx.run(f"effect give {PLAYER} minecraft:resistance infinite 4 true", r"Applied effect|Gave|Unable to apply")
    ctx.run(f"effect give {PLAYER} minecraft:regeneration infinite 4 true", r"Applied effect|Gave|Unable to apply")
    lejos(ctx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-chozas-mago"))
    a = ap.parse_args()
    a.work = os.path.abspath(a.work)
    os.makedirs(a.work, exist_ok=True)
    fails = []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    configurar(a.work, 0, 0)
    proc, ctx = at.start_server(a.work, launcher)
    try:
        jugador(ctx)
        benigna(ctx, fails)
        vencer(ctx, fails, "B", premio=False)
        configurar(a.work, 0, 100)
        ctx.run("heraldia reload", r"Heraldia: configuración recargada")
        vencer(ctx, fails, "C", premio=True)
        configurar(a.work, 100, 100)
        ctx.run("heraldia reload", r"Heraldia: configuración recargada")
        natural(ctx, fails)
        ctx.run(f"player {PLAYER} kill", r"left the game")
    finally:
        parar(proc, ctx)
    reveladas = len(REVELA.findall(ctx.log()))
    # segundo arranque: nada se revela de nuevo ni se duplica
    proc, ctx = at.start_server(a.work, launcher)
    try:
        jugador(ctx)
        ctx.until(f"execute if entity @e[type=minecraft:evoker,tag={MALVADO}]")
        ctx.ticks(20)
        malos = ctx.count(f"@e[type=minecraft:evoker,tag={MALVADO}]")
        enD = ctx.count(f"@e[type=minecraft:evoker,tag={MALVADO},{caja('D', 8)}]")
        print(f"tras reiniciar: {malos} Magos Malvados ({enD} en D); revelaciones en el primer arranque: {reveladas}")
        if malos != 1 or enD != 1:
            fails.append(f"tras reiniciar: {malos} Magos Malvados, {enD} en D (debe quedar solo el de D)")
        if ctx.count(f"@e[tag={MAGO},tag=heraldia_mago.benigno,{caja('A')}]") != 1:
            fails.append("tras reiniciar: el mago bondadoso de A no está")
        junto_al_mago(ctx, "A")
        ctx.ticks(60)
        if REVELA.search(ctx.log()) or ctx.count(f"@e[tag={MAGO},{caja('A')}]") != 1:
            fails.append("tras reiniciar: un mago se revela otra vez")
        if estado(ctx, r"Wizard's huts: evil wizards 100 %, premium loot 100 %|Chozas de mago: magos malvados 100 %") is None:
            fails.append("/heraldia status sin la línea de las chozas de mago")
        ctx.run(f"player {PLAYER} kill", r"left the game")
    finally:
        parar(proc, ctx)
    if fails:
        print("FALLOS:")
        for f in fails:
            print(" -", f)
        return 1
    print("OK: mago bondadoso con tratos que no se revela, Mago Malvado forzado con vexes y vencido (botín sin tótem, "
          "logro), premio al 100 %, decisión guardada, revelación al acercarse y reinicio sin duplicados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
