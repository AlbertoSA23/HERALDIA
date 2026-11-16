"""Mundo existente: lo ya generado no cambia al actualizar Heraldia ni su configuración (servidor dedicado 26.3 real).

Uso: python3 tools/smoke/mundo_existente.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-mundo-existente"
Tres arranques del mismo mundo (semilla de server_smoke), con la regla de ticks aleatorios a 0 y sin mobs nuevos (así lo
único que puede cambiar un chunk ya generado es el mod):
1. «Versión anterior»: configuración con lo nuevo de la 0.1.0 sin publicar apagado (caminos, medianas, entradas a mina
   y multiplicador de minas vanilla 1, arena, botín que se repone; rejilla_compatible activada) y la Guía sin entregar.
   Se genera la zona A (LADO_A x LADO_A chunks) alrededor de la aldea Heraldia más cercana al 0,0 y se dejan pasar más
   de 1.200 ticks (tick sprint): para la arena, el mundo ya no es nuevo.
2. Se borra config/heraldia.json (como al instalar la versión nueva: se crea con los valores por defecto). Se carga la
   zona A y se genera el anillo B alrededor (caminos, medianas y minas pueden salir en él). La arena no se construye
   sola (log «mundo existente»).
3. Configuración distinta en casi todo (otro nivel de dificultad, sin medianas, minas x5, caminos más anchos, botín que
   se repone, jefes sin fases, rejilla_compatible desactivada...): se cargan A y B y se genera el anillo C.
Tras cada arranque se comparan con la copia guardada los chunks de A (y, tras el 3, también los de B), leyendo las
regiones (.mca): los bloques de cada sección, los bloques con datos (id y NBT, sin los campos que cambian solos), las
alturas, los biomas y los inicios y referencias de estructuras. Las entidades: cada UUID de la zona sigue en el mundo
(los mobs pueden andar). Código 0 si todo pasa.
"""
import argparse, glob, io, json, os, queue, re, shutil, struct, subprocess, sys, threading, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s           # noqa: E402
import nbtlib                      # noqa: E402

LADO_A, ANILLO_B, ANILLO_C = 8, 4, 3          # chunks
# «Antes»: lo que no existía en la versión con la que se generó el mundo, apagado.
CONFIG_ANTES = {"unicas": {"rejilla_compatible": True}, "aldeas": {"caminos": {"activado": False}},
                "medianas": {"activadas": False}, "minas": {"entradas": {"activado": False}, "vanilla": {"multiplicador": 1.0}},
                "arena": {"activado": False}, "botin": {"reponer": {"activado": False}}, "guia": {"entregar_al_entrar": False}}
# Tercer arranque: casi todo distinto de lo de por defecto.
CONFIG_OTRA = {"unicas": {"rejilla_compatible": False, "distancia_minima": {"bloques": 1500}},
               "aldeas": {"porcentaje_grandes": 60, "caminos": {"activado": True, "ancho": 5, "distancia_maxima_bloques": 4000},
                          "vida": {"tablon": False}},
               "medianas": {"activadas": False}, "minas": {"entradas": {"separacion_bloques": 1024}, "vanilla": {"multiplicador": 5.0}},
               "golems": {"limpieza": False}, "jefes": {"fases": {"activado": False}, "refuerzos": {"activado": False}},
               "botin": {"reponer": {"activado": True, "dias": 1}},
               "dificultad": {"nivel": "heroica", "escalar_por_jugadores": True, "escalar_botin": False},
               "arena": {"activado": True, "generar_en_mundos_nuevos": True}, "guia": {"entregar_al_entrar": True}}
# Campos que cambian solos al guardar o con el reloj del mundo (no son del contenido del chunk).
VOLATILES_CHUNK = {"LastUpdate", "InhabitedTime", "block_ticks", "fluid_ticks", "PostProcessing", "isLightOn",
                   "blending_data", "Status", "DataVersion", "xPos", "zPos", "yPos"}
VOLATILES_BLOQUE = {"keepPacked"}


# ------------------------------------------------------------------ regiones
def _region(world, carpeta, cx, cz):
    for base in (os.path.join(world, "dimensions", "minecraft", "overworld"), world):
        p = os.path.join(base, carpeta, f"r.{cx >> 5}.{cz >> 5}.mca")
        if os.path.isfile(p):
            return p
    return None


