"""Choza de mago (heraldia:medianas/choza_mago/<estilo>, T43): patio de 17 x 17 con una choza de 9 x 9 de tejado empinado
y desván. Planta baja: estanterías, atril con las notas del mago, cofre del estudio, mostrador con soportes de pociones,
racimo de amatista y velas, calderos, alfombra y chimenea con fogata y tiro hasta el tejado; desván por una escalera de
mano: cama, cofre, telarañas y el mapa estelar (dos estandartes en los hastiales). Variante a: jardín de hierbas y setas
vallado al este y el gato del mago; b: círculo de piedras con velas, setas y amatista al este y bancales delante de la
puerta. El estilo del pantano va sobre pilotes (la choza 3 bloques por encima del suelo, con escalera de subida).

El mago (aldeano clérigo quieto, con tratos fijos: frascos, lapislázuli, pociones, un libro encantado modesto y perlas de
ender) lleva la etiqueta heraldia_mago. El Java (chozas/) decide con la semilla y la choza si es malvado
(chozas_mago.prob_malvado) y, si lo es, se revela al acercarse un jugador o al intentar comerciar: se convierte en el
«Mago Malvado» (un evocador con las fases y la barra de jefe), con su botín propio (tools/gen/chozas_mago.py)."""
from core import Template, B
from loot import item, empty
from unicas._comun import botin
from . import _comun as c

