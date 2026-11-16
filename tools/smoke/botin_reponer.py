"""Botín que se repone (botin.reponer.*) en un servidor dedicado 26.3 real, con jugadores simulados (Carpet).

Uso: python3 tools/smoke/botin_reponer.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Con botin.reponer.activado = true y botin.reponer.dias = 1, el reloj parado (advance_time false) y los días simulados
con /time add 24000, un jugador simulado abre los cofres (player ... use once, como un clic derecho) y se comprueba:
  - un cofre con tabla de Heraldia (heraldia:cofres/prueba_reponer, de un datapack de prueba con 7 flechas fijas): al
    abrirlo se llena y queda apuntado (custom_data heraldia_botin con su tabla); vaciado, no se repone antes de un día y sí
    al pasar el día;
  - con 4 casillas ocupadas no se repone ni se toca nada; con 3 (casi vacío) sí, y lo que había (un diamante en la
    casilla 0) sigue ahí;
  - con otro jugador a 8 bloques no se repone; con él a 100 bloques, sí;
  - no se apuntan el cofre de contenido fijo (heraldia_cofre_unico), uno con tabla de trofeo ni uno con tabla vanilla;
  - un cofre ya generado y saqueado antes de activar la opción (el de la celda de una ermita generada de verdad, la que
    da /locate, sin su LootTable y vacío): al abrirlo se reconoce su tabla original por la plantilla de la estructura y al día se repone;
  - tras reiniciar con la opción desactivada (lo de por defecto), abrir un cofre de Heraldia no apunta nada.
Sin Lootr (que desactiva todo esto) no se prueba aquí.
"""
import argparse, json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
import server_smoke as s
from guia import Server
from trofeos import CARPET
from modrinth import fetch
import medianas                      # noqa: E402  (plantillas de las medianas: dónde está el cofre de la ermita)
from pack import Registry           # noqa: E402
from estructuras_medianas import forceload, wait_generated   # noqa: E402

PLAYER, OTRO = "Testigo", "Aprendiz"     # los de guia.py (Carpet puede cambiar las mayúsculas de otros nombres)
DIA = 24000
TABLA = "heraldia:cofres/prueba_reponer"
FLECHAS = 7
C = (0, 100, 0)                       # cofre de prueba, en una losa; el jugador a 2 bloques
PACK = "heraldia_prueba_botin"
ERMITA, ERMITA_TABLA = "medianas/ermita", "heraldia:medianas/ermita/celda"
# StructureTemplate.transform (sin espejo, pivote 0): (x, z) local -> desplazamiento en el mundo, por giro
GIROS = {"none": lambda x, z: (x, z), "cw90": lambda x, z: (-z, x), "cw180": lambda x, z: (-x, -z), "ccw90": lambda x, z: (z, -x)}


def datapack(work):
    root = os.path.join(work, "world", "datapacks", PACK)
    os.makedirs(os.path.join(root, "data", "heraldia", "loot_table", "cofres"), exist_ok=True)
    with open(os.path.join(root, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"description": "Heraldia: prueba del botín que se repone", "min_format": 121, "max_format": 121}}, f)
    with open(os.path.join(root, "data", "heraldia", "loot_table", "cofres", "prueba_reponer.json"), "w") as f:
        json.dump({"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:arrow",
                   "modifier": {"type": "minecraft:set_count", "count": FLECHAS}}]}]}, f)


def config(work, activado):
    path = os.path.join(work, "config", "heraldia.json")
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    cfg["botin"] = {"reponer": {"activado": activado, "dias": 1}}
    with open(path, "w") as f:
        json.dump(cfg, f)


