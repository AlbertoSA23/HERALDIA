"""El pozo maestro y el castillete de la Mina perdida (las piezas que el tipo heraldia:mina apila sobre la colonia).

- `pozo` (7 x 8 x 7) y `pozo_corto` (7 x 1 x 7): tramos del pozo. Hueco de 3 x 3 con la escalera de mano al oeste y la
  cadena de la cubeta en el eje, forro de tablas (con un marco de troncos cada 4 bloques) y 1 bloque de piedra por
  fuera: el pozo atraviesa cuevas y acuíferos sin abrirse a ellos. Java pone tantos tramos de 8 como quepan y el resto
  de 1, de la cara superior de la colonia a los cimientos del castillete.
- `castillete`: el castillete de madera sobre el brocal (de donde cuelga la cadena), la casa del malacate con un cofre y
  la escombrera, sobre un cimiento de adoquín de 6 bloques que absorbe un terreno desigual; aire explícito encima de
  toda la huella para que la ladera no tape nada.
Coordenadas con el eje del pozo en (0, 0); y = 0 es la capa de suelo del castillete (los pies a 1).
"""
from core import Template, B
from .._common.pieces import chest, text
from .construction import S, stair, slab, h, LOOT, K, SID

SHAFT_HEIGHT = 8
FOUNDATION = 6                         # capas de cimiento bajo el suelo del castillete
FOOTPRINT = (-4, 9, -4, 4)              # x0, x1, z0, z1 respecto al eje
AIR_BLOCK = 12                            # aire explícito sobre la huella


def section(put, y, frame=False):
    """Una capa del pozo: hueco, escalera, cadena, forro y piedra."""
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            r = max(abs(dx), abs(dz))
            if r <= 1:
                put(dx, y, dz, "air")
            elif r == 2:
                side = abs(dx) == 2 and abs(dz) < 2 or abs(dz) == 2 and abs(dx) < 2
                put(dx, y, dz, S("stripped_spruce_log", axis="z" if abs(dx) == 2 else "x") if frame and side
                    else "spruce_planks")
            else:
                put(dx, y, dz, "stone")
    put(-1, y, 0, S("ladder", facing="east", waterlogged=False))
    put(0, y, 0, S("iron_chain", axis="y", waterlogged=False))


def well(height, name):
    t = Template(f"unicas/{SID}/{name}")
    for y in range(height):
        section(t.set, y, frame=(height > 1 and y % 4 == 0))
    t.normalize()
    return t


