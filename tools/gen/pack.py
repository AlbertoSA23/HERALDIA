"""Construye todas las piezas, pools y JSON del datapack."""
import json, os, random, shutil
import unicas
import medianas
import minas
from unicas._comun import botin
from core import Template, nsid, NS
from lint import passable
from themes import THEMES, FAMILIES
from houses import make_house, PROFS_HOUSE
from streets import (straight, crossroad, terminator_end, watchtower, gate, plaza, avenue, decor_piece, P)
from specials import SPECIALS, VARIANTS
from fillers import filler, villager_piece, golem_piece, rug_piece
import tablon
import tratos
import paralelo

SPARE = 22        # peso de "cama libre" en las casas

ALL_PROFS = ["armorer", "butcher", "cartographer", "cleric", "farmer", "fisherman", "fletcher", "leatherworker",
             "librarian", "mason", "shepherd", "toolsmith", "weaponsmith"]

AVENUES = {"a": ("church", "townhall"), "b": ("market", "tavern"), "c": ("blacksmith", "library"),
           "d": ("farm", None)}  # derecha de D: posada (el puerto de la costa va aparte, en la orilla)


def fix_supports(t):
    """Faroles colgantes: si no hay techo justo encima, se cuelgan con cadena hasta el techo;
    si no hay techo cerca, se apoyan o se retiran."""
    for (x, y, z), (st, nbt) in list(t.blocks.items()):
        if "lantern[" in st and "hanging=true" in st:
            above = t.get(x, y + 1, z)
            if above and not passable(above):
                continue
            for k in range(1, 9):
                b = t.get(x, y + k, z)
                if b and not passable(b):
                    for kk in range(1, k):
                        t.set(x, y + kk, z, "iron_chain[axis=y]")
                    break
            else:
                below = t.get(x, y - 1, z)
                if below and not passable(below):
                    t.set(x, y, z, st.replace("hanging=true", "hanging=false"))
                else:
                    t.clear(x, y, z)


class Registry:
    def __init__(self):
        self.templates = {}       # nombre -> Template
        self.pools = {}           # id -> dict(elements=[(loc|None, weight, projection, processors)], fallback)
        self.kinds = {}           # nombre plantilla -> tipo (house, special:x, filler, street...)
        self.warnings = []
        self.historia = {}        # id de única -> cofres con la tabla de su pliego (HISTORIA["cofre"])
        self.guardianes = {}      # id de única -> {tipo de mob: tabla de muerte original} (tag_guardians, trofeos)

    def add(self, t, kind):
        fix_supports(t)
        t.normalize()
        x0, y0, z0, x1, y1, z1 = t.bounds()
        sx, sy, sz = t.size()
        for j in t.jigsaws:
            f = j["orientation"].split("_")[0]
            x, y, z = j["pos"]
            if j["name"] in ("heraldia:entrance", "heraldia:avenue") and z != 0:
                self.warnings.append(f"{t.name}: entrada no está en el borde (z={z})")
            if j["name"] in ("heraldia:side", "heraldia:street", "heraldia:avenue", "heraldia:entrance"):
                ok = {"north": z == 0, "south": z == sz - 1, "west": x == 0, "east": x == sx - 1}[f]
                if not ok:
                    self.warnings.append(f"{t.name}: conector {j['name']} {f} en {j['pos']} no está en la cara de la caja {sx, sy, sz}")
            st = t.get(x, y, z)
            if st is None or "jigsaw" not in st:
                self.warnings.append(f"{t.name}: jigsaw sobrescrito en {j['pos']}")
        self.templates[t.name] = t
        self.kinds[t.name] = kind
        return t.name

    def pool(self, pid, elements, fallback="minecraft:empty"):
        self.pools[nsid(pid)] = dict(elements=elements, fallback=nsid(fallback) if fallback != "minecraft:empty" else fallback)


VARIANT_WEIGHTS = (2, 1, 1, 1, 1, 1, 1, 1)   # la original algo más frecuente que cada variante nueva


