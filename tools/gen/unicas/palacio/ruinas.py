"""Ruina con sentido (determinista) y desgaste por procesador. La auditoría mide el porcentaje resultante."""
import random

# Procesador de desgaste: solo piedra de construcción; nunca toca mecanismos, cofres ni madera.
WEAR = [("stone_bricks", "cracked_stone_bricks", 0.2), ("stone_bricks", "mossy_stone_bricks", 0.2),
        ("polished_andesite", "andesite", 0.25), ("mossy_cobblestone", "cobblestone", 0.15),
        ("red_terracotta", "terracotta", 0.10), ("deepslate_bricks", "cracked_deepslate_bricks", 0.15)]


def processors():
    return {"processors": [{"processor_type": "minecraft:rule", "rules": [
        {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + a, "probability": p},
         "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": {"Name": "minecraft:" + b}}
        for a, b, p in WEAR]}]}


def wear_probability(state):
    """Probabilidad de que el procesador cambie este bloque (las reglas se evalúan en orden)."""
    name = state.split("[")[0].replace("minecraft:", "")
    q, left = 0.0, 1.0
    for a, _, p in WEAR:
        if a == name:
            q += left * p
            left *= 1 - p
    return q


RUBBLE = ["cobblestone", "mossy_cobblestone", "cobblestone_slab[type=bottom,waterlogged=false]",
          "stone_brick_slab[type=bottom,waterlogged=false]", "mossy_cobblestone_slab[type=bottom,waterlogged=false]"]


