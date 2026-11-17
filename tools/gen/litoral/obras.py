"""Plantillas de la costa en coordenadas de diseño: x a lo ancho (0 en el eje), z hacia el mar (la orilla, el ancla, en
z = 0), y = 0 la fila inferior.

Faro (y = 0, la plataforma a ras del terreno más alto de la huella): la plataforma de 15 x 20 en tierra (z = -20..-1),
la torre de 7 x 7 junto a la orilla (z = -8..-2) con 28 bloques de alto, la casa del farero al fondo y el embarcadero de
3 x 11 sobre el agua (z = 0..10) con pilotes cada 3 bloques. La luz: una lámpara de redstone encendida sobre un bloque
de redstone en el centro de la linterna (y = 22-23), con piedra luminosa encima: siempre encendida, sin circuitos.

Naufragio (el galeón de 9 x 31, quilla en y = 0, bodega y = 2-4, cubierta y = 5, castillo de popa con el camarote y = 6-8,
mástil mayor hasta y = 17): encallado (a) con la proa en la playa (z = -14..16, `fila_mar` 1) o semihundido (b) en
aguas poco profundas (z = 8..38, `fila_mar` 4, con la bodega inundada). Partido por la mitad (z de 15 a 17 desde la
proa): sin cubierta y con el costado de estribor abierto. Bajo `fila_mar` no hay aire en la plantilla: lo que no es
casco queda sin poner (el agua o la arena del sitio se quedan)."""
from types import SimpleNamespace
from core import Template, B, F, NS, adulto, anclado
from medianas import _comun as c
from unicas._comun import piezas

ANCHO = 7                     # la mitad de la plataforma del faro (x = -7..7)
FONDO = 20                    # tierra del faro (z = -20..-1)
MUELLE = 10                   # el embarcadero llega hasta z = 10
TORRE_Z = -5                  # centro de la torre
ALTO_MURO = 21                # la caña de la torre: y = 1..21
GALERIA = 22                  # suelo de la galería (y = 22) y la linterna encima (y = 23-24)
ESLORA = 31


def _mesa(t, x, y, z, madera):
    t.set(x, y, z, f"{madera}_fence")
    t.set(x, y + 1, z, f"{madera}_pressure_plate[powered=false]")


# ------------------------------------------------------------------ faro
def anillo(cuadrada):
    """dentro(dx, dz, r): la planta de radio r de la torre, cuadrada o octogonal (las esquinas cortadas; r = 1, 3 x 3)."""
    if cuadrada:
        return lambda dx, dz, r: abs(dx) <= r and abs(dz) <= r
    return lambda dx, dz, r: abs(dx) <= r and abs(dz) <= r and (r <= 1 or abs(dx) + abs(dz) <= 2 * r - 1)


