"""Atlantis: only one per world, submerged in a large ocean (docs/unicas/atlantis.md).

Fixed-plan city of 768 x 768 in 3 x 3 districts. The structure type heraldia:atlantida (Java) places the base piece
(water, pavement, plinth and wall) and the 32 x 32 tiles obtained by cutting the plan built in city.py.
"""
from . import urban_layout as U
from . import city
from . import things

ID = "unicas/atlantida"
DISPLAY_NAME = {"es_es": "La Atlántida", "en_us": "Atlantis"}
# Guardian's reinforcements in each phase (bosses.py): lookouts and a sentinel with a trident.
REINFORCEMENTS = ["guardian", "guardian", {"mob": "drowned", "equipo": {"mainhand": "trident"}}]
TROPHY = {"objeto": "trident", "rareza": "epic",
          "nombre": ("Tridente de Poseidón", "Trident of Poseidon"),
          "lore": [("Aún huele a sal y a tormenta.", "It still smells of salt and storm."),
                   ("Lo empuñó el último guardián de la ciudad hundida.", "Wielded by the last warden of the sunken city.")],
          "encantamientos": {"minecraft:loyalty": 2, "minecraft:impaling": 2}}   # guardian's trophy (_comun/chest_loot.trophy)
STRUCTURE = dict(
    placement={"type": "heraldia:mundial"},   # always one, without configuration
    json={
        "type": "heraldia:atlantida", "biomes": ["minecraft:deep_frozen_ocean", "minecraft:deep_cold_ocean", "minecraft:deep_ocean",
                   "minecraft:deep_lukewarm_ocean", "minecraft:frozen_ocean", "minecraft:ocean", "minecraft:cold_ocean",
                   "minecraft:lukewarm_ocean", "minecraft:warm_ocean"], "step": "surface_structures",
        "terrain_adaptation": "none",
        "spawn_overrides": {
            "monster": {"bounding_box": "full", "spawns": [{"type": "minecraft:guardian", "weight": 1, "count": {"type": "minecraft:uniform", "min_inclusive": 2, "max_inclusive": 4}}]},
            "underground_water_creature": {"bounding_box": "full", "spawns": []},
            "axolotls": {"bounding_box": "full", "spawns": []}},
        "radio": U.RADIUS, "suelo": U.FLOOR, "base": U.BASE, "techo": U.ROOF, "piezas": [],
    },
)
from . import chest_loot
LANG = things.LANG
LOOT = chest_loot.tables()
# /heraldia key: the table gives the same item that the guardian and the chests drop, and the lock is the chests' one
KEYS = {which: {"tabla": things.key_table(which), "cerradura": things.lock(which)} for which in things.KEYS}
# Advancements (advancements.py): the unique chest has no loot table; obtaining one of its named items counts. Each seal
# counts when opening its chest or having its key (also with Lootr or if another player takes it out). Poseidon's is the guardian.
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "sello_academia",
    "final": True,   # closes the chain: the last sheet points to it and this one points to the first
    "relato": [
        ("Soy Ysolda, la última heraldo de la Atlántida. Nuestra orden trazaba los mapas del mundo y "
         "guardaba los blasones de cada reino. Cuando el mar se tragó la ciudad, salvé lo único que el "
         "océano no debía guardar: el camino de vuelta.",
         "I am Ysolda, last herald of Atlantis. Our order drew the maps of the world and kept the arms of"
         " every realm. When the sea swallowed the city, I saved the one thing the ocean must not keep: "
         "the way back."),
        ("Lo repartí en pliegos y confié cada uno a un guardián que juró custodiarlo hasta que llegara "
         "alguien digno. Sus juramentos sobrevivieron a sus vidas: por eso aún velan. Este pliego se "
         "quedó en casa, en la Academia.",
         "I set it down on leaves and entrusted each to a guardian sworn to keep it until someone worthy "
         "came. Their oaths outlived their lives: that is why they still keep watch. This leaf stayed "
         "home, in the Academy."),
    ],
    "pista": ("el océano más hondo, donde una ciudad de mármol duerme bajo las olas",
              "the deepest ocean, where a marble city sleeps beneath the waves"),
}
ADVANCEMENT = {
    "icono": "minecraft:trident",
    "tesoro": (),
    "tesoro_objeto": {"predicates": {"minecraft:custom_data": chest_loot.TREASURE}},
    "extra": [{
        "id": f"sello_{which}", "icono": "minecraft:nautilus_shell", "xp": 30,
        "titulo": (things.KEYS[which][0].replace("Llave", "Sello"), things.KEYS[which][1].replace("Key", "Seal")),
        "descripcion": (f"Abre el cofre del sello o consigue la {things.KEYS[which][0]}",
                        f"Open the seal chest or obtain the {things.KEYS[which][1]}"),
        "criterios": {
            "cofre": {"trigger": "minecraft:player_generates_container_loot",
                      "conditions": {"loot_tables": f"heraldia:unicas/atlantida/sello_{which}"}},
            "llave": {"trigger": "minecraft:inventory_changed",
                      "conditions": {"items": [{"items": things.KEY_ITEM, "predicates": things.lock(which)["predicates"]}]}}},
        "requisitos": [["cofre", "llave"]],
    } for which in ("arsenal", "academia", "anfiteatro")],
}
_blueprint = None


def blueprint():
    global _blueprint
    if _blueprint is None:
        _blueprint = city.construct()
    return _blueprint


def build(reg):
    from . import audit
    reg.warnings.extend(f"atlantida: {a}" for a in audit.audit_it(blueprint()))
    pieces = STRUCTURE["json"]["piezas"]
    pieces.clear()
    tiles = list(blueprint().tiles(ID))
    out = []
    audit.jigsaws([t for t, _ in tiles], out)
    reg.warnings.extend(f"atlantida: {a}" for a in out)
    for t, (x, y, z) in tiles:
        reg.templates[t.name] = t
        reg.kinds[t.name] = "unica"
        pieces.append({"plantilla": f"heraldia:{t.name}", "x": x, "y": y, "z": z})
