"""Wave arena (T31): the colosseum template, the data the Java side reads (arena/), its loot, its advancements and its texts.

The arena is not a world-generation structure: the mod places it near spawn (/heraldia arena place, or automatically
in a new world) with this template (heraldia:arena/arena). It is a 57 x 14 x 57 block colosseum with the ring
sunk below the terrain:
  - the ring (radius 14, floor at y = 0) with 7 mob spawn points (in front of a cell with bars in the wall), the
    bell to start next to the entrance and enough light so that monsters do not spawn on their own;
  - the ring wall (radius 14-16, 3 blocks) with glass on top up to y = 10 and a barrier roof at y = 11: neither
    arrows nor mobs reach the stands, nobody climbs out and spiders cannot escape;
  - the stands (4 steps of seats, radius 16-24) and the outer walkway at ground level (y = 7) with pillars, arches
    and lanterns, open on all sides for the spectators;
  - the entrance to the ring, to the south: a ramp going down from the walkway to the ring and a bar gate that the mod closes while
    a match lasts (open in the template).
Materials: only those in PALETTE (none burns, no enderman can pick any up): fire and endermen cannot affect
it by design; explosions, pistons, players and block-carrying endermen are stopped by the Java side.

heraldia/arena.json (inside the .jar) gives the Java side the positions (relative to the template corner): ring,
spawn points, bell, gate, respawn spot, and the floor level; errores() checks that the template
meets what it claims (generation fails otherwise).

Modes and hall of fame (T41): three standing signs (crimson wood: does not burn) on the walkway, next to the entrance, one per
mode (cooperative, time attack, survival), with the previous week's champion written by the Java side (arena/Fama).
Their position goes in arena.json ("fama"): in an arena placed before T41, the Java side puts them in only if that spot is free.
Here are also the texts of the modes, the ranking and the season, their advancements (ADVANCEMENTS_MODES) and
errores_textos(), which checks that the sign lines fit (90 px) in each language in the worst case.
"""
import math

from core import Template
from loot import item
from uniques._common import chest_loot

NS = "heraldia"
TEMPLATE = "arena/arena"
VERSION = 1
N = 57                    # side of the (square) template
C = N // 2                # center column (28)
HEIGHT = 14                 # y = 0 .. 13
FLOOR = 7                 # y of the outer floor: this layer of the template goes at terrain height
R_ARENA, R_WALL, R_BLEACHERS, R_PROMENADE = 14, 16, 24, 28.5
ROOF = 11                # barrier roof over the ring and the glass
GLASS = (4, 10)         # glass over the ring wall
WALL_HIGH = 3             # the ring wall, from y = 1 to 3
RADIUS_POINTS = 11
DOOR_X = (C - 1, C + 1)                 # width of the entrance (3)
DOOR_Z = (C + 14, C + 15)               # the gate cuts the ring wall
DOOR_Y = (1, 3)
BELL = (C, 1, C + 11)
RESPAWN = (C, FLOOR + 1, N - 3)       # top of the ramp, facing the ring
RAMP_Z0 = C + 16                         # first step: z = C + 17 at y = 1; z = C + 23 at y = 7
# T41: the hall of fame signs, one per mode (Java: arena/Modo, in that order), on the walkway east of the
# ramp, facing south (rotation 0: read by those arriving at the entrance from outside).
FAME = [(C + 3, FLOOR + 1, N - 5), (C + 4, FLOOR + 1, N - 5), (C + 5, FLOOR + 1, N - 5)]
FAME_ROTATION = 0
MODES = ("coop", "timeattack", "survival")
# Allowed materials: they do not burn (FireBlock) and are not in #minecraft:enderman_holdable.
PALETTE = frozenset({
    "air", "barrier", "glass", "iron_bars", "bell", "lantern", "soul_lantern", "sea_lantern",
    "stone", "stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks", "chiseled_stone_bricks",
    "stone_brick_stairs", "stone_brick_slab", "stone_brick_wall", "polished_andesite",
    "smooth_sandstone", "cut_sandstone", "chiseled_sandstone", "red_sandstone", "cut_red_sandstone",
    "chiseled_red_sandstone", "smooth_red_sandstone",
    "crimson_sign",                         # T41: the hall of fame signs (Nether wood: does not burn)
})
# Separate check (unused; in case someone extends PALETTE): what burns and what an enderman picks up.
# (by words in the id: "sandstone" is not "sand" and "mossy" is not "moss")
FORBIDDEN_ITEMS = ("planks", "log", "wood", "wool", "leaves", "carpet", "fence", "hay", "bookshelf", "tnt", "dirt", "grass",
              "sand", "gravel", "clay", "mud", "moss", "pumpkin", "melon", "mushroom", "cactus", "nylium", "podzol",
              "mycelium", "roots", "fungus", "flower", "scaffolding", "campfire")