def function_signature(t):
    """Lo que hace un edificio especial: huecos de aldeano y gólem (con su pool), conectores a otras piezas,
    tablas de botín, campanas y puestos de trabajo (cada uno da oficio a un aldeano; salvo los toneles, que en todas
    partes son también almacén y adorno). Todas las variantes de un especial deben tener la misma."""
    from collections import Counter
    from build import WORKSTATION
    jobs = {b: p for p, b in WORKSTATION.items()}
    sig = Counter()
    for j in t.jigsaws:
        if j["name"] != "heraldia:entrance":
            sig[("jigsaw", j["name"], j["pool"])] += 1
    for st, nbt in t.blocks.values():
        if nbt and nbt.get("LootTable"):
            sig[("botín", str(nbt["LootTable"]))] += 1
        b = st.split("[")[0].replace("minecraft:", "")
        if b == "bell":
            sig[("campana",)] += 1
        b = "cauldron" if b.endswith("_cauldron") else b
        if b in jobs and b != "barrel":
            sig[("oficio", jobs[b])] += 1
    return sig


def variant_errors(reg, names):
    base = function_signature(reg.templates[names[0]])
    return [f"{n}: no hace lo mismo que {names[0]} ({function_signature(reg.templates[n]) - base} de más, "
            f"{base - function_signature(reg.templates[n])} de menos)"
            for n in names[1:] if function_signature(reg.templates[n]) != base]


def build_theme(reg, th, seed):
    rng = random.Random(seed)
    tid = th["id"]
    street_proc = nsid(f"{tid}/street")
    bld_proc = nsid(f"{tid}/building")
    # ---- calles
    els = []
    for i, (fn, w) in enumerate([(lambda n: straight(th, rng, n, 16), 4), (lambda n: straight(th, rng, n, 16), 2),
                                 (lambda n: straight(th, rng, n, 10), 3), (lambda n: crossroad(th, rng, n, "x"), 4),
                                 (lambda n: crossroad(th, rng, n, "t"), 5), (lambda n: crossroad(th, rng, n, "l"), 2)]):
        name = reg.add(fn(f"{tid}/streets/s{i}"), "street")
        els.append((name, w, "terrain_matching", street_proc))
    reg.pool(f"{tid}/streets", els, fallback=f"{tid}/terminators")
    els = [(reg.add(terminator_end(th, rng, f"{tid}/terminators/end"), "street"), 10, "terrain_matching", street_proc),
           (reg.add(watchtower(th, rng, f"{tid}/terminators/tower", stone=th["wall_style"] != "logcabin"), "tower"), 1, "rigid", bld_proc),
           (reg.add(watchtower(th, rng, f"{tid}/terminators/tower_b", stone=th["wall_style"] != "logcabin", with_golem=False), "tower"), 1, "rigid", bld_proc),
           (reg.add(gate(th, rng, f"{tid}/terminators/gate"), "gate"), 1, "rigid", bld_proc)]
    reg.pool(f"{tid}/terminators", els)
    # ---- decoración pequeña
    els = []
    for k, w in [("lamp", 5), ("lamp_tall", 2), ("flower", 2)]:
        els.append((reg.add(decor_piece(th, rng, f"{tid}/decor/{k}", k), "decor"), w, "rigid", None))
    els.append((None, 4, "rigid", None))
    reg.pool(f"{tid}/decor", els, fallback=f"{tid}/decor")
    # ---- casas
    els = []
    profs = PROFS_HOUSE[:]
    rng.shuffle(profs)
    n = 0
    for size, count, w in (("small", 4, 3), ("medium", 5, 3), ("large", 3, 2)):
        for i in range(count):
            prof = profs[n % len(profs)]
            n += 1
            t = make_house(th, rng, f"{tid}/houses/{size}_{i}", size, prof)
            els.append((reg.add(t, "house"), w, "rigid", bld_proc))
    fills = list(dict.fromkeys(list(th["decor"]) + ["well", "garden"]))
    for k in fills:
        t = filler(th, rng, f"{tid}/fillers/{k}", k)
        els.append((reg.add(t, "filler"), 1, "rigid", bld_proc))
    reg.pool(f"{tid}/houses", els)
    # ---- especiales
    # la costa tiene posada en la avenida como las demás; su puerto (caseta + muelle) lo pone aparte, en la orilla,
    # AldeaStructure (Java), que usa los pools special/port y port_pier
    # cada especial tiene VARIANTS[kind] variantes (la 0 es la original, con el rng común del estilo para que no
    # cambie; las demás con su propio rng determinista) y el pool las sortea con VARIANT_WEIGHTS
    for kind in ("church", "townhall", "market", "tavern", "blacksmith", "library", "farm", "inn", "port", "cemetery", "mill"):
        if kind == "port" and th["family"] != "costa":
            continue
        els = []
        for v in range(VARIANTS.get(kind, 1)):
            vrng = rng if v == 0 else random.Random(f"{seed}/{tid}/{kind}/{v}")
            t = SPECIALS[kind](th, vrng, f"{tid}/specials/{kind}" + ("" if v == 0 else f"_{'abcdefgh'[v]}"), v=v)
            els.append((reg.add(t, "special:" + kind), VARIANT_WEIGHTS[v] if VARIANTS.get(kind, 1) > 1 else 1,
                        "rigid", bld_proc))
        reg.warnings += variant_errors(reg, [e[0] for e in els])
        pid = f"{tid}/{kind}" if kind in ("cemetery", "mill") else f"{tid}/special/{kind}"
        reg.pool(pid, els)
    if th["family"] == "costa":
        t = SPECIALS["port_pier"](th, rng, f"{tid}/specials/port_pier")
        reg.pool(f"{tid}/port_pier", [(reg.add(t, "special:port_pier"), 1, "terrain_matching", nsid(f"{tid}/pier"))])
    # ---- avenidas
    for a, (lft, rgt) in AVENUES.items():
        if a == "d":
            rgt = "inn"
        t = avenue(th, rng, f"{tid}/avenues/{a}", P(th, f"special/{lft}"), P(th, f"special/{rgt}"))
        reg.pool(f"{tid}/avenue_{a}", [(reg.add(t, "avenue"), 1, "terrain_matching", street_proc)])
    # ---- tablón de encargos (colgado de la plaza)
    tablon.build(reg, th)
    # ---- plaza
    reg.pool(f"{tid}/plaza", [(reg.add(plaza(th, rng, f"{tid}/plaza/std"), "plaza"), 1, "rigid", bld_proc)])
    reg.pool(f"{tid}/plaza_grande", [(reg.add(plaza(th, rng, f"{tid}/plaza/grande", grande=True), "plaza"), 1, "rigid", bld_proc)])


