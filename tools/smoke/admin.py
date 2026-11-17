"""Herramientas de administración en un servidor dedicado 26.3 real con un jugador simulado (Carpet):
/heraldia revisar, /heraldia estado y /heraldia recargar.

Uso: python3 tools/smoke/admin.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
  - revisar lista: todas las paradas, en orden (aldeas por familia sin la desactivada, únicas con la Atlántida,
    medianas, minas pequeña-mediana-grande, la arena y el camino);
  - revisar ir arena: sin arena colocada lo dice y no mueve al jugador;
  - revisar ir unica/atlantida: prevista (sin generar), avisa de que ir genera terreno y no mueve al jugador; la
    búsqueda va fuera del hilo del servidor (se mide);
  - revisar ir <mediana> (y «generar» si está prevista): teletransporte a un sitio seguro (pies y cabeza libres, suelo
    debajo) que coincide con lo que dice el log;
  - revisar marcar problema <nota>, siguiente, saltar: el progreso se guarda (heraldia_revision.json y .md en la
    carpeta del mundo) y sobrevive a un reinicio;
  - estado (y su página 2): versión, descubiertas por tipo, reposición del botín, Lootr y, como operador, los mods;
  - recargar: cambiando dificultad.nivel de heroica a fácil, el zombi anclado ya cargado pasa de 40 a 15 de vida
    máxima sin reiniciar; aldeas.separacion_bloques se lista como pendiente y /heraldia info sigue con el valor en uso.
"""
import argparse, copy, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guia import Server
from trofeos import CARPET
from modrinth import fetch

JUGADOR = "Revisor"
X, Y, Z = 0, 120, 0                       # el zombi de la prueba de la recarga (NoAI: no cae)
NUM = r"(-?\d+(?:\.\d+)?)"
TITULO = r"(?:Review|Revisión) (\d+)/(\d+): "
LOG_BUSQUEDA = r"Heraldia: /heraldia revisar ([a-z_/]+): (.+) en (\d+) ms"
LOG_TP = rf"Heraldia: /heraldia revisar: {JUGADOR} a (-?\d+) (-?\d+) (-?\d+)"
NOTA = "la puerta del patio no abre"


def config(work, **dificultad):
    cfg = copy.deepcopy(s.TEST_CONFIG)
    cfg["dificultad"] = {"nivel": "heroica", **dificultad}
    return cfg


