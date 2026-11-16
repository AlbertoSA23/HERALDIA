"""Qué pruebas ejecutar según los ficheros cambiados (el mismo mapa en local y en la CI).

Política de pruebas (docs/DESARROLLO.md): cada sesión prueba solo su trabajo (tests unitarios + las pruebas de servidor de
lo que toca, que este script elige por rutas) y una sesión auditora ejecuta la batería completa.

Uso:
  python3 tools/test.py --afectados           # tests unitarios + pruebas de servidor de lo cambiado frente a origin/develop
  python3 tools/test.py --afectados --base REF --jar build/libs/heraldia-X.jar
  python3 tools/test.py --todo --jar ...      # batería completa (sesión auditora): unitarios, humo y todas las de servidor
  python3 tools/test.py --listar [--todo]     # solo dice qué pruebas de servidor tocan (no ejecuta nada)
  python3 tools/test.py --unitarios           # solo los tests unitarios rápidos (pytest del generador)
  python3 tools/test.py --ci-matriz --base SHA [--completa]   # JSON de la matriz de la CI (grupos de pruebas)
  python3 tools/test.py --grupo "a.py b.py" --jar ... --work DIR   # ejecuta un grupo en serie (lo usa la CI)

Las pruebas de servidor se descubren solas: tools/smoke/*.py (salvo server_smoke.py, la de humo, que va siempre, y los
módulos de NO_SON_PRUEBAS) y tools/gen/unicas/*/prueba_*.py. compat_mods.py es una prueba por grupo de mods
(«tools/smoke/compat_mods.py::<grupo>», con --grupo): en un PR solo va si cambia algo de COMPAT_RUTAS. Una prueba nueva entra en la batería completa sin tocar nada; para que la elija también la
selección por rutas, basta con que esté en la carpeta de su única (o, si va en tools/smoke/, en SMOKE_DE_UNICA o en MAPA).
"""
import argparse, fnmatch, glob, json, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUMO = "tools/smoke/server_smoke.py"
TODO = "*"            # en el mapa: el cambio afecta a todo (código común) -> batería completa
NO_SON_PRUEBAS = {"server_smoke.py", "modrinth.py"}     # módulos comunes de tools/smoke/
# Compatibilidad con otros mods (una prueba por grupo, con mods de Modrinth): larga y con descargas, así que en un PR
# solo va si cambia la propia prueba, la lista de mods o el código común de colocación (lo que decide dónde sale cada
# estructura y si choca con las de otros mods). En la batería completa (push a develop, workflow_dispatch, etiqueta) siempre.
COMPAT = "tools/smoke/compat_mods.py"

# Pruebas de tools/smoke/ que son de una única concreta (las de tools/gen/unicas/<id>/ se asocian solas por carpeta).
SMOKE_DE_UNICA = {
    "ciudadela": ["tools/smoke/ciudadela_check.py"],
    "coliseo": ["tools/smoke/coliseo_redstone.py"],
    "galeon": ["tools/smoke/galeon_test.py"],
    "observatorio": ["tools/smoke/observatorio_smoke.py"],
    "palacio": ["tools/smoke/palacio_redstone.py"],
}
# Lo que toda única nueva o cambiada debe pasar además de lo suyo: su trofeo, su pliego de la crónica y sus guardianes adultos.
DE_TODA_UNICA = ["tools/smoke/trofeos.py", "tools/smoke/historia.py", "tools/smoke/guardianes_adultos.py"]
# Paquete Java de cada única con código propio (src/main/java/.../unicas/<paquete>/).
JAVA_UNICA = {"atlantida": "atlantida", "ciudadela": "ciudadela", "faro": "faro", "galeon": "galeon",
              "isla": "isla_corsario", "mina": "mina_perdida"}
