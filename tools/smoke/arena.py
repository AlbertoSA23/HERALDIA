"""Arena de oleadas (T31, Java: arena/) en un servidor dedicado 26.3 real, con un jugador simulado (Carpet).

Uso: python3 tools/smoke/arena.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-arena"
Primer arranque (mundo nuevo, con arena.generar_en_mundos_nuevos):
  1. la arena se genera sola a 200-300 bloques del spawn; /heraldia arena remove (con confirmación) la quita; confirmar
     sin propuesta falla; /heraldia arena place propone el sitio y «place confirm» la coloca (la campana, la
     puerta abierta y el cristal, donde dice arena.json); otra vez «place» dice que ya hay una;
  2. protección: el jugador simulado (creativo, sin ser operador) no rompe un bloque ni coloca piedra; como operador sí
     rompe; una TNT dentro no rompe nada (y fuera sí); un pistón no empuja su muro (y otro fuera sí); un dispensador
     pegado a la arena no vacía su cubo de lava (lo suelta como objeto) y otro lejos sí;
  3. partida: el jugador (supervivencia, resistencia 255) toca la campana: cuenta atrás, puerta cerrada, oleada 1 con 4
     enemigos sin modificador de oleada y oleada 2 con 6 y +10 % de vida (heraldia:arena_vida 0,1); los mata
     (/damage ... by el jugador): no sueltan objetos y dan el 15 % de la experiencia vanilla (log de cada oleada);
     en la 5, el mini-jefe (heraldia_guardian) pasa de fase y sus refuerzos entran en la oleada; al superarla, récord
     en el marcador, recompensa y logro heraldia:arena/oleada_5;
  4. muerte en el ruedo (daño en la pausa): no suelta objetos ni experiencia, sus datos guardados conservan los
     diamantes y los niveles (Carpet desconecta al jugador simulado al morir: la reaparición vanilla, COPY_FROM y el
     teletransporte a la entrada no se pueden probar aquí) y la partida acaba (sin mobs, puerta abierta);
  Lo que el servidor escribe en la consola sale en inglés (el servidor dedicado carga el en_us del mod).
  5. otra partida (/heraldia arena start) con mobs vivos y la puerta cerrada; se guarda y se mata el proceso (como un
     cierre en seco).
Segundo arranque (el mismo mundo): los mobs de la arena se quitan al cargarse, la puerta está abierta y no hay partida.
"""
import argparse, json, math, os, re, shutil, sys, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guia import Server
from trofeos import CARPET
from modrinth import fetch

P = "Testigo"
ARENA = "@e[tag=heraldia_arena]"
NUM = r"(-?\d+(?:\.\d+)?)"


def plano(jar):
    with zipfile.ZipFile(jar) as z:
        return json.loads(z.read("heraldia/arena.json"))


def config(work):
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    cfg["arena"] = {"generar_en_mundos_nuevos": True}
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