def leer_chunk(world, cx, cz, carpeta="region"):
    """NBT de un chunk (o del fichero de entidades, con carpeta="entities"), o None si no está guardado."""
    path = _region(world, carpeta, cx, cz)
    if not path:
        return None
    with open(path, "rb") as f:
        data = f.read()
    i = (cx & 31) + (cz & 31) * 32
    off = int.from_bytes(data[i * 4:i * 4 + 3], "big") * 4096
    if not off:
        return None
    length, comp = struct.unpack(">IB", data[off:off + 5])
    raw = data[off + 5:off + 4 + length]
    if comp == 2:
        raw = zlib.decompress(raw)
    elif comp == 1:
        import gzip
        raw = gzip.decompress(raw)
    elif comp != 3:
        raise SystemExit(f"compresión {comp} de la región no soportada (region-file-compression=deflate)")
    return nbtlib.File.parse(io.BytesIO(raw))


def _plano(v):
    """NBT de nbtlib a tipos de Python comparables con == (los arrays de longs, que nbtlib da como numpy, a listas)."""
    if isinstance(v, dict):
        if len(v) == 1 and "" in v:               # elemento de una lista mixta (26.3 los envuelve así)
            return _plano(v[""])
        return {str(k): _plano(x) for k, x in v.items()}
    if isinstance(v, (nbtlib.tag.ByteArray, nbtlib.tag.IntArray, nbtlib.tag.LongArray)):
        return [int(x) for x in v]
    if isinstance(v, (list, tuple)):
        return [_plano(x) for x in v]
    if isinstance(v, nbtlib.tag.String):
        return str(v)
    if isinstance(v, (nbtlib.tag.Float, nbtlib.tag.Double)):
        return float(v)
    if isinstance(v, int):
        return int(v)
    return v


def _sin(d, quitar):
    return {k: v for k, v in d.items() if k not in quitar}


def huella(n):
    """Lo que no debe cambiar de un chunk guardado: {apartado: valor comparable}."""
    out = {}
    secciones = {}
    for sec in n.get("sections", []):
        bs = sec.get("block_states")
        secciones[int(sec["Y"])] = (_plano(bs) if bs is not None else None, _plano(sec.get("biomes")))
    out["secciones"] = secciones
    be = {}
    for b in n.get("block_entities", []):
        d = _plano(b)
        be[(d.get("x"), d.get("y"), d.get("z"))] = _sin(d, VOLATILES_BLOQUE)
    out["bloques_con_datos"] = be
    out["alturas"] = _plano(n.get("Heightmaps"))
    out["estructuras"] = _plano(n.get("structures"))
    out["resto"] = _sin({k: _plano(v) for k, v in n.items()}, VOLATILES_CHUNK | {"sections", "block_entities", "Heightmaps", "structures"})
    return out


def estados(bs):
    """Lista de 4096 estados (nombre + propiedades) de una sección, para comparar aunque cambie el orden de la paleta."""
    if bs is None:
        return None
    # 26.3: un estado sin propiedades es una cadena («minecraft:stone»; en una lista mixta, {"": ...}, que quita
    # _plano) y uno con propiedades, {id, properties} (antes de 26.3, {Name, Properties})
    pal = [(p, ()) if isinstance(p, str) else (p.get("Name", p.get("id")),
                                                tuple(sorted((p.get("Properties") or p.get("properties") or {}).items())))
           for p in bs["palette"]]
    if len(pal) == 1 or "data" not in bs:
        return [pal[0]] * 4096
    bits = max(4, (len(pal) - 1).bit_length())
    por, mask, out = 64 // bits, (1 << bits) - 1, []
    for v in bs["data"]:
        v &= (1 << 64) - 1
        for _ in range(por):
            out.append(pal[v & mask])
            v >>= bits
            if len(out) == 4096:
                return out
    return out


