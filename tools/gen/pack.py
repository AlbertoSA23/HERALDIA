"""Construye todas las piezas, pools y JSON del datapack."""
import json, os, random, shutil
from core import Template, nsid, NS
from lint import passable
from themes import THEMES, FAMILIES
from houses import make_house, PROFS_HOUSE
from streets import (straight, crossroad, terminator_end, watchtower, gate, plaza, avenue, decor_piece, P)
from specials import SPECIALS
from fillers import filler, villager_piece, golem_piece, rug_piece

SPARE = 22        # peso de "cama libre" en las casas

ALL_PROFS = ["armorer", "butcher", "cartographer", "cleric", "farmer", "fisherman", "fletcher", "leatherworker",
             "librarian", "mason", "shepherd", "toolsmith", "weaponsmith"]

AVENUES = {"a": ("church", "townhall"), "b": ("market", "tavern"), "c": ("blacksmith", "library"),
           "d": ("farm", None)}  # derecha de D: puerto (costa) o posada


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
    for kind in ("church", "townhall", "market", "tavern", "blacksmith", "library", "farm", "inn", "port", "cemetery", "mill"):
        if kind == "port" and th["family"] != "costa":
            continue
        if kind == "inn" and th["family"] == "costa":
            continue
        t = SPECIALS[kind](th, rng, f"{tid}/specials/{kind}")
        name = reg.add(t, "special:" + kind)
        pid = f"{tid}/{kind}" if kind in ("cemetery", "mill") else f"{tid}/special/{kind}"
        reg.pool(pid, [(name, 1, "rigid", bld_proc)])
    # ---- avenidas
    for a, (lft, rgt) in AVENUES.items():
        if a == "d":
            rgt = "port" if th["family"] == "costa" else "inn"
        t = avenue(th, rng, f"{tid}/avenues/{a}", P(th, f"special/{lft}"), P(th, f"special/{rgt}"))
        reg.pool(f"{tid}/avenue_{a}", [(reg.add(t, "avenue"), 1, "terrain_matching", street_proc)])
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


def build_all(seed=2026):
    reg = Registry()
    build_common(reg)
    for i, th in enumerate(THEMES):
        build_theme(reg, th, seed * 100 + i)
    return reg
