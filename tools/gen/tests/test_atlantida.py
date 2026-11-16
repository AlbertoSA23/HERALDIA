"""Atlántida: urbanismo.dispersion y alto_muro deben dar lo mismo que BasePiece.hash y wallHeight (Java). Las sumas de
control son las de src/test/java/.../unicas/atlantida/BasePieceTest.java: si cambia un lado, falla su prueba."""
from unicas.atlantida.urbanismo import dispersion, alto_muro, ALTO_MURO


def test_dispersion_como_en_java():
    assert [dispersion(x, z, s) for x, z, s in [(0, 0, 0), (1, 2, 3), (-5, 7, 1), (100, -100, 2), (123456, -654321, 9)]] == \
        [0, 1914873318, 1252417215, 2096724523, 706372064]
    h = 0
    for x in range(-300, 301, 7):
        for z in range(-300, 301, 11):
            h = (h * 31 + dispersion(x, z, x ^ z)) & 0xFFFFFFFF
    assert h == 935813057


def test_muralla_como_en_java():
    assert alto_muro(10, 0) == 13 and alto_muro(0, 10) == 6
    s = 0
    for x in range(-300, 301, 7):
        for z in range(-300, 301, 11):
            w = alto_muro(x, z)
            assert w == ALTO_MURO or 3 <= w <= 7
            s = (s * 31 + w) & 0xFFFFFFFF
    assert s == 4003156210


def test_mobs_anclados():
    """Ahogados (centinelas, hoplitas) y el jefe: adultos y anclados (core.ANCLADO_TAG); los peces guardianes, no."""
    from core import ADULTO_TAG, ANCLADO_TAG
    from unicas._comun.piezas import GUARDIAN_TAG
    from unicas.atlantida import cosas
    for n in (cosas.ahogado(), cosas.ahogado(elite=True)):
        assert ADULTO_TAG in n["Tags"] and ANCLADO_TAG in n["Tags"]
    jefe = cosas.jefe()
    assert GUARDIAN_TAG in jefe["Tags"] and ANCLADO_TAG in jefe["Tags"]
    for n in (cosas.guardian(), cosas.anciano()):
        assert ANCLADO_TAG not in n.get("Tags", [])
