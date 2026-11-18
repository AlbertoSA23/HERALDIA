"""Acropolis (center) and underground: temple of Poseidon, vestibule, N-1 galleries and N-2 chambers.

Here we work in plan coordinates with absolute y (Vista with oy = 0 and no rotation).
"""
import math
from . import urban_layout as U
from . import things as C
from . import buildings as E
from . import redstone as R
from .buildings import BRICK, DARK, PRISMARINE, LANTERN, GLASS, QUARTZ, PILLAR, door, column, h
from .districts import room, COMBINATION_CENTRAL

S = U.FLOOR
G0, G1 = 13, 18            # N-1 galleries: floor and ceiling (interior 14..17)
RING = 156               # the galleries form a square of this half-side, plus four radial ones under the avenues
VESTIBULE = 10             # interior half-side of the vestibule under the temple
SEGMENT = 24                 # length of each section (dry or flooded) between doors


def temple(v):
    """Stepped base, colonnade and domed cella; in the center, the glass shaft that goes down to the vestibule."""
    v.site("templo", -64, S, -64, 64, S + 27, 64)
    for k, r in enumerate((62, 54, 46)):                                    # tres gradas de 2 de alto
        y = S + 1 + 2 * k
        for u in range(-r, r + 1):
            for w in range(-r, r + 1):
                d = math.hypot(u, w)
                if d <= r + 0.3:
                    grand_stairs = min(abs(u), abs(w)) <= 4
                    if grand_stairs and d > r - 2.3 and k < 3:
                        # stairway on the four axes: two steps per tier
                        toward = ("north" if w > 0 else "south") if abs(w) > abs(u) else ("west" if u > 0 else "east")
                        step = int(r + 0.3 - d)                               # 0 fuera, 1 dentro
                        v.set(u, y + step, w, f"prismarine_brick_stairs[facing={toward},half=bottom]")
                        if step:
                            v.set(u, y, w, BRICK)
                    else:
                        v.fill(u, y, w, u, y + 1, w, DARK if d > r - 1.3 else BRICK if (u + w) % 7 else PRISMARINE)
    top = S + 6                                                              # plataforma
    for k in range(24):                                                      # columnata
        a = (k + 0.5) * math.pi / 12
        cu, cw = round(36 * math.cos(a)), round(36 * math.sin(a))
        column(v, cu, cw, top + 1, top + 9)
    v.disk(0, 0, 38, top + 10, top + 10, DARK, cavity=33)
    v.disk(0, 0, 37, top + 11, top + 11, BRICK, cavity=34)
    # cella
    rc = 16
    v.disk(0, 0, rc, top + 1, top + 5, BRICK, cavity=rc - 1)
    v.disk(0, 0, rc, top + 5, top + 5, DARK, cavity=rc - 1)
    v.dome(0, 0, rc, top + 5, GLASS, rib=DARK)
    v.set(0, top + 5 + rc, 0, LANTERN)
    for du, dw in ((0, -1), (0, 1), (-1, 0), (1, 0)):                         # cuatro portales
        for t in (-1, 0, 1):
            cu, cw = du * rc + (t if du == 0 else 0), dw * rc + (t if dw == 0 else 0)
            v.remove(cu, top + 1, cw, cu, top + 3, cw)
        v.set(du * (rc - 4), top + 1, dw * (rc - 4), LANTERN)
    v.disk(0, 0, rc - 1, top, top, DARK)
    v.disk(0, 0, 6, top, top, PRISMARINE)
    v.entity(6, top + 6, 6, C.elder())
    for u, w in ((8, -8), (-8, 8), (-8, -8)):
        v.entity(u, top + 2, w, C.drowned(True))
    C.sign(v, 3, top + 2, 0, "east", [C.text("templo.1", "Bajo el templo,", "Below the temple,"),
                                         C.text("templo.2", "cuatro palancas.", "four levers."),
                                         C.text("templo.3", "Cada sello dice", "Each seal tells"),
                                         C.text("templo.4", "cómo dejar una.", "how to leave one.")])
    v.set(2, top + 2, 0, QUARTZ)
    v.set(2, top + 1, 0, QUARTZ)
    # shaft: 2 x 2 glass tube of water from the cella to the vestibule floor
    for y in range(G0 + 1, top + 1):
        for u in range(-1, 3):
            for w in range(-1, 3):
                inside = 0 <= u <= 1 and 0 <= w <= 1
                v.set(u, y, w, "water" if inside else (GLASS if G0 < y < G1 else BRICK))
    v.set(0, top + 1, -1, LANTERN)
    v.mark("pozo", 0, top, 0)