def diferencias(a, b):
    """Textos con lo que cambia entre dos huellas del mismo chunk ([] si nada)."""
    e = []
    sa, sb = a["secciones"], b["secciones"]
    for y in sorted(set(sa) | set(sb)):
        if y not in sa or y not in sb:
            e.append(f"sección {y} {'añadida' if y in sb else 'quitada'}")
            continue
        (ba, bioa), (bb, biob) = sa[y], sb[y]
        if ba != bb:
            ea, eb = estados(ba), estados(bb)
            if ea != eb:
                cambios = [(i, ea[i][0], eb[i][0]) for i in range(4096) if ea[i] != eb[i]]
                i, de, a_ = cambios[0]
                e.append(f"sección {y}: {len(cambios)} bloques cambian (p. ej. x={i & 15} y={y * 16 + (i >> 8)} z={(i >> 4) & 15}: {de} -> {a_})")
        if bioa != biob:
            e.append(f"sección {y}: cambian los biomas")
    ba, bb = a["bloques_con_datos"], b["bloques_con_datos"]
    for p in sorted(set(ba) | set(bb), key=str):
        if ba.get(p) != bb.get(p):
            ida, idb = (ba.get(p) or {}).get("id"), (bb.get(p) or {}).get("id")
            claves = sorted(k for k in set(ba.get(p) or {}) | set(bb.get(p) or {}) if (ba.get(p) or {}).get(k) != (bb.get(p) or {}).get(k))
            e.append(f"bloque con datos {p} ({ida} -> {idb}) cambia: {claves}")
    for k in ("alturas", "estructuras", "resto"):
        if a[k] != b[k]:
            claves = sorted(set(a[k] or {}) | set(b[k] or {}))
            e.append(f"{k} cambia: {[c for c in claves if (a[k] or {}).get(c) != (b[k] or {}).get(c)]}")
    return e


def foto(world, chunks):
    """{(cx, cz): huella} de los chunks guardados enteros (Status full); los que no lo están, fuera."""
    out = {}
    for c in chunks:
        n = leer_chunk(world, *c)
        if n is not None and str(n.get("Status", "")) in ("minecraft:full", "full"):
            out[c] = huella(n)
    return out


def uuids(world, chunks):
    """{uuid: id} de las entidades guardadas en esos chunks."""
    out = {}
    for c in chunks:
        n = leer_chunk(world, *c, carpeta="entities")
        for ent in (n or {}).get("Entities", []):
            u = tuple(int(x) for x in ent.get("UUID", []))
            out[u] = str(ent.get("id"))
    return out


def comparar(nombre, antes, despues):
    """Fallos (textos) de comparar dos fotos de los mismos chunks."""
    fallos = []
    for c in sorted(antes):
        if c not in despues:
            fallos.append(f"{nombre}: el chunk {c} ya no está guardado entero")
            continue
        d = diferencias(antes[c], despues[c])
        if d:
            fallos.append(f"{nombre}: el chunk {c} cambia: " + "; ".join(d[:4]) + (f" (y {len(d) - 4} más)" if len(d) > 4 else ""))
    return fallos


# ------------------------------------------------------------------ servidor
def arrancar(work, launcher, cfg):
    path = os.path.join(work, "config", "heraldia.json")
    if cfg is None:
        if os.path.exists(path):
            os.remove(path)
    else:
        with open(path, "w") as f:
            json.dump(cfg, f)
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
    ctx = s.Context(proc, lines, seen)
    ctx.run("gamerule spawn_mobs false", r"Gamerule|set to|now")
    ctx.run("gamerule random_tick_speed 0", r"Gamerule|set to|now")
    return proc, ctx


def parar(proc, ctx):
    ctx.run("save-all flush", r"Saved the game|saved")
    if proc.poll() is None:
        s.send(proc, "stop")
        proc.wait(timeout=180)


def cuadrado(c0x, c0z, lado):
    return {(x, z) for x in range(c0x, c0x + lado) for z in range(c0z, c0z + lado)}