class Prueba:
    def __init__(self, ctx, fails):
        self.ctx, self.fails = ctx, fails

    def check(self, ok, msg):
        if not ok:
            self.fails.append(msg)
            print("FALLA:", msg)
        return ok

    def esperar_log(self, patron, timeout=120):
        """La primera coincidencia de `patron` en el log (lee lo que llega con órdenes baratas), o None."""
        end = time.monotonic() + timeout
        while True:
            m = re.search(patron, self.ctx.log())
            if m:
                return m
            if time.monotonic() > end:
                return None
            self.ctx.run("time query gametime", r"[Tt]ime is \d+")
            time.sleep(0.5)

    def veces(self, patron):
        return len(re.findall(patron, self.ctx.log()))

    def esperar_veces(self, patron, n, timeout=120):
        """¿Aparece `patron` al menos n veces en el log antes de `timeout` segundos?"""
        end = time.monotonic() + timeout
        while self.veces(patron) < n:
            if time.monotonic() > end:
                return False
            self.ctx.run("time query gametime", r"[Tt]ime is \d+")
            time.sleep(0.5)
        return True

    def num(self, cmd):
        m = self.ctx.run(cmd, rf"(?:is|has|data:) {NUM}f?\b|No entity|[Nn]o modifier|has no|There is no|not found|Can't find|"
                              r"Can't get|none is set")
        return float(m.group(1)) if m.lastindex and m.group(1) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-arena"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    pl = plano(a.jar)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    config(a.work)
    fails, textos = [], []
    srv = Server(a.work, launcher)
    try:
        caja = primer_arranque(Prueba(srv.ctx, fails), pl)
        # 5. una partida a medias: se guarda y se mata el proceso
        if caja:
            a_medias(Prueba(srv.ctx, fails), pl, caja)
        srv.proc.kill()
        srv.proc.wait(timeout=60)
    finally:
        srv.stop()
        textos.append(srv.ctx.log())
    if caja:
        srv = Server(a.work, launcher)
        try:
            segundo_arranque(Prueba(srv.ctx, fails), pl, caja)
        finally:
            srv.stop()
            textos.append(srv.ctx.log())
    for bad in ("Registry loading errors", "Failed to load datapacks", "at io.github.albertosa23", "arena: mob ", "falta la plantilla"):
        if any(bad in t for t in textos):
            fails.append(f"el log contiene {bad!r}")
    print("ARENA:", "OK" if not fails else fails)
    return 1 if fails else 0


def rel(caja, pl, clave):
    o = caja[:3]
    return tuple(o[i] + pl[clave][i] for i in range(3))


