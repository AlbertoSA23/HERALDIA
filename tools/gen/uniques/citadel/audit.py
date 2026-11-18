"""Auditoría propia de la ciudadela (condición para generar) y planos/renders para la documentación.

Planos y renders: cd tools/gen && python3 -m unicas.ciudadela.documentar ../../docs/unicas/ciudadela
"""
import itertools, os, sys
from collections import deque
from lint import walk, passable, bname
from .._common import redstone
from .blueprint import F0, FT, F1, FB, F2, F3, HOST_ROCK

LIGHT = {"lantern": 15, "campfire": 15, "lava": 15, "redstone_wall_torch": 7, "redstone_torch": 7, "magma_block": 3,
         "lava_cauldron": 15, "torch": 14, "wall_torch": 14}
LEVELS = [("N0 salón, barracones, almacén", F0 + 1), ("N0 salón del trono y cámara real", FT + 1),
          ("N1 forjas y cervecería", F1 + 1), ("Bodega oculta", FB + 1), ("N2 minas y abismo", F2 + 1),
          ("N3 antecámara y bóveda", F3 + 1)]


class View:
    def __init__(self, t, blocks=None, lint_open=None):
        self.name, self.jigsaws, self.bounds = t.name, t.jigsaws, t.bounds
        self.blocks = dict(t.blocks if blocks is None else blocks)
        self.lint_open = dict(getattr(t, "lint_open", {}) if lint_open is None else lint_open)
        self.get = lambda x, y, z: (self.blocks.get((x, y, z)) or (None,))[0]


def near(cells, p, r=1):
    x, y, z = p
    return any((x + a, y + b, z + c) in cells for a in range(-r, r + 1) for c in range(-r, r + 1) for b in (-1, 0, 1)
               if abs(a) + abs(c) <= r)


def reach_errors(pl, cells):
    t, errs = pl.t, []
    for name, p in pl.marks.items():
        if not near(cells, p, 2 if name.startswith("puerta") else 1):
            errs.append(f"{name} inaccesible en {p}")
    for x, y, z, n in t.entities:
        if not near(cells, (x, y, z)):
            errs.append(f"entidad {n['id']} inaccesible en {(x, y, z)}")
        below, here = t.get(x, y - 1, z), t.get(x, y, z)
        on_rail = "minecart" in n["id"] and bname(here) == "rail"
        if not on_rail and (below is None or passable(below)):
            errs.append(f"entidad {n['id']} flotando en {(x, y, z)}")
    for (x, y, z), (s, _) in t.blocks.items():
        b = bname(s)
        if b in ("lever", "spawner", "lectern", "brewing_stand", "crafting_table", "smithing_table") and \
                not near(cells, (x, y, z), 2 if b == "lever" else 1):
            errs.append(f"{b} inaccesible en {(x, y, z)}")
    return errs


def stair_runs(pl, cells):
    """Cada peldaño de los tramos de escalera (mismo material en columna diagonal) se pisa."""
    errs = []
    for (x, y, z), (s, _) in pl.t.blocks.items():
        if bname(s) in ("deepslate_brick_stairs", "polished_blackstone_brick_stairs") and "half=bottom" in s \
                and (x, y + 1, z) not in cells and (x, y, z) not in cells:
            above = pl.t.get(x, y + 1, z)
            if above is None or bname(above) == "air":
                errs.append(f"peldaño que no se pisa en {(x, y, z)}")
    return errs


def lava_errors(t):
    errs = []
    for (x, y, z), (s, _) in t.blocks.items():
        if bname(s) == "lava":
            for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
                n = t.get(x + d[0], y + d[1], z + d[2])
                if n is None or bname(n) in ("air", "cobweb") or (passable(n) and bname(n) != "lava"):
                    errs.append(f"lava sin contener en {(x, y, z)}")
                    break
    for (x, y, z), (s, _) in t.blocks.items():
        if bname(s) in ("water",):
            errs.append(f"agua suelta en {(x, y, z)}")
    return errs


