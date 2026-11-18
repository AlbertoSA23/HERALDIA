"""Validación contra los registros reales de Minecraft 26.3 (resumen de misode/mcmeta, rama 26.3-summary)."""
import json, os
from core import parse_state, ADULT_TAG, BABY_ZOMBIE, BABY_NO_PROTECTION, ANCHORED_TAG, PICKS_UP_LOOT

BLOCKS, ITEMS, ENTITIES, TRIGGERS, ENTITY_PREDICATES = {}, set(), set(), set(), set()
# El juego suma 12 bloques de adaptación al terreno al radio y rechaza el paquete entero si pasa de 128.
DATA = {"enchantment": set(), "trim_pattern": set(), "trim_material": set(), "banner_pattern": set()}   # registros de datos
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
    TRIGGERS.update(reg["trigger_type"])
    ENTITY_PREDICATES.update(reg["entity_sub_predicate_type"])
    for k, v in DATA.items():
        v.update(reg.get(k, ()))


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
            for name, j in jigsaws(fn, s):
                if j["max_distance_from_center"] + TERRAIN_ADAPTATION_MARGIN > MAX_RADIUS_WITH_MARGIN:
                    errs.append(f"{name}: max_distance_from_center {j['max_distance_from_center']} + 12 > 128")
                if not 0 < j["size"] <= MAX_JIGSAW_SIZE:
                    errs.append(f"{name}: size {j['size']} fuera de 1..20")
    return errs


def jigsaws(fn, s):
    """Configuración jigsaw de una estructura: la propia (minecraft:jigsaw) o la que envuelve heraldia:aldea."""
    if s.get("type") == "minecraft:jigsaw":
        return [(fn, s)]
    if s.get("type") == "heraldia:aldea":
        return [(f"{fn} (aldea)", s["aldea"])]
    return []


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
    from uniques._common.pieces import GUARDIAN_TAG
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
            if n["id"] in BABY_ZOMBIE and ADULT_TAG not in (n.get("Tags") or []):
                errs.setdefault(f"{n['id']} sin la etiqueta {ADULT_TAG} (saldría bebé el 5 %: core.adulto)", []).append(t.name)
            tags = n.get("Tags") or []
            if ANCHORED_TAG not in tags and (n["id"] in PICKS_UP_LOOT or GUARDIAN_TAG in tags):
                why = "guardián" if GUARDIAN_TAG in tags else "recogería objetos"
                errs.setdefault(f"{n['id']} sin la etiqueta {ANCHORED_TAG} ({why}: core.anclado)", []).append(t.name)
            if n["id"] in BABY_NO_PROTECTION:
                errs.setdefault(f"{n['id']} en una plantilla (saldría bebé el 20 %, sin protección)", []).append(t.name)
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
            elif o.get("type") == "minecraft:set_enchantments":
                errs.extend("encantamiento inexistente " + e for e in o["enchantments"] if _short(e) not in DATA["enchantment"])
            elif o.get("type") == "minecraft:set_components":
                c = o["components"]
                trim = c.get("minecraft:trim") or {}
                refs = [("trim_pattern", trim.get("pattern")), ("trim_material", trim.get("material"))]
                refs += [("banner_pattern", b["pattern"]) for b in c.get("minecraft:banner_patterns", ())]
                errs.extend(f"{k} inexistente {v}" for k, v in refs if v and _short(v) not in DATA[k])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tables)
    return errs


FRAMES = ("task", "goal", "challenge")


def _short(i):
    return i.removeprefix("minecraft:")


