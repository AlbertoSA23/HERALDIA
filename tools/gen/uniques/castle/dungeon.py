"""Dungeon under the keep: guardroom, cells, crypt, cistern, false treasury with a trap,
arrow-slit corridor, guardian's room with the three-lever riddle and the hidden treasure chamber.
Local coordinates: x 0..47, z 0..55, y 0..15 (y=15 touches the castle base; feet at y=3)."""
import random
from core import B
from .util import Canvas, hidden_door
from .._common.pieces import (wire, connect, guardian as _guardian, spawner as _spawner, chest as put_chest,
                             tripwire_trap, tnt_trap)
from .surface import NEWEL, LOOT

OFF = (26, -16, 14)          # local + OFF = castle coordinates
NX, NZ = NEWEL[0] - OFF[0], NEWEL[1] - OFF[2]
D = 3                         # pies
SB = "stone_bricks"


def build(below, rnd=None):
    rnd = rnd or random.Random(1308)
    t = Canvas("unicas/castillo/mazmorra")
    meta = {"chests": [], "spawners": [], "secret": {}, "breakable": []}
    for x in range(48):
        for z in range(56):
            for y in range(16):
                k = rnd.random()
                t.set(x, y, z, "stone" if k < 0.8 else ("andesite" if k < 0.92 else "tuff"))
    t.fill(0, 15, 0, 47, 15, 55, "stone")
    rooms = []

    def room(x1, z1, x2, z2, h=4, floor=SB, wall=SB):
        rooms.append((x1, z1, x2, z2, h, floor, wall))

    def chest(x, y, z, f, table, kind="chest"):
        put_chest(t.set, x, y, z, f, LOOT + table, kind)
        meta["chests"].append(((x, y, z), table))

    def spawner(x, y, z, mob):
        _spawner(t.set, x, y, z, mob)
        meta["spawners"].append(((x, y, z), mob))

    def hang(x, y, z, soul=True):
        t.set(x, y, z, ("soul_lantern" if soul else "lantern") + "[hanging=true,waterlogged=false]")

    room(3, 3, 30, 14, h=6, floor="mossy_stone_bricks")        # cisterna
    room(34, 4, 44, 13, h=4, floor="polished_andesite")        # false treasury
    room(31, 9, 33, 9, h=2)                                    # cistern - treasury tunnel
    room(3, 17, 7, 38, h=4, floor="cobblestone")               # cripta
    room(5, 15, 5, 16, h=2)                                    # paso cripta - cisterna
    room(9, 26, 19, 32, h=5)                                   # cuerpo de guardia
    room(21, 28, 44, 30, h=4)                                  # corridor of the cells
    room(42, 16, 44, 27, h=4)                                  # passage to the false treasury
    room(43, 14, 43, 15, h=2)
    for x0 in (22, 27, 32, 37):
        room(x0, 22, x0 + 3, 26, h=4, floor="cobblestone")
        room(x0, 32, x0 + 3, 36, h=4, floor="cobblestone")
    room(13, 34, 15, 47, h=4)                                  # arrow-slit corridor
    room(17, 42, 35, 52, h=7, floor="polished_andesite")       # guardian's room
    room(38, 42, 44, 50, h=5, floor="polished_deepslate")      # treasure chamber
    for x1, z1, x2, z2, h, fl, wall in rooms:
        t.fill(x1 - 1, D - 1, z1 - 1, x2 + 1, D + h, z2 + 1, wall)
    for x1, z1, x2, z2, h, fl, wall in rooms:
        t.air(x1, D, z1, x2, D + h - 1, z2)
        t.fill(x1, D - 1, z1, x2, D - 1, z2, fl)
    # caracol
    t.fill(NX - 2, 0, NZ - 2, NX + 2, 15, NZ + 2, SB)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            t.set(NX + dx, D - 1, NZ + dz, SB)
            t.air(NX + dx, D, NZ + dz, NX + dx, 15, NZ + dz)
    t.fill(NX, D - 1, NZ, NX, 14, NZ, SB)
    for x, y, z, s in below:
        t.set(x - OFF[0], y - OFF[1], z - OFF[2], s)
    t.opening(NX, D, NZ + 2)
    t.jigsaw(NX, 15, NZ, "up_south", "unicas/castillo/subida", "unicas/castillo/bajada", "minecraft:empty",
             final_state=SB)
    # openings between rooms
    for x, z in ((20, 29), (8, 29), (14, 33)):
        t.opening(x, D, z)
    t.opening(16, D, 47)

    # ---------------------------------------------------------------- cuerpo de guardia
    t.fill(11, D, 30, 12, D, 30, "spruce_slab[type=top,waterlogged=false]")
    t.set(11, D, 31, "spruce_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    t.set(12, D, 29, "spruce_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    chest(19, D, 26, "west", "mazmorra")
    t.set(9, D, 26, "barrel[facing=up,open=false]")
    t.set(19, D, 32, "barrel[facing=up,open=false]")
    t.set(9, D, 32, "grindstone[face=floor,facing=east]")
    hang(14, D + 4, 29, soul=False)
    t.set(9, D + 2, 28, "wall_torch[facing=east]")
    t.set(19, D + 2, 30, "wall_torch[facing=west]")

    # ---------------------------------------------------------------- calabozos
    for x0 in (22, 27, 32, 37):
        for zf, f in ((27, "north"), (31, "south")):
            for x in range(x0, x0 + 4):
                t.fill(x, D, zf, x, D + 2, zf, "iron_bars")
            t.set(x0 + 1, D, zf, f"iron_door[facing={f},half=lower,hinge=left,open=true,powered=false]")
            t.set(x0 + 1, D + 1, zf, f"iron_door[facing={f},half=upper,hinge=left,open=true,powered=false]")
        t.set(x0 + 3, D, 22, "hay_block[axis=x]")
        t.set(x0 + 3, D, 36, "hay_block[axis=x]")
        t.set(x0, D, 26 if x0 != 32 else 22, "cauldron")
    for y in range(D, D + 3):
        t.set(34, y, 27, "air")                                  # barrotes arrancados
    spawner(33, D, 24, "zombie")
    for x, y, z in ((32, D + 3, 22), (35, D + 3, 26), (34, D + 3, 23), (24, D + 3, 34), (39, D + 3, 22)):
        t.set(x, y, z, "cobweb")
    chest(22, D, 22, "south", "mazmorra")
    chest(40, D, 36, "north", "mazmorra")
    t.set(38, D, 22, "bone_block[axis=y]")
    t.set(38, D + 1, 22, "skeleton_skull[powered=false,rotation=8]")
    # nicho oculto tras ladrillos agrietados (celda sur 2)
    t.air(28, D, 38, 29, D + 1, 38)
    t.fill(28, D - 1, 38, 29, D - 1, 38, SB)
    t.fill(28, D, 37, 29, D + 1, 37, "cracked_stone_bricks")
    meta["breakable"] = [(28, D, 37), (29, D, 37), (28, D + 1, 37), (29, D + 1, 37)]
    chest(29, D, 38, "west", "oculto")
    meta["niche"] = (29, D, 38)
    for x in (24, 29, 34, 39):
        hang(x, D + 3, 29)
    hang(43, D + 3, 21)

    # ---------------------------------------------------------------- cripta
    spawner(5, D, 21, "skeleton")
    for z in range(18, 38, 4):
        t.set(3, D, z, "bone_block[axis=y]")
        t.set(3, D + 1, z, "skeleton_skull[powered=false,rotation=12]")
        t.set(7, D, z + 2, "stone_brick_slab[type=bottom,waterlogged=false]")
    for z in (24, 28, 32):
        t.set(5, D, z, "chiseled_stone_bricks")
        t.set(5, D + 1, z, "candle[candles=3,lit=false,waterlogged=false]")
    chest(7, D, 37, "west", "mazmorra")
    for x, z in ((3, 17), (7, 17), (3, 38), (4, 30)):
        t.set(x, D + 3, z, "cobweb")
    hang(5, D + 3, 34)

    # ---------------------------------------------------------------- cisterna
    for x in range(6, 28):
        for z in range(5, 13):
            if z == 8 or (x % 5 == 3 and z in (6, 11)):
                continue
            t.fill(x, 1, z, x, D - 1, z, "water[level=0]")
    for x in range(8, 28, 5):
        for z in (6, 11):
            t.fill(x, 0, z, x, D + 5, z, SB)
    for x in range(6, 28):
        t.set(x, 1, 8, SB)
    spawner(16, D, 9, "spider")
    t.fill(15, 0, 9, 17, D - 1, 9, SB)
    chest(3, D, 3, "south", "mazmorra", "barrel")
    hang(16, D + 5, 8)
    t.set(30, D + 1, 14, "wall_torch[facing=north]")

    # ---------------------------------------------------------------- false treasury (dynamite trap)
    t.fill(37, D, 4, 41, D, 4, "polished_blackstone_bricks")
    t.set(39, D, 4, "polished_andesite")
    t.set(39, D + 1, 4, "air")
    chest(39, D + 1, 4, "south", "mazmorra")
    tnt_trap(t.set, 39, D, 5)
    for x, z in ((38, 5), (40, 5), (39, 6), (39, 4)):
        t.set(x, 1, z, "tnt[unstable=false]")
    for x in (34, 44):
        for z in (6, 9, 12):
            if (x, z) != (34, 9):
                t.set(x, D, z, "barrel[facing=up,open=false]")
    chest(44, D, 4, "west", "menor", "barrel")
    for x in (37, 41):
        t.set(x, D + 2, 4, "red_wall_banner[facing=south]")
    hang(39, D + 3, 9, soul=False)

    # ---------------------------------------------------------------- arrow-slit corridor
    arrows = {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": 16}]}
    tripwire_trap(t.set, (12, 40), (16, 40), D, "x",
                  [((x, y, z), f) for x, f in ((12, "east"), (16, "west")) for y, z in ((D + 1, 40), (D, 41), (D, 39))])
    t.set(14, D + 3, 35, "cobweb")

    # ---------------------------------------------------------------- guardian's room
    for x in (21, 26, 31):
        for z in (45, 49):
            t.fill(x, D, z, x, D + 6, z, "polished_deepslate")
    t.fill(33, D, 45, 35, D, 49, "polished_blackstone_bricks")
    t.set(35, D + 1, 47, "dark_oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    for x, z in ((24, 47), (29, 47), (19, 44), (19, 50)):
        hang(x, D + 6, z)
    for z in (44, 50):
        t.set(35, D + 4, z, "red_wall_banner[facing=west]")
    # secret door of the treasure chamber (northeast corner) and the three-lever riddle
    a, c = 35, 42
    info = hidden_door(t.set, a, c, D, +1, SB, input_floor=False)
    meta["secret"]["tesoro"] = info
    levers = {"green": 27, "red": 30, "black": 33}
    for color, x in levers.items():
        t.set(x, D + 1, c, "lever[face=wall,facing=south,powered=false]")
        t.set(x, D + 4, c, f"{color}_wall_banner[facing=south]")
    for color in ("green", "black"):
        x = levers[color]
        for dx, y in ((0, D), (-1, D + 1), (1, D + 1)):
            t.set(x + dx, y, c - 1, "dispenser[facing=south,triggered=false]", dict(arrows))
    xr = levers["red"]
    t.set(xr + 1, D + 1, c - 2, "air")
    t.set(xr + 2, D, c - 2, "air")
    wire(t.set, [(xr, D + 1, c - 2), (xr + 1, D, c - 2), (xr + 2, D - 1, c - 2), (xr + 3, D - 1, c - 2),
                      (xr + 4, D - 1, c - 2)])
    meta["levers"] = {k: (x, D + 1, c) for k, x in levers.items()}
    # guardian
    t.entity(30, D, 47, guardian())

    # ---------------------------------------------------------------- treasure chamber
    t.opening(37, D, 42)
    t.set(41, D - 1, 50, "chiseled_stone_bricks")
    chest(41, D, 50, "north", "premium")
    meta["premium"] = (41, D, 50)
    for x in (40, 42):
        t.set(x, D, 50, "gold_block")
        t.set(x, D + 1, 50, "candle[candles=4,lit=true,waterlogged=false]")
    chest(44, D, 45, "west", "oculto")
    t.set(38, D, 50, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    t.set(44, D, 50, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    t.set(41, D + 3, 50, "red_wall_banner[facing=north]")
    hang(41, D + 4, 46, soul=False)
    connect(t)
    return t, meta


def guardian():
    eq = {k: {"id": "minecraft:" + v, "count": 1} for k, v in
          (("mainhand", "iron_sword"), ("head", "iron_helmet"), ("chest", "chainmail_chestplate"),
           ("legs", "iron_leggings"), ("feet", "chainmail_boots"))}
    return _guardian("zombie", "heraldia.castillo.guardian", "Sir Aldric, el Castellano Maldito", 60, equipment=eq,
                     drop_chances={k: (0.2 if k == "mainhand" else 0.1) for k in eq},
                     attributes={"attack_damage": 5, "knockback_resistance": 0.4, "follow_range": 24},
                     extra={"IsBaby": B(0), "CanPickUpLoot": B(0)})
