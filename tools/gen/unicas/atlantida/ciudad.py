"""Plano de la Atlántida: trazado, solares y distritos."""
import math
from . import urbanismo as U
from . import cosas as C
from . import edificios as E
from .mundo import Mundo, Vista

S = U.SUELO
PASO = 24                 # retícula de solares
NUCLEO = 96               # radio reservado a la acrópolis
CARDINAL, DIAGONAL = 230, 156
ZONAS = {                 # distritos singulares: centro y radio reservado
    "agora": (0, -CARDINAL, 60), "termas": (CARDINAL, 0, 60), "puerto": (0, CARDINAL, 60), "academia": (-CARDINAL, 0, 60),
    "artesanos": (DIAGONAL, -DIAGONAL, 34), "arsenal": (DIAGONAL, DIAGONAL, 50), "jardines": (-DIAGONAL, DIAGONAL, 50),
    "anfiteatro": (-DIAGONAL, -DIAGONAL, 50),
}


def libre(x, z, medio):
    """El solar centrado en (x, z) con semilado medio no pisa avenidas, núcleo, muralla ni distritos singulares."""
    r = math.hypot(x, z)
    if r < NUCLEO + medio or r > U.RADIO - U.MURO - U.RONDA - medio * 1.5:
        return False
    if abs(x) < U.AVENIDA + 4 + medio or abs(z) < U.AVENIDA + 4 + medio:
        return False
    return all(math.hypot(x - cx, z - cz) >= rad + medio for cx, cz, rad in ZONAS.values() if rad)


def giro_al_centro(x, z):
    """Giro para que la fachada mire a la avenida más cercana (hacia el eje dominante)."""
    if abs(x) >= abs(z):
        return 3 if x > 0 else 1
    return 0 if z > 0 else 2


def vista_centrada(m, x, z, w, d, giro):
    v = Vista(m, 0, 0, giro, S)
    du, dv = v.p((w - 1) // 2, (d - 1) // 2)
    return Vista(m, x - du, z - dv, giro, S)


def solares(m):
    """Barrios: retícula ortogonal simétrica; el tipo depende de |x|, |z| (simetría), el detalle de x, z."""
    n, medio = 0, PASO // 2
    for i in range(-16, 16):
        for j in range(-16, 16):
            x, z = i * PASO + medio, j * PASO + medio
            if not libre(x, z, 8):
                continue
            tipo = U.dispersion(i if i >= 0 else -i - 1, j if j >= 0 else -j - 1, 11) % 100
            sal = U.dispersion(i, j, 12) % 1000
            giro = giro_al_centro(x, z)
            ruinoso = x < 0 and z > 0 or z > 0 and abs(x) < 110        # hacia los jardines y el puerto: más ruina
            w, d = 11 + 2 * (sal % 3), 11 + 2 * (sal // 3 % 2)
            if tipo < (21 if ruinoso else 5):
                E.ruina(vista_centrada(m, x, z, w, d, giro), w, d, sal, cofre="menor" if sal % 6 == 0 else None)
            elif tipo < 58:
                E.casa(vista_centrada(m, x, z, w, d, giro), w, d, True, sal, cofre="menor" if sal % 3 == 0 else None)
            elif tipo < 76:
                v = vista_centrada(m, x, z, w, d, giro)
                E.casa(v, w, d, False, sal, cofre="menor" if sal % 5 == 0 else None, nombre="casa_inundada")
                if sal % 4 == 1:
                    C.generador(v, 1, 1, d - 2, "drowned", tridente=sal % 8 == 1)
                elif sal % 4 == 2:
                    v.entity(w // 2, 2, d // 2, C.ahogado(sal % 3 == 0))
            elif tipo < 88:
                E.torre(vista_centrada(m, x, z, 11, 11, giro), 5, sal, cofre="media")
            else:
                E.plazuela(vista_centrada(m, x, z, 9, 9, giro), 9, sal)
                if sal % 2:
                    m.entity(x, S + 3, z + 6, C.guardian())
            n += 1
    return n


def construir():
    from . import distritos as D
    from . import acropolis as A
    m = Mundo()
    m.cuenta_solares = solares(m)
    for nombre, (cx, cz, _) in ZONAS.items():
        giro = {"agora": 2, "termas": 3, "puerto": 0, "academia": 1}.get(nombre, giro_al_centro(cx, cz))
        D.DISTRITOS[nombre](Vista(m, cx, cz, giro, S))
    v = Vista(m, 0, 0, 0, 0)
    A.templo(v)
    fin = A.vestibulo(v)
    tramos = A.galerias(v)
    A.poblar_galerias(v, tramos)
    A.camaras(v, fin)
    m.sanear_algas()
    m.anegar()
    return m
