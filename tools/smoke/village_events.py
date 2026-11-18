"""Village events (market day, wedding, funeral, festival) on a real 26.3 dedicated server.

Usage: python3 tools/smoke/village_events.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-eventos"
With Carpet (a simulated player) and a really generated village (the closest to 0,0, as village_life.py: /place structure
does not save the start, and the events find the square through it). The square, one block under its paving to seven
above, is read from the saved region files (after save-all flush) before anything happens; after every event it is read
again and must be identical, block for block, and no entity with the event tag may be left anywhere. (Not with a clone
into the sky and `execute if blocks`: the copy's sand and gravel fall, onto the square itself.)
First start (eventos.frecuencia 0: only the command starts them):
  - a player's block (oak planks) stands where the wedding's arch would go in one bay: the wedding goes elsewhere and the
    planks are still there at the end (they are in the saved reference);
  - each kind in turn: /heraldia event start <kind> brings at most 25 entities, places its props (the square differs from
    the reference), takes part (a poppy to the bride and a dandelion to the widow are taken and thanked, the band takes a
    request, a guest and a shopper answer), runs its beats (sprinted: the ceremony's three lines and the "yes", the
    eulogy), and /heraldia event stop removes exactly its figures and blocks;
  - during the market, the top prop is swapped for a player's block: at the end it is left alone (not ours any more);
  - the festival runs to its natural end (sprinted 5 min): it ends by itself and leaves nothing.
Second start: an event is running when the server stops: it is cleaned up on the way down; after the restart there is
nothing to clean, the square is identical and no event entity loads. Then one is running when the server is killed
(after save-all flush, like a crash): at the third start its figures are removed as they load and its blocks are taken
down from the saved record. Fourth start (eventos.frecuencia 100, espera 5 min): with the player in the village, more than
24 blocks from the square, the draw starts one by itself; only one per village; with the light profile and
/heraldia reload it ends and none starts again.
Each round prints the entity count around the square before, during and after (the baseline it returns to).
"""
import argparse, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomes import fetch
from trophies import CARPET
from village_life import Server, plaza
from village_terrain import read_blocks

PLAYER = "hrd_fiesta"
RADIUS = 80
CAP = 25
START = re.compile(r"Heraldia: events: event (\d+) starts: (\w+) in .*?, bays \[([\d, ]+)\], (\d+) figures and (\d+) blocks "
                   r"\(the top one (\S+) at (-?\d+) (-?\d+) (-?\d+)\)")
END = re.compile(r"Heraldia: events: event (\d+) ends: (\w+) in .*?, (\w+) \((\d+) entities removed, (\d+) blocks taken down, "
                 r"(\d+) left alone, (\d+) waiting for their chunk")
NOT = r"Heraldia: events: \w+ not started: (\w+)"


def write_config(work, extra):
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    for k, v in extra.items():
        if isinstance(v, dict):
            cfg.setdefault(k, {}).update(v)
        else:
            cfg[k] = v
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def wait_log(srv, pattern, timeout=s.COMMAND_TIMEOUT_S, since=0):
    """The first log line from `since` (an index in srv.seen) matching `pattern`, already read or still to come."""
    rx = re.compile(pattern)
    for line in srv.seen[since:]:
        m = rx.search(line)
        if m:
            return m
    return s.wait_for(srv.ctx.lines, pattern, timeout, srv.seen)


def as_player(srv, cmd):
    s.send(srv.proc, f"execute as {PLAYER} at @s run {cmd}")


def sprint(srv, ticks):
    """`ticks` game ticks as fast as the server can, waiting until they are done."""
    mark = len(srv.seen)
    srv.run(f"tick sprint {ticks}", r"The game is sprinting|Sprint completed|[Ss]print")
    wait_log(srv, r"Sprint completed", timeout=600, since=mark)


def to_square(b, dx, dz, n=23):
    """events/Layout.toSquare: bay coordinates to square coordinates (from the square's box corner, not the template's)."""
    x, z = n // 2 + dx, dz
    return [(x, z), (n - 1 - z, x), (n - 1 - x, n - 1 - z), (z, n - 1 - x)][b % 4]


