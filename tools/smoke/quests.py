"""Board quests and per-village reputation on a real 26.3 dedicated server (T38).

Usage: python3 tools/smoke/quests.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke-encargos"
With Carpet (simulated player) and a really generated village (the closest to 0,0, like village_life.py: the board is
recognized by the structure and the constable, and /place structure does not save the start in the chunk). Deterministic: the test
seed, the same village and the same period always give the same board (the first a fetch quest; the second a
guardian quest, because there are unique structures within 4,000 blocks).
First start:
  - the player touches the board's lectern: the server records it ("look at the board") and shows the board of 2 to 4 quests;
  - /heraldia quest accept 1 (fetch) and 2 (guardian); fetch without the items is not handed in; with them, it is: it removes the
    items, pays the emeralds and raises reputation;
  - guardian: a mob with the tags of that unique structure's guardian, next to the quest site, killed with /damage by
    the player, completes the quest; on handing it in, its emeralds and the reputation reach "conocido";
  - a plaza villager with a fixed trade of 10 emeralds: with no reputation the price does not change; with "conocido", it drops
    to 9 (10 %);
  - hitting that villager lowers the reputation; another is accepted and abandoned; /heraldia status counts the quests.
  - reputation visible in the village (reputacion.aldea_visible): before "conocido" a block not placed by the mod is put on
    one corner of the fountain's rim; on reaching "conocido" the other three corners get flower pots and that block is left
    as it was (never destroy a player's block).
  - villager conversations (P9a), with the test villager tagged as a Heraldia one (dialogos.viajeros_porcentaje = 100:
    every villager is a wayfarer): the simulated player's click opens the trades (a Carpet bot, like a trading
    automation's fake player, does not send the network packet the conversation listens to); /heraldia talk with
    opens a conversation as a real click would; "keep talking" answers; "any news?" with reputation "conocido" gives the
    hint (a real structure, direction and distance, no coordinates in the chat line); "trade" opens the trades; a
    second conversation while it rests says it is busy and does not tell the hint again.
Second start (same world): the board is the same, the player keeps what was handed in (cannot accept 1 again),
their reputation and the reduced price; the wayfarer remembers it already told its hint (saved in the villager) and,
with dialogos.activado set to false and /heraldia reload, there is no conversation; with quests.switched_on and
reputacion.activado set to false and /heraldia reload, the quests say they are disabled and the price goes back to 10.
The flower pots are still there after restarting; with reputation disabled the mod takes down exactly the three pots it put
up and the other block stays.
Then the other looks (tiers_lap), in four more starts; the record (overworld attachment heraldia:reputacion_visible) and
the test player's data are edited with the server stopped, and what each look put up is read back from the record:
  - a world saved before this feature (the record removed): nothing changes on starting; when the player with
    reputation "conocido" joins, the village gets its 3 pots. The villages around are located in the same start;
  - hero (250, for a player who never joins) on the first of them with a watchtower (the one closest to 0,0 has none):
    the 8 pots, the square and board banners, the carpet, the gates' lanterns and banners and the towers' banners;
  - in one start, the test player holds the reputation and kills villagers inside the village (-40 each): friend (170)
    removes exactly the hero-only blocks, known (50) exactly the banners, shunned (-30, after one tower window is changed
    by hand; on the way, 10 is neutral and the pots go) puts shutters outside every unchanged window and not outside the
    changed one, and the windows stay the same blocks;
  - neutral (5, a village that recovers): exactly the shutters go, the changed window is still the player's and an
    unchanged one is exactly as it was before the shutters.
The block that was not the mod's on the fountain stays through all of it.
"""
import argparse, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomes import fetch
from trophies import CARPET
from village_life import Server, plaza, RADIUS, BOT, SPOT, ATTEMPTS, RETRY_S

PLAYER = "Testigo"
PRICE = 10
BOARD = re.compile(r"Heraldia: encargos: tablón de (.+?) \((-?\d+), (-?\d+)\), periodo (\d+): (.*)")
QUEST = re.compile(r"(\d)=(\w+):(\S*?):(\d+)@(-?\d+),(-?\d+)")
VILLAGER = ('summon minecraft:villager {x} {y} {z} {{NoAI:1b,PersistenceRequired:1b,Invulnerable:0b,Tags:["heraldia_prueba"],'
            'VillagerData:{{profession:"minecraft:librarian",level:2,type:"minecraft:plains"}},Xp:20,'
            'Offers:{{Recipes:[{{buy:{{id:"minecraft:emerald",count:%d}},sell:{{id:"minecraft:book",count:1}},maxUses:99,'
            'uses:0,xp:1,priceMultiplier:0.0f,specialPrice:0,demand:0}}]}}}}' % PRICE)


def write_config(work, extra=None):
    cfg = json.loads(json.dumps(s.TEST_CONFIG))
    for k, v in (extra or {}).items():
        cfg.setdefault(k, {}).update(v)
    with open(os.path.join(work, "config", "heraldia.json"), "w") as f:
        json.dump(cfg, f)


def as_player(srv, cmd, ok, at=True):
    """The command run by the simulated player (reply in the console: "execute as" keeps the source)."""
    return srv.run(f"execute as {PLAYER} {'at @s ' if at else ''}run {cmd}", ok)


def board(srv, fails, action):
    """Does `action` (which asks for the board) and returns (name, quests) from the board's log line."""
    m = action()
    if m is None or not m.group(0).startswith("Heraldia: encargos: tablón"):
        m = s.wait_for(srv.ctx.lines, BOARD.pattern, s.COMMAND_TIMEOUT_S, srv.seen)
    g = BOARD.search(m.group(0))
    quests = [(int(a), t, o, int(c), int(x), int(z)) for a, t, o, c, x, z in QUEST.findall(g.group(5))]
    print(f"board of {g.group(1)} ({g.group(2)}, {g.group(3)}), period {g.group(4)}: {quests}")
    if not 2 <= len(quests) <= 4:
        fails.append(f"the board has {len(quests)} quests (must be 2 to 4)")
    return g.group(1), g.group(4), quests