def ermita_cofres():
    """Posiciones locales (x, y, z) de los cofres con la tabla de la celda en los estilos y variantes de la ermita."""
    reg = Registry()
    medianas.build(reg, "ermita")
    out = set()
    for n, t in reg.templates.items():
        if n.startswith(ERMITA + "/"):
            out |= {p for p, (st, nbt) in t.blocks.items() if nbt and nbt.get("LootTable") == ERMITA_TABLA}
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-botin"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    locales = ermita_cofres()
    if len(locales) != 1:
        raise SystemExit(f"la ermita debería tener un solo cofre de celda (en todos sus estilos y variantes): {locales}")
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    datapack(a.work)
    config(a.work, True)
    fails, ok = [], 0
    srv = Server(a.work, launcher)
    ctx = srv.ctx

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)
            print("FALLA:", msg)

    def at(p):
        return " ".join(str(v) for v in p)

    def use(p, who=PLAYER):
        x, y, z = p
        # las acciones de Carpet no responden nada en la consola: se envían y se espera con una orden que sí responde
        s.send(srv.proc, f"player {who} look at {x + 0.5} {y + 0.5} {z + 0.5}")
        s.send(srv.proc, f"player {who} use once")
        ctx.ticks(4)

    def items(p, extra=""):
        return ctx.test(f"execute if data block {at(p)} Items[{extra}]")

    def arrows(p):
        """¿Hay flechas del datapack? (el botín de cofre reparte una pila en varias casillas libres al azar)"""
        return ctx.test(f'execute if data block {at(p)} Items[{{id:"minecraft:arrow"}}]')

    def record(p, tabla=None):
        sel = f'{{tabla:"{tabla}"}}' if tabla else ""
        return ctx.test(f'execute if data block {at(p)} components."minecraft:custom_data".heraldia_botin{sel}')

    def empty(p):
        ctx.run(f"data modify block {at(p)} Items set value []", r"Modified block data|[Nn]othing changed")

    def day():
        ctx.run(f"time add {DIA}", r"[Tt]ime|[Ss]et")

    try:
        x, y, z = C
        ctx.run(f"forceload add {x - 16} {z - 16} {x + 16} {z + 16}", r"Marked|force|already|[Aa]dded")
        for _ in range(s.PLACE_ATTEMPTS):
            m = ctx.run(f"fill {x - 4} {y - 1} {z - 4} {x + 12} {y - 1} {z + 4} minecraft:stone", r"Successfully filled|No blocks|not loaded")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        ctx.run(f"fill {x - 4} {y} {z - 4} {x + 12} {y + 4} {z + 4} minecraft:air", r"Successfully filled|No blocks")
        for rule in ("spawn_mobs", "advance_time"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
        ctx.run(f"player {PLAYER} spawn at {x + 2} {y} {z}", r"joined the game|Player .* spawn|Unknown|Incorrect")
        if not ctx.until(f"execute if entity @a[name={PLAYER}]"):
            raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
        s.send(srv.proc, f"gamemode survival {PLAYER}")  # sin respuesta en la consola si ya lo tenía
        check("botín que se repone activado: cada 1 días" in ctx.log(), "no sale en el log que la opción está activada")

        # 1) cofre nuevo con tabla de Heraldia: se llena y queda apuntado; vaciado, espera un día
        ctx.run(f'setblock {at(C)} minecraft:chest{{LootTable:"{TABLA}"}}', r"Changed the block|Could not set")
        use(C)
        check(arrows(C), "el cofre nuevo no se llena con su tabla al abrirlo")
        check(record(C, TABLA), "el cofre nuevo no queda apuntado (heraldia_botin con su tabla)")
        check(not ctx.test(f"execute if data block {at(C)} LootTable"), "el cofre conserva la LootTable tras abrirlo")
        empty(C)
        use(C)
        check(not items(C), "se repone sin que pase el día")
        ctx.run(f"time add {DIA - 1}", r"[Tt]ime|[Ss]et")
        use(C)
        check(not items(C), "se repone un tick antes del día")
        ctx.run("time add 1", r"[Tt]ime|[Ss]et")
        use(C)
        check(arrows(C), "vacío y pasado el día, no se repone")
        use(C)
        cerca = f"@e[type=minecraft:item,x={x},y={y},z={z},distance=..8]"     # (no la hojarasca que suelta el terreno)
        n = ctx.count(cerca)
        if n:
            m = ctx.run(f"data get entity {cerca[:-1]},limit=1] Item", r"has the following entity data: (.*)|No entity")
            print("DIAG: objeto en el suelo:", m.group(1), ctx.pos(cerca))
        check(n == 0, f"{n} objetos han caído al suelo")

        # 2) con cosas dentro: 4 casillas no; 3 (casi vacío) sí, sin tocar lo que había
        ctx.run(f'data modify block {at(C)} Items set value [{{Slot:0b,id:"minecraft:diamond",count:1}},'
                f'{{Slot:1b,id:"minecraft:dirt",count:5}},{{Slot:2b,id:"minecraft:dirt",count:5}},{{Slot:3b,id:"minecraft:dirt",count:5}}]',
                r"Modified block data")
        day()
        use(C)
        check(not arrows(C) and items(C, "{Slot:3b}"), "con 4 casillas ocupadas se repone o se toca")
        ctx.run(f"data remove block {at(C)} Items[{{Slot:3b}}]", r"Modified block data")
        use(C)
        check(arrows(C), "casi vacío (3 casillas) y pasado el día, no se repone")
        check(items(C, '{Slot:0b,id:"minecraft:diamond",count:1}') and items(C, '{Slot:1b,id:"minecraft:dirt",count:5}')
              and items(C, '{Slot:2b,id:"minecraft:dirt",count:5}'), "al reponer se ha tocado lo que había")

        # 3) otro jugador cerca lo impide
        empty(C)
        day()
        ctx.run(f"player {OTRO} spawn at {x + 8} {y} {z}", r"joined the game|Player .* spawn|Unknown|Incorrect")
        check(ctx.until(f"execute if entity @a[name={OTRO}]"), f"no aparece {OTRO}")
        s.send(srv.proc, f"gamemode survival {OTRO}")  # sin respuesta en la consola si ya lo tenía
        use(C)
        check(not items(C), "se repone con otro jugador a 8 bloques")
        ctx.run(f"tp {OTRO} {x + 100} {y + 20} {z}", r"Teleported")
        ctx.ticks(4)
        use(C)
        check(arrows(C), "con el otro jugador a 100 bloques no se repone")
        ctx.run(f"player {OTRO} kill", r"left the game|Unknown|Incorrect")

        # 4) lo que no se repone: contenido fijo, trofeo, vanilla
        otros = {"fijo": ((x + 4, y, z), 'minecraft:chest{components:{"minecraft:custom_data":{heraldia_cofre_unico:"atlantida"}},'
                          f'LootTable:"{TABLA}"}}'),
                 "trofeo": ((x + 6, y, z), 'minecraft:chest{LootTable:"heraldia:trofeos/castillo"}'),
                 "vanilla": ((x + 8, y, z), 'minecraft:chest{LootTable:"minecraft:chests/simple_dungeon"}')}
        for nombre, (p, bloque) in otros.items():
            ctx.run(f"setblock {at(p)} {bloque}", r"Changed the block|Could not set")
            ctx.run(f"tp {PLAYER} {p[0] - 2} {y} {z}", r"Teleported")
            ctx.ticks(2)
            use(p)
            check(not record(p), f"el cofre {nombre} queda apuntado para reponerse")
        ctx.run(f"tp {PLAYER} {x + 2} {y} {z}", r"Teleported")

        # 5) cofre ya generado y saqueado antes de activar la opción: se reconoce por la plantilla. Una ermita generada de
        #    verdad (/place structure no guarda el inicio en los chunks: getStructureWithPieceAt no la vería)
        m = ctx.run("execute positioned 0 64 0 run locate structure #heraldia:medianas/ermita",
                    r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
        check(bool(m.lastindex and m.group(1)), "/locate no encuentra ninguna ermita")
        cofre = None
        if m.lastindex and m.group(1):
            px, pz = int(m.group(1)), int(m.group(2))
            ex, ez = px >> 4 << 4, pz >> 4 << 4         # el origen de la pieza es la esquina del chunk de inicio
            forceload(ctx, ex - 32, ez - 32, ex + 31, ez + 31)
            check(wait_generated(ctx, ex, ez, "ermita"), f"la ermita de {px}, {pz} no se genera")
            lx, ly, lz = locales[0]
            for giro, f in GIROS.items():
                dx, dz = f(lx, lz)
                for cy in range(-20, 260):
                    p = (ex + dx, cy + ly, ez + dz)
                    if ctx.test(f'execute if block {at(p)} minecraft:chest{{LootTable:"{ERMITA_TABLA}"}}'):
                        cofre = p
                        break
                if cofre:
                    print(f"cofre de la ermita de {px}, {pz} en {cofre} (giro {giro})")
                    break
            check(cofre is not None, f"no se encuentra el cofre de la celda de la ermita de {px}, {pz}")
        if cofre:
            # «saqueado antes»: sin su tabla ni nada dentro, y sin apuntar
            ctx.run(f"data remove block {at(cofre)} LootTable", r"Modified block data")
            empty(cofre)
            cx, cy, cz = cofre
            ctx.run(f"fill {cx} {cy + 1} {cz} {cx} {cy + 2} {cz} minecraft:air", r"Successfully filled|No blocks")
            ctx.run(f"tp {PLAYER} {cx + 0.5} {cy + 1} {cz + 0.5}", r"Teleported")
            ctx.ticks(10)
            use(cofre)
            check(record(cofre, ERMITA_TABLA), "el cofre saqueado de la ermita no se reconoce por su plantilla")
            check(not items(cofre), "el cofre saqueado de la ermita se llena sin esperar")
            day()
            use(cofre)
            check(items(cofre), "el cofre de la ermita no se repone pasado el día")
        srv.stop()

        # 6) con la opción desactivada (por defecto), nada se apunta
        config(a.work, False)
        srv = Server(a.work, launcher)
        ctx = srv.ctx
        p = (x, y, z + 2)
        ctx.run(f"forceload add {x - 16} {z - 16} {x + 16} {z + 16}", r"Marked|force|already|[Aa]dded")
        ctx.run(f"player {PLAYER} spawn at {x + 2} {y} {z + 2}", r"joined the game|Player .* spawn|Unknown|Incorrect")
        ctx.until(f"execute if entity @a[name={PLAYER}]")
        for _ in range(s.PLACE_ATTEMPTS):
            m = ctx.run(f'setblock {at(p)} minecraft:chest{{LootTable:"{TABLA}"}}', r"Changed the block|Could not set|not loaded")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        use(p)
        check(arrows(p), "con la opción desactivada el cofre no se abre con su tabla")
        check(not record(p), "con la opción desactivada el cofre queda apuntado")
        bad = [b for b in ("Registry loading errors", "Failed to load datapacks") if b in ctx.log()]
        bad += [l.strip() for l in ctx.log().splitlines() if "Exception" in l and "heraldia" in l.lower()]
        check(not bad, f"errores en el log: {bad}")
    finally:
        srv.stop()
    print(f"botin_reponer: {ok} comprobaciones bien, {len(fails)} mal")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