def validate_advancements(out, ns="heraldia"):
    """Comprueba los logros escritos (data/<ns>/advancement) contra el formato de 26.3 (en 26.3 los logros son un
    registro: uno ilegible puede tumbar la carga): padre, disparadores, requisitos, icono, marco, fondo de la raíz,
    claves de texto en es_es y en_us, y que existan las estructuras, etiquetas, tablas, objetos y mobs que citan."""
    errs = []
    base = os.path.join(out, "data", ns, "advancement")
    langs = {}
    for lang in ("es_es", "en_us"):
        with open(os.path.join(out, "assets", ns, "lang", f"{lang}.json"), encoding="utf-8") as f:
            langs[lang] = json.load(f)

    def exists(kind, rid):
        tag = rid.startswith("#")
        n, path = rid.lstrip("#").split(":", 1) if ":" in rid else ("minecraft", rid.lstrip("#"))
        if n != ns:
            return True   # vanilla: lo valida el juego
        rel = {"structure": ("tags/worldgen/structure" if tag else "worldgen/structure"),
               "loot_table": "loot_table", "advancement": "advancement", "entity_type": "tags/entity_type"}[kind]
        return os.path.isfile(os.path.join(out, "data", n, rel, path + ".json"))

    def text(name, c):
        if not isinstance(c, dict) or "translate" not in c:
            return [f"{name}: texto sin clave de traducción"]
        e = [f"{name}: falta la clave {c['translate']} en {lang}" for lang, t in langs.items()
             if c["translate"] not in t and not c["translate"].startswith(("advancements.minecraft", "item.minecraft"))]
        return e + [x for a in c.get("with", []) for x in text(name, a)]

    def refs(name, o):
        e = []
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "structures" and isinstance(v, str) and not exists("structure", v):
                    e.append(f"{name}: estructura o etiqueta inexistente {v}")
                elif k == "loot_tables" and isinstance(v, str) and not exists("loot_table", v):
                    e.append(f"{name}: tabla de botín inexistente {v}")
                elif k == "minecraft:entity_type" and (not exists("entity_type", v) if v.startswith("#")
                                                       else _short(v) not in ENTITIES):
                    e.append(f"{name}: entidad inexistente {v}")
                elif k == "items" and isinstance(v, str) and _short(v) not in ITEMS:
                    e.append(f"{name}: objeto inexistente {v}")
                elif k == "predicate" and isinstance(v, dict):
                    e += [f"{name}: predicado de entidad desconocido {p}" for p in v if _short(p) not in ENTITY_PREDICATES]
                e += refs(name, v)
        elif isinstance(o, list):
            for v in o:
                e += refs(name, v)
        return e

    for root, _, files in os.walk(base):
        for fn in files:
            name = os.path.relpath(os.path.join(root, fn), base).replace(os.sep, "/")
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                a = json.load(f)
            unknown = set(a) - {"parent", "criteria", "display", "requirements", "rewards", "sends_telemetry_event"}
            if unknown:
                errs.append(f"{name}: campos desconocidos {sorted(unknown)}")
            crit = a.get("criteria") or {}
            if not crit:
                errs.append(f"{name}: sin criterios")
            for c, d in crit.items():
                if _short(d.get("trigger", "")) not in TRIGGERS:
                    errs.append(f"{name}: disparador desconocido {d.get('trigger')} en {c}")
            req = a.get("requirements", [[c] for c in crit])
            named = [c for group in req for c in group]
            if any(not g for g in req) or set(named) != set(crit):
                errs.append(f"{name}: requisitos {req} no cubren exactamente los criterios {sorted(crit)}")
            if "parent" in a and not exists("advancement", a["parent"]):
                errs.append(f"{name}: padre inexistente {a['parent']}")
            d = a.get("display")
            if d:
                if _short(d.get("icon", {}).get("id", "")) not in ITEMS:
                    errs.append(f"{name}: icono inexistente {d.get('icon')}")
                if d.get("frame", "task") not in FRAMES:
                    errs.append(f"{name}: marco {d.get('frame')} no es {FRAMES}")
                if "parent" not in a and not d.get("background"):
                    errs.append(f"{name}: la raíz de la pestaña necesita fondo (background)")
                errs += text(name, d.get("title")) + text(name, d.get("description"))
            xp = a.get("rewards", {}).get("experience", 0)
            # Solo experiencia (Decisiones del dueño), salvo los encargos del tablón de las aldeas (tablon.py), que
            # pagan con su tabla de recompensa (esmeraldas y algún objeto con nombre)
            allowed = {"experience", "loot"} if name.startswith("aldeas/encargos/") else {"experience"}
            if set(a.get("rewards", {})) - allowed or not isinstance(xp, int) or xp < 0:
                errs.append(f"{name}: recompensa no permitida {a['rewards']} (solo experiencia)")
            errs += [f"{name}: tabla de recompensa inexistente {t}" for t in a.get("rewards", {}).get("loot", [])
                     if not exists("loot_table", t)]
            errs += refs(name, crit)
    return errs
