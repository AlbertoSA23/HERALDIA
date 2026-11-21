"""Look at what was built: top-down and isometric renders of a template or of a saved world's blocks.

render.py draws flat-coloured cubes, enough to check a shape. This one is for judging how something *looks*: every
block gets the average colour of its real texture, thin blocks keep their shape (slabs, stairs, walls, fences, panes,
carpets, lanterns), faces are shaded by their side and by height, and only the faces that show are drawn. The textures
are Mojang's and are never committed: pass a clone of misode/mcmeta's `<version>-assets` branch with --assets (or the
HERALDIA_ASSETS variable); without one, the colours fall back to render.py's table.

    python3 tools/gen/look.py template casa_heraldo/casa out.png [--view iso|top] [--turn 0..3] [--cut Y] [--scale N]
    python3 tools/gen/look.py world <world folder> x0 z0 x1 z1 out.png [--y0 Y --y1 Y] [--view ...]

From Python: blocks is {(x, y, z): "minecraft:id[props]"}; `iso(blocks, path)` and `top(blocks, path)`.
"""
import argparse
import colorsys
import functools
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render

ASSETS = os.environ.get("HERALDIA_ASSETS")
SKIP = ("air", "cave_air", "void_air", "structure_void", "jigsaw", "barrier", "light")
# biome tints (plains): the textures of these are grey
TINT = {"grass_block": (124, 189, 80), "short_grass": (124, 189, 80), "tall_grass": (124, 189, 80),
        "fern": (124, 189, 80), "large_fern": (124, 189, 80), "vine": (84, 150, 60), "lily_pad": (32, 128, 48),
        "water": (52, 96, 196), "sugar_cane": (140, 200, 100)}
LEAF_TINT = {"birch_leaves": (128, 167, 85), "spruce_leaves": (97, 153, 97)}
LEAF_DEFAULT = (86, 152, 52)
UNTINTED_LEAVES = ("cherry_leaves", "azalea_leaves", "flowering_azalea_leaves", "pale_oak_leaves")
SUFFIXES = ("_stairs", "_slab", "_wall", "_fence_gate", "_fence", "_pressure_plate", "_button", "_trapdoor", "_door",
            "_wall_sign", "_wall_hanging_sign", "_hanging_sign", "_sign", "_pane", "_carpet", "_wall_banner", "_banner",
            "_bed", "_candle", "_wall_torch", "_torch", "_wall_head", "_head")
GLOW = ("lantern", "torch", "campfire", "glowstone", "sea_lantern", "shroomlight", "candle", "lava", "fire",
        "jack_o_lantern", "end_rod", "froglight", "redstone_lamp", "copper_bulb")
DYES = {"white": (233, 236, 236), "orange": (240, 118, 19), "magenta": (189, 68, 179), "light_blue": (58, 175, 217),
        "yellow": (248, 198, 39), "lime": (112, 185, 25), "pink": (237, 141, 172), "gray": (62, 68, 71),
        "light_gray": (142, 142, 134), "cyan": (21, 137, 145), "purple": (121, 42, 172), "blue": (53, 57, 157),
        "brown": (114, 71, 40), "green": (84, 109, 27), "red": (160, 39, 34), "black": (20, 21, 25)}


def name_of(state):
    return state.split("[")[0].replace("minecraft:", "")


def props_of(state):
    if "[" not in state:
        return {}
    return dict(kv.split("=") for kv in state[state.index("[") + 1:-1].split(","))


