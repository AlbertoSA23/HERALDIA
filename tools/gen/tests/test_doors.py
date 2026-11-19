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
