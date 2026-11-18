"""Ciudadela enana: ciudad excavada en una montaña con la puerta en la ladera (ver docs/unicas/ciudadela.md).

Una sola plantilla colocada por el tipo de estructura propio heraldia:ciudadela (Java), que orienta la puerta
hacia donde baja la ladera y comprueba que la ciudad quede bajo la roca. El generador escribe en el JSON la
entrada y la rejilla de techos que usa esa comprobación.
"""
import functools
from .botin import TABLES as LOOT
from . import plano, auditoria

NOMBRE = {"es_es": "Ciudadela enana", "en_us": "Dwarven Citadel"}
TROFEO = {"objeto": "iron_axe", "rareza": "rare",
          "nombre": ("Hacha de Borin Barbahierro", "Borin Ironbeard's Axe"),
          "lore": [("Ha partido roca, hierro y orgullo de trasgo.", "It has cleaved stone, iron and goblin pride.")],
          "encantamientos": {"minecraft:efficiency": 3, "minecraft:unbreaking": 2}}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/STORY.md, _comun/botin.historia_*)
    "cofre": "real",
    "relato": [
        ("Subí a las cumbres de piedra hasta la ciudadela que los enanos excavaron en la montaña. Borin "
         "Barbahierro me invitó a una jarra en la cervecería y me habló de vetas, de forjas y de su rey "
         "bajo la montaña.",
         "I climbed the stony peaks to the citadel the dwarves carved into the mountain. Borin Ironbeard "
         "stood me a tankard in the brewery and told me of veins, of forges and of his king beneath the "
         "mountain."),
        ("Los enanos guardan bien lo que se mete en la roca. Borin escondió el pliego en la cámara real y"
         " juró ser el último en abandonar la ciudadela. Cumplió: nunca salió de ella.",
         "Dwarves keep well what is set in stone. Borin hid the leaf in the royal chamber and swore to be"
         " the last to leave the citadel. He kept his word: he never left."),
    ],
    "pista": ("las cumbres de piedra, donde los enanos excavaron una ciudadela en la roca",
              "the stony peaks, where dwarves carved a citadel into the rock"),
}
LOGRO = {"icono": "minecraft:iron_pickaxe"}   # logros.py
ROOF_CELL = 8
PORCH_DEPTH = 8          # filas del pórtico (z < 8): al aire libre, no cuentan para la cubierta de roca

LANG = {
    "es_es": {
        "heraldia.ciudadela.guardian": "Borin Barbahierro, último guardián",
        "item.heraldia.ciudadela.hacha": "Hacha de Borin",
        "item.heraldia.ciudadela.yelmo": "Yelmo del Rey Bajo la Montaña",
        "item.heraldia.ciudadela.jarra": "Jarra de la última cerveza",
        "item.heraldia.ciudadela.pico": "Pico del maestro minero",
        "item.heraldia.ciudadela.pico_diamante": "Pico de la veta profunda",
        "item.heraldia.ciudadela.peto": "Peto de la guardia real",
        "item.heraldia.ciudadela.corona": "Corona del rey enano",
    },
    "en_us": {
        "heraldia.ciudadela.guardian": "Borin Ironbeard, the Last Warden",
        "item.heraldia.ciudadela.hacha": "Borin's Axe",
        "item.heraldia.ciudadela.yelmo": "Helm of the King Under the Mountain",
        "item.heraldia.ciudadela.jarra": "Mug of the Last Ale",
        "item.heraldia.ciudadela.pico": "Master Miner's Pickaxe",
        "item.heraldia.ciudadela.pico_diamante": "Pickaxe of the Deep Vein",
        "item.heraldia.ciudadela.peto": "Royal Guard Chestplate",
        "item.heraldia.ciudadela.corona": "Crown of the Dwarf King",
    },
}

# Degradación (ver auditoria.ruin_ratio): ~15-20 % de la superficie visible queda en mal estado.
DEGRADE = {"deepslate_bricks": ("cracked_deepslate_bricks", 0.25), "deepslate_tiles": ("cracked_deepslate_tiles", 0.20),
           "polished_deepslate": ("cobbled_deepslate", 0.10), "polished_blackstone_bricks": ("cracked_polished_blackstone_bricks", 0.20)}
PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + a, "probability": p},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + b}
    for a, (b, p) in DEGRADE.items()]}]}


@functools.lru_cache(maxsize=None)
def datos():
    """Plantilla normalizada, sus metadatos y el resultado de la auditoría propia."""
    from pack import fix_supports
    pl = plano.construir()
    t = pl.t
    fix_supports(t)
    x0, y0, z0, *_ = t.bounds()
    t.normalize()
    pl.shift = (x0, y0, z0)
    sh = lambda p: (p[0] - x0, p[1] - y0, p[2] - z0)
    pl.lint_open = {sh(p): s for p, s in pl.lint_open.items()}
    pl.marks = {k: sh(p) for k, p in pl.marks.items()}
    pl.ruina = {sh(p) for p in pl.ruina}
    for c in pl.circuits.values():
        for k, v in list(c.items()):
            if isinstance(v, tuple):
                c[k] = sh(v)
            elif isinstance(v, list):
                c[k] = [sh(p) for p in v]
            elif isinstance(v, dict) and all(isinstance(p, tuple) for p in v.values()):
                c[k] = {n: sh(p) for n, p in v.items()}
    t.lint_open = pl.lint_open
    j = t.jigsaws[0]["pos"]
    entrance = (j[0], j[1] + 1, j[2])
    sx, sy, sz = t.size()
    top = {}
    for (x, y, z) in t.blocks:
        if y > top.get((x, z), -1):
            top[(x, z)] = y
    nx, nz = -(-sx // ROOF_CELL), -(-sz // ROOF_CELL)
    roof = []
    for j_ in range(nz):
        for i in range(nx):
            v = -1
            if (j_ + 1) * ROOF_CELL > PORCH_DEPTH:
                for x in range(i * ROOF_CELL, min(sx, (i + 1) * ROOF_CELL)):
                    for z in range(max(PORCH_DEPTH, j_ * ROOF_CELL), min(sz, (j_ + 1) * ROOF_CELL)):
                        v = max(v, top.get((x, z), -1))
            roof.append(v)
    errors = auditoria.auditar(pl)
    return pl, dict(entrance=entrance, roof=roof, roof_width=nx), errors


def _structure():
    pl, meta, _ = datos()
    return {"type": "heraldia:ciudadela", "biomes": ["minecraft:stony_peaks", "minecraft:jagged_peaks"],
            "step": "underground_structures", "spawn_overrides": {}, "terrain_adaptation": "none",
            "start_pool": "heraldia:unicas/ciudadela/inicio", "entrance": list(meta["entrance"]),
            "roof_cell": ROOF_CELL, "roof_width": meta["roof_width"], "roof": meta["roof"]}


class _Lazy(dict):
    """STRUCTURE con el JSON calculado al leerlo (la plantilla se construye una sola vez)."""
    def get(self, k, default=None):
        if k == "json":
            return _structure()
        return super().get(k, default)

    def __getitem__(self, k):
        return self.get(k) if k == "json" else super().__getitem__(k)


STRUCTURE = _Lazy(start_pool="unicas/ciudadela/inicio", size=1, max_distance=1,
                  terrain_adaptation="none", step="underground_structures", spacing=250, separation=190)


def build(reg):
    pl, meta, errors = datos()
    reg.warnings.extend(f"ciudadela: {e}" for e in errors)
    name = reg.add(pl.t, "unica:ciudadela")
    reg.pool("unicas/ciudadela/inicio", [(name, 1, "rigid", PROCESSORS)])