def emeralds(srv):
    m = srv.run(f"clear {PLAYER} minecraft:emerald 0", r"Found (\d+) matching|No items")
    return int(m.group(1) or 0)


def look_and_use(srv, pos, start, y):
    srv.run(f"tp {PLAYER} {start[0]} {y} {start[1]}", r"Teleported")
    s.send(srv.proc, f"player {PLAYER} look at {pos[0]} {pos[1]} {pos[2]}")
    srv.ctx.ticks(2)
    s.send(srv.proc, f"player {PLAYER} use once")   # no reply in the console


def price(srv, spot, y, floor_bottom):
    """Summons the fixed-trade villager and returns its specialPrice with its trades open (0 without a discount)."""
    srv.run("kill @e[tag=heraldia_prueba]", r"Killed|No entity was found")
    for _ in range(ATTEMPTS):
        m = srv.run(VILLAGER.format(x=spot[0], y=y, z=spot[1]), r"Summoned")
        if "Summoned" in m.group(0):
            break
        time.sleep(RETRY_S)
    return existing_price(srv, spot, y, floor_bottom)


def clear_spot(srv, spot, y):
    """The plaza villagers (with AI) walk up to the player (SetLookAndInteract); if `use once` hits one, it trades and
    follows the player (LookAndFollowTradingPlayerSink), every retry hits it again and the test villager never opens its
    trades (its specialPrice stays 0, which the NBT omits). The ones near the spot are removed and the rest cannot walk (slowness 255)."""
    for kind in ("minecraft:villager", "minecraft:wandering_trader"):
        srv.run(f"execute positioned {spot[0]} {y} {spot[1]} run kill "
                f"@e[type={kind},tag=!heraldia_prueba,tag=!heraldia_alguacil,distance=..6]", r"Killed|No entity was found")
    # (not `execute as ... run data merge`: with no villager left it prints nothing and the console wait times out)
    srv.run(f"execute positioned {spot[0]} {y} {spot[1]} run effect give @e[type=minecraft:villager,tag=!heraldia_prueba,"
            f"tag=!heraldia_alguacil,distance=..48] minecraft:slowness infinite 255 true",
            r"Applied effect|No entity was found|Unable to apply")


def open_trades(srv, spot, y, floor_bottom):
    """The player opens the test villager's trades and returns the specialPrice it gets (0 if it never gets one: the
    field is then absent). Before each use, any open trade is closed and the plaza villagers next to the spot are removed."""
    price = None
    for _ in range(10):
        close_out(srv)   # a trade left open (also with another villager) is closed first
        clear_spot(srv, spot, y)
        look_and_use(srv, (spot[0], y + 1.2, spot[1]), floor_bottom, y)
        srv.ctx.ticks(4)
        price = read_price(srv)
        if price:
            return price
    return price


def read_price(srv):
    """specialPrice of the test trade: MerchantOffer.CODEC omits it when it is 0 (optionalFieldOf with default 0)."""
    m = srv.run("data get entity @e[tag=heraldia_prueba,limit=1] Offers.Recipes[0].specialPrice",
                r"has the following entity data: (-?\d+)|Found no elements|No entity")
    return None if m.group(0).startswith("No entity") else int(m.group(1) or 0)


def existing_price(srv, spot, y, floor_bottom):
    """specialPrice of the test villager already in the plaza, with its trades open (0 without a discount; None: it is gone)."""
    return open_trades(srv, spot, y, floor_bottom)


def close_out(srv):
    """Closes the trades (vanilla then removes the discount): the player goes far away for a moment."""
    srv.run(f"execute as {PLAYER} at @s run tp @s ~ ~ ~100", r"Teleported")
    srv.ctx.ticks(4)


