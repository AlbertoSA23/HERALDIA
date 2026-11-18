"""Fases, refuerzos y barra de jefe de los guardianes en un servidor dedicado 26.3 real (Java: jefes/).

Uso: python3 tools/smoke/boss_phases.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Con un jugador simulado (Carpet, en creativo: los refuerzos no le atacan y no muere) a 8 bloques de cada guardián.
Los guardianes se invocan con /summon solo con sus etiquetas (como uno ya generado en un mundo existente: el estado de
las fases vive en sus Tags) y NoAI (no se mueven); se les hace daño con /damage ... by <jugador> hasta cada umbral:
  1. castillo (zombi, refuerzos propios: 2 zombis con espada y yelmo y un esqueleto): al 80 % nada; al 60 % la fase 2
     (etiqueta, velocidad/resistencia/fuerza, sus 3 refuerzos con heraldia_refuerzo, heraldia_anclado y heraldia_adulto,
     sin la etiqueta ni la tabla del guardián, adultos y con su equipo); otro golpe en la franja no repite; al 25 % la
     fase 3 (velocidad II) con solo 1 refuerzo más (tope de 4 vivos); muertos los refuerzos, otro golpe no llama más.
     La barra: para 1 jugador al primer golpe, quitada al alejarse el jugador, otra vez al volver y quitada al morir.
  2. stray sin id de única (guardián de un mundo viejo): herido sin nadie a menos de 48 bloques no pasa de fase ni
     muestra la barra; con el jugador de vuelta, sí, con la familia de su tipo (2 strays).
  3. faro (ahogado, familia por defecto): un solo golpe del 100 % al 10 % da las dos fases y 4 ahogados (2 + 2).
  4. Con jefes.fases/refuerzos/barra desactivados (el servidor se reinicia con esa configuración): nada de lo anterior.
Lo que se ve en el cliente (barra, aviso en la barra de acción, partículas, sonido) no se puede leer desde la consola:
la barra se comprueba por las líneas del log que escribe el mod al mostrarla y quitarla.
"""
import argparse, json, os, queue, re, shutil, subprocess, sys, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from modrinth import MODS, fetch

CARPET = (MODS["carpet"].file, MODS["carpet"].url, MODS["carpet"].sha512)
PLAYER = "Testigo"
X, Y, Z = 0, 101, 0
GZ = 8                       # los guardianes, a 8 bloques del jugador (dentro del radio de 32 de la barra)
REF = "@e[tag=heraldia_refuerzo]"
HEALTH = 100


def reinforcements(jar):
    with zipfile.ZipFile(jar) as z:
        return json.loads(z.read("heraldia/jefes.json"))


def guardian(mob, tag, tags):
    return (f'summon minecraft:{mob} {X} {Y} {Z + GZ} {{NoAI:1b,PersistenceRequired:1b,Health:{HEALTH}f,'
            f'Tags:[{",".join(json.dumps(t) for t in ["heraldia_guardian", "heraldia_anclado", "heraldia_adulto", tag] + tags)}],'
            f'CustomName:"Jefe de prueba",attributes:[{{id:"minecraft:max_health",base:{HEALTH}.0d}},'
            f'{{id:"minecraft:armor",base:0.0d}}]}}')


class Test:
    def __init__(self, ctx, fails):
        self.ctx, self.fails = ctx, fails

    def check(self, ok, msg):
        if not ok:
            self.fails.append(msg)
        return ok

    def strike(self, sel, n):
        # la invulnerabilidad tras un golpe dura 10 ticks (20 de hurtTime): se espera antes del siguiente
        self.ctx.ticks(25)
        self.ctx.run(f"damage {sel} {n} minecraft:player_attack by {PLAYER}", r"Applied|damage")
        self.ctx.ticks(5)

    def log(self, pattern, timeout=30):
        """¿Aparece `patron` en el log? Lee lo que vaya llegando con órdenes baratas hasta `timeout` segundos."""
        end = time.monotonic() + timeout
        while True:
            if re.search(pattern, self.ctx.log()):
                return True
            if time.monotonic() > end:
                return False
            self.ctx.run("time query gametime", r"[Tt]ime is \d+")
            time.sleep(0.5)

    def times(self, pattern):
        return len(re.findall(pattern, self.ctx.log()))

    def tally(self, sel, n, msg):
        got = self.ctx.count(sel)
        return self.check(got == n, f"{msg}: {got} (debían ser {n}) [{sel}]")