def primer_arranque(p, pl):
    ctx = p.ctx
    # 1. generada sola en un mundo nuevo, a 200-300 bloques del spawn
    m = p.esperar_log(r"arena: sitio propuesto en (-?\d+) (-?\d+) (-?\d+) \(a (\d+) bloques del spawn")
    if not p.check(m, "mundo nuevo: no se busca sitio para la arena"):
        return None
    p.check(200 <= int(m.group(4)) <= 300, f"arena a {m.group(4)} bloques del spawn (200-300)")
    m = p.esperar_log(r"arena: colocada en (-?\d+) (-?\d+) (-?\d+) \(caja (-?\d+) (-?\d+) (-?\d+) a (-?\d+) (-?\d+) (-?\d+)\)")
    if not p.check(m, "mundo nuevo: la arena no se coloca sola"):
        return None
    sola = tuple(int(g) for g in m.groups())
    for rule in ("spawn_mobs", "advance_time"):
        ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
    ctx.run("difficulty normal", r"difficulty|Difficulty")
    # quitar, con confirmación
    ctx.run("heraldia arena remove", r"Se quitará la arena|will be removed")
    ctx.run("heraldia arena remove confirm", r"arena: quitada de|arena: obra terminada")
    p.check(p.esperar_log(r"arena: quitada de"), "no se quita la arena")
    ctx.run("heraldia arena place confirm", r"Primero pide un sitio|First ask for a site")
    # place: propuesta y confirmación
    m = ctx.run("heraldia arena place", r"arena: sitio propuesto en (-?\d+) (-?\d+) (-?\d+) \(a (\d+) bloques")
    p.check(200 <= int(m.group(4)) <= 300, f"propuesta a {m.group(4)} bloques del spawn")
    ctx.run("heraldia arena place confirm", r"Colocando la arena en|Building the arena at")
    if not p.check(p.esperar_veces(r"arena: colocada en", 2), "«place confirm» no coloca la arena"):
        return None
    caja = sola[3:]
    p.check(re.findall(r"arena: colocada en .*\(caja ([-\d ]+) a", ctx.log())[-1].split() == [str(c) for c in caja[:3]],
            "la arena colocada a mano no está donde la generada (la búsqueda es determinista)")
    ctx.run("heraldia arena place", r"Ya hay una arena en|There is already an arena")
    minx, miny, minz, maxx, maxy, maxz = caja
    ctx.run(f"forceload add {minx - 16} {minz - 16} {maxx + 16} {maxz + 16}", r"Marked|force|already")
    bell, reap = rel(caja, pl, "campana"), rel(caja, pl, "reaparicion")
    p.check(ctx.block(bell, "minecraft:bell"), f"sin campana en {bell}")
    puerta = tuple(caja[i] + pl["puerta"][0][i] for i in range(3))
    p.check(ctx.block(puerta, "minecraft:air"), "la puerta no está abierta")
    cx, cz = caja[0] + pl["centro"][0], caja[2] + pl["centro"][2]
    p.check(ctx.block((cx + 15, miny + 6, cz), "minecraft:glass"), "sin cristal sobre el muro del ruedo")
    p.check(ctx.block((cx, miny + 11, cz), "minecraft:barrier"), "sin techo de barreras sobre el ruedo")
    ctx.run("heraldia arena", r"Arena de oleadas en|Wave arena at")

    # 2. protección
    ctx.run(f"player {P} spawn at {reap[0] + 0.5} {reap[1]} {reap[2] + 0.5}", r"joined the game|Player .* spawn|Unknown|Incorrect")
    if not ctx.until(f"execute if entity @a[name={P}]"):
        raise SystemExit(f"no aparece el jugador simulado {P} (Carpet)")
    ctx.run(f"gamemode survival {P}", r"Set .* game mode|game mode")
    ctx.run(f"gamemode creative {P}", r"Set .* game mode|game mode")
    suelo = (reap[0], reap[1] - 1, reap[2] + 1)
    estado = "minecraft:polished_andesite"
    p.check(ctx.block(suelo, estado), f"no hay {estado} en {suelo} (plano de la arena)")
    s.send(ctx.proc, f"player {P} look at {suelo[0] + 0.5} {suelo[1] + 1} {suelo[2] + 0.5}")
    ctx.ticks(5)
    romper(ctx)
    p.check(ctx.block(suelo, estado), "un jugador que no es operador rompe un bloque de la arena")
    ctx.run(f"item replace entity {P} weapon.mainhand with minecraft:stone", r"Replaced|replaced")
    s.send(ctx.proc, f"player {P} use once")
    ctx.ticks(10)
    p.check(ctx.block((suelo[0], suelo[1] + 1, suelo[2]), "minecraft:air"), "un jugador que no es operador coloca un bloque")
    ctx.run(f"item replace entity {P} weapon.mainhand with minecraft:air", r"Replaced|replaced")
    ctx.run(f"op {P}", r"Made .* operator|already|Nothing changed")
    romper(ctx)
    p.check(ctx.block(suelo, "minecraft:air"), "un operador no puede romper un bloque de la arena")
    ctx.run(f"deop {P}", r"no longer|Nothing changed|not an operator")
    ctx.run(f"setblock {' '.join(map(str, suelo))} {estado}", r"Changed the block|Could not set")
    # explosión dentro (en el paseo, al norte) y fuera (control)
    tx, ty, tz = cx, miny + pl["suelo"] + 1, minz + 3
    vecinos = [(tx + dx, ty - 1, tz + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)]
    ctx.run(f"summon minecraft:tnt {tx} {ty} {tz} {{fuse:1}}", r"Summoned")
    fx, fy, fz = maxx + 20, miny + pl["suelo"] + 6, cz
    ctx.run(f"fill {fx - 2} {fy - 1} {fz - 2} {fx + 2} {fy + 3} {fz + 2} minecraft:air", r"Successfully filled|No blocks")
    ctx.run(f"fill {fx - 1} {fy - 1} {fz - 1} {fx + 1} {fy - 1} {fz + 1} minecraft:stone", r"Successfully filled|No blocks")
    ctx.run(f"summon minecraft:tnt {fx} {fy} {fz} {{fuse:1}}", r"Summoned")
    ctx.ticks(30)
    p.check(all(not ctx.block(v, "minecraft:air") for v in vecinos), "una TNT rompe bloques de la arena")
    p.check(ctx.block((fx, fy - 1, fz), "minecraft:air"), "control: la TNT de fuera no rompe nada (¿no explotó?)")
    # pistón contra un pilar de la fachada (este) y otro fuera (control)
    py = miny + pl["suelo"] + 3
    pilar = (maxx, py, cz)
    p.check(not ctx.block(pilar, "minecraft:air"), f"no hay pilar en {pilar}")
    ctx.run(f"setblock {maxx + 1} {py} {cz} minecraft:piston[facing=west]", r"Changed the block|Could not set")
    ctx.run(f"setblock {maxx + 2} {py} {cz} minecraft:redstone_block", r"Changed the block|Could not set")
    gx = maxx + 12
    ctx.run(f"fill {gx - 3} {py - 1} {cz - 1} {gx + 2} {py + 1} {cz + 1} minecraft:air", r"Successfully filled|No blocks")
    ctx.run(f"setblock {gx - 1} {py} {cz} minecraft:stone", r"Changed the block|Could not set")
    ctx.run(f"setblock {gx} {py} {cz} minecraft:piston[facing=west]", r"Changed the block|Could not set")
    ctx.run(f"setblock {gx + 1} {py} {cz} minecraft:redstone_block", r"Changed the block|Could not set")
    ctx.ticks(10)
    p.check(ctx.block((maxx + 1, py, cz), "minecraft:piston[extended=false]"), "un pistón empuja el muro de la arena")
    p.check(not ctx.block(pilar, "minecraft:air"), "el pilar de la arena se movió")
    p.check(ctx.block((gx, py, cz), "minecraft:piston[extended=true]"), "control: el pistón de fuera no se mueve")
    # dispensador con un cubo de lava pegado a la fachada (oeste) y otro lejos (control): ArenaCuboMixin
    for x0, desc in ((minx - 2, "junto a la arena"), (maxx + 30, "lejos (control)")):
        ctx.run(f"fill {x0 - 2} {py - 1} {cz - 1} {x0 + 1} {py + 1} {cz + 1} minecraft:air", r"Successfully filled|No blocks")
        ctx.run(f"fill {x0 - 2} {py - 2} {cz - 1} {x0 + 1} {py - 2} {cz + 1} minecraft:stone", r"Successfully filled|No blocks")
        ctx.run(f'setblock {x0} {py} {cz} minecraft:dispenser[facing=east]{{Items:[{{Slot:0b,id:"minecraft:lava_bucket",count:1}}]}}',
                r"Changed the block|Could not set")
        ctx.run(f"setblock {x0 - 1} {py} {cz} minecraft:redstone_block", r"Changed the block|Could not set")
    ctx.ticks(10)
    p.check(not ctx.block((minx - 1, py, cz), "minecraft:lava"), "un dispensador vacía un cubo de lava junto a la arena")
    p.check(ctx.until(f"execute if entity @e[type=minecraft:item,x={minx - 1},y={py},z={cz},distance=..3,"
                      f"nbt={{Item:{{id:\"minecraft:lava_bucket\"}}}}]"),
            "el dispensador junto a la arena no suelta el cubo de lava como objeto")
    p.check(ctx.block((maxx + 31, py, cz), "minecraft:lava"), "control: el dispensador lejos de la arena no vacía su cubo")
    ctx.run(f"fill {maxx + 27} {py - 1} {cz - 1} {maxx + 33} {py + 1} {cz + 1} minecraft:air", r"Successfully filled|No blocks")
    ctx.run(f"fill {minx - 4} {py - 1} {cz - 1} {minx - 1} {py + 1} {cz + 1} minecraft:air", r"Successfully filled|No blocks")
    ctx.run(f"kill @e[type=minecraft:item,x={minx - 1},y={py},z={cz},distance=..6]", r"Killed|No entity")

    # 3. partida con la campana
    ctx.run(f"gamemode survival {P}", r"Set .* game mode|game mode")
    ctx.run(f"effect give {P} minecraft:resistance infinite 255 true", r"Applied effect|Gave")
    ctx.run(f"give {P} minecraft:diamond 7", r"Gave")
    ctx.run(f"experience add {P} 10 levels", r"Gave|experience")
    ctx.run(f"tp {P} {bell[0] + 0.5} {bell[1]} {bell[2] - 1.5}", r"Teleported")
    s.send(ctx.proc, f"player {P} look at {bell[0] + 0.5} {bell[1] + 0.4} {bell[2] + 0.5}")
    ctx.ticks(5)
    s.send(ctx.proc, f"player {P} use once")
    if not p.check(p.esperar_log(rf"arena: cuenta atrás \(la empieza {P}\)", timeout=60), "la campana no empieza la partida"):
        return caja
    p.check(ctx.block(puerta, "minecraft:iron_bars"), "la puerta no se cierra al empezar")
    p.check(p.esperar_log(r"arena: partida empieza con 1 participantes"), "la partida no empieza con el jugador")
    p.check(p.esperar_log(r"arena: oleada 1: 4 enemigos"), "la oleada 1 no trae 4 enemigos")
    p.check(ctx.until(f"execute if entity {ARENA}") and wait_count(ctx, ARENA, 4), "no salen 4 enemigos en la oleada 1")
    p.check(p.num(f"attribute {ARENA[:-1]},limit=1] minecraft:max_health modifier value get heraldia:arena_vida") in (None, 0.0),
            "oleada 1 con modificador de vida")
    limpiar(p, 1)
    items = ctx.count(f"@e[type=item,x={minx},y={miny},z={minz},dx={maxx - minx},dy={maxy - miny},dz={maxz - minz}]")
    if not p.check(items == 0, f"los mobs de la arena sueltan objetos ({items})"):
        print("DIAG:", ctx.run(f"data get entity @e[type=item,limit=1,x={minx},y={miny},z={minz},dx={maxx - minx},dy={maxy - miny},"
                               f"dz={maxz - minz}]", r"entity data|No entity").string)
    experiencia(p, 1)
    p.check(p.esperar_log(r"arena: oleada 2: 6 enemigos", timeout=60), "la oleada 2 no trae 6 enemigos")
    p.check(wait_count(ctx, ARENA, 6), "no salen 6 enemigos en la oleada 2")
    v = p.num(f"attribute {ARENA[:-1]},limit=1] minecraft:max_health modifier value get heraldia:arena_vida")
    p.check(v is not None and abs(v - 0.1) < 1e-6, f"oleada 2: heraldia:arena_vida {v} (debía ser 0,1)")
    v = p.num(f"attribute {ARENA[:-1]},limit=1] minecraft:attack_damage modifier value get heraldia:arena_dano")
    p.check(v is not None and abs(v - 0.1) < 1e-6, f"oleada 2: heraldia:arena_dano {v} (debía ser 0,1)")
    limpiar(p, 2)
    experiencia(p, 2)
    for n in (3, 4):
        p.check(p.esperar_log(rf"arena: oleada {n}: \d+ enemigos", timeout=60), f"no empieza la oleada {n}")
        limpiar(p, n)
    # oleada 5: el mini-jefe
    p.check(p.esperar_log(r"arena: oleada 5: 13 enemigos", timeout=60), "la oleada 5 no trae 12 enemigos y el mini-jefe")
    jefe = "@e[tag=heraldia_arena,tag=heraldia_guardian,limit=1]"
    if p.check(p.esperar_log(r"arena: mini-jefe minecraft:zombie en la oleada 5"), "no sale el mini-jefe en la oleada 5"):
        ctx.wait_entity(jefe)
        ctx.ticks(25)
        ctx.run(f"damage {jefe} 70 minecraft:player_attack by {P}", r"Applied|damage")
        p.check(p.esperar_log(r"jefes: zombie/\w+ pasa a la fase 2", timeout=30), "el mini-jefe no pasa a la fase 2")
        p.check(p.esperar_log(r"arena: un refuerzo del mini-jefe entra en la oleada", timeout=30),
                "los refuerzos del mini-jefe no entran en la oleada")
    limpiar(p, 5)
    p.check(p.esperar_log(rf"arena: recompensa 1 \(\d+ objetos\) para {P} en la oleada 5"), "sin recompensa en la oleada 5")
    p.check(ctx.test(f"execute if entity @a[name={P},advancements={{heraldia:arena/oleada_5=true}}]"), "sin el logro de la oleada 5")
    p.check(p.num(f"scoreboard players get {P} heraldia_arena") == 5, "el marcador no tiene el récord 5 del jugador")
    p.check(p.num("scoreboard players get -servidor- heraldia_arena") == 5, "el marcador no tiene el récord 5 del servidor")
    p.check(p.esperar_log(rf"arena: récord del servidor: {P} en la oleada 5"), "sin anuncio del récord")

    # 4. muerte en el ruedo, en la pausa. Carpet desconecta al jugador simulado al morir (no pasa por la reaparición
    # vanilla): se comprueba que no suelta nada y que, al volver a crearlo, sus datos guardados conservan lo que llevaba.
    nivel_antes = p.num(f"experience query {P} levels")
    muerte = ctx.pos(f"@a[name={P}]")
    cerca = f"x={muerte[0]:.1f},y={muerte[1]:.1f},z={muerte[2]:.1f},distance=..4" if muerte else "distance=..0"
    ctx.run("kill @e[type=experience_orb]", r"Killed|No entity")       # los de los mobs (en la pausa no salen más)
    orbes_antes = ctx.count(f"@e[type=experience_orb,{cerca}]")
    ctx.run(f"effect clear {P}", r"Removed|effect")
    ctx.run(f"damage {P} 1000 minecraft:generic", r"Applied|damage")
    p.check(p.esperar_log(rf"arena: {P} cae en el ruedo y conserva", timeout=30), "al caer en el ruedo no conserva el inventario")
    ctx.ticks(10)
    p.check(ctx.count('@e[type=item,nbt={Item:{id:"minecraft:diamond"}}]') == 0, "suelta sus diamantes al caer en el ruedo")
    p.check(ctx.count(f"@e[type=experience_orb,{cerca}]") <= orbes_antes, "suelta experiencia al caer en el ruedo")
    ctx.until(f"execute if entity @a[name={P}]", want=False, timeout=30)
    ctx.run(f"player {P} spawn at {reap[0] + 0.5} {reap[1]} {reap[2] + 0.5}", r"joined the game|Player .* spawn|Unknown|Incorrect")
    ctx.until(f"execute if entity @a[name={P}]")
    p.check(ctx.test(f'execute if entity @a[name={P},nbt={{Inventory:[{{id:"minecraft:diamond",count:7}}]}}]'),
            "pierde los diamantes al caer en el ruedo")
    nivel = p.num(f"experience query {P} levels")
    p.check(nivel is not None and nivel_antes is not None and nivel >= nivel_antes and nivel >= 10,
            f"pierde la experiencia al caer en el ruedo ({nivel_antes} -> {nivel})")
    p.check(p.esperar_log(r"arena: partida terminada \(sin participantes\) con 5 oleadas superadas"), "la partida no acaba sin participantes")
    p.check(ctx.count(ARENA) == 0, "quedan mobs de la arena al acabar")
    p.check(ctx.block(puerta, "minecraft:air"), "la puerta no se abre al acabar")
    return caja