def _candidates(n):
    """Texture file names to try for a block, most specific first."""
    base = n[6:] if n.startswith("waxed_") else n
    out = [base + "_top", base]
    for suf in SUFFIXES:
        if base.endswith(suf):
            stem = base[:-len(suf)]
            out += [stem, stem + "s", stem + "_planks", stem + "_top", stem.replace("brick", "bricks"),
                    stem + "_block", stem + "_wool" if suf in ("_carpet", "_bed", "_banner", "_wall_banner") else stem,
                    stem + "_door_top" if suf == "_door" else stem, stem + "_stained_glass", "smooth_" + stem]
            if stem.endswith("_stained_glass") or stem == "glass":
                out.append(stem)
    special = {"water": "water_still", "lava": "lava_still", "campfire": "campfire_log_lit", "bell": "bell_top",
               "smooth_stone_slab": "smooth_stone", "petrified_oak_slab": "oak_planks", "snow": "snow",
               "farmland": "farmland_moist", "dirt_path": "dirt_path_top", "iron_bars": "iron_bars",
               "glass_pane": "glass", "moss_carpet": "moss_block", "fire": "fire_0", "chest": "oak_planks",
               "trapped_chest": "oak_planks", "ender_chest": "obsidian", "wheat": "wheat_stage7",
               "carrots": "carrots_stage3", "potatoes": "potatoes_stage3", "beetroots": "beetroots_stage3",
               "quartz_block": "quartz_block_top", "smooth_quartz": "quartz_block_bottom", "magma_block": "magma",
               "tall_seagrass": "tall_seagrass_top", "cobweb": "cobweb", "pale_moss_carpet": "pale_moss_block",
               "sweet_berry_bush": "sweet_berry_bush_stage3", "bamboo": "bamboo_stalk", "torchflower_crop": "torchflower",
               "decorated_pot": "terracotta", "armor_stand": "stone", "wall_torch": "torch", "soul_wall_torch": "soul_torch",
               "redstone_wire": "redstone_block", "kelp_plant": "kelp_plant", "snow_block": "snow",
               "infested_stone_bricks": "stone_bricks", "infested_cobblestone": "cobblestone", "cauldron": "cauldron_side",
               "water_cauldron": "cauldron_side", "hopper": "hopper_outside", "anvil": "anvil", "lectern": "lectern_top",
               "grindstone": "grindstone_side", "stonecutter": "stonecutter_top", "composter": "composter_side",
               "scaffolding": "scaffolding_top", "chain": "iron_chain", "iron_chain": "iron_chain",
               "leaf_litter": "leaf_litter", "bookshelf": "bookshelf", "chiseled_bookshelf": "chiseled_bookshelf_empty"}
    if n in special:
        out.insert(0, special[n])
    if base.startswith("potted_"):
        out.insert(0, base[7:])
    if base.startswith("stripped_") and base.endswith("_wood"):
        out.insert(0, base[:-5] + "_log")
    if base.endswith("_wood"):
        out.insert(0, base[:-5] + "_log")
    if base.endswith("_hyphae"):
        out.insert(0, base[:-7] + "_stem")
    return out