def start_up(work, launcher, hour):
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)
    s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
    ctx.run(f"forceload add {X - 16} {Z - 16} {X + 16} {Z + 16}", r"Marked|force|already")
    for _ in range(s.PLACE_ATTEMPTS):
        m = ctx.run(f"fill {X - 10} {Y} {Z - 6} {X + 10} {Y + 6} {Z + GZ + 10} minecraft:air", r"Successfully filled|No blocks")
        if "not loaded" not in m.string:
            break
        time.sleep(s.PLACE_RETRY_S)
    ctx.run(f"fill {X - 10} {Y - 1} {Z - 6} {X + 10} {Y - 1} {Z + GZ + 10} minecraft:stone", r"Successfully filled|No blocks")
    # De noche y sin que pase el tiempo (zombis y esqueletos no arden), sin monstruos naturales, dificultad normal
    # (en pacífico no hay refuerzos; en difícil los zombis llaman a los suyos, vanilla).
    for rule in ("spawn_mobs", "advance_time"):
        ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
    ctx.run(f"time set {hour}", rf"Set .*{hour}")     # a la misma hora que ya tiene, /time set no responde
    ctx.run("difficulty normal", r"difficulty|Difficulty")
    ctx.run(f"player {PLAYER} spawn at {X} {Y} {Z}", r"joined the game|Player .* spawn|Unknown|Incorrect")
    if not ctx.until(f"execute if entity @a[name={PLAYER}]"):
        raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
    # Carpet lo crea en creativo desde la consola, y /gamemode al mismo modo no responde: se pasa por supervivencia
    ctx.run(f"gamemode survival {PLAYER}", r"Set .* game mode|game mode")
    ctx.run(f"gamemode creative {PLAYER}", r"Set .* game mode|game mode")
    return proc, ctx


def halt(proc):
    if proc.poll() is None:
        s.send(proc, "stop")
        try:
            proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()


