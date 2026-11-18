"""Cleared uniques (jefes.apagar_generadores) on a real 26.3 dedicated server.

Usage: python3 tools/smoke/cleared_spawners.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
A really generated castle (--sid; /place structure does not save the start, so it would not count) is located and loaded,
and its guardian found. The guardian is moved (with fire resistance, at night) to the structure's start chunk, which in the
castle is more than 2 chunks from its spawners; then only that chunk stays forced (a forced chunk keeps 5 x 5 chunks
loaded), the server restarts (so the rest of the structure is not in memory) and the guardian is killed: still inside its
structure (the start's references reach that chunk), with some spawners in chunks that are not loaded. It checks:
  - the log reports the structure cleared, with its spawners turned off and the ones of unloaded chunks pending;
  - each turned-off spawner is still a spawner but has no mob (no SpawnData.entity.id);
  - loading the rest of the structure turns off the pending ones (log and blocks);
  - a second guardian of the same structure dying (summoned with its tags) does nothing more, not even to a spawner
    filled again by hand; also after a restart (the record is saved in the world);
  - no Heraldia errors in the log.
"""
import argparse, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from guide import Server
from medium_structures import forceload

SID = "castillo"           # the test configuration puts one every ~1,000 blocks; large enough for some spawners to unload
AREA = 160                 # blocks loaded around the /locate position to find the guardian (the castle fits in it)
PENDING_DONE = r"Heraldia: bosses: (\d+) pending spawners turned off when chunk .* loaded: (.*)"
POS = re.compile(r"(pending )?(-?\d+) (-?\d+) (-?\d+)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-generadores"))
    ap.add_argument("--sid", default=SID, help="unique to clear (default: castillo)")
    ap.add_argument("--area", type=int, default=AREA)
    a = ap.parse_args()
    sid, area = a.sid, a.area
    GUARDIAN = f"@e[tag=heraldia_guardian.{sid}]"
    DEFEATED = (rf"Heraldia: bosses: \S+ defeated: (heraldia:unicas/{sid}@-?\d+) cleared, (\d+) spawners turned off, "
                rf"(\d+) pending until their chunk loads \((\d+) ms\): (.*)")
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    fails, ok = [], 0
    srv = Server(a.work, launcher)
    ctx = srv.ctx

    def check(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)
            print("FAIL:", msg)
        return cond

    def off(p):
        """Still a spawner, without a mob to spawn."""
        x, y, z = p
        return (ctx.test(f"execute if block {x} {y} {z} minecraft:spawner")
                and not ctx.test(f"execute if data block {x} {y} {z} SpawnData.entity.id"))

    def load_area(x, z, remove=False):
        """forceload of the whole area in quadrants (a forceload command takes at most 256 chunks)."""
        for x0, x1 in ((x - area, x - 1), (x, x + area)):
            for z0, z1 in ((z - area, z - 1), (z, z + area)):
                forceload(ctx, x0, z0, x1, z1, remove=remove)

    def defeated_lines():
        return re.findall(DEFEATED, ctx.log())

    try:
        m = ctx.run(f"locate structure heraldia:unicas/{sid}", r"is at \[(-?\d+), [^,]+, (-?\d+)\]|Could not find")
        if not m.lastindex or not m.group(1):
            raise SystemExit(f"/locate does not find any {sid}")
        lx, lz = int(m.group(1)), int(m.group(2))
        print(f"{sid} at {lx}, {lz}")
        load_area(lx, lz)
        if not ctx.wait_entity(GUARDIAN, timeout=600):
            raise SystemExit(f"the guardian of the {sid} at {lx}, {lz} does not appear")
        gx, gy, gz = (int(v // 1) for v in ctx.pos(GUARDIAN))
        print(f"guardian at {gx} {gy} {gz}")
        # to the start chunk, on the surface: far enough from the spawners for some to unload (see the docstring)
        ctx.run("time set midnight", r"[Ss]et the time|[Tt]ime")
        ctx.run(f"effect give {GUARDIAN} minecraft:fire_resistance infinite 0 true", r"Applied effect|Unable|No entity")
        ctx.run(f"execute positioned {lx + 8} 0 {lz + 8} positioned over motion_blocking run tp {GUARDIAN} ~ ~ ~",
                r"Teleported|No entity")
        gx, gy, gz = (int(v // 1) for v in ctx.pos(GUARDIAN))
        print(f"guardian moved to {gx} {gy} {gz}")

        # only the guardian's chunk stays forced, and the server restarts: the rest of the structure is not in memory any more
        # (a chunk that only drops below full stays cached and is handled at once; that case is the one of the first start)
        load_area(lx, lz, remove=True)
        forceload(ctx, gx, gz, gx, gz)
        srv.stop()
        srv = Server(a.work, launcher)
        ctx = srv.ctx
        if not ctx.wait_entity(GUARDIAN, timeout=300):
            raise SystemExit("the guardian does not come back after the restart")

        ctx.run(f"kill {GUARDIAN}", r"Killed|No entity")
        d = re.search(DEFEATED, ctx.log()) or s.wait_for(ctx.lines, DEFEATED, 120, ctx.seen)   # (it comes before the reply)
        key, n_off, n_pending, ms = d.group(1), int(d.group(2)), int(d.group(3)), int(d.group(4))
        spots = [(bool(g[0]), (int(g[1]), int(g[2]), int(g[3]))) for g in POS.findall(d.group(5))]
        now = [p for pend, p in spots if not pend]
        later = [p for pend, p in spots if pend]
        print(f"cleared {key}: {n_off} off, {n_pending} pending, {ms} ms; off {now}; pending {later}")
        check(n_off + n_pending >= 1, f"the {sid} has no spawner to turn off")
        check(len(now) == n_off and len(later) == n_pending, "the logged positions do not match the counts")
        check(ms < 1000, f"clearing took {ms} ms")
        for p in now:
            check(off(p), f"the spawner at {p} is not off right after the guardian's death")
        if not later:
            print("NOTE: every spawner was loaded already: the pending path (chunk load) is not exercised in this run")

        # the rest of the structure loads: the pending ones turn off
        load_area(lx, lz)
        if later:
            # the command can already read the block before the chunk's load event (which turns them off) has run
            end = time.monotonic() + 300
            while sum(int(g[0]) for g in re.findall(PENDING_DONE, ctx.log())) < n_pending and time.monotonic() < end:
                ctx.ticks(20)
            for p in later:
                ctx.until(f"execute if loaded {p[0]} {p[1]} {p[2]}", timeout=120)
                check(off(p), f"the pending spawner at {p} is not off once its chunk loaded")
            done = sum(int(g[0]) for g in re.findall(PENDING_DONE, ctx.log()))
            check(done == n_pending, f"the log reports {done} pending spawners turned off, {n_pending} expected")

        # idempotent: a second guardian of the same structure, with a spawner filled again by hand
        refill = (now + later)[0] if now + later else None
        if refill:
            x, y, z = refill
            ctx.run(f'data merge block {x} {y} {z} {{SpawnData:{{entity:{{id:"minecraft:zombie"}}}}}}', r"Modified block data|Nothing")

        def second_death(when):
            before = len(defeated_lines())
            ctx.run(f'summon minecraft:zombie {gx} {gy} {gz} {{Tags:["heraldia_guardian","heraldia_guardian.{sid}"]}}',
                    r"Summoned new|Unable")
            ctx.run(f"kill {GUARDIAN}", r"Killed|No entity")
            ctx.ticks(20)
            check(len(defeated_lines()) == before, f"a second guardian's death clears the structure again ({when})")
            if refill:
                x, y, z = refill
                check(ctx.test(f'execute if data block {x} {y} {z} SpawnData.entity{{id:"minecraft:zombie"}}'),
                      f"a second death touches a spawner filled again by hand ({when})")

        second_death("same run")
        srv.stop()
        srv = Server(a.work, launcher)
        ctx = srv.ctx
        forceload(ctx, gx - 8, gz - 8, gx + 8, gz + 8)
        ctx.until(f"execute if loaded {gx} {gy} {gz}", timeout=120)
        second_death("after a restart")

        bad = [b for b in ("Registry loading errors", "Failed to load datapacks") if b in ctx.log()]
        bad += [l.strip() for l in ctx.log().splitlines() if "Exception" in l and "heraldia" in l.lower()]
        check(not bad, f"errors in the log: {bad}")
    finally:
        srv.stop()
    print(f"cleared_spawners: {ok} checks passed, {len(fails)} failed")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