def vestibule(v):
    """Dry room under the temple: the glass shaft in the center, four doors to the galleries, the three locked
    arks and the combination door that goes down to N-2."""
    L = VESTIBULE + 1
    v.site("vestibulo", -L - 14, G0 - 1, -L - 6, L + 14, G1 + 3, L + 6)
    v.shell(-L, G0, -L, L, G1 + 2, L, BRICK, floor=DARK, roof=DARK)
    v.air(-L + 1, G0 + 1, -L + 1, L - 1, G1 + 1, L - 1)
    for y in range(G0 + 1, G1 + 2):                                         # the shaft is restored (the air has overwritten it)
        for u in range(-1, 3):
            for w in range(-1, 3):
                inside = 0 <= u <= 1 and 0 <= w <= 1
                v.set(u, y, w, "water" if inside else GLASS)
    v.fill(-1, G1 + 2, -1, 2, G1 + 2, 2, BRICK)
    v.fill(0, G1 + 2, 0, 1, G1 + 2, 1, "water")
    door(v, 0, G0 + 1, -1, "north")                                       # exit of the shaft
    v.set(0, G0 + 3, -1, GLASS)
    for u, w in ((-L + 1, -L + 1), (L - 1, -L + 1), (-L + 1, L - 1), (L - 1, L - 1), (-5, -5), (5, 5), (-5, 5), (5, -5)):
        v.set(u, G1 + 1, w, LANTERN)
    # arks (west wall, at the sides of the west gallery door at w = 0) with their sign
    for w, which in zip((-6, -3, 3), ("arsenal", "academia", "anfiteatro")):
        C.place_chest(v, -L + 1, G0 + 1, w, "east", "arca", key=which)
        C.sign(v, -L + 1, G0 + 2, w + 1, "east", [C.text("arca." + which, *{"arsenal": ("Arca: Arsenal", "Arsenal Coffer"),
                                                                              "academia": ("Arca: Academia", "Academy Coffer"),
                                                                              "anfiteatro": ("Arca: Anfiteatro", "Theatre Coffer")}[which])])
    # combination in the south wall, toward the east; the passage goes down to N-2
    finish = R.combination(v, -3, G0 + 2, L, COMBINATION_CENTRAL, "templo")
    v.mark("seca", 4, G0 + 1, -4)
    v.mark("vestibulo", 4, G0 + 1, -4)
    return finish


