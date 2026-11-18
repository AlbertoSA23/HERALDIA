"""Auditoría de las entradas a mina (condición para generar; la genérica de lint.py no sirve para una plantilla sin
caja que baja 30 bloques bajo el patio). Devuelve la lista de errores de una obra (minas.obra):

- estanca: toda celda excavada tiene escritas sus 6 vecinas (no entra agua ni lava de las cuevas vanilla) y ningún forro
  es de un bloque natural (dentro no nacerían manantiales, liquen ni charcas);
- se baja andando (recorrido.andar, sin saltos): desde el patio se llega a todos los cruces de la galería y junto a
  todos los cofres; en la grande, también por el pozo de la torre sin pasar por la boca (la escalera de caracol);
- la vía sigue sin descarrilar del patio al último cruce del tronco (en la grande, hasta el nivel hondo) y cada raíl
  tiene debajo un bloque macizo;
- botín: cada contenedor con una tabla de LOOT y todas las tablas del tamaño en algún contenedor;
- entidades y generadores dentro del máximo, los mobs persistentes y anclados, y muestras de techo para el Java.
"""
from core import ANCHORED_TAG
from uniques._common import walkthrough
from uniques.lost_mine.tracks import traverse, is_rail
from .construction import N6

NATURAL = {"stone", "deepslate", "tuff", "andesite", "granite", "diorite", "dirt", "gravel", "sand", "red_sand", "clay",
           "calcite", "grass_block", "coarse_dirt", "moss_block", "snow_block", "packed_ice", "powder_snow"}
TABLES = {"pequena": {"boca", "galeria"}, "mediana": {"vagoneta", "capataz", "fundicion", "galeria"},
          "grande": {"vagoneta", "capataz", "fundicion", "galeria", "filon"}}


def name(st):
    return st.split("[")[0].replace("minecraft:", "") if st else None


def errors(o, size):
    from . import MAX_ENTITIES, MAX_GENERATORS, LOOT
    t, e = o.t, []
    blocks = t.blocks
    # estanca y sin forro natural
    open_ones = [c for c in o.carved for d in N6 if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) not in blocks]
    if open_ones:
        e.append(f"{len(open_ones)} celdas excavadas sin cerrar, p. ej. {sorted(open_ones)[0]}")
    lining = {(c[0] + d[0], c[1] + d[1], c[2] + d[2]) for c in o.carved for d in N6} - o.carved - o.surface
    naturals = sorted(p for p in lining if p in blocks and name(blocks[p][0]) in NATURAL)
    if naturals:
        e.append(f"{len(naturals)} bloques naturales en el forro, p. ej. {naturals[0]} {blocks[naturals[0]][0]}")
    # recorrido a pie
    x0, y0, z0, x1, y1, z1 = t.bounds()
    view = {p: st for p, (st, _) in blocks.items()}
    start = (2, 1, -2)
    reach, _ = walkthrough.strict_walk(walkthrough.View(view), start, (x0, x1, z0, z1))
    for (x, y, z) in o.nodes:
        if (x, y + 1, z) not in reach:
            e.append(f"cruce de la galería en {(x, y + 1, z)} inalcanzable a pie desde el patio")
    for (x, y, z), tbl in o.chest_list:
        if not any((x + dx, y + dy, z + dz) in reach for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) for dy in (0, -1, 1)):
            e.append(f"cofre {tbl} en {(x, y, z)} inalcanzable")
    if o.descent:
        no_mouth = dict(view)
        for y in range(-3, 4):
            for x in range(-1, 2):
                no_mouth[(x, y, 4)] = "minecraft:stone"          # tapiada la bajada: solo queda el pozo
        reach2, _ = walkthrough.strict_walk(walkthrough.View(no_mouth), start, (x0, x1, z0, z1))
        bx, by, bz = o.descent
        if (bx, by, bz + 1) not in reach2:
            e.append(f"el pie de la escalera de caracol {(bx, by, bz + 1)} no se alcanza bajando por el pozo")
    # vía del patio a la galería
    get = lambda x, y, z: view.get((x, y, z))
    for ini, direction, _ in o.tracks:
        if not is_rail(get(*ini)):
            e.append(f"no hay vía en {ini}")
            continue
        try:
            finish, road = traverse(get, ini, direction, steps=2000)
        except ValueError as err:
            e.append(f"vía: {err}")
            continue
        deep = min(n[1] for n in o.nodes) + 1
        if finish[1] != deep:
            e.append(f"la vía desde {ini} acaba en {finish}, no en el nivel más hondo (pies {deep})")
    # cada raíl sobre un bloque macizo (sobre un camino de tierra, una losa o un escalón saltaría al primer aviso)
    for p, (st, _) in blocks.items():
        if is_rail(st):
            below = view.get((p[0], p[1] - 1, p[2]))
            if not walkthrough.is_full(below) or name(below) in ("dirt_path", "farmland", "glass"):
                e.append(f"raíl en {p} sin apoyo macizo ({below})")
                break
    # botín
    used = set()
    for p, (st, nbt) in blocks.items():
        lt = nbt.get("LootTable") if nbt else None
        if lt:
            short = str(lt).split("heraldia:minas/")[-1]
            if not str(lt).startswith("heraldia:minas/") or short not in LOOT:
                e.append(f"contenedor en {p} con una tabla ajena: {lt}")
            used.add(short)
    for *_, n in t.entities:
        if n.get("LootTable"):
            used.add(str(n["LootTable"]).split("heraldia:minas/")[-1])
    if used != TABLES[size]:
        e.append(f"tablas usadas {sorted(used)}, esperadas {sorted(TABLES[size])}")
    # entidades y generadores
    if len(t.entities) > MAX_ENTITIES:
        e.append(f"{len(t.entities)} entidades (máximo {MAX_ENTITIES})")
    for *_, n in t.entities:
        if n["id"] not in ("minecraft:minecart", "minecraft:chest_minecart") and \
                (not n.get("PersistenceRequired") or ANCHORED_TAG not in (n.get("Tags") or [])):
            e.append(f"{n['id']} sin PersistenceRequired o sin anclar")
    gen = sum(1 for st, _ in blocks.values() if st.startswith("minecraft:spawner"))
    if gen > MAX_GENERATORS[size]:
        e.append(f"{gen} generadores (máximo {MAX_GENERATORS[size]})")
    if len(o.roof_samples()) < 4:
        e.append("menos de 4 muestras de techo para el Java")
    return e
