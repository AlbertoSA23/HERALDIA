"""The door rule (doors.py): on a layout of buildings, all of it; on a single template, what can be checked inside it."""
from core import Template
import doors


def test_footprints_room_facing_and_spacing():
    a = ("a", (10, 10, 20, 20), [("east", 20, 15)])
    assert doors.footprint_errors([a, ("b", (30, 10, 40, 20), [("west", 30, 15)])]) == []
    e = doors.footprint_errors([a, ("b", (27, 12, 37, 18), [])])
    assert e == ["the door of a at 20 15 faces the wall of b 7 blocks away"]
    e = doors.footprint_errors([a, ("b", (23, 14, 30, 18), [])])
    assert "a and b are 2 blocks apart (at least 4)" in e
    assert "the door of a at 20 15 opens onto b 3 blocks out" in e


def _house(front=None):
    """A 5 x 5 stone hut with a roof, its door in the south wall; `front`: a block 2 cells out of the door."""
    t = Template("x")
    for x in range(0, 7):
        for z in range(0, 12):
            t.set(x, 0, z, "stone")
    for x in range(1, 6):
        for z in range(1, 6):
            for y in (1, 2, 3):
                t.set(x, y, z, "stone_bricks" if x in (1, 5) or z in (1, 5) else "air")
            t.set(x, 4, z, "stone_bricks")
    t.set(3, 1, 5, "oak_door[facing=south,half=lower,hinge=left,open=false]")
    t.set(3, 2, 5, "oak_door[facing=south,half=upper,hinge=left,open=false]")
    for z in range(6, 12):
        for y in (1, 2):
            t.set(3, y, z, "air")
    if front:
        for y in (1, 2):
            t.set(3, y, 7, front)
    return t


def test_template_door_with_room_in_front():
    assert doors.template_report(_house()) == []


def test_template_door_blocked_in_front():
    r = doors.template_report(_house("stone_bricks"))
    assert r == ["door at 3 1 5: 3 1 7 (2 out) is not free and walkable"]


def test_template_door_facing_a_wall():
    t = _house()
    for x in (2, 3, 4):
        for y in (1, 2):
            t.set(x, y, 10, "stone_bricks")
    assert doors.template_report(t) == ["door at 3 1 5: a wall 5 blocks in front of it (2 10)"]


def _eave(t):
    """The same hut with its roof carried one block out over the door (an eave, a porch): the door's way out is covered."""
    for x in range(1, 6):
        t.set(x, 4, 6, "stone_brick_slab[type=bottom]")
    return t


def test_a_door_under_a_cover_is_still_checked():
    """Until Nov 2026 a door with a roof over the cell in front of it was skipped without a word (1,386 of the mod's
    2,153 doors: every house with eaves). The way out is found on foot instead, and the same rule applies."""
    assert [k for *_, k, _ in doors.survey(_eave(_house()))] == ["covered"]
    assert doors.survey(_eave(_house()))[0][4] == "south"
    assert doors.template_report(_eave(_house())) == []
    assert doors.template_report(_eave(_house(front="cobblestone")))
    assert doors.template_report(_eave(_house(front="oak_fence")))


def test_what_cannot_be_checked_is_said():
    """A door between two rooms, a door at the template's edge and a gate with the sky on both sides are not outside
    doors of one building: survey() names each, template_report() leaves them, and nothing is passed over in silence."""
    t = Template("x")                                  # two roofed rooms and a door between them
    for x in range(0, 11):
        for z in range(0, 7):
            t.set(x, 0, z, "stone")
            t.set(x, 4, z, "stone")
            for y in (1, 2, 3):
                t.set(x, y, z, "stone_bricks" if x in (0, 5, 10) or z in (0, 6) else "air")
    t.set(5, 1, 3, "oak_door[facing=east,half=lower,hinge=left,open=false]")
    t.set(5, 2, 3, "oak_door[facing=east,half=upper,hinge=left,open=false]")
    assert [k for *_, k, _ in doors.survey(t)] == ["inner"]
    g = Template("y")                                  # a gate in a yard wall, open to the sky on both sides
    for x in range(0, 7):
        for z in range(0, 7):
            g.set(x, 0, z, "stone")
    for x in range(0, 7):
        g.set(x, 1, 3, "cobblestone_wall")
    g.set(3, 1, 3, "oak_door[facing=south,half=lower,hinge=left,open=false]")
    g.set(3, 2, 3, "oak_door[facing=south,half=upper,hinge=left,open=false]")
    assert [k for *_, k, _ in doors.survey(g)] == ["open"]
    e = _house()                                       # the hut cut at its own door: what is beyond is another piece
    e.blocks = {p: v for p, v in e.blocks.items() if p[2] <= 5}
    assert [k for *_, k, _ in doors.survey(e)] == ["edge"]
    for tt in (t, g, e):
        assert doors.template_report(tt) == []
    assert set(doors.CHECKED) | set(doors.UNCHECKED) == {"sky", "covered", "inner", "edge", "open", "through"}


def test_the_report_counts_every_door():
    class Reg:
        templates = {"a": _house(), "b": _eave(_house()), "c": _eave(_house(front="cobblestone"))}
    assert doors.registry_survey(Reg) == {"sky": 1, "covered": 2}
    assert set(doors.registry_report(Reg)) == {"c"}


def test_a_layer_of_snow_does_not_block_a_door():
    t = _house()
    t.set(3, 1, 6, "snow[layers=1]")
    assert doors.template_report(t) == []