def light_map(t):
    level = {}
    q = deque()
    for p, (s, _) in t.blocks.items():
        b = bname(s)
        if b in LIGHT and (b != "redstone_wall_torch" or "lit=true" in s) and (b != "campfire" or "lit=true" in s):
            level[p] = LIGHT[b]
            q.append(p)
    while q:
        x, y, z = q.popleft()
        v = level[(x, y, z)] - 1
        if v <= 0:
            continue
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            s = t.get(*n)
            if s is None or redstone.conductor(s) and bname(s) not in ("lava",):
                continue
            if level.get(n, 0) < v:
                level[n] = v
                q.append(n)
    return level


def spawner_errors(pl):
    errs = []
    lm = light_map(pl.t)
    for name, p in pl.marks.items():
        if not name.startswith("generador"):
            continue
        x, y, z = p
        worst = max(lm.get((x + a, y + b, z + c), 0) for a in range(-4, 5) for b in (-1, 0, 1) for c in range(-4, 5))
        if worst > 0:
            errs.append(f"{name}: hay luz {worst} en su zona de aparición")
    return errs


def ruin_ratio(pl):
    from . import DEGRADE
    t = pl.t
    air = {p for p, (s, _) in t.blocks.items() if s == "minecraft:air"}
    surf = set()
    for (x, y, z) in air:
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in t.blocks and n not in air:
                surf.add(n)
    bad = 0.0
    for p in surf:
        if p in pl.ruin_piece:
            bad += 1
        else:
            bad += DEGRADE.get(bname(t.get(*p)), (None, 0.0))[1]
    return bad / len(surf), len(surf)


def circuit_errors(pl):
    t = pl.t
    errs, sim = redstone.check_static(t)
    c = pl.circuits["trono"]
    off = redstone.Sim(t, {c["lever"]: False})
    if any(off.powered(p) for p in c["pistons"]):
        errs.append("trono: la palanca buena no retira los pistones")
    if not all(redstone.Sim(t, {c["decoy"]: False}).powered(p) for p in c["pistons"]):
        errs.append("trono: el señuelo mueve los pistones")
    v = pl.circuits["boveda"]
    keys = sorted(v["levers"])
    for combo in itertools.product((False, True), repeat=len(keys)):
        inp = {v["levers"][k]: on for k, on in zip(keys, combo)}
        opened = redstone.Sim(t, inp).powered(v["door"])
        right = all(v["solution"][k] == on for k, on in zip(keys, combo))
        if opened != right:
            errs.append(f"bóveda: combinación {dict(zip(keys, combo))} {'abre' if opened else 'no abre'}")
    a = pl.circuits["flechas"]
    s = redstone.Sim(t, {h: True for h in a["hooks"]})
    if not all(s.powered(d) for d in a["dispensers"]):
        errs.append("trampa de flechas: algún dispensador no dispara")
    tn = pl.circuits["tnt"]
    if not redstone.Sim(t, {tn["plate"]: True}).powered(tn["tnt"]):
        errs.append("trampa de TNT: la placa no la activa")
    return errs


def locked_errors(pl):
    """Con los puzles cerrados (sin abrir la puerta de pistones ni la de hierro) no se llega a sus salas."""
    t = pl.t
    blocks = dict(t.blocks)
    d = pl.circuits["boveda"]["door"]
    for p in (d, (d[0], d[1] + 1, d[2])):
        blocks[p] = ("minecraft:deepslate_bricks", None)
    cells = walk(View(t, blocks, {}))
    errs = []
    for name in ("cofre_premium", "cofre_boveda_1", "cofre_real"):
        if near(cells, pl.marks[name]):
            errs.append(f"{name} se alcanza sin resolver su puzle")
    return errs


def audit_it(pl):
    t = pl.t
    cells = walk(t)
    errs = reach_errors(pl, cells) + stair_runs(pl, cells) + lava_errors(t) + spawner_errors(pl)
    errs += circuit_errors(pl) + locked_errors(pl)
    ratio, _ = ruin_ratio(pl)
    if not 0.15 <= ratio <= 0.20:
        errs.append(f"proporción de ruina {ratio:.1%} fuera de 15-20 %")
    chests = sum(1 for _, (s, n) in t.blocks.items() if n and "LootTable" in n)
    if chests < 20:
        errs.append(f"solo {chests} contenedores con botín")
    return errs


