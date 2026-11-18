"""Floor plans per level (PNG): one cell = one enlarged pixel. Use: python3 -m uniques.atlantis.planos <folder>."""
import os, sys
from PIL import Image
from . import urban_layout as U
from .world import block_name

COLOR = {"water": (58, 110, 190), "air": (250, 240, 170), None: (20, 30, 60), "stone": (95, 95, 95),
         "prismarine_bricks": (70, 150, 135), "dark_prismarine": (35, 85, 75), "prismarine": (95, 160, 150),
         "sea_lantern": (230, 245, 240), "gravel": (130, 125, 120), "quartz_bricks": (235, 230, 225), "quartz_pillar": (235, 230, 225),
         "chiseled_quartz_block": (235, 230, 225), "light_blue_stained_glass": (150, 200, 240), "spawner": (200, 40, 40),
         "chest": (240, 150, 30), "trapped_chest": (240, 100, 30), "barrel": (160, 110, 60), "kelp": (40, 130, 60),
         "kelp_plant": (40, 130, 60), "ladder": (150, 110, 60), "warped_door": (40, 200, 190), "iron_door": (220, 220, 220)}


def color(st):
    b = block_name(st)
    if b in COLOR:
        return COLOR[b]
    if b and "coral" in b:
        return (220, 90, 150)
    if b and ("sign" in b or "bookshelf" in b or "bed" in b or "table" in b or "lectern" in b):
        return (170, 120, 70)
    if b and ("redstone" in b or "lever" in b or "dispenser" in b or "plate" in b or "tnt" in b):
        return (220, 30, 30)
    return (110, 120, 125)


def blueprint(m, y, route, box=None, scale=2):
    x1, z1, x2, z2 = box or (-U.SIDE, -U.SIDE, U.SIDE - 1, U.SIDE - 1)
    img = Image.new("RGB", (x2 - x1 + 1, z2 - z1 + 1))
    px = img.load()
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            px[x - x1, z - z1] = color(m.get(x, y, z))
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(route)


def view(m, site_name, route, scale=3, y_min=None):
    """Isometric render of what is built in a site's box (without water or air)."""
    import render
    from core import Template
    _, x1, y1, z1, x2, y2, z2, _ = next(s for s in m.sites if s[0] == site_name)
    y1 = y1 if y_min is None else max(y1, y_min)
    t = Template(site_name)
    for (x, y, z), (st, _) in m.blocks.items():
        if x1 <= x <= x2 and y1 <= y <= y2 and z1 <= z <= z2 and block_name(st) not in ("air", "water", "bubble_column"):
            t.blocks[(x - x1, y - y1, z - z1)] = (st, None)
    render.render(t, route, scale=scale)


LEVELS = (("n1_plantas_altas_y38", 38, None), ("n0_calle_y33", 33, None), ("n-1_galerias_y15", 15, (-176, -176, 175, 175)),
           ("n-2_camaras_y-5", -5, (-16, -40, 111, 71)), ("n-2_cripta_y-12", -12, (40, -8, 103, 39)))
VIEWS = (("templo", 2), ("agora", 3), ("termas", 3), ("academia", 3), ("arsenal", 3), ("anfiteatro", 3), ("jardines", 3),
          ("puerto", 3), ("lonja", 4))

if __name__ == "__main__":
    from . import blueprint as _blueprint
    destination = sys.argv[1]
    os.makedirs(destination, exist_ok=True)
    m = _blueprint()
    for name_, y, box in LEVELS:
        blueprint(m, y, os.path.join(destination, f"plano_{name_}.png"), box=box, scale=1 if box is None else 4)
    for site, scale in VIEWS:
        view(m, site, os.path.join(destination, f"vista_{site}.png"), scale, y_min=U.FLOOR)