def arruinar(o):
    t, rng = o.t, random.Random(2026)
    keepset = o.protect | {p for p, _ in o.chests}

    def rm(x, y, z):
        if (x, y, z) not in keepset and (x, y, z) in t.blocks:
            t.set(x, y, z, "air")

    def rubble(x, y, z, pool=RUBBLE, p=0.4):
        if (x, y, z) in keepset or rng.random() > p:
            return
        b = t.get(x, y, z)
        if b in (None, "minecraft:air"):
            t.set(x, y, z, rng.choice(pool))

    # a) brecha en la esquina noreste de la muralla, con escombros dentro del patio
    for x in range(66, 81):
        for z in range(2, 13):
            d = max(abs(x - 77), abs(z - 4))
            keep = 2 + int(d * 1.25)
            for y in range(max(keep, 2), 11):
                rm(x, y, z)
    for x in range(69, 78):
        for z in range(5, 11):
            rubble(x, 2, z, p=0.35)
    # a2) muro oeste del patio del trono: lienzo derrumbado hasta media altura, escombro a ambos lados
    for x in range(0, 3):
        for z in range(58, 73):
            d = abs(z - 65)
            keep = 4 + int(d * 0.8)
            for y in range(keep, 11):
                rm(x, y, z)
    for z in range(60, 71):
        rubble(3, 2, z, p=0.5)
        rubble(4, 2, z, p=0.25)
    # b) albardilla y últimas hiladas caídas en el muro este del jardín
    for z in range(95, 106):
        keep = 7 if abs(z - 100) < 3 else 8
        for x in range(78, 81):
            for y in range(keep, 11):
                rm(x, y, z)
        rubble(77, 2, z, p=0.5)
    # c) pabellón de las concubinas del sureste medio hundido: tejado y muro trasero abiertos
    for x in range(70, 78):
        for z in range(111, 119):
            for y in range(7, 17):
                rm(x, y, z)
    for z in range(110, 115):
        for y in range(4, 7):
            rm(75, y, z)
    rm(70, 6, 111)
    t.set(70, 3, 112, "lantern[hanging=false,waterlogged=false]")          # el farol caído
    for x in range(70, 75):
        for z in range(111, 116):
            rubble(x, 3, z, pool=RUBBLE[:2] + ["prismarine_brick_slab[type=bottom,waterlogged=false]", "moss_carpet"], p=0.3)
    for x in range(66, 75):
        if rng.random() < 0.5 and t.get(x, 4, 116) == "minecraft:red_terracotta":
            for y in (4, 5):
                if t.get(x, y, 117) in (None, "minecraft:air"):
                    t.set(x, y, 117, "vine[east=false,north=true,south=false,up=false,west=false]")
    # d) linterna de piedra derribada en el patio exterior
    for y in (2, 3, 4):
        rm(45, y, 23)
    t.set(45, 2, 23, "stone_brick_slab[type=bottom,waterlogged=false]")
    t.set(46, 2, 24, "chiseled_stone_bricks")
    # e) tejas caídas en la Puerta de la Armonía (sobre la despensa)
    for x in range(45, 48):
        for z in range(25, 28):
            for y in range(9, 16):
                rm(x, y, z)
    for x in range(45, 48):
        rubble(x, 3, 27, pool=["bamboo_mosaic_slab[type=bottom,waterlogged=false]"], p=0.6)

    # f) pabellón de la Puerta del Mediodía: esquina noreste del tejado hundida
    for x in range(43, 50):
        for z in range(0, 5):
            for y in range(15, 20):
                rm(x, y, z)
    # g) muro del jardín: hiladas altas caídas al oeste de la puerta de luna, escombro al pie
    for x in range(4, 13):
        keep = 6 + (x % 3 == 0)
        for z in (80, 81, 82):
            for y in range(keep, 11):
                rm(x, y, z)
        for z in (79, 83):
            rubble(x, 2, z, p=0.45)
    # h) balaustrada rota en la grada baja del este
    for z in range(50, 58):
        rm(58, 4, z)
        rubble(59, 2, z, pool=["diorite_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]",
                               "polished_diorite_slab[type=bottom,waterlogged=false]"], p=0.5)
    # i) vegetación: hiedra en las caras interiores de la muralla del jardín y musgo en los rincones
    for z in range(83, 120):
        for x, side in ((3, "west"), (77, "east")):
            for y in range(2, 9):
                if t.get(x, y, z) in (None, "minecraft:air") and rng.random() < 0.35 and \
                        t.get(x + (-1 if side == "west" else 1), y, z) == "minecraft:red_terracotta":
                    t.set(x, y, z, f"vine[east={'true' if side == 'east' else 'false'},north=false,south=false,up=false,"
                                   f"west={'true' if side == 'west' else 'false'}]")
    for x in range(4, 77):
        for y in range(2, 9):
            if t.get(x, y, 119) in (None, "minecraft:air") and rng.random() < 0.3 and t.get(x, y, 120) == "minecraft:red_terracotta":
                t.set(x, y, 119, "vine[east=false,north=false,south=true,up=false,west=false]")
    for (x0, z0, x1, z1) in ((3, 5, 10, 13), (70, 19, 77, 27), (3, 58, 7, 79), (73, 58, 77, 79)):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if t.get(x, 2, z) in (None, "minecraft:air") and t.get(x, 1, z) == "minecraft:stone_bricks" and rng.random() < 0.45:
                    t.set(x, 2, z, "moss_carpet")
    # j) tejas sueltas: falta alguna teja en todos los tejados (debajo queda el macizo del tejado)
    for p, (st, _) in list(t.blocks.items()):
        if ("bamboo_mosaic_stairs" in st or "prismarine_brick_stairs" in st) and "outer" not in st and p not in keepset \
                and t.get(p[0], p[1] - 1, p[2]) not in (None, "minecraft:air") and rng.random() < 0.12:
            t.set(*p, "air")
    # k) hierba y musgo que rompen el pavimento junto a los muros de los patios
    for (x0, z0, x1, z1) in ((3, 5, 77, 27), (3, 31, 77, 79)):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge = min(x - x0, x1 - x, z - z0, z1 - z)
                if edge <= 3 and t.get(x, 1, z) == "minecraft:stone_bricks" and t.get(x, 2, z) in (None, "minecraft:air", "minecraft:moss_carpet") \
                        and rng.random() < 0.35 - 0.07 * edge:
                    t.set(x, 1, z, rng.choice(["moss_block", "grass_block[snowy=false]", "coarse_dirt", "mossy_cobblestone"]))
