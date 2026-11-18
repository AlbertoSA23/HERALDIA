"""Wizard hut (heraldia:medianas/choza_mago/<estilo>, T43): 17 x 17 courtyard with a 9 x 9 hut with a steep roof
and an attic. Ground floor: bookshelves, lectern with the wizard's notes, study chest, counter with potion stands,
amethyst cluster and candles, cauldrons, rug and a fireplace with a campfire and a flue up to the roof; attic via a
ladder: bed, chest, cobwebs and the star map (two banners on the gables). Variant a: fenced herb and mushroom garden
to the east and the wizard's cat; b: circle of stones with candles, mushrooms and amethyst to the east and terraces in front of the
door. The swamp style goes on piles (the hut 3 blocks above the ground, with a staircase up).

The wizard (stationary cleric villager, with fixed trades: bottles, lapis lazuli, potions, a modest enchanted book and ender
pearls) carries the tag heraldia_mago. The Java side (chozas/) decides with the seed and the hut whether he is evil
(wizard_huts.prob_malvado) and, if so, he reveals himself when a player approaches or tries to trade: he turns into the
"Mago Malvado" (an evoker with the phases and the boss bar), with his own loot (tools/gen/wizard_huts.py)."""
from core import Template, B
from loot import item, empty
from uniques._common import chest_loot
from . import _common as c

MID = "choza_mago"
DISPLAY_NAME = {"es_es": "Choza de mago", "en_us": "Wizard's Hut"}
SEPARATION = 1024
ADVANCEMENT_ICON = "minecraft:brewing_stand"
# Looks for the same interior of the same biomes as the mine entrances (taigas, hills, peaks, cherry grove, desert): without
# this it would take the spot from the mine next to it (mines always yield to medium structures). This way it yields.
YIELDS_TO_MINES = True
TAG_WIZARD = "heraldia_mago"           # the tag the Java side looks for (chozas/Magos.TAG)
TAG_EVIL = "heraldia_mago_malvado"  # that of the evoker it turns into (chozas/Magos.EVIL)
_K = f"heraldia.medianas.{MID}."
LANG = chest_loot.lang(_K, {
    "mago": ("Mago de Heraldia", "Heraldia Wizard"),
    "gato": ("Sombra", "Shadow"),
    "notas": ("Notas del mago", "The Wizard's Notes"),
    "notas.p1": ("Las estrellas de esta noche, otra vez torcidas. Anoto: la amatista canta más con luna nueva y las "
                 "setas del jardín no son para la sopa.",
                 "Tonight's stars, crooked again. Note: amethyst sings louder at the new moon and the mushrooms in the "
                 "garden are not for soup."),
    "notas.p2": ("Algunos de mi gremio venden su alma por un poco de poder. Si un mago te sonríe demasiado, viajero, "
                 "no le des la espalda.",
                 "Some of my guild sell their souls for a little power. If a wizard smiles at you too much, traveller, "
                 "do not turn your back."),
})
ADVANCEMENTS = [
    dict(id="tratos", icono="minecraft:potion", marco="task",
         titulo=("Aprendiz de brujería", "Sorcerer's Apprentice"),
         descripcion=("Comercia con el mago de una choza de mago", "Trade with the wizard of a wizard's hut"),
         criterios={"trato": {"trigger": "minecraft:villager_trade", "conditions": {"villager": {
             "type": "minecraft:entity_properties", "entity": "this",
             "predicate": {"minecraft:entity_tags": {"all_of": [TAG_WIZARD]}}}}}}),
    dict(id="malvado", icono="minecraft:totem_of_undying", marco="challenge",
         titulo=("Ni magia ni trucos", "No Tricks Left"),
         descripcion=("Vence a un mago malvado escondido en una choza de mago",
                      "Defeat an evil wizard hiding in a wizard's hut"),
         criterios={"malvado": {"trigger": "minecraft:player_killed_entity", "conditions": {"entity": {
             "type": "minecraft:entity_properties", "entity": "this",
             "predicate": {"minecraft:entity_type": "minecraft:evoker",
                           "minecraft:entity_tags": {"all_of": [TAG_EVIL]}}}}}}),
]
_NOTES = chest_loot.written_book([{"translate": _K + "notas.p1", "fallback": LANG["es_es"][_K + "notas.p1"]},
                      {"translate": _K + "notas.p2", "fallback": LANG["es_es"][_K + "notas.p2"]}],
                     {"translate": _K + "notas", "fallback": LANG["es_es"][_K + "notas"]},
                     LANG["es_es"][_K + "notas"], "Mago")