LIGHTS = ("lantern", "soul_lantern", "sea_lantern")


def dist(x, z):
    """Distance to the ring center from the column center (x, z)."""
    return math.hypot(x - C, z - C)


def at_entrance(x, z):
    return DOOR_X[0] <= x <= DOOR_X[1] and z >= DOOR_Z[0]


def at_door(x, y, z):
    return DOOR_X[0] <= x <= DOOR_X[1] and DOOR_Z[0] <= z <= DOOR_Z[1] and DOOR_Y[0] <= y <= DOOR_Y[1]


def outward(x, z):
    """Dominant direction from the center (for the stairs: `facing` is the high side, the back)."""
    dx, dz = x - C, z - C
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def angle_points():
    """Angles (degrees, from +x toward +z) of the spawn points: every 45 degrees except south (90), the entrance."""
    return [a for a in range(0, 360, 45) if a != 90]


def points():
    out = []
    for a in angle_points():
        r = math.radians(a)
        out.append((C + round(RADIUS_POINTS * math.cos(r)), 1, C + round(RADIUS_POINTS * math.sin(r))))
    return out


def cell_behind(p, radius):
    """The column in the same direction as point p, at `radius` from the center (the bars and the lantern of its cell)."""
    a = math.atan2(p[2] - C, p[0] - C)
    return C + round(radius * math.cos(a)), C + round(radius * math.sin(a))


