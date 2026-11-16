"""Dificultad configurable (dificultad.*) en un servidor dedicado 26.3 real, con reinicios y jugadores simulados (Carpet).

Uso: python3 tools/smoke/dificultad.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Invoca (con NBT, sin finalizeSpawn) zombis anclados (heraldia_anclado), un guardián (heraldia_guardian, vida base 60),
uno herido, un zombi sin etiquetas y un lobo anclado, y reinicia el mismo mundo con cada nivel:
  - heroica: el anclado tiene vida 40 y daño 4,5 (modificadores heraldia:dificultad_vida y _dano), el guardián 120, el
    herido conserva su proporción (10/20 -> 20/40), el zombi sin etiquetas y el lobo no cambian; el botín de una tabla de
    cofre de Heraldia (datapack de prueba, 10 flechas) sale x1,5 y un objeto con nombre o una tabla de otra carpeta, igual;
  - fácil (tras reiniciar: los ya generados se recalculan al cargar): 15, 45 y el herido 7,5/15; 7 u 8 flechas;
  - normal: todo como siempre (20, 60, herido 10/20, sin modificadores) y 10 flechas;
  - heroica con dificultad.escalar_por_jugadores: con 3 jugadores cerca, al recibir un golpe el anclado pasa a 60 de
    vida máxima (x2 x1,5); con 1, a 40.
"""
import argparse, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guia import Server
from trofeos import CARPET
from modrinth import fetch

X, Y, Z = 0, 100, 0
PACK = "heraldia_prueba_dificultad"
TABLA, OTRA = "heraldia:cofres/prueba_dificultad", "heraldia:pruebas/prueba_dificultad"
MOBS = {   # etiqueta de prueba: (tipo, etiquetas de Heraldia, vida base, vida inicial, dx)
    "p_anclado": ("zombie", ["heraldia_anclado", "heraldia_adulto"], 20, 20, 0),
    "p_guardian": ("zombie", ["heraldia_guardian", "heraldia_guardian.prueba", "heraldia_anclado", "heraldia_adulto"], 60, 60, 2),
    "p_herido": ("zombie", ["heraldia_anclado", "heraldia_adulto"], 20, 10, 4),
    "p_libre": ("zombie", [], 20, 20, 6),
    "p_lobo": ("wolf", ["heraldia_anclado"], 8, 8, 8),
}
NUM = r"(-?\d+(?:\.\d+)?)"


def datapack(work):
    root = os.path.join(work, "world", "datapacks", PACK)
    for d in ("cofres", "pruebas"):
        os.makedirs(os.path.join(root, "data", "heraldia", "loot_table", d), exist_ok=True)
    with open(os.path.join(root, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"description": "Heraldia: prueba de la dificultad", "min_format": 121, "max_format": 121}}, f)
    # formato de 26.3: «modifier» con «type» (no «functions»/«function», que se ignoran sin avisar)
    flechas = {"type": "minecraft:item", "name": "minecraft:arrow", "modifier": {"type": "minecraft:set_count", "count": 10}}
    palos = {"type": "minecraft:item", "name": "minecraft:stick", "modifier": [
        {"type": "minecraft:set_count", "count": 10},
        {"type": "minecraft:set_name", "target": "custom_name", "name": {"text": "Palo con nombre"}}]}
    tabla = {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [flechas]}, {"rolls": 1, "entries": [palos]}]}
    for d in ("cofres", "pruebas"):
        with open(os.path.join(root, "data", "heraldia", "loot_table", d, "prueba_dificultad.json"), "w") as f:
            json.dump(tabla, f)