def castle(p, dataset):
    ctx = p.ctx
    lst = dataset["unicas"]["castillo"]
    g = "@e[tag=prueba_castillo,limit=1]"
    ctx.run(guardian("zombie", "heraldia_guardian.castillo", ["prueba_castillo"]), r"Summoned")
    if not ctx.wait_entity(g):
        p.fails.append("castillo: no aparece el guardián invocado")
        return
    # 80 %: aún fase 1, sin refuerzos; empieza el combate (barra)
    p.strike(g, 20)
    p.check(not ctx.test(f"execute if entity @e[tag=prueba_castillo,tag=heraldia_fase.2]"), "castillo: fase 2 al 80 %")
    p.tally(REF, 0, "castillo: refuerzos al 80 %")
    p.check(p.log(r"jefes: barra de castillo/\w+ para 1 jugadores"), "castillo: sin barra para el jugador al primer golpe")
    # 60 %: fase 2, efectos y sus refuerzos
    p.strike(g, 20)
    p.check(p.log(rf"jefes: castillo/\w+ pasa a la fase 2 \({len(lst)} refuerzos\)"), "castillo: no pasa a la fase 2")
    p.check(ctx.test("execute if entity @e[tag=prueba_castillo,tag=heraldia_fase.2]"), "castillo: sin la etiqueta de la fase 2")
    # (el nivel I, amplifier 0, no se guarda: es el valor por defecto del códec)
    for ef in ("speed", "resistance", "strength"):
        p.check(ctx.test(f'execute if entity @e[tag=prueba_castillo,nbt={{active_effects:[{{id:"minecraft:{ef}"}}]}}]'),
                f"castillo: fase 2 sin {ef}")
    p.tally(REF, len(lst), "castillo: refuerzos de la fase 2")
    for t in ("heraldia_anclado", "heraldia_adulto"):
        p.tally(f"@e[tag=heraldia_refuerzo,tag={t}]", len(lst), f"castillo: refuerzos con {t}")
    p.tally("@e[tag=heraldia_refuerzo,tag=heraldia_guardian]", 0, "castillo: refuerzos con la etiqueta de guardián")
    p.tally("@e[tag=heraldia_refuerzo,nbt={DeathLootTable:\"heraldia:guardianes/castillo/minecraft:zombie\"}]", 0,
             "castillo: refuerzos con la tabla del guardián")
    p.tally("@e[tag=heraldia_refuerzo,type=minecraft:zombie,nbt={IsBaby:1b}]", 0, "castillo: refuerzos bebés")
    for mob in sorted({r["mob"] for r in lst}):
        n = sum(r["mob"] == mob for r in lst)
        p.tally(f"@e[tag=heraldia_refuerzo,type={mob}]", n, f"castillo: refuerzos {mob}")
        hand = next((r.get("equipo", {}).get("mainhand") for r in lst if r["mob"] == mob and r.get("equipo")), None)
        if hand:
            p.tally(f'@e[tag=heraldia_refuerzo,type={mob},nbt={{equipment:{{mainhand:{{id:"{hand}"}}}}}}]',
                     sum(r["mob"] == mob and r.get("equipo", {}).get("mainhand") == hand for r in lst),
                     f"castillo: refuerzos {mob} con {hand}")
    # 50 %: sigue en la fase 2, no se repite
    p.strike(g, 10)
    p.tally(REF, len(lst), "castillo: otro golpe en la fase 2 llama más refuerzos")
    # 25 %: fase 3, con el tope de vivos
    p.strike(g, 25)
    third = min(len(lst), 4 - len(lst))
    p.check(p.log(rf"jefes: castillo/\w+ pasa a la fase 3 \({third} refuerzos\)"), "castillo: no pasa a la fase 3")
    p.check(ctx.test('execute if entity @e[tag=prueba_castillo,nbt={active_effects:[{id:"minecraft:speed",amplifier:1b}]}]'),
            "castillo: fase 3 sin velocidad II")
    p.tally(REF, len(lst) + third, "castillo: refuerzos vivos tras la fase 3 (tope 4)")
    # sin refuerzos vivos, otro golpe (20 %) no llama a nadie: cada fase una vez
    ctx.run(f"kill {REF}", r"Killed|No entity was found")
    p.strike(g, 5)
    p.tally(REF, 0, "castillo: un golpe en la fase 3 vuelve a llamar refuerzos")
    p.check(p.times(r"jefes: castillo/\w+ pasa a la fase") == 2, "castillo: más de un cambio por fase en el log")
    # la barra se quita al irse el jugador y vuelve con el siguiente golpe
    ctx.run(f"tp {PLAYER} {X} {Y} {Z - 70}", r"Teleported")
    p.check(p.log(r"jefes: barra de castillo/\w+ quitada \(sin jugadores cerca\)"), "castillo: la barra no se quita al alejarse")
    ctx.run(f"tp {PLAYER} {X} {Y} {Z}", r"Teleported")
    p.strike(g, 1)
    p.check(p.times(r"jefes: barra de castillo/\w+ para 1 jugadores") >= 2, "castillo: la barra no vuelve al volver el jugador")
    p.strike(g, 1000)
    p.check(p.log(r"jefes: barra de castillo/\w+ quitada \(muerto\)"), "castillo: la barra no se quita al morir")
    ctx.run(f"kill {REF}", r"Killed|No entity was found")