def lectern_of(srv, sheriff_pos):
    bx, by, bz = int(sheriff_pos[0] // 1), int(sheriff_pos[1] // 1), int(sheriff_pos[2] // 1)
    for ex, ez in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if srv.test(f"execute if block {bx + ex} {by} {bz + ez} minecraft:lectern"):
            return (bx + ex, by, bz + ez), (bx + 3 * ex, bz + 3 * ez)   # the lectern and the spot in front (far from the constable)
    return None, None


def state(srv):
    """The quests handed in by everyone according to /heraldia status (goes through its pages)."""
    pat = re.compile(r"(?:handed in by everyone|entregados entre todos): (\d+)")
    for page in range(1, 6):
        m = as_player(srv, f"heraldia status {page}", r"server status \(page (\d+) of (\d+)\)|estado del servidor \(página (\d+) de (\d+)\)",
                 at=False)
        for line in s.drain(srv.ctx):
            if pat.search(line):
                return pat.search(line).group(1)
        if (m.group(1) or m.group(3)) == (m.group(2) or m.group(4)):
            return None
    return None


TALK_STAT = "heraldia_trato"     # minecraft.custom:minecraft.talked_to_villager: rises each time the trades are asked for
TALK = rf"Heraldia: diálogos: {PLAYER} habla con un aldeano de (.+?) \((\w+), (\w*), (\w+), (\w+), (\w+)\)"
BUSY = rf"Heraldia: diálogos: {PLAYER} habla con un aldeano de .*: está ocupado"
HINT = (rf"Heraldia: diálogos: un viajero de .* le cuenta a {PLAYER} dónde está (\S+) \((-?\d+), (-?\d+)\): (\w+) a unos "
        r"(\d+) bloques")
TOLD = rf"Heraldia: diálogos: un viajero de .* ya contó su pista \({PLAYER} pregunta\)"
DIALOGUE_CONFIG = {"dialogos": {"viajeros_porcentaje": 100, "espera_segundos": 600}}   # every villager a wayfarer; long rest


def maybe(srv, pattern, timeout):
    """The log line, or None if it does not show within `timeout` seconds."""
    try:
        return s.wait_for(srv.ctx.lines, pattern, timeout, srv.seen)
    except SystemExit:
        return None


def talk_score(srv):
    m = srv.run(f"scoreboard players get {PLAYER} {TALK_STAT}", r"has (\d+) \[|Can't get value|has no score")
    return int(m.group(1)) if m.group(1) else 0


def click_villager(srv, spot, y, floor_bottom):
    """The simulated player right-clicks the test villager (retrying if a plaza villager gets in the way): True if its
    trades opened (the talked_to_villager statistic rose)."""
    before = talk_score(srv)
    for _ in range(5):
        close_out(srv)
        clear_spot(srv, spot, y)
        look_and_use(srv, (spot[0], y + 1.2, spot[1]), floor_bottom, y)
        srv.ctx.ticks(4)
        if talk_score(srv) > before:
            return True
    return False


WITH = "heraldia talk with @e[tag=heraldia_prueba,limit=1]"


def conversation(srv, fails, spot, y, floor_bottom):
    """P9a in the plaza, with the reputation already at "conocido" (see the docstring)."""
    srv.run(f"scoreboard objectives add {TALK_STAT} minecraft.custom:minecraft.talked_to_villager", r"Created new objective|already exists")
    srv.run(f"scoreboard players set {PLAYER} {TALK_STAT} 0", r"Set \[")
    srv.run("tag @e[tag=heraldia_prueba,limit=1] add heraldia", r"Added tag|Nothing changed")
    # a Carpet bot's click does not go through the network packet (nor would a trading automation's fake player): it trades
    if not click_villager(srv, spot, y, floor_bottom):
        fails.append("conversation: a simulated player's click no longer opens the trades")
    if maybe(srv, TALK, 2) is not None:
        fails.append("conversation: a simulated player's click opened a conversation")
    close_out(srv)
    srv.run(f"tp {PLAYER} {floor_bottom[0]} {y} {floor_bottom[1]}", r"Teleported")
    m = as_player(srv, WITH, TALK)
    print(f"conversation in {m.group(1)}: profession {m.group(2)}, family {m.group(3)}, {m.group(4)}, {m.group(5)}, {m.group(6)}")
    if m.group(2) != "librarian" or m.group(6) != "conocido":
        fails.append(f"conversation: context {m.groups()[1:]} (must be librarian, ..., conocido)")
    as_player(srv, "heraldia talk more", r"Keep talking|Seguir hablando|Goodbye|Adiós")
    as_player(srv, "heraldia talk rumor", r"Goodbye|Adiós")
    m = maybe(srv, HINT, 60)
    if m is None:
        fails.append("conversation: the wayfarer (100 %) with reputation 'conocido' does not tell its hint")
    else:
        place, px, pz, bearing, dist = m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5))
        print(f"hint: {place} at {px}, {pz} ({bearing}, about {dist} blocks)")
        if dist % 100 or dist < 100:
            fails.append(f"hint: distance {dist} (must be rounded to 100)")
        chat = [l for l in srv.seen[-60:] if ("blocks" in l or "bloques" in l) and "Heraldia: diálogos" not in l]
        if not chat:
            fails.append("hint: its line does not reach the chat")
        elif any(px in l and pz in l for l in chat):
            fails.append(f"hint: the chat line shows the coordinates: {chat[-1].strip()}")
    before = talk_score(srv)
    as_player(srv, "heraldia talk trade", rf"Heraldia: diálogos: {PLAYER} comercia con")
    srv.ctx.ticks(4)
    if talk_score(srv) <= before:
        fails.append(f"conversation: [Trade] does not open the trades (statistic {talk_score(srv)})")
    close_out(srv)
    srv.run(f"tp {PLAYER} {floor_bottom[0]} {y} {floor_bottom[1]}", r"Teleported")
    as_player(srv, WITH, BUSY)
    as_player(srv, "heraldia talk rumor", r"Goodbye|Adiós")      # asked already in this conversation: busy, no new hint
    if maybe(srv, HINT, 2) is not None:
        fails.append("conversation: the hint was told twice")
    close_out(srv)
    srv.run("tag @e[tag=heraldia_prueba] remove heraldia", r"Removed tag|Nothing changed")


# Reputation visible in the village (welcome/Welcome): the four corners of the fountain's rim (streets.plaza: centre 11,
# rim at distance 3, y 1), where a "conocido" village puts flower pots at y 2. One corner gets a block the mod did not place.
RIM = [(8, 8), (14, 8), (8, 14), (14, 14)]
OTHER_BLOCK = "minecraft:mossy_cobblestone"
LOOK = r"Heraldia: village look: (-?\d+,-?\d+) {}: placed (\d+), removed (\d+), left alone (\d+)"


def rim_cells(found):
    """World (x, y, z) of the cells above the fountain's rim corners."""
    import math
    style, to_world, y, sheriff_pos = found
    out = []
    for p in RIM:
        wx, wz = to_world(p)
        out.append((math.floor(wx), math.floor(y) + 1, math.floor(wz)))
    return out


def look_line(srv, look, timeout):
    """The village look log line for that look (already seen, or within `timeout` s), or None."""
    pat = LOOK.format(look)
    for line in srv.seen[-400:]:
        m = re.search(pat, line)
        if m:
            return m
    return maybe(srv, pat, timeout)


def pots(srv, cells):
    """Which of the cells hold a potted plant (any of #minecraft:flower_pots but the empty pot)."""
    return [srv.test(f"execute if block {x} {y} {z} #minecraft:flower_pots") and
            not srv.test(f"execute if block {x} {y} {z} minecraft:flower_pot") for x, y, z in cells]


# --- the other looks, with the record edited between starts (tiers_lap) ---
ATTACHMENTS = os.path.join("world", "dimensions", "minecraft", "overworld", "data", "fabric", "attachments.dat")
NOBODY = "00000000-0000-4000-8000-0000000000be"   # a player who never joins: their reputation is never re-synchronized
FACING = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def unpack(l):
    """BlockPos.asLong -> (x, y, z): X 26 bits at 38, Z 26 bits at 12, Y 12 bits at 0."""
    l = int(l)
    return (l >> 38, ((l & 0xFFF) ^ 0x800) - 0x800, (((l >> 12) & 0x3FFFFFF) ^ 0x2000000) - 0x2000000)