LOOT = {
    "estudio": chest_loot.place_chest(((3, 5), [item("book", 8, 1, 3), item("paper", 8, 2, 6), item("glass_bottle", 8, 1, 4),
                                     item("lapis_lazuli", 7, 2, 6), item("redstone", 5, 2, 6),
                                     item("glowstone_dust", 4, 1, 4), item("amethyst_shard", 5, 1, 3),
                                     item("feather", 4, 1, 3), item("ink_sac", 4, 1, 2), item("candle", 4, 1, 3),
                                     item("nether_wart", 3, 1, 3), item("blaze_powder", 1), empty(4)]),
                           ((1, 1), [item("experience_bottle", 4, 1, 3), item("book", 3, rand_ench=True),
                                     item("emerald", 4, 1, 3), item("ender_pearl", 1), empty(6)])),
    "desvan": chest_loot.place_chest(((2, 4), [item("string", 8, 2, 5), item("cobweb", 3, 1, 2), item("candle", 6, 1, 3),
                                    item("brown_mushroom", 5, 1, 3), item("red_mushroom", 5, 1, 3),
                                    item("spider_eye", 5, 1, 2), item("sugar", 5, 1, 4), item("bone", 5, 1, 3),
                                    item("gunpowder", 3, 1, 2), item("fermented_spider_eye", 2),
                                    item("phantom_membrane", 1), item("rabbit_foot", 1), empty(4)]),
                          ((1, 1), [_NOTES, item("name_tag", 1), item("emerald", 3, 1, 2), empty(8)])),
}

WIDTH = DEPTH = 17
X0, Z0, X1, Z1 = 2, 5, 10, 13      # hut walls (9 x 9); door to the north at CX
CX = 6
GX0, GX1 = 12, 16                  # the east annex (garden or circle), from z = Z0 to Z1


def _p(n, s):
    return f"{s}[facing={n},half=bottom,shape=straight,waterlogged=false]"


def _potion(pid):
    return {"id": "minecraft:potion", "count": 1, "components": {"minecraft:potion_contents": {"potion": f"minecraft:{pid}"}}}


def _book(ench, level):
    return {"id": "minecraft:enchanted_book", "count": 1,
            "components": {"minecraft:stored_enchantments": {f"minecraft:{ench}": level}}}


def offers(p):
    """The wizard's trades: bottles, lapis lazuli, three potions of the style, a modest book and ender pearls."""
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    potions = [c.offer(em(n), _potion(pid), 4) for pid, n in p["pociones"]]
    ench, level = p["libro"]
    return ([c.offer(em(1), {"id": "minecraft:glass_bottle", "count": 4}, 12),
             c.offer(em(1), {"id": "minecraft:lapis_lazuli", "count": 6}, 12)] + potions +
            [c.offer(em(14), _book(ench, level), 2, buy_b={"id": "minecraft:book", "count": 1}),
             c.offer(em(5), {"id": "minecraft:ender_pearl", "count": 1}, 4),
             c.offer({"id": "minecraft:nether_wart", "count": 8}, em(1), 8)])


def wizard(p, rot=180.0):
    n = c.villager(MID, "mago", "Mago de Heraldia", "cleric", p["aldeano"], offers(p), rot=rot)
    n["VillagerData"]["level"] = 4
    n["Xp"] = 150
    n["Tags"] = [TAG_WIZARD]
    return n


def _floor(p):
    mats = p["patio"]
    return lambda x, z: p["senda"] if x == CX and z < Z0 else mats[(x * 7 + z * 5 + x * z) % len(mats)]


def _banner(color, patterns):
    return {"id": "minecraft:banner", "patterns": [{"pattern": f"minecraft:{pt}", "color": col} for pt, col in patterns]}


