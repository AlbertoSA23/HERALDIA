"""Simulador simplificado del ensamblado jigsaw (terreno plano) para validar conexiones y contar edificios."""
import random
from collections import Counter

ROT = ["north", "east", "south", "west"]
DV = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west", "up": "down", "down": "up"}


def rd(d, k):
    return d if d in ("up", "down") else ROT[(ROT.index(d) + k) % 4]


def rp(x, z, k):
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


class Piece:
    def __init__(self, tpl, k, off, depth, proj, parent=None):
        self.tpl, self.k, self.off, self.depth, self.proj, self.parent = tpl, k, off, depth, proj, parent
        sx, sy, sz = tpl.size()
        pts = [rp(x, z, k) for x in (0, sx - 1) for z in (0, sz - 1)]
        ox, oy, oz = off
        self.box = (min(p[0] for p in pts) + ox, oy, min(p[1] for p in pts) + oz,
                    max(p[0] for p in pts) + ox, oy + sy - 1, max(p[1] for p in pts) + oz)
        self.inside_children = []

    def jigs(self):
        out = []
        for j in self.tpl.jigsaws:
            x, y, z = j["pos"]
            rx, rz = rp(x, z, self.k)
            f, top = j["orientation"].split("_")
            out.append(dict(j, wpos=(rx + self.off[0], y + self.off[1], rz + self.off[2]),
                            front=rd(f, self.k), top=rd(top, self.k)))
        return out


def overlap2(a, b):
    return a[0] <= b[3] and b[0] <= a[3] and a[2] <= b[5] and b[2] <= a[5]


def inside2(a, b):
    return b[0] <= a[0] and a[3] <= b[3] and b[2] <= a[2] and a[5] <= b[5]


def simulate(reg, start_pool, size, maxdist, seed=0, verbose=False, aliases=None):
    rng = random.Random(seed)
    pools = reg.pools
    aliases = aliases or {}
    errors = []

    def shuffled(pid):
        pid = aliases.get(pid, pid)
        if pid not in pools:
            if pid != "minecraft:empty":
                errors.append("pool inexistente: " + pid)
            return []
        lst = []
        for (loc, w, proj, proc) in pools[pid]["elements"]:
            lst += [(loc, proj)] * w
        rng.shuffle(lst)
        return lst

    loc, proj = shuffled(start_pool)[0]
    start = Piece(reg.templates[loc], rng.randrange(4), (0, 0, 0), 0, proj)
    cx = (start.box[0] + start.box[3]) // 2
    cz = (start.box[2] + start.box[5]) // 2
    bound = (cx - maxdist, -999, cz - maxdist, cx + maxdist, 999, cz + maxdist)
    pieces = [start]
    outside = [start]
    queue = [(start, 0)]
    placed_kinds = Counter()
    placed_kinds[reg.kinds[loc]] += 1
    while queue:
        # prioridad de colocación: mayor primero, FIFO
        queue.sort(key=lambda q: -q[1])
        piece, _ = queue.pop(0)
        jl = piece.jigs()
        rng.shuffle(jl)
        jl.sort(key=lambda j: -j["sel"])
        for j in jl:
            pid = j["pool"]
            target = j["target"]
            dx, dy, dz = DV[j["front"]]
            T = (j["wpos"][0] + dx, j["wpos"][1] + dy, j["wpos"][2] + dz)
            ins = inside2((T[0], 0, T[2], T[0], 0, T[2]), piece.box)
            cands = []
            if piece.depth != size:
                cands += shuffled(pid)
            fb = pools.get(pid, {}).get("fallback", "minecraft:empty")
            cands += shuffled(fb)
            done = False
            for (cloc, cproj) in cands:
                if cloc is None:
                    break
                tpl = reg.templates[cloc]
                ks = [0, 1, 2, 3]
                rng.shuffle(ks)
                for k in ks:
                    cj = [c for c in tpl.jigsaws if c["name"] == target]
                    rng.shuffle(cj)
                    for c in cj:
                        f, top = c["orientation"].split("_")
                        cf, ct = rd(f, k), rd(top, k)
                        if cf != OPP[j["front"]]:
                            continue
                        if j["front"] in ("up", "down") and j["joint"] == "aligned" and ct != j["top"]:
                            continue
                        rx, rz = rp(c["pos"][0], c["pos"][2], k)
                        off = (T[0] - rx, T[1] - c["pos"][1], T[2] - rz)
                        np_ = Piece(tpl, k, off, piece.depth + 1, cproj, piece)
                        if ins:
                            ok = inside2(np_.box, piece.box) and not any(overlap2(np_.box, s.box) for s in piece.inside_children)
                        else:
                            ok = inside2(np_.box, bound) and not any(overlap2(np_.box, s.box) for s in outside)
                        if ok:
                            pieces.append(np_)
                            if ins:
                                piece.inside_children.append(np_)
                            else:
                                outside.append(np_)
                            placed_kinds[reg.kinds[cloc]] += 1
                            if piece.depth + 1 <= size:
                                queue.append((np_, j["place"]))
                            done = True
                            break
                    if done:
                        break
                if done:
                    break
    return pieces, placed_kinds, errors


