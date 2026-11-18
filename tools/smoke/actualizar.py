"""Actualizaciones seguras (T46) en un servidor dedicado 26.3 real: /heraldia update analyze y apply con una «casa» puesta
a mano, los arreglos por versión y el panel de configuración en diálogos.

Uso: python3 tools/smoke/actualizar.py --jar build/libs/heraldia-X.jar [--work build/smoke-actualizar]
Dos arranques del mismo mundo (semilla de server_smoke, sin mobs nuevos ni ticks aleatorios y, al comparar, con el mundo
congelado: /tick freeze), con Carpet para un jugador simulado:
1. Se genera una zona de LADO x LADO chunks lejos del spawn, se pone a mano una «casa» (suelo de tablones, cama, cofre y
   mesa de trabajo) y unos bloques de oro de marca bajo tierra: unos a menos de 50 bloques de la casa y otros lejos. Se
   invoca un zombi bebé con el nombre de un guardián de la 0.1.0 (sin etiquetas): el arreglo lo vuelve adulto y anclado
   al cargarse, una vez.
   - analyze no cambia nada: los chunks de la zona, leídos de las regiones, son los mismos antes y después, y deja el
     informe, el mapa en texto y la imagen; protege la casa y propone regenerar chunks vírgenes;
   - se vuelve el zombi bebé a mano (data merge);
   - apply (desde la consola): pide confirmación con su id; al confirmar con copia, el servidor se para solo.
2. Al arrancar a mano: copia de seguridad, chunks vírgenes borrados e informe. Con el mundo congelado:
   - ningún chunk a 50 bloques o menos de la casa ha cambiado y las marcas de oro cercanas siguen;
   - alguna marca lejana ha desaparecido (su chunk virgen se ha regenerado);
   - el zombi sigue bebé (el arreglo no se repite: lleva la marca) hasta /heraldia update repair, que lo arregla
     (repair dry-run antes no cambia nada);
   - /heraldia config abre el diálogo (jugador simulado, operador) y su submenú, config set escribe el fichero y
     /heraldia language fija el idioma del jugador.
Código 0 si todo pasa.
"""
import argparse, glob, json, math, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s                       # noqa: E402
import mundo_existente as me                   # noqa: E402
from terralith_biomas import fetch             # noqa: E402
from trofeos import CARPET                     # noqa: E402

LADO, C0 = 20, 15                              # zona de chunks C0..C0+LADO-1 (bloques 240..559)
CASA = (396, 150, 396, 404, 150, 404)          # suelo de la casa (minX, y, minZ, maxX, y, maxZ), en el aire
MARGEN = 50
Y_MARCA = -50
CERCA = [(440, 400), (400, 440), (360, 360)]   # a menos de 50 bloques de la casa (en chunks protegidos)
LEJOS = [(520, 400), (520, 300), (300, 520), (280, 280), (540, 540)]   # a más de 100 bloques
ZOMBI = "prueba_arreglo"
JUGADOR = "Panel"


def cerca_de_casa(cx, cz):
    dx = max(0, CASA[0] - (cx * 16 + 15), cx * 16 - CASA[3])
    dz = max(0, CASA[2] - (cz * 16 + 15), cz * 16 - CASA[5])
    return math.hypot(dx, dz) <= MARGEN


def bloque(ctx, x, y, z, b):
    return ctx.test(f"execute if block {x} {y} {z} {b}")


def con_chunk(ctx, x, z, f):
    """Carga el chunk del bloque (forceload), hace f() y lo suelta."""
    ctx.run(f"forceload add {x} {z}", r"Marked|[Aa]dded|force|already")
    ctx.until(f"execute if loaded {x} 64 {z}", timeout=120)
    try:
        return f()
    finally:
        ctx.run(f"forceload remove {x} {z}", r"[Rr]emoved|[Uu]nmarked|force|not")


def foto(world, chunks):
    """Como mundo_existente.foto, con las referencias a estructuras sin orden: el juego las guarda en un conjunto y, al
    volver a guardar el chunk, pueden salir en otro orden (visto aquí: las mismas dos referencias de una mina, al revés)."""
    out = me.foto(world, chunks)
    for h in out.values():
        refs = (h.get("estructuras") or {}).get("References")
        if isinstance(refs, dict):
            h["estructuras"]["References"] = {k: sorted(v) if isinstance(v, list) else v for k, v in refs.items()}
    return out


def esperar(ctx, patron, timeout):
    """Como server_smoke.wait_for, pero también vale si la línea ya salió (p. ej. durante el arranque)."""
    m = re.search(patron, ctx.log())
    return m or s.wait_for(ctx.lines, patron, timeout, ctx.seen)


