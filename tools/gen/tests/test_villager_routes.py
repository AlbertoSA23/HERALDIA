"""Villager routes (pack.build_theme, houses.make_house, specials): where beds, workstations and bells go, in the 36 styles.

Vanilla villagers walk on their own between the bed they claim (home), the workstation of their profession (job site) and
the bell (meeting point), each within 48 blocks and the closest first. A villager whose workstation stands next to their
own bed spends the day indoors; these checks keep home and work apart. The real behaviour (how many villagers walk the
village during a simulated day) is measured on a server by tools/smoke/village_routes.py.
"""
import pytest
import pack
from build import WORKSTATION
from themes import THEMES

JOBS = {b: p for p, b in WORKSTATION.items()}


def residents(t):
    """[(profession, (x, y, z))] of the bed slots of a template that can hold an employed villager (nobed staff stand at
    their workstation and sleep elsewhere, so they do not count)."""
    out = []
    for j in t.jigsaws:
        pool = j["pool"]
        if "/villagers/" not in pool and not pool.startswith("heraldia:villagers/"):
            continue
        prof = pool.rsplit("/", 1)[1]
        if prof.startswith("nobed_"):
            continue
        out.append((prof.replace("fixed_", "").replace("room_", ""), j["pos"]))
    return out


def workstations(t):
    """[(profession, (x, y, z))] of the workstations of a template (all cauldrons are the leatherworker's)."""
    out = []
    for pos, (st, _) in t.blocks.items():
        b = st.split("[")[0].replace("minecraft:", "")
        b = "cauldron" if b.endswith("cauldron") else b
        if b in JOBS:
            out.append((JOBS[b], pos))
    return out


@pytest.fixture(scope="module")
def styles():
    out = {}
    for i, th in enumerate(THEMES):
        reg = pack.Registry()
        pack.build_theme(reg, th, 2026 * 100 + i)
        out[th["id"]] = reg
    return out


def test_all_styles_built(styles):
    assert len(styles) == 36


def test_nobody_works_next_to_their_bed(styles):
    """No template holds a bed for a villager of a profession together with a workstation of that same profession:
    houses, inn and tavern rooms, the smithy and the farm."""
    bad = []
    for sid, reg in styles.items():
        for name, t in reg.templates.items():
            ws = {p for p, _ in workstations(t)}
            for prof, pos in residents(t):
                if prof in ws:
                    bad.append(f"{name}: {prof} sleeps at {pos} next to their workstation")
    assert not bad, "\n".join(bad[:20])


def test_houses_hold_another_trade(styles):
    """Each house has one workstation, of another profession, and the style's houses together offer the same
    professions they house (a fixed permutation): the village keeps its job supply."""
    for sid, reg in styles.items():
        houses = {n: t for n, t in reg.templates.items() if "/houses/" in n}
        assert len(houses) == 12, sid
        res, jobs = [], []
        for n, t in houses.items():
            r = residents(t)
            w = [p for p, _ in workstations(t)]
            assert len(r) == 1, n
            assert len(w) <= 2, n               # the workstation, and maybe a barrel of the woodshed
            res.append(r[0][0])
            jobs += [p for p in w if p != "fisherman" or r[0][0] != "fisherman"]
        assert set(res) <= set(jobs) | {"fisherman"}, sid


def test_every_profession_has_a_job_site_elsewhere(styles):
    """Every profession a villager of the style can be born with (bed slots) finds a workstation of its own in some other
    template of the same style: a house of another trade or a special building."""
    for sid, reg in styles.items():
        where = {}
        for name, t in reg.templates.items():
            for p, _ in workstations(t):
                where.setdefault(p, set()).add(name)
        for name, t in reg.templates.items():
            for prof, _ in residents(t):
                if prof == "none":
                    continue
                assert where.get(prof, set()) - {name}, f"{sid}: no {prof} workstation outside {name}"


def test_square_bell_where_people_meet(styles):
    """The square has one bell, hung low (villagers reach a bell within 6 blocks of where they stand) and with free
    ground around it, so that the midday gathering happens on the square."""
    for sid, reg in styles.items():
        for size in ("std", "grande"):
            t = reg.templates[f"{sid}/plaza/{size}"]
            bells = [p for p, (st, _) in t.blocks.items() if st.split("[")[0].replace("minecraft:", "") == "bell"]
            assert len(bells) == 1, (sid, size)
            x, y, z = bells[0]
            assert y <= 4, (sid, size, bells[0])
            free = [(x + dx, z + dz) for dx in (-1, 1) for dz in (-1, 0, 1)
                    if (t.get(x + dx, 1, z + dz) or "minecraft:air") in ("minecraft:air", "air")]
            assert len(free) >= 3, (sid, size, free)


def test_no_bed_up_a_ladder(styles):
    """Villagers do not plan paths up ladders: no bed slot stands on a floor that is only reached by one (the 2-storey
    houses keep the bed downstairs and the inns and taverns climb to their rooms by a staircase)."""
    bad = []
    for sid, reg in styles.items():
        for name, t in reg.templates.items():
            tops = {}
            for (x, y, z), (st, _) in t.blocks.items():
                if st.split("[")[0].replace("minecraft:", "") == "ladder":
                    tops[(x, z)] = max(tops.get((x, z), y), y)
            floors = set(tops.values())
            for j in t.jigsaws:
                if "villagers/" in j["pool"] and "/nobed_" not in j["pool"] and j["pos"][1] in floors:
                    bad.append(f"{name}: bed slot at {j['pos']} on a floor reached by ladder")
    assert not bad, "\n".join(bad[:20])


def test_inn_and_tavern_rooms_by_stairs(styles):
    """The inns and taverns have a 4-step staircase up to the rooms and no ladder."""
    for sid, reg in styles.items():
        for name, t in reg.templates.items():
            if "/specials/tavern" not in name and "/specials/inn" not in name:
                continue
            kinds = [st.split("[")[0].replace("minecraft:", "") for st, _ in t.blocks.values()]
            assert "ladder" not in kinds, name
            ys = sorted({p[1] for p, (st, _) in t.blocks.items() if "stairs" in st and "half=bottom" in st and 1 <= p[1] <= 4})
            assert ys[:4] == [1, 2, 3, 4], (name, ys)


def test_rooms_always_have_a_bed(styles):
    """The inn and tavern rooms always hold a bed (pool room_<profession>: bed with or without its guest, never a rug):
    the staff of the special buildings sleep there or in a house, never at work."""
    for sid, reg in styles.items():
        for name, t in reg.templates.items():
            if "/specials/tavern" in name or "/specials/inn" in name:
                pools = [j["pool"] for j in t.jigsaws if "villagers/" in j["pool"] and "/nobed_" not in j["pool"]]
                assert pools and all("/room_" in p for p in pools), (name, pools)
    reg = pack.Registry()
    pack.build_common(reg)
    for pid, pool in reg.pools.items():
        if "/room_" in pid:
            assert not any("/rug" in (e[0] or "") for e in pool["elements"]), pid
