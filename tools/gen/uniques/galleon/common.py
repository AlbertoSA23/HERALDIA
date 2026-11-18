"""Shared galleon utilities: design coordinates (y=0 is sea level) and small pieces."""
import random

SC = 64            # ship's centerline (X)
ANCHOR = (SC, 0, 31)   # waterline at midship: it sits at the world's sea level
ZMIN = -12         # north face of the template (entrance)

DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
VDIR = {v: k for k, v in DIRV.items()}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


class Construction:
    """Template wrapper with a record of ruin, surface and circuits."""

    def __init__(self, t):
        self.t = t
        self.rng = random.Random(1588)
        self.ruin_piece = set()        # hand-damaged cells (holes, tears, barnacles)
        self.surface = set()   # celdas de obra expuesta (casco, cubiertas, velas)
        self.circuits = []       # escenarios de redstone a comprobar
        self.torn = {}         # tear in each sail column
        t.lint_open = {}       # puzzle doors opened for the walkthrough

    # --- basics
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def g(self, x, y, z):
        return self.t.get(x, y, z)

    def fill(self, x1, y1, z1, x2, y2, z2, st):
        self.t.fill(x1, y1, z1, x2, y2, z2, st)

    def air(self, x1, y1, z1, x2, y2, z2):
        self.t.fill(x1, y1, z1, x2, y2, z2, "air")

    def smash(self, x, y, z, st="air"):
        """Hand-made ruin damage: counts toward the damaged-surface percentage."""
        self.s(x, y, z, st)
        self.ruin_piece.add((x, y, z))

    # --- piezas
    def door(self, x, y, z, facing, mat="spruce", hinge="left"):
        for half, dy in (("lower", 0), ("upper", 1)):
            self.s(x, y + dy, z, f"{mat}_door[facing={facing},half={half},hinge={hinge},open=false,powered=false]")

    def flight(self, x, z, y0, d, n, mat="spruce", width=1, support="spruce_planks"):
        """Flight of n steps rising toward d from foot level y0. Clears the head space and fills the support."""
        dx, dz = DIRV[d]
        sx, sz = (dz != 0, dx != 0)   # width axis
        for w in range(width):
            for i in range(n):
                X, Y, Z = x + dx * i + sx * w, y0 + i, z + dz * i + sz * w
                self.s(X, Y, Z, f"{mat}_stairs[facing={d},half=bottom,shape=straight,waterlogged=false]")
                self.air(X, Y + 1, Z, X, Y + 2, Z)
                for yy in range(y0, Y):
                    self.s(X, yy, Z, support)

    def ladder(self, x, z, y1, y2, facing):
        for y in range(y1, y2 + 1):
            self.s(x, y, z, f"ladder[facing={facing},waterlogged=false]")

    def lantern_hang(self, x, y, z):
        self.s(x, y, z, "lantern[hanging=true,waterlogged=false]")

    def chest(self, x, y, z, facing, loot):
        self.s(x, y, z, f"chest[facing={facing},type=single,waterlogged=false]",
               {"id": "minecraft:chest", "LootTable": f"heraldia:unicas/galeon/{loot}"})

    def barrel(self, x, y, z, loot=None, facing="up"):
        n = {"id": "minecraft:barrel"}
        if loot:
            n["LootTable"] = f"heraldia:unicas/galeon/{loot}"
        self.s(x, y, z, f"barrel[facing={facing},open=false]", n)

    def spawner(self, x, y, z, mob, dark=False):
        data = {"entity": {"id": f"minecraft:{mob}"}}
        if dark:   # drowned out of the water: their own light rules instead of the water ones
            data["custom_spawn_rules"] = {"block_light_limit": {"min_inclusive": 0, "max_inclusive": 7},
                                          "sky_light_limit": {"min_inclusive": 0, "max_inclusive": 7}}
        self.s(x, y, z, "spawner", {"id": "minecraft:mob_spawner", "SpawnData": data, "Delay": 20})

    def table(self, x, y, z, cloth="white_carpet"):
        self.s(x, y, z, "spruce_fence")
        self.s(x, y + 1, z, cloth)

    def chair(self, x, y, z, back):
        """Chair: a step with the backrest (high side) toward back."""
        self.s(x, y, z, f"spruce_stairs[facing={back},half=bottom,shape=straight,waterlogged=false]")

    def bed(self, x, y, z, facing, color="red"):
        """Bed with the head at (x,y,z) facing facing; the foot behind."""
        dx, dz = DIRV[facing]
        self.s(x, y, z, f"{color}_bed[facing={facing},occupied=false,part=head]")
        self.s(x - dx, y, z - dz, f"{color}_bed[facing={facing},occupied=false,part=foot]")

    def sign(self, x, y, z, facing, keys, langs):
        msgs = [{"translate": k, "fallback": langs[k]} if k else "" for k in keys]
        text = {"messages": msgs, "color": "black", "has_glowing_text": False}
        empty = {"messages": ["", "", "", ""], "color": "black", "has_glowing_text": False}
        self.s(x, y, z, f"spruce_wall_sign[facing={facing},waterlogged=false]",
               {"id": "minecraft:sign", "front_text": text, "back_text": empty, "is_waxed": True})

    def dispenser(self, x, y, z, facing, arrows=12):
        self.s(x, y, z, f"dispenser[facing={facing},triggered=false]",
               {"id": "minecraft:dispenser", "Items": [{"Slot": _B(0), "id": "minecraft:arrow", "count": arrows}]})


def _B(v):
    from core import B
    return B(v)