MID = "choza_mago"
NOMBRE = {"es_es": "Choza de mago", "en_us": "Wizard's Hut"}
SEPARACION = 1024
LOGRO_ICONO = "minecraft:brewing_stand"
TAG_MAGO = "heraldia_mago"           # la etiqueta que busca el Java (chozas/Magos.TAG)
TAG_MALVADO = "heraldia_mago_malvado"  # la del evocador en que se convierte (chozas/Magos.MALVADO)
_K = f"heraldia.medianas.{MID}."
LANG = botin.lang(_K, {
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
LOGROS = [
    dict(id="tratos", icono="minecraft:potion", marco="task",
         titulo=("Aprendiz de brujería", "Sorcerer's Apprentice"),
         descripcion=("Comercia con el mago de una choza de mago", "Trade with the wizard of a wizard's hut"),
         criterios={"trato": {"trigger": "minecraft:villager_trade", "conditions": {"villager": {
             "type": "minecraft:entity_properties", "entity": "this",
             "predicate": {"minecraft:entity_tags": {"all_of": [TAG_MAGO]}}}}}}),
    dict(id="malvado", icono="minecraft:totem_of_undying", marco="challenge",
         titulo=("Ni magia ni trucos", "No Tricks Left"),
         descripcion=("Vence a un mago malvado escondido en una choza de mago",
                      "Defeat an evil wizard hiding in a wizard's hut"),
         criterios={"malvado": {"trigger": "minecraft:player_killed_entity", "conditions": {"entity": {
             "type": "minecraft:entity_properties", "entity": "this",
             "predicate": {"minecraft:entity_type": "minecraft:evoker",
                           "minecraft:entity_tags": {"all_of": [TAG_MALVADO]}}}}}}),
]
_NOTAS = botin.libro([{"translate": _K + "notas.p1", "fallback": LANG["es_es"][_K + "notas.p1"]},
                      {"translate": _K + "notas.p2", "fallback": LANG["es_es"][_K + "notas.p2"]}],
                     {"translate": _K + "notas", "fallback": LANG["es_es"][_K + "notas"]},
                     LANG["es_es"][_K + "notas"], "Mago")
LOOT = {
    "estudio": botin.cofre(((3, 5), [item("book", 8, 1, 3), item("paper", 8, 2, 6), item("glass_bottle", 8, 1, 4),
                                     item("lapis_lazuli", 7, 2, 6), item("redstone", 5, 2, 6),
                                     item("glowstone_dust", 4, 1, 4), item("amethyst_shard", 5, 1, 3),
                                     item("feather", 4, 1, 3), item("ink_sac", 4, 1, 2), item("candle", 4, 1, 3),
                                     item("nether_wart", 3, 1, 3), item("blaze_powder", 1), empty(4)]),
                           ((1, 1), [item("experience_bottle", 4, 1, 3), item("book", 3, rand_ench=True),
                                     item("emerald", 4, 1, 3), item("ender_pearl", 1), empty(6)])),
    "desvan": botin.cofre(((2, 4), [item("string", 8, 2, 5), item("cobweb", 3, 1, 2), item("candle", 6, 1, 3),
                                    item("brown_mushroom", 5, 1, 3), item("red_mushroom", 5, 1, 3),
                                    item("spider_eye", 5, 1, 2), item("sugar", 5, 1, 4), item("bone", 5, 1, 3),
                                    item("gunpowder", 3, 1, 2), item("fermented_spider_eye", 2),
                                    item("phantom_membrane", 1), item("rabbit_foot", 1), empty(4)]),
                          ((1, 1), [_NOTAS, item("name_tag", 1), item("emerald", 3, 1, 2), empty(8)])),
}

ANCHO = FONDO = 17
X0, Z0, X1, Z1 = 2, 5, 10, 13      # muros de la choza (9 x 9); puerta al norte en CX
CX = 6
GX0, GX1 = 12, 16                  # el anexo del este (jardín o círculo), de z = Z0 a Z1


def _p(n, s):
    return f"{s}[facing={n},half=bottom,shape=straight,waterlogged=false]"


def _pocion(pid):
    return {"id": "minecraft:potion", "count": 1, "components": {"minecraft:potion_contents": {"potion": f"minecraft:{pid}"}}}


def _libro(ench, nivel):
    return {"id": "minecraft:enchanted_book", "count": 1,
            "components": {"minecraft:stored_enchantments": {f"minecraft:{ench}": nivel}}}


def ofertas(p):
    """Tratos del mago: frascos, lapislázuli, tres pociones del estilo, un libro modesto y perlas de ender."""
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    pociones = [c.oferta(em(n), _pocion(pid), 4) for pid, n in p["pociones"]]
    ench, nivel = p["libro"]
    return ([c.oferta(em(1), {"id": "minecraft:glass_bottle", "count": 4}, 12),
             c.oferta(em(1), {"id": "minecraft:lapis_lazuli", "count": 6}, 12)] + pociones +
            [c.oferta(em(14), _libro(ench, nivel), 2, buy_b={"id": "minecraft:book", "count": 1}),
             c.oferta(em(5), {"id": "minecraft:ender_pearl", "count": 1}, 4),
             c.oferta({"id": "minecraft:nether_wart", "count": 8}, em(1), 8)])


def mago(p, rot=180.0):
    n = c.aldeano(MID, "mago", "Mago de Heraldia", "cleric", p["aldeano"], ofertas(p), rot=rot)
    n["VillagerData"]["level"] = 4
    n["Xp"] = 150
    n["Tags"] = [TAG_MAGO]
    return n


def _suelo(p):
    mats = p["patio"]
    return lambda x, z: p["senda"] if x == CX and z < Z0 else mats[(x * 7 + z * 5 + x * z) % len(mats)]


def _estandarte(color, patrones):
    return {"id": "minecraft:banner", "patterns": [{"pattern": f"minecraft:{pt}", "color": col} for pt, col in patrones]}


def _choza(p, name):
    """La choza entera (patio, muros, tejado, chimenea, planta baja y desván). Devuelve (plantilla, H)."""
    t = Template(name)
    m, H = p["madera"], p.get("pilotes", 0)
    c.patio(t, 0, 0, ANCHO - 1, FONDO - 1, _suelo(p), aire=3)
    c.entrada(t, CX, p["senda"])
    # base: a ras de suelo o sobre pilotes de tronco (esquinas y centros de cada lado)
    if H:
        for x in (X0, CX, X1):
            for z in (Z0, (Z0 + Z1) // 2, Z1):
                if (x, z) != (CX, (Z0 + Z1) // 2):
                    t.fill(x, 1, z, x, H - 1, z, f"{p['tronco']}[axis=y]")
        for x in range(X0, X1 + 1):            # bajo la choza no queda nada del terreno
            for z in range(Z0, Z1 + 1):
                for y in range(1, H):
                    t.set(x, y, z, "air", keep=True)
        # escalera de subida a la puerta (de z = Z0 - 3 a Z0 - 1), con su apoyo
        for i in range(H):
            z = Z0 - H + i
            t.set(CX, 1 + i, z, _p("south", f"{m}_stairs"))
            for y in range(1, 1 + i):
                t.set(CX, y, z, f"{m}_planks")
    t.fill(X0, H, Z0, X1, H, Z1, p["zocalo"])
    t.fill(X0 + 1, H, Z0 + 1, X1 - 1, H, Z1 - 1, p["suelo"])
    # muros (planta baja de 4 de alto) y el suelo del desván en H + 5
    c.caja(t, X0, H + 1, Z0, X1, H + 5, Z1, p["muro"], esquina=f"{p['tronco']}[axis=y]")
    t.fill(X0 + 1, H + 5, Z0 + 1, X1 - 1, H + 5, Z1 - 1, f"{m}_planks")
    c.tejado(t, X0, Z0, X1, Z1, H + 5, p["teja"], p["cumbrera"], p["muro"])
    c.door(t, CX, H + 1, Z0, "south", f"{m}_door")
    for x in (X0 + 2, X1 - 2):
        c.ventana(t, x, H + 2, Z0, p["vidrio"])
    c.ventana(t, X0, H + 2, 9, p["vidrio"])
    c.ventana(t, X1, H + 3, 8, p["vidrio"])
    c.ventana(t, X0, H + 7, 9, p["vidrio"])       # ventanuco del desván en el hastial oeste
    _chimenea(t, p, H)
    _planta_baja(t, p, H)
    _desvan(t, p, H)
    return t, H


def _chimenea(t, p, H):
    """Hogar en el muro sur (fogata en un nicho de 1 x 2) y tiro hueco hasta un bloque por encima de la cumbrera."""
    lad, cima = p["chimenea"], H + 11
    t.set(CX, H + 1, Z1, "campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    t.set(CX, H + 1, Z1 - 1, "air")
    t.set(CX, H + 2, Z1 - 1, "air")
    for y in range(H + 2, cima + 1):
        t.set(CX, y, Z1, "air")                  # el tiro
    for y in range(H + 1, cima + 1):
        t.set(CX - 1, y, Z1, lad)
        t.set(CX + 1, y, Z1, lad)
    for y in range(1, cima + 1):
        t.set(CX, y, Z1 + 1, lad)                # la cara exterior, desde el suelo
    for y in range(H + 3, cima + 1):
        t.set(CX, y, Z1 - 1, lad)                # la campana del hogar y el pecho de la chimenea en el desván


def _planta_baja(t, p, H):
    y = H + 1
    xo, xe = X0 + 1, X1 - 1                      # x = 3 (oeste) y x = 9 (este)
    # oeste: estanterías, cofre del estudio y atril con las notas bajo la ventana
    for z in (Z0 + 1, Z0 + 2, Z1 - 3, Z1 - 2, Z1 - 1):
        t.fill(xo, y, z, xo, y + 2, z, "bookshelf")
    t.set(xo, y + 3, Z0 + 1, "candle[candles=2,lit=true,waterlogged=false]")
    t.set(xo, y + 3, Z1 - 1, "candle[candles=3,lit=true,waterlogged=false]")
    c.cofre(t, xo, y, Z0 + 3, "east", MID, "estudio")
    t.set(xo, y, Z0 + 4, "lectern[facing=east,has_book=true,powered=false]", {
        "id": "minecraft:lectern", "Page": 0,
        "Book": {"id": "minecraft:written_book", "count": 1, "components": _NOTAS["modifier"][0]["components"]}})
    # este: tonel, mostrador con soportes de pociones, amatista y velas; escalera de mano al desván; caldero lleno
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
    c.escalera_mano(t, xe, Z1 - 2, y, H + 5, "west")
    t.set(xe, y, Z1 - 1, "water_cauldron[level=3]")
    t.set(xo + 1, y, Z1 - 1, "cauldron")
    t.set(CX + 1, y, Z1 - 1, "decorated_pot[cracked=false,facing=north,waterlogged=false]", {"id": "minecraft:decorated_pot"})
    # alfombra en el centro y dos faroles colgados del suelo del desván
    t.fill(CX - 1, y, Z0 + 3, CX + 1, y, Z0 + 5, f"{p['alfombra']}_carpet")
    t.set(xo + 1, y, Z0 + 1, p["maceta"])
    c.farol(t, CX, H + 4, Z0 + 2)
    c.farol(t, CX, H + 4, Z1 - 3)


def _desvan(t, p, H):
    """Desván (pies en H + 6; de pie solo de z = 7 a 11): cama, cofre, telarañas, amatista, el mapa estelar."""
    y, xo, xe = H + 6, X0 + 1, X1 - 1
    t.set(xe, H + 5, Z1 - 2, "ladder[facing=west,waterlogged=false]")     # el hueco de la escalera
    c.cama(t, xo, Z0 + 3, "west", p["cama"], y=y)
    c.cofre(t, xo, y, Z0 + 5, "east", MID, "desvan")
    for x, yy, z in ((xo, y, Z0 + 1), (xe, y, Z0 + 1), (xo, y + 1, Z0 + 2), (xe, y + 1, Z0 + 2), (xo, y, Z1 - 1)):
        t.set(x, yy, z, "cobweb")
    t.set(xe, y, Z0 + 3, "amethyst_cluster[facing=up,waterlogged=false]")
    t.set(xe, y, Z0 + 4, "candle[candles=4,lit=true,waterlogged=false]")
    # mapa estelar: dos estandartes colgados de los hastiales, mirando al centro
    t.set(xo, H + 8, Z0 + 4, "blue_wall_banner[facing=east]",
          _estandarte("blue", [("globe", "yellow"), ("border", "black")]))
    t.set(xe, H + 8, Z0 + 4, "black_wall_banner[facing=west]",
          _estandarte("black", [("flower", "white"), ("circle", "yellow"), ("border", "blue")]))
    c.farol(t, CX, H + 9, Z0 + 4)


def _bancal(t, x0, z0, x1, z1, tierra, plantas):
    """Bancal elevado (tierra en y = 1, plantas en y = 2): el patio de y = 0 sigue sin tierra fértil."""
    i = 0
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            t.set(x, 1, z, tierra)
            t.set(x, 2, z, plantas[i % len(plantas)])
            i += 1


def con_jardin(p, name):
    """Variante a: jardín de hierbas y setas vallado al este (dos bancales, farol en un poste) y el gato del mago."""
    t, H = _choza(p, name)
    m = p["madera"]
    for x in range(GX0, GX1 + 1):
        for z in range(Z0, Z1 + 1):
            if x in (GX0, GX1) or z in (Z0, Z1):
                t.set(x, 1, z, f"{m}_fence")
    t.set((GX0 + GX1) // 2, 1, Z0, f"{m}_fence_gate[facing=north,in_wall=false,open=false,powered=false]")
    _bancal(t, GX0 + 1, Z0 + 2, GX1 - 2, Z0 + 3, p["tierra"], p["hierbas"])
    _bancal(t, GX0 + 1, Z1 - 3, GX1 - 2, Z1 - 2, p["tierra_setas"], p["setas"])
    t.set(GX1, 2, Z0, "lantern[hanging=false,waterlogged=false]")
    t.set(GX0 + 1, 1, Z1 - 1, "composter[level=3]")
    t.entity(CX, H + 1, Z0 + 3, mago(p))
    t.entity(GX0 + 2, 1, (Z0 + Z1) // 2, c.mob("cat", MID, "gato", "Sombra", rot=270.0, variant="minecraft:all_black",
                                              CollarColor=B(10)))
    return t


def con_circulo(p, name):
    """Variante b: círculo de piedras con velas alrededor de un racimo de amatista y cuatro setas al este, y dos
    bancales de hierbas delante de la puerta."""
    t, H = _choza(p, name)
    cx, cz = (GX0 + GX1) // 2, (Z0 + Z1) // 2
    for dx, dz in ((-2, -2), (2, -2), (-2, 2), (2, 2), (0, -3), (0, 3)):
        t.fill(cx + dx, 1, cz + dz, cx + dx, 2, cz + dz, p["piedra"])
        t.set(cx + dx, 3, cz + dz, "candle[candles=1,lit=true,waterlogged=false]")
    t.set(cx, 0, cz, "amethyst_block")
    t.set(cx, 1, cz, "amethyst_cluster[facing=up,waterlogged=false]")
    for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        t.set(cx + dx, 1, cz + dz, p["tierra_setas"])
        t.set(cx + dx, 2, cz + dz, p["setas"][(dx + dz) % len(p["setas"])])
    _bancal(t, X0, 1, CX - 2, 2, p["tierra"], p["hierbas"])
    _bancal(t, CX + 2, 1, X1, 2, p["tierra"], list(reversed(p["hierbas"])))
    t.entity(CX, H + 1, Z0 + 3, mago(p))
    return t


_VAR = {"a": con_jardin, "b": con_circulo}
_SETAS = ["brown_mushroom", "red_mushroom"]
ESTILOS = {
    "oscuro": dict(biomas=["dark_forest", "pale_garden"], convencionales=["c:is_dark_forest"],
                   paleta=dict(madera="dark_oak", tronco="dark_oak_log", muro="dark_oak_planks", zocalo="cobblestone",
                               suelo="spruce_planks", teja="dark_oak_stairs", cumbrera="dark_oak_planks",
                               chimenea="mossy_cobblestone", vidrio="purple_stained_glass_pane", cama="purple",
                               alfombra="purple", mostrador="stripped_dark_oak_log[axis=z]", maceta="potted_red_mushroom",
                               piedra="mossy_cobblestone", aldeano="plains", tierra="podzol", tierra_setas="podzol",
                               hierbas=["fern", "lily_of_the_valley", "fern", "allium"], setas=_SETAS,
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
                                hierbas=["blue_orchid", "fern", "blue_orchid", "brown_mushroom"], setas=_SETAS,
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
                              setas=_SETAS, senda="minecraft:dirt_path",
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
                                hierbas=["azure_bluet", "lily_of_the_valley", "fern", "azure_bluet"], setas=_SETAS,
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
                                        "pink_petals[facing=east,flower_amount=3]"], setas=_SETAS,
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
                                 hierbas=["dead_bush", "short_dry_grass", "dead_bush", "tall_dry_grass"], setas=_SETAS,
                                 senda="minecraft:smooth_sandstone",
                                 patio=["minecraft:smooth_sandstone", "minecraft:sandstone", "minecraft:gravel"],
                                 pociones=[("fire_resistance", 5), ("healing", 3), ("invisibility", 6)],
                                 libro=("fire_protection", 2)),
                     variantes=_VAR),
}