def record(work, points=None, remove=False):
    """Reads (and with `points`, {village key: {player: reputation}}, sets; or with `remove` deletes) the village look record
    with the server stopped. Returns {village key: {(x, y, z): (block id, properties)}} of what is put up."""
    import nbtlib
    from nbtlib.tag import Compound, Int
    path = os.path.join(work, ATTACHMENTS)
    f = nbtlib.load(path)
    att = f["data"]["fabric:attachments"]
    if remove:
        att.pop("heraldia:reputacion_visible", None)
    elif points is not None:
        rv = att.setdefault("heraldia:reputacion_visible", Compound({"aldeas": Compound()}))
        for key, players in points.items():
            v = rv["aldeas"].setdefault(key, Compound())
            v["jugadores"] = Compound({u: Int(r) for u, r in players.items()})
    if remove or points is not None:
        f.save()
    out = {}
    for key, v in att.get("heraldia:reputacion_visible", {}).get("aldeas", {}).items():
        out[key] = {unpack(p["pos"]): saved_state(p["bloque"]) for p in v.get("colocados", [])}
    return out


def saved_state(b):
    """(id, properties) of a saved block state: 26.3 writes it as a string ("minecraft:brown_banner") when it has its
    default properties and as {id, properties} otherwise."""
    if isinstance(b, str):
        return str(b), {}
    return str(b["id"]), {k: str(x) for k, x in b.get("properties", {}).items()}


def kinds(placed):
    """How many of each kind of decoration: pot, banner, wall_banner, carpet, lantern, trapdoor."""
    n = {}
    for name, _ in placed.values():
        k = ("pot" if "potted_" in name else "wall_banner" if name.endswith("_wall_banner") else "banner" if name.endswith("_banner")
             else "carpet" if name.endswith("_carpet") else "lantern" if name.endswith("lantern") else
             "trapdoor" if name.endswith("_trapdoor") else name)
        n[k] = n.get(k, 0) + 1
    return n


def towers(placed):
    """The watchtowers, from their pair of wall banners (local x 2 and 4, y 3, z 1, two blocks apart and facing the same way;
    the gate's pair is four apart): for each, a function local (x, y, z) -> world (x, y, z)."""
    walls = [(p, props.get("facing", "north")) for p, (name, props) in placed.items()   # north: default, not saved
             if name.endswith("_wall_banner")]
    out = []
    for a, fa in walls:
        fx, fz = FACING[fa]
        ex, ez = -fz, fx                              # local east, from local north (the banners face north)
        b = (a[0] + 2 * ex, a[1], a[2] + 2 * ez)
        if (b, fa) in walls:
            out.append(lambda x, y, z, a=a, ex=ex, ez=ez, fx=fx, fz=fz:
                       (a[0] + (x - 2) * ex - (z - 1) * fx, a[1] + y - 3, a[2] + (x - 2) * ez - (z - 1) * fz))
    return out


WINDOWS = [((3, y, 6), (3, y, 7)) for y in (4, 8)] + [((1, y, 4), (0, y, 4)) for y in (4, 8)] + \
          [((5, y, 4), (6, y, 4)) for y in (4, 8)]     # (window, the shutter's cell outside it)
SCRATCH_Y = 300
WINDOW_BLOCKS = ["minecraft:iron_bars", "minecraft:glass_pane"] + [f"minecraft:{c}_stained_glass_pane" for c in (
    "white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray", "cyan", "purple", "blue",
    "brown", "green", "red", "black")]


def settle(srv, look, key=None, first=120, quiet=3):
    """Waits for the village (`key`, or any) to take that look while its chunks load: the passes logged (also those already
    read) until none comes for `quiet` s. Returns (placed, removed, left alone, passes) summed, or None if none came in `first` s."""
    pat = LOOK.format(look)
    if key:
        pat = pat.replace(r"(-?\d+,-?\d+)", "(" + re.escape(key) + ")")
    seen = [mm for mm in (re.search(pat, line) for line in srv.seen) if mm]
    srv.seen[:] = [line for line in srv.seen if not re.search(pat, line)]      # each pass is counted once
    m = None if seen else maybe(srv, pat, first)
    if not seen and m is None:
        return None
    total = [0, 0, 0, 0]
    for mm in seen + ([m] if m else []):
        for i in range(3):
            total[i] += int(mm.group(i + 2))
        total[3] += 1
    while (m := maybe(srv, pat, quiet)) is not None:
        srv.seen.remove(m.string) if m.string in srv.seen else None
        for i in range(3):
            total[i] += int(m.group(i + 2))
        total[3] += 1
    return tuple(total)


def start_at(work, launcher, x, z):
    srv = Server(work, launcher)
    srv.run(f"forceload add {x - RADIUS} {z - RADIUS} {x + RADIUS} {z + RADIUS}", r"Marked|Added|force|already|No chunks")
    return srv


def bot_reputation(work, values):
    """Sets the test player's own reputation with villages ({key: points}) in their saved data, with the server stopped."""
    import glob
    import nbtlib
    from nbtlib.tag import Compound, Int
    path = glob.glob(os.path.join(work, "world", "players", "data", "*.dat"))[0]
    f = nbtlib.load(path)
    q = f["fabric:attachments"]["heraldia:encargos"]
    rep = q.setdefault("reputacion", Compound())
    for k, v in values.items():
        rep[k] = Int(v)
    f.save()
    return os.path.basename(path)[:-len(".dat")]


def in_world(srv, blocks, gone=()):
    """The positions that do not hold their block (by id), and those of `gone` that are not air."""
    bad = [p for p, (name, _) in blocks.items() if not srv.test("execute if block {} {} {} {}".format(*p, name))]
    return bad + [p for p in gone if not srv.test("execute if block {} {} {} minecraft:air".format(*p))]


