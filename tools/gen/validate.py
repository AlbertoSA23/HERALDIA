"""Validación contra los registros reales de Minecraft 26.3 (resumen de misode/mcmeta, rama 26.3-summary)."""
import json, os
from core import parse_state

BLOCKS, ITEMS, ENTITIES = {}, set(), set()
# El juego suma 12 bloques de adaptación al terreno al radio y rechaza el paquete entero si pasa de 128.
TERRAIN_ADAPTATION_MARGIN, MAX_RADIUS_WITH_MARGIN, MAX_JIGSAW_SIZE = 12, 128, 20


def load_registries(summary_dir):
    """Carga bloques, objetos y entidades del resumen de mcmeta; falla con un mensaje claro si falta."""
    blocks_file = os.path.join(summary_dir, "blocks", "data.json")
    registries_file = os.path.join(summary_dir, "registries", "data.json")
    for f in (blocks_file, registries_file):
        if not os.path.isfile(f):
            raise SystemExit(f"No encuentro {f}. Clona misode/mcmeta (rama 26.3-summary) y pasa su ruta con --registries.")
    with open(blocks_file, encoding="utf-8") as f:
        BLOCKS.update(json.load(f))
    with open(registries_file, encoding="utf-8") as f:
        reg = json.load(f)
    ITEMS.update(reg["item"])
    ENTITIES.update(reg["entity_type"])


def validate_structures(out):
    """Comprueba sobre los JSON escritos los límites de jigsaw que hacen que el juego rechace el paquete."""
    errs = []
    sdir = os.path.join(out, "data")
    for root, _, files in os.walk(sdir):
        rel = root.replace(os.sep, "/").split("/worldgen/")[-1]
        if rel != "structure" and not rel.startswith("structure/"):     # incluye worldgen/structure/unicas
            continue
        for fn in files:
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                s = json.load(f)
            if s.get("type") != "minecraft:jigsaw":
                continue
            if s["max_distance_from_center"] + TERRAIN_ADAPTATION_MARGIN > MAX_RADIUS_WITH_MARGIN:
                errs.append(f"{fn}: max_distance_from_center {s['max_distance_from_center']} + 12 > 128")
            if not 0 < s["size"] <= MAX_JIGSAW_SIZE:
                errs.append(f"{fn}: size {s['size']} fuera de 1..20")
    return errs


def check_state(s):
    bid, props = parse_state(s)
    b = bid.replace("minecraft:", "")
    if b not in BLOCKS:
        return f"bloque inexistente: {bid}"
    allowed = BLOCKS[b][0]
    for k, v in props.items():
        if k not in allowed:
            return f"propiedad {k} no válida en {bid}"
        if v not in allowed[k]:
            return f"valor {k}={v} no válido en {bid}"
    return None


def validate_registry(reg):
    errs = {}
    for t in reg.templates.values():
        for pos, (st, nbt) in t.blocks.items():
            e = check_state(st)
            if e:
                errs.setdefault(e, []).append(t.name)
            if nbt and nbt.get("id") == "minecraft:jigsaw":
                e = check_state(nbt["final_state"])
                if e:
                    errs.setdefault("final_state " + e, []).append(t.name)
        for x, y, z, n in t.entities:
            if n["id"].replace("minecraft:", "") not in ENTITIES:
                errs.setdefault("entidad " + n["id"], []).append(t.name)
        for j in t.jigsaws:
            p = j["pool"]
            if p != "minecraft:empty" and p not in reg.pools:
                errs.setdefault("pool inexistente " + p, []).append(t.name)
    for pid, p in reg.pools.items():
        if p["fallback"] != "minecraft:empty" and p["fallback"] not in reg.pools:
            errs.setdefault("fallback inexistente " + p["fallback"], []).append(pid)
        for loc, w, proj, proc in p["elements"]:
            if loc and loc not in reg.templates:
                errs.setdefault("plantilla inexistente " + loc, []).append(pid)
    return errs


def validate_loot(tables):
    errs = []
    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "minecraft:item":
                n = o["name"].replace("minecraft:", "")
                if n not in ITEMS:
                    errs.append("objeto inexistente " + n)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tables)
    return errs