def tier(d):
    """Step of the stands (0-3) for a column at distance d (R_WALL <= d < R_BLEACHERS)."""
    return int((d - R_WALL) // 2)


def construct():
    t = Template(TEMPLATE)
    pillars = 16
    for x in range(N):
        for z in range(N):
            d = dist(x, z)
            for y in range(HEIGHT):
                t.set(x, y, z, "air")
            if d < R_ARENA:
                floor = "smooth_sandstone"
                if d < 2.5:
                    floor = "chiseled_sandstone"
                elif 6.5 <= d < 7.5:
                    floor = "cut_sandstone"
                elif 12.5 <= d:
                    floor = "cut_red_sandstone"
                t.set(x, 0, z, floor)
                t.set(x, ROOF, z, "barrier")
            elif d < R_WALL:
                t.set(x, 0, z, "stone_bricks")
                t.fill(x, 1, z, x, WALL_HIGH - 1, z, "polished_andesite")
                t.set(x, WALL_HIGH, z, "chiseled_stone_bricks")
                t.fill(x, GLASS[0], z, x, GLASS[1], z, "glass")
                t.set(x, ROOF, z, "barrier")
            elif d < R_BLEACHERS:
                k = tier(d)
                upward = WALL_HIGH + k
                t.fill(x, 0, z, x, upward - 1, z, "stone_bricks")
                edge_block = (d - R_WALL) - 2 * k < 1          # inner half of the step: the seat
                t.set(x, upward, z, f"stone_brick_stairs[facing={outward(x, z)},half=bottom]" if edge_block
                      else "polished_andesite")
            else:
                t.fill(x, 0, z, x, FLOOR - 1, z, "stone" if d >= R_PROMENADE else "stone_bricks")
                t.set(x, FLOOR, z, "polished_andesite" if d >= R_PROMENADE or (x + z) % 2 else "stone_bricks")
                if 27 <= d < R_PROMENADE:                       # facade: pillars, arches and lanterns
                    s = (math.atan2(z - C, x - C) % (2 * math.pi)) / (2 * math.pi) * pillars
                    if s % 1 < 0.12 or s % 1 > 0.88:
                        t.fill(x, FLOOR + 1, z, x, FLOOR + 4, z, "stone_bricks")
                        t.set(x, FLOOR + 6, z, "lantern")
                    t.set(x, FLOOR + 5, z, "chiseled_stone_bricks")
    # ring light: the center and a ring of 8 sea lanterns on the floor
    t.set(C, 0, C, "sea_lantern")
    for a in range(0, 360, 45):
        r = math.radians(a + 22.5)
        t.set(C + round(7 * math.cos(r)), 0, C + round(7 * math.sin(r)), "sea_lantern")
    # stand light: sea lanterns on the back of each step, every 30 degrees
    for k in range(4):
        rr = R_WALL + 2 * k + 1.5
        for a in range(0, 360, 30):
            r = math.radians(a + 15)
            x, z = C + round(rr * math.cos(r)), C + round(rr * math.sin(r))
            if R_WALL <= dist(x, z) < R_BLEACHERS and not at_entrance(x, z) and not t.get(x, WALL_HIGH + tier(dist(x, z)), z).startswith("minecraft:stone_brick_stairs"):
                t.set(x, WALL_HIGH + tier(dist(x, z)), z, "sea_lantern")
    # spawn points: a mark on the floor and, behind it, a cell with bars and a soul lantern
    for p in points():
        t.set(p[0], 0, p[2], "chiseled_red_sandstone")
        bx, bz = cell_behind(p, R_ARENA + 0.5)
        lx, lz = cell_behind(p, R_ARENA + 1.5)
        t.fill(bx, 1, bz, bx, 2, bz, "iron_bars")
        t.set(lx, 1, lz, "soul_lantern")
        t.set(lx, 2, lz, "air")
    # entrance: ramp from the walkway to the ring, with parapets on the sides and the (open) gate in the wall
    for z in range(DOOR_Z[0], N):
        story = min(FLOOR, max(0, z - RAMP_Z0))
        for x in range(DOOR_X[0], DOOR_X[1] + 1):
            for y in range(1, FLOOR + 5):         # the facade arch (y = 12) sits above the entrance
                if not (GLASS[0] <= y <= ROOF and dist(x, z) < R_WALL):
                    t.set(x, y, z, "air")
            t.fill(x, 0, z, x, story, z, "stone_bricks")
            if 0 < story and z <= RAMP_Z0 + FLOOR:
                t.set(x, story, z, "stone_brick_stairs[facing=south,half=bottom]")
            elif story == FLOOR:
                t.set(x, story, z, "polished_andesite")
        if z >= RAMP_Z0:
            for x in (DOOR_X[0] - 1, DOOR_X[1] + 1):
                d = dist(x, z)
                height = WALL_HIGH + tier(d) if d < R_BLEACHERS else FLOOR
                t.set(x, height + 1, z, "stone_brick_wall")
    # lanterns on the walkway (every 30 degrees, except at the entrance) and at the four corners of the plaza
    for a in range(0, 360, 30):
        r = math.radians(a + 15)
        x, z = C + round(25.5 * math.cos(r)), C + round(25.5 * math.sin(r))
        if not at_entrance(x, z) and not at_entrance(x - 1, z) and not at_entrance(x + 1, z):
            t.set(x, FLOOR + 1, z, "lantern")
    for x, z in ((4, 4), (N - 5, 4), (4, N - 5), (N - 5, N - 5)):
        t.set(x, FLOOR + 1, z, "lantern")
    t.set(*BELL, "bell[attachment=floor,facing=north]")
    for p in FAME:
        t.set(*p, f"crimson_sign[rotation={FAME_ROTATION}]")
    return t


def dataset():
    """What the Java side reads (heraldia/arena.json): positions relative to the corner (minimum x, y, z) of the template."""
    return {
        "version": VERSION,
        "plantilla": f"{NS}:{TEMPLATE}",
        "tamano": [N, HEIGHT, N],
        "suelo": FLOOR,
        "centro": [C, 1, C],
        "radio_ruedo": R_ARENA,
        "ruedo_y": [1, ROOF - 1],
        "puntos": [list(p) for p in points()],
        "campana": list(BELL),
        "puerta": [[DOOR_X[0], DOOR_Y[0], DOOR_Z[0]], [DOOR_X[1], DOOR_Y[1], DOOR_Z[1]]],
        "reaparicion": list(RESPAWN),
        "fama": [list(p) for p in FAME],
        "fama_rotacion": FAME_ROTATION,
    }


def _name(st):
    return st.split("[")[0].removeprefix("minecraft:")


def _solid(st):
    return st is not None and _name(st) not in ("air", "lantern", "soul_lantern", "bell", "crimson_sign")


def errors(t, d=None):
    """[] if the template meets what arena.json promises: materials, closed ring, glass and roof, points, bell,
    gate and respawn."""
    d = d or dataset()
    e = []
    bad_many = sorted({_name(st) for st, _ in t.blocks.values()} - PALETTE)
    if bad_many:
        e.append(f"arena: materiales fuera de la PALETA: {bad_many}")
    for b in PALETTE:
        if set(b.split("_")) & set(FORBIDDEN_ITEMS):
            e.append(f"arena: {b} arde o lo coge un enderman")
    if t.size() != tuple(d["tamano"]):
        e.append(f"arena: tamaño {t.size()} distinto de {d['tamano']}")
    cx, _, cz = d["centro"]
    r = d["radio_ruedo"]
    y0, y1 = d["ruedo_y"]
    # the ring, closed with the gate closed: from the center no cell outside its radius can be reached
    shut = {(x, y, z) for x in range(d["puerta"][0][0], d["puerta"][1][0] + 1)
               for y in range(d["puerta"][0][1], d["puerta"][1][1] + 1)
               for z in range(d["puerta"][0][2], d["puerta"][1][2] + 1)}
    seen_all, queue = {(cx, 1, cz)}, [(cx, 1, cz)]
    while queue:
        x, y, z = queue.pop()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            p = (x + dx, y + dy, z + dz)
            if p in seen_all or p in shut or not (0 <= p[0] < N and 0 <= p[1] < HEIGHT and 0 <= p[2] < N):
                continue
            if _solid(t.get(*p)) or _name(t.get(*p)) == "iron_bars":
                continue
            seen_all.add(p)
            queue.append(p)
    outside = [p for p in seen_all if math.hypot(p[0] - cx, p[2] - cz) >= r or not y0 <= p[1] <= y1]
    if outside:
        e.append(f"arena: el ruedo no está cerrado (se llega a {sorted(outside)[:3]}...)")
    if len(seen_all) < 3.14 * (r - 1) ** 2 * (y1 - y0):
        e.append(f"arena: ruedo demasiado pequeño ({len(seen_all)} celdas)")
    # glass over the wall and barrier roof
    for x in range(N):
        for z in range(N):
            dd = dist(x, z)
            if dd < R_WALL and _name(t.get(x, ROOF, z)) != "barrier":
                e.append(f"arena: falta el techo de barreras en {x}, {ROOF}, {z}")
            if R_ARENA <= dd < R_WALL and any(_name(t.get(x, y, z)) != "glass" for y in range(GLASS[0], GLASS[1] + 1)):
                e.append(f"arena: falta cristal sobre el muro en {x}, {z}")
            if dd < r and not _solid(t.get(x, 0, z)):
                e.append(f"arena: el suelo del ruedo tiene un hueco en {x}, 0, {z}")
    for p in d["puntos"]:
        if math.hypot(p[0] - cx, p[2] - cz) >= r - 1 or not _solid(t.get(p[0], p[1] - 1, p[2])) \
                or _solid(t.get(*p)) or _solid(t.get(p[0], p[1] + 1, p[2])):
            e.append(f"arena: punto de aparición {p} fuera del ruedo, sin suelo o sin sitio")
    if len(d["puntos"]) < 4:
        e.append("arena: menos de 4 puntos de aparición")
    b = d["campana"]
    if not _name(t.get(*b)) == "bell" or not _solid(t.get(b[0], b[1] - 1, b[2])) or tuple(b) not in seen_all:
        e.append(f"arena: la campana {b} no está en el suelo del ruedo")
    if any(_solid(t.get(*p)) for p in shut):
        e.append("arena: la puerta no está abierta en la plantilla")
    rp = d["reaparicion"]
    if _solid(t.get(*rp)) or _solid(t.get(rp[0], rp[1] + 1, rp[2])) or not _solid(t.get(rp[0], rp[1] - 1, rp[2])) \
            or tuple(rp) in seen_all:
        e.append(f"arena: la reaparición {rp} no es un sitio libre con suelo fuera del ruedo")
    # T41: the hall of fame signs, one per mode, on the walkway (outside the ring and the entrance), on solid
    # ground and with air in front (to the south) so they can be read
    if len(d.get("fama", [])) != len(MODES):
        e.append(f"arena: hacen falta {len(MODES)} carteles del salón de la fama, uno por modo")
    for p in d.get("fama", []):
        x, y, z = p
        if _name(t.get(*p)) != "crimson_sign" or not _solid(t.get(x, y - 1, z)) or _solid(t.get(x, y, z + 1)) \
                or tuple(p) in seen_all or at_entrance(x, z) or dist(x, z) < R_BLEACHERS or dist(x, z) >= 27:
            e.append(f"arena: el cartel del salón de la fama {p} no está en el paseo sobre suelo y con sitio delante")
    lights = sum(1 for (x, y, z), (st, _) in t.blocks.items() if _name(st) in LIGHTS and dist(x, z) < r)
    if lights < 8:
        e.append(f"arena: el ruedo tiene solo {lights} luces (aparecerían monstruos solos)")
    return e


# --- rewards, advancements and texts ---

def _pool_table(*pools):
    return {"type": "minecraft:chest", "pools": [chest_loot.pool(r, es) for r, es in pools]}


# One reward per player every 5 waves, better as the wave rises (level 1: wave 5; 2: wave 10; 3: wave 15; 4: wave 20 and
# beyond). Vanilla only, no netherite or elytra (Owner's decisions).
REWARDS = {
    1: _pool_table((3, [item("iron_ingot", 6, 2, 5), item("bread", 4, 3, 6), item("arrow", 4, 8, 16), item("emerald", 4, 2, 5),
                   item("golden_carrot", 3, 2, 4)]),
              (1, [item("golden_apple", 1), item("iron_sword", 1, ench=(5, 15))])),
    2: _pool_table((3, [item("iron_ingot", 4, 4, 8), item("gold_ingot", 4, 2, 5), item("emerald", 4, 4, 8), item("arrow", 3, 16, 32),
                   item("experience_bottle", 3, 3, 6)]),
              (1, [item("diamond", 3, 1, 2), item("golden_apple", 2, 1, 2), item("iron_chestplate", 1, ench=(10, 20))])),
    3: _pool_table((3, [item("diamond", 3, 1, 3), item("emerald", 4, 6, 12), item("experience_bottle", 4, 5, 10),
                   item("golden_apple", 3, 1, 2)]),
              (1, [item("diamond_sword", 1, ench=(15, 25)), item("bow", 1, ench=(15, 25)), item("diamond_helmet", 1, ench=(10, 20))])),
    4: _pool_table((3, [item("diamond", 3, 2, 4), item("emerald_block", 2, 1, 2), item("experience_bottle", 4, 8, 16),
                   item("golden_apple", 3, 2, 3)]),
              (1, [item("enchanted_golden_apple", 1), item("diamond_chestplate", 2, ench=(20, 30)), item("totem_of_undying", 1),
                   item("diamond_sword", 2, ench=(25, 30))])),
}
ADVANCEMENTS = {5: ("iron_sword", "task", 50), 10: ("golden_sword", "goal", 100), 20: ("diamond_sword", "challenge", 250)}
# T41: mode advancements (granted by the Java side: arena/Marcas.logros and Fama). (id, icon, frame, xp, parent,
# (title es, en), (description es, en)). The figures are those of arena/Marcas (TIME_ATTACK_WAVES = 10,
# CONTRARRELOJ_RAPIDO_TICKS = 15 min, WAVE_SURVIVAL = 15).
TIME_ATTACK_WAVES, TIME_ATTACK_FAST_MIN, WAVE_SURVIVAL = 10, 15, 15
ADVANCEMENTS_MODES = [
    ("contrarreloj", "clock", "goal", 100, "oleada_5", ("Contra el reloj", "Against the Clock"),
     (f"Termina un contrarreloj de {TIME_ATTACK_WAVES} oleadas en la arena",
      f"Finish a {TIME_ATTACK_WAVES}-wave time attack in the arena")),
    ("contrarreloj_rapido", "sugar", "challenge", 250, "contrarreloj", ("Relámpago", "Lightning"),
     (f"Termina un contrarreloj de {TIME_ATTACK_WAVES} oleadas en menos de {TIME_ATTACK_FAST_MIN} minutos",
      f"Finish a {TIME_ATTACK_WAVES}-wave time attack in under {TIME_ATTACK_FAST_MIN} minutes")),
    (f"supervivencia_{WAVE_SURVIVAL}", "shield", "goal", 150, "oleada_5", ("Incansable", "Relentless"),
     (f"Supera la oleada {WAVE_SURVIVAL} en supervivencia, sin pausas",
      f"Clear wave {WAVE_SURVIVAL} in survival mode, with no breaks")),
    ("campeon_coop", "golden_helmet", "challenge", 100, "oleada_5", ("Héroe de la semana", "Hero of the Week"),
     ("Gana una semana de la arena en el modo cooperativo", "Win an arena week in co-op mode")),
    ("campeon_timeattack", "golden_boots", "challenge", 100, "contrarreloj", ("El más rápido", "The Fastest"),
     ("Gana una semana de la arena en el contrarreloj", "Win an arena week in time attack")),
    (f"campeon_survival", "golden_chestplate", "challenge", 100, f"supervivencia_{WAVE_SURVIVAL}",
     ("El último en pie", "Last One Standing"),
     ("Gana una semana de la arena en supervivencia", "Win an arena week in survival mode")),
]


def reward_id(level):
    return f"{NS}:arena/recompensa_{level}"


def advancement_id(wave):
    return f"{NS}:arena/oleada_{wave}"


def _advancement_key(wave, part):
    return f"advancements.{NS}.arena.oleada_{wave}.{part}"


def advancements():
    """{path: json} of the arena advancements (granted by the Java side on clearing the wave; "impossible" criterion)."""
    out = {}
    parent = f"{NS}:raiz"
    for wave, (emblem, frame, xp) in sorted(ADVANCEMENTS.items()):
        out[f"arena/oleada_{wave}"] = {
            "parent": parent,
            "criteria": {"oleada": {"trigger": "minecraft:impossible"}},
            "display": {"icon": {"id": f"minecraft:{emblem}"},
                        "title": {"translate": _advancement_key(wave, "title"), "fallback": LANG_ADVANCEMENTS[wave][0][0]},
                        "description": {"translate": _advancement_key(wave, "description"),
                                        "fallback": LANG_ADVANCEMENTS[wave][1][0]},
                        "frame": frame},
            "requirements": [["oleada"]],
            "rewards": {"experience": xp},
        }
        parent = advancement_id(wave)
    for lid, emblem, frame, xp, parent, title, desc in ADVANCEMENTS_MODES:
        out[f"arena/{lid}"] = {
            "parent": f"{NS}:arena/{parent}",
            "criteria": {"logro": {"trigger": "minecraft:impossible"}},
            "display": {"icon": {"id": f"minecraft:{emblem}"},
                        "title": {"translate": f"advancements.{NS}.arena.{lid}.title", "fallback": title[0]},
                        "description": {"translate": f"advancements.{NS}.arena.{lid}.description", "fallback": desc[0]},
                        "frame": frame},
            "requirements": [["logro"]],
            "rewards": {"experience": xp},
        }
    return out


LANG_ADVANCEMENTS = {
    5: (("Gladiador", "Gladiator"), ("Supera la oleada 5 de la arena", "Survive wave 5 of the arena")),
    10: (("Campeón de la arena", "Arena Champion"), ("Supera la oleada 10 de la arena", "Survive wave 10 of the arena")),
    20: (("Leyenda del ruedo", "Legend of the Ring"), ("Supera la oleada 20 de la arena", "Survive wave 20 of the arena")),
}
# Names of the mini-bosses (one every 5 waves, in rotation; the Java side picks by wave).
BOSSES = [("Gorbak el Rompehuesos", "Gorbak the Bonebreaker"), ("Saeta Negra", "Black Arrow"),
         ("Verdugo de la Arena", "Arena Executioner"), ("El Último Campeón", "The Last Champion")]
TEXTS = {
    "nombre": ("Arena de oleadas", "Wave arena"),
    "propuesta": ("Sitio propuesto para la arena: %s, %s, %s (a %s bloques del spawn). Las partículas marcan sus esquinas.",
                  "Proposed arena site: %s, %s, %s (%s blocks from spawn). The particles mark its corners."),
    "propuesta.confirmar": ("Confirma con %s", "Confirm with %s"),
    "copia": ("Se despeja y nivela el terreno: conviene hacer antes una copia de seguridad del mundo.",
              "The ground will be cleared and levelled: make a backup of the world first."),
    "sin_sitio": ("No hay ningún sitio llano y sin agua a 200-300 bloques del spawn.",
                  "There is no flat, dry site 200-300 blocks from spawn."),
    "sin_propuesta": ("Primero pide un sitio con %s.", "First ask for a site with %s."),
    "ya_existe": ("Ya hay una arena en %s, %s, %s: quítala con /heraldia arena remove o muévela con /heraldia arena move.",
                  "There is already an arena at %s, %s, %s: remove it with /heraldia arena remove or move it with /heraldia arena move."),
    "no_existe": ("No hay ninguna arena en este mundo.", "There is no arena in this world."),
    "colocando": ("Colocando la arena en %s, %s, %s…", "Building the arena at %s, %s, %s…"),
    "colocada": ("La arena está lista en %s, %s, %s.", "The arena is ready at %s, %s, %s."),
    "quitar.confirmar": ("Se quitará la arena de %s, %s, %s (el terreno queda llano). Confirma con /heraldia arena remove confirm.",
                         "The arena at %s, %s, %s will be removed (the ground stays flat). Confirm with /heraldia arena remove confirm."),
    "quitada": ("Arena quitada.", "Arena removed."),
    "ocupada": ("Hay una partida en marcha: espera a que acabe o usa /heraldia arena stop.",
                "A match is in progress: wait for it to end or use /heraldia arena stop."),
    "trabajando": ("Ya se está colocando o quitando la arena.", "The arena is already being built or removed."),
    "desactivada": ("La arena está desactivada en la configuración (arena.activado).",
                    "The arena is disabled in the configuration (arena.activado)."),
    "info": ("Arena de oleadas en %s, %s, %s.", "Wave arena at %s, %s, %s."),
    "info.libre": ("Sin partida: entra en el ruedo y toca la campana.", "No match: step into the ring and ring the bell."),
    "info.partida": ("Partida en marcha: oleada %s, %s participantes.", "Match in progress: wave %s, %s players."),
    "info.record": ("Tu récord: oleada %s. Récord del servidor: oleada %s.", "Your record: wave %s. Server record: wave %s."),
    "cuenta": ("Prepárate", "Get ready"),
    "lucha": ("¡Lucha!", "Fight!"),
    "oleada": ("Oleada %s", "Wave %s"),
    "oleada.jefe": ("¡Llega %s!", "%s is coming!"),
    "oleada.mobs": ("%s enemigos", "%s enemies"),
    "oleada.superada": ("Oleada %s superada", "Wave %s cleared"),
    "oleada.siguiente": ("Siguiente oleada en %s s", "Next wave in %s s"),
    "barra": ("Arena · oleada %s · quedan %s", "Arena · wave %s · %s left"),
    "barra.pausa": ("Arena · oleada %s superada", "Arena · wave %s cleared"),
    "barra.cuenta": ("Arena · empieza en %s", "Arena · starts in %s"),
    "fin": ("La partida de la arena ha terminado: %s oleadas superadas.", "The arena match is over: %s waves cleared."),
    "sale": ("%s ha salido del ruedo.", "%s has left the ring."),
    "cae": ("%s ha caído en la oleada %s.", "%s fell in wave %s."),
    "conservado": ("Has caído en la arena: conservas tu inventario y tu experiencia.",
                   "You fell in the arena: you keep your inventory and experience."),
    "record.personal": ("Nuevo récord personal en la arena: oleada %s.", "New personal arena record: wave %s."),
    "record.servidor": ("¡%s ha batido el récord de la arena: oleada %s!", "%s has broken the arena record: wave %s!"),
    "recompensa": ("Recompensa por superar la oleada %s.", "Reward for clearing wave %s."),
    "sin_participantes": ("No hay nadie en el ruedo: entrad y tocad la campana.", "Nobody is in the ring: step in and ring the bell."),
    "en_marcha": ("Ya hay una partida en marcha.", "A match is already in progress."),
    "prohibido": ("La arena está protegida.", "The arena is protected."),
    "perla": ("No se pueden lanzar perlas de ender en el ruedo durante la partida.",
              "Ender pearls cannot be thrown in the ring during a match."),
    "salir.no": ("No estás en ninguna partida de la arena.", "You are not in an arena match."),
    "parada": ("Partida de la arena detenida.", "Arena match stopped."),
    "marcador": ("Arena: récord de oleadas", "Arena: wave records"),
    "marcador.servidor": ("Récord del servidor", "Server record"),
    # T41: modes, weekly ranking, season and hall of fame
    "modo.coop": ("Cooperativo", "Co-op"),
    "modo.timeattack": ("Contrarreloj", "Time attack"),
    "modo.survival": ("Supervivencia", "Survival"),
    "modo.coop.ayuda": ("Oleadas sin fin con pausa entre ellas: puntúa la oleada a la que llegáis.",
                        "Endless waves with a break in between: your score is the wave you reach."),
    "modo.timeattack.ayuda": ("%s oleadas contra el reloj: gana quien las supera antes.",
                              "%s waves against the clock: whoever clears them fastest wins."),
    "modo.survival.ayuda": ("Oleadas sin pausa hasta que caigáis: puntúa la oleada más alta.",
                            "Waves with no break until you fall: your score is the highest wave."),
    "modo.elige": ("Elige el modo de la partida (pulsa uno):", "Choose the match mode (click one):"),
    "modo.ninguno": ("No hay ningún modo de partida activado (arena.modos.*).", "No match mode is enabled (arena.modos.*)."),
    "modo.desactivado": ("El modo %s está desactivado en la configuración.", "The %s mode is disabled in the configuration."),
    "modo.ruedo": ("Entra en el ruedo para empezar una partida.", "Step into the ring to start a match."),
    "cuenta.modo": ("Prepárate: %s", "Get ready: %s"),
    "info.partida.modo": ("Partida en marcha (%s): oleada %s, %s participantes.", "Match in progress (%s): wave %s, %s players."),
    "oleada.de": ("Oleada %s de %s", "Wave %s of %s"),
    "sin_pausa": ("Sin respiro: llega la siguiente", "No respite: here comes the next one"),
    "tiempo": ("Tiempo: %s", "Time: %s"),
    "fin.contrarreloj": ("¡Contrarreloj completado: %s oleadas en %s!", "Time attack complete: %s waves in %s!"),
    "fin.contrarreloj.no": ("Contrarreloj sin acabar: %s de %s oleadas.", "Time attack unfinished: %s of %s waves."),
    "barra.contrarreloj": ("Contrarreloj · oleada %s/%s · quedan %s · %s", "Time attack · wave %s/%s · %s left · %s"),
    "barra.supervivencia": ("Supervivencia · oleada %s · quedan %s", "Survival · wave %s · %s left"),
    "puntos.oleadas": ("oleada %s", "wave %s"),
    "puntos.tiempo": ("%s (%s oleadas)", "%s (%s waves)"),
    "puntos.parcial": ("%s/%s oleadas", "%s/%s waves"),
    "record.modo": ("¡%s bate el récord de la arena en %s: %s!", "%s has set a new arena record in %s: %s!"),
    "semana.cerrada": ("Termina la semana de la arena (la del %s).", "The arena week of %s is over."),
    "semana.campeon": ("Campeón de %s: %s, %s.", "%s champion: %s, %s."),
    "semana.sin_campeones": ("Nadie jugó en la arena esa semana.", "Nobody played in the arena that week."),
    "clasificacion.actual": ("Clasificación de la arena, semana del %s (en curso):", "Arena leaderboard, week of %s (current):"),
    "clasificacion.pasada": ("Clasificación de la arena, semana del %s:", "Arena leaderboard, week of %s:"),
    "clasificacion.vacia": ("  Sin marcas todavía.", "  No results yet."),
    "clasificacion.linea": ("  %s. %s: %s", "  %s. %s: %s"),
    "clasificacion.record": ("  Récord: %s, %s", "  Record: %s, %s"),
    "clasificacion.sin_semana": ("No se guarda esa semana: el histórico tiene %s.",
                                 "That week is not kept: the history has %s."),
    "temporada.info": ("Semana de la arena del %s; próximo reinicio: %s (%s); %s semanas en el histórico.",
                       "Arena week of %s; next reset: %s (%s); %s weeks in the history."),
    "temporada.reiniciada": ("Semana de la arena del %s cerrada a mano.", "Arena week of %s closed by hand."),
    "cartel.titulo": ("Campeón", "Champion"),
    "cartel.nadie": ("Sin campeón", "No champion"),
}
# Lines of the hall of fame signs (Java: arena/Fama.lineas): (key, bold, worst-case arguments).
# The player's is their name (up to 16 characters of A-Z, a-z, 0-9 and _; one of 16 "W" does not fit: the client cuts it off).
SIGN = [("cartel.titulo", True, []), ("modo.coop", False, []), ("modo.timeattack", False, []), ("modo.survival", False, []),
          ("cartel.nadie", False, []), ("puntos.oleadas", False, ["999"]),
          ("puntos.parcial", False, ["99", "99"])]          # finished time attack: only its time (m:ss)
TYPICAL_NAME = "Steve_Builder12"       # 15 medium-width characters: what must fit on the player's line



def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][f"{NS}.arena.{k}"], out["en_us"][f"{NS}.arena.{k}"] = es, en
    for i, (es, en) in enumerate(BOSSES):
        out["es_es"][f"{NS}.arena.jefe.{i}"], out["en_us"][f"{NS}.arena.jefe.{i}"] = es, en
    for wave, (title, desc) in LANG_ADVANCEMENTS.items():
        for i, language in enumerate(("es_es", "en_us")):
            out[language][_advancement_key(wave, "title")] = title[i]
            out[language][_advancement_key(wave, "description")] = desc[i]
    for lid, _, _, _, _, title, desc in ADVANCEMENTS_MODES:
        for i, language in enumerate(("es_es", "en_us")):
            out[language][f"advancements.{NS}.arena.{lid}.title"] = title[i]
            out[language][f"advancements.{NS}.arena.{lid}.description"] = desc[i]
    return out