def tunnels(v):
    """N-1: four radials under the avenues and a square ring; alternating dry and flooded sections with doors."""
    def axis_segment(axis, constant, a, b, dry_part, salt):
        """Straight gallery along 'eje' ('x' or 'z') at the fixed coordinate, from a to b (a < b)."""
        for t in range(a, b + 1):
            for lat in range(-2, 3):
                u, w = (t, constant + lat) if axis == "x" else (constant + lat, t)
                for y in range(G0, G1 + 1):
                    if abs(lat) == 2 or y in (G0, G1):
                        mat = DARK if y in (G0, G1) and lat == 0 else BRICK
                        if y == G1 and lat == 0 and t % 8 == 0:
                            mat = LANTERN
                        v.set(u, y, w, mat)
                    else:
                        v.set(u, y, w, "air" if dry_part else "water")

    def partition(axis, constant, t):
        for lat in range(-1, 2):
            u, w = (t, constant + lat) if axis == "x" else (constant + lat, t)
            v.fill(u, G0 + 1, w, u, G1 - 1, w, BRICK)
        u, w = (t, constant) if axis == "x" else (constant, t)
        door(v, u, G0 + 1, w, "west" if axis == "x" else "north")

    def tunnel(axis, constant, a, b, name, starts_dry):
        """From a to b with partitions every SEGMENT; returns [(a_i, b_i, dry)]."""
        v.m.site(name, *((a, G0 - 1, constant - 3, b, G1 + 1, constant + 3) if axis == "x" else (constant - 3, G0 - 1, a, constant + 3, G1 + 1, b)))
        segments, t, dry_part = [], a, starts_dry
        while t <= b:
            finish = min(b, t + SEGMENT - 1)
            if b - finish < 8:
                finish = b
            axis_segment(axis, constant, t, finish, dry_part, 0)
            segments.append((t, finish, dry_part))
            if finish < b:
                partition(axis, constant, finish + 1)
                # the partition closes the tube: walls, floor and ceiling in that section
                for lat in (-2, 2):
                    u, w = (finish + 1, constant + lat) if axis == "x" else (constant + lat, finish + 1)
                    v.fill(u, G0, w, u, G1, w, BRICK)
                for y in (G0, G1):
                    for lat in range(-1, 2):
                        u, w = (finish + 1, constant + lat) if axis == "x" else (constant + lat, finish + 1)
                        v.set(u, y, w, DARK)
            t, dry_part = finish + 2, not dry_part
        return segments

    everyone = []
    L = VESTIBULE + 1
    # radials: leave the vestibule through a door in each wall
    for axis, sgn in (("x", 1), ("x", -1), ("z", 1), ("z", -1)):
        if axis == "z" and sgn == 1:
            a, b = L + 8, RING - 3            # the south wall carries the combination: the south radial starts farther away, through an elbow
        else:
            a, b = L + 1, RING - 3
        lo, hi = (a, b) if sgn == 1 else (-b, -a)
        tr = tunnel(axis, 0, lo, hi, "radial", starts_dry=(sgn == 1))
        everyone += [(axis, 0, t) for t in tr]
        if not (axis == "z" and sgn == 1):
            u, w = (sgn * L, 0) if axis == "x" else (0, sgn * L)
            facing = {("x", 1): "east", ("x", -1): "west", ("z", -1): "north"}[(axis, sgn)]
            door(v, u, G0 + 1, w, facing)
    # anillo cuadrado
    for axis, constant in (("x", -RING), ("x", RING), ("z", -RING), ("z", RING)):
        tr = tunnel(axis, constant, -RING + 3, RING - 3, "anillo", starts_dry=False)
        everyone += [(axis, constant, t) for t in tr]
    # junctions: flooded 7 x 7 chambers at the corners and at the crossings with the radials
    junctions = [(sx * RING, sz * RING) for sx in (-1, 1) for sz in (-1, 1)] + [(0, -RING), (0, RING), (-RING, 0), (RING, 0)]
    for cu, cw in junctions:
        v.shell(cu - 4, G0, cw - 4, cu + 4, G1 + 2, cw + 4, BRICK, floor=DARK, roof=DARK)
        v.fill(cu - 3, G0 + 1, cw - 3, cu + 3, G1 + 1, cw + 3, "water")
        v.set(cu, G1 + 2, cw, LANTERN)
        v.m.site("nudo", cu - 4, G0 - 1, cw - 4, cu + 4, S + 8, cw + 4)
        for du, dw in ((1, 0), (-1, 0), (0, 1), (0, -1)):                    # openings toward the galleries that arrive
            for lat in (-1, 0, 1):
                u, w = cu + du * 4 + (lat if du == 0 else 0), cw + dw * 4 + (lat if dw == 0 else 0)
                outside = v.get(u + du, G0 + 1, w + dw)
                if outside == "minecraft:water":
                    v.fill(u, G0 + 1, w, u, G1 - 1, w, "water")
                elif outside == "minecraft:air" and lat == 0:
                    door(v, u, G0 + 1, w, {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(du, dw)])
        # access shaft from the street: wellhead with a small shrine
        px, pw = cu + 2, cw + 2
        for y in range(G1 + 2, S + 1):
            for u in range(px - 1, px + 3):
                for w in range(pw - 1, pw + 3):
                    inside = px <= u <= px + 1 and pw <= w <= pw + 1
                    v.set(u, y, w, "water" if inside else BRICK)
        if v.get(px, S + 1, pw) == "minecraft:water" and v.get(px - 1, S + 1, pw - 1) == "minecraft:water":   # in the open air: small shrine
            for u, w in ((px - 1, pw - 1), (px + 2, pw - 1), (px - 1, pw + 2), (px + 2, pw + 2)):
                column(v, u, w, S + 1, S + 4)
            v.fill(px - 1, S + 5, pw - 1, px + 2, S + 5, pw + 2, DARK)
            v.set(px, S + 5, pw, LANTERN)
        v.mark("pozo", px, S, pw)
    return everyone