def build_common(reg):
    for vtype in ("plains", "taiga", "snow", "desert", "savanna", "jungle", "swamp"):
        un = reg.add(villager_piece(vtype, f"villagers/{vtype}/unemployed", prof="none", employed=False), "villager")
        spare = reg.add(villager_piece(vtype, f"villagers/{vtype}/spare_bed"), "bed")
        rug = reg.add(rug_piece(vtype, f"villagers/{vtype}/rug"), "rug")
        for prof in ALL_PROFS:
            e = reg.add(villager_piece(vtype, f"villagers/{vtype}/e_{prof}", prof=prof), "villager")
            nb = reg.add(villager_piece(vtype, f"villagers/{vtype}/nb_{prof}", prof=prof, bed=False), "villager_nobed")
            # casas: 24 % con aldeano (75 % con oficio) y 14 % cama libre (camas ~1,2x aldeanos)
            # el fallback apunta al propio pool para que también se pueblen las piezas de profundidad máxima
            p = f"villagers/{vtype}/{prof}"
            reg.pool(p, [(e, 8, "rigid", None), (un, 4, "rigid", None),
                         (spare, 30, "rigid", None), (rug, 58, "rigid", None)], fallback=p)
            # aldeas grandes (alias en la estructura): algo más de población
            pg = f"villagers/{vtype}/{prof}_grande"
            reg.pool(pg, [(e, 16, "rigid", None), (un, 6, "rigid", None),
                          (spare, 27, "rigid", None), (rug, 51, "rigid", None)], fallback=pg)
            reg.pool(f"villagers/{vtype}/fixed_{prof}", [(e, 1, "rigid", None)], fallback=f"villagers/{vtype}/fixed_{prof}")
            reg.pool(f"villagers/{vtype}/nobed_{prof}", [(nb, 1, "rigid", None)], fallback=f"villagers/{vtype}/nobed_{prof}")
    g = reg.add(golem_piece("golem"), "golem")
    reg.pool("golem", [(g, 1, "rigid", None)], fallback="golem")


# Coste relativo de construir cada única (medido): las más largas se reparten antes entre los procesos.
COSTE = {"isla_corsario": 9, "atlantida": 8, "acueducto": 6, "piramide": 6, "mina_perdida": 5, "ciudadela": 4}


def _parte(tarea, seed):
    """Construye una parte del registro (lo común, un estilo o una única) en un registro propio."""
    reg = Registry()
    kind, x = tarea
    if kind == "comun":
        build_common(reg)
    elif kind == "estilo":
        build_theme(reg, THEMES[x], seed * 100 + x)
    elif kind == "mediana":
        medianas.build(reg, x)
    elif kind == "mina":
        minas.build(reg, x)
    else:
        mod = dict(unicas.modules())[x]
        mod.build(reg)
        tag_guardians(reg, x)
        reg.warnings += botin.trofeo_errores(x, getattr(mod, "TROFEO", None))
        reg.warnings += historia_cofre(reg, x, mod)
    return reg