@functools.lru_cache(maxsize=None)
def colour(n):
    """Average colour of a block's texture (top face if it has one), tinted like a plains biome; None if not drawn."""
    if n in SKIP:
        return None
    folder = os.path.join(ASSETS, "assets", "minecraft", "textures", "block") if ASSETS else None
    rgb = None
    if folder and os.path.isdir(folder):
        for c in _candidates(n):
            p = os.path.join(folder, c + ".png")
            if os.path.exists(p):
                im = Image.open(p).convert("RGBA")
                im = im.crop((0, 0, im.width, min(im.height, im.width)))      # first frame of an animation
                px = [q for q in im.getdata() if q[3] > 40]
                if px:
                    rgb = tuple(sum(q[i] for q in px) // len(px) for i in range(3))
                    break
    if rgb is None:
        for dye, c in DYES.items():
            if n.startswith(dye + "_"):
                rgb = c
                break
    if rgb is None:
        rgb = render.color_of(n) or (128, 128, 128)
    tint = TINT.get(n) or LEAF_TINT.get(n) or (LEAF_DEFAULT if n.endswith("_leaves") and n not in UNTINTED_LEAVES else None)
    if tint:
        g = sum(rgb) / 3 / 255 * 1.35
        rgb = tuple(min(255, int(t * g)) for t in tint)
    return rgb


def boxes(n, p):
    """The block's shape as boxes (x0, y0, z0, x1, y1, z1) inside the unit cube (y up)."""
    f = p.get("facing", "north")
    if n.endswith("_slab"):
        t = p.get("type", "bottom")
        return [(0, 0, 0, 1, 1, 1)] if t == "double" else [(0, .5, 0, 1, 1, 1)] if t == "top" else [(0, 0, 0, 1, .5, 1)]
    if n.endswith("_stairs"):
        top = p.get("half") == "top"
        slab = (0, .5, 0, 1, 1, 1) if top else (0, 0, 0, 1, .5, 1)
        y0, y1 = (0, .5) if top else (.5, 1)
        half = {"north": (0, y0, 0, 1, y1, .5), "south": (0, y0, .5, 1, y1, 1),
                "west": (0, y0, 0, .5, y1, 1), "east": (.5, y0, 0, 1, y1, 1)}[f]
        return [slab, half]
    if n.endswith("_wall") or n.endswith("_fence") or n in ("iron_bars",) or n.endswith("_pane"):
        w = .25 if n.endswith("_wall") else .12
        out = [(.5 - w, 0, .5 - w, .5 + w, 1, .5 + w)]
        h = .85 if n.endswith("_wall") else 1
        for d, b in (("north", (.5 - w * .7, 0, 0, .5 + w * .7, h, .5)), ("south", (.5 - w * .7, 0, .5, .5 + w * .7, h, 1)),
                     ("west", (0, 0, .5 - w * .7, .5, h, .5 + w * .7)), ("east", (.5, 0, .5 - w * .7, 1, h, .5 + w * .7))):
            if p.get(d, "none") not in ("none", "false"):
                out.append(b)
        return out
    if n.endswith("_fence_gate"):
        return [(0, .3, .4, 1, 1, .6)] if f in ("north", "south") else [(.4, .3, 0, .6, 1, 1)]
    if n.endswith("_carpet") or n in ("snow", "leaf_litter", "lily_pad", "moss_carpet") or n.endswith("_pressure_plate"):
        return [(0, 0, 0, 1, .1, 1)]
    if n.endswith("_trapdoor"):
        if p.get("open") == "true":
            return [{"north": (0, 0, .82, 1, 1, 1), "south": (0, 0, 0, 1, 1, .18), "west": (.82, 0, 0, 1, 1, 1),
                     "east": (0, 0, 0, .18, 1, 1)}[f]]
        return [(0, .82, 0, 1, 1, 1)] if p.get("half") == "top" else [(0, 0, 0, 1, .18, 1)]
    if n.endswith("_door"):
        return [{"north": (0, 0, .82, 1, 1, 1), "south": (0, 0, 0, 1, 1, .18), "west": (.82, 0, 0, 1, 1, 1),
                 "east": (0, 0, 0, .18, 1, 1)}[f]]
    if n in ("lantern", "soul_lantern") or n.endswith("_lantern") and n not in ("sea_lantern", "jack_o_lantern"):
        return [(.33, .35, .33, .67, .9, .67)] if p.get("hanging") == "true" else [(.33, 0, .33, .67, .55, .67)]
    if n.endswith("torch") or n in ("end_rod", "lightning_rod", "chain", "iron_chain") or n.endswith("candle"):
        return [(.42, 0, .42, .58, .7, .58)]
    if n.startswith("potted_") or n == "flower_pot":
        return [(.3, 0, .3, .7, .45, .7), (.4, .45, .4, .6, .95, .6)]
    if n.endswith("_bed"):
        return [(0, 0, 0, 1, .56, 1)]
    if n in ("farmland", "dirt_path"):
        return [(0, 0, 0, 1, .94, 1)]
    if n.endswith("campfire"):
        return [(0, 0, 0, 1, .4, 1)]
    if n.endswith("_wall_banner") or n.endswith("_wall_sign"):
        return [{"north": (.05, 0, .88, .95, 1, 1), "south": (.05, 0, 0, .95, 1, .12), "west": (.88, 0, .05, 1, 1, .95),
                 "east": (0, 0, .05, .12, 1, .95)}[f]]
    if n.endswith("_banner") or n.endswith("_sign"):
        return [(.2, 0, .44, .8, 1, .56)]
    if n in ("ladder", "vine", "glow_lichen"):
        return [{"north": (0, 0, .9, 1, 1, 1), "south": (0, 0, 0, 1, 1, .1), "west": (.9, 0, 0, 1, 1, 1),
                 "east": (0, 0, 0, .1, 1, 1)}.get(f, (0, 0, .9, 1, 1, 1))]
    if n in PLANT or n.endswith("_sapling") or n.endswith("_tulip") or n.endswith("_bush") or n.endswith("_roots") \
            or n.endswith("_fungus") or n.endswith("_mushroom") or n.endswith("_sprouts"):
        return [(.25, 0, .25, .75, .7, .75)]
    if n == "bell":
        return [(.25, .2, .25, .75, .8, .75)]
    if n in ("anvil", "grindstone", "brewing_stand", "lectern", "stonecutter", "cauldron", "water_cauldron", "hopper"):
        return [(.12, 0, .12, .88, .8, .88)]
    if n in ("chest", "trapped_chest", "ender_chest"):
        return [(.06, 0, .06, .94, .88, .94)]
    if n.endswith("_head") or n.endswith("_skull"):
        return [(.25, 0, .25, .75, .5, .75)]
    return [(0, 0, 0, 1, 1, 1)]


PLANT = {"short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "poppy", "dandelion", "cornflower", "allium",
         "azure_bluet", "oxeye_daisy", "blue_orchid", "lily_of_the_valley", "sunflower", "lilac", "rose_bush", "peony",
         "wheat", "carrots", "potatoes", "beetroots", "sugar_cane", "sweet_berry_bush", "cobweb", "torchflower",
         "pink_petals", "wildflowers", "short_dry_grass", "tall_dry_grass", "bush", "firefly_bush", "cactus_flower",
         "seagrass", "tall_seagrass", "kelp", "kelp_plant", "nether_wart", "melon_stem", "pumpkin_stem", "pitcher_plant",
         "wither_rose", "cactus", "bamboo", "open_eyeblossom", "closed_eyeblossom", "hanging_roots", "spore_blossom"}


def _full(n, p):
    """True if the block hides what is behind it (a full, opaque cube)."""
    if n in SKIP or n in PLANT or "glass" in n or n in ("water", "ice") or n.endswith("_leaves"):
        return False
    return boxes(n, p) == [(0, 0, 0, 1, 1, 1)]


def _shade(c, f, glow=False):
    if glow:
        return tuple(min(255, int(v * 1.15 + 25)) for v in c)
    return tuple(max(0, min(255, int(v * f))) for v in c)


def turned(blocks, turn):
    """The blocks seen from another corner: turn quarter turns clockwise (states' facings turn with them)."""
    turn %= 4
    if not turn or not blocks:
        return blocks
    cw = {"north": "east", "east": "south", "south": "west", "west": "north"}
    out = {}
    mx = max(p[0] for p in blocks)
    mz = max(p[2] for p in blocks)
    for (x, y, z), st in blocks.items():
        nx, nz, s = x, z, st
        span = [mz, mx]
        for k in range(turn):
            nx, nz = span[k % 2] - nz, nx
            if "[" in s:
                n, p = s.split("[")[0], props_of(s)
                q = {k2: v for k2, v in p.items() if k2 not in cw}
                if p.get("facing") in cw:
                    q["facing"] = cw[p["facing"]]
                for dname in cw:
                    if dname in p:
                        q[cw[dname]] = p[dname]
                s = n + "[" + ",".join(f"{k2}={v}" for k2, v in sorted(q.items())) + "]"
        out[(nx, y, nz)] = s
    return out


def iso(blocks, path, scale=6, cut=None, turn=0, bg=(232, 236, 240), label=None):
    """Isometric picture (seen from the south-east corner, looking north-west; `turn` picks another corner). `cut`:
    nothing above that y is drawn (to look inside). Returns the image."""
    blocks = {p: s for p, s in blocks.items() if name_of(s) not in SKIP and (cut is None or p[1] <= cut)}
    blocks = turned(blocks, turn)
    if not blocks:
        return None
    xs = [p[0] for p in blocks]; ys = [p[1] for p in blocks]; zs = [p[2] for p in blocks]
    x0, y0, z0 = min(xs), min(ys), min(zs)
    X, Y, Z = max(xs) - x0 + 1, max(ys) - y0 + 1, max(zs) - z0 + 1
    s = scale
    W, H = (X + Z) * 2 * s + 4 * s, (X + Z) * s + Y * 2 * s + 6 * s
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    ox, oy = Z * 2 * s + 2 * s, Y * 2 * s + 2 * s

    def pt(x, y, z):
        return ox + (x - z) * 2 * s, oy + (x + z) * s - y * 2 * s

    parsed = {p: (name_of(st), props_of(st)) for p, st in blocks.items()}
    full = {p for p, (n, pr) in parsed.items() if _full(n, pr)}
    for p in sorted(parsed, key=lambda q: (q[0] + q[2], q[1], q[0])):
        x, y, z = p
        n, pr = parsed[p]
        c = colour(n)
        if c is None:
            continue
        cube = p in full
        seen_top = (x, y + 1, z) not in full
        seen_s = (x, y, z + 1) not in full
        seen_e = (x + 1, y, z) not in full
        if cube and not (seen_top or seen_s or seen_e):
            continue
        glow = any(g in n for g in GLOW) and pr.get("lit", "true") != "false"
        lift = 0.9 + 0.1 * min(1.0, (y - y0) / max(8, Y))
        v = ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) % 7 / 100.0 - 0.03    # a little grain per block
        alpha = "glass" in n or n == "water"
        for (a0, b0, c0, a1, b1, c1) in boxes(n, pr):
            gx0, gy0, gz0, gx1, gy1, gz1 = x - x0 + a0, y - y0 + b0, z - z0 + c0, x - x0 + a1, y - y0 + b1, z - z0 + c1
            if not cube or seen_top:
                d.polygon([pt(gx0, gy1, gz0), pt(gx1, gy1, gz0), pt(gx1, gy1, gz1), pt(gx0, gy1, gz1)],
                          fill=_shade(c, (1.0 + v) * lift, glow))
            if (not cube or seen_s) and not (alpha and (x, y, z + 1) in parsed and parsed[(x, y, z + 1)][0] == n):
                d.polygon([pt(gx0, gy1, gz1), pt(gx1, gy1, gz1), pt(gx1, gy0, gz1), pt(gx0, gy0, gz1)],
                          fill=_shade(c, (0.78 + v) * lift, glow))
            if (not cube or seen_e) and not (alpha and (x + 1, y, z) in parsed and parsed[(x + 1, y, z)][0] == n):
                d.polygon([pt(gx1, gy1, gz0), pt(gx1, gy1, gz1), pt(gx1, gy0, gz1), pt(gx1, gy0, gz0)],
                          fill=_shade(c, (0.60 + v) * lift, glow))
    if label:
        d.text((6, 4), label, fill=(30, 30, 30))
    if path:
        img.save(path, optimize=True)
    return img