ALDEAS = ["tools/smoke/aldeas_terreno.py", "tools/smoke/aldeas_vida.py", "tools/smoke/aldeas_variantes.py"]
JAVA = "src/main/java/io/github/albertosa23/heraldia/"
COMPAT_RUTAS = [COMPAT, "tools/smoke/modrinth.py", "gradle.properties", "tools/gen/biomas.py", "tools/gen/etiquetas_c.json",
                JAVA + "config/GridPlacement.java", JAVA + "config/UniqueSeparation.java", JAVA + "config/VillageRules.java",
                JAVA + "mixin/ChunkGeneratorMixin.java", JAVA + "mixin/StructureCheckMixin.java", JAVA + "comun/ZonaAjenas.java",
                JAVA + "unicas/isla/IslaZona.java", JAVA + "unicas/atlantida/AtlantisAnchor.java"]

# Mapa ruta -> pruebas de servidor. Se recorre en orden y gana la PRIMERA regla que casa (fnmatch: * cruza «/»).
# Una lista vacía: el cambio no necesita pruebas de servidor (más allá de la de humo, que va siempre en la CI).
# Lo que no casa con ninguna regla se trata como común: batería completa (mejor de más que de menos).
MAPA = [
    # sin pruebas de servidor: documentación, tests unitarios, cliente, registro de cambios
    ("docs/*", []), ("*.md", []), ("tools/gen/tests/*", []), ("src/test/*", []), ("src/client/*", []),
    ("tools/changelog.py", []), ("tools/gen/render.py", []), ("tools/gen/LEEME.md", []), (".gitignore", []),
    # aldeas: generador de piezas y su Java
    ("tools/gen/houses.py", ALDEAS), ("tools/gen/streets.py", ALDEAS), ("tools/gen/specials.py", ALDEAS),
    ("tools/gen/fillers.py", ALDEAS), ("tools/gen/themes.py", ALDEAS), ("tools/gen/sim.py", ALDEAS),
    ("tools/gen/tablon.py", ["tools/smoke/aldeas_vida.py"]),
    ("tools/gen/tratos.py", ["tools/smoke/aldeas_vida.py"]), (JAVA + "aldeas/*", ALDEAS),
    ("tools/gen/mapas.py", ["tools/smoke/aldeas_vida.py", "tools/smoke/historia.py"]),
    ("tools/gen/loot.py", []),                 # la de humo lee todas las tablas
    ("tools/gen/logros.py", ["tools/smoke/trofeos.py", "tools/smoke/historia.py", "tools/smoke/aldeas_vida.py"]),
    ("tools/gen/biomas.py", ["tools/smoke/terralith_biomas.py"]),
    ("tools/gen/etiquetas_c.json", ["tools/smoke/terralith_biomas.py"]),
    # los mods de Modrinth fijados: las pruebas que los descargan (las de compatibilidad, por COMPAT_RUTAS)
    ("tools/smoke/modrinth.py", ["tools/smoke/trofeos.py", "tools/smoke/historia.py", "tools/smoke/aldeas_vida.py",
                                 "tools/smoke/terralith_biomas.py"]),
    # mixins de los mobs de plantilla y comandos (la de humo prueba /heraldia info y llave)
    (JAVA + "mixin/Zombie*", ["tools/smoke/guardianes_adultos.py"]),
    (JAVA + "mixin/DrownedMixin.java", ["tools/smoke/guardianes_adultos.py"]),
    (JAVA + "comando/*", []),
    # código común: batería completa
    ("tools/gen/unicas/_comun/*", TODO), ("tools/gen/unicas/__init__.py", TODO), ("tools/gen/writer.py", TODO),
    ("tools/gen/core.py", TODO), ("tools/gen/pack.py", TODO), ("tools/gen/lint.py", TODO), ("tools/gen/validate.py", TODO),
    ("tools/gen/main.py", TODO), ("tools/gen/build.py", TODO), ("tools/gen/opciones.py", TODO), ("tools/gen/requirements.txt", TODO),
    ("tools/smoke/server_smoke.py", TODO), ("tools/test.py", TODO), (".github/*", TODO), ("build.gradle", TODO),
    ("gradle.properties", TODO), ("settings.gradle", TODO), ("gradle/*", TODO), ("gradlew*", TODO),
    ("src/main/resources/*", TODO), (JAVA + "*", TODO),
]


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def grupos_compat():
    """Grupos de compat_mods.py (lo importa sin ejecutar nada)."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "smoke"))
    import compat_mods
    return list(compat_mods.GRUPOS)


def descubrir():
    """Todas las pruebas de servidor (sin la de humo), ordenadas; compat_mods.py, una por grupo."""
    smoke = [rel(p) for p in glob.glob(os.path.join(ROOT, "tools", "smoke", "*.py")) if os.path.basename(p) not in NO_SON_PRUEBAS]
    unicas = [rel(p) for p in glob.glob(os.path.join(ROOT, "tools", "gen", "unicas", "*", "prueba_*.py"))]
    if COMPAT in smoke:
        smoke.remove(COMPAT)
        smoke += [f"{COMPAT}::{g}" for g in grupos_compat()]
    return sorted(smoke + unicas)


def es_compat(prueba):
    return prueba.split("::")[0] == COMPAT


def orden(prueba):
    """Orden para ejecutar una prueba: [script, argumentos...] («ruta::grupo» pasa --grupo grupo)."""
    script, _, grupo = prueba.partition("::")
    return [os.path.join(ROOT, script)] + (["--grupo", grupo] if grupo else [])


def de_unica(sid, todas):
    """Pruebas de servidor de una única: las de su carpeta, las de SMOKE_DE_UNICA y DE_TODA_UNICA."""
    propias = [p for p in todas if p.startswith(f"tools/gen/unicas/{sid}/")]
    return propias + SMOKE_DE_UNICA.get(sid, []) + DE_TODA_UNICA


def para(ruta, todas):
    """Pruebas de servidor que pide un fichero cambiado: lista, o TODO."""
    if ruta in todas:                                           # la propia prueba
        return [ruta]
    if ruta == COMPAT:
        return [p for p in todas if es_compat(p)]
    partes = ruta.split("/")
    if ruta.startswith("tools/gen/unicas/") and len(partes) >= 4 and not partes[3].startswith("_"):
        sid = partes[3][:-3] if len(partes) == 4 and partes[3].endswith(".py") else partes[3]
        if len(partes) > 4 or ruta.endswith(".py"):
            return de_unica(sid, todas)
    if ruta.startswith(JAVA + "unicas/") and len(partes) > 9:      # src/main/java/io/github/albertosa23/heraldia/unicas/<paquete>/...
        pkg = partes[8]
        if pkg in JAVA_UNICA:
            return de_unica(JAVA_UNICA[pkg], todas)
        return TODO
    for patron, pruebas in MAPA:
        if fnmatch.fnmatch(ruta, patron):
            return pruebas
    return TODO


def seleccionar(cambiados, todas=None):
    """(completa, [pruebas]) para una lista de rutas cambiadas (relativas a la raíz, con «/»). Las de compatibilidad
    (COMPAT) solo entran si alguna ruta está en COMPAT_RUTAS, también cuando lo cambiado pide la batería completa."""
    todas = descubrir() if todas is None else todas
    compat = any(fnmatch.fnmatch(r, pat) for r in cambiados for pat in COMPAT_RUTAS)
    elegidas = set()
    for r in cambiados:
        p = para(r, todas)
        if p == TODO:
            return True, [x for x in todas if compat or not es_compat(x)]
        elegidas.update(x for x in p if x in todas)
    if compat:
        elegidas.update(x for x in todas if es_compat(x))
    return False, sorted(elegidas)


def cambiados(base):
    """Ficheros cambiados frente a `base` (merge-base), más los del árbol de trabajo sin confirmar."""
    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    mb = git("merge-base", base, "HEAD")[0].strip()
    out = git("diff", "--name-only", mb) + git("ls-files", "--others", "--exclude-standard")
    return sorted({l.strip() for l in out if l.strip()})


# Duración medida de cada prueba en la CI (s, solo el paso de la prueba; servidor ya en caché). Sirve para repartirlas
# en grupos parecidos; una prueba que no está aquí cuenta como DEFECTO_S.
DURACION_S = {
    "tools/smoke/aldeas_vida.py": 170, "tools/smoke/aldeas_variantes.py": 135, "tools/smoke/aldeas_terreno.py": 105,
    "tools/gen/unicas/isla_corsario/prueba_servidor.py": 100, "tools/gen/unicas/mina_perdida/prueba_servidor.py": 95,
    "tools/smoke/trofeos.py": 90, "tools/smoke/ciudadela_check.py": 80, "tools/smoke/observatorio_smoke.py": 75,
    "tools/smoke/guardianes_adultos.py": 72, "tools/gen/unicas/santuario/prueba_servidor.py": 70,
    "tools/gen/unicas/catedral/prueba_juego.py": 65, "tools/gen/unicas/salon_jarl/prueba_servidor.py": 65,
    "tools/gen/unicas/laboratorio_micelio/prueba_servidor.py": 64, "tools/smoke/historia.py": 62,
    "tools/smoke/palacio_redstone.py": 57, "tools/smoke/terralith_biomas.py": 50,
    "tools/gen/unicas/fortaleza_hielo/prueba_servidor.py": 47, "tools/gen/unicas/monasterio/prueba_servidor.py": 45,
    "tools/gen/unicas/castillo/prueba_redstone.py": 44, "tools/gen/unicas/mansion/prueba_servidor.py": 40,
    "tools/smoke/coliseo_redstone.py": 39, "tools/smoke/rejilla_compatible.py": 80,
    "tools/gen/unicas/torre_mago/prueba_redstone.py": 33,
    "tools/gen/unicas/piramide/prueba_servidor.py": 28, "tools/smoke/galeon_test.py": 26,
    # compatibilidad (medidas en local en 4 núcleos con las descargas en caché, más un 30 % para la CI)
    **{f"{COMPAT}::{g}": s for g, s in {"base": 75, "rendimiento": 75, "biomas": 90, "servidor": 90, "distanthorizons": 90,
                                         "estructuras": 100, "terreno": 110, "tectonic": 140, "wwoo": 170}.items()},
}
DEFECTO_S = 90
# Cada job de la CI paga ~25 s de preparación (máquina, Java, Python, cachés) antes de la prueba: se juntan pruebas cortas
# en un job mientras el grupo no pase de la más larga (así no se alarga la CI y se ocupan menos máquinas). GitHub
# Actions gratis da 20 jobs a la vez: con la de humo y la compilación, la batería completa cabe en una sola tanda.
TOPE_GRUPO_S = 170


def grupos(pruebas, tope=TOPE_GRUPO_S):
    """Reparte las pruebas en grupos (listas) de duración <= max(tope, la más larga): primero las largas, cada una en
    el grupo más corto donde quepa (si no cabe en ninguno, abre otro). Determinista."""
    dur = lambda p: DURACION_S.get(p, DEFECTO_S)
    tope = max([tope] + [dur(p) for p in pruebas])
    out = []
    for p in sorted(pruebas, key=lambda p: (-dur(p), p)):
        cabe = [g for g in out if sum(map(dur, g)) + dur(p) <= tope]
        if cabe:
            min(cabe, key=lambda g: sum(map(dur, g))).append(p)
        else:
            out.append([p])
    return out


def nombre(g):
    """Nombre corto de un grupo para la CI: «isla_corsario + piramide»."""
    def corto(p):
        if "::" in p:
            return "compat " + p.split("::")[1]
        parts = p.split("/")
        return parts[3] if p.startswith("tools/gen/unicas/") else parts[-1][:-3]
    return " + ".join(corto(p) for p in g)


def matriz(completa, pruebas):
    return {"include": [{"nombre": nombre(g), "pruebas": " ".join(g)} for g in grupos(pruebas)]} if pruebas else {"include": []}


def unitarios():
    """Tests unitarios rápidos del generador (pytest). Los JUnit van con ./gradlew test."""
    return subprocess.run([sys.executable, "-m", "pytest", "-q", os.path.join(ROOT, "tools", "gen", "tests")],
                          cwd=ROOT).returncode


def ejecutar(pruebas, jar, work, logs=None):
    """Ejecuta las pruebas de servidor en serie (todas, aunque falle una) y devuelve las que fallan. Copia el
    logs/latest.log de cada una a `logs` (si se da) para subirlo como artefacto."""
    malas = []
    for p in pruebas:
        t0 = time.monotonic()
        print(f"::group::{p}" if os.environ.get("GITHUB_ACTIONS") else f"== {p}", flush=True)
        r = subprocess.run([sys.executable, *orden(p), "--jar", jar, "--work", work], cwd=ROOT).returncode
        if os.environ.get("GITHUB_ACTIONS"):
            print("::endgroup::")
        print(f"{'OK' if r == 0 else 'FALLA'} {p} ({time.monotonic() - t0:.0f} s)", flush=True)
        if logs:
            os.makedirs(logs, exist_ok=True)
            src = os.path.join(work, "logs", "latest.log")
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(logs, p.replace("::", "-").replace("/", "-").replace(".py", "") + ".log"))
        if r:
            malas.append(p)
    return malas


def jar_por_defecto():
    props = dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, "gradle.properties"), encoding="utf-8")
                 if "=" in l and not l.lstrip().startswith("#"))
    return os.path.join(ROOT, "build", "libs", f"heraldia-{props['mod_version']}.jar")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--afectados", action="store_true", help="unitarios + pruebas de servidor de lo cambiado")
    modo.add_argument("--todo", action="store_true", help="batería completa (sesión auditora)")
    modo.add_argument("--listar", action="store_true", help="solo lista las pruebas de servidor elegidas")
    modo.add_argument("--unitarios", action="store_true", help="solo los tests unitarios del generador")
    modo.add_argument("--ci-matriz", action="store_true", help="matriz JSON para la CI")
    modo.add_argument("--grupo", help="ejecuta en serie estas pruebas (separadas por espacios)")
    ap.add_argument("--base", default="origin/develop", help="referencia con la que comparar (por defecto origin/develop)")
    ap.add_argument("--completa", action="store_true", help="con --ci-matriz/--listar: batería completa")
    ap.add_argument("--jar", help="el .jar del mod (por defecto el de la versión de gradle.properties)")
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke"), help="carpeta del servidor de prueba")
    ap.add_argument("--logs", help="carpeta donde copiar el log de cada prueba")
    ap.add_argument("--sin-unitarios", action="store_true", help="con --afectados/--todo: no pasa los unitarios")
    a = ap.parse_args(argv)
    work = os.path.abspath(a.work)       # los scripts arrancan Java con cwd=--work: ruta absoluta
    jar = os.path.abspath(a.jar or jar_por_defecto())

    if a.unitarios:
        return unitarios()
    if a.grupo is not None:
        malas = ejecutar(a.grupo.split(), jar, work, a.logs)
        print("Fallan:" if malas else "Todas pasan.", " ".join(malas))
        return 1 if malas else 0

    if a.todo or a.completa:
        completa, pruebas, cambios = True, descubrir(), []
    else:
        cambios = cambiados(a.base)
        completa, pruebas = seleccionar(cambios)
    if a.ci_matriz:
        print(json.dumps(dict(matriz(completa, pruebas), completa=completa), ensure_ascii=False))
        return 0
    if a.listar or a.afectados:
        print(f"{len(cambios)} ficheros cambiados frente a {a.base}" if cambios else "batería completa", file=sys.stderr)
        print(("Batería completa: " if completa else "Pruebas de servidor afectadas: ") + (", ".join(pruebas) or "ninguna"),
              file=sys.stderr)
        if a.listar:
            print("\n".join(pruebas))
            return 0
    if not a.sin_unitarios and unitarios():
        return 1
    if not os.path.isfile(jar):
        print(f"No está el .jar {jar}: compila antes con ./gradlew build (o pasa --jar).", file=sys.stderr)
        return 1
    malas = ejecutar(([HUMO] if a.todo else []) + pruebas, jar, work, a.logs)
    print("Fallan:" if malas else "Todas pasan.", " ".join(malas))
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
