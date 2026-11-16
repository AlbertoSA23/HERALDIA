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
from core import ANCLADO_TAG
from unicas._comun import recorrido
from unicas.mina_perdida.vias import recorrer, es_rail
from .obra import N6

NATURAL = {"stone", "deepslate", "tuff", "andesite", "granite", "diorite", "dirt", "gravel", "sand", "red_sand", "clay",
           "calcite", "grass_block", "coarse_dirt", "moss_block", "snow_block", "packed_ice", "powder_snow"}
TABLAS = {"pequena": {"boca", "galeria"}, "mediana": {"vagoneta", "capataz", "fundicion", "galeria"},
          "grande": {"vagoneta", "capataz", "fundicion", "galeria", "filon"}}


def nombre(st):
    return st.split("[")[0].replace("minecraft:", "") if st else None


def errores(o, tam):
    from . import MAX_ENTIDADES, MAX_GENERADORES, LOOT
    t, e = o.t, []
    blocks = t.blocks
    # estanca y sin forro natural
    abiertas = [c for c in o.carved for d in N6 if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) not in blocks]
    if abiertas:
        e.append(f"{len(abiertas)} celdas excavadas sin cerrar, p. ej. {sorted(abiertas)[0]}")
    forro = {(c[0] + d[0], c[1] + d[1], c[2] + d[2]) for c in o.carved for d in N6} - o.carved - o.superficie
    naturales = sorted(p for p in forro if p in blocks and nombre(blocks[p][0]) in NATURAL)
    if naturales:
        e.append(f"{len(naturales)} bloques naturales en el forro, p. ej. {naturales[0]} {blocks[naturales[0]][0]}")
    # recorrido a pie
    x0, y0, z0, x1, y1, z1 = t.bounds()
    vista = {p: st for p, (st, _) in blocks.items()}
    inicio = (2, 1, -2)
    alc, _ = recorrido.andar(recorrido.Vista(vista), inicio, (x0, x1, z0, z1))
    for (x, y, z) in o.nodos:
        if (x, y + 1, z) not in alc:
            e.append(f"cruce de la galería en {(x, y + 1, z)} inalcanzable a pie desde el patio")
    for (x, y, z), tabla in o.cofres:
        if not any((x + dx, y + dy, z + dz) in alc for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) for dy in (0, -1, 1)):
            e.append(f"cofre {tabla} en {(x, y, z)} inalcanzable")
    if o.bajada:
        sin_boca = dict(vista)
        for y in range(-3, 4):
            for x in range(-1, 2):
                sin_boca[(x, y, 4)] = "minecraft:stone"          # tapiada la bajada: solo queda el pozo
        alc2, _ = recorrido.andar(recorrido.Vista(sin_boca), inicio, (x0, x1, z0, z1))
        bx, by, bz = o.bajada
        if (bx, by, bz + 1) not in alc2:
            e.append(f"el pie de la escalera de caracol {(bx, by, bz + 1)} no se alcanza bajando por el pozo")
    # vía del patio a la galería
    get = lambda x, y, z: vista.get((x, y, z))
    for ini, sentido, _ in o.vias:
        if not es_rail(get(*ini)):
            e.append(f"no hay vía en {ini}")
            continue
        try:
            fin, camino = recorrer(get, ini, sentido, pasos=2000)
        except ValueError as err:
            e.append(f"vía: {err}")
            continue
        hondo = min(n[1] for n in o.nodos) + 1
        if fin[1] != hondo:
            e.append(f"la vía desde {ini} acaba en {fin}, no en el nivel más hondo (pies {hondo})")
    # cada raíl sobre un bloque macizo (sobre un camino de tierra, una losa o un escalón saltaría al primer aviso)
    for p, (st, _) in blocks.items():
        if es_rail(st):
            debajo = vista.get((p[0], p[1] - 1, p[2]))
            if not recorrido.is_full(debajo) or nombre(debajo) in ("dirt_path", "farmland", "glass"):
                e.append(f"raíl en {p} sin apoyo macizo ({debajo})")
                break
    # botín
    usadas = set()
    for p, (st, nbt) in blocks.items():
        lt = nbt.get("LootTable") if nbt else None
        if lt:
            corta = str(lt).split("heraldia:minas/")[-1]
            if not str(lt).startswith("heraldia:minas/") or corta not in LOOT:
                e.append(f"contenedor en {p} con una tabla ajena: {lt}")
            usadas.add(corta)
    for *_, n in t.entities:
        if n.get("LootTable"):
            usadas.add(str(n["LootTable"]).split("heraldia:minas/")[-1])
    if usadas != TABLAS[tam]:
        e.append(f"tablas usadas {sorted(usadas)}, esperadas {sorted(TABLAS[tam])}")
    # entidades y generadores
    if len(t.entities) > MAX_ENTIDADES:
        e.append(f"{len(t.entities)} entidades (máximo {MAX_ENTIDADES})")
    for *_, n in t.entities:
        if n["id"] not in ("minecraft:minecart", "minecraft:chest_minecart") and \
                (not n.get("PersistenceRequired") or ANCLADO_TAG not in (n.get("Tags") or [])):
            e.append(f"{n['id']} sin PersistenceRequired o sin anclar")
    gen = sum(1 for st, _ in blocks.values() if st.startswith("minecraft:spawner"))
    if gen > MAX_GENERADORES[tam]:
        e.append(f"{gen} generadores (máximo {MAX_GENERADORES[tam]})")
    if len(o.muestras_techo()) < 4:
        e.append("menos de 4 muestras de techo para el Java")
    return e