def config(work, nivel, jugadores=False):
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    cfg["dificultad"] = {"nivel": nivel, "escalar_por_jugadores": jugadores}
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-dificultad"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    datapack(a.work)
    fails, ok = [], 0
    srv = None

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)
            print("FALLA:", msg)

    def arrancar(nivel, jugadores=False):
        nonlocal srv
        if srv:
            srv.stop()
        config(a.work, nivel, jugadores)
        srv = Server(a.work, launcher)
        return srv.ctx

    def sel(tag):
        return f"@e[tag={tag},limit=1]"

    def num(ctx, cmd):
        m = ctx.run(cmd, rf"(?:is|data:) {NUM}f?\b|No entity|[Nn]o modifier|has no|There is no|not found|Unknown|Can't find")
        return float(m.group(1)) if m.lastindex and m.group(1) else None

    def vida_max(ctx, tag):
        return num(ctx, f"attribute {sel(tag)} minecraft:max_health get")

    def vida(ctx, tag):
        return num(ctx, f"data get entity {sel(tag)} Health")

    def modificador(ctx, tag, attr, mod):
        return num(ctx, f"attribute {sel(tag)} minecraft:{attr} modifier value get heraldia:{mod}")

    def esperar_mobs(ctx):
        for tag in MOBS:
            if not ctx.until(f"execute if entity {sel(tag)}"):
                raise SystemExit(f"no aparece el mob {tag} tras arrancar")

    def mobs(ctx, nivel, esperado):
        """esperado: {tag: (vida máxima, vida)}"""
        for tag, (vm, v) in esperado.items():
            got_vm, got_v = vida_max(ctx, tag), vida(ctx, tag)
            check(got_vm is not None and abs(got_vm - vm) < 1e-3, f"{nivel}: {tag} con vida máxima {got_vm} (debe ser {vm})")
            check(got_v is not None and abs(got_v - v) < 1e-3, f"{nivel}: {tag} con vida {got_v} (debe ser {v})")

    def cuenta(ctx, item):
        """Cantidad del objeto `item` que hay en el suelo (una sola pila), o None."""
        e = f'@e[type=minecraft:item,x={X},y={Y + 1},z={Z + 6},distance=..4,nbt={{Item:{{id:"{item}"}}}},limit=1]'
        m = ctx.run(f"data get entity {e} Item.count", r"has the following entity data: (\d+)|No entity")
        return int(m.group(1)) if m.lastindex and m.group(1) else None

    def botin(ctx, nivel, flechas):
        """La tabla de cofre de Heraldia da `flechas` (conjunto de valores válidos); la otra y el palo con nombre, 10."""
        for tabla, want in ((TABLA, flechas), (OTRA, {10})):
            ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
            ctx.run(f"loot spawn {X} {Y + 3} {Z + 6} loot {tabla}", r"Dropped|No items")
            ctx.ticks(2)
            flechas_n = cuenta(ctx, "minecraft:arrow")
            check(flechas_n in want, f"{nivel}: {tabla} da {flechas_n} flechas (debe ser {sorted(want)})")
            palos_n = cuenta(ctx, "minecraft:stick")
            check(palos_n == 10, f"{nivel}: {tabla}: el palo con nombre sale con {palos_n} (debe ser 10)")
        ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")

    try:
        # heroica: se invocan los mobs (ENTITY_LOAD al añadirse al mundo)
        ctx = arrancar("heroica")
        ctx.run(f"forceload add {X - 16} {Z - 16} {X + 16} {Z + 16}", r"Marked|force|already|[Aa]dded")
        for _ in range(s.PLACE_ATTEMPTS):
            m = ctx.run(f"fill {X - 2} {Y - 1} {Z - 2} {X + 12} {Y - 1} {Z + 8} minecraft:stone", r"Successfully filled|No blocks|not loaded")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        ctx.run(f"fill {X - 2} {Y} {Z - 2} {X + 12} {Y + 3} {Z + 8} minecraft:air", r"Successfully filled|No blocks")
        for rule in ("spawn_mobs", "advance_time"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
        ctx.run("time set midnight", r"[Tt]ime|[Ss]et")      # de noche y con techo: los zombis no arden
        ctx.run(f"fill {X - 2} {Y + 4} {Z - 2} {X + 12} {Y + 4} {Z + 8} minecraft:stone", r"Successfully filled|No blocks")
        for tag, (tipo, tags, base, v, dx) in MOBS.items():
            etiquetas = ",".join(f'"{t}"' for t in tags + [tag])
            ctx.run(f'summon minecraft:{tipo} {X + dx} {Y} {Z} {{NoAI:1b,PersistenceRequired:1b,Silent:1b,Tags:[{etiquetas}],'
                    f'Health:{v}f,attributes:[{{id:"minecraft:max_health",base:{base}}}]}}', r"Summoned|Unable")
        esperar_mobs(ctx)
        mobs(ctx, "heroica", {"p_anclado": (40, 40), "p_guardian": (120, 120), "p_herido": (40, 20), "p_libre": (20, 20), "p_lobo": (8, 8)})
        dano = num(ctx, f"attribute {sel('p_anclado')} minecraft:attack_damage get")
        check(dano is not None and abs(dano - 4.5) < 1e-3, f"heroica: daño del anclado {dano} (debe ser 4,5)")
        check(modificador(ctx, "p_anclado", "max_health", "dificultad_vida") == 1.0, "heroica: sin modificador heraldia:dificultad_vida = 1")
        check(modificador(ctx, "p_anclado", "attack_damage", "dificultad_dano") == 0.5, "heroica: sin modificador heraldia:dificultad_dano = 0,5")
        check(modificador(ctx, "p_libre", "max_health", "dificultad_vida") is None, "heroica: el zombi sin etiquetas tiene modificador")
        botin(ctx, "heroica", {15})

        # fácil, tras reiniciar: los mobs ya generados se recalculan al cargar
        ctx = arrancar("facil")
        esperar_mobs(ctx)
        mobs(ctx, "fácil", {"p_anclado": (15, 15), "p_guardian": (45, 45), "p_herido": (15, 7.5), "p_libre": (20, 20), "p_lobo": (8, 8)})
        check(modificador(ctx, "p_anclado", "max_health", "dificultad_vida") == -0.25, "fácil: el modificador no es -0,25")
        botin(ctx, "fácil", {7, 8})

        # normal: exactamente como siempre
        ctx = arrancar("normal")
        esperar_mobs(ctx)
        mobs(ctx, "normal", {"p_anclado": (20, 20), "p_guardian": (60, 60), "p_herido": (20, 10), "p_libre": (20, 20), "p_lobo": (8, 8)})
        dano = num(ctx, f"attribute {sel('p_anclado')} minecraft:attack_damage get")
        check(dano is not None and abs(dano - 3) < 1e-3, f"normal: daño del anclado {dano} (debe ser 3)")
        for mod, attr in (("dificultad_vida", "max_health"), ("dificultad_dano", "attack_damage"), ("dificultad_jugadores", "max_health")):
            check(modificador(ctx, "p_anclado", attr, mod) is None, f"normal: queda el modificador {mod}")
        botin(ctx, "normal", {10})

        # heroica con más vida por jugadores cerca (al recibir un golpe)
        ctx = arrancar("heroica", jugadores=True)
        esperar_mobs(ctx)
        nombres = ["Testigo", "Aprendiz", "Escudero"]
        for i, n in enumerate(nombres):
            ctx.run(f"player {n} spawn at {X + i} {Y} {Z + 4}", r"joined the game|Player .* spawn|Unknown|Incorrect")
            check(ctx.until(f"execute if entity @a[name={n}]"), f"no aparece el jugador simulado {n}")
            s.send(srv.proc, f"gamemode creative {n}")  # sin respuesta en la consola si ya lo tenía
        ctx.run(f"damage {sel('p_anclado')} 1 minecraft:player_attack by Testigo", r"Applied|damage")
        ctx.ticks(2)
        vm = vida_max(ctx, "p_anclado")
        check(vm is not None and abs(vm - 60) < 1e-3, f"con 3 jugadores: vida máxima {vm} (debe ser 60)")
        check(modificador(ctx, "p_anclado", "max_health", "dificultad_jugadores") == 0.5, "con 3 jugadores: el modificador no es 0,5")
        for n in nombres[1:]:
            ctx.run(f"player {n} kill", r"left the game|Unknown|Incorrect")
            ctx.until(f"execute if entity @a[name={n}]", want=False)
        ctx.run(f"damage {sel('p_anclado')} 1 minecraft:player_attack by Testigo", r"Applied|damage")
        ctx.ticks(2)
        vm = vida_max(ctx, "p_anclado")
        check(vm is not None and abs(vm - 40) < 1e-3, f"con 1 jugador: vida máxima {vm} (debe ser 40)")
        vm = vida_max(ctx, "p_libre")
        check(vm == 20, f"el zombi sin etiquetas cambia: {vm}")
        log = ctx.log()
        bad = [b for b in ("Registry loading errors", "Failed to load datapacks") if b in log]
        bad += [l.strip() for l in log.splitlines() if "Exception" in l and "heraldia" in l.lower()]
        check(not bad, f"errores en el log: {bad}")
    finally:
        if srv:
            srv.stop()
    print(f"dificultad: {ok} comprobaciones bien, {len(fails)} mal")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
