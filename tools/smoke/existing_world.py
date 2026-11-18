"""Mundo existente: lo ya generado no cambia al actualizar Heraldia ni su configuración (servidor dedicado 26.3 real).

Uso: python3 tools/smoke/existing_world.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-mundo-existente"
Tres arranques del mismo mundo (semilla de server_smoke), con la regla de ticks aleatorios a 0, sin mobs nuevos y, en los
arranques 2 y 3, el mundo congelado (/tick freeze: se cargan y generan chunks, pero no corren los ticks de bloques,
fluidos ni entidades), así que lo único que puede cambiar un chunk ya generado es el mod:
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
import argparse, glob, io, json, os, queue, re, shutil, struct, subprocess, sys, threading, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s           # noqa: E402
import nbtlib                      # noqa: E402

SIDE_A, RING_B, RING_C = 8, 4, 3          # chunks
# «Antes»: lo que no existía en la versión con la que se generó el mundo, apagado.
CONFIG_BEFORE = {"unicas": {"rejilla_compatible": True}, "aldeas": {"caminos": {"activado": False}},
                "medianas": {"activadas": False}, "minas": {"entradas": {"activado": False}, "vanilla": {"multiplicador": 1.0}},
                "faros": {"activado": False}, "naufragios": {"activado": False},
                "arena": {"activado": False}, "botin": {"reponer": {"activado": False}}, "guia": {"entregar_al_entrar": False}}
# Tercer arranque: casi todo distinto de lo de por defecto.
CONFIG_OTHER = {"unicas": {"rejilla_compatible": False, "distancia_minima": {"bloques": 1500}},
               "aldeas": {"porcentaje_grandes": 60, "caminos": {"activado": True, "ancho": 5, "distancia_maxima_bloques": 4000},
                          "vida": {"tablon": False}},
               "medianas": {"activadas": False}, "minas": {"entradas": {"separacion_bloques": 1024}, "vanilla": {"multiplicador": 5.0}},
               "faros": {"separacion_bloques": 256}, "naufragios": {"separacion_bloques": 256},
               "golems": {"limpieza": False}, "jefes": {"fases": {"activado": False}, "refuerzos": {"activado": False}},
               "botin": {"reponer": {"activado": True, "dias": 1}},
               "dificultad": {"nivel": "heroica", "escalar_por_jugadores": True, "escalar_botin": False},
               "arena": {"activado": True, "generar_en_mundos_nuevos": True}, "guia": {"entregar_al_entrar": True}}
# Campos que cambian solos al guardar o con el reloj del mundo (no son del contenido del chunk).
VOLATILE_CHUNK = {"LastUpdate", "InhabitedTime", "block_ticks", "fluid_ticks", "PostProcessing", "isLightOn",
                   "blending_data", "Status", "DataVersion", "xPos", "zPos", "yPos"}
VOLATILE_BLOCK = {"keepPacked"}


# ------------------------------------------------------------------ regiones
def _region(world, folder, cx, cz):
    for base in (os.path.join(world, "dimensions", "minecraft", "overworld"), world):
        p = os.path.join(base, folder, f"r.{cx >> 5}.{cz >> 5}.mca")
        if os.path.isfile(p):
            return p
    return None


def read_chunk(world, cx, cz, folder="region"):
    """NBT de un chunk (o del fichero de entidades, con carpeta="entities"), o None si no está guardado."""
    path = _region(world, folder, cx, cz)
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


def _blueprint(v):
    """NBT de nbtlib a tipos de Python comparables con == (los arrays de longs, que nbtlib da como numpy, a listas)."""
    if isinstance(v, dict):
        if len(v) == 1 and "" in v:               # elemento de una lista mixta (26.3 los envuelve así)
            return _blueprint(v[""])
        return {str(k): _blueprint(x) for k, x in v.items()}
    if isinstance(v, (nbtlib.tag.ByteArray, nbtlib.tag.IntArray, nbtlib.tag.LongArray)):
        return [int(x) for x in v]
    if isinstance(v, (list, tuple)):
        return [_blueprint(x) for x in v]
    if isinstance(v, nbtlib.tag.String):
        return str(v)
    if isinstance(v, (nbtlib.tag.Float, nbtlib.tag.Double)):
        return float(v)
    if isinstance(v, int):
        return int(v)
    return v


def _stripped(d, remove):
    return {k: v for k, v in d.items() if k not in remove}


def footprint(n):
    """Lo que no debe cambiar de un chunk guardado: {apartado: valor comparable}."""
    out = {}
    sections_list = {}
    for sec in n.get("sections", []):
        bs = sec.get("block_states")
        sections_list[int(sec["Y"])] = (_blueprint(bs) if bs is not None else None, _blueprint(sec.get("biomes")))
    out["secciones"] = sections_list
    be = {}
    for b in n.get("block_entities", []):
        d = _blueprint(b)
        be[(d.get("x"), d.get("y"), d.get("z"))] = _stripped(d, VOLATILE_BLOCK)
    out["bloques_con_datos"] = be
    out["alturas"] = _blueprint(n.get("Heightmaps"))
    out["estructuras"] = _blueprint(n.get("structures"))
    out["resto"] = _stripped({k: _blueprint(v) for k, v in n.items()}, VOLATILE_CHUNK | {"sections", "block_entities", "Heightmaps", "structures"})
    return out


def states(bs):
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
    per, mask, out = 64 // bits, (1 << bits) - 1, []
    for v in bs["data"]:
        v &= (1 << 64) - 1
        for _ in range(per):
            out.append(pal[v & mask])
            v >>= bits
            if len(out) == 4096:
                return out
    return out


def differences(a, b):
    """Textos con lo que cambia entre dos huellas del mismo chunk ([] si nada)."""
    e = []
    sa, sb = a["secciones"], b["secciones"]
    for y in sorted(set(sa) | set(sb)):
        if y not in sa or y not in sb:
            e.append(f"sección {y} {'añadida' if y in sb else 'quitada'}")
            continue
        (ba, bioa), (bb, biob) = sa[y], sb[y]
        if ba != bb:
            ea, eb = states(ba), states(bb)
            if ea != eb:
                changes = [(i, ea[i][0], eb[i][0]) for i in range(4096) if ea[i] != eb[i]]
                i, dimension_of, a_ = changes[0]
                e.append(f"sección {y}: {len(changes)} bloques cambian (p. ej. x={i & 15} y={y * 16 + (i >> 8)} z={(i >> 4) & 15}: {dimension_of} -> {a_})")
        if bioa != biob:
            e.append(f"sección {y}: cambian los biomas")
    ba, bb = a["bloques_con_datos"], b["bloques_con_datos"]
    for p in sorted(set(ba) | set(bb), key=str):
        if ba.get(p) != bb.get(p):
            forward, idb = (ba.get(p) or {}).get("id"), (bb.get(p) or {}).get("id")
            keys = sorted(k for k in set(ba.get(p) or {}) | set(bb.get(p) or {}) if (ba.get(p) or {}).get(k) != (bb.get(p) or {}).get(k))
            e.append(f"bloque con datos {p} ({forward} -> {idb}) cambia: {keys}")
    for k in ("alturas", "estructuras", "resto"):
        if a[k] != b[k]:
            keys = sorted(set(a[k] or {}) | set(b[k] or {}))
            e.append(f"{k} cambia: {[c for c in keys if (a[k] or {}).get(c) != (b[k] or {}).get(c)]}")
    return e


def snapshot(world, chunks):
    """{(cx, cz): huella} de los chunks guardados enteros (Status full); los que no lo están, fuera."""
    out = {}
    for c in chunks:
        n = read_chunk(world, *c)
        if n is not None and str(n.get("Status", "")) in ("minecraft:full", "full"):
            out[c] = footprint(n)
    return out


def uuids(world, chunks):
    """{uuid: id} de las entidades guardadas en esos chunks."""
    out = {}
    for c in chunks:
        n = read_chunk(world, *c, folder="entities")
        for ent in (n or {}).get("Entities", []):
            u = tuple(int(x) for x in ent.get("UUID", []))
            out[u] = str(ent.get("id"))
    return out


def compare(name, before, after):
    """Fallos (textos) de comparar dos fotos de los mismos chunks."""
    failures = []
    for c in sorted(before):
        if c not in after:
            failures.append(f"{name}: el chunk {c} ya no está guardado entero")
            continue
        d = differences(before[c], after[c])
        if d:
            failures.append(f"{name}: el chunk {c} cambia: " + "; ".join(d[:4]) + (f" (y {len(d) - 4} más)" if len(d) > 4 else ""))
    return failures


# ------------------------------------------------------------------ servidor
def start_up(work, launcher, cfg):
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


def halt(proc, ctx):
    ctx.run("save-all flush", r"Saved the game|saved")
    if proc.poll() is None:
        s.send(proc, "stop")
        proc.wait(timeout=180)
    while True:          # lo que escribió al parar (la línea de coste de los caminos) también a ctx.seen
        try:
            line = ctx.lines.get(timeout=10)
        except queue.Empty:
            return
        if line is None:
            return
        ctx.seen.append(line)


def square(c0x, c0z, side):
    return {(x, z) for x in range(c0x, c0x + side) for z in range(c0z, c0z + side)}


FORCELOAD_MAX = 16          # /forceload acepta como mucho 256 chunks por orden: trozos de 16 x 16


def fragments(chunks):
    """Rectángulos (x0, z0, x1, z1) en bloques, de como mucho FORCELOAD_MAX x FORCELOAD_MAX chunks, que cubren los chunks."""
    xs, zs = [c[0] for c in chunks], [c[1] for c in chunks]
    out = []
    for cx in range(min(xs), max(xs) + 1, FORCELOAD_MAX):
        for cz in range(min(zs), max(zs) + 1, FORCELOAD_MAX):
            ex, ez = min(cx + FORCELOAD_MAX - 1, max(xs)), min(cz + FORCELOAD_MAX - 1, max(zs))
            out.append((cx * 16, cz * 16, ex * 16 + 15, ez * 16 + 15))
    return out


def freeze(ctx):
    """/tick freeze: el mundo sigue cargando y generando chunks (y cargando sus entidades, que es cuando el mod las toca),
    pero no corren los ticks de bloques, fluidos ni entidades. Sin esto, la lava y el agua de las cuevas de los bordes
    siguen fluyendo, los aldeanos abren puertas y las bóvedas de las cámaras de pruebas cambian sus datos: cambios del
    juego, no del mod, que taparían lo que se quiere ver."""
    ctx.run("tick freeze", r"[Ff]rozen|freeze|[Gg]ame")


def load_data(ctx, chunks, frozen=False):
    """Fuerza y carga los chunks (los genera si no lo están) y espera a que estén todos; luego los suelta."""
    for x0, z0, x1, z1 in fragments(chunks):
        ctx.run(f"forceload add {x0} {z0} {x1} {z1}", r"Marked|[Aa]dded|force|already")
    for cx, cz in sorted(chunks):
        if not ctx.until(f"execute if loaded {cx * 16} 64 {cz * 16}", timeout=600):
            raise SystemExit(f"el chunk {cx}, {cz} no se carga")
    if frozen:
        time.sleep(5)                 # con el mundo congelado el reloj no avanza: se deja terminar lo que quede
    else:
        ctx.ticks(60)
    for x0, z0, x1, z1 in fragments(chunks):
        ctx.run(f"forceload remove {x0} {z0} {x1} {z1}", r"[Rr]emoved|[Uu]nmarked|force|not")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-mundo-existente"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    world = os.path.join(a.work, "world")
    failures = []

    # 1. versión anterior
    proc, ctx = start_up(a.work, launcher, CONFIG_BEFORE)
    try:
        m = ctx.run("locate structure #heraldia:aldeas", r"is at \[(-?\d+), ~, (-?\d+)\]|Could not find")
        if not m.lastindex:
            raise SystemExit("no se localiza ninguna aldea Heraldia")
        ax, az = int(m.group(1)) >> 4, int(m.group(2)) >> 4
        print(f"Zona A: {SIDE_A} x {SIDE_A} chunks alrededor de la aldea en chunk {ax}, {az}")
        A = square(ax - SIDE_A // 2, az - SIDE_A // 2, SIDE_A)
        load_data(ctx, A)
        ctx.run("tick sprint 1300", r"[Ss]print|ticks")
        s.wait_for(ctx.lines, r"[Ss]print completed|[Ss]print .*(finished|ended)|ticks per second", 300, ctx.seen)
        if ctx.gametime() < 1300:
            failures.append(f"el mundo no llega a 1.300 ticks ({ctx.gametime()})")
    finally:
        halt(proc, ctx)
    snapshot_a, ents_a = snapshot(world, A), uuids(world, A)
    print(f"Zona A: {len(snapshot_a)} de {len(A)} chunks guardados enteros, {len(ents_a)} entidades")
    if len(snapshot_a) < len(A) * 3 // 4:
        failures.append(f"solo {len(snapshot_a)} chunks de A guardados enteros")
    backup = os.path.join(a.work, "world-tras-1")         # para mirar a mano qué cambió si falla
    shutil.rmtree(backup, ignore_errors=True)
    shutil.copytree(world, backup)

    # 2. versión nueva con la configuración por defecto
    B = square(ax - SIDE_A // 2 - RING_B, az - SIDE_A // 2 - RING_B, SIDE_A + 2 * RING_B)
    proc, ctx = start_up(a.work, launcher, None)
    try:
        if not re.search(r"arena: mundo existente", ctx.log()):
            failures.append("la arena no reconoce el mundo existente (línea «arena: mundo existente» del log)")
        freeze(ctx)
        load_data(ctx, B, frozen=True)
    finally:
        halt(proc, ctx)
    with open(os.path.join(a.work, "config", "heraldia.json"), encoding="utf-8") as f:
        by_default = json.load(f)
    print("Configuración por defecto creada:", json.dumps({k: v for k, v in by_default.items() if not k.startswith("_")}, ensure_ascii=False)[:400])
    failures += compare("arranque 2 (por defecto)", snapshot_a, snapshot(world, A))
    ents = uuids(world, B)
    losses = {u: t for u, t in ents_a.items() if u not in ents}
    if losses:
        failures.append(f"arranque 2: {len(losses)} entidades de la zona A ya no están: {sorted(set(losses.values()))}")
    snapshot_b = snapshot(world, B - A)
    print(f"Anillo B: {len(snapshot_b)} chunks nuevos guardados enteros")
    if re.search(r"arena: (mundo nuevo|colocada|sitio propuesto)", ctx.log()):
        failures.append("arranque 2: la arena se construye sola en un mundo existente")
    m = re.search(r"caminos: \d+ chunks, (\d+) junto a una ruta \((\d+) columnas", ctx.log())
    if not m or int(m.group(2)) == 0:
        failures.append("arranque 2: no sale ningún camino en el anillo nuevo (la prueba no vería si toca lo viejo)")
    else:
        print(f"Anillo B: {m.group(1)} chunks junto a una ruta, {m.group(2)} columnas de camino puestas")

    # 3. otra configuración
    C = square(ax - SIDE_A // 2 - RING_B - RING_C, az - SIDE_A // 2 - RING_B - RING_C,
                 SIDE_A + 2 * (RING_B + RING_C))
    proc, ctx = start_up(a.work, launcher, CONFIG_OTHER)
    try:
        freeze(ctx)
        load_data(ctx, C, frozen=True)
        if re.search(r"arena: (mundo nuevo|colocada|sitio propuesto)", ctx.log()):
            failures.append("arranque 3: la arena se construye sola en un mundo existente")
    finally:
        halt(proc, ctx)
    failures += compare("arranque 3 (otra configuración), zona A", snapshot_a, snapshot(world, A))
    failures += compare("arranque 3 (otra configuración), anillo B", snapshot_b, snapshot(world, B - A))
    ents = uuids(world, C)
    losses = {u: t for u, t in ents_a.items() if u not in ents}
    if losses:
        failures.append(f"arranque 3: {len(losses)} entidades de la zona A ya no están: {sorted(set(losses.values()))}")

    for f_ in failures:
        print("[FALLO]", f_)
    print("PRUEBA MUNDO EXISTENTE " + ("OK" if not failures else f"FALLIDA ({len(failures)} fallos)"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
