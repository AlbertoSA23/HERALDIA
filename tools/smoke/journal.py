"""Each player's journal (/heraldia journal) on a real 26.3 dedicated server, with a simulated player (Carpet, like guide.py).

Usage: python3 tools/smoke/journal.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Reads from the .jar (and the disabled families from the configuration) the advancements that make the catalog (aldeas/todas, unicas/todas, medianas/todas|nether|end, minas/*,
costa/*), the unique structures' dimension and the en_us texts, and checks that:
  - a new player sees every kind at 0 out of the total that the advancements give (the Nether and End ones apart), and the
    overall total;
  - after granting one advancement (or criterion) of each kind, each kind counts 1 and the total goes up by as many;
  - /heraldia journal uniques gives the discovered one by name and the rest as missing; mines keep their size order;
  - nothing in the replies is a coordinate;
  - /heraldia status, asked by the player, counts the Nether medium structure as discovered and points to the journal.
"""
import argparse, json, os, re, shutil, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomes import fetch
from trophies import CARPET
from guide import Server

PLAYER = "cronista"   # lowercase: this Carpet build logs the fake player in as "cronista" for "Cronista"
X, Y, Z = 0, 101, 0
OVERVIEW_END = r"are in the Herald's Guide: |You have found everything"   # the last line while unique structures are missing
DETAIL_END = r"\[« Journal\]"
SECTIONS = {"villages": "Village families", "uniques": "Unique structures", "mediums": r"Medium structures \(by type\)",
            "mines": r"Mine entrances \(by size\)", "coast": "Coast: lighthouse and shipwreck", "nether": "The Nether",
            "end": "The End"}


def jar_data(jar):
    """(expected totals per section, the first id of each kind, en_us texts) from the .jar's advancements and structures."""
    with zipfile.ZipFile(jar) as z:
        names = set(z.namelist())
        adv = lambda p: json.loads(z.read(f"data/heraldia/advancement/{p}.json"))
        lang = json.loads(z.read("assets/heraldia/lang/en_us.json"))
        families = sorted(adv("aldeas/todas")["criteria"])
        uniques = {"uniques": [], "nether": [], "end": []}
        for sid in sorted(adv("unicas/todas")["criteria"]):
            st = json.loads(z.read(f"data/heraldia/worldgen/structure/unicas/{sid}.json"))
            uniques[st.get("modo", "uniques") if st["type"] == "heraldia:dimension" else "uniques"].append(sid)
        mediums = {d: sorted(adv(f"medianas/{p}")["criteria"]) if f"data/heraldia/advancement/medianas/{p}.json" in names else []
                   for d, p in (("mediums", "todas"), ("nether", "nether"), ("end", "end"))}
        mines = [m for m in ("pequena", "mediana", "grande") if f"data/heraldia/advancement/minas/{m}.json" in names]
        coast = [c for c in ("faro", "naufragio") if f"data/heraldia/advancement/costa/{c}.json" in names]
    totals = {"villages": len(families), "uniques": len(uniques["uniques"]), "mediums": len(mediums["mediums"]),
              "mines": len(mines), "coast": len(coast), "nether": len(uniques["nether"]) + len(mediums["nether"]),
              "end": len(uniques["end"]) + len(mediums["end"])}
    first = {"family": families[0], "unique": uniques["uniques"][0], "medium": mediums["mediums"][0],
             "nether_medium": mediums["nether"][0] if mediums["nether"] else None, "mines": mines, "coast": coast[0]}
    return totals, first, lang


REPLIES = []


def ask(srv, cmd, end):
    """Everything the server writes in reply to `cmd` (as the player) up to the line matching `end`."""
    mark = len(srv.seen)
    srv.ctx.run(f"execute as {PLAYER} run {cmd}", end + r"|Unknown|Incorrect")
    text = "".join(srv.seen[mark:])
    if "journal" in cmd:
        REPLIES.append(text)
    return text


