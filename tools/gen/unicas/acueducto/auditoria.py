"""Auditoría propia del acueducto sobre la estructura completa montada (coordenadas globales).

Recorrido a pie con los puzles cerrados y resueltos, nada flotando, redstone simulada, porcentaje de ruina y
planos de planta. `python3 -m unicas.acueducto.auditoria <carpeta>` (desde tools/gen) escribe planos y renders."""
import os, sys
from collections import deque
from core import Template, parse_state
import lint
from .redstone import Sim, name

ENTRADA = (47, 0, 98)          # fuera de la puerta sur


def variante(o, modo):
    """Copia de la plantilla global en un estado de los puzles: 'cerrado', 'p1' (castellum abierto) o 'resuelto'."""
    t = Template("acueducto/" + modo)
    t.blocks = dict(o.t.blocks)
    r = o.red

    def put(p, st):
        t.blocks[p] = (st, None)
    if modo in ("p1", "resuelto"):
        for p in r["puerta_1"]:
            x, y, z = p
            put((x, y, z), "minecraft:air")
            put((x, y, z + 1), "minecraft:chiseled_sandstone")
            put((x, y, z + 2), "minecraft:sticky_piston[extended=false,facing=north]")
    if modo != "resuelto":
        for p in r["puerta_2"]:
            put(p, "minecraft:stone")          # la puerta de hierro no se abre a mano
        put(r["reja"], o.t.blocks[r["reja"]][0])
    else:
        put(r["reja"], "minecraft:ladder[facing=north,waterlogged=false]")
        put(r["trampilla_favissa"], "minecraft:ladder[facing=south,waterlogged=false]")
    x0, y0, z0, x1, y1, z1 = o.t.bounds()
    for x in range(x0 - 1, x1 + 2):          # suelo natural explícito bajo lo que no tiene subsuelo
        for z in range(z0 - 1, z1 + 2):
            for y in range(y0 - 1, 0):
                if (x, y, z) not in t.blocks:
                    t.blocks[(x, y, z)] = ("minecraft:dirt", None)
    t.jigsaws = [dict(pos=ENTRADA, name="heraldia:entrance", orientation="north_up")]
    return t


def alcanzables(t):
    return lint.walk(t)


def flotantes(o):
    """Bloques no unidos al suelo (y <= 0) por una cadena de vecinos."""
    b = {p for p, (st, _) in o.t.blocks.items() if name(st) != "air"}
    seen = {p for p in b if p[1] <= 0}
    q = deque(seen)
    while q:
        x, y, z = q.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in b and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(b - seen)


def redstone(o):
    """Comprueba puzles y trampas con el simulador; devuelve la lista de fallos."""
    g = lambda p: o.t.get(*p)
    r = o.red
    cells = [p for p, (st, _) in o.t.blocks.items()
             if any(k in name(st) for k in ("redstone", "lever", "button", "pressure_plate", "tripwire_hook"))]
    sim = Sim(g)
    errs = []
    A, I, T = r["palanca_A"], r["palanca_I"], r["palanca_T"]
    for a in (0, 1):
        for i in (0, 1):
            for tt in (0, 1):
                s = sim.run(cells, {A: a, I: i, T: tt})
                cerrada = all(s.mech_powered(p) for p in (r["piston_1"], r["piston_2"]))
                if cerrada != (not (a and not i and tt)):
                    errs.append(f"puzle 1: AQVA={a} IGNIS={i} TERRA={tt} -> {'cerrada' if cerrada else 'abierta'}")
                if s.mech_powered(r["piston_1"]) != s.mech_powered(r["piston_2"]):
                    errs.append(f"puzle 1: los pistones no van a la par ({a}{i}{tt})")
    s = sim.run(cells, {})
    for p, lit in s.lit.items():
        if (o.t.get(*p) or "").find(f"lit={'true' if lit else 'false'}") < 0:
            errs.append(f"antorcha {p} colocada en un estado inestable")
    for w, pw in s.dust.items():
        if f"power={pw}," not in o.t.get(*w) and not o.t.get(*w).endswith(f"power={pw}]"):
            errs.append(f"polvo {w} colocado con potencia distinta de {pw}")
    mechs = r["dispensadores_1"] + r["dispensadores_28"] + r["dispensadores_30"] + r["puerta_2"] + [r["reja"]]
    for p in mechs:
        if s.mech_powered(p):
            errs.append(f"{p} recibe señal sin que nadie lo active")
    checks = [({r["gancho_O"]: 1, r["gancho_E"]: 1}, r["dispensadores_1"]),
              ({r["placa_28"]: 1}, r["dispensadores_28"]), ({r["placa_30"]: 1}, r["dispensadores_30"]),
              ({r["placa_ofrenda"]: 1}, r["puerta_2"][:1]), ({r["boton"]: 1}, r["puerta_2"][:1]),
              ({r["palanca_reja"]: 1}, [r["reja"]])]
    for inp, outs in checks:
        s = sim.run(cells, inp)
        for p in outs:
            if not s.mech_powered(p):
                errs.append(f"{list(inp)} no activa {p}")
    return errs