def populate_galleries(v, segments):
    """Content of each section: niches with chests, traps, spawners and lookouts."""
    for n, (axis, constant, (a, b, dry_part)) in enumerate(segments):
        middle = (a + b) // 2
        def pos(t, lat):
            return (t, constant + lat) if axis == "x" else (constant + lat, t)
        salt = U.dispersion(a, constant, 51)
        if b - a < 12:
            continue
        if dry_part:
            kind = salt % 4
            if kind == 0:                                                    # niche with a chest at one side
                u, w = pos(middle, 2)
                v.set(u, G0 + 1, w, "air")
                v.set(u, G0 + 2, w, "air")
                ext = pos(middle, 3)
                v.fill(ext[0], G0, ext[1], ext[0], G0 + 3, ext[1], BRICK)
                v.set(u, G0 + 3, w, BRICK)
                facing = ("north" if axis == "x" else "west")
                C.place_chest(v, u, G0 + 1, w, facing, "media" if salt % 3 == 0 else "menor")
            elif kind == 1:                                                  # trampa de flechas
                u, w = pos(middle, 1)
                d = pos(middle, 2)
                facing = ("north" if axis == "x" else "west")
                C.dispenser(v, d[0], G0 + 1, d[1], facing, "arrow", 24)
                v.set(u, G0 + 1, w, "stone_pressure_plate[powered=false]")
                c = pos(middle, 0)
                v.set(c[0], G0 + 1, c[1], "stone_pressure_plate[powered=false]")
                o = pos(middle, -1)
                d2 = pos(middle, -2)
                C.dispenser(v, d2[0], G0 + 1, d2[1], ("south" if axis == "x" else "east"), "arrow", 24)
                v.set(o[0], G0 + 1, o[1], "stone_pressure_plate[powered=false]")
                v.mark("trampa", u, G0 + 1, w)
            elif kind == 2:                                                  # generador de ahogados
                u, w = pos(middle, 0)
                C.generator(v, u, G0 + 1, w, "drowned", trident=salt % 2 == 0)
            else:                                                            # hoplita de guardia
                u, w = pos(middle, 0)
                v.entity(u, G0 + 1, w, C.drowned(True))
        else:
            kind = salt % 3
            u, w = pos(middle, 0)
            if kind == 0:
                v.entity(u, G0 + 2, w, C.guardian())
            elif kind == 1:
                C.generator(v, u, G0 + 1, w, "guardian")
            else:
                for t in range(middle - 3, middle + 4):
                    c = pos(t, 0)
                    v.set(c[0], G0, c[1], "magma_block")


