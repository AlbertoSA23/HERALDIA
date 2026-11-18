"""The coast's own audit (besides the generic support one of lint.py): what the Java takes for granted when placing the
templates and what cannot be seen without entering the game.

  lighthouse  20 to 35 blocks tall; the light at the top (lit redstone lamp on a redstone block, with
              glass around); continuous ladder from the ground floor to the gallery; pier over the sea (z > 0)
              with piles in the bottom row; nothing under the platform.
  shipwreck   no air in the rows below the water (y <= fila_mar: the sea does not get in or spill), the hull touches the
              water (there is hull below fila_mar), the cabin chest dry, two masts and the drowned (if any) anchored
              and adult.
  both        chests and barrels with table heraldia:costa/<table> from chest_loot.LOOT; at most MAX_ENTITIES entities; the
              footprint fits in the reach of a start; the land footprint behind the anchor and the sea one in front.
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
        err.append(f"footprint of {x1 - x0 + 1} x {z1 - z0 + 1}: does not fit in the reach of a start")
    tx0, tz0, tx1, tz1 = o.land
    mx0, mz0, mx1, mz1 = o.sea
    if not (tx0 <= tx1 and tz0 <= tz1 < 0 and mx0 <= mx1 and 0 < mz0 <= mz1):
        err.append(f"land footprint {o.land} and sea footprint {o.sea}: the land behind the anchor (z < 0) and the sea in front")
    for p, tbl in _tables(t):
        if not tbl.startswith("heraldia:costa/") or tbl.split("/", 1)[1] not in LOOT:
            err.append(f"tabla desconocida {tbl} en {p}")
    if len(t.entities) > MAX_ENTITIES:
        err.append(f"{len(t.entities)} entities (maximum {MAX_ENTITIES})")
    for *_, n in t.entities:
        if n.get("id") != "minecraft:villager" and ANCHORED_TAG not in (n.get("Tags") or []):
            err.append(f"{n.get('id')} not anchored")
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
        err.append(f"lighthouse of {y1 - y0 + 1} blocks (from {height[0]} to {height[1]})")
    if y0 != 0:
        err.append("something under the platform (y < 0)")
    x, y, z = o.light
    if t.get(x, y, z) != "minecraft:redstone_lamp[lit=true]" or t.get(x, y - 1, z) != "minecraft:redstone_block":
        err.append(f"the light at {o.light} is not a lit lamp on a redstone block")
    if y < y1 - 5:
        err.append(f"the light ({y}) is not at the top ({y1})")
    glass_panes = sum(1 for (bx, by, bz), (st, _) in t.blocks.items() if by == y and "glass" in st)
    if glass_panes < 6:
        err.append("the lantern has no glass")
    stairs = sorted(by for (bx, by, bz), (st, _) in t.blocks.items() if "ladder" in st)
    if not stairs or stairs != list(range(1, stairs[-1] + 1)) or stairs[-1] < o.tunnel:
        err.append("the ladder does not run continuously up to the gallery")
    tables = [(bz, by) for (bx, by, bz), (st, _) in t.blocks.items() if by == 0 and bz > 0 and "planks" in st]
    piles = [(bz, by) for (bx, by, bz), (st, _) in t.blocks.items() if by == 0 and bz > 0 and "_log" in st]
    if len(tables) < 10 or len(piles) < 6:
        err.append("no pier over the sea (planks and piles at z > 0)")
    if sum(1 for *_, n in t.entities if n.get("id") == "minecraft:villager") > 1:
        err.append("more than one lighthouse keeper")
    return err


def _shipwreck(o):
    t, err = o.t, []
    row = o.sea_row
    wet = 0
    for (x, y, z), (st, _) in t.blocks.items():
        if y <= row:
            if st.startswith("minecraft:air"):
                err.append(f"air under the water at {(x, y, z)} (sea row {row}): the sea would spill")
            else:
                wet += 1
    if not wet:
        err.append("the hull does not touch the water")
    for p, tbl in _tables(t):
        if tbl.endswith("/camarote") and p[1] <= row:
            err.append(f"the cabin chest under the water at {p}")
    mast_cells = {(x, z) for (x, y, z), (st, _) in t.blocks.items() if "_log[axis=y]" in st}
    if len(mast_cells) < 2:
        err.append("without its two masts")
    for *_, n in t.entities:
        if n.get("id") == "minecraft:drowned" and ADULT_TAG not in (n.get("Tags") or []):
            err.append("drowned without the adult tag")
    return err
