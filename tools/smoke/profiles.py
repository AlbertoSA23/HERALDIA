"""Perfiles de juego (opción «perfil», T36) en un servidor dedicado 26.3 real, reiniciando el mismo mundo.

Uso: python3 tools/smoke/profiles.py --jar build/libs/heraldia-X.jar [--work build/smoke-perfiles]
Invoca un zombi anclado (heraldia_anclado, vida base 20, como dificultad.py) y reinicia con cada configuración:
  - perfil hardcore: el zombi a vida 40 (heroica), el log dice el perfil, /heraldia profile (comando nuevo, en inglés)
    lo nombra sin opciones fijadas a mano, y el fichero reescrito no lleva las opciones que da el perfil;
  - perfil hardcore con dificultad.nivel = dificil en el fichero: manda el fichero (vida 30), el log y /heraldia profile
    dicen que el perfil queda como personalizado y qué opción difiere, y el fichero la conserva;
  - perfil casual: vida 15 (fácil) y el botín que se repone activado (el bloque «_perfil» del fichero);
  - perfil estandar: vida 20, como siempre.
En todos, las líneas de /heraldia info de la generación (aldeas, únicas, medianas y minas) son las mismas: el perfil no
toca la generación del mundo. Código 0 si todo pasa.
"""
import argparse, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guide import Server

X, Y, Z = 0, 100, 0
NUM = r"(-?\d+(?:\.\d+)?)"
# Líneas de /heraldia info que dependen de la generación (en inglés: la consola usa en_us).
GENERATION = ("Villages:", "Unique structures", "Minimum distance", "Medium structures", "Mine entrances", "Registered structures")
CASES = [   # (nombre, configuración extra, vida máxima esperada, efectivo, opciones que difieren)
    ("hardcore", {"perfil": "hardcore"}, 40, "Hardcore", []),
    ("hardcore+dificil", {"perfil": "hardcore", "dificultad": {"nivel": "dificil"}}, 30, "Custom", ["dificultad.nivel"]),
    ("casual", {"perfil": "casual"}, 15, "Casual", []),
    ("estandar", {"perfil": "estandar"}, 20, "Standard", []),
]


def config(work, extra):
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    for k, v in extra.items():
        if isinstance(v, dict):
            cfg.setdefault(k, {}).update(v)
        else:
            cfg[k] = v
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def read(work):
    with open(os.path.join(work, "config", "heraldia.json"), encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-perfiles"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    fails, info_gen, srv = [], None, None

    def check(cond, msg):
        if not cond:
            fails.append(msg)
            print("FALLA:", msg)

    def num(ctx, cmd):
        m = ctx.run(cmd, rf"(?:is|data:) {NUM}f?\b|No entity|Unknown|Can't find")
        return float(m.group(1)) if m.lastindex and m.group(1) else None

    def answer(ctx, cmd, finish):
        """Las líneas que escribe una orden de varias líneas (hasta la que casa con `fin`)."""
        s.pending(ctx.lines, ctx.seen)
        n0 = len(ctx.seen)
        ctx.run(cmd, finish)
        ctx.run("seed", r"Seed: \[")          # lo que quede de la respuesta llega antes que esta
        return "".join(ctx.seen[n0:])

    try:
        for i, (name, extra, health, effective, differ) in enumerate(CASES):
            if srv:
                srv.stop()
            config(a.work, extra)
            srv = Server(a.work, launcher)
            ctx = srv.ctx
            if i == 0:
                ctx.run("forceload add 0 0", r"Marked|[Aa]dded|force|already")
                ctx.run(f'summon minecraft:zombie {X} {Y} {Z} {{NoAI:1b,PersistenceRequired:1b,Silent:1b,'
                        f'Tags:["p_anclado","heraldia_anclado","heraldia_adulto"],attributes:[{{id:"minecraft:max_health",base:20}}]}}',
                        r"Summoned|Unable")
            if not ctx.until("execute if entity @e[tag=p_anclado]"):
                raise SystemExit(f"{name}: no aparece el zombi de prueba")
            got = num(ctx, "attribute @e[tag=p_anclado,limit=1] minecraft:max_health get")
            check(got is not None and abs(got - health) < 1e-3, f"{name}: vida máxima {got} (debe ser {health})")
            log = ctx.log()
            chosen = extra["perfil"]
            if differ:
                check(re.search(rf"perfil {chosen} con opciones fijadas a mano en el fichero, que mandan sobre el perfil: "
                                rf"{re.escape(differ[0])}=.*el perfil queda como personalizado", log),
                      f"{name}: el log no dice que el perfil queda como personalizado")
            else:
                check(re.search(rf"Heraldia: perfil {chosen}\r?\n", log), f"{name}: el log no dice el perfil")
            text = answer(ctx, "heraldia profile", r"No option set by hand|the profile becomes custom|Unknown|Incorrect")
            check(f"Gameplay profile: {effective} (in the file:" in text, f"{name}: /heraldia profile no dice {effective}: {text[-300:]!r}")
            for k in differ:
                check(re.search(rf"{re.escape(k)} = \w+ \(set by hand; the profile gives", text), f"{name}: /heraldia profile no marca {k}")
            check(("the profile becomes custom" in text) == bool(differ), f"{name}: /heraldia profile: final equivocado")
            written = read(a.work)
            check(written.get("perfil") == chosen, f"{name}: el fichero reescrito cambió el perfil: {written.get('perfil')}")
            check(("nivel" in written.get("dificultad", {})) == ("dificultad.nivel" in differ),
                  f"{name}: dificultad.nivel {'falta' if differ else 'sobra'} en el fichero reescrito")
            check("maximo_vivos" not in written.get("jefes", {}).get("refuerzos", {}), f"{name}: el fichero escribe lo que da el perfil")
            check(written.get("_perfil", {}).get("efectivo") == ("personalizado" if differ else chosen), f"{name}: _perfil.efectivo")
            info = answer(ctx, "heraldia info", r"Mine entrances|Entradas a mina|Unknown|Incorrect")
            lines = sorted(l.split("]: ", 1)[-1].strip() for l in info.splitlines() if any(g in l for g in GENERATION))
            if info_gen is None:
                info_gen = lines
                check(len(lines) >= 4, f"{name}: /heraldia info sin líneas de la generación: {lines}")
            else:
                check(lines == info_gen, f"{name}: /heraldia info de la generación cambió con el perfil: {lines} != {info_gen}")
            if name == "casual":
                check(written.get("_perfil", {}).get("valores", {}).get("botin.reponer.activado") is True,
                      f"{name}: el botín que se repone no queda activado")
            print(f"{name}: vida {got}, perfil efectivo {effective}, difieren {differ}")
    finally:
        if srv:
            srv.stop()
    print("PERFILES:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
