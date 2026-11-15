"""La Atlántida: una sola por mundo, sumergida en un océano grande (docs/unicas/atlantida.md).

Ciudad de plano fijo de 768 x 768 en 3 x 3 distritos. El tipo de estructura heraldia:atlantida (Java) coloca la pieza
base (agua, pavimento, zócalo y muralla) y las teselas de 32 x 32 que salen de cortar el plano construido en ciudad.py.
"""
from . import urbanismo as U
from . import ciudad
from . import cosas

ID = "unicas/atlantida"
NOMBRE = {"es_es": "La Atlántida", "en_us": "Atlantis"}
STRUCTURE = dict(
    placement={"type": "heraldia:mundial"},   # siempre una, sin configuración
    json={
        "type": "heraldia:atlantida", "biomes": ["minecraft:deep_frozen_ocean", "minecraft:deep_cold_ocean", "minecraft:deep_ocean",
                   "minecraft:deep_lukewarm_ocean", "minecraft:frozen_ocean", "minecraft:ocean", "minecraft:cold_ocean",
                   "minecraft:lukewarm_ocean", "minecraft:warm_ocean"], "step": "surface_structures",
        "terrain_adaptation": "none",
        "spawn_overrides": {
            "monster": {"bounding_box": "full", "spawns": [{"type": "minecraft:guardian", "weight": 1, "count": {"type": "minecraft:uniform", "min_inclusive": 2, "max_inclusive": 4}}]},
            "underground_water_creature": {"bounding_box": "full", "spawns": []},
            "axolotls": {"bounding_box": "full", "spawns": []}},
        "radio": U.RADIO, "suelo": U.SUELO, "base": U.BASE, "techo": U.TECHO, "piezas": [],
    },
)
from . import botin
LANG = cosas.LANG
LOOT = botin.tablas()
# /heraldia llave: la tabla da el mismo objeto que sueltan el guardián y los cofres, y la cerradura es la de los cofres
LLAVES = {cual: {"tabla": cosas.tabla_llave(cual), "cerradura": cosas.cerradura(cual)} for cual in cosas.LLAVES}
_plano = None


def plano():
    global _plano
    if _plano is None:
        _plano = ciudad.construir()
    return _plano


def build(reg):
    from . import auditoria
    reg.warnings.extend(f"atlantida: {a}" for a in auditoria.auditar(plano()))
    piezas = STRUCTURE["json"]["piezas"]
    piezas.clear()
    teselas = list(plano().teselas(ID))
    out = []
    auditoria.jigsaws([t for t, _ in teselas], out)
    reg.warnings.extend(f"atlantida: {a}" for a in out)
    for t, (x, y, z) in teselas:
        reg.templates[t.name] = t
        reg.kinds[t.name] = "unica"
        piezas.append({"plantilla": f"heraldia:{t.name}", "x": x, "y": y, "z": z})