def esperar_desde(ctx, n0, patron, timeout):
    """La primera línea que case desde la línea n0 del log (también las que ya pasaron a ctx.seen), o la espera."""
    m = re.search(patron, "".join(ctx.seen[n0:]))
    return m or s.wait_for(ctx.lines, patron, timeout, ctx.seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-actualizar"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    world = os.path.join(a.work, "world")
    carpeta = os.path.join(world, "heraldia", "actualizar")
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    zona = me.cuadrado(C0, C0, LADO)
    cercanos = {c for c in zona if cerca_de_casa(*c)}
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)
            print("FALLA:", msg)
        return cond

    # ------------------------------------------------------------------ arranque 1
    proc, ctx = me.arrancar(a.work, launcher, cfg)
    try:
        ctx.run("gamerule advance_time false", r"Gamerule|set to|now")
        t0 = time.time()
        me.cargar(ctx, zona)
        print(f"zona de {len(zona)} chunks generada en {time.time() - t0:.0f} s")
        for x0, z0, x1, z1 in me.trozos(cercanos):
            ctx.run(f"forceload add {x0} {z0} {x1} {z1}", r"Marked|[Aa]dded|force|already")
        x0, y, z0, x1, _, z1 = CASA
        ctx.run(f"fill {x0} {y} {z0} {x1} {y} {z1} minecraft:oak_planks", r"Successfully filled|No blocks")
        ctx.run(f"setblock {x0 + 1} {y + 1} {z0 + 1} minecraft:red_bed[facing=south,part=foot]", r"Changed the block|Could not")
        ctx.run(f"setblock {x0 + 1} {y + 1} {z0 + 2} minecraft:red_bed[facing=south,part=head]", r"Changed the block|Could not")
        ctx.run(f"setblock {x1 - 1} {y + 1} {z0 + 1} minecraft:chest", r"Changed the block|Could not")
        ctx.run(f"setblock {x1 - 1} {y + 1} {z1 - 1} minecraft:crafting_table", r"Changed the block|Could not")
        for x, z in CERCA + LEJOS:
            con_chunk(ctx, x, z, lambda: ctx.run(f"setblock {x} {Y_MARCA} {z} minecraft:gold_block", r"Changed the block|Could not"))
        # un guardián de la 0.1.0: nombre traducible de Heraldia, persistente, sin etiquetas y bebé (/summon con NBT no
        # llama a finalizeSpawn, así que sale tal cual)
        ctx.run(f'summon minecraft:zombie 400 {y + 1} 400 {{IsBaby:1b,PersistenceRequired:1b,NoAI:1b,Tags:["{ZOMBI}"],'
                f'CustomName:{{translate:"heraldia.unicas.castillo.guardian",fallback:"Sir Aldric"}}}}',
                r"Summoned|Unable|Invalid")
        check(ctx.until(f"execute if entity @e[tag={ZOMBI},tag=heraldia_anclado,tag=heraldia_guardian,tag=heraldia_adulto]"),
              "el arreglo «marcas» no ha puesto las etiquetas al guardián antiguo")
        check(ctx.test(f"execute if entity @e[tag={ZOMBI},nbt={{IsBaby:0b}}]"), "el arreglo «bebes» no ha hecho adulto al guardián")
        arreglos_1 = len(re.findall(r"Heraldia: arreglos \{marcas=CAMBIA, bebes=CAMBIA", "".join(ctx.seen)))
        check(arreglos_1 == 1, f"el arreglo se ha aplicado {arreglos_1} veces al invocarlo (debía ser 1)")
        me.congelar(ctx)
        ctx.run("save-all flush", r"Saved the game|saved")
        antes = foto(world, zona)
        check(len(antes) == len(zona), f"solo {len(antes)} de {len(zona)} chunks guardados enteros")
        # analyze no cambia nada
        n0 = len(ctx.seen)
        ctx.run("heraldia update analyze", r"Analizando|Analysing|Unknown|Incorrect")
        m = esperar_desde(ctx, n0, r"update analyze: (\d+) chunks, (\d+) construcciones, (\d+) protegidos, (\d+) vírgenes \((\d+) se "
                       r"regenerarían\), (\d+) estructuras nuevas", 600)
        total, constr, prot, virg, regen = (int(m.group(i)) for i in range(1, 6))
        print(f"analyze: {total} chunks, {constr} construcciones, {prot} protegidos, {virg} vírgenes, {regen} a regenerar")
        check(total >= len(zona), f"analyze solo ha visto {total} chunks")
        check(constr >= 3, f"analyze no ve la casa ({constr} construcciones)")
        check(prot >= len(cercanos), f"analyze protege {prot} chunks, menos que los {len(cercanos)} a 50 bloques de la casa")
        check(regen > 0, "analyze no propone regenerar ningún chunk virgen")
        ctx.run("save-all flush", r"Saved the game|saved")
        check(not me.comparar("analyze", antes, foto(world, zona)), "analyze ha cambiado chunks: "
              + "; ".join(me.comparar("analyze", antes, foto(world, zona))[:3]))
        for patron in ("analisis-*.txt", "mapa-*.txt", "mapa-*.png"):
            check(glob.glob(os.path.join(carpeta, patron)), f"analyze no ha dejado {patron} en {carpeta}")
        mapas = glob.glob(os.path.join(carpeta, "mapa-*.txt"))
        if mapas:
            texto = open(mapas[0], encoding="utf-8").read()
            check("#" in texto and "R" in texto, "el mapa en texto no marca la casa (#) y lo que se regenera (R)")
        check(not os.path.exists(os.path.join(carpeta, "plan.json")), "analyze ha dejado un plan")
        # el guardián vuelve a ser bebé (a mano): el arreglo no debe repetirse al recargarlo
        ctx.run(f"data merge entity @e[tag={ZOMBI},limit=1] {{IsBaby:1b}}", r"Modified|Unable|Nothing")
        # sin chunks forzados al volver a arrancar: si no, sus fluidos corren antes de congelar el mundo (cambios del juego)
        for x0, z0, x1, z1 in me.trozos(cercanos):
            ctx.run(f"forceload remove {x0} {z0} {x1} {z1}", r"[Rr]emoved|[Uu]nmarked|force|not")
        # apply: confirmación con id, con copia
        n0 = len(ctx.seen)
        ctx.run("heraldia update apply", r"Analizando|Analysing|Unknown|Incorrect")
        m = esperar_desde(ctx, n0, r"update apply confirm (\w+) backup", 600)
        ident = m.group(1)
        check(not os.path.exists(os.path.join(carpeta, "plan.json")), "apply sin confirmar ya ha dejado el plan")
        s.send(proc, f"heraldia update apply confirm {ident} backup")
        esperar_desde(ctx, n0, r"update apply confirmado .*el servidor se para", 60)
        check(os.path.exists(os.path.join(carpeta, "plan.json")), "al confirmar no queda el plan")
        proc.wait(timeout=180)
        print("el servidor se ha parado solo tras confirmar")
    finally:
        if proc.poll() is None:
            proc.kill()
    log1 = "".join(ctx.seen)

    # ------------------------------------------------------------------ arranque 2 (a mano)
    proc, ctx = me.arrancar(a.work, launcher, cfg)
    try:
        esperar(ctx, r"update apply terminado", 300)
        log2 = "".join(ctx.seen)
        m = re.search(r"update apply: (\d+) chunks vírgenes borrados", log2)
        borrados = int(m.group(1)) if m else 0
        check(borrados > 0, "al arrancar no se ha borrado ningún chunk virgen")
        check(re.search(r"copia de seguridad de [1-9]\d* ficheros", log2), "no se ha hecho la copia de seguridad")
        check(glob.glob(os.path.join(carpeta, "copia-*", "region", "r.*.mca")), "no está la copia de las regiones")
        check(glob.glob(os.path.join(carpeta, "informe-*.txt")), "no está el informe de apply")
        check(glob.glob(os.path.join(carpeta, "hecho-*.json")) and not os.path.exists(os.path.join(carpeta, "plan.json")),
              "el plan no ha quedado como hecho")
        i_cs = log2.index("chunks vírgenes borrados") if "chunks vírgenes borrados" in log2 else -1
        i_prep = log2.find("Preparing")
        check(i_cs >= 0 and (i_prep < 0 or i_cs < i_prep), "los chunks se borraron después de cargar el mundo")
        me.congelar(ctx)
        me.cargar(ctx, zona, congelado=True)
        ctx.run("save-all flush", r"Saved the game|saved")
        despues = foto(world, cercanos)
        dif = me.comparar("apply", {c: antes[c] for c in cercanos if c in antes}, despues)
        check(not dif, f"apply ha cambiado chunks a menos de {MARGEN} bloques de la casa: " + "; ".join(dif[:3]))
        for x, z in CERCA:
            check(con_chunk(ctx, x, z, lambda: bloque(ctx, x, Y_MARCA, z, "minecraft:gold_block")),
                  f"la marca de oro de {x}, {z} (a menos de 50 bloques de la casa) ha desaparecido")
        quitadas = [(x, z) for x, z in LEJOS if not con_chunk(ctx, x, z, lambda: bloque(ctx, x, Y_MARCA, z, "minecraft:gold_block"))]
        print(f"marcas lejanas regeneradas: {quitadas} de {LEJOS}")
        check(quitadas, "ninguna marca lejana ha desaparecido: no se ha regenerado ningún chunk virgen")
        check(con_chunk(ctx, *CASA[:1], CASA[2], lambda: bloque(ctx, CASA[0] + 1, CASA[1] + 1, CASA[2] + 1, "minecraft:red_bed")),
              "la cama de la casa ha desaparecido")
        # los arreglos no se repiten: el guardián sigue bebé hasta repair
        ctx.run(f"forceload add 400 400", r"Marked|[Aa]dded|force|already")
        ctx.until("execute if loaded 400 64 400", timeout=120)
        check(ctx.until(f"execute if entity @e[tag={ZOMBI}]"), "no está el guardián de prueba")
        check(ctx.test(f"execute if entity @e[tag={ZOMBI},nbt={{IsBaby:1b}}]"), "el arreglo se ha vuelto a aplicar al recargar")
        veces = len(re.findall(r"Heraldia: arreglos \{marcas=CAMBIA", log1 + "".join(ctx.seen)))
        check(veces == 1, f"el arreglo de marcas se ha aplicado {veces} veces (debía ser 1)")
        n0 = len(ctx.seen)
        ctx.run("heraldia update repair dry-run", r"Prueba|Dry run|Unknown|Incorrect")
        m = esperar_desde(ctx, n0, r"update repair dry-run: (\d+) mobs de plantilla revisados, (\d+) cambios (\{.*\})", 30)
        check("bebes=1/0" in m.group(3), f"repair dry-run no ve el bebé: {m.group(3)}")
        check(ctx.test(f"execute if entity @e[tag={ZOMBI},nbt={{IsBaby:1b}}]"), "repair dry-run ha cambiado el guardián")
        n0 = len(ctx.seen)
        ctx.run("heraldia update repair", r"Arreglos|Fixes|Unknown|Incorrect")
        esperar_desde(ctx, n0, r"update repair: \d+ mobs de plantilla revisados, [1-9]\d* cambios", 30)
        check(ctx.test(f"execute if entity @e[tag={ZOMBI},nbt={{IsBaby:0b}}]"), "repair no ha hecho adulto al guardián")
        n0 = len(ctx.seen)
        ctx.run("heraldia update repair dry-run", r"Prueba|Dry run|Unknown|Incorrect")
        m = esperar_desde(ctx, n0, r"update repair dry-run: (\d+) mobs de plantilla revisados, (\d+) cambios", 30)
        check(m.group(2) == "0", f"tras repair aún quedan {m.group(2)} cambios (no es idempotente)")
        # panel de configuración y preferencias
        ctx.run(f"player {JUGADOR} spawn at 0 100 0", r"joined the game|Player .* spawn|Unknown|Incorrect")
        check(ctx.until(f"execute if entity @a[name={JUGADOR}]"), "no aparece el jugador simulado (Carpet)")
        ctx.run(f"op {JUGADOR}", r"Made .* operator|Nothing changed")
        ctx.run(f"execute as {JUGADOR} run heraldia config", rf"panel de configuración abierto \({JUGADOR}, principal\)|Unknown|Incorrect")
        check(re.search(rf"panel de configuración abierto \({JUGADOR}, principal\)", "".join(ctx.seen)), "/heraldia config no abre el diálogo")
        ctx.run(f"execute as {JUGADOR} run heraldia config menu combate", rf"abierto \({JUGADOR}, combate\)|Unknown|Incorrect")
        check(re.search(rf"abierto \({JUGADOR}, combate\)", "".join(ctx.seen)), "/heraldia config menu combate no abre el submenú")
        ctx.run("heraldia config set arena.max_mobs_vivos 30", r"guardadas por|Valor no válido|Unknown|Incorrect")
        with open(os.path.join(a.work, "config", "heraldia.json"), encoding="utf-8") as f:
            check(json.load(f).get("arena", {}).get("max_mobs_vivos") == 30, "config set no ha escrito el fichero")
        ctx.run(f"execute as {JUGADOR} run heraldia language fr_fr", rf"idioma de {JUGADOR}: fr_fr|Unknown|Incorrect")
        check(re.search(rf"idioma de {JUGADOR}: fr_fr", "".join(ctx.seen)), "/heraldia language no fija el idioma")
        check(re.search(r"mundo generado con la versión", "".join(ctx.seen)), "no se dice con qué versión se generó el mundo")
        me.parar(proc, ctx)
    finally:
        if proc.poll() is None:
            proc.kill()
    if fails:
        print(f"{len(fails)} fallos")
        return 1
    print("actualizar: todo bien")
    return 0


if __name__ == "__main__":
    sys.exit(main())