def estabilizar(o):
    """Escribe en la plantilla el nivel de señal estable del polvo con todas las entradas apagadas."""
    cells = [p for p, (st, _) in o.t.blocks.items() if "redstone" in name(st)]
    s = Sim(lambda p: o.t.get(*p)).run(cells, {})
    for w, pw in s.dust.items():
        bid, pr = parse_state(o.t.get(*w))
        pr["power"] = str(pw)
        o.s(*w, bid + "[" + ",".join(f"{k}={v}" for k, v in sorted(pr.items())) + "]")


def auditar(o):
    errs = []
    if not 0.15 <= o.ruina / o.sup <= 0.20:
        errs.append(f"ruina {o.ruina}/{o.sup} = {o.ruina / o.sup:.1%} fuera de 15-20 %")
    errs += [f"flotando: {p} {o.t.get(*p)}" for p in flotantes(o)[:10]]
    errs += redstone(o)
    res = variante(o, "resuelto")
    acc = [i for i in lint.access_issues(res) + lint.support_issues(res) if i[1] != ENTRADA]
    errs += [f"{m} {p}" for m, p in acc[:20]]
    cells = alcanzables(res)
    near = lambda p, rr=1: any((p[0] + dx, p[1] + dy, p[2] + dz) in cells for dx in range(-rr, rr + 1)
                               for dz in range(-rr, rr + 1) for dy in (-1, 0, 1) if abs(dx) + abs(dz) <= rr)
    for p, (st, _) in o.t.blocks.items():
        n = name(st)
        if n in ("lever", "stone_button", "spawner") and not near(p, 2 if n == "spawner" else 1):
            errs.append(f"{n} inaccesible {p}")
    for x, y, z, nbt in o.t.entities:
        if not near((x, y, z)):
            errs.append(f"guardián inaccesible {(x, y, z)}")
    prem = o.red["premium"]
    p1 = alcanzables(variante(o, "p1"))
    cer = alcanzables(variante(o, "cerrado"))
    if any(c[1] < 0 and 64 <= c[0] <= 92 and -5 <= c[2] <= 44 for c in cer):
        errs.append("las cloacas se alcanzan sin resolver el puzle 1")
    for nombre, cs in (("cerrado", cer), ("p1", p1)):
        if any(abs(c[0] - prem[0]) + abs(c[2] - prem[2]) <= 1 and abs(c[1] - prem[1]) <= 1 for c in cs):
            errs.append(f"el cofre premium se alcanza con los puzles en estado {nombre}")
    return errs, (cer, res, cells)


NIVELES = [("ciudad", 1, (-1, 5, 96, 98)), ("castellum_p1", 8, (72, -12, 86, 4)),
           ("castellum_azotea", 15, (72, -12, 86, 4)), ("templo_y_caldarium", 4, (40, 24, 92, 46)),
           ("cloacas", -8, (64, -5, 92, 44)), ("cisterna", -7, (33, 42, 63, 60))]


def planos(o, cer, cells, out):
    os.makedirs(out, exist_ok=True)
    marks = {"chest": "C", "barrel": "B", "spawner": "G", "_door": "P", "ladder": "E", "_stairs": "e",
             "lever": "L", "pressure_plate": "T", "tripwire": "T", "dispenser": "D", "water": "~", "piston": "M"}
    for nom, y, (x0, z0, x1, z1) in NIVELES:
        lines = [f"# {nom}: pies en y = {y}. · se alcanza a pie desde la puerta sur; o solo con los puzles resueltos;",
                 "# C cofre, B barril, G generador, P puerta, E escalera de mano, e escalón, L palanca,",
                 "# T placa o cable trampa, D dispensador, M pistón, ~ agua, # muro. Norte arriba; x de izquierda a derecha.", ""]
        for z in range(z0, z1 + 1):
            row = ""
            for x in range(x0, x1 + 1):
                ch = None
                for yy in (y, y - 1):
                    n = name(o.t.get(x, yy, z))
                    for k, m in marks.items():
                        if k in n and ch is None:
                            ch = m
                if ch is None:
                    c = next(((x, yy, z) for yy in (y, y - 1, y + 1) if (x, yy, z) in cells), None)
                    if c:
                        ch = "·" if c in cer else "o"
                    elif name(o.t.get(x, y, z)) != "air" and o.t.get(x, y, z):
                        ch = "#"
                    else:
                        ch = " "
                row += ch
            lines.append(row.rstrip())
        with open(os.path.join(out, f"plano_{nom}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def renders(o, out):
    import render
    full = Template("r")
    full.blocks = {p: v for p, v in o.t.blocks.items() if p[1] >= 0}
    full.normalize()
    render.render(full, os.path.join(out, "render_conjunto.png"), scale=2)
    city = Template("c")
    city.blocks = {p: v for p, v in o.t.blocks.items() if 0 <= p[1] <= 5 and p[2] >= -12}
    city.normalize()
    render.render(city, os.path.join(out, "render_ciudad_sin_tejados.png"), scale=3)


if __name__ == "__main__":
    from . import mundo
    o = mundo()
    errs, (cer, res, cells) = auditar(o)
    print("\n".join(errs) or "auditoría OK", f"ruina {o.ruina / o.sup:.1%}")
    planos(o, cer, cells, sys.argv[1])
    renders(o, sys.argv[1])
