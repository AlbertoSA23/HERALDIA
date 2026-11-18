"""Estructura única «Ciudadela de Ceniza» (Nether): la fortaleza de un mariscal que se negó a volver al mundo de arriba,
en los deltas de basalto y el valle de las almas. Una plantilla rígida de 35 x 35: muralla de ladrillo de piedra negra
pulida con portón al norte y cuatro torres en las esquinas (armería, jaula de los blazes con su generador, despensa y
una torre sin puerta a la vista: la sala oculta, tras una puerta de pistones con palanca), patio con la forja y braseros
de almas, y en medio el torreón (unicas/_recinto): pasillo con trampa de placa y flechas, salón del Mariscal (el
guardián, con fases), cámara del tesoro tras una puerta de hierro con botones y planta alta con la biblioteca.

Se coloca con heraldia:dimension (dimensiones.py): el suelo se busca bajo el techo de bedrock, con aire para toda la
altura de la plantilla, y el terreno se ajusta a la caja (beard_thin). Botín sin romper el progreso: ni equipo de
netherita, ni lingotes, ni restos antiguos; como mucho un fragmento de netherita en el cofre premium (el tesoro de un
bastión da hasta uno por cofre), lo comprueba dimensiones.fragmentos_de_mas."""
from core import Template, B, F
from loot import item, empty
from uniques._common import chest_loot, pieces
from uniques._common.chest_loot import pool, table
from uniques import _enclosure as r
import dimensions

SID = "ciudadela_ceniza"
P = f"unicas/{SID}"
NSP = f"heraldia:{P}"
DIMENSION = dimensions.NETHER
SIDE = 35
HEIGHT = r.HEIGHT + 2          # alto de la plantilla (y = 0 a 12)
BIOME_MAP = ["basalt_deltas", "soul_sand_valley"]

STRUCTURE = dict(biomes=[f"minecraft:{b}" for b in BIOME_MAP], start_pool=f"{P}/inicio", size=1, max_distance=40,
                 terrain_adaptation="beard_thin", step="surface_structures", spacing=100, separation=76,
                 json=dimensions.structure(f"{P}/inicio", [f"minecraft:{b}" for b in BIOME_MAP], 1, 40,
                                             dimensions.NETHER, 10, HEIGHT + dimensions.SLACK))
DISPLAY_NAME = {"es_es": "Ciudadela de Ceniza", "en_us": "Ashen Citadel"}
MAP = {"decoration": "minecraft:red_x"}
REINFORCEMENTS = ["wither_skeleton", {"mob": "skeleton", "equipo": {"mainhand": "bow"}}]     # jefes.py: los que llama el Mariscal al bajar del 66 % y del 33 %
TROPHY = {"objeto": "golden_sword", "rareza": "epic",
          "nombre": ("Hoja de Brasa del Mariscal", "The Marshal's Ember Blade"),
          "lore": [("Forjada en la lava que nunca se enfría.", "Forged in lava that never cools."),
                   ("Su dueño no quiso volver a ver el sol.", "Its owner never wished to see the sun again.")],
          "encantamientos": {"minecraft:fire_aspect": 1, "minecraft:sharpness": 2}}
STORY = {
    "cofre": "oculto",
    "relato": [
        ("Crucé el portal tras el rastro de un heraldo perdido. En los deltas de basalto, entre la ceniza, se alza una"
         " ciudadela de piedra negra. Su mariscal juró guardar la frontera del Nether y no volvió jamás.",
         "I crossed the portal on the trail of a lost herald. In the basalt deltas, amid the ash, rises a citadel of"
         " black stone. Its marshal swore to guard the border of the Nether and never came back."),
        ("Me dejó dormir en su torre oculta, junto a la forja, y guardó mi pliego allí. Dicen que la ceniza se le metió"
         " en los huesos y que hoy solo obedece a los blazes de su jaula.",
         "He let me sleep in his hidden tower, by the forge, and kept my leaf there. They say the ash crept into his"
         " bones and that today he obeys only the blazes in his cage."),
    ],
    "pista": ("el Nether, donde una ciudadela de piedra negra se alza entre la ceniza del basalto",
              "the Nether, where a citadel of black stone rises amid the basalt ash"),
}
ADVANCEMENT = {"icono": "minecraft:polished_blackstone_bricks"}

