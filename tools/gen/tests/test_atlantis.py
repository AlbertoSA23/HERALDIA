"""Atlantis: urbanismo.dispersion and alto_muro must give the same as BasePiece.hash and wallHeight (Java). The checksums
are those of src/test/java/.../unicas/atlantida/BasePieceTest.java: if one side changes, its test fails."""
from uniques.atlantis.urban_layout import dispersion, wall_height, WALL_HEIGHT


def test_scatter_like_in_java():
    assert [dispersion(x, z, s) for x, z, s in [(0, 0, 0), (1, 2, 3), (-5, 7, 1), (100, -100, 2), (123456, -654321, 9)]] == \
        [0, 1914873318, 1252417215, 2096724523, 706372064]
    h = 0
    for x in range(-300, 301, 7):
        for z in range(-300, 301, 11):
            h = (h * 31 + dispersion(x, z, x ^ z)) & 0xFFFFFFFF
    assert h == 935813057


def test_rampart_as_in_java():
    assert wall_height(10, 0) == 13 and wall_height(0, 10) == 6
    s = 0
    for x in range(-300, 301, 7):
        for z in range(-300, 301, 11):
            w = wall_height(x, z)
            assert w == WALL_HEIGHT or 3 <= w <= 7
            s = (s * 31 + w) & 0xFFFFFFFF
    assert s == 4003156210


def test_anchored_mobs():
    """Drowned (sentinels, hoplites) and the boss: adult and anchored (core.ANCLADO_TAG); the guardian fish, not."""
    from core import ADULT_TAG, ANCHORED_TAG
    from uniques._common.pieces import GUARDIAN_TAG
    from uniques.atlantis import things
    for n in (things.drowned(), things.drowned(elite=True)):
        assert ADULT_TAG in n["Tags"] and ANCHORED_TAG in n["Tags"]
    boss = things.boss()
    assert GUARDIAN_TAG in boss["Tags"] and ANCHORED_TAG in boss["Tags"]
    for n in (things.guardian(), things.elder()):
        assert ANCHORED_TAG not in n.get("Tags", [])