def build_all(seed=2026):
    """Registro completo: lo común, cada estilo, cada única, cada mediana y cada tamaño de mina (en este orden, como en serie), construidos en paralelo
    (paralelo.mapa_con_estado: los datos que un build deja en su módulo vuelven al padre). Mismo resultado en serie
    (HERALDIA_PROCESOS=1)."""
    tareas = [("comun", None)] + [("estilo", i) for i in range(len(THEMES))] + [("unica", sid) for sid, _ in unicas.modules()] \
        + [("mediana", mid) for mid, _ in medianas.modules()] + [("mina", tam) for tam in minas.TAMANOS]
    partes = paralelo.mapa_con_estado(lambda t: _parte(t, seed), tareas,
                                      prioridad=lambda t: COSTE.get(t[1], 1) if t[0] == "unica" else 0)
    reg = Registry()
    for p in partes:
        for k, v in p.templates.items():
            if k in reg.templates:
                reg.warnings.append(f"plantilla repetida: {k}")
        reg.templates.update(p.templates)
        reg.pools.update(p.pools)
        reg.kinds.update(p.kinds)
        reg.warnings += p.warnings
        reg.historia.update(p.historia)
        reg.guardianes.update(p.guardianes)
    reg.warnings += botin.historia_cadena_errores(unicas.modules())
    reg.warnings += tratos.errores(unicas.modules()) + tablon.errores(THEMES)
    return reg


def historia_cofre(reg, sid, mod):
    """Contrato HISTORIA (botin.historia_errores) y que su cofre exista: algún contenedor de las plantillas de la única
    usa la tabla HISTORIA["cofre"] (el pliego no cambia la geometría: va en un cofre que ya estaba)."""
    d = getattr(mod, "HISTORIA", None)
    e = botin.historia_errores(sid, d, getattr(mod, "LOOT", {}))
    if e:
        return e
    tabla = f"{NS}:unicas/{sid}/{d['cofre']}"
    n = sum(1 for name, t in reg.templates.items() if name.startswith(f"unicas/{sid}/")
            for _, nbt in t.blocks.values() if nbt and str(nbt.get("LootTable", "")) == tabla)
    reg.historia[sid] = n
    return [] if n else [f"unicas/{sid}: ningún cofre de sus plantillas usa {tabla} (HISTORIA.cofre)"]


def tag_guardians(reg, sid):
    """Añade a los guardianes de una única (Tags con piezas.GUARDIAN_TAG) la etiqueta heraldia_guardian.<id>, con la
    que su logro los reconoce al morir (logros.py), y les pone como DeathLootTable la tabla de su trofeo
    (botin.guardian_tabla: su botín de siempre + el trofeo si lo mata un jugador). Toda única debe tener al menos uno."""
    from unicas._comun.piezas import GUARDIAN_TAG
    found, orig = 0, reg.guardianes.setdefault(sid, {})
    for name, t in reg.templates.items():
        if not name.startswith(f"unicas/{sid}/"):
            continue
        for *_, n in t.entities:
            tags = n.get("Tags") or []
            if GUARDIAN_TAG in tags:
                if f"{GUARDIAN_TAG}.{sid}" not in tags:
                    n["Tags"] = list(tags) + [f"{GUARDIAN_TAG}.{sid}"]
                mob = str(n["id"])
                prev = str(n.get("DeathLootTable") or f"minecraft:entities/{mob.split(':')[-1]}")
                if prev != botin.guardian_tabla_id(sid, mob):
                    if orig.setdefault(mob, prev) != prev:
                        reg.warnings.append(f"unicas/{sid}: guardianes {mob} con tablas de muerte distintas")
                    n["DeathLootTable"] = botin.guardian_tabla_id(sid, mob)
                found += 1
    if not found:
        reg.warnings.append(f"unicas/{sid}: ningún guardián con la etiqueta {GUARDIAN_TAG} (usa _comun/piezas.guardian)")
    elif found > 1:   # cada guardián suelta un trofeo: uno por estructura
        reg.warnings.append(f"unicas/{sid}: {found} guardianes con la etiqueta {GUARDIAN_TAG}; debe haber uno (su trofeo)")