# ---------------------------------------------------------------- documentación
def blueprint_text(pl, cells):
    t = pl.t
    x0, _, z0, x1, _, z1 = t.bounds()
    out = ["Planos de la Ciudadela enana (generados por tools/gen/uniques/citadel/audit.py).",
           "Norte arriba (la puerta, z=0); x hacia la derecha. Una celda = un bloque.",
           ". suelo alcanzable a pie   # muro o roca labrada   : hueco no transitable (abismo, aire)   ~ lava",
           "C cofre  B barril  S generador  P palanca  D puerta  H escalera de mano  = peldaño  T trampa  G guardián",
           "M vagoneta  ^ pistón  r redstone", ""]
    ents = {(x, y, z): n["id"] for x, y, z, n in t.entities}
    for title, y in LEVELS:
        y -= pl.shift[1]
        rows = []
        for z in range(z0, z1 + 1):
            row = ""
            for x in range(x0, x1 + 1):
                s, below = t.get(x, y, z), t.get(x, y - 1, z)
                b, bb = bname(s) or "", bname(below) or ""
                e = ents.get((x, y, z), "")
                if "vindicator" in e:
                    ch = "G"
                elif "minecart" in e:
                    ch = "M"
                elif b in ("chest",):
                    ch = "C"
                elif b == "barrel":
                    ch = "B"
                elif b == "spawner":
                    ch = "S"
                elif b == "lever" or bname(t.get(x, y + 1, z)) == "lever":
                    ch = "P"
                elif b.endswith("_door") or b.endswith("trapdoor"):
                    ch = "D"
                elif b == "ladder":
                    ch = "H"
                elif b in ("tripwire", "tripwire_hook", "stone_pressure_plate", "dispenser") or bb == "tnt":
                    ch = "T"
                elif "piston" in b:
                    ch = "^"
                elif "redstone" in b:
                    ch = "r"
                elif b.endswith("_stairs") or bb.endswith("_stairs") and (x, y, z) in cells:
                    ch = "="
                elif "lava" in (b, bb):
                    ch = "~"
                elif (x, y, z) in cells:
                    ch = "."
                elif s is None:
                    ch = " "
                elif b == "air":
                    ch = ":"
                else:
                    ch = "#" if b != "stone" else "#"
                row += ch
            rows.append(row.rstrip())
        while rows and not rows[-1].strip():
            rows.pop()
        out += [f"== {title} (pies a y={y}) ==", ""] + rows + [""]
    return "\n".join(out)


def renders(pl, path):
    from PIL import Image
    from render import render
    from core import Template
    import tempfile
    ims = []
    for title, y in LEVELS[:1] + LEVELS[2:3] + LEVELS[4:]:
        y -= pl.shift[1]
        v = Template("vista")
        v.blocks = {p: b for p, b in pl.t.blocks.items() if y - 1 <= p[1] <= y + 3 and bname(b[0]) != HOST_ROCK}
        f = tempfile.mktemp(suffix=".png")
        render(v, f, scale=3)
        ims.append(Image.open(f))
    v = Template("exterior")
    v.blocks = {p: b for p, b in pl.t.blocks.items() if p[2] <= 14 and bname(b[0]) != HOST_ROCK}
    f = tempfile.mktemp(suffix=".png")
    render(v, f, scale=3, flip=True)
    ims.append(Image.open(f))
    w = max(i.width for i in ims); h = max(i.height for i in ims)
    out = Image.new("RGB", (w * 2, h * 3), (255, 255, 255))
    for k, im in enumerate(ims):
        out.paste(im, ((k % 2) * w, (k // 2) * h))
    out = out.resize((out.width // 2, out.height // 2))
    out.save(path, optimize=True)