def a_medias(p, pl, caja):
    ctx = p.ctx
    cx, cz = caja[0] + pl["centro"][0], caja[2] + pl["centro"][2]
    ctx.run(f"tp {P} {cx + 0.5} {caja[1] + 1} {cz + 0.5}", r"Teleported")
    ctx.run("heraldia arena start", r"Prepárate|Get ready")
    ctx.run(f"effect give {P} minecraft:resistance infinite 255 true", r"Applied effect|Gave")
    p.check(p.esperar_veces(r"arena: oleada 1: 4 enemigos", 2, timeout=60), "la segunda partida no empieza")
    p.check(wait_count(ctx, ARENA, 4), "la segunda partida no saca sus mobs")
    puerta = tuple(caja[i] + pl["puerta"][0][i] for i in range(3))
    p.check(ctx.block(puerta, "minecraft:iron_bars"), "segunda partida: la puerta no se cierra")
    ctx.run("save-all flush", r"Saved the game")


def segundo_arranque(p, pl, caja):
    ctx = p.ctx
    m = p.esperar_log(r"arena: en (-?\d+) (-?\d+) (-?\d+)", timeout=60)
    p.check(m, "tras reiniciar no se recuerda la arena")
    p.check(p.esperar_log(r"arena: quitado un mob de arena de una partida anterior", timeout=120),
            "tras reiniciar no se quitan los mobs de la partida anterior")
    p.check(ctx.until(f"execute if entity {ARENA}", want=False, timeout=60), "tras reiniciar quedan mobs de la arena")
    puerta = tuple(caja[i] + pl["puerta"][0][i] for i in range(3))
    p.check(ctx.block(puerta, "minecraft:air"), "tras reiniciar la puerta sigue cerrada")
    ctx.run("heraldia arena", r"Arena de oleadas en|Wave arena at")
    p.check(p.esperar_log(r"Sin partida|No match", timeout=30), "tras reiniciar hay una partida")
    p.check(ctx.block(tuple(caja[i] + pl["campana"][i] for i in range(3)), "minecraft:bell"), "tras reiniciar no está la campana")