def _hut(p, name):
    """The whole hut (courtyard, walls, roof, chimney, ground floor and attic). Returns (template, H)."""
    t = Template(name)
    m, H = p["madera"], p.get("pilotes", 0)
    c.courtyard(t, 0, 0, WIDTH - 1, DEPTH - 1, _floor(p), air_block=3)
    c.entrance(t, CX, p["senda"])
    # base: at ground level or on log piles (corners and centers of each side)
    if H:
        for x in (X0, CX, X1):
            for z in (Z0, (Z0 + Z1) // 2, Z1):
                if (x, z) != (CX, (Z0 + Z1) // 2):
                    t.fill(x, 1, z, x, H - 1, z, f"{p['tronco']}[axis=y]")
        for x in range(X0, X1 + 1):            # nothing of the terrain is left under the hut
            for z in range(Z0, Z1 + 1):
                for y in range(1, H):
                    t.set(x, y, z, "air", keep=True)
        # staircase up to the door (from z = Z0 - 3 to Z0 - 1), with its support
        for i in range(H):
            z = Z0 - H + i
            t.set(CX, 1 + i, z, _p("south", f"{m}_stairs"))
            for y in range(1, 1 + i):
                t.set(CX, y, z, f"{m}_planks")
    t.fill(X0, H, Z0, X1, H, Z1, p["zocalo"])
    t.fill(X0 + 1, H, Z0 + 1, X1 - 1, H, Z1 - 1, p["suelo"])
    # walls (ground floor 4 high) and the attic floor at H + 5
    c.box(t, X0, H + 1, Z0, X1, H + 5, Z1, p["muro"], corner_block=f"{p['tronco']}[axis=y]")
    t.fill(X0 + 1, H + 5, Z0 + 1, X1 - 1, H + 5, Z1 - 1, f"{m}_planks")
    c.roof_tiles(t, X0, Z0, X1, Z1, H + 5, p["teja"], p["cumbrera"], p["muro"])
    c.door(t, CX, H + 1, Z0, "south", f"{m}_door")
    for x in (X0 + 2, X1 - 2):
        c.window(t, x, H + 2, Z0, p["vidrio"])
    c.window(t, X0, H + 2, 9, p["vidrio"])
    c.window(t, X1, H + 3, 8, p["vidrio"])
    c.window(t, X0, H + 7, 9, p["vidrio"])       # small attic window in the west gable
    _chimney(t, p, H)
    _ground_floor(t, p, H)
    _attic(t, p, H)
    return t, H


def _chimney(t, p, H):
    """Hearth in the south wall (campfire in a 1 x 2 niche) and a hollow flue up to one block above the ridge."""
    lad, summit = p["chimenea"], H + 11
    t.set(CX, H + 1, Z1, "campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    t.set(CX, H + 1, Z1 - 1, "air")
    t.set(CX, H + 2, Z1 - 1, "air")
    for y in range(H + 2, summit + 1):
        t.set(CX, y, Z1, "air")                  # the flue
    for y in range(H + 1, summit + 1):
        t.set(CX - 1, y, Z1, lad)
        t.set(CX + 1, y, Z1, lad)
    for y in range(1, summit + 1):
        t.set(CX, y, Z1 + 1, lad)                # the outer face, from the ground
    for y in range(H + 3, summit + 1):
        t.set(CX, y, Z1 - 1, lad)                # the hearth hood and the chimney breast in the attic


def _ground_floor(t, p, H):
    y = H + 1
    xo, xe = X0 + 1, X1 - 1                      # x = 3 (west) and x = 9 (east)
    # west: bookshelves, study chest and lectern with the notes under the window
    for z in (Z0 + 1, Z0 + 2, Z1 - 3, Z1 - 2, Z1 - 1):
        t.fill(xo, y, z, xo, y + 2, z, "bookshelf")
    t.set(xo, y + 3, Z0 + 1, "candle[candles=2,lit=true,waterlogged=false]")
    t.set(xo, y + 3, Z1 - 1, "candle[candles=3,lit=true,waterlogged=false]")
    c.place_chest(t, xo, y, Z0 + 3, "east", MID, "estudio")
    t.set(xo, y, Z0 + 4, "lectern[facing=east,has_book=true,powered=false]", {
        "id": "minecraft:lectern", "Page": 0,
        "Book": {"id": "minecraft:written_book", "count": 1, "components": _NOTES["modifier"][0]["components"]}})
    # east: barrel, counter with potion stands, amethyst and candles; ladder to the attic; full cauldron
    t.set(xe, y, Z0 + 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    t.set(xe, y + 1, Z0 + 1, p["maceta"])
    for z in range(Z0 + 2, Z0 + 6):
        t.set(xe, y, z, p["mostrador"])
    t.set(xe, y + 1, Z0 + 2, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]",
          {"id": "minecraft:brewing_stand"})
    t.set(xe, y + 1, Z0 + 3, "amethyst_cluster[facing=up,waterlogged=false]")
    t.set(xe, y + 1, Z0 + 4, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]",
          {"id": "minecraft:brewing_stand"})
    t.set(xe, y + 1, Z0 + 5, "candle[candles=3,lit=true,waterlogged=false]")
    c.ladder(t, xe, Z1 - 2, y, H + 5, "west")
    t.set(xe, y, Z1 - 1, "water_cauldron[level=3]")
    t.set(xo + 1, y, Z1 - 1, "cauldron")
    t.set(CX + 1, y, Z1 - 1, "decorated_pot[cracked=false,facing=north,waterlogged=false]", {"id": "minecraft:decorated_pot"})
    # rug in the center and two lanterns hanging from the attic floor
    t.fill(CX - 1, y, Z0 + 3, CX + 1, y, Z0 + 5, f"{p['alfombra']}_carpet")
    t.set(xo + 1, y, Z0 + 1, p["maceta"])
    c.lantern(t, CX, H + 4, Z0 + 2)
    c.lantern(t, CX, H + 4, Z1 - 3)


def _attic(t, p, H):
    """Attic (feet at H + 6; standing only from z = 7 to 11): bed, chest, cobwebs, amethyst, the star map."""
    y, xo, xe = H + 6, X0 + 1, X1 - 1
    t.set(xe, H + 5, Z1 - 2, "ladder[facing=west,waterlogged=false]")     # the stairwell opening
    c.bed(t, xo, Z0 + 3, "west", p["cama"], y=y)
    c.place_chest(t, xo, y, Z0 + 5, "east", MID, "desvan")
    for x, yy, z in ((xo, y, Z0 + 1), (xe, y, Z0 + 1), (xo, y + 1, Z0 + 2), (xe, y + 1, Z0 + 2), (xo, y, Z1 - 1)):
        t.set(x, yy, z, "cobweb")
    t.set(xe, y, Z0 + 3, "amethyst_cluster[facing=up,waterlogged=false]")
    t.set(xe, y, Z0 + 4, "candle[candles=4,lit=true,waterlogged=false]")
    # star map: two banners hanging from the gables, facing the center
    t.set(xo, H + 8, Z0 + 4, "blue_wall_banner[facing=east]",
          _banner("blue", [("globe", "yellow"), ("border", "black")]))
    t.set(xe, H + 8, Z0 + 4, "black_wall_banner[facing=west]",
          _banner("black", [("flower", "white"), ("circle", "yellow"), ("border", "blue")]))
    c.lantern(t, CX, H + 9, Z0 + 4)


def _terrace(t, x0, z0, x1, z1, land, floors):
    """Raised bed (soil at y = 1, plants at y = 2): the y = 0 courtyard still has no fertile soil."""
    i = 0
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            t.set(x, 1, z, land)
            t.set(x, 2, z, floors[i % len(floors)])
            i += 1


def with_garden(p, name):
    """Variant a: fenced herb and mushroom garden to the east (two beds, lantern on a post) and the wizard's cat."""
    t, H = _hut(p, name)
    m = p["madera"]
    for x in range(GX0, GX1 + 1):
        for z in range(Z0, Z1 + 1):
            if x in (GX0, GX1) or z in (Z0, Z1):
                t.set(x, 1, z, f"{m}_fence")
    t.set((GX0 + GX1) // 2, 1, Z0, f"{m}_fence_gate[facing=north,in_wall=false,open=false,powered=false]")
    _terrace(t, GX0 + 1, Z0 + 2, GX1 - 2, Z0 + 3, p["tierra"], p["hierbas"])
    _terrace(t, GX0 + 1, Z1 - 3, GX1 - 2, Z1 - 2, p["tierra_setas"], p["setas"])
    t.set(GX1, 2, Z0, "lantern[hanging=false,waterlogged=false]")
    t.set(GX0 + 1, 1, Z1 - 1, "composter[level=3]")
    t.entity(CX, H + 1, Z0 + 3, wizard(p))
    t.entity(GX0 + 2, 1, (Z0 + Z1) // 2, c.mob("cat", MID, "gato", "Sombra", rot=270.0, variant="minecraft:all_black",
                                              CollarColor=B(10)))
    return t


def with_circle(p, name):
    """Variant b: circle of stones with candles around an amethyst cluster and four mushrooms to the east, and two
    herb beds in front of the door."""
    t, H = _hut(p, name)
    cx, cz = (GX0 + GX1) // 2, (Z0 + Z1) // 2
    for dx, dz in ((-2, -2), (2, -2), (-2, 2), (2, 2), (0, -3), (0, 3)):
        t.fill(cx + dx, 1, cz + dz, cx + dx, 2, cz + dz, p["piedra"])
        t.set(cx + dx, 3, cz + dz, "candle[candles=1,lit=true,waterlogged=false]")
    t.set(cx, 0, cz, "amethyst_block")
    t.set(cx, 1, cz, "amethyst_cluster[facing=up,waterlogged=false]")
    for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        t.set(cx + dx, 1, cz + dz, p["tierra_setas"])
        t.set(cx + dx, 2, cz + dz, p["setas"][(dx + dz) % len(p["setas"])])
    _terrace(t, X0, 1, CX - 2, 2, p["tierra"], p["hierbas"])
    _terrace(t, CX + 2, 1, X1, 2, p["tierra"], list(reversed(p["hierbas"])))
    t.entity(CX, H + 1, Z0 + 3, wizard(p))
    return t


_VAR = {"a": with_garden, "b": with_circle}
_MUSHROOMS = ["brown_mushroom", "red_mushroom"]
STYLES = {
    "oscuro": dict(biomas=["dark_forest", "pale_garden"], convencionales=["c:is_dark_forest"],
                   paleta=dict(madera="dark_oak", tronco="dark_oak_log", muro="dark_oak_planks", zocalo="cobblestone",
                               suelo="spruce_planks", teja="dark_oak_stairs", cumbrera="dark_oak_planks",
                               chimenea="mossy_cobblestone", vidrio="purple_stained_glass_pane", cama="purple",
                               alfombra="purple", mostrador="stripped_dark_oak_log[axis=z]", maceta="potted_red_mushroom",
                               piedra="mossy_cobblestone", aldeano="plains", tierra="podzol", tierra_setas="podzol",
                               hierbas=["fern", "lily_of_the_valley", "fern", "allium"], setas=_MUSHROOMS,
                               senda="minecraft:dirt_path",
                               patio=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:mossy_cobblestone"],
                               pociones=[("night_vision", 4), ("healing", 3), ("swiftness", 3)],
                               libro=("efficiency", 2)),
                   variantes=_VAR),
    "pantano": dict(biomas=["swamp", "mangrove_swamp"], convencionales=["c:is_swamp"],
                    paleta=dict(madera="mangrove", tronco="mangrove_log", muro="mangrove_planks", zocalo="mangrove_planks",
                                suelo="mangrove_planks", teja="dark_oak_stairs", cumbrera="dark_oak_planks",
                                chimenea="mud_bricks", vidrio="green_stained_glass_pane", cama="green", alfombra="green",
                                mostrador="stripped_mangrove_log[axis=z]", maceta="potted_blue_orchid",
                                piedra="mud_bricks", aldeano="swamp", tierra="podzol", tierra_setas="podzol",
                                hierbas=["blue_orchid", "fern", "blue_orchid", "brown_mushroom"], setas=_MUSHROOMS,
                                senda="minecraft:packed_mud", pilotes=3,
                                patio=["minecraft:packed_mud", "minecraft:muddy_mangrove_roots", "minecraft:gravel"],
                                pociones=[("water_breathing", 4), ("healing", 3), ("leaping", 3)],
                                libro=("respiration", 2)),
                    variantes=_VAR),
    "taiga": dict(biomas=["taiga", "old_growth_pine_taiga", "old_growth_spruce_taiga"],
                  paleta=dict(madera="spruce", tronco="spruce_log", muro="spruce_planks", zocalo="cobblestone",
                              suelo="spruce_planks", teja="spruce_stairs", cumbrera="dark_oak_planks",
                              chimenea="cobblestone", vidrio="glass_pane", cama="red", alfombra="red",
                              mostrador="stripped_spruce_log[axis=z]", maceta="potted_fern", piedra="mossy_cobblestone",
                              aldeano="taiga", tierra="podzol", tierra_setas="podzol",
                              hierbas=["sweet_berry_bush[age=3]", "fern", "sweet_berry_bush[age=2]", "fern"],
                              setas=_MUSHROOMS, senda="minecraft:dirt_path",
                              patio=["minecraft:dirt_path", "minecraft:cobblestone", "minecraft:gravel"],
                              pociones=[("night_vision", 4), ("healing", 3), ("strength", 5)],
                              libro=("unbreaking", 2)),
                  variantes=_VAR),
    "montana": dict(biomas=["windswept_hills", "windswept_gravelly_hills", "windswept_forest", "stony_peaks"],
                    paleta=dict(madera="spruce", tronco="spruce_log", muro="cobblestone", zocalo="stone_bricks",
                                suelo="polished_andesite", teja="cobblestone_stairs", cumbrera="cobblestone",
                                chimenea="stone_bricks", vidrio="light_blue_stained_glass_pane", cama="light_blue",
                                alfombra="blue", mostrador="polished_andesite", maceta="potted_azure_bluet",
                                piedra="mossy_stone_bricks", aldeano="plains", tierra="podzol", tierra_setas="podzol",
                                hierbas=["azure_bluet", "lily_of_the_valley", "fern", "azure_bluet"], setas=_MUSHROOMS,
                                senda="minecraft:gravel",
                                patio=["minecraft:gravel", "minecraft:cobblestone", "minecraft:stone_bricks"],
                                pociones=[("slow_falling", 4), ("healing", 3), ("fire_resistance", 5)],
                                libro=("feather_falling", 2)),
                    variantes=_VAR),
    "cerezo": dict(biomas=["cherry_grove"],
                   paleta=dict(madera="cherry", tronco="cherry_log", muro="cherry_planks", zocalo="stone_bricks",
                               suelo="cherry_planks", teja="cherry_stairs", cumbrera="cherry_planks",
                               chimenea="stone_bricks", vidrio="pink_stained_glass_pane", cama="pink", alfombra="magenta",
                               mostrador="stripped_cherry_log[axis=z]", maceta="potted_allium", piedra="stone_bricks",
                               aldeano="plains", tierra="podzol", tierra_setas="podzol",
                               hierbas=["pink_petals[facing=north,flower_amount=4]", "allium", "lily_of_the_valley",
                                        "pink_petals[facing=east,flower_amount=3]"], setas=_MUSHROOMS,
                               senda="minecraft:dirt_path",
                               patio=["minecraft:dirt_path", "minecraft:stone_bricks", "minecraft:gravel"],
                               pociones=[("regeneration", 6), ("healing", 3), ("swiftness", 3)],
                               libro=("protection", 2)),
                   variantes=_VAR),
    "desierto": dict(biomas=["desert"], convencionales=["c:is_desert"],
                     paleta=dict(madera="jungle", tronco="stripped_jungle_log", muro="sandstone", zocalo="cut_sandstone",
                                 suelo="smooth_sandstone", teja="sandstone_stairs", cumbrera="cut_sandstone",
                                 chimenea="chiseled_sandstone", vidrio="orange_stained_glass_pane", cama="orange",
                                 alfombra="orange", mostrador="cut_sandstone", maceta="potted_cactus",
                                 piedra="chiseled_sandstone", aldeano="desert", tierra="sand", tierra_setas="podzol",
                                 hierbas=["dead_bush", "short_dry_grass", "dead_bush", "tall_dry_grass"], setas=_MUSHROOMS,
                                 senda="minecraft:smooth_sandstone",
                                 patio=["minecraft:smooth_sandstone", "minecraft:sandstone", "minecraft:gravel"],
                                 pociones=[("fire_resistance", 5), ("healing", 3), ("invisibility", 6)],
                                 libro=("fire_protection", 2)),
                     variantes=_VAR),
}
