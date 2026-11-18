"""Qué pruebas ejecutar según los ficheros cambiados (el mismo mapa en local y en la CI).

Política de pruebas (docs/DEVELOPMENT.md): cada sesión prueba solo su trabajo (tests unitarios + las pruebas de servidor de
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
módulos de NO_SON_PRUEBAS) y tools/gen/uniques/*/smoke_*.py. compat_mods.py es una prueba por grupo de mods
(«tools/smoke/compat_mods.py::<grupo>», con --grupo): en un PR solo va si cambia algo de COMPAT_RUTAS. Una prueba nueva entra en la batería completa sin tocar nada; para que la elija también la
selección por rutas, basta con que esté en la carpeta de su única (o, si va en tools/smoke/, en SMOKE_DE_UNICA o en MAPA).
La de coste de generación (tools/smoke/generation_cost.py) no va en los grupos: tiene su job en la CI («coste» en la
salida de --ci-matriz) y en local va al final de --afectados (si lo cambiado toca COSTE_RUTAS) y de --todo (--sin-coste
la quita).
"""
import argparse, fnmatch, glob, json, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMOKE = "tools/smoke/server_smoke.py"
FULL = "*"            # en el mapa: el cambio afecta a todo (código común) -> batería completa
NOT_TESTS = {"server_smoke.py", "modrinth.py", "generation_cost.py"}  # módulos comunes y la de coste (job propio)
# Compatibilidad con otros mods (una prueba por grupo, con mods de Modrinth): larga y con descargas, así que en un PR
# solo va si cambia la propia prueba, la lista de mods o el código común de colocación (lo que decide dónde sale cada
# estructura y si choca con las de otros mods). En la batería completa (push a develop, workflow_dispatch, etiqueta) siempre.
COMPAT = "tools/smoke/compat_mods.py"

# Pruebas de tools/smoke/ que son de una única concreta (las de tools/gen/uniques/<id>/ se asocian solas por carpeta).
SMOKE_OF_UNIQUE = {
    "citadel": ["tools/smoke/citadel_check.py"],
    "colosseum": ["tools/smoke/colosseum_redstone.py"],
    "galleon": ["tools/smoke/galleon_test.py"],
    "ash_citadel": ["tools/smoke/nether_end.py"], "void_sanctum": ["tools/smoke/nether_end.py"],
    "observatory": ["tools/smoke/observatory_smoke.py"],
    "palace": ["tools/smoke/palace_redstone.py"],
}
# Lo que toda única nueva o cambiada debe pasar además de lo suyo: su trofeo, su pliego de la crónica y sus guardianes
# adultos y anclados.
OF_EVERY_UNIQUE = ["tools/smoke/trophies.py", "tools/smoke/story.py", "tools/smoke/adult_guardians.py",
                 "tools/smoke/anchored_guardians.py"]
# Paquete Java de cada única con código propio (src/main/java/.../uniques/<paquete>/).
JAVA_UNIQUE = {"atlantis": "atlantis", "citadel": "citadel", "lighthouse": "lighthouse", "galleon": "galleon",
               "island": "corsair_island", "mine": "lost_mine"}
VILLAGES = ["tools/smoke/village_terrain.py", "tools/smoke/village_life.py", "tools/smoke/village_variants.py"]
JAVA = "src/main/java/io/github/albertosa23/heraldia/"
COMPAT_PATHS = [COMPAT, "tools/smoke/modrinth.py", "gradle.properties", "tools/gen/biomes.py", "tools/gen/c_tags.json",
                JAVA + "config/GridPlacement.java", JAVA + "config/UniqueSeparation.java", JAVA + "config/VillageRules.java",
                JAVA + "mixin/ChunkGeneratorMixin.java", JAVA + "mixin/StructureCheckMixin.java", JAVA + "common/ForeignZone.java",
                JAVA + "uniques/island/IslandZone.java", JAVA + "uniques/atlantis/AtlantisAnchor.java", JAVA + "common/MediumStructures.java"]