# Where to look for more villages (the one closest to 0,0 has no tower or gate with the test seed: street ends are mostly plain)
ORIGINS = [(0, 0), (3000, 0), (-3000, 0), (0, 3000), (0, -3000), (3000, 3000), (-3000, -3000)]
SQUARE_SPOTS = 19     # the square's 16 and the job board's 3: a village with more has a gate or a watchtower
KILL = ('summon minecraft:villager {} {} {} {{NoAI:1b,PersistenceRequired:1b,Tags:["heraldia_prueba_k"]}}',
        "damage @e[tag=heraldia_prueba_k,limit=1] 2000 minecraft:player_attack by " + PLAYER)


def kill_villagers(srv, at, n):
    """The test player kills `n` villagers inside the village (-40 reputation each); returns the last reputation logged."""
    rep = None
    for _ in range(n):
        srv.run(KILL[0].format(*at), r"Summoned")
        m = srv.run(KILL[1], rf"Heraldia: encargos: {PLAYER} mata a un aldeano de .*: reputación (-?\d+)")
        rep = int(m.group(1))
    return rep


def tiers_lap(work, launcher, found, fails):
    """The other looks (see the module docstring), in four more starts."""
    write_config(work, {})
    style, to_world, y, sheriff_pos = found
    cells = rim_cells(found)
    first_key = next(iter(record(work)))
    # 1) a world saved before this feature (no record at all): nothing changes until the player with reputation joins;
    #    in the same start, the villages around are located
    record(work, remove=True)
    srv = start_at(work, launcher, int(sheriff_pos[0]), int(sheriff_pos[2]))
    candidates = {}
    try:
        if settle(srv, r"\w+", first=5, quiet=1) is not None:
            fails.append("old world: a village changed with nobody's reputation recorded")
        if any(pots(srv, cells)):
            fails.append("old world: flower pots before anyone joined")
        bot = to_world(BOT)
        srv.run(f"player {PLAYER} spawn at {bot[0]} {y} {bot[1]}", r"joined the game")
        m = settle(srv, "conocida", first_key, first=60)
        if m is None or m[0] != 3:
            fails.append(f"old world: on joining, {m or 'nothing'} (must place the 3 pots)")
        if pots(srv, cells) != [False, True, True, True]:
            fails.append(f"old world: flower pots {pots(srv, cells)} after joining (must be [False, True, True, True])")
        if not srv.test("execute if block {} {} {} {}".format(*cells[0], OTHER_BLOCK)):
            fails.append("old world: the block that was not the mod's was touched")
        srv.run(f"player {PLAYER} kill", r"left the game")
        for ox, oz in ORIGINS:
            m = srv.run(f"execute positioned {ox} 100 {oz} run locate structure #heraldia:aldeas",
                        r"is at \[(-?\d+), ~?(-?\d+|~), (-?\d+)\]|Could not find")
            if m.group(1) and f"{int(m.group(1)) >> 4},{int(m.group(3)) >> 4}" != first_key:
                candidates.setdefault(f"{int(m.group(1)) >> 4},{int(m.group(3)) >> 4}", (int(m.group(1)), int(m.group(3))))
    finally:
        srv.stop()
    print(f"villages around: {candidates}")
    # 2) hero (written into the record for a player who never joins) on the first of them with a watchtower
    key = None
    for k, (vx, vz) in candidates.items():
        record(work, {k: {NOBODY: 250}})
        srv = start_at(work, launcher, vx, vz)
        try:
            m = settle(srv, "heroica", k, first=240)
        finally:
            srv.stop()
        hero = record(work).get(k, {})
        print(f"village {k}: {m}, {kinds(hero)}")
        if m and towers(hero):
            key = k
            break
        record(work, {k: {}})
    if key is None:
        fails.append(f"no village with a watchtower among {list(candidates)}")
        return
    k = kinds(hero)
    tw = towers(hero)
    print(f"hero: {k}, {len(tw)} towers")
    if k.get("pot") != 8 or k.get("banner") != 10 or k.get("carpet") != 1 or k.get("trapdoor"):
        fails.append(f"hero: {k} (must be 8 pots, 10 banners, 1 carpet and no trapdoor)")
    if k.get("wall_banner", 0) < 2 * len(tw):
        fails.append(f"hero: {k.get('wall_banner', 0)} wall banners for {len(tw)} towers (2 each, plus the gates')")
    hero_only = {p: b for p, b in hero.items() if b[0].endswith(("_carpet", "lantern")) or
                 ("potted_" in b[0] and p in hero_pots_middle(hero))}
    friend_set = {p: b for p, b in hero.items() if p not in hero_only}
    banners = {p: b for p, b in friend_set.items() if b[0].endswith("_banner")}
    known_set = {p: b for p, b in friend_set.items() if p not in banners}
    if kinds(known_set) != {"pot": 4}:
        fails.append(f"hero: {kinds(known_set)} would be left as known (must be the 4 corner pots)")
    tower = tw[0]
    changed_win, changed_out = tower(*WINDOWS[0][0]), tower(*WINDOWS[0][1])
    keep_win = tower(*WINDOWS[2][0])
    scratch = (keep_win[0], SCRATCH_Y, keep_win[2])
    want = {t(*out) for t in tw for _, out in WINDOWS} - {changed_out}
    carpet = next(p for p, b in hero.items() if b[0].endswith("_carpet"))
    # 3) friend, known and shunned in one start: the test player holds the reputation (170) and kills villagers inside the
    #    village, the way reputation really drops (-40 each)
    bot_uuid = bot_reputation(work, {key: 170})
    record(work, {key: {bot_uuid: 170}})
    vx, vz = candidates[key]
    srv = start_at(work, launcher, vx, vz)
    try:
        m = settle(srv, "amiga", key)
        if m is None or (m[0], m[1]) != (0, len(hero_only)):
            fails.append(f"friend: {m} (must place 0 and remove {len(hero_only)}: {kinds(hero_only)})")
        bad = in_world(srv, friend_set, hero_only)
        if bad:
            fails.append(f"friend: not as expected at {bad}")
        srv.run(f"player {PLAYER} spawn at {carpet[0]} {carpet[1]} {carpet[2]}", r"joined the game")
        srv.run(f"gamemode survival {PLAYER}", r"game mode")
        rep = kill_villagers(srv, carpet, 3)
        m = settle(srv, "conocida", key, first=30)
        print(f"known (reputation {rep}): {m}")
        if m is None or (m[0], m[1]) != (0, len(banners)):
            fails.append(f"known: {m} (must place 0 and remove the {len(banners)} banners)")
        bad = in_world(srv, known_set, banners)
        if bad:
            fails.append(f"known: not as expected at {bad}")
        window_id = next((w for w in WINDOW_BLOCKS if srv.test("execute if block {} {} {} {}".format(*keep_win, w))), None)
        srv.run("setblock {} {} {} minecraft:glass".format(*changed_win), r"Changed the block|Could not set")
        srv.run("clone {0} {1} {2} {0} {1} {2} {3} {4} {5} strict".format(*keep_win, *scratch), r"cloned|No blocks|Could not")
        rep = kill_villagers(srv, carpet, 1)      # 50 -> 10: neutral on the way down, the pots go
        m = settle(srv, "normal", key, first=30)
        print(f"neutral on the way (reputation {rep}): {m}")
        if m is None or (m[0], m[1]) != (0, len(known_set)) or in_world(srv, {}, known_set):
            fails.append(f"neutral on the way down: {m} (must place 0 and remove the {len(known_set)} pots)")
        rep = kill_villagers(srv, carpet, 1)      # 10 -> -30: shunned
        m = settle(srv, "recelosa", key, first=30)
        print(f"shunned (reputation {rep}): {m}, {len(want)} shutters expected")
        if m is None or (m[0], m[1]) != (len(want), 0):
            fails.append(f"shunned: {m} (must place {len(want)} shutters and remove nothing)")
        if not srv.test("execute if block {} {} {} minecraft:glass".format(*changed_win)):
            fails.append("shunned: the window changed by hand was touched")
        if not srv.test("execute if block {} {} {} minecraft:air".format(*changed_out)):
            fails.append("shunned: a shutter went up outside the window changed by hand")
        # the same block (a shutter's flat face makes iron bars or a pane next to it connect: vanilla shape, not a new block)
        if window_id is None or not srv.test("execute if block {} {} {} {}".format(*keep_win, window_id)):
            fails.append(f"shunned: an unchanged window is no longer {window_id}")
        srv.run(f"player {PLAYER} kill", r"left the game")
    finally:
        srv.stop()
    shunned = record(work)[key]
    got = {p for p, (name, _) in shunned.items() if name.endswith("_trapdoor")}
    if kinds(shunned) != {"trapdoor": len(want)} or got != want:
        fails.append(f"shunned: {kinds(shunned)} at {sorted(got)} (must be {len(want)} trapdoors at {sorted(want)})")
    if any(shunned[p][1].get("open") != "true" for p in got):
        fails.append("shunned: a shutter that is not an open trapdoor")
    # 4) neutral (a village that recovers its reputation): exactly the shutters go; the windows are as they were
    bot_reputation(work, {key: 5})
    record(work, {key: {bot_uuid: 5}})
    srv = start_at(work, launcher, vx, vz)
    try:
        m = settle(srv, "normal", key)
        if m is None or (m[0], m[1]) != (0, len(want)):
            fails.append(f"neutral: {m} (must place 0 and remove the {len(want)} shutters)")
        if not srv.test("execute if block {} {} {} minecraft:glass".format(*changed_win)):
            fails.append("neutral: the window changed by hand was touched")
        if not srv.test("execute if blocks {0} {1} {2} {0} {1} {2} {3} {4} {5} all".format(*keep_win, *scratch)):
            fails.append("neutral: an unchanged window is not exactly as it was before the shutters")
        if in_world(srv, {}, want):
            fails.append("neutral: shutters left")
    finally:
        srv.stop()
    if record(work).get(key):
        fails.append(f"neutral: {kinds(record(work)[key])} still recorded as put up (must be nothing)")
    print(f"looks on {key}: hero {len(hero)} blocks, friend {len(friend_set)}, known {len(known_set)}, shunned {len(shunned)}, "
          f"neutral 0; {len(tw)} towers")


