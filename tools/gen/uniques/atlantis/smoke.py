"""Comprobaciones de la Atlántida en la prueba de humo (servidor dedicado real). La llama tools/smoke/server_smoke.py.

Genera por worldgen el distrito central (templo, vestíbulo, galerías y cámaras) y comprueba: /locate, celdas secas y
de agua, puerta de combinación del vestíbulo, cofre premium (contenido y cerradura) y llave del guardián final.
"""
import re, time
from . import blueprint, urban_layout as U
from .districts import COMBINATION_CENTRAL

ID = "heraldia:unicas/atlantida"
MIDDLE = 128        # el distrito central ocupa [-128, 128) en x y z


def check(ctx):
    failures = []
    m = re.search(r"Atlántida (?:situada )?en el bloque (-?\d+), (-?\d+)", ctx.log())
    if not m:
        return ["el log no dice dónde está la Atlántida"]
    X, Z = int(m.group(1)), int(m.group(2))
    r = ctx.run(f"locate structure {ID}", r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
    if r.group(1) is None or (int(r.group(1)), int(r.group(2))) != (X, Z):
        failures.append(f"/locate no señala el ancla {X}, {Z}: {r.string.strip()}")
    pl = blueprint()

    def block(c, state):
        g = ctx.run(f"execute if block {X + c[0]} {c[1]} {Z + c[2]} {state}", r"Test passed|Test failed|not loaded").group(0)
        return None if "loaded" in g else "passed" in g

    ctx.run(f"forceload add {X - MIDDLE} {Z - MIDDLE} {X + MIDDLE - 1} {Z + MIDDLE - 1}", r"Marked|Added|force")
    corners = [(-MIDDLE, 20, -MIDDLE), (MIDDLE - 1, 20, MIDDLE - 1), (-MIDDLE, 20, MIDDLE - 1), (MIDDLE - 1, 20, -MIDDLE), (0, 20, 0)]
    finish = time.monotonic() + 600
    while time.monotonic() < finish and not all(block(c, "minecraft:air") is not None for c in corners):
        time.sleep(5)
    ctx.ticks(800)                      # margen (40 s de juego) para que el agua mal contenida, si la hubiera, llegase a correr
    inside = lambda c: -MIDDLE <= c[0] < MIDDLE and -MIDDLE <= c[2] < MIDDLE
    for mark, state in (("seca", "minecraft:air"), ("agua", "minecraft:water")):
        cell_list = [c for c in pl.marks[mark] if inside(c)]
        wrong = [c for c in cell_list if not block(c, state)]
        if wrong or len(cell_list) < 5:
            failures.append(f"celdas «{mark}» incorrectas: {len(wrong)} de {len(cell_list)}, p. ej. {wrong[:4]}")
    for c, state in (((0, U.FLOOR, 104), "minecraft:sea_lantern"), ((3, U.FLOOR, 104), "minecraft:dark_prismarine"),
                      ((100, U.FLOOR + 5, 100), "minecraft:water"), ((100, U.BASE, 100), "minecraft:stone")):
        if not block(c, state):
            failures.append(f"la pieza base no dejó {state} en {c}")

    # puerta de combinación del vestíbulo: se accionan las palancas y se «toca» el bloque sobre cada componente,
    # que es la actualización que provoca un jugador al accionarlas (setblock no avisa al bloque de apoyo)
    levers, door, touches = pl.marks["palanca_templo"], pl.marks["puerta_templo"][0], pl.marks["toque_templo"]

    def put(states):
        for c, on in zip(levers, states):
            st = pl.blocks[c][0].replace("powered=false", f"powered={'true' if on else 'false'}")
            ctx.run(f"setblock {X + c[0]} {c[1]} {Z + c[2]} {st}", r"Changed the block|Could not set")
        for _ in range(2):
            for c in touches:
                for b in ("minecraft:glass", pl.blocks[c][0]):
                    ctx.run(f"setblock {X + c[0]} {c[1]} {Z + c[2]} {b}", r"Changed the block|Could not set")
            ctx.ticks(30)

    def is_open(value):
        return block(door, f"minecraft:iron_door[open={'true' if value else 'false'}]")

    steps = [("al generarse", None, False), ("con todas alzadas", [True] * 4, False), ("con la combinación", COMBINATION_CENTRAL, True),
             ("con una mal", [not COMBINATION_CENTRAL[0]] + COMBINATION_CENTRAL[1:], False), ("con la combinación otra vez", COMBINATION_CENTRAL, True)]
    for name, states, required in steps:
        if states:
            put(states)
        if not is_open(required):
            failures.append(f"puerta del vestíbulo {name}: debería estar {'abierta' if required else 'cerrada'}")

    # cofre premium: contenido fijo (dos tridentes), cerradura y marca del cofre por jugador (custom_data del bloque)
    px, py, pz = pl.marks["premium"][0]
    r = ctx.run(f"data get block {X + px} {py} {Z + pz}", r"has the following block data: (.*)")
    dataset = r.group(1) if r.group(0).startswith("has") else ""
    if (dataset.count('id: "minecraft:trident"') < 2 or "LootTable" in dataset or 'heraldia_llave:"poseidon"' not in dataset.replace("\\", "")
            or not re.search(r'heraldia_cofre_unico:\s*"atlantida"', dataset.replace("\\", ""))):
        failures.append(f"cofre premium incorrecto: {r.string.strip()[:300]}")

    # guardián final: existe y suelta la llave de Poseidón
    # (su DeathLootTable es la del trofeo, _comun/botin.guardian_tabla, que incluye la de la llave)
    boss = '@e[type=minecraft:elder_guardian,nbt={DeathLootTable:"heraldia:guardianes/atlantida/elder_guardian"}]'
    if not ctx.wait_entity(boss):       # las entidades aparecen unos segundos después que los bloques
        failures.append("no está el guardián final")
    failures += _info_here(ctx, X, Z, r"Guardian: alive|Guardián: vivo")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity")
    ctx.run(f"kill {boss}", r"Killed|No entity")
    ctx.ticks(20)                       # un segundo de juego (en ticks: con el servidor atrasado, el reloj no basta)
    failures += _info_here(ctx, X, Z, r"Guardian: defeated|Guardián: derrotado")
    key = '@e[type=minecraft:item,nbt={Item:{id:"minecraft:nautilus_shell",components:{"minecraft:custom_data":{heraldia_llave:"poseidon"}}}}]'
    if "passed" not in ctx.run(f"execute if entity {key}", r"Test passed|Test failed").group(0):
        failures.append("el guardián final no suelta la llave de Poseidón")
    trophy = '@e[type=minecraft:item,nbt={Item:{components:{"minecraft:custom_data":{heraldia_trofeo:"atlantida"}}}}]'
    if "failed" not in ctx.run(f"execute if entity {trophy}", r"Test passed|Test failed").group(0):
        failures.append("el guardián final suelta su trofeo con /kill (sin jugador)")
    ctx.run(f"forceload remove {X - MIDDLE} {Z - MIDDLE} {X + MIDDLE - 1} {Z + MIDDLE - 1}", r"Unmarked|Removed|No chunks|force")
    return failures


def _info_here(ctx, X, Z, guardian):
    """/heraldia info here dentro del distrito central (generado por worldgen, con el distrito forzado): dice que es la
    Atlántida y el estado del guardián (se busca por su etiqueta en la caja del distrito central)."""
    c = f"execute positioned {X} {U.FLOOR} {Z + 104} run heraldia info here"
    m = ctx.run(c, r"(?:You are in|Estás en) .*\(heraldia:unicas/atlantida\)|no Heraldia structure|ninguna estructura Heraldia")
    if "atlantida" not in m.group(0):
        return [f"/heraldia info here no reconoce la Atlántida: {m.string.strip()}"]
    m = ctx.run("say fin de info aqui", r"(?:Guardian|Guardián): .*|fin de info aqui")
    if not re.search(guardian, m.group(0)):
        return [f"/heraldia info here: se esperaba «{guardian}»: {m.string.strip()}"]
    return []