_T = {
    "guardian": ("Mariscal de Ceniza", "Marshal of Ash"),
    "lanza": ("Lanza del Centinela", "Sentinel's Lance"),
    "yelmo": ("Yelmo de Brasa", "Ember Helm"),
}
LANG = chest_loot.lang(f"heraldia.{SID}.", _T)


def text(k):
    return pieces.text(f"heraldia.{SID}.{k}", _T[k][0])


LOOT = {
    "premium": chest_loot.cofre(
        ((3, 5), [item("gold_ingot", 10, 2, 6), item("gold_block", 2), item("quartz", 6, 4, 10), item("diamond", 3, 1, 2),
                  item("blaze_rod", 6, 1, 3), item("magma_cream", 4, 2, 4), item("netherite_scrap", 1),
                  item("golden_apple", 4), item("book", 4, ench=(15, 25)),
                  chest_loot.named("golden_helmet", 3, f"heraldia.{SID}.yelmo", _T["yelmo"][0], levels=(10, 20)),
                  item("snout_armor_trim_smithing_template", 2), item("music_disc_pigstep", 1)]),
        ((1, 2), [item("gold_ingot", 6, 2, 4), item("diamond", 2), item("golden_carrot", 4, 2, 5), empty(6)])),
    "cuartel": chest_loot.cofre(((2, 4), [item("arrow", 8, 4, 12), item("bone", 6, 2, 6), item("coal", 6, 2, 6),
                                     item("gold_nugget", 8, 3, 9), item("cooked_porkchop", 5, 1, 3),
                                     item("crossbow", 2, dmg=(0.4, 0.8)), item("iron_ingot", 3, 1, 3), empty(5)]),
                           ((1, 1), [item("gold_ingot", 3, 1, 2), item("spectral_arrow", 3, 2, 6), empty(8)])),
    "armeria": chest_loot.cofre(((2, 4), [item("golden_sword", 4, dmg=(0.2, 0.6)), item("golden_axe", 3, dmg=(0.2, 0.6)),
                                     item("iron_sword", 3, dmg=(0.2, 0.6)), item("chainmail_chestplate", 2),
                                     item("shield", 3), item("arrow", 6, 4, 10), item("iron_ingot", 4, 1, 4),
                                     chest_loot.named("iron_sword", 1, f"heraldia.{SID}.lanza", _T["lanza"][0], levels=(5, 15)),
                                     empty(4)]),
                           ((1, 1), [item("gold_ingot", 3), item("iron_ingot", 3, 1, 3), empty(8)])),
    "despensa": chest_loot.cofre(((2, 4), [item("cooked_porkchop", 8, 1, 4), item("golden_carrot", 3, 1, 3),
                                      item("crimson_fungus", 5, 1, 3), item("warped_fungus", 5, 1, 3),
                                      item("nether_wart", 6, 2, 6), item("glass_bottle", 4, 1, 3), empty(5)]),
                            ((1, 1), [item("gold_nugget", 5, 2, 6), item("golden_apple", 1), empty(8)])),
    "forja": chest_loot.table(pool((1, 3), [item("gold_nugget", 8, 2, 7), item("iron_nugget", 6, 2, 6), item("coal", 6, 1, 4),
                                       item("magma_cream", 4, 1, 3), item("blaze_powder", 3, 1, 2), empty(6)])),
    "biblioteca": chest_loot.cofre(((2, 4), [item("paper", 8, 2, 6), item("book", 6, 1, 3), item("book", 3, rand_ench=True),
                                        item("map", 3), item("glowstone_dust", 5, 2, 5), item("ink_sac", 4, 1, 3),
                                        empty(5)]),
                              ((1, 1), [item("experience_bottle", 3, 1, 3), item("gold_ingot", 2), empty(8)])),
    "oculto": chest_loot.cofre(((2, 4), [item("gold_ingot", 6, 1, 4), item("blaze_rod", 4, 1, 2), item("quartz", 6, 3, 8),
                                    item("obsidian", 4, 1, 3), item("fire_charge", 4, 1, 3), item("diamond", 1),
                                    empty(4)]),
                          ((1, 1), [item("golden_apple", 2), item("experience_bottle", 3, 2, 4), empty(6)])),
}