# Coste de generación (con y sin Heraldia, comparado con tools/smoke/cost_reference.json): job propio de la CI, en
# paralelo con los grupos de servidor. En la batería completa siempre; en un PR solo si cambia algo de COSTE_RUTAS (el
# Java de la generación, el generador o la propia prueba), salvo lo de COSTE_SIN (tests y documentación).
COST = "tools/smoke/generation_cost.py"
COST_PATHS = [COST, "tools/smoke/cost_reference.json", "tools/gen/*", "gradle.properties",
               JAVA + "villages/*", JAVA + "roads/*", JAVA + "common/*", JAVA + "config/*", JAVA + "mines/*", JAVA + "coast/*",
               JAVA + "uniques/*",
               JAVA + "mixin/ChunkGeneratorMixin.java", JAVA + "mixin/StructureCheckMixin.java"]
COST_WITHOUT = ["tools/gen/tests/*", "*.md", "tools/gen/render.py"]
MEDIUMS = ["tools/smoke/medium_structures.py"]
ADMIN = ["tools/smoke/admin.py"]
UPDATE = ["tools/smoke/update_check.py"]
WEB_MAPS = ["tools/smoke/web_maps.py"]
# Búsqueda del tesoro (T40): su Java (paquete tesoro/) y su generador (tablas, textos, logros).
TREASURE = ["tools/smoke/treasure.py"]
# Arena de oleadas (T31) y sus modos, clasificación semanal y salón de la fama (T41).
ARENA = ["tools/smoke/arena.py", "tools/smoke/arena_modes.py"]
COMMANDS = UPDATE + ADMIN + ["tools/smoke/guide.py"] + ARENA
# Entradas a mina: su generador (tools/gen/mines/) y su Java (paquete minas/); la regla de colocación toca la de las medianas.
MINES = ["tools/smoke/mine_entrances.py"]
# Faros y naufragios de la costa (T42): su generador (tools/gen/shore/) y su Java (paquete costa/); su regla es la de las
# minas (minas/Minas.familia), y el ahogado del semihundido entra en las pruebas que recorren los mobs de las plantillas.
COAST = ["tools/smoke/coast.py"]
COAST_MOBS = COAST + ["tools/smoke/adult_guardians.py", "tools/smoke/anchored_guardians.py"]
# Perfiles de juego (opción «perfil», T36): su prueba de servidor (reinicios con cada perfil y una opción fijada a mano).
PROFILES = ["tools/smoke/profiles.py"]
# Encargos del tablón y reputación por aldea (T38): su Java, el mixin de los precios y sus textos y logros.
QUESTS = ["tools/smoke/quests.py"]
# Caravanas por los caminos (T39): su Java y sus textos y logro.
CARAVANS = ["tools/smoke/caravans.py"]
# Los tipos de medianas traen mobs anclados (y zombis adultos): las pruebas que recorren todos los mobs de las plantillas.
MEDIUMS_MOBS = MEDIUMS + ["tools/smoke/adult_guardians.py", "tools/smoke/anchored_guardians.py"]
# contenido del Nether y el End (T44): medianas y únicas con DIMENSION, su tipo de estructura y su colocación
NETHER_END = ["tools/smoke/nether_end.py"]
# Chozas de mago (T43): el Mago Malvado (Java chozas/) y su botín y textos; su plantilla es una mediana.
HUTS = ["tools/smoke/wizard_huts.py"]
# Actualizaciones seguras (T46): panel en diálogos, idioma por jugador, arreglos por versión y update analyze/apply.
SAFE_UPDATE = ["tools/smoke/update.py"]

