"""Render isométrico sencillo de plantillas para revisión visual."""
from PIL import Image, ImageDraw
import hashlib

COL = {
    "air": None, "structure_void": None, "jigsaw": None,
    "glass_pane": (190, 220, 235), "white_stained_glass_pane": (235, 235, 235), "water": (60, 90, 200),
    "lantern": (255, 200, 80), "soul_lantern": (80, 200, 220), "torch": (255, 200, 80),
    "grass_block": (90, 150, 60), "dirt_path": (150, 120, 70), "gravel": (130, 125, 120),
    "cobblestone": (120, 120, 120), "stone_bricks": (125, 125, 125), "bricks": (150, 75, 60),
    "white_terracotta": (210, 180, 160), "calcite": (225, 225, 220), "white_concrete": (230, 232, 233),
    "hay_block": (200, 170, 40), "brick_stairs": (150, 75, 60), "brick_slab": (150, 75, 60), "bookshelf": (120, 80, 50), "lava": (230, 100, 20),
}
WOODCOL = {"oak": (162, 130, 78), "spruce": (110, 80, 50), "birch": (200, 185, 125), "jungle": (160, 115, 80),
           "acacia": (170, 90, 50), "dark_oak": (66, 43, 20), "mangrove": (117, 54, 48), "cherry": (225, 175, 170),
           "pale_oak": (230, 220, 215), "bamboo": (195, 175, 80)}
STONECOL = {"red_sandstone": (180, 95, 35), "red_sand": (190, 100, 40), "red_nether": (110, 20, 20), "deepslate": (70, 70, 75), "sandstone": (215, 200, 150),
            "mud": (120, 90, 70), "tuff": (110, 110, 100), "blackstone": (45, 40, 45), "copper": (80, 160, 130),
            "quartz": (235, 230, 225), "terracotta": (150, 90, 65), "prismarine": (90, 160, 150),
            "andesite": (130, 132, 132), "granite": (150, 105, 85), "diorite": (190, 190, 190),
            "mossy": (100, 120, 90), "stone": (125, 125, 125), "red": (160, 40, 40), "white": (225, 225, 225),
            "orange": (200, 110, 30), "black": (30, 30, 30), "blue": (50, 60, 160), "green": (70, 110, 40),
            "yellow": (220, 190, 50), "purple": (110, 50, 140), "pink": (220, 140, 170), "brown": (110, 75, 45),
            "gray": (80, 80, 80), "lime": (110, 190, 40), "cyan": (40, 140, 150), "light_blue": (100, 170, 220),
            "leaves": (60, 120, 40), "nether": (110, 20, 20)}


def color_of(state):
    b = state.split("[")[0].replace("minecraft:", "")
    if b in COL:
        return COL[b]
    for k, c in WOODCOL.items():
        if b.startswith(k + "_") or b.startswith("stripped_" + k):
            if "leaves" in b:
                return (230, 150, 180) if k == "cherry" else STONECOL["leaves"]
            return c
    for k, c in STONECOL.items():
        if k in b:
            return c
    h = hashlib.md5(b.encode()).digest()
    return (h[0] // 2 + 60, h[1] // 2 + 60, h[2] // 2 + 60)


def render(t, path, scale=6, cut_y=None, flip=False):
    blocks = t.blocks
    if flip and blocks:
        mx = max(p[0] for p in blocks); mz = max(p[2] for p in blocks)
        blocks = {(mx - x, y, mz - z): v for (x, y, z), v in blocks.items()}
    if not blocks:
        return
    xs = [p[0] for p in blocks]; ys = [p[1] for p in blocks]; zs = [p[2] for p in blocks]
    X, Y, Z = max(xs) + 1, max(ys) + 1, max(zs) + 1
    W = (X + Z) * scale * 2 + 20
    H = (X + Z) * scale + Y * scale * 2 + 40
    img = Image.new("RGB", (W, H), (245, 245, 240))
    d = ImageDraw.Draw(img)
    ox, oy = Z * scale * 2 + 10, Y * scale * 2 + 20
    order = sorted(blocks, key=lambda p: (p[0] + p[2], p[1]))
    for (x, y, z) in order:
        if cut_y is not None and y > cut_y:
            continue
        st = blocks[(x, y, z)][0]
        c = color_of(st)
        if c is None:
            continue
        # proyección isométrica: cara superior, izquierda, derecha
        px = ox + (x - z) * scale * 2
        py = oy + (x + z) * scale - y * scale * 2
        s = scale
        top = [(px, py), (px + 2 * s, py + s), (px, py + 2 * s), (px - 2 * s, py + s)]
        left = [(px - 2 * s, py + s), (px, py + 2 * s), (px, py + 4 * s), (px - 2 * s, py + 3 * s)]
        right = [(px + 2 * s, py + s), (px, py + 2 * s), (px, py + 4 * s), (px + 2 * s, py + 3 * s)]
        thin = any(k in st for k in ("_pane", "_carpet", "_slab", "_stairs", "fence", "door", "lantern", "flower_pot", "potted"))
        f = 0.85 if thin else 1.0
        d.polygon(top, fill=tuple(int(v * f) for v in c))
        d.polygon(left, fill=tuple(int(v * 0.75 * f) for v in c))
        d.polygon(right, fill=tuple(int(v * 0.6 * f) for v in c))
    img.save(path)


def render_many(ts, path, scale=4, cols=4, cut_y=None, flip=False):
    import os, tempfile
    ims = []
    for t in ts:
        p = tempfile.mktemp(suffix=".png")
        render(t, p, scale=scale, cut_y=cut_y, flip=flip)
        ims.append(Image.open(p))
    if not ims:
        return
    w = max(i.width for i in ims); h = max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (w * min(cols, len(ims)), h * rows), (255, 255, 255))
    for k, im in enumerate(ims):
        out.paste(im, ((k % cols) * w, (k // cols) * h))
    out.save(path)
