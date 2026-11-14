"""Herramientas de obra sobre una plantilla global (coordenadas: x este, z sur, y = 0 el enlosado)."""
from core import Template

NS_LOOT = "heraldia:unicas/acueducto/"
FACE = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


class Obra:
    def __init__(self):
        self.t = Template("acueducto/global")
        self.sup = 0          # superficie construida en planta (celdas)
        self.ruina = 0        # parte de esa superficie con daños
        self.red = {}         # elementos de redstone con nombre -> posición

    # --- básico ---
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def g(self, x, y, z):
        return self.t.get(x, y, z)

    def f(self, x1, y1, z1, x2, y2, z2, st):
        self.t.fill(x1, y1, z1, x2, y2, z2, st)

    def air(self, x1, y1, z1, x2, y2, z2):
        self.t.fill(x1, y1, z1, x2, y2, z2, "air")

    def ring(self, x0, z0, x1, z1, y0, y1, st):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.s(x, y, z0, st); self.s(x, y, z1, st)
            for z in range(z0, z1 + 1):
                self.s(x0, y, z, st); self.s(x1, y, z, st)

    def solid(self, x, y, z):
        st = self.g(x, y, z)
        return st is not None and not st.startswith("minecraft:air")

    # --- piezas de mobiliario y carpintería ---
    def stair(self, x, y, z, facing, mat="smooth_sandstone_stairs", half="bottom"):
        self.s(x, y, z, f"{mat}[facing={facing},half={half},shape=straight,waterlogged=false]")

    def slab(self, x, y, z, typ="bottom", mat="smooth_sandstone_slab"):
        self.s(x, y, z, f"{mat}[type={typ},waterlogged=false]")

    def door(self, x, z, facing, y=1, mat="spruce_door", hinge="left"):
        for half, dy in (("lower", 0), ("upper", 1)):
            self.s(x, y + dy, z, f"{mat}[facing={facing},half={half},hinge={hinge},open=false,powered=false]")

    def lantern(self, x, y, z, soul=False):
        self.s(x, y, z, ("soul_lantern" if soul else "lantern") + "[hanging=true,waterlogged=false]")

    def chest(self, x, y, z, facing, tabla):
        self.t.chest(x, y, z, facing, NS_LOOT + tabla)

    def barrel(self, x, y, z, tabla=None):
        self.t.barrel(x, y, z, "up", NS_LOOT + tabla if tabla else None)

    def pot(self, x, y, z, facing="north"):
        self.s(x, y, z, f"decorated_pot[cracked=false,facing={facing},waterlogged=false]")

    def bed(self, x, y, z, facing, color="red"):
        dx, dz = FACE[facing]
        self.s(x, y, z, f"{color}_bed[facing={facing},occupied=false,part=foot]")
        self.s(x + dx, y, z + dz, f"{color}_bed[facing={facing},occupied=false,part=head]")

    def sign(self, x, y, z, facing, lines, mat="spruce"):
        """Rótulo de pared con textos traducibles: lines = [(clave, respaldo)] (hasta 4)."""
        msgs = [{"translate": k, "fallback": fb} for k, fb in lines]
        msgs += [{"text": ""}] * (4 - len(msgs))
        nbt = {"id": "minecraft:sign", "is_waxed": True,
               "front_text": {"messages": msgs, "color": "black", "has_glowing_text": False},
               "back_text": {"messages": [{"text": ""}] * 4, "color": "black", "has_glowing_text": False}}
        self.s(x, y, z, f"{mat}_wall_sign[facing={facing},waterlogged=false]", nbt)

    def spawner(self, x, y, z, mob):
        nbt = {"id": "minecraft:mob_spawner", "SpawnData": {"entity": {"id": "minecraft:" + mob}},
               "SpawnPotentials": [{"weight": 1, "data": {"entity": {"id": "minecraft:" + mob}}}]}
        self.s(x, y, z, "spawner", nbt)

    def dispenser(self, x, y, z, facing, n=24):
        from core import B
        nbt = {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": n}]}
        self.s(x, y, z, f"dispenser[facing={facing},triggered=false]", nbt)

    def brush(self, x, y, z):
        self.s(x, y, z, "suspicious_sand[dusted=0]",
               {"id": "minecraft:brushable_block", "LootTable": "minecraft:archaeology/desert_pyramid"})

    # --- cubiertas ---
    def tejado(self, x0, z0, x1, z1, y, eje, mat="brick_slab", hastial="smooth_sandstone", hueco=None):
        """Tejado de poca pendiente (media losa por bloque). Rectángulo con alero incluido; eje = cumbrera."""
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if hueco and hueco(x, z):
                    continue
                d = min(x - x0, x1 - x) if eje == "z" else min(z - z0, z1 - z)
                yy = y + d // 2
                self.slab(x, yy, z, "bottom" if d % 2 == 0 else "top", mat)
                ends = (z in (z0 + 1, z1 - 1) and x0 < x < x1) if eje == "z" else (x in (x0 + 1, x1 - 1) and z0 < z < z1)
                if ends:
                    for k in range(y, yy):
                        self.s(x, k, z, hastial)

    def plano(self, x0, z0, x1, z1, y, mat="brick_slab"):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.slab(x, y, z, "bottom", mat)
