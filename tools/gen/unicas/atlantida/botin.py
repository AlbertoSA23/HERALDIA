"""Botín de la Atlántida: más alto que el del resto de estructuras únicas, sin netherita, élitros ni maza."""
from .._comun import botin as CB
from .._comun.botin import item, empty, pool, table
from . import cosas as C


def _libro(ench, nivel, w):
    return CB.book(w, {"minecraft:" + ench: nivel})


MARINO = [item("prismarine_shard", 10, 2, 8), item("prismarine_crystals", 8, 2, 6), item("nautilus_shell", 5, 1, 2),
          item("cooked_cod", 8, 2, 5), item("cooked_salmon", 8, 2, 5), item("dried_kelp", 6, 3, 8), item("gold_ingot", 8, 1, 4),
          item("iron_ingot", 8, 2, 5), item("emerald", 8, 1, 4), item("lapis_lazuli", 5, 3, 8), item("sea_pickle", 4, 1, 3)]
VALIOSO = [item("diamond", 8, 1, 3), item("emerald", 8, 3, 8), item("gold_block", 3), item("sponge", 5, 1, 2),
           item("experience_bottle", 6, 3, 8), item("golden_apple", 4, 1, 2), item("name_tag", 2), item("heart_of_the_sea", 1),
           _libro("respiration", 3, 3), _libro("depth_strider", 3, 3), _libro("aqua_affinity", 1, 3), _libro("impaling", 4, 2),
           _libro("loyalty", 2, 2), _libro("mending", 1, 1), item("diamond_helmet", 2, ench=(15, 25)), item("diamond_boots", 2, ench=(15, 25)),
           item("turtle_helmet", 2), item("tide_armor_trim_smithing_template", 1), item("coast_armor_trim_smithing_template", 1)]


def _sello(cual):
    t = C.tabla_llave(cual)
    t["pools"] += [pool((3, 5), VALIOSO), pool((2, 3), VALIOSO, extra=True)]
    return t


def tablas():
    """Todas con un grupo extra solo_sin_lootr (con Lootr cada jugador recibe solo lo fijo)."""
    return {
        "menor": table(pool((3, 5), MARINO), pool(1, [item("diamond", 2), CB.potion("water_breathing", 3), empty(6)] + VALIOSO[:3]),
                       pool((1, 2), MARINO, extra=True)),
        "media": table(pool((3, 5), MARINO), pool((1, 2), VALIOSO), pool((1, 2), VALIOSO, extra=True)),
        "tesoro": table(pool((4, 6), VALIOSO), pool(1, [item("trident", 1), item("diamond", 3, 2, 5), item("enchanted_golden_apple", 1)]),
                        pool((2, 3), VALIOSO, extra=True)),
        "arca": table(pool((4, 6), VALIOSO), pool(2, [item("golden_apple", 3, 1, 2), item("experience_bottle", 3, 8, 16), item("diamond", 3, 2, 4)]),
                      pool((2, 3), VALIOSO, extra=True)),
        "sello_arsenal": _sello("arsenal"), "sello_academia": _sello("academia"), "sello_anfiteatro": _sello("anfiteatro"),
        "jefe": C.tabla_llave("poseidon"),
    }


def _nombre(clave, es, en):
    return C.nombre_objeto("premium." + clave, es, en, "gold")


TESORO = {"heraldia_tesoro": "atlantida"}   # custom_data de los objetos con nombre: logro unicas/atlantida/tesoro


def premium():
    """Contenido fijo del cofre premium: [(objeto, cantidad, componentes)]. Es único: no lleva tabla de botín. Los
    objetos con nombre llevan además custom_data TESORO (el logro del tesoro los reconoce)."""
    return [(o, n, dict(c, **{"minecraft:custom_data": TESORO}) if c else c) for o, n, c in _premium()]


def _premium():
    def ench(**e):
        return {"minecraft:" + k: v for k, v in e.items()}
    return [
        ("trident", 1, {"minecraft:custom_name": _nombre("poseidon", "Tridente de Poseidón", "Trident of Poseidon"),
                        "minecraft:enchantments": ench(loyalty=3, channeling=1, impaling=5, unbreaking=3, mending=1)}),
        ("trident", 1, {"minecraft:custom_name": _nombre("mareas", "Tridente de las Mareas", "Trident of the Tides"),
                        "minecraft:enchantments": ench(riptide=3, impaling=5, unbreaking=3, mending=1)}),
        ("conduit", 1, None),
        ("heart_of_the_sea", 3, None),
        ("enchanted_golden_apple", 2, None),
        ("totem_of_undying", 1, None),
        ("turtle_helmet", 1, {"minecraft:custom_name": _nombre("yelmo", "Yelmo de las Profundidades", "Helm of the Deep"),
                              "minecraft:enchantments": ench(respiration=3, aqua_affinity=1, protection=4, unbreaking=3, mending=1)}),
        ("diamond_boots", 1, {"minecraft:custom_name": _nombre("botas", "Botas de la Corriente", "Boots of the Current"),
                              "minecraft:enchantments": ench(depth_strider=3, feather_falling=4, unbreaking=3, mending=1)}),
        ("diamond_spear", 1, {"minecraft:custom_name": _nombre("lanza", "Lanza de Tritón", "Triton's Spear"),
                              "minecraft:enchantments": ench(lunge=3, sharpness=4, unbreaking=3)}),
        ("diamond_nautilus_armor", 1, None),
        ("tide_armor_trim_smithing_template", 2, None),
        ("music_disc_otherside", 1, None),
        ("wet_sponge", 8, None),
        ("nautilus_shell", 16, None),
        ("diamond", 12, None),
        ("emerald_block", 4, None),
        ("gold_block", 8, None),
        ("experience_bottle", 32, None),
    ]