def chambers(v, finish):
    """N-2: dry staircase from the combination door, antechamber, final guardian's room (flooded), treasure
    (dry) and the hidden crypt of the premium chest under a covered trapdoor."""
    pu, py, pw = finish                                                         # cell behind the door, y = feet
    # elbow: corridor toward the east and staircase going down toward the east
    y = py
    u = pu
    v.m.site("bajada", pu - 2, -10, pw - 1, pu + 40, G1 + 3, pw + 4)
    v.fill(pu - 1, y - 1, pw, pu + 3, y + 3, pw + 3, BRICK)
    v.air(pu, y, pw, pu + 2, y + 2, pw + 2)
    u, w = pu + 3, pw + 1
    lower = (py - (-6))
    for k in range(lower):
        # each step: one block lower and one block further east
        yy = py - k
        v.fill(u + k, yy - 2, w - 1, u + k, yy + 3, w + 1, BRICK)
        v.air(u + k, yy, w, u + k, yy + 2, w)
        v.set(u + k, yy - 1, w, "prismarine_brick_stairs[facing=west,half=bottom]")
        if k % 6 == 3:
            v.set(u + k, yy + 3, w, LANTERN)
    ex = u + lower                                                            # x where the staircase ends, feet at y = -6
    story = -7
    # dry antechamber
    room(v, ex - 1, w - 5, ex + 9, w + 5, story, story + 6)
    v.air(ex - 1, story + 1, w, ex - 1, story + 3, w)
    v.fill(ex - 1, story + 4, w, ex - 1, story + 4, w, BRICK)
    v.set(ex + 4, story + 5, w, LANTERN)
    C.sign(v, ex + 8, story + 2, w - 2, "west", [C.text("antecamara.1", "Aquí vela", "Here watches"),
                                                  C.text("antecamara.2", "el Guardián", "the Warden"),
                                                  C.text("antecamara.3", "de Poseidón.", "of Poseidon.")])
    C.place_chest(v, ex + 1, story + 1, w - 4, "south", "media")
    v.mark("seca", ex + 4, story + 1, w + 2)
    # final guardian's room: 31 x 31 x 12, flooded
    bx1, bx2, bz1, bz2 = ex + 9, ex + 41, w - 16, w + 16
    v.m.site("camaras", ex - 2, -24, bz1 - 1, bx2 + 24, story + 14, bz2 + 1)
    v.shell(bx1, story - 1, bz1, bx2, story + 12, bz2, BRICK, floor=DARK, roof=DARK)
    v.fill(bx1 + 1, story, bz1 + 1, bx2 - 1, story + 11, bz2 - 1, "water")
    door(v, bx1, story + 1, w, "west")
    v.set(bx1, story, w, DARK)
    v.fill(bx1 + 1, story, w - 1, bx1 + 2, story, w + 1, DARK)               # interior landing at the height of the door
    cx = (bx1 + bx2) // 2
    for du in (-10, 0, 10):
        for dw in (-10, 10):
            column(v, cx + du, w + dw, story, story + 11)
    for du, dw in ((-12, -12), (12, -12), (-12, 12), (12, 12), (0, 0)):
        v.set(cx + du, story + 12, w + dw, LANTERN)
        v.set(cx + du, story - 1, w + dw, LANTERN)
    v.entity(cx, story + 5, w, C.boss())
    for du, dw in ((-6, -6), (6, -6), (-6, 6), (6, 6)):
        v.entity(cx + du, story + 1, w + dw, C.drowned(True))
    C.generator(v, cx - 13, story, w - 13, "guardian")
    C.generator(v, cx + 13, story, w + 13, "guardian")
    v.mark("jefe", cx, story + 5, w)
    # treasure (dry), to the east
    tx1, tx2 = bx2, bx2 + 16
    room(v, tx1, w - 7, tx2, w + 7, story, story + 6)
    door(v, tx1, story + 1, w, "west")
    for k, dw in enumerate((-6, -3, 3, 6)):
        C.place_chest(v, tx2 - 1, story + 1, w + dw, "west", "tesoro")
    for u_ in (tx1 + 2, tx2 - 2):
        for dw in (-6, 6):
            v.set(u_, story + 5, w + dw, LANTERN)
    v.fill(tx1 + 4, story + 1, w - 6, tx1 + 5, story + 1, w - 6, "gold_block")
    v.fill(tx1 + 4, story + 1, w + 6, tx1 + 5, story + 1, w + 6, "gold_block")
    v.fill(tx1 + 3, story, w - 2, tx2 - 3, story, w + 2, "cyan_terracotta")
    v.mark("seca", tx1 + 6, story + 1, w)
    # hidden crypt: under the corner trapdoor, covered by a carpet
    hu, hw = tx2 - 2, w - 1
    room(v, hu - 5, hw - 3, hu + 1, hw + 3, story - 7, story - 1)
    v.set(hu, story, hw, "warped_trapdoor[facing=north,half=top,open=false]")
    v.set(hu, story + 1, hw, "cyan_carpet")
    for yy in range(story - 6, story):
        v.set(hu, yy, hw, "ladder[facing=west]")
    v.set(hu + 1, story - 1, hw, BRICK)
    v.set(hu - 4, story - 2, hw - 2, LANTERN)
    v.set(hu - 4, story - 2, hw + 2, LANTERN)
    v.fill(hu - 4, story - 6, hw - 1, hu - 4, story - 6, hw + 1, "gold_block")
    from . import chest_loot
    C.fixed_chest(v, hu - 4, story - 5, hw, "east", chest_loot.premium(), key="poseidon", per_player="atlantida")
    v.mark("premium", hu - 4, story - 5, hw)
    v.mark("seca", hu - 2, story - 6, hw)
    v.mark("oculta", hu - 2, story - 6, hw)