def text_errors(translations=None):
    """[] if every line of the hall of fame signs fits (90 px, bold counts) in each language, with the
    worst-case arguments. `translations`: {code: texts} of the languages other than es/en."""
    import languages
    base = lang()
    e = []
    everyone = [("es_es", base["es_es"]), ("en_us", base["en_us"])] + list((translations or {}).items())
    for lang_code, texts in everyone:
        for k, bold, args in SIGN:
            text = languages.format_text(texts[f"{NS}.arena.{k}"], args)
            if languages.sign_width(text, bold) > languages.SIGN_WIDTH:
                e.append(f"arena: {lang_code}: la línea del cartel {k} no cabe: «{text}» "
                         f"({languages.sign_width(text, bold)} px de {languages.SIGN_WIDTH})")
    if languages.sign_width(TYPICAL_NAME) > languages.SIGN_WIDTH:
        e.append("arena: un nombre de jugador típico no cabe en el cartel")
    return e


def tables():
    """{name: table} for the loot validation."""
    return {f"arena/recompensa_{n}": t for n, t in REWARDS.items()}


def write(out, jdump):
    """Writes the template, heraldia/arena.json, the rewards and the advancements; returns the texts. Fails if the
    template does not meet what it promises."""
    t = construct()
    e = errors(t)
    if e:
        raise SystemExit("\n".join(e))
    t.save(out)
    jdump(out, f"{NS}/arena.json", dict(dataset(), jefes=len(BOSSES)))
    for n, tbl in REWARDS.items():
        jdump(out, f"data/{NS}/loot_table/arena/recompensa_{n}.json", tbl)
    for route, advancement in advancements().items():
        jdump(out, f"data/{NS}/advancement/{route}.json", advancement)
    return lang()
