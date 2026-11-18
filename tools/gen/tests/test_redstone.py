"""_comun/redstone.py: static simulation with the game rules, stability check and puzzles."""
from uniques._common import redstone as rs, pieces
from core import Template


def t_of(blocks):
    t = Template("r")
    for p, st in blocks.items():
        t.set(*p, st)
    return t


def test_conductor():
    assert rs.conductor("minecraft:stone") and rs.conductor("minecraft:oak_planks")
    for b in ("minecraft:glass", "minecraft:oak_slab[type=bottom]", "minecraft:redstone_wire", "minecraft:air", None):
        assert not rs.conductor(b)


def test_attached_dir():
    assert rs.attached_dir("minecraft:redstone_torch[lit=true]") == "down"
    assert rs.attached_dir("minecraft:redstone_wall_torch[facing=east,lit=true]") == "west"
    assert rs.attached_dir("minecraft:lever[face=floor,facing=north,powered=false]") == "down"
    assert rs.attached_dir("minecraft:lever[face=ceiling,facing=north,powered=false]") == "up"
    assert rs.attached_dir("minecraft:lever[face=wall,facing=north,powered=false]") == "south"
    assert rs.attached_dir("minecraft:stone") is None


def test_cable_straight_and_loose():
    # a wire alone forms a cross; in a line, it connects with its neighbours and with the lever
    t = t_of({(0, 0, 0): "stone", (0, 1, 0): "redstone_wire[power=0]"})
    c = rs.wire_connections(t.get, (0, 1, 0))
    assert all(c.values())
    t = t_of({(x, 0, 0): "stone" for x in range(3)})
    t.set(0, 1, 0, "redstone_wire")
    t.set(1, 1, 0, "redstone_wire")
    c = rs.wire_connections(t.get, (0, 1, 0))
    assert c["east"] and c["west"] and not c["north"] and not c["south"]


def test_cable_that_climbs():
    t = t_of({(0, 0, 0): "stone", (1, 0, 0): "stone", (1, 1, 0): "stone"})
    t.set(0, 1, 0, "redstone_wire")
    t.set(1, 2, 0, "redstone_wire")
    assert rs.wire_links(t.get, (0, 1, 0)) == {"east": (1, 2, 0)}
    rs.wire_shapes(t)
    assert "east=up" in t.get(0, 1, 0)
    # with a conductive block on top of the one below, it does not climb
    t.set(0, 2, 0, "stone")
    assert rs.wire_links(t.get, (0, 1, 0)) == {}


def test_lever_wire_lamp():
    t = t_of({(x, 0, 0): "stone" for x in range(5)})
    t.set(0, 1, 0, "lever[face=floor,facing=east,powered=true]")
    for x in (1, 2, 3):
        t.set(x, 1, 0, "redstone_wire")
    t.set(4, 1, 0, "redstone_lamp[lit=false]")
    sim = rs.Sim(t)
    assert [sim.wire[(x, 1, 0)] for x in (1, 2, 3)] == [15, 14, 13]
    assert sim.powered((4, 1, 0))
    sim = rs.Sim(t, {(0, 1, 0): False})          # the input replaces the written state
    assert not sim.powered((4, 1, 0)) and sim.wire[(1, 1, 0)] == 0


def test_torch_inverting():
    # lever on one block and wall torch on the other side: lever on -> torch off
    t = t_of({(1, 1, 0): "stone"})
    t.set(0, 1, 0, "lever[face=wall,facing=west,powered=false]")
    t.set(2, 1, 0, "redstone_wall_torch[facing=east,lit=true]")
    assert rs.Sim(t).torch[(2, 1, 0)] is True
    assert rs.Sim(t, {(0, 1, 0): True}).torch[(2, 1, 0)] is False


def test_clock_oscillates():
    # wall torch on support S, block above the torch and dust above S: the torch powers itself
    # through the dust and turns off (a clock that burns out in the game): the simulator finds no fixed point
    import pytest
    t = t_of({(0, 0, 0): "stone", (1, 1, 0): "stone", (1, 0, 0): "redstone_wall_torch[facing=east,lit=true]",
              (0, 1, 0): "redstone_wire[power=0]"})
    with pytest.raises(ValueError, match="oscillates"):
        rs.Sim(t)