def stray_without_id(p, dataset):
    ctx = p.ctx
    fam = dataset["familias"][dataset["mob_familia"]["minecraft:stray"]]
    g = "@e[tag=prueba_stray,limit=1]"
    ctx.run(guardian("stray", "prueba_stray", []), r"Summoned")
    if not ctx.wait_entity(g):
        p.fails.append("stray: no aparece el guardián invocado")
        return
    # sin nadie a menos de 48 bloques (daño del sol, de lava...): no pasa de fase ni muestra la barra
    ctx.run(f"tp {PLAYER} {X} {Y} {Z - 70}", r"Teleported")
    p.strike(g, 50)
    p.check(not ctx.test("execute if entity @e[tag=prueba_stray,tag=heraldia_fase.2]"), "stray: pasa de fase sin jugadores cerca")
    p.tally(REF, 0, "stray: refuerzos sin jugadores cerca")
    ctx.run(f"tp {PLAYER} {X} {Y} {Z}", r"Teleported")
    p.strike(g, 1)
    p.check(p.log(rf"jefes: stray/\w+ pasa a la fase 2 \({len(fam)} refuerzos\)"), "stray sin id: no pasa a la fase 2")
    p.check(p.times(r"jefes: barra de stray/") == 1, "stray: barra sin jugadores cerca")
    for mob in {r["mob"] for r in fam}:
        p.tally(f"@e[tag=heraldia_refuerzo,type={mob}]", sum(r["mob"] == mob for r in fam), f"stray sin id: refuerzos {mob}")
    ctx.run(f"kill {g}", r"Killed|No entity was found")
    ctx.run(f"kill {REF}", r"Killed|No entity was found")


def hit_lighthouse(p, dataset):
    ctx = p.ctx
    lst = dataset["unicas"]["faro"]
    g = "@e[tag=prueba_faro,limit=1]"
    ctx.run(guardian("drowned", "heraldia_guardian.faro", ["prueba_faro"]), r"Summoned")
    if not ctx.wait_entity(g):
        p.fails.append("faro: no aparece el guardián invocado")
        return
    p.strike(g, 90)
    second, third = min(len(lst), 4), min(len(lst), 4 - min(len(lst), 4))
    p.check(p.log(rf"jefes: faro/\w+ pasa a la fase 3 \({second + third} refuerzos\)"), "faro: un golpe grande no da las dos fases")
    p.check(ctx.test("execute if entity @e[tag=prueba_faro,tag=heraldia_fase.2,tag=heraldia_fase.3]"), "faro: sin las dos etiquetas")
    p.tally(REF, second + third, "faro: refuerzos de las dos fases")
    p.tally("@e[tag=heraldia_refuerzo,type=minecraft:drowned,nbt={IsBaby:1b}]", 0, "faro: ahogados bebés")
    ctx.run(f"kill {g}", r"Killed|No entity was found")
    ctx.run(f"kill {REF}", r"Killed|No entity was found")


def disabled(p):
    ctx = p.ctx
    g = "@e[tag=prueba_off,limit=1]"
    ctx.run(guardian("zombie", "heraldia_guardian.castillo", ["prueba_off"]), r"Summoned")
    if not ctx.wait_entity(g):
        p.fails.append("desactivado: no aparece el guardián invocado")
        return
    p.strike(g, 50)
    p.strike(g, 30)
    p.check(not ctx.test("execute if entity @e[tag=prueba_off,tag=heraldia_fase.2]"), "desactivado: pasa de fase")
    p.tally(REF, 0, "desactivado: llama refuerzos")
    p.check(not ctx.test('execute if entity @e[tag=prueba_off,nbt={active_effects:[{id:"minecraft:speed"}]}]'), "desactivado: efectos")
    ctx.ticks(40)
    p.check(not re.search(r"jefes: (barra|castillo)", ctx.log()), "desactivado: barra o fases en el log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-jefes"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    dataset = reinforcements(a.jar)
    fails = []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    texts = []
    proc, ctx = start_up(a.work, launcher, 18000)
    try:
        p = Test(ctx, fails)
        castle(p, dataset)
        stray_without_id(p, dataset)
        hit_lighthouse(p, dataset)
    finally:
        halt(proc)
        texts.append(ctx.log())
    # Segundo arranque, con las tres opciones desactivadas
    cfg = os.path.join(a.work, "config", "heraldia.json")
    with open(cfg, encoding="utf-8") as f:
        conf = json.load(f)
    conf["jefes"] = {"fases": {"activado": False}, "refuerzos": {"activado": False}, "barra": {"activado": False}}
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump(conf, f)
    proc, ctx = start_up(a.work, launcher, 18100)
    try:
        disabled(Test(ctx, fails))
    finally:
        halt(proc)
        texts.append(ctx.log())
    for bad in ("Registry loading errors", "Failed to load datapacks", "jefes: refuerzo", "jefes: objeto"):
        if any(bad in t for t in texts):
            fails.append(f"el log contiene {bad!r}")
    print("JEFES:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
