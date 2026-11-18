"""Estructura única «Sagrario del Vacío» (End, islas exteriores, lejos de la isla central y del dragón): el santuario de
una orden que adoraba el vacío entre las islas. Una plantilla rígida de 33 x 33: una plataforma de ladrillo de piedra
del End con un anillo de ocho pilares de púrpura coronados de varas del End, tres capillas en las esquinas (el relicario,
la capilla de los endermites con su generador y la sacristía) y una cuarta sin puerta a la vista (la cripta oculta, tras
una puerta de pistones con palanca), y en medio el templo (unicas/_recinto): pasillo con trampa de placa y flechas, nave
del Hierofante (el guardián, un evocador con fases), cámara del tesoro tras una puerta de hierro con botones y el coro
alto con la biblioteca.

Se coloca con heraldia:dimension (dimensiones.py): el centro y las esquinas deben estar sobre una isla (nada de vacío
debajo) y a más de 1.024 bloques del centro del End. Botín sin romper el progreso: ni élitros, ni nada del dragón, ni
netherita (dimensiones.PROHIBIDO); a lo sumo un caparazón de shulker."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot, pieces
from uniques._common.chest_loot import pool
from uniques import _enclosure as r
import dimensions

SID = "sagrario_vacio"
P = f"unicas/{SID}"
NSP = f"heraldia:{P}"
DIMENSION = dimensions.END
SIDE = 33
HEIGHT = r.HEIGHT + 2
BIOME_MAP = ["end_highlands", "end_midlands"]

STRUCTURE = dict(biomes=[f"minecraft:{b}" for b in BIOME_MAP], start_pool=f"{P}/inicio", size=1, max_distance=40,
                 terrain_adaptation="beard_thin", step="surface_structures", spacing=125, separation=95,
                 json=dimensions.structure(f"{P}/inicio", [f"minecraft:{b}" for b in BIOME_MAP], 1, 40,
                                             dimensions.END, 12, HEIGHT + dimensions.SLACK))
DISPLAY_NAME = {"es_es": "Sagrario del Vacío", "en_us": "Sanctum of the Void"}
MAP = {"decoration": "minecraft:red_x"}
REINFORCEMENTS = ["vindicator", "stray"]      # jefes.py: los que llama el Hierofante al bajar del 66 % y del 33 %
TROPHY = {"objeto": "ender_eye", "rareza": "epic",
          "nombre": ("Ojo del Hierofante", "The Hierophant's Eye"),
          "lore": [("Miraba al vacío hasta que el vacío le devolvió la mirada.",
                    "It gazed into the void until the void gazed back.")]}
STORY = {
    "cofre": "oculto",
    "relato": [
        ("Más allá del dragón, en las islas que flotan sobre la nada, una orden levantó un sagrario de púrpura. Rezaban"
         " al vacío entre las islas y su hierofante me enseñó a orientarme por las varas que brillan.",
         "Beyond the dragon, on the islands that float above nothing, an order raised a sanctum of purpur. They prayed"
         " to the void between the islands, and their hierophant taught me to find my way by the shining rods."),
        ("Le confié mi pliego y lo selló en la cripta oculta. Cuando me fui, el hierofante seguía mirando al vacío. Dicen"
         " que ya no parpadea y que los espíritus le obedecen.",
         "I entrusted him with my leaf and he sealed it in the hidden crypt. When I left, the hierophant was still"
         " staring into the void. They say he no longer blinks and that the spirits obey him."),
    ],
    "pista": ("el End, más allá del dragón, donde un sagrario de púrpura rodeado de pilares mira al vacío",
              "the End, beyond the dragon, where a purpur sanctum ringed with pillars gazes into the void"),
}
ADVANCEMENT = {"icono": "minecraft:purpur_pillar"}

_T = {
    "guardian": ("Hierofante del Vacío", "Hierophant of the Void"),
    "baculo": ("Báculo del Coro", "Choir Staff"),
    "corona": ("Diadema del Vacío", "Void Diadem"),
}
LANG = chest_loot.lang(f"heraldia.{SID}.", _T)


def text(k):
    return pieces.text(f"heraldia.{SID}.{k}", _T[k][0])


LOOT = {
    "premium": chest_loot.cofre(
        ((3, 5), [item("ender_pearl", 10, 2, 5), item("diamond", 3, 1, 2), item("emerald", 6, 2, 6),
                  item("amethyst_shard", 6, 3, 8), item("shulker_shell", 1), item("golden_apple", 4),
                  item("book", 4, ench=(15, 25)), item("experience_bottle", 4, 2, 5),
                  chest_loot.named("golden_helmet", 3, f"heraldia.{SID}.corona", _T["corona"][0], levels=(10, 20)),
                  item("spire_armor_trim_smithing_template", 2), item("music_disc_otherside", 1)]),
        ((1, 2), [item("ender_eye", 3, 1, 2), item("diamond", 2), item("emerald", 4, 1, 3), empty(6)])),
    "cuartel": chest_loot.cofre(((2, 4), [item("chorus_fruit", 8, 2, 6), item("popped_chorus_fruit", 5, 1, 4),
                                     item("arrow", 6, 4, 10), item("candle", 5, 1, 3), item("iron_ingot", 5, 1, 3),
                                     item("ender_pearl", 3, 1, 2), empty(5)]),
                           ((1, 1), [item("gold_ingot", 3, 1, 2), item("emerald", 3, 1, 2), empty(8)])),
    "relicario": chest_loot.cofre(((2, 4), [item("amethyst_shard", 6, 2, 6), item("candle", 5, 1, 3), item("gold_ingot", 4, 1, 3),
                                       item("end_rod", 4, 1, 3), item("ender_eye", 2),
                                       chest_loot.named("blaze_rod", 1, f"heraldia.{SID}.baculo", _T["baculo"][0]),
                                       item("purple_banner", 2), empty(4)]),
                             ((1, 1), [item("emerald", 3, 1, 3), item("golden_apple", 1), empty(8)])),
    "sacristia": chest_loot.cofre(((2, 4), [item("chorus_fruit", 8, 2, 6), item("glass_bottle", 5, 1, 3), item("candle", 5, 1, 3),
                                       item("purple_wool", 4, 1, 3), item("iron_nugget", 5, 2, 6), empty(5)]),
                             ((1, 1), [item("ender_pearl", 3), item("emerald", 2), empty(8)])),
    "forja": chest_loot.table(pool((1, 3), [item("iron_nugget", 6, 2, 6), item("gold_nugget", 6, 2, 6), item("purpur_block", 5, 2, 6),
                                       item("end_rod", 3, 1, 2), item("chorus_fruit", 4, 1, 3), empty(6)])),
    "biblioteca": chest_loot.cofre(((2, 4), [item("paper", 8, 2, 6), item("book", 6, 1, 3), item("book", 3, rand_ench=True),
                                        item("map", 3), item("ink_sac", 4, 1, 3), item("feather", 4, 1, 3), empty(5)]),
                              ((1, 1), [item("experience_bottle", 3, 1, 3), item("ender_pearl", 2), empty(8)])),
    "oculto": chest_loot.cofre(((2, 4), [item("ender_pearl", 6, 1, 3), item("amethyst_shard", 6, 3, 8), item("diamond", 1),
                                    item("emerald", 5, 1, 4), item("ender_eye", 3), item("obsidian", 3, 1, 3), empty(4)]),
                          ((1, 1), [item("golden_apple", 2), item("experience_bottle", 3, 2, 4), empty(6)])),
}

PALETTE = dict(piso="purpur_block", muro="purpur_block", esquina="purpur_pillar[axis=y]", forjado="end_stone_bricks",
              almena="end_stone_brick_wall", puerta="birch_door", columna="purpur_pillar[axis=y]", tesoro="purpur_pillar[axis=y]")
CHAPEL = dict(PALETTE, muro="end_stone_bricks", piso="end_stone_bricks", forjado="purpur_block", almena="purpur_slab")
PLATAFORMA = ["minecraft:end_stone_bricks", "minecraft:end_stone_bricks", "minecraft:purpur_block",
              "minecraft:end_stone_bricks", "minecraft:purpur_pillar[axis=y]"]
PILLARS = [(6, 3), (16, 2), (26, 3), (30, 16), (26, 29), (16, 30), (6, 29), (2, 16)]


def cofre(t, x, y, z, facing, tbl, kind="chest"):
    if kind == "barrel":
        t.barrel(x, y, z, facing="up", loot=f"{NSP}/{tbl}")
    else:
        pieces.chest(lambda *a, **k: t.set(*a, **k), x, y, z, facing, f"{NSP}/{tbl}")


def guardian():
    k = text("guardian")
    return pieces.guardian("evoker", k["translate"], k["fallback"], 70.0, armor=4,
                           attributes={"knockback_resistance": 0.3})


def construction():
    t = Template(f"{P}/sagrario")
    n = SIDE - 1
    # plataforma con aire encima y un borde de losas
    for x in range(SIDE):
        for z in range(SIDE):
            edge_block = x in (0, n) or z in (0, n)
            t.set(x, 0, z, "minecraft:purpur_block" if edge_block else PLATAFORMA[(x * 5 + z * 11 + x * z) % len(PLATAFORMA)])
            for y in range(1, 10):
                t.set(x, y, z, "air", keep=True)
            if edge_block and (x + z) % 4 == 0 and not 14 <= x <= 18:
                t.set(x, 1, z, "end_stone_brick_wall")
    # anillo de pilares con varas del End (la luz del vacío)
    for x, z in PILLARS:
        for y in range(1, 7):
            t.set(x, y, z, "purpur_pillar[axis=y]")
        t.set(x, 7, z, "end_rod[facing=up]")
    # capillas de las esquinas
    r.tower(t, CHAPEL, 0, 0, 5, (4, 2, "east"), merlon=False)
    cofre(t, 2, 1, 1, "south", "relicario")
    t.set(1, 1, 3, "candle[candles=4,lit=true,waterlogged=false]")
    r.tower(t, CHAPEL, n - 4, 0, 5, (n - 4, 2, "west"), merlon=False)
    pieces.spawner(t.set, n - 2, 1, 2, "endermite")
    r.tower(t, CHAPEL, 0, n - 4, 5, (4, n - 2, "east"), merlon=False)
    cofre(t, 2, 1, n - 1, "north", "sacristia")
    cofre(t, 1, 1, n - 1, "north", "forja", "barrel")
    abierta = r.hidden(t, CHAPEL, n - 4, n - 4)
    cofre(t, n - 2, 1, n - 1, "north", "oculto")
    t.set(n - 1, 1, n - 3, "candle[candles=2,lit=true,waterlogged=false]")
    # el templo en medio
    r.great_tower(t, PALETTE, 9, 10, cofre, guardian())
    for x in (12, 20):                                    # escalinata de la portada
        t.set(x, 1, 8, "end_rod[facing=up]")
    pieces.connect(t)
    t.lint_open = abierta
    t.jigsaw(16, 0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
             final_state="minecraft:purpur_block")
    return t


def build(reg):
    t = construction()
    reg.add(t, f"unica:{SID}")
    reg.pool(f"{P}/inicio", [(t.name, 1, "rigid", None)])