def _faro(variante, p, name):
    """La plataforma y la torre: caña (r = 3) de y = 1 a 21 con el interior (r = 2) hueco, la sala de guardia en y = 12,
    la galería (r = 4, y = 22) con barandilla y el paseo sobre el muro, y la linterna (r = 2) acristalada con la luz."""
    t = Template(name)
    dentro = anillo(variante == "b")
    m, cim = p["madera"], p["cimiento"]
    # plataforma (y = 0) y aire encima: el terreno de la huella queda despejado
    for x in range(-ANCHO, ANCHO + 1):
        for z in range(-FONDO, 0):
            t.set(x, 0, z, cim[(x * 7 + z * 3 + x * z) % len(cim)])
            for y in range(1, 5):
                t.set(x, y, z, "air")
            if p["nieve"] and (x * 5 + z * 11) % 7 == 0:
                t.set(x, 1, z, "snow[layers=1]")
    for dx in range(-4, 5):
        for dz in range(-4, 5):
            x, z = dx, TORRE_Z + dz
            if dentro(dx, dz, 3) and not dentro(dx, dz, 2):            # muro de la caña
                for y in range(1, ALTO_MURO + 1):
                    esquina = variante == "b" and abs(dx) == 3 and abs(dz) == 3
                    if y == 1:
                        st = p["zocalo"]
                    elif esquina:
                        st = f"{p['esquina']}[axis=y]" if p["esquina"].endswith(("_log", "_wood")) else p["esquina"]
                    elif variante == "a":
                        st = p["banda"] if y in (7, 8, 15, 16) else p["muro"]
                    else:
                        st = p["banda"] if (y // 3) % 2 == 1 else p["muro"]
                    t.set(x, y, z, f"{st}[axis=y]" if st.endswith("_wood") else st)
            elif dentro(dx, dz, 2):                                     # interior hueco con el piso de la sala
                t.set(x, 0, z, cim[0])
                for y in range(1, GALERIA):
                    t.set(x, y, z, "air")
                t.set(x, 11, z, f"{m}_planks")
            if not dentro(dx, dz, 4):
                continue
            # galería, barandilla, paseo y linterna
            if (dx, dz) != (0, 2):
                t.set(x, GALERIA, z, p["zocalo"])
            if not dentro(dx, dz, 3):
                t.set(x, GALERIA + 1, z, f"{m}_fence")
            elif not dentro(dx, dz, 2) or dentro(dx, dz, 1) or (dx, dz) == (0, 2):
                for y in (GALERIA + 1, GALERIA + 2):
                    t.set(x, y, z, "air")
            else:
                for y in (GALERIA + 1, GALERIA + 2):
                    t.set(x, y, z, "glass_pane")
            if dentro(dx, dz, 2):                                       # tejado de la linterna
                t.set(x, GALERIA + 3, z, p["zocalo"] if dentro(dx, dz, 1) else f"{p['losa']}[type=bottom,waterlogged=false]")
    # ventanas en tres caras (en la del mar, la sur, va la escalera por dentro)
    for y in (5, 9, 14, 18):
        for dx, dz in ((3, 0), (-3, 0), (0, -3)):
            t.set(dx, y, TORRE_Z + dz, "glass_pane")
    # puerta al norte (hacia la casa) y escalera de mano pegada al muro sur, de la planta baja a la galería
    c.door(t, 0, 1, TORRE_Z - 3, "south", f"{m}_door")
    for y in range(1, GALERIA + 1):
        t.set(0, y, TORRE_Z + 2, "ladder[facing=north,waterlogged=false]")
    # la luz: bloque de redstone bajo la lámpara (siempre encendida) y piedra luminosa encima; el pararrayos en lo alto
    t.set(0, GALERIA, TORRE_Z, "redstone_block")
    t.set(0, GALERIA + 1, TORRE_Z, "redstone_lamp[lit=true]")
    t.set(0, GALERIA + 2, TORRE_Z, "glowstone")
    t.set(0, GALERIA + 4, TORRE_Z, "lightning_rod[facing=up,powered=false,waterlogged=false]")
    if p["nieve"]:
        for dx, dz in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            t.set(dx, GALERIA + 4, TORRE_Z + dz, "snow[layers=2]")
    # dentro: planta baja con toneles y farol; sala de guardia (y = 12) con el cofre y la mesa de cartografía
    t.set(-2, 1, TORRE_Z - 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    t.set(2, 1, TORRE_Z - 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    c.farol(t, 2, 1, TORRE_Z + 1, colgado=False)
    piezas.chest(c.put(t), -2, 12, TORRE_Z, "east", f"{NS}:costa/faro")
    t.set(2, 12, TORRE_Z, "cartography_table")
    c.farol(t, 0, 21, TORRE_Z, colgado=True)
    c.farol(t, 0, 10, TORRE_Z, colgado=True)
    return t


def _casa(t, p, lado):
    """Casa del farero de 7 x 6 al fondo de la plataforma (lado -1: al oeste; 1: al este), con la puerta al sur."""
    m, casa = p["madera"], p["casa"]
    x0, x1 = (-6, 0) if lado < 0 else (0, 6)
    z0, z1 = -18, -13
    c.caja(t, x0, 1, z0, x1, 3, z1, casa, esquina=f"{p['tronco']}[axis=y]")
    t.fill(x0, 0, z0, x1, 0, z1, p["cimiento"][0])
    t.fill(x0, 4, z0, x1, 4, z1, f"{m}_planks")
    c.tejado(t, x0, z0, x1, z1, 5, p["teja"], p["cumbrera"], casa)
    puerta = (x0 + x1) // 2
    c.door(t, puerta, 1, z1, "north", f"{m}_door")
    c.ventana(t, x0, 2, -15)
    c.ventana(t, x1, 2, -15)
    c.ventana(t, puerta, 2, z0)
    # cama, mesa con silla, horno y el tonel del farero
    c.cama(t, x0 + 1, z0 + 1, "north", p["cama"])
    _mesa(t, x1 - 2, 1, z0 + 2, m)
    t.set(x1 - 1, 1, z0 + 2, f"{m}_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    t.set(x1 - 1, 1, z0 + 1, "furnace[facing=west,lit=false]")
    piezas.chest(c.put(t), x0 + 1, 1, z1 - 1, "east", f"{NS}:costa/faro", kind="barrel")
    c.farol(t, puerta, 3, z0 + 3)
    # senda de la puerta a la torre
    for z in range(z1 + 1, TORRE_Z - 3):
        t.set(puerta, 0, z, p["cimiento"][1])
    if puerta != 0:
        for x in range(min(puerta, 0), max(puerta, 0) + 1):
            t.set(x, 0, TORRE_Z - 4, p["cimiento"][1])
    return puerta


def _muelle(t, p):
    """Embarcadero de 3 x 11 (z = 0..10) a la altura de la plataforma, sobre pilotes cada 3 bloques (bajan al fondo)."""
    m = p["madera"]
    for z in range(-1, MUELLE + 1):
        for x in (-1, 0, 1):
            t.set(x, 0, z, f"{m}_planks")
        if z >= 0 and (z % 3 == 0 or z == MUELLE):
            for x in (-1, 1):
                t.set(x, 0, z, f"{p['tronco']}[axis=y]")
    for x in (-1, 0, 1):
        t.set(x, 1, MUELLE, f"{m}_fence")
    t.set(-1, 1, MUELLE - 1, f"{m}_fence")
    t.set(1, 1, MUELLE - 1, f"{m}_fence")
    c.farol(t, 1, 2, MUELLE, colgado=False)
    t.set(-1, 1, 4, f"{m}_fence")                    # bolardo


def ofertas():
    """Tratos del farero: compra bacalao y algas secas, vende mapas vacíos, una brújula y un catalejo."""
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [c.oferta({"id": "minecraft:cod", "count": 12}, em(1), 12),
            c.oferta({"id": "minecraft:dried_kelp_block", "count": 6}, em(1), 12),
            c.oferta(em(2), {"id": "minecraft:map", "count": 1}, 6),
            c.oferta(em(4), {"id": "minecraft:compass", "count": 1}, 3),
            c.oferta(em(6), {"id": "minecraft:spyglass", "count": 1}, 2)]


def faro(variante, p, name):
    t = _faro(variante, p, name)
    lado = -1 if variante == "a" else 1
    puerta = _casa(t, p, lado)
    _muelle(t, p)
    if variante == "a":                               # el farero, junto a su puerta
        n = {"id": "minecraft:villager", "PersistenceRequired": B(1), "NoAI": B(1), "Invulnerable": B(1),
             "CustomName": piezas.text(f"{NS}.costa.farero", "Farero"), "CustomNameVisible": B(1),
             "VillagerData": {"profession": "minecraft:cartographer", "level": 2, "type": f"minecraft:{p['aldeano']}"},
             "Xp": 10, "Rotation": [F(0.0), F(0.0)], "Offers": {"Recipes": ofertas()}}
        t.entity(puerta, 1, -11, n)
    o = SimpleNamespace(t=t, ancla=(0, 0), fila_mar=None, luz=(0, GALERIA + 1, TORRE_Z),
                        tierra=(-ANCHO, -FONDO, ANCHO, -1), mar=(-1, 2, 1, MUELLE), galeria=GALERIA, torre=TORRE_Z)
    return o


# ------------------------------------------------------------------ naufragio
def manga(s):
    """Media manga del casco a s bloques de la proa (0) hacia la popa (ESLORA - 1)."""
    return (0, 1, 2, 2, 3)[s] if s < 5 else 4 if s < 27 else 3


def _galeon(t, p, z0, fila_mar, hundido):
    """El casco con la proa en z0 y la popa en z0 + ESLORA - 1. Bajo fila_mar no se pone aire."""
    m, tronco, banda = p["madera"], p["tronco"], p["banda"]
    tablon = f"{m}_planks"
    aire = lambda x, y, z: t.set(x, y, z, "air") if y > fila_mar else None
    roto = lambda s: 15 <= s <= 17
    for s in range(ESLORA):
        z, h = z0 + s, manga(s)
        # quilla y fondo
        t.set(0, 0, z, f"{tronco}[axis=z]")
        for x in range(-max(h - 2, 0), max(h - 2, 0) + 1):
            if x:
                t.set(x, 0, z, tablon)
        # costados (y = 1 un bloque más adentro: la curva del casco) y suelo de la bodega
        for x in range(-h, h + 1):
            if abs(x) == max(h - 1, 0) and h > 0:
                t.set(x, 1, z, tablon)
            elif abs(x) < h - 1:
                t.set(x, 1, z, tablon)
        for y in range(2, 5):
            for x in range(-h, h + 1):
                if abs(x) == h:
                    if not (roto(s) and x > 0):               # estribor abierto en la rotura
                        t.set(x, y, z, banda if y == 3 else tablon)
                elif not roto(s):
                    aire(x, y, z)
        # cubierta (y = 5) y borda (y = 6)
        for x in range(-h, h + 1):
            if roto(s) and x >= -1:
                continue
            if (x, s) in ((0, 9), (0, 10)):
                aire(x, 5, z)                                 # escotilla abierta a la bodega
            else:
                t.set(x, 5, z, tablon)
        if 8 <= s <= 21 and not roto(s) and s not in (14, 18):
            for x in (-h, h):
                t.set(x, 6, z, f"{m}_fence")
    # castillo de proa (y = 6) con su borda y un peldaño desde la cubierta
    for s in range(1, 8):
        for x in range(-manga(s), manga(s) + 1):
            t.set(x, 6, z0 + s, tablon)
        for x in (-manga(s), manga(s)):
            if manga(s):
                t.set(x, 7, z0 + s, f"{m}_fence")
    t.set(0, 6, z0 + 8, f"{m}_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    for s in range(-3, 1):                                     # bauprés
        t.set(0, 6, z0 + s, f"{tronco}[axis=z]")
    # castillo de popa: el camarote (y = 6-8) con su puerta a proa y el techo con borda (y = 9-10)
    for s in range(22, ESLORA):
        z, h = z0 + s, manga(s)
        for x in range(-h, h + 1):
            borde = abs(x) == h or s in (22, ESLORA - 1)
            for y in range(6, 9):
                t.set(x, y, z, tablon if borde else "air")
            t.set(x, 9, z, tablon)
            if abs(x) == h or s == ESLORA - 1:
                t.set(x, 10, z, f"{m}_fence")
    c.door(t, 0, 6, z0 + 22, "south", f"{m}_door")
    for s in (25, 28):
        for x in (-manga(s), manga(s)):
            t.set(x, 7, z0 + s, "glass_pane")
    piezas.chest(c.put(t), -2, 6, z0 + 28, "east", f"{NS}:costa/camarote")
    _mesa(t, 2, 6, z0 + 26, m)
    t.set(2, 6, z0 + 27, f"{m}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    c.farol(t, 0, 8, z0 + 26, colgado=True)
    # mástil mayor (y = 1..17) con la verga y la vela rota; el muñón del de mesana, partido en y = 9
    for y in range(1, 18):
        t.set(0, y, z0 + 12, f"{tronco}[axis=y]")
    for x in range(-4, 5):
        t.set(x, 15, z0 + 13, f"{tronco}[axis=x]")
    for x in range(-3, 4):
        for y in range(8, 15):
            if (x * 3 + y * 5) % 7 != 0 and not (y < 10 and (x + y) % 3 == 0):
                t.set(x, y, z0 + 13, p["vela"])
    for y in range(1, 10):
        t.set(0, y, z0 + 20, f"{tronco}[axis=y]")
    t.set(0, 10, z0 + 20, f"stripped_{tronco}[axis=y]")
    # en la bodega: el cofre (bajo el agua en el semihundido) y unos toneles
    piezas.chest(c.put(t), 2, 2, z0 + 6, "west", f"{NS}:costa/bodega", waterlogged=hundido)
    if not hundido:
        t.set(-2, 2, z0 + 6, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
        t.set(-2, 2, z0 + 10, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    if p["nieve"]:
        for s in range(9, 22):
            for x in range(-manga(s) + 1, manga(s)):
                if not roto(s) and (x * 7 + s * 3) % 5 == 0 and t.get(x, 6, z0 + s) is None \
                        and "planks" in (t.get(x, 5, z0 + s) or ""):
                    t.set(x, 6, z0 + s, "snow[layers=1]")


def naufragio(variante, p, name):
    t = Template(name)
    hundido = variante == "b"
    if hundido:
        z0, fila = 8, 4
    else:
        z0, fila = -14, 1
    _galeon(t, p, z0, fila, hundido)
    if hundido:                                       # el ahogado de la bodega inundada, anclado y adulto
        n = {"id": "minecraft:drowned", "PersistenceRequired": B(1), "Rotation": [F(180.0), F(0.0)]}
        t.entity(-2, 2, z0 + 4, anclado(adulto(n), siempre=True))
        tierra, mar = (-2, -6, 2, -2), (-4, z0, 4, z0 + ESLORA - 1)
    else:
        tierra, mar = (-3, z0, 3, -3), (-3, 3, 3, z0 + ESLORA - 1)
    return SimpleNamespace(t=t, ancla=(0, 0), fila_mar=fila, luz=None, tierra=tierra, mar=mar, proa=z0)


def construir(tipo, variante, paleta, name):
    return (faro if tipo == "faro" else naufragio)(variante, paleta, name)