def test_repeater_only_forward():
    # (the simulator does not treat the redstone block as a source: the tests use lit levers)
    t = t_of({(x, 0, 0): "stone" for x in range(3)})
    t.set(0, 1, 0, "lever[face=floor,facing=east,powered=true]")
    t.set(1, 1, 0, "repeater[delay=1,facing=west,locked=false,powered=false]")   # faces its input (west)
    t.set(2, 1, 0, "redstone_lamp[lit=false]")
    sim = rs.Sim(t)
    assert sim.rep[(1, 1, 0)] and sim.powered((2, 1, 0))
    t.set(1, 1, 0, "repeater[delay=1,facing=east,locked=false,powered=false]")   # the other way round: nothing happens
    sim = rs.Sim(t)
    assert not sim.rep[(1, 1, 0)] and not sim.powered((2, 1, 0))


def test_quasi_connectivity_of_the_piston():
    # a piston activates if the block above would receive a signal (redstone block above the cell above)
    t = t_of({(0, 0, 0): "sticky_piston[extended=false,facing=north]", (2, 1, 0): "stone",
              (1, 1, 0): "lever[face=wall,facing=west,powered=true]"})
    sim = rs.Sim(t)
    assert sim.signal_at((0, 0, 0)) == 0 and sim.powered((0, 0, 0))      # only through the cell above
    t.clear(1, 1, 0)
    assert not rs.Sim(t).powered((0, 0, 0))


def test_check_static_detects_unstable():
    t = t_of({(1, 1, 0): "stone"})
    t.set(0, 1, 0, "lever[face=wall,facing=west,powered=false]")
    t.set(2, 1, 0, "redstone_wall_torch[facing=east,lit=false]")      # it should be lit
    errs, _ = rs.check_static(t)
    assert any("antorcha de redstone inestable" in e for e in errs)
    rs.set_torches(t)
    assert rs.check_static(t)[0] == []


def test_check_static_piston_without_head_and_lever_without_support():
    t = t_of({(0, 0, 0): "sticky_piston[extended=true,facing=north]", (1, 0, 0): "stone",
              (1, 0, 1): "lever[face=wall,facing=south,powered=true]"})
    errs, _ = rs.check_static(t)
    assert any("without a head" in e for e in errs)
    t = t_of({(0, 0, 0): "lever[face=wall,facing=north,powered=false]"})
    errs, _ = rs.check_static(t)
    assert any("without a solid block" in e for e in errs)


def test_check_static_cable_and_tnt():
    t = t_of({(x, 0, 0): "stone" for x in range(3)})
    t.set(0, 1, 0, "lever[face=floor,facing=east,powered=true]")
    t.set(1, 1, 0, "redstone_wire[east=side,west=side,north=none,south=none,power=3]")
    t.set(2, 1, 0, "tnt[unstable=false]")
    errs, _ = rs.check_static(t)
    assert any("power 3" in e for e in errs) and any("TNT" in e for e in errs)
    rs.set_wire_power(t)
    assert not any("power" in e for e in rs.check_static(t)[0])


def _combination_door(n_levers):
    """Wall four thick with a combination door (piezas.combo_door)."""
    t = Template("c")
    put = lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt)
    for x in range(0, 12):
        for y in range(0, 3):
            for z in range(0, 4):
                put(x, y, z, "stone_bricks")
    levers = []
    for i in range(n_levers):
        k = 4 + 2 * i
        put(k, 1, -1, "air")
        levers.append(((k, 1, -1), (k, 1, 0)))
    rec = pieces.combo_door(put, (0, 0, 2), "x", 1, [((k, 1, -1 + 0), (k, 1, 0)) for (k, _, _), _ in levers],
                            block="stone_bricks")
    return t, rec


def test_combo_door_stable_and_only_with_the_solution():
    t, rec = _combination_door(2)
    # the torches are at z = 1 (middle layer), the dust in the door layer (z = 2)
    assert all(p[2] == 1 for p in rec["antorchas"]) and all(p[2] == 2 for p, _ in rec["polvo"])
    assert rs.check_static(t)[0] == []
    levers = [lp for lp, _ in rec["palancas"]]
    assert rs.check_puzzle(t, "combo", levers, (True, True), rec["pistones"], opens_if="sin_potencia") == []
    # with another declared solution, the checker finds the fault
    assert rs.check_puzzle(t, "combo", levers, (True, False), rec["pistones"], opens_if="sin_potencia")


def test_retract_pulls_the_block():
    t = Template("p")
    put = lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt)
    pieces.piston_door(put, [(0, 0, 0)], (1, 0), "west", "stone_bricks")
    sim = rs.Sim(t)                      # without power: the piston retracts
    b = rs.retract(t, sim)
    assert b[(2, 0, 0)].startswith("minecraft:sticky_piston[extended=false")
    assert b[(1, 0, 0)] == "minecraft:stone_bricks" and (0, 0, 0) not in b
