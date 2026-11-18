"""Atlantis checks in the smoke test (real dedicated server). Called by tools/smoke/server_smoke.py.

Generates the central district (temple, vestibule, galleries and chambers) via worldgen and checks: /locate, dry and
water cells, the vestibule combination door, premium chest (content and lock) and the final guardian's key.
"""
import re, time
from . import blueprint, urban_layout as U
from .districts import COMBINATION_CENTRAL

ID = "heraldia:unicas/atlantida"
MIDDLE = 128        # the central district occupies [-128, 128) in x and z


def check(ctx):
    failures = []
    m = re.search(r"Atlántida (?:situada )?en el bloque (-?\d+), (-?\d+)", ctx.log())
    if not m:
        return ["el log no dice dónde está la Atlántida"]
    X, Z = int(m.group(1)), int(m.group(2))
    r = ctx.run(f"locate structure {ID}", r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
    if r.group(1) is None or (int(r.group(1)), int(r.group(2))) != (X, Z):
        failures.append(f"/locate does not point to the anchor {X}, {Z}: {r.string.strip()}")
    pl = blueprint()

    def block(c, state):
        g = ctx.run(f"execute if block {X + c[0]} {c[1]} {Z + c[2]} {state}", r"Test passed|Test failed|not loaded").group(0)
        return None if "loaded" in g else "passed" in g

    ctx.run(f"forceload add {X - MIDDLE} {Z - MIDDLE} {X + MIDDLE - 1} {Z + MIDDLE - 1}", r"Marked|Added|force")
    corners = [(-MIDDLE, 20, -MIDDLE), (MIDDLE - 1, 20, MIDDLE - 1), (-MIDDLE, 20, MIDDLE - 1), (MIDDLE - 1, 20, -MIDDLE), (0, 20, 0)]
    finish = time.monotonic() + 600
    while time.monotonic() < finish and not all(block(c, "minecraft:air") is not None for c in corners):
        time.sleep(5)
    ctx.ticks(800)                      # margin (40 game seconds) so that poorly contained water, if any, has time to flow
    inside = lambda c: -MIDDLE <= c[0] < MIDDLE and -MIDDLE <= c[2] < MIDDLE
    for mark, state in (("seca", "minecraft:air"), ("agua", "minecraft:water")):
        cell_list = [c for c in pl.marks[mark] if inside(c)]
        wrong = [c for c in cell_list if not block(c, state)]
        if wrong or len(cell_list) < 5:
            failures.append(f"celdas «{mark}» incorrectas: {len(wrong)} de {len(cell_list)}, p. ej. {wrong[:4]}")
    for c, state in (((0, U.FLOOR, 104), "minecraft:sea_lantern"), ((3, U.FLOOR, 104), "minecraft:dark_prismarine"),
                      ((100, U.FLOOR + 5, 100), "minecraft:water"), ((100, U.BASE, 100), "minecraft:stone")):
        if not block(c, state):
            failures.append(f"the base piece did not leave {state} at {c}")

    # vestibule combination door: the levers are pulled and the block over each component is "touched",
    # which is the update a player causes when pulling them (setblock does not notify the supporting block)
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

    # premium chest: fixed content (two tridents), lock and the per-player chest mark (block custom_data)
    px, py, pz = pl.marks["premium"][0]
    r = ctx.run(f"data get block {X + px} {py} {Z + pz}", r"has the following block data: (.*)")
    dataset = r.group(1) if r.group(0).startswith("has") else ""
    if (dataset.count('id: "minecraft:trident"') < 2 or "LootTable" in dataset or 'heraldia_llave:"poseidon"' not in dataset.replace("\\", "")
            or not re.search(r'heraldia_cofre_unico:\s*"atlantida"', dataset.replace("\\", ""))):
        failures.append(f"incorrect premium chest: {r.string.strip()[:300]}")

    # final guardian: exists and drops Poseidon's key
    # (its DeathLootTable is the trophy one, _comun/chest_loot.guardian_table, which includes the key's)
    boss = '@e[type=minecraft:elder_guardian,nbt={DeathLootTable:"heraldia:guardianes/atlantida/elder_guardian"}]'
    if not ctx.wait_entity(boss):       # entities appear a few seconds after the blocks
        failures.append("the final guardian is missing")
    failures += _info_here(ctx, X, Z, r"Guardian: alive|Guardián: vivo")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity")
    ctx.run(f"kill {boss}", r"Killed|No entity")
    ctx.ticks(20)                       # one game second (in ticks: with the server lagging, the clock is not enough)
    failures += _info_here(ctx, X, Z, r"Guardian: defeated|Guardián: derrotado")
    key = '@e[type=minecraft:item,nbt={Item:{id:"minecraft:nautilus_shell",components:{"minecraft:custom_data":{heraldia_llave:"poseidon"}}}}]'
    if "passed" not in ctx.run(f"execute if entity {key}", r"Test passed|Test failed").group(0):
        failures.append("the final guardian does not drop Poseidon's key")
    trophy = '@e[type=minecraft:item,nbt={Item:{components:{"minecraft:custom_data":{heraldia_trofeo:"atlantida"}}}}]'
    if "failed" not in ctx.run(f"execute if entity {trophy}", r"Test passed|Test failed").group(0):
        failures.append("the final guardian drops its trophy with /kill (no player)")
    ctx.run(f"forceload remove {X - MIDDLE} {Z - MIDDLE} {X + MIDDLE - 1} {Z + MIDDLE - 1}", r"Unmarked|Removed|No chunks|force")
    return failures


def _info_here(ctx, X, Z, guardian):
    """/heraldia info here inside the central district (generated by worldgen, with the district forced): says it is
    Atlantis and the state of the guardian (looked up by its tag in the central district's box)."""
    c = f"execute positioned {X} {U.FLOOR} {Z + 104} run heraldia info here"
    m = ctx.run(c, r"(?:You are in|Estás en) .*\(heraldia:unicas/atlantida\)|no Heraldia structure|ninguna estructura Heraldia")
    if "atlantida" not in m.group(0):
        return [f"/heraldia info here no reconoce la Atlántida: {m.string.strip()}"]
    m = ctx.run("say fin de info aqui", r"(?:Guardian|Guardián): .*|fin de info aqui")
    if not re.search(guardian, m.group(0)):
        return [f"/heraldia info here: se esperaba «{guardian}»: {m.string.strip()}"]
    return []