class Square:
    """Where the square is: its corners, the floor, its saved reference and helpers to count around it."""

    def __init__(self, to_world, y, world):
        self.world_dir = world
        xs, zs = [], []
        for p in ((0, 0), (22, 22)):
            w = to_world(p)
            xs.append(int(w[0] // 1))
            zs.append(int(w[1] // 1))
        self.x1, self.x2, self.z1, self.z2 = min(xs), max(xs), min(zs), max(zs)
        self.floor = int(y // 1) - 1
        self.y1, self.y2 = self.floor - 1, self.floor + 7
        c = to_world((11, 11))
        self.cx, self.cz = int(c[0] // 1), int(c[1] // 1)
        self.to_world = to_world

    def box(self):
        return f"{self.x1} {self.y1} {self.z1} {self.x2} {self.y2} {self.z2}"

    def read(self, srv):
        """{(x, y, z): block} of the square's box as saved now (save-all flush, then the region files)."""
        srv.run("save-all flush", r"Saved the game|saved")
        blocks = read_blocks(self.world_dir, self.x1, self.z1, self.x2, self.z2)
        return {k: v for k, v in blocks.items() if self.x1 <= k[0] <= self.x2 and self.y1 <= k[1] <= self.y2
                and self.z1 <= k[2] <= self.z2}

    def snapshot(self, srv):
        self.reference = self.read(srv)
        print(f"square saved: {len(self.reference)} blocks in its box")

    def identical(self, srv, quiet=False):
        now = self.read(srv)
        diff = sorted(k for k in set(now) | set(self.reference) if now.get(k) != self.reference.get(k))
        for k in ([] if quiet else diff[:6]):
            print(f"  differs at {k}: was {self.reference.get(k, 'air')}, now {now.get(k, 'air')}")
        return not diff

    def around(self, srv):
        return srv.ctx.count(f"@e[x={self.cx},y={self.floor},z={self.cz},distance=..64]")

    def tagged(self, srv):
        return srv.ctx.count("@e[tag=heraldia_evento]")

    def world(self, lx, ly, lz):
        w = self.to_world((lx, lz))
        return int(w[0] // 1), self.floor + ly, int(w[1] // 1)


def start_event(srv, kind, fails):
    """/heraldia event start <kind> as the player; returns the START match or None."""
    mark = len(srv.seen)
    as_player(srv, f"heraldia event start {kind}")
    m = wait_log(srv, START.pattern + "|" + NOT, since=mark)
    if not m.group(0).startswith("Heraldia: events: event"):
        fails.append(f"{kind}: did not start ({m.group(0)})")
        return None
    print(f"{kind}: event {m.group(1)}, bays [{m.group(3)}], {m.group(4)} figures, {m.group(5)} blocks")
    return m


def stop_event(srv, fails, kind, start):
    mark = len(srv.seen)
    as_player(srv, "heraldia event stop")
    e = wait_log(srv, END.pattern, since=mark)
    print(f"{kind}: ends ({e.group(3)}): {e.group(4)} entities removed, {e.group(5)} blocks taken down, {e.group(6)} left alone, "
          f"{e.group(7)} waiting")
    if int(e.group(4)) != int(start.group(4)):
        fails.append(f"{kind}: {e.group(4)} entities removed, {start.group(4)} spawned")
    if int(e.group(7)) != 0:
        fails.append(f"{kind}: {e.group(7)} blocks left waiting with the square loaded")
    return e


def check_clean(srv, sq, fails, what, baseline):
    tagged, around = sq.tagged(srv), sq.around(srv)
    print(f"{what}: {tagged} event entities in the world, {around} entities around the square (baseline {baseline})")
    if tagged:
        fails.append(f"{what}: {tagged} event entities left")
    # (the total around is printed, not checked: the village's own people, cats and the night's mobs come and go, more so
    #  with the sprinted ticks; what the event brought is the tagged count, and the END line's removed == spawned)
    if not sq.identical(srv):
        fails.append(f"{what}: the square is not identical to its saved reference")


def during(srv, sq, fails, kind, start, baseline):
    figures = int(start.group(4))
    tagged, around = sq.tagged(srv), sq.around(srv)
    print(f"{kind}: during: {tagged} event entities, {around} around the square")
    if not 1 <= tagged <= CAP or tagged != figures:
        fails.append(f"{kind}: {tagged} event entities (figures {figures}, cap {CAP})")
    if int(start.group(5)) and sq.identical(srv, quiet=True):
        fails.append(f"{kind}: {start.group(5)} blocks placed but the square looks unchanged")


def gift(srv, fails, role, item, kind):
    srv.run(f"item replace entity {PLAYER} weapon.mainhand with minecraft:{item}", r"Replaced|replaced")
    mark = len(srv.seen)
    as_player(srv, f"heraldia event with @e[tag=heraldia_evento.{role},limit=1]")
    wait_log(srv, rf"Heraldia: events: {PLAYER} gives {item} at the {kind}", since=mark)
    left = srv.run(f"clear {PLAYER} minecraft:{item} 0", r"Found (\d+) matching|No items")
    if "No items" not in left.group(0):
        fails.append(f"{kind}: the {item} was not taken")
    wait_log(srv, rf"says event\.{kind}\.thanks\.\d to {PLAYER}", since=mark)


def round_one(srv, sq, fails, baseline, planks):
    for kind in ("wedding", "market", "funeral", "festival"):
        m = start_event(srv, kind, fails)
        if m is None:
            continue
        srv.ctx.ticks(25)
        during(srv, sq, fails, kind, m, baseline)
        mark = len(srv.seen)
        if kind == "wedding":
            lp = (planks[0] - sq.x1, planks[2] - sq.z1)
            blocked = [b for b in range(4) if lp in (to_square(b, -2, 2), to_square(b, 2, 2))]
            used = [int(b) for b in m.group(3).split(",")]
            print(f"wedding: the player's planks are in bay {blocked}, the wedding uses {used}")
            if not blocked or set(blocked) & set(used):
                fails.append(f"wedding: the player's planks (bay {blocked}) and the wedding (bays {used})")
            gift(srv, fails, "bride", "poppy", kind)
            sprint(srv, 95 * 20)
            for i in (1, 2, 3):
                wait_log(srv, rf"says event\.wedding\.ceremony\.{i} to {PLAYER}", since=mark)
            wait_log(srv, r"the couple say yes", since=mark)
        elif kind == "funeral":
            gift(srv, fails, "widow", "dandelion", kind)
            sprint(srv, 105 * 20)
            for i in (1, 2, 3):
                wait_log(srv, rf"says event\.funeral\.eulogy\.{i} to {PLAYER}", since=mark)
        elif kind == "market":
            as_player(srv, "heraldia event with @e[tag=heraldia_evento.shopper,limit=1]")
            wait_log(srv, rf"says event\.market\.guest\.\d to {PLAYER}", since=mark)
            # a player swaps the top prop for their own block: it must stay
            top = (m.group(7), m.group(8), m.group(9))
            srv.run(f"setblock {' '.join(top)} minecraft:oak_planks", r"Changed the block|Could not set")
        if kind == "festival":
            as_player(srv, "heraldia event with @e[tag=heraldia_evento.musician,limit=1]")
            wait_log(srv, rf"{PLAYER} asks the band in .* for a song", since=mark)
            as_player(srv, "heraldia event with @e[tag=heraldia_evento.dancer,limit=1]")
            wait_log(srv, rf"says event\.festival\.guest\.\d to {PLAYER}", since=mark)
            sprint(srv, 5 * 60 * 20 + 40)
            e = wait_log(srv, END.pattern, since=mark)
            print(f"festival: ends by itself ({e.group(3)}): {e.group(4)} entities removed, {e.group(5)} blocks taken down")
            if e.group(3) != "termina" or int(e.group(4)) != int(m.group(4)):
                fails.append(f"festival: natural end {e.group(0)}")
        else:
            e = stop_event(srv, fails, kind, m)
            if kind == "market":
                # the swapped awning stays, and so do the stall's posts under it (something rests on them now): 1 to 3
                if not 1 <= int(e.group(6)) <= 3:
                    fails.append(f"market: {e.group(6)} blocks left alone (the swapped awning and the posts under it)")
                top = (m.group(7), m.group(8), m.group(9))
                if not srv.ctx.block(" ".join(top), "minecraft:oak_planks"):
                    fails.append("market: the player's block on the prop's cell was removed")
                # the test itself clears that column (what the player made theirs) before comparing with the reference
                x, y0, z = int(top[0]), int(top[1]), int(top[2])
                for y in range(y0, sq.floor, -1):
                    srv.run(f"setblock {x} {y} {z} minecraft:air", r"Changed the block|Could not set")
        srv.ctx.ticks(10)
        check_clean(srv, sq, fails, f"after the {kind}", baseline)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-eventos"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    write_config(a.work, {"eventos": {"frecuencia": 0, "max_activos": 2}})
    fails = []
    srv = Server(a.work, launcher)
    sq = None
    try:
        found = plaza(srv, fails)
        if not found:
            raise SystemExit("no village square")
        style, to_world, y, _ = found
        sq = Square(to_world, y, os.path.join(a.work, "world"))
        print(f"square of {style}: {sq.box()}, floor {sq.floor}")
        srv.run("gamerule advance_time false", r"Gamerule|gamerule|set to")
        srv.run("time set 4000", r"Set|set|Clock")
        srv.run("weather clear 100000", r"weather|Weather")
        srv.run(f"forceload add {sq.x1 - 16} {sq.z1 - 16} {sq.x2 + 16} {sq.z2 + 16}", r"Marked|Added|force|already")
        # a player's planks where the wedding's arch goes in bay 0 (the north edge, dz = 2, dx = -2: local 9, 2)
        planks = sq.world(9, 1, 2)
        srv.run(f"setblock {planks[0]} {planks[1]} {planks[2]} minecraft:oak_planks", r"Changed the block|Could not set")
        bot = sq.world(11, 1, 2)
        srv.run(f"player {PLAYER} spawn at {bot[0]} {bot[1]} {bot[2]}", r"joined the game")
        if not srv.until(f"execute if entity @a[name={PLAYER}]"):
            raise SystemExit(f"the simulated player {PLAYER} does not appear (Carpet)")
        srv.run(f"gamemode survival {PLAYER}", r"game mode|Set")
        srv.run(f"effect give {PLAYER} minecraft:resistance infinite 255 true", r"Applied|Unable")
        srv.ctx.ticks(40)
        sq.snapshot(srv)
        baseline = sq.around(srv)
        print(f"baseline: {baseline} entities around the square, {sq.tagged(srv)} event entities")
        round_one(srv, sq, fails, baseline, planks)
        if not srv.ctx.block(f"{planks[0]} {planks[1]} {planks[2]}", "minecraft:oak_planks"):
            fails.append("the player's planks are gone")
        # an event running when the server stops
        m = start_event(srv, "market", fails)
        srv.ctx.ticks(20)
        srv.run(f"player {PLAYER} kill", r"left the game")
        srv.stop()
        if m:
            with open(os.path.join(a.work, "logs", "latest.log"), encoding="utf-8", errors="replace") as f:
                stopping = [END.search(l) for l in f if END.search(l)]
            stopping = [e for e in stopping if e.group(1) == m.group(1)]
            print(f"stopping with an event running: {stopping[-1].group(0) if stopping else 'no end line'}")
            if not stopping or stopping[-1].group(3) != "limpieza":
                fails.append("the running market was not cleaned up when the server stopped")
        srv = Server(a.work, launcher)
        srv.ctx.ticks(60)
        if any("blocks of an earlier run" in l for l in srv.seen):
            fails.append("after a clean stop there were blocks to take down at startup")
        check_clean(srv, sq, fails, "after a clean restart", baseline)
        # an event running when the server is killed (a crash, after the last autosave)
        srv.run(f"player {PLAYER} spawn at {bot[0]} {bot[1]} {bot[2]}", r"joined the game")
        srv.until(f"execute if entity @a[name={PLAYER}]")
        m = start_event(srv, "funeral", fails)
        srv.ctx.ticks(20)
        srv.run("save-all flush", r"Saved the game|saved")
        srv.proc.kill()
        srv.proc.wait(timeout=60)
        srv = Server(a.work, launcher)
        srv.ctx.ticks(100)
        log = srv.ctx.log()
        removed = len(re.findall(r"removed an entity of an event that is no longer running", log))
        taken = sum(int(x) for x in re.findall(r"chunk -?\d+ -?\d+: (\d+) leftover blocks taken down", log))
        print(f"after the crash: {removed} leftover figures removed as they loaded, {taken} leftover blocks taken down")
        if m and (removed != int(m.group(4)) or taken != int(m.group(5))):
            fails.append(f"after the crash: removed {removed} of {m.group(4)} figures and {taken} of {m.group(5)} blocks")
        check_clean(srv, sq, fails, "after a crash and a restart", baseline)
        srv.stop()
        # the draw, and the light profile
        write_config(a.work, {"eventos": {"frecuencia": 100, "espera_minutos": 5, "max_activos": 2}})
        srv = Server(a.work, launcher)
        away = sq.world(11, 1, -20)
        srv.run(f"player {PLAYER} spawn at {away[0]} {away[1] + 2} {away[2]}", r"joined the game")
        srv.until(f"execute if entity @a[name={PLAYER}]")
        sprint(srv, 5 * 60 * 20)            # the village's rest after the market cleaned up at the first stop
        mark = len(srv.seen)
        sprint(srv, 30 * 20 + 20)
        d = wait_log(srv, START.pattern, timeout=120, since=mark)
        print(f"draw: {d.group(2)} started by itself, {d.group(4)} figures")
        sprint(srv, 60 * 20)
        if len([l for l in srv.seen[mark:] if START.search(l)]) != 1:
            fails.append("more than one event started in the same village")
        write_config(a.work, {"perfil": "ligero", "eventos": {"frecuencia": 100, "espera_minutos": 5}})
        mark = len(srv.seen)
        srv.run("heraldia reload", r"(?:Configuration reloaded from|Configuración recargada de) heraldia\.json|No option|No ha cambiado")
        sprint(srv, 40)
        e = wait_log(srv, END.pattern, since=mark)
        if e.group(3) != "limpieza":
            fails.append(f"light profile: the running event did not end ({e.group(0)})")
        sprint(srv, 30 * 20 * 2)
        if any(START.search(l) for l in srv.seen[mark:]):
            fails.append("light profile: an event started")
        check_clean(srv, sq, fails, "with the light profile", baseline)
        srv.run(f"player {PLAYER} kill", r"left the game")
    finally:
        srv.stop()
    if fails:
        print("FALLOS:")
        for f in fails:
            print(" -", f)
        return 1
    print("OK: four events, taking part, nothing left after stop, natural end, restart, crash, draw and light profile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
