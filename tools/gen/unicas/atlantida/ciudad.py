"""Plano de la Atlántida: distritos y edificios."""
from . import urbanismo as U
from .mundo import Mundo

S = U.SUELO
LADRILLO, OSCURA, PRISMARINA, LINTERNA, CRISTAL = "prismarine_bricks", "dark_prismarine", "prismarine", "sea_lantern", "light_blue_stained_glass"


def casa_seca(m, x, z, w=9, d=9, nombre="casa"):
    """Casa de dos plantas: baja inundada con portal al sur; alta seca, a la que se sube buceando por una piscina lunar."""
    y0, y1, y2 = S, S + 5, S + 10                      # suelo, forjado, techo
    m.shell(x, y0, z, x + w - 1, y2, z + d - 1, LADRILLO, floor=OSCURA, roof=OSCURA)
    m.fill(x, y1, z, x + w - 1, y1, z + d - 1, OSCURA)                       # forjado
    m.water(x + 1, y0 + 1, z + 1, x + w - 2, y1 - 1, z + d - 2)             # planta baja inundada
    cx = x + w // 2
    m.water(cx, y0 + 1, z + d - 1, cx, y0 + 2, z + d - 1)                   # portal sur
    m.air(x + 1, y1 + 1, z + 1, x + w - 2, y2 - 1, z + d - 2)               # planta alta seca
    m.water(cx, y1, z + 2, cx + 1, y1, z + 3)                               # piscina lunar (2 x 2)
    for wx in (x, x + w - 1):                                               # ventanas de cristal macizo
        m.fill(wx, y1 + 2, z + d // 2 - 1, wx, y1 + 3, z + d // 2 + 1, CRISTAL)
    m.set(x + 1, y2 - 1, z + 1, LINTERNA)
    m.set(x + w - 2, y2 - 1, z + d - 2, LINTERNA)
    for c in ((x + 1, y1 + 1, z + d - 2), (x + w - 2, y1 + 2, z + 1), (cx, y1 + 1, z + 3)):
        m.marca("seca", *c)
    m.marca("agua", cx, y1, z + 2)
    return m


def construir():
    m = Mundo()
    casa_seca(m, 20, -330)
    casa_seca(m, -29, -330)
    return m