def cargar(ctx, chunks):
    """Fuerza y carga los chunks (los genera si no lo están) y espera a que estén todos; luego los suelta."""
    xs, zs = [c[0] for c in chunks], [c[1] for c in chunks]
    x0, z0, x1, z1 = min(xs) * 16, min(zs) * 16, max(xs) * 16 + 15, max(zs) * 16 + 15
    ctx.run(f"forceload add {x0} {z0} {x1} {z1}", r"Marked|[Aa]dded|force|already")
    for cx, cz in sorted(chunks):
        if not ctx.until(f"execute if loaded {cx * 16} 64 {cz * 16}", timeout=600):
            raise SystemExit(f"el chunk {cx}, {cz} no se carga")
    ctx.ticks(60)
    ctx.run(f"forceload remove {x0} {z0} {x1} {z1}", r"[Rr]emoved|[Uu]nmarked|force|not")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-mundo-existente"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    world = os.path.join(a.work, "world")
    fallos = []

    # 1. versión anterior
    proc, ctx = arrancar(a.work, launcher, CONFIG_ANTES)
    try:
        m = ctx.run("locate structure #heraldia:aldeas", r"is at \[(-?\d+), ~, (-?\d+)\]|Could not find")
        if not m.lastindex:
            raise SystemExit("no se localiza ninguna aldea Heraldia")
        ax, az = int(m.group(1)) >> 4, int(m.group(2)) >> 4
        print(f"Zona A: {LADO_A} x {LADO_A} chunks alrededor de la aldea en chunk {ax}, {az}")
        A = cuadrado(ax - LADO_A // 2, az - LADO_A // 2, LADO_A)
        cargar(ctx, A)
        ctx.run("tick sprint 1300", r"[Ss]print|ticks")
        s.wait_for(ctx.lines, r"[Ss]print completed|[Ss]print .*(finished|ended)|ticks per second", 300, ctx.seen)
        if ctx.gametime() < 1300:
            fallos.append(f"el mundo no llega a 1.300 ticks ({ctx.gametime()})")
    finally:
        parar(proc, ctx)
    foto_a, ents_a = foto(world, A), uuids(world, A)
    print(f"Zona A: {len(foto_a)} de {len(A)} chunks guardados enteros, {len(ents_a)} entidades")
    if len(foto_a) < len(A) * 3 // 4:
        fallos.append(f"solo {len(foto_a)} chunks de A guardados enteros")
    copia = os.path.join(a.work, "world-tras-1")         # para mirar a mano qué cambió si falla
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(world, copia)

    # 2. versión nueva con la configuración por defecto
    B = cuadrado(ax - LADO_A // 2 - ANILLO_B, az - LADO_A // 2 - ANILLO_B, LADO_A + 2 * ANILLO_B)
    proc, ctx = arrancar(a.work, launcher, None)
    try:
        if not re.search(r"arena: mundo existente", ctx.log()):
            fallos.append("la arena no reconoce el mundo existente (línea «arena: mundo existente» del log)")
        cargar(ctx, B)
    finally:
        parar(proc, ctx)
    with open(os.path.join(a.work, "config", "heraldia.json"), encoding="utf-8") as f:
        por_defecto = json.load(f)
    print("Configuración por defecto creada:", json.dumps({k: v for k, v in por_defecto.items() if not k.startswith("_")}, ensure_ascii=False)[:400])
    fallos += comparar("arranque 2 (por defecto)", foto_a, foto(world, A))
    ents = uuids(world, B)
    perdidas = {u: t for u, t in ents_a.items() if u not in ents}
    if perdidas:
        fallos.append(f"arranque 2: {len(perdidas)} entidades de la zona A ya no están: {sorted(set(perdidas.values()))}")
    foto_b = foto(world, B - A)
    print(f"Anillo B: {len(foto_b)} chunks nuevos guardados enteros")
    if re.search(r"arena: (mundo nuevo|colocada|sitio propuesto)", ctx.log()):
        fallos.append("arranque 2: la arena se construye sola en un mundo existente")

    # 3. otra configuración
    C = cuadrado(ax - LADO_A // 2 - ANILLO_B - ANILLO_C, az - LADO_A // 2 - ANILLO_B - ANILLO_C,
                 LADO_A + 2 * (ANILLO_B + ANILLO_C))
    proc, ctx = arrancar(a.work, launcher, CONFIG_OTRA)
    try:
        cargar(ctx, C)
        if re.search(r"arena: (mundo nuevo|colocada|sitio propuesto)", ctx.log()):
            fallos.append("arranque 3: la arena se construye sola en un mundo existente")
    finally:
        parar(proc, ctx)
    fallos += comparar("arranque 3 (otra configuración), zona A", foto_a, foto(world, A))
    fallos += comparar("arranque 3 (otra configuración), anillo B", foto_b, foto(world, B - A))
    ents = uuids(world, C)
    perdidas = {u: t for u, t in ents_a.items() if u not in ents}
    if perdidas:
        fallos.append(f"arranque 3: {len(perdidas)} entidades de la zona A ya no están: {sorted(set(perdidas.values()))}")

    for f_ in fallos:
        print("[FALLO]", f_)
    print("PRUEBA MUNDO EXISTENTE " + ("OK" if not fallos else f"FALLIDA ({len(fallos)} fallos)"))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
