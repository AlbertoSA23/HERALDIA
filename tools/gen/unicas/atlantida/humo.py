"""Comprobaciones de la Atlántida en la prueba de humo (servidor dedicado real). La llama tools/smoke/server_smoke.py.

Genera por worldgen el distrito central (templo, vestíbulo, galerías y cámaras) y comprueba: /locate, celdas secas y
de agua, puerta de combinación del vestíbulo, cofre premium (contenido y cerradura) y llave del guardián final.
"""
import re, time
from . import plano, urbanismo as U
from .distritos import COMBINACION_CENTRAL

ID = "heraldia:unicas/atlantida"
MEDIO = 128        # el distrito central ocupa [-128, 128) en x y z


def comprobar(ctx):
    fallos = []
    m = re.search(r"Atlántida (?:situada )?en el bloque (-?\d+), (-?\d+)", ctx.log())
    if not m:
        return ["el log no dice dónde está la Atlántida"]
    X, Z = int(m.group(1)), int(m.group(2))
    r = ctx.run(f"locate structure {ID}", r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
    if r.group(1) is None or (int(r.group(1)), int(r.group(2))) != (X, Z):
        fallos.append(f"/locate no señala el ancla {X}, {Z}: {r.string.strip()}")
    pl = plano()

    def bloque(c, estado):
        g = ctx.run(f"execute if block {X + c[0]} {c[1]} {Z + c[2]} {estado}", r"Test passed|Test failed|not loaded").group(0)
        return None if "loaded" in g else "passed" in g

    ctx.run(f"forceload add {X - MEDIO} {Z - MEDIO} {X + MEDIO - 1} {Z + MEDIO - 1}", r"Marked|Added|force")
    esquinas = [(-MEDIO, 20, -MEDIO), (MEDIO - 1, 20, MEDIO - 1), (-MEDIO, 20, MEDIO - 1), (MEDIO - 1, 20, -MEDIO), (0, 20, 0)]
    fin = time.monotonic() + 600
    while time.monotonic() < fin and not all(bloque(c, "minecraft:air") is not None for c in esquinas):
        time.sleep(5)
    time.sleep(40)                      # margen para que el agua mal contenida, si la hubiera, llegase a correr
    dentro = lambda c: -MEDIO <= c[0] < MEDIO and -MEDIO <= c[2] < MEDIO
    for marca, estado in (("seca", "minecraft:air"), ("agua", "minecraft:water")):
        celdas = [c for c in pl.marcas[marca] if dentro(c)]
        mal = [c for c in celdas if not bloque(c, estado)]
        if mal or len(celdas) < 5:
            fallos.append(f"celdas «{marca}» incorrectas: {len(mal)} de {len(celdas)}, p. ej. {mal[:4]}")
    for c, estado in (((0, U.SUELO, 104), "minecraft:sea_lantern"), ((3, U.SUELO, 104), "minecraft:dark_prismarine"),
                      ((100, U.SUELO + 5, 100), "minecraft:water"), ((100, U.BASE, 100), "minecraft:stone")):
        if not bloque(c, estado):
            fallos.append(f"la pieza base no dejó {estado} en {c}")

    # puerta de combinación del vestíbulo: se accionan las palancas y se «toca» el bloque sobre cada componente,
    # que es la actualización que provoca un jugador al accionarlas (setblock no avisa al bloque de apoyo)
    palancas, puerta, toques = pl.marcas["palanca_templo"], pl.marcas["puerta_templo"][0], pl.marcas["toque_templo"]

    def poner(estados):
        for c, on in zip(palancas, estados):
            st = pl.blocks[c][0].replace("powered=false", f"powered={'true' if on else 'false'}")
            ctx.run(f"setblock {X + c[0]} {c[1]} {Z + c[2]} {st}", r"Changed the block|Could not set")
        for _ in range(2):
            for c in toques:
                for b in ("minecraft:glass", pl.blocks[c][0]):
                    ctx.run(f"setblock {X + c[0]} {c[1]} {Z + c[2]} {b}", r"Changed the block|Could not set")
            time.sleep(1.5)

    def abierta(valor):
        return bloque(puerta, f"minecraft:iron_door[open={'true' if valor else 'false'}]")

    pasos = [("al generarse", None, False), ("con todas alzadas", [True] * 4, False), ("con la combinación", COMBINACION_CENTRAL, True),
             ("con una mal", [not COMBINACION_CENTRAL[0]] + COMBINACION_CENTRAL[1:], False), ("con la combinación otra vez", COMBINACION_CENTRAL, True)]
    for nombre, estados, debe in pasos:
        if estados:
            poner(estados)
        if not abierta(debe):
            fallos.append(f"puerta del vestíbulo {nombre}: debería estar {'abierta' if debe else 'cerrada'}")

    # cofre premium: contenido fijo (dos tridentes) y cerradura
    px, py, pz = pl.marcas["premium"][0]
    r = ctx.run(f"data get block {X + px} {py} {Z + pz}", r"has the following block data: (.*)")
    datos = r.group(1) if r.group(0).startswith("has") else ""
    if datos.count('id: "minecraft:trident"') < 2 or "LootTable" in datos or 'heraldia_llave:"poseidon"' not in datos.replace("\\", ""):
        fallos.append(f"cofre premium incorrecto: {r.string.strip()[:300]}")

    # guardián final: existe y suelta la llave de Poseidón
    jefe = '@e[type=minecraft:elder_guardian,nbt={DeathLootTable:"heraldia:unicas/atlantida/jefe"}]'
    if "passed" not in ctx.run(f"execute if entity {jefe}", r"Test passed|Test failed").group(0):
        fallos.append("no está el guardián final")
    ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity")
    ctx.run(f"kill {jefe}", r"Killed|No entity")
    time.sleep(1)
    llave = '@e[type=minecraft:item,nbt={Item:{id:"minecraft:nautilus_shell",components:{"minecraft:custom_data":{heraldia_llave:"poseidon"}}}}]'
    if "passed" not in ctx.run(f"execute if entity {llave}", r"Test passed|Test failed").group(0):
        fallos.append("el guardián final no suelta la llave de Poseidón")
    ctx.run(f"forceload remove {X - MEDIO} {Z - MEDIO} {X + MEDIO - 1} {Z + MEDIO - 1}", r"Unmarked|Removed|No chunks|force")
    return fallos