def top(blocks, path, scale=6, cut=None, bg=(232, 236, 240), label=None, relief=True):
    """Plan view: each column's highest drawn block, shaded by height and by the slope towards the north-west."""
    cols = {}
    for (x, y, z), st in blocks.items():
        n = name_of(st)
        if n in SKIP or (cut is not None and y > cut):
            continue
        if (x, z) not in cols or y > cols[(x, z)][0]:
            cols[(x, z)] = (y, n, st)
    if not cols:
        return None
    x0 = min(p[0] for p in cols); z0 = min(p[1] for p in cols)
    X = max(p[0] for p in cols) - x0 + 1; Z = max(p[1] for p in cols) - z0 + 1
    ylo = min(c[0] for c in cols.values()); yhi = max(c[0] for c in cols.values())
    img = Image.new("RGB", (X * scale, Z * scale), bg)
    d = ImageDraw.Draw(img)
    for (x, z), (y, n, st) in cols.items():
        c = colour(n)
        if c is None:
            continue
        f = 0.82 + 0.3 * (y - ylo) / max(1, yhi - ylo) if relief else 1.0
        if relief:
            a = cols.get((x - 1, z), (y,))[0]; b = cols.get((x, z - 1), (y,))[0]
            f += max(-0.22, min(0.22, 0.07 * ((y - a) + (y - b))))
        glow = any(g in n for g in GLOW)
        px, pz = (x - x0) * scale, (z - z0) * scale
        bx = boxes(n, props_of(st))
        if len(bx) == 1 and (bx[0][3] - bx[0][0] < 1 or bx[0][5] - bx[0][2] < 1) and scale >= 4:
            a0, _, c0, a1, _, c1 = bx[0]
            under = max((yy for (xx, yy, zz) in ((x, y - 1, z),) if (xx, yy, zz) in blocks), default=None)
            if under is not None:
                uc = colour(name_of(blocks[(x, y - 1, z)]))
                if uc:
                    d.rectangle([px, pz, px + scale - 1, pz + scale - 1], fill=_shade(uc, f))
            d.rectangle([px + a0 * scale, pz + c0 * scale, max(px + a0 * scale, px + a1 * scale - 1),
                         max(pz + c0 * scale, pz + c1 * scale - 1)], fill=_shade(c, f, glow))
        else:
            d.rectangle([px, pz, px + scale - 1, pz + scale - 1], fill=_shade(c, f, glow))
    if label:
        d.text((6, 4), label, fill=(20, 20, 20))
    if path:
        img.save(path, optimize=True)
    return img


