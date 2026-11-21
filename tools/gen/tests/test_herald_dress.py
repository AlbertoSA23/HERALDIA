"""The Herald's House, dressed (herald_dress.py): relief, texture and a skyline over the plain build, and nothing else.
The dressed template has the same entities, block entities and light sources as the plain one, the wall walk stays
open from tower to tower (two lanes, three blocks of headroom), the mural towers stand two to a side clear of every
building and every door, and each roof gets its eaves, its ridge and (the long gables) its dormers."""
import collections

import pytest

import herald_dress as d
import herald_house as h

LIGHTS = ("lantern", "torch", "campfire", "candle", "glowstone", "lamp", "froglight", "shroomlight")


@pytest.fixture(scope="module")
def plain():
    return h.construct(dressed=False)


@pytest.fixture(scope="module")
def t():
    return h.construct()


def names(t, keys):
    return collections.Counter(h._name(st) for st, _ in t.blocks.values() if any(k in st for k in keys))


def test_only_blocks_are_added(t, plain):
    assert len(t.entities) == len(plain.entities)
    assert sorted(p for p, v in t.blocks.items() if v[1]) == sorted(p for p, v in plain.blocks.items() if v[1])
    assert names(t, LIGHTS) == names(plain, LIGHTS)
    assert t.size() == plain.size()


def test_the_detail_is_modest_in_blocks(t, plain):
    solid = lambda tt: sum(1 for st, _ in tt.blocks.values() if st != "minecraft:air")
    assert solid(plain) < solid(t) <= solid(plain) * 1.03


def test_nothing_that_was_kept_free_is_filled(t, plain):
    """What players and villagers walk on and through at ground level stays as it was, but for the towers' feet and the
    wall's buttresses (on grass the plain town leaves empty)."""
    filled = [p for p, (st, _) in t.blocks.items() if p[1] in (h.FLOOR + 1, h.FLOOR + 2) and st != "minecraft:air"
              and plain.blocks[p][0] == "minecraft:air"]
    assert filled
    for x, y, z in filled:
        assert h._name(plain.get(x, h.FLOOR, z)) == "grass_block", (x, y, z)
        assert min(x, z, h.N - 1 - x, h.SOUTH + h.WALL_T - 1 - z) <= d.TOWER_D, (x, y, z)


def test_two_mural_towers_a_side_clear_of_buildings_and_doors(t):
    assert collections.Counter(side for side, _ in t.mural_towers) == {"north": 2, "south": 2, "west": 2, "east": 2}
    sides = d._sides()
    for side, i0 in t.mural_towers:
        at, (dx, dz), _ = sides[side]
        foot = [(at(i0 + j)[0] + dx * k, at(i0 + j)[1] + dz * k) for j in range(d.TOWER_W) for k in range(d.TOWER_D)]
        for b in t.blds:
            if b.name.startswith("torre_") and b.name != "torre_reloj":
                continue
            assert all(not (b.x0 - h.GAP <= x <= b.x1 + h.GAP and b.z0 - h.GAP <= z <= b.z1 + h.GAP) for x, z in foot), (side, i0, b.name)
            for dside, x, y, z in b.doors():
                ox, oz = h.OPEN_DIR[dside]
                front = {(x + ox * k + w * abs(oz), z + oz * k + w * abs(ox)) for k in range(1, h.FACE_CLEAR + 1) for w in (-1, 0, 1)}
                assert not front & set(foot), (side, i0, b.name)


def test_the_wall_walk_stays_open(t):
    """Both lanes of the walk, feet to three blocks up, all along every side between the corner towers and the gates:
    the golems that keep the night watch walk it, through the mural towers too."""
    top = h.WALL_TOP
    for side, (at, (dx, dz), length) in d._sides().items():
        for i in range(length):
            if d._blocked(t, side, i):
                continue
            ox, oz = at(i)
            for k in (1, 2):
                x, z = ox + dx * k, oz + dz * k
                assert lint_solid(t.get(x, top, z)), (side, i, k)
                for y in range(top + 1, top + 4):
                    assert t.is_free(x, y, z), (side, i, k, y, t.get(x, y, z))


def lint_solid(st):
    import lint
    return lint.top_height(st) == 1.0


def test_nobody_falls_off_the_battlements(t):
    """Outside, over the walk's floor, every cell is a merlon, a crenel's low wall or a tower's breast: no gap."""
    top = h.WALL_TOP
    for side, (at, _, length) in d._sides().items():
        for i in range(length):
            if not d._blocked(t, side, i):
                assert not t.is_free(*at(i)[:1], top + 1, at(i)[1]), (side, i)


def test_every_roof_gets_eaves_and_a_ridge(t, plain):
    changed = collections.Counter()
    for p, (st, _) in t.blocks.items():
        if plain.blocks[p][0] != st and p[1] > h.FLOOR + 4:
            for b in t.blds:
                if b.x0 - 2 <= p[0] <= b.x1 + 2 and b.z0 - 2 <= p[2] <= b.z1 + 2:
                    changed[b.name] += 1
    for b in t.blds:
        if not b.name.startswith(d.SKIP_ROOFS):
            assert changed[b.name] >= 20, (b.name, changed[b.name])


def test_long_gables_get_dormers(t, plain):
    inner = lambda x, z: min(x, z, h.N - 1 - x, h.SOUTH + h.WALL_T - 1 - z) >= d.TOWER_D     # not a mural tower's window
    panes = [p for p, (st, _) in t.blocks.items() if "glass_pane" in st and plain.blocks[p][0] == "minecraft:air"
             and p[1] > h.FLOOR + 5 and inner(p[0], p[2])]
    assert len(panes) >= 10, len(panes)
    for x, y, z in panes:                       # a dormer's pane stands on the roof, between two posts
        assert not t.is_free(x, y - 1, z)
        assert sum(h._name(t.get(x + dx, y, z + dz)) == h.BEAM for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))) == 2


def test_door_lanes_are_cobbled_and_still_walkable(t, plain):
    """Every cell of a door's path that the plain town lays as dirt path is a full block or a path in the dressed one,
    with the same free space over it; most of them are stone now."""
    import lint
    cells = {c for _, _, cs in plain.paths for c in cs or () if h._name(plain.get(c[0], h.FLOOR, c[1])) == "dirt_path"
             and not plain.street.get(c)}
    assert len(cells) > 100
    stone = 0
    for x, z in cells:
        st = t.get(x, h.FLOOR, z)
        assert lint.top_height(st) in (1.0, 0.9375) or h._name(st) == "dirt_path", (x, z, st)
        assert t.is_free(x, h.FLOOR + 1, z) and t.is_free(x, h.FLOOR + 2, z), (x, z)
        stone += h._name(st) != "dirt_path"
    assert stone > 0.7 * len(cells)
