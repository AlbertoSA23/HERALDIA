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
from core import ANCLADO_TAG, ADULTO_TAG
from .botin import LOOT


def _tablas(t):
    out = []
    for p, (st, nbt) in t.blocks.items():
        if nbt and nbt.get("LootTable"):
            out.append((p, str(nbt["LootTable"])))
    return out


def errores(o, tipo):
    from . import MAX_ENTIDADES, ALTURA_FARO
    t, err = o.t, []
    x0, y0, z0, x1, y1, z1 = t.bounds()
    if max(x1 - x0, z1 - z0) + 1 > 8 * 16 - 32:
        err.append(f"huella de {x1 - x0 + 1} x {z1 - z0 + 1}: no cabe en el alcance de un inicio")
    tx0, tz0, tx1, tz1 = o.tierra
    mx0, mz0, mx1, mz1 = o.mar
    if not (tx0 <= tx1 and tz0 <= tz1 < 0 and mx0 <= mx1 and 0 < mz0 <= mz1):
        err.append(f"huellas de tierra {o.tierra} y de mar {o.mar}: la tierra detrás del ancla (z < 0) y el mar delante")
    for p, tabla in _tablas(t):
        if not tabla.startswith("heraldia:costa/") or tabla.split("/", 1)[1] not in LOOT:
            err.append(f"tabla desconocida {tabla} en {p}")
    if len(t.entities) > MAX_ENTIDADES:
        err.append(f"{len(t.entities)} entidades (máximo {MAX_ENTIDADES})")
    for *_, n in t.entities:
        if n.get("id") != "minecraft:villager" and ANCLADO_TAG not in (n.get("Tags") or []):
            err.append(f"{n.get('id')} sin anclar")
        if str(n.get("PersistenceRequired", 0)) != "1":
            err.append(f"{n.get('id')} no persistente")
    if tipo == "faro":
        err += _faro(o, ALTURA_FARO)
    else:
        err += _naufragio(o)
    return err


def _faro(o, altura):
    t, err = o.t, []
    _, y0, _, _, y1, _ = t.bounds()
    if not altura[0] <= y1 - y0 + 1 <= altura[1]:
        err.append(f"faro de {y1 - y0 + 1} bloques (de {altura[0]} a {altura[1]})")
    if y0 != 0:
        err.append("algo bajo la plataforma (y < 0)")
    x, y, z = o.luz
    if t.get(x, y, z) != "minecraft:redstone_lamp[lit=true]" or t.get(x, y - 1, z) != "minecraft:redstone_block":
        err.append(f"la luz de {o.luz} no es una lámpara encendida sobre un bloque de redstone")
    if y < y1 - 5:
        err.append(f"la luz ({y}) no está en lo alto ({y1})")
    vidrios = sum(1 for (bx, by, bz), (st, _) in t.blocks.items() if by == y and "glass" in st)
    if vidrios < 6:
        err.append("la linterna no tiene sus cristales")
    escalera = sorted(by for (bx, by, bz), (st, _) in t.blocks.items() if "ladder" in st)
    if not escalera or escalera != list(range(1, escalera[-1] + 1)) or escalera[-1] < o.galeria:
        err.append("la escalera de mano no sube seguida hasta la galería")
    tablas = [(bz, by) for (bx, by, bz), (st, _) in t.blocks.items() if by == 0 and bz > 0 and "planks" in st]
    pilotes = [(bz, by) for (bx, by, bz), (st, _) in t.blocks.items() if by == 0 and bz > 0 and "_log" in st]
    if len(tablas) < 10 or len(pilotes) < 6:
        err.append("sin embarcadero sobre el mar (tablas y pilotes en z > 0)")
    if sum(1 for *_, n in t.entities if n.get("id") == "minecraft:villager") > 1:
        err.append("más de un farero")
    return err


def _naufragio(o):
    t, err = o.t, []
    fila = o.fila_mar
    mojado = 0
    for (x, y, z), (st, _) in t.blocks.items():
        if y <= fila:
            if st.startswith("minecraft:air"):
                err.append(f"aire bajo el agua en {(x, y, z)} (fila del mar {fila}): el mar se derramaría")
            else:
                mojado += 1
    if not mojado:
        err.append("el casco no toca el agua")
    for p, tabla in _tablas(t):
        if tabla.endswith("/camarote") and p[1] <= fila:
            err.append(f"el cofre del camarote bajo el agua en {p}")
    mastiles = {(x, z) for (x, y, z), (st, _) in t.blocks.items() if "_log[axis=y]" in st}
    if len(mastiles) < 2:
        err.append("sin sus dos mástiles")
    for *_, n in t.entities:
        if n.get("id") == "minecraft:drowned" and ADULTO_TAG not in (n.get("Tags") or []):
            err.append("ahogado sin la etiqueta de adulto")
    return err