def hero_pots_middle(hero):
    """The hero-only pots: on the middle of each side of the rim, so the four of them with the extreme coordinates are the
    corners' (known); the middle ones are those sharing x or z with the fountain's centre."""
    pots_ = [p for p, b in hero.items() if "potted_" in b[0]]
    cx = sorted(p[0] for p in pots_)[len(pots_) // 2]
    cz = sorted(p[2] for p in pots_)[len(pots_) // 2]
    return {p for p in pots_ if p[0] == cx or p[2] == cz}


def first_lap(srv, fails, found):
    style, to_world, y, sheriff_pos = found
    spot, floor_bottom = to_world(SPOT), to_world(BOT)
    srv.run(f"player {PLAYER} spawn at {floor_bottom[0]} {y} {floor_bottom[1]}", r"joined the game")
    if not srv.until(f"execute if entity @a[name={PLAYER}]"):
        raise SystemExit(f"simulated player {PLAYER} (Carpet) does not appear")
    srv.run(f"gamemode survival {PLAYER}", r"Set .* game mode|game mode")
    for effect in ("water_breathing", "resistance"):   # close_out leaves the player wherever it lands (sometimes in water)
        srv.run(f"effect give {PLAYER} minecraft:{effect} infinite 4 true", r"Applied effect|Unable to apply")
    srv.run(f"clear {PLAYER}", r"Removed|No items")
    lec, ahead = lectern_of(srv, sheriff_pos)
    if lec is None:
        fails.append("no lectern next to the constable")
        return None
    # 1) touch the board's lectern: the board appears in the chat (and is recorded in the log)
    look_and_use(srv, (lec[0] + 0.5, lec[1] + 0.6, lec[2] + 0.5), ahead, y)
    m = s.wait_for(srv.ctx.lines, rf"Heraldia: encargos: {PLAYER} mira el tablón de (.+)", s.COMMAND_TIMEOUT_S, srv.seen)
    lectern_name = m.group(1).strip()
    name, period, qst = board(srv, fails, lambda: None)
    if name != lectern_name:
        fails.append(f"the lectern belongs to {lectern_name} and the board to {name}")
    kinds = [t for _, t, *_ in qst]
    if kinds[:2] != ["traer", "guardian"]:
        fails.append(f"the board starts with {kinds[:2]} (must be traer and guardian: there are unique structures nearby)")
        return None
    srv.run(f"tp {PLAYER} {floor_bottom[0]} {y} {floor_bottom[1]}", r"Teleported")
    # control: with no reputation in the village, the fixed trade does not change price
    before = price(srv, spot, y, floor_bottom)
    if before != 0:
        fails.append(f"price without reputation: specialPrice {before} (must be 0)")
    close_out(srv)
    srv.run(f"tp {PLAYER} {floor_bottom[0]} {y} {floor_bottom[1]}", r"Teleported")
    # 2) accept the fetch one and the guardian one
    _, _, item, amount, _, _ = qst[0]
    _, _, sid, _, gx, gz = qst[1]
    for n in (1, 2):
        as_player(srv, f"heraldia quest accept {n}", rf"Heraldia: encargos: {PLAYER} acepta")
    m = as_player(srv, "heraldia quest accept 1", r"already have that job|Ya tienes ese encargo")
    print(f"accepted: fetch {amount} × {item}, guardian of {sid} at {gx}, {gz}")
    # 3) fetch: without the items it is not handed in; with them, it is
    as_player(srv, "heraldia quest turnin", r"not enough yet|aún no basta")
    srv.run(f"give {PLAYER} {item} {amount + 3}", r"Gave")
    m = as_player(srv, "heraldia quest turnin", rf"Heraldia: encargos: {PLAYER} entrega .*reputación (-?\d+) \((\w+)\)")
    rep1 = int(m.group(1))
    em1 = emeralds(srv)
    m = srv.run(f"clear {PLAYER} {item} 0", r"Found (\d+) matching|No items")
    if int(m.group(1) or 0) != 3:
        fails.append(f"fetch: {m.group(1) or 0} × {item} left (3 must be left: {amount} were handed in)")
    if not 3 <= em1 <= 6:
        fails.append(f"traer: paga {em1} esmeraldas (de 3 a 6)")
    if rep1 != 10:
        fails.append(f"fetch: reputation {rep1} (must be 10)")
    print(f"fetch handed in: {em1} emeralds, reputation {rep1}")
    cells = rim_cells(found)
    x0, y0, z0 = cells[0]
    srv.run(f"setblock {x0} {y0} {z0} {OTHER_BLOCK}", r"Changed the block|Could not set")
    if any(pots(srv, cells)):
        fails.append(f"village look: flower pots on the rim with reputation {rep1} (must be none before 'conocido')")
    # 4) guardian: a mob with its tags next to the quest site, killed by the player
    tx, tz = gx + 40, gz
    srv.run(f"forceload add {tx} {tz}", r"Marked|force|already")
    if not srv.until(f"execute if loaded {tx} 64 {tz}", attempts=480):   # with its entities: otherwise the mob is lost
        fails.append("guardian: the chunk of the quest site does not get loaded")
        return None
    for _ in range(ATTEMPTS):
        m = srv.run(f'summon minecraft:zombie {tx} 200 {tz} {{NoAI:1b,PersistenceRequired:1b,NoGravity:1b,'
                    f'Tags:["heraldia_guardian","heraldia_guardian.{sid}","heraldia_adulto","heraldia_prueba_g"]}}', r"Summoned")
        if "Summoned" in m.group(0) and srv.until("execute if entity @e[tag=heraldia_prueba_g]", attempts=10):
            break
        time.sleep(RETRY_S)
    else:
        fails.append("guardian: could not be summoned next to the quest site")
        return None
    srv.run(f"damage @e[tag=heraldia_prueba_g,limit=1] 2000 minecraft:player_attack by {PLAYER}",
            rf"Heraldia: encargos: {PLAYER} cumple .* \(guardian\)")
    m = as_player(srv, "heraldia quest turnin", rf"Heraldia: encargos: {PLAYER} entrega .*reputación (-?\d+) \((\w+)\)")
    rep2, level = int(m.group(1)), m.group(2)
    em2 = emeralds(srv) - em1
    if rep2 != 40 or level != "conocido":
        fails.append(f"guardian: reputation {rep2} ({level}); must be 40 (conocido)")
    if em2 not in (8, 12):
        fails.append(f"guardian: pays {em2} emeralds (8 or 12)")
    if not srv.test(f"execute if entity @a[name={PLAYER},advancements={{heraldia:encargos/primero=true}}]"):
        fails.append("advancement encargos/primero not granted")
    print(f"guardian handed in: {em2} emeralds, reputation {rep2} ({level})")
    m = look_line(srv, "conocida", 20)
    if m is None:
        fails.append("village look: reaching 'conocido' does not change the village")
    else:
        print(f"village look {m.group(1)}: placed {m.group(2)}, removed {m.group(3)}, left alone {m.group(4)}")
        if (m.group(2), m.group(3)) != ("3", "0"):
            fails.append(f"village look: placed {m.group(2)} and removed {m.group(3)} (must be 3 and 0: one corner is taken)")
    if pots(srv, cells) != [False, True, True, True]:
        fails.append(f"village look: flower pots on the rim {pots(srv, cells)} (must be [False, True, True, True])")
    if not srv.test(f"execute if block {x0} {y0} {z0} {OTHER_BLOCK}"):
        fails.append("village look: the block that was not the mod's was touched")
    # 5) price in the plaza with "conocido": 10 % discount (before the quests there was none: see above)
    inside = price(srv, spot, y, floor_bottom)
    print(f"price in the plaza: before {before}, with reputation 'conocido' {inside}")
    if inside != -1:
        fails.append(f"price in the plaza with reputation 'conocido': specialPrice {inside} (must be -1)")
    close_out(srv)
    # 6) hitting the villager lowers the reputation
    m = srv.run(f"damage @e[tag=heraldia_prueba,limit=1] 1 minecraft:player_attack by {PLAYER}",
                rf"Heraldia: encargos: {PLAYER} golpea a un aldeano de .*: reputación (-?\d+)")
    if m.group(1) != "35":
        fails.append(f"hit on the villager: reputation {m.group(1)} (must be 35)")
    # 7) abandonar uno aceptado
    if len(qst) >= 3:
        srv.run(f"tp {PLAYER} {floor_bottom[0]} {y} {floor_bottom[1]}", r"Teleported")
        as_player(srv, "heraldia quest accept 3", rf"Heraldia: encargos: {PLAYER} acepta")
        as_player(srv, "heraldia quest abandon 1", r"Job abandoned|Encargo abandonado")
        as_player(srv, "heraldia quest abandon 1", r"no job number 1|No hay encargo número 1")
    # 8) villager conversations (P9a)
    srv.run(f"tp {PLAYER} {floor_bottom[0]} {y} {floor_bottom[1]}", r"Teleported")
    conversation(srv, fails, spot, y, floor_bottom)
    delivered = state(srv)
    if delivered != "2":
        fails.append(f"/heraldia status: {delivered} encargos entregados (deben ser 2)")
    return name, period, qst


def second_lap(srv, fails, found, first_item, work):
    style, to_world, y, sheriff_pos = found
    spot, floor_bottom = to_world(SPOT), to_world(BOT)
    srv.run(f"forceload add {int(sheriff_pos[0]) - RADIUS} {int(sheriff_pos[2]) - RADIUS} {int(sheriff_pos[0]) + RADIUS} {int(sheriff_pos[2]) + RADIUS}",
            r"Marked|Added|force|already")
    srv.run(f"player {PLAYER} spawn at {floor_bottom[0]} {y} {floor_bottom[1]}", r"joined the game")
    srv.until(f"execute if entity @a[name={PLAYER}]")
    srv.ctx.ticks(10)
    for effect in ("water_breathing", "resistance"):   # close_out leaves the player wherever it lands (sometimes in water)
        srv.run(f"effect give {PLAYER} minecraft:{effect} infinite 4 true", r"Applied effect|Unable to apply")
    name, period, qst = board(srv, fails, lambda: as_player(srv, "heraldia quest", BOARD.pattern))
    if (name, period, qst) != first_item:
        fails.append(f"after restarting, another board: {qst} (before {first_item[2]})")
    as_player(srv, "heraldia quest accept 1", r"already handed in that job|Ya entregaste ese encargo")
    if not srv.until(f"execute if entity @e[tag=heraldia_prueba]"):
        fails.append("the test villager is no longer in the plaza")
    inside = existing_price(srv, spot, y, floor_bottom)
    if inside != -1:
        fails.append(f"after restarting, price in the plaza {inside} (must be -1: the reputation is kept)")
    close_out(srv)
    # P9a: the wayfarer remembers its hint, saved in the villager (no wait between conversations from now on)
    write_config(work, {"dialogos": {"viajeros_porcentaje": 100, "espera_segundos": 0}})
    srv.run("heraldia reload", r"Heraldia: configuración recargada")
    srv.run("tag @e[tag=heraldia_prueba] add heraldia", r"Added tag|Nothing changed")
    srv.run(f"tp {PLAYER} {floor_bottom[0]} {y} {floor_bottom[1]}", r"Teleported")
    as_player(srv, WITH, TALK)
    as_player(srv, "heraldia talk rumor", TOLD)
    write_config(work, {"dialogos": {"activado": False}})
    srv.run("heraldia reload", r"Heraldia: configuración recargada")
    as_player(srv, WITH, r"Conversations with villagers are disabled|conversaciones con los aldeanos están desactivadas")
    srv.run("tag @e[tag=heraldia_prueba] remove heraldia", r"Removed tag|Nothing changed")
    # options disabled and reloaded without restarting
    cells = rim_cells(found)
    if pots(srv, cells) != [False, True, True, True]:
        fails.append(f"village look: after restarting, flower pots on the rim {pots(srv, cells)} (must be [False, True, True, True])")
    write_config(work, {"encargos": {"activado": False}, "reputacion": {"activado": False}})
    srv.run("heraldia reload", r"Heraldia: configuración recargada")
    m = look_line(srv, "normal", 30)
    if m is None or (m.group(2), m.group(3)) != ("0", "3"):
        fails.append(f"village look: with reputation disabled, {m.group(0) if m else 'nothing'} (must place 0 and remove 3)")
    if any(pots(srv, cells)):
        fails.append(f"village look: with reputation disabled, flower pots left {pots(srv, cells)}")
    if not srv.test(f"execute if block {cells[0][0]} {cells[0][1]} {cells[0][2]} {OTHER_BLOCK}"):
        fails.append("village look: with reputation disabled, the block that was not the mod's was touched")
    as_player(srv, "heraldia quest", r"quests are disabled|están desactivados")
    sin = existing_price(srv, spot, y, floor_bottom)
    if sin != 0:
        fails.append(f"with reputation disabled, specialPrice {sin} (must be 0)")
    print(f"after restarting: same board, handed-in quests kept, price {inside}; disabled: price {sin}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-encargos"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    fails = []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    write_config(a.work, DIALOGUE_CONFIG)
    srv = Server(a.work, launcher)
    first_item = found = None
    try:
        found = plaza(srv, fails)
        if found:
            first_item = first_lap(srv, fails, found)
            srv.run(f"player {PLAYER} kill", r"left the game")
    finally:
        srv.stop()
    if found and first_item:
        srv = Server(a.work, launcher)
        try:
            second_lap(srv, fails, found, first_item, a.work)
            srv.run(f"player {PLAYER} kill", r"left the game")
        finally:
            srv.stop()
    if found and first_item and not fails:
        tiers_lap(a.work, launcher, found, fails)
    if fails:
        print("FALLOS:")
        for f in fails:
            print(" -", f)
        return 1
    print("OK: board, accepting, fetch and guardian handed in, reputation, reduced price, villager conversations and hint, "
          "restart and disabled options; reputation visible in the village without touching a block that is not the mod's")
    return 0


if __name__ == "__main__":
    sys.exit(main())