PALETTE = dict(piso="polished_blackstone_bricks", muro="polished_blackstone_bricks", esquina="polished_basalt[axis=y]",
              forjado="polished_blackstone", almena="polished_blackstone_brick_wall", puerta="crimson_door",
              columna="polished_basalt[axis=y]", tesoro="gilded_blackstone")
COURTYARD = ["minecraft:smooth_basalt", "minecraft:polished_blackstone", "minecraft:blackstone",
         "minecraft:polished_blackstone_bricks", "minecraft:smooth_basalt"]


def cofre(t, x, y, z, facing, tbl, kind="chest"):
    if kind == "barrel":
        t.barrel(x, y, z, facing="up", loot=f"{NSP}/{tbl}")
    else:
        pieces.chest(lambda *a, **k: t.set(*a, **k), x, y, z, facing, f"{NSP}/{tbl}")


def guardian():
    k = text("guardian")
    return pieces.guardian("wither_skeleton", k["translate"], k["fallback"], 80.0, armor=6,
                           equipment={"mainhand": {"id": "minecraft:golden_sword", "count": 1,
                                                   "components": {"minecraft:enchantments": {"minecraft:fire_aspect": 1}}},
                                      "head": {"id": "minecraft:golden_helmet", "count": 1}},
                           drop_chances={"mainhand": 0.05, "head": 0.1}, attributes={"knockback_resistance": 0.4})


def construction():
    t = Template(f"{P}/ciudadela")
    p = PALETTE
    n = SIDE - 1
    # patio: suelo variado y aire explícito encima (el terreno no asoma dentro de la muralla)
    for x in range(SIDE):
        for z in range(SIDE):
            t.set(x, 0, z, COURTYARD[(x * 7 + z * 13 + x * z) % len(COURTYARD)])
            for y in range(1, 9):
                t.set(x, y, z, "air", keep=True)
    # muralla y portón al norte
    for x in range(SIDE):
        for z in range(SIDE):
            if x in (0, n) or z in (0, n):
                for y in range(1, 7):
                    t.set(x, y, z, p["muro"])
    r.battlements(t, 0, 0, n, n, 7, p["almena"])
    for x in (16, 17, 18):
        for y in (1, 2, 3, 4):
            t.set(x, y, 0, "air")
    for x in (15, 19):
        for y in range(1, 8):
            t.set(x, y, 0, p["esquina"])
        r.lantern(t, x, 8, 0, hanging=False)
    # torres de las esquinas
    r.tower(t, p, 0, 0, 8, (4, 2, "east"))
    cofre(t, 2, 1, 1, "south", "armeria")
    t.set(1, 1, 3, "smithing_table")
    r.tower(t, p, n - 4, 0, 8, (n - 4, 2, "west"))
    pieces.spawner(t.set, n - 2, 1, 2, "blaze")
    r.tower(t, p, 0, n - 4, 8, (4, n - 2, "east"))
    cofre(t, 2, 1, n - 1, "north", "despensa", "barrel")
    cofre(t, 1, 1, n - 1, "north", "despensa")
    abierta = r.hidden(t, p, n - 4, n - 4)
    cofre(t, n - 2, 1, n - 1, "north", "oculto")
    t.set(n - 1, 1, n - 3, "red_bed[facing=north,occupied=false,part=head]")
    t.set(n - 1, 1, n - 2, "red_bed[facing=north,occupied=false,part=foot]")
    # el torreón en medio
    r.great_tower(t, p, 10, 12, cofre, guardian())
    # forja del patio (al oeste del torreón) y braseros de almas
    t.set(5, 1, 14, "lava_cauldron")
    t.set(5, 1, 16, "anvil[facing=north]")
    t.set(6, 1, 14, "blast_furnace[facing=east,lit=false]")
    cofre(t, 5, 1, 18, "east", "forja", "barrel")
    for x, z in ((8, 4), (26, 4), (8, 30), (26, 30), (30, 16), (4, 24)):
        t.set(x, 1, z, p["esquina"])
        t.set(x, 2, z, "soul_campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    pieces.connect(t)
    t.lint_open = abierta
    t.jigsaw(17, 0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
             final_state="minecraft:polished_blackstone_bricks")
    return t


def build(reg):
    t = construction()
    reg.add(t, f"unica:{SID}")
    reg.pool(f"{P}/inicio", [(t.name, 1, "rigid", None)])