def counts(text):
    out = {}
    for sec, name in SECTIONS.items():
        m = re.search(rf"(\d+)/(\d+) {name}", text)
        if m:
            out[sec] = (int(m.group(1)), int(m.group(2)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-diario"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    totals, first, lang = jar_data(a.jar)
    fails = []
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    srv = Server(a.work, launcher)
    try:
        ctx = srv.ctx
        # a family disabled in the configuration (pantano, by default) is not missing: it cannot appear
        with open(os.path.join(a.work, "config", "heraldia.json"), encoding="utf-8") as f:
            off = [k for k, v in json.load(f).get("aldeas", {}).get("familias", {}).items() if v is False]
        totals["villages"] -= len(off)
        if first["family"] in off:
            raise SystemExit(f"the first family ({first['family']}) is disabled in this configuration")
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        for rule in ("spawn_mobs", "advance_time"):
            ctx.run(f"gamerule {rule} false", rf"[Gg]ame ?rule .*{rule}")
        srv.spawn(PLAYER)
        ctx.run(f"advancement revoke {PLAYER} everything", r"Revoked|revoked|Couldn't")
        # 1) nothing found yet: every kind at 0 of its total
        text = ask(srv, "heraldia journal", OVERVIEW_END)
        total = sum(totals.values())
        print(f"expected totals (families disabled: {off}): {totals}")
        if f"{PLAYER}'s journal" not in text or f"0 of {total} discoveries in total" not in text:
            fails.append(f"new player: no title or total 0 of {total}: {text[-1500:]}")
        got = counts(text)
        for sec, n in totals.items():
            want = (0, n) if n else None
            if got.get(sec) != want:
                fails.append(f"new player, {sec}: {got.get(sec)}, should be {want}")
        print(f"journal of a new player: {got}")
        # 2) one of each kind
        grants = [f"only heraldia:aldeas/{first['family']}", f"only heraldia:unicas/{first['unique']}/descubrir",
                  f"only heraldia:medianas/todas {first['medium']}", f"only heraldia:minas/{first['mines'][0]}",
                  f"only heraldia:costa/{first['coast']}"]
        if first["nether_medium"]:
            grants.append(f"only heraldia:medianas/nether {first['nether_medium']}")
        for g in grants:
            ctx.run(f"advancement grant {PLAYER} {g}", r"Granted|granted|Couldn't|Unknown|Incorrect|No ")
        text = ask(srv, "heraldia journal", OVERVIEW_END)
        got = counts(text)
        for sec in ("villages", "uniques", "mediums", "mines", "coast") + (("nether",) if first["nether_medium"] else ()):
            if got.get(sec) != (1, totals[sec]):
                fails.append(f"after one of each kind, {sec}: {got.get(sec)}, should be (1, {totals[sec]})")
        if f"{len(grants)} of {total} discoveries in total" not in text:
            fails.append(f"after {len(grants)} discoveries the total does not say so: {text[-1500:]}")
        if "/heraldia guide" not in text:
            fails.append("with unique structures missing it does not point to the Herald's Guide")
        print(f"after one of each kind: {got}")
        # 3) a kind's detail: names found and missing
        text = ask(srv, "heraldia journal uniques", DETAIL_END)
        name = lang[f"heraldia.unicas.{first['unique']}.nombre"]
        if f"Found (1): {name}" not in text or f"Still to find ({totals['uniques'] - 1}):" not in text:
            fails.append(f"journal uniques: {text[-1200:]}")
        text = ask(srv, "heraldia journal mines", DETAIL_END)
        names = [lang[f"heraldia.minas.{m}.nombre"] for m in first["mines"]]
        if f"Found (1): {names[0]}" not in text or ("Still to find" in text and ", ".join(names[1:]) not in text):
            fails.append(f"journal mines (size order): {text[-800:]}")
        # no coordinates in any journal reply (three numbers in a row, or a "[x, y, z]")
        for t in REPLIES:
            for line in t.splitlines():
                body = line.split("]: ", 1)[-1]
                if re.search(r"-?\d+,? -?~?\d+,? -?\d+|\[-?\d+, ", body):
                    fails.append(f"a journal reply looks like coordinates: {body}")
        # 4) /heraldia status: the Nether medium counts and the player is pointed to the journal
        text = ""
        for page in range(1, 6):   # paged: 8 lines a page, the last one has only the previous-page button
            text += ask(srv, f"heraldia status {page}", r"\[« Previous page\]|\[Next page »\]")
            if re.search(r"page (\d+) of \1\)", text):
                break
        if "/heraldia journal" not in text:
            fails.append(f"/heraldia status does not point to the journal: {text[-1200:]}")
        m = re.search(r"Medium structures \(by type\): (\d+) of (\d+)", text)
        want = 2 if first["nether_medium"] else 1
        if not m or int(m.group(1)) != want:
            fails.append(f"/heraldia status medium structures: {m and m.group(0)}, should count {want} (the Nether one too)")
    finally:
        srv.stop()
    if fails:
        print("JOURNAL FAILED:\n - " + "\n - ".join(fails))
        return 1
    print("JOURNAL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