# Mapa ruta -> pruebas de servidor. Se recorre en orden y gana la PRIMERA regla que casa (fnmatch: * cruza «/»).
# Una lista vacía: el cambio no necesita pruebas de servidor (más allá de la de humo, que va siempre en la CI).
# Lo que no casa con ninguna regla se trata como común: batería completa (mejor de más que de menos).
MAP = [
    # sin pruebas de servidor: documentación, tests unitarios, cliente, registro de cambios
    ("docs/*", []), ("*.md", []), ("tools/gen/tests/*", []), ("src/test/*", []), ("src/client/*", []),
    ("tools/changelog.py", []), ("tools/gen/render.py", []), ("tools/gen/README.md", []), (".gitignore", []),
    # aldeas: generador de piezas y su Java
    ("tools/gen/houses.py", VILLAGES), ("tools/gen/streets.py", VILLAGES), ("tools/gen/specials.py", VILLAGES),
    ("tools/gen/fillers.py", VILLAGES), ("tools/gen/themes.py", VILLAGES), ("tools/gen/sim.py", VILLAGES),
    ("tools/gen/board.py", ["tools/smoke/village_life.py"]),
    ("tools/gen/trades.py", ["tools/smoke/village_life.py"]), (JAVA + "villages/*", VILLAGES),
    ("tools/gen/maps.py", ["tools/smoke/village_life.py", "tools/smoke/story.py"]),
    ("tools/gen/loot.py", []),                 # la de humo lee todas las tablas
    ("tools/gen/advancements.py", ["tools/smoke/trophies.py", "tools/smoke/story.py", "tools/smoke/village_life.py"]),
    # estructuras medianas: sus tipos (tools/gen/mediums/) y su regla de colocación en Java
    ("tools/gen/dimensions.py", NETHER_END + MEDIUMS), (JAVA + "dimensions/*", NETHER_END),
    ("tools/gen/uniques/_enclosure.py", NETHER_END + OF_EVERY_UNIQUE),
    ("tools/gen/mediums/wizard_hut.py", MEDIUMS_MOBS + HUTS),
    ("tools/gen/mediums/*", MEDIUMS_MOBS + NETHER_END), (JAVA + "common/MediumStructures.java", MEDIUMS + NETHER_END),
    ("tools/gen/mines/*", MINES), (JAVA + "mines/*", MINES + COAST),
    ("tools/gen/shore/*", COAST_MOBS), (JAVA + "coast/*", COAST),
    # /locate de las minas (T36): la caché compartida de alturas y el cálculo adelantado en paralelo solo los usan las minas
    (JAVA + "common/HeightCache.java", MINES), (JAVA + "mixin/ChunkGeneratorLocateMixin.java", MINES),
    # encargos del tablón y reputación (T38)
    (JAVA + "quests/*", QUESTS), (JAVA + "mixin/VillagerPricesMixin.java", QUESTS), ("tools/gen/quests.py", QUESTS),
    # caravanas por los caminos (T39)
    (JAVA + "caravans/*", CARAVANS), ("tools/gen/caravans.py", CARAVANS),
    # chozas de mago (T43)
    (JAVA + "huts/*", HUTS), ("tools/gen/wizard_huts.py", HUTS),
    # actualizaciones seguras (T46): su Java, el panel, las preferencias, los menús, la migración y sus textos
    (JAVA + "update/*", SAFE_UPDATE), (JAVA + "command/ConfigPanel.java", SAFE_UPDATE),
    (JAVA + "command/Preferences.java", SAFE_UPDATE), (JAVA + "config/Menus.java", SAFE_UPDATE),
    (JAVA + "config/ConfigMigration.java", SAFE_UPDATE), ("tools/gen/updates.py", SAFE_UPDATE),
    # perfiles de juego (T36): su lógica y su comando (el resto de la configuración es común: batería completa)
    (JAVA + "config/Profiles.java", PROFILES), (JAVA + "command/ProfileCommand.java", PROFILES),
    ("tools/gen/biomes.py", ["tools/smoke/terralith_biomes.py"]),
    ("tools/gen/c_tags.json", ["tools/smoke/terralith_biomes.py"]),
    # los mods de Modrinth fijados: las pruebas que los descargan (las de compatibilidad, por COMPAT_RUTAS)
    ("tools/smoke/modrinth.py", ["tools/smoke/trophies.py", "tools/smoke/story.py", "tools/smoke/village_life.py",
                                 "tools/smoke/terralith_biomes.py"]),
    # mixins de los mobs de plantilla y comandos (la de humo prueba /heraldia info y llave)
    (JAVA + "mixin/Zombie*", ["tools/smoke/adult_guardians.py"]),
    (JAVA + "mixin/DrownedMixin.java", ["tools/smoke/adult_guardians.py"]),
    (JAVA + "mixin/DrownedWaterMixin.java", ["tools/smoke/anchored_guardians.py"]),
    (JAVA + "mixin/DrownedBeachMixin.java", ["tools/smoke/anchored_guardians.py"]),
    (JAVA + "common/Anchoring.java", ["tools/smoke/anchored_guardians.py"]),
    # botín que se repone y dificultad configurable (T29)
    (JAVA + "loot/RestockedLoot.java", ["tools/smoke/loot_restock.py"]), (JAVA + "loot/Restock.java", ["tools/smoke/loot_restock.py"]),
    (JAVA + "difficulty/*", ["tools/smoke/difficulty.py"]),
    # Guía del Heraldo: su Java (y los textos por idioma que usa), su generador y su prueba
    (JAVA + "command/Guide*", ["tools/smoke/guide.py"]), (JAVA + "command/Texts.java", ["tools/smoke/guide.py"]),
    ("tools/gen/guide.py", ["tools/smoke/guide.py"]),
    # idiomas del mod (traducciones y su comprobación): la Guía es lo único que el servidor entrega en el idioma del cliente
    ("tools/gen/languages.py", ["tools/smoke/guide.py"]), ("tools/gen/languages/*", ["tools/smoke/guide.py"]),
    # herramientas de administración (T35): /heraldia review, status y reload (y la búsqueda de info nearby que reutilizan)
    (JAVA + "command/Revi*", ADMIN), (JAVA + "command/SafeSpot.java", ADMIN),
    (JAVA + "command/StatusCommand.java", ADMIN), (JAVA + "command/State.java", ADMIN), (JAVA + "command/ReloadCommand*", ADMIN), (JAVA + "command/InfoCommand.java", ADMIN),
    (JAVA + "config/Reload.java", ADMIN), ("tools/gen/admin.py", ADMIN),
    # comandos en inglés y sus alias antiguos (T35b): el árbol de /heraldia lo usan todas las pruebas de comandos; el
    # aviso de versión nueva, su prueba con la API de mentira
    (JAVA + "command/HeraldiaCommands.java", COMMANDS), (JAVA + "command/Alias.java", COMMANDS),
    (JAVA + "mixin/CommandsMixin.java", COMMANDS), ("tools/gen/commands.py", COMMANDS),
    (JAVA + "command/VersionNotice.java", UPDATE), (JAVA + "version/*", UPDATE),
    # mapas web (T37): su Java (con los adaptadores), el mixin de los logros y su prueba con squaremap y sin mapas
    (JAVA + "maps/*", WEB_MAPS), (JAVA + "mixin/PlayerAdvancementsMixin.java", WEB_MAPS),
    # búsqueda del tesoro (T40): su Java y su generador; la recompensa de las hazañas del tablón va en tablon.py (arriba)
    (JAVA + "treasure/*", TREASURE), ("tools/gen/treasure.py", TREASURE),
    (JAVA + "command/*", []),
    # jefes: fases, refuerzos y barra de los guardianes (su Java y el contrato de refuerzos del generador)
    (JAVA + "bosses/*", ["tools/smoke/boss_phases.py"]), ("tools/gen/bosses.py", ["tools/smoke/boss_phases.py"]),
    # arena de oleadas (T31) y sus modos (T41): su Java, sus mixins y su generador (plantilla, datos, botín y logros)
    (JAVA + "arena/*", ARENA), (JAVA + "mixin/Arena*", ARENA), ("tools/gen/arena_waves.py", ARENA),
    # caminos entre aldeas: su Java y sus datos
    (JAVA + "roads/*", ["tools/smoke/roads.py"]), ("tools/gen/roads.py", ["tools/smoke/roads.py"]),
    # código común: batería completa
    ("tools/gen/uniques/_common/*", FULL), ("tools/gen/uniques/__init__.py", FULL), ("tools/gen/writer.py", FULL),
    ("tools/gen/core.py", FULL), ("tools/gen/pack.py", FULL), ("tools/gen/lint.py", FULL), ("tools/gen/validate.py", FULL),
    ("tools/gen/main.py", FULL), ("tools/gen/build.py", FULL), ("tools/gen/options.py", FULL), ("tools/gen/requirements.txt", FULL),
    ("tools/smoke/server_smoke.py", FULL), ("tools/test.py", FULL), (".github/*", FULL), ("build.gradle", FULL),
    ("gradle.properties", FULL), ("settings.gradle", FULL), ("gradle/*", FULL), ("gradlew*", FULL),
    ("src/main/resources/*", FULL), (JAVA + "*", FULL),
]


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def compat_groups():
    """Grupos de compat_mods.py (lo importa sin ejecutar nada)."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "smoke"))
    import compat_mods
    return list(compat_mods.GROUPS)


def discover():
    """Todas las pruebas de servidor (sin la de humo), ordenadas; compat_mods.py, una por grupo."""
    smoke = [rel(p) for p in glob.glob(os.path.join(ROOT, "tools", "smoke", "*.py")) if os.path.basename(p) not in NOT_TESTS]
    uniques = [rel(p) for p in glob.glob(os.path.join(ROOT, "tools", "gen", "uniques", "*", "smoke_*.py"))]
    if COMPAT in smoke:
        smoke.remove(COMPAT)
        smoke += [f"{COMPAT}::{g}" for g in compat_groups()]
    return sorted(smoke + uniques)


def is_compat(test):
    return test.split("::")[0] == COMPAT


def order(test):
    """Orden para ejecutar una prueba: [script, argumentos...] («ruta::grupo» pasa --grupo grupo)."""
    script, _, group = test.partition("::")
    return [os.path.join(ROOT, script)] + (["--group", group] if group else [])


def for_unique(sid, all_items):
    """Pruebas de servidor de una única: las de su carpeta, las de SMOKE_DE_UNICA y DE_TODA_UNICA."""
    own_ones = [p for p in all_items if p.startswith(f"tools/gen/uniques/{sid}/")]
    return own_ones + SMOKE_OF_UNIQUE.get(sid, []) + OF_EVERY_UNIQUE


def dest(route, all_items):
    """Pruebas de servidor que pide un fichero cambiado: lista, o TODO."""
    if route in all_items:                                           # la propia prueba
        return [route]
    if route == COMPAT:
        return [p for p in all_items if is_compat(p)]
    parts = route.split("/")
    if route.startswith("tools/gen/uniques/") and len(parts) >= 4 and not parts[3].startswith("_"):
        sid = parts[3][:-3] if len(parts) == 4 and parts[3].endswith(".py") else parts[3]
        if len(parts) > 4 or route.endswith(".py"):
            return for_unique(sid, all_items)
    if route.startswith(JAVA + "uniques/") and len(parts) > 9:      # src/main/java/io/github/albertosa23/heraldia/uniques/<paquete>/...
        pkg = parts[8]
        if pkg in JAVA_UNIQUE:
            return for_unique(JAVA_UNIQUE[pkg], all_items)
        return FULL
    for pattern, tests in MAP:
        if fnmatch.fnmatch(route, pattern):
            return tests
    return FULL


def choose(changed_list, all_items=None):
    """(completa, [pruebas]) para una lista de rutas cambiadas (relativas a la raíz, con «/»). Las de compatibilidad
    (COMPAT) solo entran si alguna ruta está en COMPAT_RUTAS, también cuando lo cambiado pide la batería completa."""
    all_items = discover() if all_items is None else all_items
    compat = any(fnmatch.fnmatch(r, pat) for r in changed_list for pat in COMPAT_PATHS)
    chosen_ones = set()
    for r in changed_list:
        p = dest(r, all_items)
        if p == FULL:
            return True, [x for x in all_items if compat or not is_compat(x)]
        chosen_ones.update(x for x in p if x in all_items)
    if compat:
        chosen_ones.update(x for x in all_items if is_compat(x))
    return False, sorted(chosen_ones)


def cost(changed_list):
    """¿Pide la lista de rutas cambiadas la prueba de coste de generación (COSTE_RUTAS sin COSTE_SIN)?"""
    return any(any(fnmatch.fnmatch(r, p) for p in COST_PATHS) and not any(fnmatch.fnmatch(r, p) for p in COST_WITHOUT)
               for r in changed_list)


def changed_list(base):
    """Ficheros cambiados frente a `base` (merge-base), más los del árbol de trabajo sin confirmar."""
    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    mb = git("merge-base", base, "HEAD")[0].strip()
    out = git("diff", "--name-only", mb) + git("ls-files", "--others", "--exclude-standard")
    return sorted({l.strip() for l in out if l.strip()})


# Duración medida de cada prueba en la CI (s, solo el paso de la prueba; servidor ya en caché). Sirve para repartirlas
# en grupos parecidos; una prueba que no está aquí cuenta como DEFECTO_S.
DURATION_S = {
    "tools/smoke/village_life.py": 170, "tools/smoke/village_variants.py": 135, "tools/smoke/village_terrain.py": 185,
    "tools/gen/uniques/corsair_island/smoke_server.py": 100, "tools/gen/uniques/lost_mine/smoke_server.py": 95,
    "tools/smoke/trophies.py": 90, "tools/smoke/citadel_check.py": 80, "tools/smoke/observatory_smoke.py": 75,
    "tools/smoke/adult_guardians.py": 72, "tools/gen/uniques/sanctuary/smoke_server.py": 70,
    "tools/gen/uniques/cathedral/smoke_game.py": 65, "tools/gen/uniques/jarl_hall/smoke_server.py": 65,
    "tools/gen/uniques/mycelium_lab/smoke_server.py": 64, "tools/smoke/story.py": 62,
    "tools/smoke/palace_redstone.py": 57, "tools/smoke/terralith_biomes.py": 50,
    "tools/gen/uniques/ice_fortress/smoke_server.py": 47, "tools/gen/uniques/monastery/smoke_server.py": 45,
    "tools/gen/uniques/castle/smoke_redstone.py": 44, "tools/gen/uniques/mansion/smoke_server.py": 40,
    "tools/smoke/colosseum_redstone.py": 39, "tools/smoke/compatible_grid.py": 80, "tools/smoke/roads.py": 300,
    "tools/gen/uniques/wizard_tower/smoke_redstone.py": 33,
    "tools/gen/uniques/pyramid/smoke_server.py": 28, "tools/smoke/galleon_test.py": 26,
    "tools/smoke/boss_phases.py": 70,                     # medida en local: 60 s con dos arranques (el segundo, con las opciones desactivadas)
    # compatibilidad (medidas en local en 4 núcleos con las descargas en caché, más un 30 % para la CI)
    **{f"{COMPAT}::{g}": s for g, s in {"base": 75, "rendimiento": 75, "biomas": 90, "servidor": 90, "distanthorizons": 90,
                                         "estructuras": 100, "terreno": 110, "tectonic": 140, "wwoo": 170}.items()},
    "tools/smoke/anchored_guardians.py": 450,
    "tools/smoke/medium_structures.py": 200,          # medida en local (4 núcleos): 3 min 20 s con el arranque; 2 min 40 s con los 8 tipos
    "tools/smoke/guide.py": 120,                      # tres arranques del servidor
    "tools/smoke/mine_entrances.py": 250,                     # dos arranques (multiplicador 1 y 5), la generación de las minas y /locate lejos
    "tools/smoke/coast.py": 280,                     # medida en local: ~3 min 50 s (dos arranques, cuatro /locate con su generación y /place junto a playas)
    "tools/smoke/profiles.py": 110,                  # cuatro arranques del mismo mundo
    "tools/smoke/update.py": 140,                # medida en local: ~2 min 15 s (dos arranques y una zona de 400 chunks)
    "tools/smoke/loot_restock.py": 100,             # medida en local: 72 s (dos arranques y una ermita generada)
    "tools/smoke/difficulty.py": 100,                # medida en local: ~70 s (cuatro arranques del mismo mundo)
    "tools/smoke/arena.py": 150,                     # medida en local: ~2 min (dos arranques, tres obras y cinco oleadas)
    "tools/smoke/arena_modes.py": 200,               # dos arranques, una obra, siete oleadas cortas y el cierre de dos semanas
    "tools/smoke/admin.py": 80,                      # medida en local: 60 s (dos arranques y dos medianas cargadas o generadas)
    "tools/smoke/update_check.py": 120,              # tres arranques (con la API de mentira, sin red y desactivado)
    "tools/smoke/web_maps.py": 240,                 # tres arranques (sin mapas, con squaremap y Carpet, y tras reiniciar)
    "tools/smoke/existing_world.py": 150,           # medida en local: ~2 min (tres arranques del mismo mundo)
    "tools/smoke/quests.py": 150,                  # dos arranques del mismo mundo y una aldea generada
    "tools/smoke/treasure.py": 130,                    # medida en local: ~1 min 40 s (tres arranques, la cadena entera y el cofre)
    "tools/smoke/nether_end.py": 300,                # T44: un arranque, /locate y generación en el Nether y el End, /place de 16 estilos
    "tools/smoke/wizard_huts.py": 100,               # medida en local: ~75 s (dos arranques, cuatro chozas y tres Magos Malvados)
    "tools/smoke/caravans.py": 240,                 # medida en local: ~3,5 min (dos arranques, 387 chunks de pasillo y 5 caravanas)
}
DEFAULT_S = 90
# Cada job de la CI paga ~25 s de preparación (máquina, Java, Python, cachés) antes de la prueba: se juntan pruebas cortas
# en un job mientras el grupo no pase de la más larga (así no se alarga la CI y se ocupan menos máquinas). GitHub
# Actions gratis da 20 jobs a la vez: con la de humo y la compilación, la batería completa cabe en una sola tanda.
GROUP_CAP_S = 170


def groups(tests, cap=GROUP_CAP_S):
    """Reparte las pruebas en grupos (listas) de duración <= max(tope, la más larga): primero las largas, cada una en
    el grupo más corto donde quepa (si no cabe en ninguno, abre otro). Determinista."""
    dur = lambda p: DURATION_S.get(p, DEFAULT_S)
    cap = max([cap] + [dur(p) for p in tests])
    out = []
    for p in sorted(tests, key=lambda p: (-dur(p), p)):
        fits = [g for g in out if sum(map(dur, g)) + dur(p) <= cap]
        if fits:
            min(fits, key=lambda g: sum(map(dur, g))).append(p)
        else:
            out.append([p])
    return out


def name(g):
    """Nombre corto de un grupo para la CI: «isla_corsario + piramide»."""
    def brief(p):
        if "::" in p:
            return "compat " + p.split("::")[1]
        parts = p.split("/")
        return parts[3] if p.startswith("tools/gen/uniques/") else parts[-1][:-3]
    return " + ".join(brief(p) for p in g)


def matrix(full, tests):
    return {"include": [{"name": name(g), "tests": " ".join(g)} for g in groups(tests)]} if tests else {"include": []}


def unit_tests():
    """Tests unitarios rápidos del generador (pytest). Los JUnit van con ./gradlew test."""
    return subprocess.run([sys.executable, "-m", "pytest", "-q", os.path.join(ROOT, "tools", "gen", "tests")],
                          cwd=ROOT).returncode


def execute(tests, jar, work, logs=None):
    """Ejecuta las pruebas de servidor en serie (todas, aunque falle una) y devuelve las que fallan. Copia el
    logs/latest.log de cada una a `logs` (si se da) para subirlo como artefacto."""
    bad_all = []
    for p in tests:
        t0 = time.monotonic()
        print(f"::group::{p}" if os.environ.get("GITHUB_ACTIONS") else f"== {p}", flush=True)
        r = subprocess.run([sys.executable, *order(p), "--jar", jar, "--work", work], cwd=ROOT).returncode
        if os.environ.get("GITHUB_ACTIONS"):
            print("::endgroup::")
        print(f"{'OK' if r == 0 else 'FALLA'} {p} ({time.monotonic() - t0:.0f} s)", flush=True)
        if logs:
            os.makedirs(logs, exist_ok=True)
            src = os.path.join(work, "logs", "latest.log")
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(logs, p.replace("::", "-").replace("/", "-").replace(".py", "") + ".log"))
        if r:
            bad_all.append(p)
    return bad_all


def default_jar():
    props = dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, "gradle.properties"), encoding="utf-8")
                 if "=" in l and not l.lstrip().startswith("#"))
    return os.path.join(ROOT, "build", "libs", f"heraldia-{props['mod_version']}.jar")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--affected", action="store_true", help="unitarios + pruebas de servidor de lo cambiado")
    mode.add_argument("--all", action="store_true", help="batería completa (sesión auditora)")
    mode.add_argument("--list-only", action="store_true", help="solo lista las pruebas de servidor elegidas")
    mode.add_argument("--unit-tests", action="store_true", help="solo los tests unitarios del generador")
    mode.add_argument("--ci-matrix", action="store_true", help="matriz JSON para la CI")
    mode.add_argument("--group", help="ejecuta en serie estas pruebas (separadas por espacios)")
    ap.add_argument("--base", default="origin/develop", help="referencia con la que comparar (por defecto origin/develop)")
    ap.add_argument("--full", action="store_true", help="con --ci-matriz/--listar: batería completa")
    ap.add_argument("--jar", help="el .jar del mod (por defecto el de la versión de gradle.properties)")
    ap.add_argument("--work", default=os.path.join(ROOT, "build", "smoke"), help="carpeta del servidor de prueba")
    ap.add_argument("--logs", help="carpeta donde copiar el log de cada prueba")
    ap.add_argument("--no-unit", action="store_true", help="con --afectados/--todo: no pasa los unitarios")
    ap.add_argument("--no-cost", action="store_true", help="con --afectados/--todo: no pasa la prueba de coste de generación")
    a = ap.parse_args(argv)
    work = os.path.abspath(a.work)       # los scripts arrancan Java con cwd=--work: ruta absoluta
    jar = os.path.abspath(a.jar or default_jar())

    if a.unit_tests:
        return unit_tests()
    if a.group is not None:
        bad_all = execute(a.group.split(), jar, work, a.logs)
        print("Fallan:" if bad_all else "Todas pasan.", " ".join(bad_all))
        return 1 if bad_all else 0

    if a.all or a.full:
        full, tests, changes, with_cost = True, discover(), [], True
    else:
        changes = changed_list(a.base)
        (full, tests), with_cost = choose(changes), cost(changes)
    if a.ci_matrix:
        print(json.dumps(dict(matrix(full, tests), full=full, cost=with_cost), ensure_ascii=False))
        return 0
    if a.list_only or a.affected:
        print(f"{len(changes)} ficheros cambiados frente a {a.base}" if changes else "batería completa", file=sys.stderr)
        print(("Batería completa: " if full else "Pruebas de servidor afectadas: ") + (", ".join(tests) or "ninguna"),
              file=sys.stderr)
        print(f"Coste de generación ({COST}): {'sí' if with_cost else 'no'}", file=sys.stderr)
        if a.list_only:
            print("\n".join(tests + ([COST] if with_cost else [])))
            return 0
    if with_cost and not a.no_cost:
        tests = tests + [COST]
    if not a.no_unit and unit_tests():
        return 1
    if not os.path.isfile(jar):
        print(f"No está el .jar {jar}: compila antes con ./gradlew build (o pasa --jar).", file=sys.stderr)
        return 1
    bad_all = execute(([SMOKE] if a.all else []) + tests, jar, work, a.logs)
    print("Fallan:" if bad_all else "Todas pasan.", " ".join(bad_all))
    return 1 if bad_all else 0


if __name__ == "__main__":
    sys.exit(main())