def side_by_side(images, path, gap=12, bg=(255, 255, 255)):
    """Several pictures in a row (before / after)."""
    images = [i for i in images if i is not None]
    w = sum(i.width for i in images) + gap * (len(images) - 1)
    h = max(i.height for i in images)
    out = Image.new("RGB", (w, h), bg)
    x = 0
    for i in images:
        out.paste(i, (x, 0))
        x += i.width + gap
    out.save(path, optimize=True)
    return out


def template_blocks(t):
    return {p: v[0] for p, v in t.blocks.items()}


def nbt_blocks(path):
    """The blocks of a written template (.nbt)."""
    import nbtlib
    root = nbtlib.load(path)
    pal = []
    for e in root["palette"]:
        pr = e.get("properties") or e.get("Properties")
        nm = str(e.get("id") or e.get("Name"))
        pal.append(nm + ("[" + ",".join(f"{k}={v}" for k, v in sorted(pr.items())) + "]" if pr else ""))
    return {tuple(int(c) for c in b["pos"]): pal[int(b["state"])] for b in root["blocks"]}


def world_blocks(world, x0, z0, x1, z1, y0=-64, y1=319):
    """The saved overworld's blocks in a box, read from its region files (the server stopped, or after save-all flush)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "smoke"))
    import existing_world as ew
    out = {}
    for cx in range(x0 >> 4, (x1 >> 4) + 1):
        for cz in range(z0 >> 4, (z1 >> 4) + 1):
            n = ew.read_chunk(world, cx, cz)
            if n is None:
                continue
            for sec in n.get("sections", []):
                sy = int(sec["Y"])
                if sy * 16 > y1 or sy * 16 + 15 < y0 or sec.get("block_states") is None:
                    continue
                st = ew.states(ew._blueprint(sec["block_states"]))
                names = [s[0] + ("[" + ",".join(f"{k}={v}" for k, v in s[1]) + "]" if s[1] else "") for s in st]
                if len(set(names)) == 1 and name_of(names[0]) in SKIP:
                    continue
                for i, s in enumerate(names):
                    if name_of(s) in SKIP:
                        continue
                    x, y, z = cx * 16 + (i & 15), sy * 16 + (i >> 8), cz * 16 + ((i >> 4) & 15)
                    if x0 <= x <= x1 and z0 <= z <= z1 and y0 <= y <= y1:
                        out[(x, y, z)] = s
    return out


def main():
    global ASSETS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=("template", "nbt", "world"))
    ap.add_argument("args", nargs="+")
    ap.add_argument("--assets", default=ASSETS)
    ap.add_argument("--view", default="iso", choices=("iso", "top"))
    ap.add_argument("--turn", type=int, default=0)
    ap.add_argument("--cut", type=int)
    ap.add_argument("--scale", type=int, default=6)
    ap.add_argument("--y0", type=int, default=-64)
    ap.add_argument("--y1", type=int, default=319)
    a = ap.parse_args()
    ASSETS = a.assets
    colour.cache_clear()
    if a.what == "template":
        from pack import build_all
        reg = build_all()
        blocks, out = template_blocks(reg.templates[a.args[0]]), a.args[1]
    elif a.what == "nbt":
        blocks, out = nbt_blocks(a.args[0]), a.args[1]
    else:
        x0, z0, x1, z1 = (int(v) for v in a.args[1:5])
        blocks, out = world_blocks(a.args[0], x0, z0, x1, z1, a.y0, a.y1), a.args[5]
    if a.view == "top":
        top(blocks, out, scale=a.scale, cut=a.cut)
    else:
        iso(blocks, out, scale=a.scale, cut=a.cut, turn=a.turn)
    print(out)


if __name__ == "__main__":
    main()
