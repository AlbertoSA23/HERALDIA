"""Auditoría propia de la costa (además de la genérica de apoyos de lint.py): lo que el Java da por hecho al colocar las
plantillas y lo que no se ve sin entrar al juego.

  faro       alto de 20 a 35 bloques; la luz arriba (lámpara de redstone encendida sobre un bloque de redstone, con
             vidrio alrededor); escalera de mano seguida de la planta baja a la galería; embarcadero sobre el mar (z > 0)
             con pilotes en la fila inferior; nada bajo la plataforma.
  naufragio  ningún aire en las filas de bajo el agua (y <= fila_mar: el mar no entra ni se derrama), el casco toca el
             agua (hay casco bajo fila_mar), el cofre del camarote en seco, dos mástiles y el ahogado (si lo hay) anclado
             y adulto.
  los dos    cofres y toneles con tabla heraldia:costa/<tabla> de botin.LOOT; como mucho MAX_ENTIDADES entidades; la
             huella cabe en el alcance de un inicio; la huella de tierra detrás del ancla y la de mar delante.
"""
from core import ANCHORED_TAG, ADULT_TAG
from .chest_loot import LOOT


def _tables(t):
    out = []
    for p, (st, nbt) in t.blocks.items():
        if nbt and nbt.get("LootTable"):
            out.append((p, str(nbt["LootTable"])))
    return out


def errors(o, kind):
    from . import MAX_ENTITIES, LIGHTHOUSE_HEIGHT
    t, err = o.t, []
    x0, y0, z0, x1, y1, z1 = t.bounds()
    if max(x1 - x0, z1 - z0) + 1 > 8 * 16 - 32:
        err.append(f"huella de {x1 - x0 + 1} x {z1 - z0 + 1}: no cabe en el alcance de un inicio")
    tx0, tz0, tx1, tz1 = o.land
    mx0, mz0, mx1, mz1 = o.sea
    if not (tx0 <= tx1 and tz0 <= tz1 < 0 and mx0 <= mx1 and 0 < mz0 <= mz1):
        err.append(f"huellas de tierra {o.land} y de mar {o.sea}: la tierra detrás del ancla (z < 0) y el mar delante")
    for p, tbl in _tables(t):
        if not tbl.startswith("heraldia:costa/") or tbl.split("/", 1)[1] not in LOOT:
            err.append(f"tabla desconocida {tbl} en {p}")
    if len(t.entities) > MAX_ENTITIES:
        err.append(f"{len(t.entities)} entidades (máximo {MAX_ENTITIES})")
    for *_, n in t.entities:
        if n.get("id") != "minecraft:villager" and ANCHORED_TAG not in (n.get("Tags") or []):
            err.append(f"{n.get('id')} sin anclar")
        if str(n.get("PersistenceRequired", 0)) != "1":
            err.append(f"{n.get('id')} no persistente")
    if kind == "faro":
        err += _lighthouse(o, LIGHTHOUSE_HEIGHT)
    else:
        err += _shipwreck(o)
    return err


def _lighthouse(o, height):
    t, err = o.t, []
    _, y0, _, _, y1, _ = t.bounds()
    if not height[0] <= y1 - y0 + 1 <= height[1]:
        err.append(f"faro de {y1 - y0 + 1} bloques (de {height[0]} a {height[1]})")
    if y0 != 0:
        err.append("algo bajo la plataforma (y < 0)")
    x, y, z = o.light
    if t.get(x, y, z) != "minecraft:redstone_lamp[lit=true]" or t.get(x, y - 1, z) != "minecraft:redstone_block":
        err.append(f"la luz de {o.light} no es una lámpara encendida sobre un bloque de redstone")
    if y < y1 - 5:
        err.append(f"la luz ({y}) no está en lo alto ({y1})")
    glass_panes = sum(1 for (bx, by, bz), (st, _) in t.blocks.items() if by == y and "glass" in st)
    if glass_panes < 6:
        err.append("la linterna no tiene sus cristales")
    stairs = sorted(by for (bx, by, bz), (st, _) in t.blocks.items() if "ladder" in st)
    if not stairs or stairs != list(range(1, stairs[-1] + 1)) or stairs[-1] < o.tunnel:
        err.append("la escalera de mano no sube seguida hasta la galería")
    tables = [(bz, by) for (bx, by, bz), (st, _) in t.blocks.items() if by == 0 and bz > 0 and "planks" in st]
    piles = [(bz, by) for (bx, by, bz), (st, _) in t.blocks.items() if by == 0 and bz > 0 and "_log" in st]
    if len(tables) < 10 or len(piles) < 6:
        err.append("sin embarcadero sobre el mar (tablas y pilotes en z > 0)")
    if sum(1 for *_, n in t.entities if n.get("id") == "minecraft:villager") > 1:
        err.append("más de un farero")
    return err


def _shipwreck(o):
    t, err = o.t, []
    row = o.sea_row
    wet = 0
    for (x, y, z), (st, _) in t.blocks.items():
        if y <= row:
            if st.startswith("minecraft:air"):
                err.append(f"aire bajo el agua en {(x, y, z)} (fila del mar {row}): el mar se derramaría")
            else:
                wet += 1
    if not wet:
        err.append("el casco no toca el agua")
    for p, tbl in _tables(t):
        if tbl.endswith("/camarote") and p[1] <= row:
            err.append(f"el cofre del camarote bajo el agua en {p}")
    mast_cells = {(x, z) for (x, y, z), (st, _) in t.blocks.items() if "_log[axis=y]" in st}
    if len(mast_cells) < 2:
        err.append("sin sus dos mástiles")
    for *_, n in t.entities:
        if n.get("id") == "minecraft:drowned" and ADULT_TAG not in (n.get("Tags") or []):
            err.append("ahogado sin la etiqueta de adulto")
    return err
