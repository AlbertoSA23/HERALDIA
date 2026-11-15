"""12 familias de biomas x 3 temáticas = 36 estilos."""

WOODS = {"oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "pale_oak", "bamboo"}


def roofset(kind):
    """Devuelve (escalera, losa, bloque) para un material de tejado."""
    special = {
        "brick": ("brick_stairs", "brick_slab", "bricks"),
        "deepslate_tile": ("deepslate_tile_stairs", "deepslate_tile_slab", "deepslate_tiles"),
        "deepslate_brick": ("deepslate_brick_stairs", "deepslate_brick_slab", "deepslate_bricks"),
        "copper": ("waxed_oxidized_cut_copper_stairs", "waxed_oxidized_cut_copper_slab", "waxed_oxidized_cut_copper"),
        "copper_new": ("waxed_cut_copper_stairs", "waxed_cut_copper_slab", "waxed_cut_copper"),
        "mud_brick": ("mud_brick_stairs", "mud_brick_slab", "mud_bricks"),
        "tuff_brick": ("tuff_brick_stairs", "tuff_brick_slab", "tuff_bricks"),
        "stone_brick": ("stone_brick_stairs", "stone_brick_slab", "stone_bricks"),
        "mossy_stone_brick": ("mossy_stone_brick_stairs", "mossy_stone_brick_slab", "mossy_stone_bricks"),
        "cobblestone": ("cobblestone_stairs", "cobblestone_slab", "cobblestone"),
        "mossy_cobblestone": ("mossy_cobblestone_stairs", "mossy_cobblestone_slab", "mossy_cobblestone"),
        "sandstone": ("sandstone_stairs", "sandstone_slab", "sandstone"),
        "smooth_sandstone": ("smooth_sandstone_stairs", "smooth_sandstone_slab", "smooth_sandstone"),
        "red_sandstone": ("red_sandstone_stairs", "red_sandstone_slab", "red_sandstone"),
        "smooth_red_sandstone": ("smooth_red_sandstone_stairs", "smooth_red_sandstone_slab", "smooth_red_sandstone"),
        "red_nether_brick": ("red_nether_brick_stairs", "red_nether_brick_slab", "red_nether_bricks"),
        "blackstone_brick": ("polished_blackstone_brick_stairs", "polished_blackstone_brick_slab", "polished_blackstone_bricks"),
        "quartz": ("smooth_quartz_stairs", "smooth_quartz_slab", "smooth_quartz"),
        "prismarine": ("prismarine_brick_stairs", "prismarine_brick_slab", "prismarine_bricks"),
        "dark_prismarine": ("dark_prismarine_stairs", "dark_prismarine_slab", "dark_prismarine"),
        "andesite": ("polished_andesite_stairs", "polished_andesite_slab", "polished_andesite"),
        "granite": ("polished_granite_stairs", "polished_granite_slab", "polished_granite"),
        "diorite": ("polished_diorite_stairs", "polished_diorite_slab", "polished_diorite"),
        "bamboo_mosaic": ("bamboo_mosaic_stairs", "bamboo_mosaic_slab", "bamboo_mosaic"),
        "end_stone_brick": ("end_stone_brick_stairs", "end_stone_brick_slab", "end_stone_bricks"),
    }
    if kind in special:
        return special[kind]
    if kind in WOODS:
        return (f"{kind}_stairs", f"{kind}_slab", f"{kind}_planks")
    raise KeyError(kind)


def wood(kind):
    """Bloques de madera derivados."""
    log = {"bamboo": "bamboo_block", "mangrove": "mangrove_log"}.get(kind, f"{kind}_log")
    stripped = {"bamboo": "stripped_bamboo_block"}.get(kind, f"stripped_{kind}_log")
    return dict(planks=f"{kind}_planks", log=log, stripped=stripped, fence=f"{kind}_fence",
                gate=f"{kind}_fence_gate", door=f"{kind}_door", trapdoor=f"{kind}_trapdoor",
                wstairs=f"{kind}_stairs", wslab=f"{kind}_slab", plate=f"{kind}_pressure_plate",
                button=f"{kind}_button")


def theme(tid, family, name, *, wall, wood_kind, roof, found="cobblestone", floor=None, wall2=None,
          frame=True, roof_type="gable", wall_style="frame", window="glass_pane", path="dirt_path",
          path2="coarse_dirt", light="lantern", carpet=("red", "brown"), bed="red", church_glass="light_blue",
          church="romanesque", tower_cap="spire", shape="rect", stilts=0, vtype="plains", trim=None,
          accent=None, plants=("poppy", "dandelion"), leaves="oak_leaves", decor=(), wool="white",
          street_edge=None, flat_parapet=None, dome=None, chimney=True, banner="red", pier="oak"):
    w = wood(wood_kind)
    rs, rsl, rf = roofset(roof)
    t = dict(id=tid, family=family, name=name, wall=wall, wall2=wall2 or wall, found=found,
             floor=floor or w["planks"], roof_stairs=rs, roof_slab=rsl, roof_full=rf,
             roof_type=roof_type, wall_style=wall_style if frame else "plain", window=window,
             path=path, path2=path2, light=light, carpet=list(carpet), bed=bed, church_glass=church_glass,
             church=church, tower_cap=tower_cap, shape=shape, stilts=stilts, vtype=vtype,
             trim=trim or roofset(roof)[0], accent=accent or w["stripped"], plants=list(plants),
             leaves=leaves, decor=list(decor), wool=wool, street_edge=street_edge,
             flat_parapet=flat_parapet, dome=dome, chimney=chimney, banner=banner,
             wood_kind=wood_kind, pier=wood(pier))
    t.update(w)
    return t


THEMES = [
    # 1. Llanuras
    theme("llanuras_castellana", "llanuras", "Medieval castellana", wall="white_terracotta", wall2="stone_bricks",
          wood_kind="spruce", roof="brick", roof_type="hip", wall_style="stone_base", found="stone_bricks",
          church="romanesque", tower_cap="pyramid", carpet=("red", "yellow"), banner="red",
          decor=("well", "haystack", "cart")),
    theme("llanuras_gallega", "llanuras", "Gallega de granito", wall="stone_bricks", wall2="cobblestone",
          wood_kind="oak", roof="deepslate_tile", roof_type="gable", wall_style="stone_base", found="cobblestone",
          floor="oak_planks", church="romanesque", tower_cap="spire", accent="smooth_stone", path="gravel",
          path2="cobblestone", carpet=("blue", "white"), banner="blue", decor=("horreo", "cruceiro", "well")),
    theme("llanuras_entramado", "llanuras", "Campiña de entramado", wall="calcite", wood_kind="dark_oak",
          roof="dark_oak", roof_type="steep", wall_style="frame", found="cobblestone", church="gothic",
          tower_cap="spire", carpet=("green", "brown"), banner="green", decor=("haystack", "flowerbed", "well")),
    # 2. Bosque templado
    theme("bosque_lenadores", "bosque", "Leñadores y aserradero", wall="oak_log", wood_kind="spruce", roof="spruce",
          roof_type="gable", wall_style="logcabin", found="cobblestone", church="chapel", tower_cap="spire",
          carpet=("brown", "orange"), banner="brown", decor=("logpile", "stump", "cart")),
    theme("bosque_elfica", "bosque", "Aldea élfica de abedul", wall="birch_planks", wood_kind="birch", roof="copper",
          roof_type="steep", wall_style="frame", found="mossy_stone_bricks", church="gothic", tower_cap="spire",
          window="white_stained_glass_pane", carpet=("lime", "white"), church_glass="lime", leaves="azalea_leaves",
          plants=("allium", "azure_bluet", "lily_of_the_valley"), banner="lime", decor=("flowerbed", "planter", "lamp_tall")),
    theme("bosque_abadia", "bosque", "Abadía monacal", wall="stone_bricks", wall2="mossy_stone_bricks", wood_kind="oak",
          roof="deepslate_tile", roof_type="gable", wall_style="stone_base", found="stone_bricks", church="gothic",
          tower_cap="pyramid", accent="polished_andesite", path="gravel", path2="cobblestone", carpet=("brown", "gray"),
          banner="brown", decor=("herbgarden", "well", "beehives")),
    # 3. Bosque oscuro
    theme("oscuro_gotica", "oscuro", "Gótica", wall="deepslate_bricks", wall2="cobbled_deepslate", wood_kind="dark_oak",
          roof="deepslate_tile", roof_type="steep", wall_style="stone_base", found="cobbled_deepslate",
          church="gothic", tower_cap="spire", window="gray_stained_glass_pane", light="soul_lantern",
          church_glass="purple", carpet=("purple", "black"), banner="black", path="gravel", path2="cobbled_deepslate",
          decor=("lamp_tall", "gargoyle", "well")),
    theme("oscuro_alquimistas", "oscuro", "Alquimistas y herboristas", wall="pale_oak_planks", wall2="tuff_bricks",
          wood_kind="dark_oak", roof="tuff_brick", roof_type="steep", wall_style="frame", found="tuff",
          church="chapel", tower_cap="spire", window="purple_stained_glass_pane", carpet=("purple", "green"),
          church_glass="magenta", leaves="pale_oak_leaves", banner="purple", decor=("herbgarden", "cauldrons", "planter")),
    theme("oscuro_fortificada", "oscuro", "Fortificada con empalizada", wall="spruce_planks", wall2="cobblestone",
          wood_kind="spruce", roof="dark_oak", roof_type="gable", wall_style="frame", found="cobbled_deepslate",
          church="chapel", tower_cap="pyramid", carpet=("gray", "red"), banner="gray", decor=("palisade", "logpile", "targets")),
    # 4. Taiga
    theme("taiga_nordica", "taiga", "Nórdica de casas largas", wall="spruce_planks", wall2="cobblestone",
          wood_kind="spruce", roof="spruce", roof_type="steep", wall_style="frame", shape="long",
          church="stave", tower_cap="pagoda", vtype="taiga", carpet=("red", "blue"), leaves="spruce_leaves",
          plants=("fern", "sweet_berry_bush"), banner="blue", path="podzol", path2="coarse_dirt",
          decor=("logpile", "runestone", "fishrack")),
    theme("taiga_eslava", "taiga", "Eslava de madera tallada", wall="spruce_log", wood_kind="spruce", roof="dark_oak",
          roof_type="gable", wall_style="logcabin", accent="stripped_birch_log", church="onion", tower_cap="onion",
          vtype="taiga", carpet=("red", "yellow"), leaves="spruce_leaves", banner="red", path="podzol",
          path2="coarse_dirt", dome="copper_new", decor=("well", "logpile", "beehives")),
    theme("taiga_cazadores", "taiga", "Cazadores y peleteros", wall="stripped_spruce_log", wall2="cobblestone",
          wood_kind="spruce", roof="spruce", roof_type="gable", wall_style="stone_base", church="chapel",
          tower_cap="spire", vtype="taiga", carpet=("brown", "white"), leaves="spruce_leaves", path="podzol",
          path2="coarse_dirt", banner="brown", decor=("dryrack", "campfire", "logpile")),
    # 5. Nieve
    theme("nieve_alpina", "nieve", "Alpina", wall="spruce_planks", wall2="stone_bricks", wood_kind="spruce",
          roof="spruce", roof_type="gable", wall_style="stone_base", church="romanesque", tower_cap="onion",
          dome="copper", vtype="snow", carpet=("red", "white"), leaves="spruce_leaves", path="gravel",
          path2="packed_ice", banner="red", decor=("logpile", "sled", "lamp_tall")),
    theme("nieve_fortaleza", "nieve", "Fortaleza del norte", wall="stone_bricks", wall2="cobblestone",
          wood_kind="spruce", roof="deepslate_brick", roof_type="steep", wall_style="stone_base",
          found="cobblestone", church="romanesque", tower_cap="pyramid", vtype="snow", carpet=("blue", "gray"),
          leaves="spruce_leaves", path="gravel", path2="cobblestone", banner="blue", decor=("palisade", "targets", "campfire")),
    theme("nieve_pastores", "nieve", "Iglesia de piedra y pastores", wall="cobblestone", wall2="mossy_cobblestone",
          wood_kind="spruce", roof="spruce", roof_type="gable", wall_style="plain", church="romanesque",
          tower_cap="spire", vtype="snow", carpet=("white", "light_gray"), leaves="spruce_leaves", path="gravel",
          path2="snow_block", banner="white", decor=("sheep_pen", "haystack", "campfire")),
    # 6. Desierto
    theme("desierto_andalusi", "desierto", "Oasis andalusí", wall="smooth_sandstone", wall2="cut_sandstone",
          wood_kind="jungle", roof="smooth_sandstone", roof_type="flat", wall_style="plain", found="sandstone",
          floor="smooth_sandstone", church="domed", tower_cap="dome", dome="copper", vtype="desert",
          carpet=("orange", "cyan"), church_glass="orange", plants=("cactus_pot",), leaves="jungle_leaves",
          path="sandstone", path2="smooth_sandstone", banner="cyan", flat_parapet="sandstone_wall",
          decor=("palm", "fountain_small", "awning")),
    theme("desierto_obelisco", "desierto", "Adobe con obelisco", wall="sandstone", wall2="chiseled_sandstone",
          wood_kind="acacia", roof="sandstone", roof_type="flat", wall_style="plain", found="cut_sandstone",
          floor="cut_sandstone", church="pyramid", tower_cap="pyramid", vtype="desert", carpet=("yellow", "blue"),
          church_glass="yellow", plants=("cactus_pot",), path="sandstone", path2="sand", banner="yellow",
          flat_parapet="sandstone_wall", decor=("obelisk", "palm", "jars")),
    theme("desierto_caravanera", "desierto", "Caravanera de mercaderes", wall="smooth_red_sandstone", wall2="cut_red_sandstone",
          wood_kind="acacia", roof="smooth_red_sandstone", roof_type="flat", wall_style="plain", found="red_sandstone",
          floor="cut_red_sandstone", church="domed", tower_cap="dome", dome="smooth_sandstone", vtype="desert",
          carpet=("red", "orange"), plants=("cactus_pot",), path="red_sandstone", path2="red_sand", banner="orange",
          flat_parapet="red_sandstone_wall", decor=("tent", "jars", "camel_post")),
    # 7. Sabana
    theme("sabana_paja", "sabana", "Adobe con techos de paja", wall="packed_mud", wall2="mud_bricks", wood_kind="acacia",
          roof="acacia", roof_type="cone", shape="round", wall_style="plain", found="mud_bricks", floor="acacia_planks",
          church="chapel", tower_cap="cone", vtype="savanna", carpet=("orange", "yellow"), leaves="acacia_leaves",
          path="coarse_dirt", path2="dirt_path", banner="orange", decor=("haystack", "jars", "campfire")),
    theme("sabana_terracota", "sabana", "Terracota pintada", wall="white_terracotta", wall2="orange_terracotta",
          wood_kind="acacia", roof="acacia", roof_type="hip", wall_style="stripes", found="terracotta",
          church="domed", tower_cap="dome", dome="mud_brick", vtype="savanna", carpet=("orange", "red"),
          leaves="acacia_leaves", path="coarse_dirt", path2="dirt_path", banner="red", decor=("jars", "planter", "awning")),
    theme("sabana_pastores", "sabana", "Campamento de pastores", wall="acacia_planks", wall2="stripped_acacia_log",
          wood_kind="acacia", roof="acacia", roof_type="gable", wall_style="frame", found="cobblestone",
          church="chapel", tower_cap="pyramid", vtype="savanna", carpet=("yellow", "brown"), leaves="acacia_leaves",
          path="coarse_dirt", path2="dirt_path", banner="yellow", decor=("sheep_pen", "haystack", "campfire")),
    # 8. Jungla
    theme("jungla_arboles", "jungla", "Plataformas en los árboles", wall="jungle_planks", wood_kind="jungle",
          roof="jungle", roof_type="hip", wall_style="frame", stilts=5, found="jungle_log", church="chapel",
          tower_cap="pyramid", vtype="jungle", carpet=("lime", "green"), leaves="jungle_leaves", path="jungle_planks",
          path2="coarse_dirt", banner="lime", plants=("fern", "bamboo_pot"), decor=("planter", "lamp_tall", "vines_post")),
    theme("jungla_templos", "jungla", "Templos escalonados", wall="mossy_stone_bricks", wall2="cobblestone",
          wood_kind="jungle", roof="mossy_stone_brick", roof_type="hip", wall_style="stone_base", found="mossy_cobblestone",
          church="pyramid", tower_cap="pyramid", vtype="jungle", carpet=("green", "yellow"), leaves="jungle_leaves",
          path="mossy_cobblestone", path2="coarse_dirt", banner="green", decor=("idol", "planter", "jars")),
    theme("jungla_bambu", "jungla", "Ribereña de bambú", wall="bamboo_planks", wall2="bamboo_mosaic", wood_kind="bamboo",
          roof="bamboo_mosaic", roof_type="gable", wall_style="frame", stilts=2, found="bamboo_block", church="chapel",
          tower_cap="pagoda", vtype="jungle", carpet=("yellow", "lime"), leaves="jungle_leaves", path="bamboo_planks",
          path2="coarse_dirt", banner="yellow", plants=("bamboo_pot", "fern"), decor=("fishrack", "planter", "jars")),
    # 9. Pantano y manglar
    theme("pantano_palafitos", "pantano", "Palafitos", wall="mangrove_planks", wood_kind="mangrove", roof="mangrove",
          roof_type="gable", wall_style="frame", stilts=3, found="mangrove_log", church="chapel", tower_cap="spire",
          vtype="swamp", carpet=("green", "brown"), leaves="mangrove_leaves", path="mangrove_planks", path2="mud",
          banner="green", decor=("fishrack", "lamp_tall", "planter")),
    theme("pantano_brujas", "pantano", "Aldea de brujas", wall="dark_oak_planks", wall2="mud_bricks", wood_kind="dark_oak",
          roof="mud_brick", roof_type="steep", wall_style="stone_base", found="mud_bricks", church="gothic",
          tower_cap="spire", window="purple_stained_glass_pane", light="soul_lantern", vtype="swamp",
          carpet=("purple", "black"), church_glass="purple", leaves="dark_oak_leaves", path="mud_bricks",
          path2="mud", banner="purple", decor=("cauldrons", "herbgarden", "gargoyle")),
    theme("pantano_turba", "pantano", "Pescadores de turba", wall="packed_mud", wall2="mud_bricks", wood_kind="spruce",
          roof="spruce", roof_type="gable", wall_style="frame", found="mud_bricks", church="chapel", tower_cap="pyramid",
          vtype="swamp", carpet=("brown", "green"), leaves="oak_leaves", path="mud_bricks", path2="mud",
          banner="brown", decor=("fishrack", "logpile", "jars")),
    # 10. Cerezos
    theme("cerezos_japonesa", "cerezos", "Japonesa tradicional", wall="calcite", wood_kind="dark_oak",
          roof="deepslate_tile", roof_type="pagoda", wall_style="frame", found="stone_bricks", church="pagoda",
          tower_cap="pagoda", carpet=("white", "red"), leaves="cherry_leaves", path="gravel", path2="stone",
          window="white_stained_glass_pane", banner="red", plants=("pink_tulip", "azure_bluet"),
          decor=("torii", "stone_lantern", "pond")),
    theme("cerezos_templo", "cerezos", "Templo de montaña con jardines", wall="cherry_planks", wood_kind="cherry",
          roof="red_nether_brick", roof_type="pagoda", wall_style="frame", found="stone_bricks", church="pagoda",
          tower_cap="pagoda", carpet=("pink", "red"), leaves="cherry_leaves", path="gravel", path2="moss_block",
          banner="pink", plants=("pink_tulip", "allium"), decor=("torii", "stone_lantern", "planter")),
    theme("cerezos_artesanos", "cerezos", "Artesanos y casas de té", wall="calcite", wall2="cherry_planks",
          wood_kind="cherry", roof="cherry", roof_type="hip", wall_style="frame", found="cobblestone", church="pagoda",
          tower_cap="pagoda", carpet=("pink", "white"), leaves="cherry_leaves", path="gravel", path2="coarse_dirt",
          banner="pink", decor=("stone_lantern", "awning", "beehives")),
    # 11. Badlands
    theme("badlands_minera", "badlands", "Minera del oeste", wall="spruce_planks", wall2="stripped_oak_log",
          wood_kind="spruce", roof="spruce", roof_type="flat", wall_style="frame", found="terracotta",
          church="chapel", tower_cap="spire", vtype="desert", carpet=("orange", "brown"), path="red_sand",
          path2="coarse_dirt", banner="orange", flat_parapet="spruce_fence", decor=("minecart", "cart", "barrels")),
    theme("badlands_roca", "badlands", "Casas excavadas en la roca", wall="terracotta", wall2="red_terracotta",
          wood_kind="dark_oak", roof="mud_brick", roof_type="flat", wall_style="stripes", found="red_terracotta",
          floor="dark_oak_planks", church="pyramid", tower_cap="flat", vtype="desert", carpet=("red", "orange"),
          path="red_sand", path2="terracotta", banner="red", flat_parapet="mud_brick_wall", decor=("jars", "ladders", "campfire")),
    theme("badlands_canon", "badlands", "Fortaleza de cañón", wall="cut_red_sandstone", wall2="red_sandstone",
          wood_kind="acacia", roof="red_sandstone", roof_type="hip", wall_style="stone_base", found="red_sandstone",
          church="romanesque", tower_cap="pyramid", vtype="desert", carpet=("orange", "yellow"), path="red_sandstone",
          path2="red_sand", banner="orange", decor=("palisade", "targets", "jars")),
    # 12. Costa
    theme("costa_pescadores", "costa", "Pescadores", wall="oak_planks", wall2="cobblestone", wood_kind="spruce",
          roof="spruce", roof_type="gable", wall_style="stone_base", church="chapel", tower_cap="spire",
          carpet=("blue", "white"), path="gravel", path2="sand", banner="blue", decor=("fishrack", "boat", "barrels")),
    theme("costa_mercante", "costa", "Puerto mercante", wall="bricks", wall2="stone_bricks", wood_kind="dark_oak",
          roof="deepslate_tile", roof_type="gable", wall_style="stone_base", found="stone_bricks", church="gothic",
          tower_cap="spire", carpet=("red", "blue"), path="stone_bricks", path2="gravel", banner="red",
          decor=("barrels", "crates", "lamp_tall")),
    theme("costa_mediterranea", "costa", "Mediterránea encalada", wall="white_concrete", wall2="calcite",
          wood_kind="birch", roof="quartz", roof_type="flat", wall_style="plain", found="stone_bricks",
          floor="smooth_stone", church="domed", tower_cap="dome", dome="prismarine", window="light_blue_stained_glass_pane",
          carpet=("light_blue", "white"), church_glass="light_blue", path="smooth_stone", path2="calcite",
          banner="light_blue", flat_parapet="diorite_wall", plants=("blue_orchid", "cornflower"),
          decor=("planter", "awning", "fountain_small")),
]

FAMILIES = {
    "llanuras": dict(biomes=["plains", "sunflower_plains", "meadow"], vtype="plains", nombre=("Llanuras", "Plains"), icono="minecraft:wheat"),
    "bosque": dict(biomes=["forest", "flower_forest", "birch_forest", "old_growth_birch_forest", "dappled_forest"], vtype="plains", nombre=("Bosque", "Forest"), icono="minecraft:oak_sapling"),
    "oscuro": dict(biomes=["dark_forest", "pale_garden"], vtype="plains", nombre=("Bosque oscuro", "Dark Forest"), icono="minecraft:dark_oak_sapling"),
    "taiga": dict(biomes=["taiga", "old_growth_pine_taiga", "old_growth_spruce_taiga"], vtype="taiga", nombre=("Taiga", "Taiga"), icono="minecraft:spruce_sapling"),
    "nieve": dict(biomes=["snowy_plains", "snowy_taiga", "grove", "ice_spikes"], vtype="snow", nombre=("Nieve", "Snow"), icono="minecraft:snowball"),
    "desierto": dict(biomes=["desert"], vtype="desert", nombre=("Desierto", "Desert"), icono="minecraft:cactus"),
    "sabana": dict(biomes=["savanna", "savanna_plateau"], vtype="savanna", nombre=("Sabana", "Savanna"), icono="minecraft:acacia_sapling"),
    "jungla": dict(biomes=["jungle", "sparse_jungle", "bamboo_jungle"], vtype="jungle", nombre=("Jungla", "Jungle"), icono="minecraft:cocoa_beans"),
    "pantano": dict(biomes=["swamp", "mangrove_swamp"], vtype="swamp", nombre=("Pantano", "Swamp"), icono="minecraft:lily_pad"),
    "cerezos": dict(biomes=["cherry_grove"], vtype="plains", nombre=("Cerezos", "Cherry Grove"), icono="minecraft:cherry_sapling"),
    "badlands": dict(biomes=["badlands", "eroded_badlands", "wooded_badlands"], vtype="desert", nombre=("Badlands", "Badlands"), icono="minecraft:terracotta"),
    "costa": dict(biomes=["beach", "snowy_beach", "stony_shore"], vtype="plains", nombre=("Costa", "Coast"), icono="minecraft:sand"),
}

for _t in THEMES:
    _t["vtype"] = FAMILIES[_t["family"]]["vtype"]