def escribir(work, cfg):
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-admin"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    escribir(a.work, config(a.work))
    mundo = os.path.join(a.work, "world")
    fails, ok = [], 0
    srv = None

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)
            print("FALLA:", msg)

    def como(cmd):
        return f"execute as {JUGADOR} run heraldia revisar {cmd}"

    def busqueda(ctx, parada):
        """Espera a que termine la búsqueda (fuera del hilo del servidor) de una parada: (resultado, ms)."""
        while True:
            m = s.wait_for(ctx.lines, LOG_BUSQUEDA, s.COMMAND_TIMEOUT_S, ctx.seen)
            if m.group(1) == parada:
                return m.group(2), int(m.group(3))

    def pos(ctx):
        return ctx.pos(f"@a[name={JUGADOR}]")

    def num(ctx, cmd):
        m = ctx.run(cmd, rf"(?:is|data:) {NUM}f?\b|No entity|[Nn]o modifier|has no|There is no|not found|Can't find")
        return float(m.group(1)) if m.lastindex and m.group(1) else None

    def jugador(ctx):
        ctx.run(f"player {JUGADOR} spawn at 0 100 0", r"joined the game|Player .* spawn|Unknown|Incorrect")
        if not ctx.until(f"execute if entity @a[name={JUGADOR}]"):
            raise SystemExit(f"no aparece el jugador simulado {JUGADOR} (Carpet)")

    def llega(ctx, parada, idx):
        """Tras ir a una parada con destino: el log del teletransporte, el título y un sitio seguro (pies y cabeza
        libres, suelo debajo, nunca lava) en el que está de verdad el jugador."""
        m = s.wait_for(ctx.lines, LOG_TP + "|" + r"no safe spot|ningún sitio seguro", s.COMMAND_TIMEOUT_S, ctx.seen)
        check(m.lastindex, f"{parada}: no hay sitio seguro: {m.string.strip()}")
        if not m.lastindex:
            return
        x, y, z = (int(v) for v in m.groups()[:3])
        texto = "".join(s.drain(ctx))
        t = re.search(TITULO, texto)
        check(t and int(t.group(1)) == idx + 1, f"{parada}: título {t and t.group(0)} (debe ser la parada {idx + 1})")
        p = pos(ctx)
        check(p and abs(p[0] - (x + 0.5)) < 0.01 and abs(p[1] - y) < 0.01 and abs(p[2] - (z + 0.5)) < 0.01,
              f"{parada}: el jugador está en {p}, el log dice {x} {y} {z}")
        check(ctx.block((x, y, z), "#minecraft:replaceable") and ctx.block((x, y + 1, z), "#minecraft:replaceable"),
              f"{parada}: pies o cabeza dentro de un bloque en {x} {y} {z}")
        check(ctx.test(f"execute unless block {x} {y - 1} {z} #minecraft:air"), f"{parada}: sin suelo bajo {x} {y} {z}")
        check(ctx.test(f"execute unless block {x} {y - 1} {z} minecraft:lava"), f"{parada}: encima de lava")
        print(f"{parada}: en {x} {y} {z}")

    try:
        srv = Server(a.work, launcher)
        ctx = srv.ctx
        jugador(ctx)

        # --- lista: paradas en orden ---
        m = ctx.run(como("lista"), r"(?:Review route|Ruta de revisión) \((\d+)")
        total = int(m.group(1)) if m.lastindex else 0
        lineas = "".join(s.drain(ctx))
        ids = re.findall(r"\d+\. .+? \(([a-z_]+(?:/[a-z_]+)?)\): ", lineas)
        print(f"revisar lista: {total} paradas: {ids}")
        check(total > 20 and len(ids) == total, f"lista: {total} paradas, {len(ids)} leídas")
        tipos = [i.split("/")[0] for i in ids]
        orden = ["aldea", "unica", "mediana", "mina", "arena", "camino"]
        check(tipos == sorted(tipos, key=orden.index), f"lista: tipos fuera de orden: {tipos}")
        check(set(tipos) == set(orden), f"lista: faltan tipos: {set(orden) - set(tipos)}")
        check("aldea/pantano" not in ids, "lista: sale la familia pantano, desactivada en la configuración de prueba")
        check("unica/atlantida" in ids and "unica/isla_corsario" in ids, "lista: faltan la Atlántida o la isla")
        check([i for i in ids if i.startswith("mina/")] == ["mina/pequena", "mina/mediana", "mina/grande"], "lista: minas fuera de orden")

        # --- la arena, sin colocar ---
        antes = pos(ctx)
        m = ctx.run(como("ir arena"), r"has not been placed|no está colocada")
        check(m.lastindex is None and m.group(0) in ("has not been placed", "no está colocada"), f"ir arena: {m.string.strip()}")

        # --- la Atlántida: prevista, se avisa y no se mueve ---
        ctx.run(como("ir unica/atlantida"), r"(?:Looking for|Buscando) ")
        res, ms = busqueda(ctx, "unica/atlantida")
        print(f"revisar ir unica/atlantida: {res} en {ms} ms (fuera del hilo del servidor)")
        texto = "".join(s.drain(ctx))
        check("generada=false" in res, f"atlántida: debería estar prevista: {res}")
        check(re.search(r"has not been generated yet|aún no se ha generado", texto), "atlántida: no avisa de que se generaría terreno")
        check(re.search(r"Go and generate|Ir y generar", texto), "atlántida: falta el botón «Ir y generar»")
        check(re.search(r"(?:What to check|Qué mirar):", texto) and re.search(r"water breathing|respiración acuática", texto),
              "atlántida: falta la lista de qué mirar (con su punto propio)")
        despues = pos(ctx)
        check(antes and despues and abs(antes[0] - despues[0]) < 1 and abs(antes[2] - despues[2]) < 1,
              f"atlántida prevista: el jugador se ha movido de {antes} a {despues}")

        # --- una mediana: teletransporte seguro ---
        mediana = next(i for i in ids if i.startswith("mediana/"))
        idx = ids.index(mediana)
        ctx.run(como(f"ir {mediana}"), r"(?:Looking for|Buscando) ")
        res, ms = busqueda(ctx, mediana)
        print(f"revisar ir {mediana}: {res} en {ms} ms")
        check("Destino" in res, f"{mediana}: no se encuentra ninguna: {res}")
        if "generada=false" in res:
            s.drain(ctx)
            ctx.run(como(f"ir {mediana} generar"), r"(?:Looking for|Buscando) ")
            busqueda(ctx, mediana)
        llega(ctx, mediana, idx)

        # --- marcar, siguiente y saltar ---
        m = ctx.run(como(f"marcar problema {NOTA}"), r"with a problem|con problema")
        check(m.lastindex is None and NOTA in m.string, f"marcar: {m.string.strip()}")
        for orden_, esperado in (("siguiente", idx + 2), ("saltar", idx + 3)):
            ctx.run(como(orden_), r"(?:Looking for|Buscando) ")
            busqueda(ctx, ids[esperado - 1])
            texto = "".join(s.drain(ctx, 3))
            if re.search(r"(?:Loading the area|Cargando la zona)", texto) and not re.search(LOG_TP, texto):
                s.wait_for(ctx.lines, LOG_TP, s.COMMAND_TIMEOUT_S, ctx.seen)
                texto += "".join(s.drain(ctx))
            t = re.search(TITULO, texto)
            check(t and int(t.group(1)) == esperado, f"{orden_}: debería ir a la parada {esperado}: {t and t.group(0)}")

        def resumen(ctx, cuando):
            m = ctx.run("heraldia revisar estado", rf"(?:Review by|Revisión de) {JUGADOR}: (\d+) \D+ (\d+) \D+, (\d+) \D+, (\d+) \D+, (\d+)")
            check(m.lastindex and (int(m.group(3)), int(m.group(4))) == (1, 1) and int(m.group(2)) == total,
                  f"{cuando}: resumen {m.group(0) if m else None} (debe tener 1 con problema y 1 saltada de {total})")
            texto = "".join(s.drain(ctx))
            check(NOTA in texto, f"{cuando}: el resumen no lista el problema")

        resumen(ctx, "revisar estado")
        md, js = os.path.join(mundo, "heraldia_revision.md"), os.path.join(mundo, "heraldia_revision.json")
        fin = time.monotonic() + 30
        while time.monotonic() < fin and not (os.path.exists(md) and NOTA in open(md, encoding="utf-8").read()):
            time.sleep(0.5)
        check(os.path.exists(md) and NOTA in open(md, encoding="utf-8").read(), "no se escribe heraldia_revision.md con la nota")
        if os.path.exists(md):
            texto = open(md, encoding="utf-8").read()
            check("**problema**" in texto and "saltada" in texto and f"## {JUGADOR}" in texto, "heraldia_revision.md incompleto")
            check(texto.index(f"`{mediana}`") < texto.index(f"`{ids[0]}`"), "heraldia_revision.md: el problema no va primero")
        if os.path.exists(js):
            d = json.load(open(js, encoding="utf-8"))
            prog = next(iter(d["jugadores"].values()), {})
            check(prog.get("paradas", {}).get(mediana, {}).get("marca") == "problema", f"json: {prog}")
            check(prog.get("actual") == idx + 2, f"json: parada actual {prog.get('actual')} (debe ser {idx + 2})")

        # --- una prevista con «Ir y generar»: se genera el terreno y se llega a un sitio seguro ---
        prevista = None
        for i in ids[idx + 1:]:
            if not i.startswith("mediana/"):
                break
            ctx.run(como(f"ir {i}"), r"(?:Looking for|Buscando) ")
            res, _ = busqueda(ctx, i)
            if "generada=false" in res:
                s.drain(ctx)
                prevista = i
                break
            if "generada=true" in res:      # ya generada: espera al teletransporte (si no, la siguiente orden está «ocupada»)
                s.wait_for(ctx.lines, LOG_TP + "|no safe spot|ningún sitio seguro", s.COMMAND_TIMEOUT_S, ctx.seen)
            s.drain(ctx)
        check(prevista, "no hay ninguna mediana prevista para probar «Ir y generar»")
        if prevista:
            ctx.run(como(f"ir {prevista} generar"), r"(?:Looking for|Buscando) ")
            res, ms = busqueda(ctx, prevista)
            print(f"revisar ir {prevista} generar: {res} en {ms} ms")
            llega(ctx, prevista, ids.index(prevista))

        # --- /heraldia estado ---
        m = ctx.run("heraldia estado", r"Heraldia (\S+): (?:server status|estado del servidor) \((?:page|página) 1 (?:of|de) (\d+)\)")
        paginas = int(m.group(2)) if m.lastindex else 0
        texto = "".join(s.drain(ctx))
        check(paginas >= 2, f"estado: {m.string.strip()}")
        check(re.search(r"Discovered by some player|Descubiertas por algún jugador", texto), "estado: falta lo descubierto")
        check(re.search(r"(?:Unique structures|Estructuras únicas): 0 (?:of|de) \d+", texto), "estado: falta el recuento de únicas")
        check(re.search(r"(?:Difficulty|Dificultad): ", texto), "estado (operador): falta la dificultad")
        for n in range(2, paginas + 1):
            m = ctx.run(f"heraldia estado {n}", rf"\((?:page|página) {n} (?:of|de) {paginas}\)")
            check(m.lastindex is None and f"{n} " in m.group(0), f"estado {n}: {m.string.strip()}")
            texto += "".join(s.drain(ctx))
        m = ctx.run("heraldia estado 99", rf"\((?:page|página) {paginas} (?:of|de) {paginas}\)")
        check(m.lastindex is None and str(paginas) in m.group(0), f"estado 99: debería dar la última página: {m.string.strip()}")
        s.drain(ctx)
        check(re.search(r"(?:Guardians defeated|Guardianes vencidos): 0 (?:of|de) \d+", texto), "estado: faltan los guardianes")
        check(re.search(r"(?:Restocking loot|Botín que se repone): (?:disabled|desactivado)", texto), "estado: falta la reposición")
        check(re.search(r"(?:Other mods|Otros mods) \(\d+\): .*Carpet", texto), "estado (operador): no lista Carpet entre los mods")

        # --- /heraldia recargar: dificultad sin reiniciar ---
        ctx.run(f"forceload add {X - 16} {Z - 16} {X + 16} {Z + 16}", r"Marked|force|already|[Aa]dded")
        for rule in ("spawn_mobs", "advance_time"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
        ctx.run("time set midnight", r"[Tt]ime|[Ss]et")
        ctx.run(f'summon minecraft:zombie {X} {Y} {Z} {{NoAI:1b,PersistenceRequired:1b,Silent:1b,Tags:["heraldia_anclado",'
                f'"heraldia_adulto","p_recarga"],Health:20f,attributes:[{{id:"minecraft:max_health",base:20}}]}}', r"Summoned|Unable")
        zombi = "@e[tag=p_recarga,limit=1]"
        check(ctx.until(f"execute if entity {zombi}"), "no aparece el zombi de la recarga")
        vm = num(ctx, f"attribute {zombi} minecraft:max_health get")
        check(vm is not None and abs(vm - 40) < 1e-3, f"heroica: vida máxima {vm} (debe ser 40)")
        cfg = config(a.work)
        cfg["dificultad"]["nivel"] = "facil"
        cfg["aldeas"]["separacion_bloques"] = 3000
        escribir(a.work, cfg)
        m = ctx.run("heraldia recargar", r"(?:Configuration reloaded from|Configuración recargada de) heraldia\.json")
        texto = "".join(s.drain(ctx))
        check(m.lastindex is None and "heraldia.json" in m.group(0), f"recargar: {m.string.strip()}")
        check("dificultad.nivel = facil" in texto, "recargar: no lista dificultad.nivel como aplicada")
        check(re.search(r"aldeas\.separacion_bloques: 1500 \S+ \S+, 3000", texto), "recargar: no lista aldeas.separacion_bloques como pendiente")
        n = re.search(r"(?:recalculated for|recalculada en) (\d+)", texto)
        check(n and int(n.group(1)) >= 1, f"recargar: mobs recalculados {n and n.group(1)}")
        vm = num(ctx, f"attribute {zombi} minecraft:max_health get")
        check(vm is not None and abs(vm - 15) < 1e-3, f"fácil sin reiniciar: vida máxima {vm} (debe ser 15)")
        mod = num(ctx, f"attribute {zombi} minecraft:max_health modifier value get heraldia:dificultad_vida")
        check(mod == -0.25, f"fácil sin reiniciar: modificador {mod} (debe ser -0,25)")
        m = ctx.run("heraldia info", r"(?:Villages: every|Aldeas: cada) (\d+)")
        check(m.lastindex and m.group(1) == "1500", f"recargar aplicó la separación de las aldeas: {m.group(0)}")
        s.drain(ctx)
        m = ctx.run("heraldia recargar", r"(?:No option that can be applied live|No ha cambiado ninguna opción)")
        check(m.lastindex is None, f"segunda recarga: {m.string.strip()}")
        s.drain(ctx)

        # --- reinicio: el progreso de la revisión se conserva ---
        srv.stop()
        srv = Server(a.work, launcher)
        ctx = srv.ctx
        resumen(ctx, "tras reiniciar")
        log = ctx.log()
        bad = [l.strip() for l in log.splitlines() if "Exception" in l and "heraldia" in l.lower()]
        check(not bad, f"errores en el log: {bad}")
    finally:
        if srv:
            srv.stop()
    print(f"admin: {ok} comprobaciones bien, {len(fails)} mal")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
