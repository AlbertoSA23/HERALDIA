"""Filler loot (filler_loot.py) on a real 26.3 dedicated server: no container of a Heraldia structure is empty.

Usage: python3 tools/smoke/filler_loot.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-relleno"
One start, no extra mods. It reads the templates from the .jar itself (what a world really gets) and:
  - every filler table (heraldia:relleno/<name>) loads in the game and, rolled ten times with /loot spawn, gives at least
    one item every time;
  - it places one template of each family (a village house and an inn, a mine, a shipwreck, a medium structure, a piece
    of a unique structure and a hut of the spawn roads) with /place template, and for two filler containers of each it
    checks that the placed block keeps its filler table and that a hopper put under it (the game unpacks the table the
    same way when a player opens it) gets items out of it.
"""
import argparse, os, re, sys, zipfile, gzip, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guide import Server

import nbtlib

PREFIX = "heraldia:relleno/"
SAMPLES = ["taiga_eslava/houses/medium_3", "llanuras_castellana/specials/inn", "minas/pequena/taiga/a",
           "costa/naufragio/templada/a", "medianas/pescador/playa/b", "unicas/mansion/sotano", "casa_heraldo/choza_fisherman"]
PER_TEMPLATE = 2
ROLLS = 10
ORIGIN = (0, 120, 0)
STEP = 64                    # templates side by side along x


def jar_templates(jar):
    """{template: (size, [(local pos, block, table)] of its filler containers)} of SAMPLES, and the filler table names."""
    out = {}
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        tables = sorted(re.sub(r".*/relleno/(.*)\.json$", r"\1", n) for n in names
                        if re.match(r"data/heraldia/loot_table/relleno/[^/]+\.json$", n))
        for t in SAMPLES:
            raw = gzip.decompress(z.read(f"data/heraldia/structure/{t}.nbt"))
            n = nbtlib.File.parse(io.BytesIO(raw))
            pal = n["palette"]
            found = []
            for b in n["blocks"]:
                nb = b.get("nbt") or {}
                lt = str(nb.get("LootTable", ""))
                if lt.startswith(PREFIX):
                    pe = pal[int(b["state"])]
                    found.append((tuple(int(c) for c in b["pos"]), str(pe.get("Name") or pe.get("id")), lt))
            out[t] = ([int(c) for c in n["size"]], found)
    return out, tables


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-relleno"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    templates, tables = jar_templates(os.path.abspath(a.jar))
    fails, ok = [], 0

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)
            print("FAIL:", msg)

    check(len(tables) >= 10, f"only {len(tables)} filler tables in the jar")
    for t, (_, found) in templates.items():
        check(len(found) >= 1, f"{t}: no container with a filler table in the jar's template")
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    srv = Server(a.work, launcher)
    ctx = srv.ctx
    at = lambda p: " ".join(str(v) for v in p)
    try:
        x0, y0, z0 = ORIGIN
        span = STEP * len(SAMPLES)
        ctx.run(f"forceload add {x0 - 16} {z0 - 16} {x0 + span} {z0 + STEP}", r"Marked|force|already|[Aa]dded")
        for rule in ("spawn_mobs", "advance_time"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
        # 1) every filler table, rolled ROLLS times, gives something every time
        for name in tables:
            counts = []
            for _ in range(ROLLS):
                m = ctx.run(f"loot spawn {x0} {y0} {z0} loot {PREFIX}{name}", r"Dropped (\d+)|No loot|[Uu]nknown|[Ii]nvalid")
                counts.append(int(m.group(1)) if m.group(1) else 0)
            check(min(counts) >= 1, f"{PREFIX}{name}: a roll gave nothing ({counts})")
            ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity")
        # 2) placed templates: the containers keep their filler table and give items when unpacked
        for i, t in enumerate(SAMPLES):
            size, found = templates[t]
            base = (x0 + i * STEP, y0, z0)
            for _ in range(s.PLACE_ATTEMPTS):
                m = ctx.run(f"place template heraldia:{t} {at(base)}", r"Loaded template|not loaded|Failed|Invalid|Unknown")
                if "not loaded" not in m.group(0):
                    break
                ctx.ticks(40)
            check("Loaded" in m.group(0), f"place template {t}: {m.string.strip()}")
            for (lx, ly, lz), block, table in found[:PER_TEMPLATE]:
                p = (base[0] + lx, base[1] + ly, base[2] + lz)
                below = (p[0], p[1] - 1, p[2])
                check(ctx.test(f'execute if data block {at(p)} {{LootTable:"{table}"}}'), f"{t} {p}: {block} without {table}")
                ctx.run(f"setblock {at(below)} minecraft:hopper[facing=down]", r"Changed the block|Could not set")
                got = ctx.until(f"execute if data block {at(below)} Items[0]")
                check(got, f"{t} {p}: the hopper under the {block} got nothing out of {table}")
                check(ctx.test(f"execute unless data block {at(p)} LootTable"), f"{t} {p}: its table was not unpacked")
                if got:
                    print(f"OK {t} {block} {table}")
    finally:
        srv.stop()
    print(f"\n{ok} checks OK, {len(fails)} failures")
    for f in fails:
        print(" -", f)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