def wait_count(ctx, sel, n, timeout=60):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if ctx.count(sel) == n:
            return True
        ctx.ticks(5)
    print(f"DIAG: {sel}: {ctx.count(sel)} (esperados {n})")
    return False


def limpiar(p, n, timeout=180):
    """Mata (a nombre del jugador) a los enemigos de la oleada n hasta que se supere."""
    ctx = p.ctx
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if re.search(rf"arena: oleada {n} superada", ctx.log()):
            return True
        if ctx.count(ARENA):
            ctx.run(f"damage {ARENA[:-1]},limit=1,sort=random] 1000 minecraft:player_attack by {P}", r"Applied|damage|No entity")
        else:
            ctx.ticks(5)
    p.check(False, f"no se supera la oleada {n}")
    return False


def experiencia(p, n):
    m = re.search(rf"arena: oleada {n} superada \(experiencia: (\d+) de vanilla, (\d+) dada, al (\d+) %\)", p.ctx.log())
    if not p.check(m, f"oleada {n}: sin el resumen de experiencia"):
        return
    vanilla, dada, pct = (int(g) for g in m.groups())
    mobs = 4 if n == 1 else 6
    p.check(pct == 15 and vanilla > 0, f"oleada {n}: experiencia vanilla {vanilla} al {pct} %")
    p.check(abs(dada - vanilla * 0.15) <= mobs, f"oleada {n}: {dada} de experiencia de {vanilla} (debía ser el 15 %)")


def romper(ctx):
    """El jugador simulado pica el bloque al que mira (en creativo, al instante): «attack once» de Carpet no rompe nada."""
    s.send(ctx.proc, f"player {P} attack continuous")
    ctx.ticks(20)
    s.send(ctx.proc, f"player {P} stop")
    ctx.ticks(5)


if __name__ == "__main__":
    sys.exit(main())
