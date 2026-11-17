"""Perfiles de juego (opción «perfil», T36) en un servidor dedicado 26.3 real, reiniciando el mismo mundo.

Uso: python3 tools/smoke/perfiles.py --jar build/libs/heraldia-X.jar [--work build/smoke-perfiles]
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
from guia import Server

X, Y, Z = 0, 100, 0
NUM = r"(-?\d+(?:\.\d+)?)"
# Líneas de /heraldia info que dependen de la generación (en inglés: la consola usa en_us).
GENERACION = ("Villages:", "Unique structures", "Minimum distance", "Medium structures", "Mine entrances", "Registered structures")
CASOS = [   # (nombre, configuración extra, vida máxima esperada, efectivo, opciones que difieren)
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


def leer(work):
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

    def respuesta(ctx, cmd, fin):
        """Las líneas que escribe una orden de varias líneas (hasta la que casa con `fin`)."""
        s.pending(ctx.lines, ctx.seen)
        n0 = len(ctx.seen)
        ctx.run(cmd, fin)
        ctx.run("seed", r"Seed: \[")          # lo que quede de la respuesta llega antes que esta
        return "".join(ctx.seen[n0:])

    try:
        for i, (nombre, extra, vida, efectivo, difieren) in enumerate(CASOS):
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
                raise SystemExit(f"{nombre}: no aparece el zombi de prueba")
            got = num(ctx, "attribute @e[tag=p_anclado,limit=1] minecraft:max_health get")
            check(got is not None and abs(got - vida) < 1e-3, f"{nombre}: vida máxima {got} (debe ser {vida})")
            log = ctx.log()
            elegido = extra["perfil"]
            if difieren:
                check(re.search(rf"perfil {elegido} con opciones fijadas a mano en el fichero, que mandan sobre el perfil: "
                                rf"{re.escape(difieren[0])}=.*el perfil queda como personalizado", log),
                      f"{nombre}: el log no dice que el perfil queda como personalizado")
            else:
                check(re.search(rf"Heraldia: perfil {elegido}\r?\n", log), f"{nombre}: el log no dice el perfil")
            texto = respuesta(ctx, "heraldia profile", r"No option set by hand|the profile becomes custom|Unknown|Incorrect")
            check(f"Gameplay profile: {efectivo} (in the file:" in texto, f"{nombre}: /heraldia profile no dice {efectivo}: {texto[-300:]!r}")
            for k in difieren:
                check(re.search(rf"{re.escape(k)} = \w+ \(set by hand; the profile gives", texto), f"{nombre}: /heraldia profile no marca {k}")
            check(("the profile becomes custom" in texto) == bool(difieren), f"{nombre}: /heraldia profile: final equivocado")
            escrito = leer(a.work)
            check(escrito.get("perfil") == elegido, f"{nombre}: el fichero reescrito cambió el perfil: {escrito.get('perfil')}")
            check(("nivel" in escrito.get("dificultad", {})) == ("dificultad.nivel" in difieren),
                  f"{nombre}: dificultad.nivel {'falta' if difieren else 'sobra'} en el fichero reescrito")
            check("maximo_vivos" not in escrito.get("jefes", {}).get("refuerzos", {}), f"{nombre}: el fichero escribe lo que da el perfil")
            check(escrito.get("_perfil", {}).get("efectivo") == ("personalizado" if difieren else elegido), f"{nombre}: _perfil.efectivo")
            info = respuesta(ctx, "heraldia info", r"Mine entrances|Entradas a mina|Unknown|Incorrect")
            lineas = sorted(l.split("]: ", 1)[-1].strip() for l in info.splitlines() if any(g in l for g in GENERACION))
            if info_gen is None:
                info_gen = lineas
                check(len(lineas) >= 4, f"{nombre}: /heraldia info sin líneas de la generación: {lineas}")
            else:
                check(lineas == info_gen, f"{nombre}: /heraldia info de la generación cambió con el perfil: {lineas} != {info_gen}")
            if nombre == "casual":
                check(escrito.get("_perfil", {}).get("valores", {}).get("botin.reponer.activado") is True,
                      f"{nombre}: el botín que se repone no queda activado")
            print(f"{nombre}: vida {got}, perfil efectivo {efectivo}, difieren {difieren}")
    finally:
        if srv:
            srv.stop()
    print("PERFILES:", "OK" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