class Headframe:
    def __init__(self):
        self.t = Template(f"unicas/{SID}/castillete")
        self.signs = []
        self.chests = []

    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def build(self):
        x0, x1, z0, z1 = FOOTPRINT
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                for y in range(-FOUNDATION, 0):
                    self.s(x, y, z, "cobblestone")
                self.s(x, 0, z, "gravel" if h(x, z, 31) < 0.45 else ("cobblestone" if h(x, z, 32) < 0.6 else "dirt_path"))
                for y in range(1, AIR_BLOCK + 1):
                    self.s(x, y, z, "air")
        for y in range(-FOUNDATION, 1):                                   # el pozo atraviesa el cimiento
            section(lambda x, yy, z, st: self.s(x, yy, z, st) if max(abs(x), abs(z)) <= 2 else None, y)
        self.s(-1, 0, 0, S("ladder", facing="east", waterlogged=False))
        # brocal: muro bajo de adoquín alrededor de la boca, abierto junto a la escalera
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if max(abs(dx), abs(dz)) == 2 and (dx, dz) != (-2, 0):
                    self.s(dx, 1, dz, "cobblestone_wall")
        for x in range(-2, 3):                                           # tablones de la boca (salvo el hueco)
            for z in range(-2, 3):
                if max(abs(x), abs(z)) == 2:
                    self.s(x, 0, z, "spruce_planks")
        # el castillete: cuatro pies derechos, vigas a y = 9, la viga maestra a y = 10 y la cadena hasta el fondo
        for (px, pz) in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
            for y in range(1, 10):
                self.s(px, y, pz, S("spruce_log", axis="y"))
        for d in range(-2, 3):
            for z in (-3, 3):
                self.s(d, 9, z, S("spruce_log", axis="x"))
            for x in (-3, 3):
                self.s(x, 9, d, S("spruce_log", axis="z"))
        for x in (-3, 3):
            self.s(x, 10, 0, S("spruce_log", axis="y"))
        for x in range(-2, 3):
            self.s(x, 10, 0, S("spruce_log", axis="x"))
        for x in range(-3, 4):                                           # tejadillo a dos aguas sobre la viga
            self.s(x, 11, -1, stair("spruce", "south"))
            self.s(x, 11, 1, stair("spruce", "north"))
            self.s(x, 11, 0, slab("spruce"))
        for (px, pz, f) in ((-2, -3, "east"), (2, -3, "west"), (-2, 3, "east"), (2, 3, "west")):
            self.s(px, 8, pz, stair("spruce", f, "top"))                 # tornapuntas
        for y in range(1, 10):
            self.s(0, y, 0, S("iron_chain", axis="y", waterlogged=False))
        # casa del malacate: el torno de la cadena, el cofre del capataz de superficie
        hx0, hx1, hz0, hz1 = 5, 9, -2, 2
        for x in range(hx0, hx1 + 1):
            for z in range(hz0, hz1 + 1):
                edge_block = x in (hx0, hx1) or z in (hz0, hz1)
                self.s(x, 0, z, "spruce_planks")
                for y in range(1, 4):
                    corner_block = x in (hx0, hx1) and z in (hz0, hz1)
                    self.s(x, y, z, S("spruce_log", axis="y") if corner_block else ("cobblestone" if edge_block else "air"))
                self.s(x, 4, z, slab("spruce"))
        for (x, y, z, f) in ((hx0, 1, 0, "west"),):
            for hh, dy in (("lower", 0), ("upper", 1)):
                self.s(x, y + dy, z, S("spruce_door", facing="west", half=hh, hinge="left", open=False, powered=False))
        for (x, z) in ((7, hz0), (7, hz1)):
            self.s(x, 2, z, "glass_pane")
        for z in (-1, 0, 1):                                             # el tambor del torno, al fondo
            self.s(8, 2, z, S("stripped_spruce_log", axis="z"))
        self.s(8, 1, -1, "spruce_fence")
        self.s(8, 1, 1, "spruce_fence")
        chest(self.s, 6, 1, -1, "south", LOOT + "malacate")
        self.chests.append(((6, 1, -1), "malacate"))
        self.s(6, 1, 1, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
        self.s(6, 3, 0, S("lantern", hanging=True, waterlogged=False))
        # escombrera junto a la casa y un cartel a la entrada
        for (x, y, z) in ((5, 1, 3), (6, 1, 3), (7, 1, 3), (6, 1, 4), (7, 1, 4), (8, 1, 4), (6, 2, 4), (7, 2, 3)):
            self.s(x, y, z, "gravel")
        self.signs.append(("castillete", [("Mina Hondavena", "Hondavena Mine"), ("Pozo maestro", "Master shaft"),
                                          ("Cerrada por", "Closed by order"), ("orden real", "of the Crown")]))
        msgs = [text(f"{K}cartel.castillete.{i + 1}", es) for i, (es, _) in enumerate(self.signs[-1][1])]
        self.s(-4, 1, -2, S("spruce_sign", rotation=4, waterlogged=False),
               {"id": "minecraft:sign", "is_waxed": B(1),
                "front_text": {"messages": msgs, "color": "black", "has_glowing_text": B(0)},
                "back_text": {"messages": [{"text": ""}] * 4, "color": "black", "has_glowing_text": B(0)}})
        self.ruin = {(-2, 1, 2), (3, 9, 1)}                              # una piedra del brocal caída, una viga rota
        self.s(-2, 1, 2, "air")
        self.s(3, 9, 1, "air")
        self.s(-3, 0, 3, "cobblestone")
        return self
