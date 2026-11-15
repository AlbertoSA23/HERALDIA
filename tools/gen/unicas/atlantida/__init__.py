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
        "type": "heraldia:atlantida", "biomes": "#minecraft:is_ocean", "step": "surface_structures",
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
# Logros (logros.py): el cofre único no tiene tabla de botín; cuenta conseguir uno de sus objetos con nombre. Cada sello
# cuenta al abrir su cofre o al tener su llave (también con Lootr o si otro jugador la saca). El de Poseidón es el guardián.
LOGRO = {
    "icono": "minecraft:trident",
    "tesoro": (),
    "tesoro_objeto": {"predicates": {"minecraft:custom_data": botin.TESORO}},
    "extra": [{
        "id": f"sello_{cual}", "icono": "minecraft:nautilus_shell", "xp": 30,
        "titulo": (cosas.LLAVES[cual][0].replace("Llave", "Sello"), cosas.LLAVES[cual][1].replace("Key", "Seal")),
        "descripcion": (f"Abre el cofre del sello o consigue la {cosas.LLAVES[cual][0]}",
                        f"Open the seal chest or obtain the {cosas.LLAVES[cual][1]}"),
        "criterios": {
            "cofre": {"trigger": "minecraft:player_generates_container_loot",
                      "conditions": {"loot_tables": f"heraldia:unicas/atlantida/sello_{cual}"}},
            "llave": {"trigger": "minecraft:inventory_changed",
                      "conditions": {"items": [{"items": cosas.OBJETO_LLAVE, "predicates": cosas.cerradura(cual)["predicates"]}]}}},
        "requisitos": [["cofre", "llave"]],
    } for cual in ("arsenal", "academia", "anfiteatro")],
}
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