def stats(reg, pieces):
    c = Counter()
    for p in pieces:
        kind = reg.kinds[p.tpl.name]
        c[kind] += 1
        for e in p.tpl.entities:
            i = e[3]["id"]
            if i == "minecraft:villager":
                depth = e[3]["VillagerData"]["profession"]
                c["aldeanos"] += 1
                if depth != "minecraft:none":
                    c["con_oficio"] += 1
            elif i == "minecraft:iron_golem":
                c["golems"] += 1
        for (pos, (st, nbt)) in p.tpl.blocks.items():
            if "_bed[" in st and "part=head" in st:
                c["camas"] += 1
    # las camas de piezas de aldeano: la cabecera se cuenta arriba
    return c


def variant_report(reg, seeds=40, themes=None):
    """Ensambla `seeds` aldeas de cada estilo (estándar y grande) y cuenta, por edificio especial, cuántas veces sale
    cada variante (y cuántas no cabe), además de casas, aldeanos, gólems y camas por aldea."""
    from themes import THEMES
    from writer import sizes, ALL_PROFS
    out = {}
    for th in THEMES:
        if themes and th["id"] not in themes:
            continue
        tid = th["id"]
        std, large = sizes(th)
        al = {f"heraldia:villagers/{th['vtype']}/{p}": f"heraldia:villagers/{th['vtype']}/{p}_grande" for p in ALL_PROFS}
        var, pop = Counter(), Counter()
        for pool, sz, aliases in (("plaza", std, None), ("plaza_grande", large, al)):
            for s in range(seeds):
                pieces, _, errors = simulate(reg, f"heraldia:{tid}/{pool}", sz["size"], sz["maxdist"], seed=s,
                                             aliases=aliases)
                if errors:
                    raise RuntimeError(errors[:3])
                pop += stats(reg, pieces)
                for p in pieces:
                    k = reg.kinds[p.tpl.name]
                    if k.startswith("special:"):
                        var[p.tpl.name.split("/")[-1]] += 1
        out[tid] = (var, {k: pop[k] / (2 * seeds) for k in ("house", "aldeanos", "con_oficio", "golems", "camas")})
    return out


if __name__ == "__main__":
    import argparse, os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from pack import Registry, build_common, build_theme
    from themes import THEMES
    ap = argparse.ArgumentParser(description="Diversidad de los edificios especiales en ensamblados simulados")
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("themes", nargs="*")
    a = ap.parse_args()
    reg = Registry()
    build_common(reg)
    for i, th in enumerate(THEMES):
        if not a.themes or th["id"] in a.themes:
            build_theme(reg, th, 2026 * 100 + i)
    for tid, (var, pop) in variant_report(reg, a.seeds, a.themes).items():
        print(tid, " ".join(f"{k}={v:.1f}" for k, v in pop.items()))
        print("   ", " ".join(f"{k}:{n}" for k, n in sorted(var.items())))
