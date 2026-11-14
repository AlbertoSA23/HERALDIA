"""Edificios genéricos de la Atlántida. Sistema local de Vista: fachada en v = 0, y = 0 es el pavimento."""
from . import urbanismo as U
from . import cosas as C

LADRILLO, OSCURA, PRISMARINA, LINTERNA = "prismarine_bricks", "dark_prismarine", "prismarine", "sea_lantern"
CRISTAL, CUARZO, PILAR = "light_blue_stained_glass", "quartz_bricks", "quartz_pillar[axis=y]"
PUERTA = "warped_door"
CORALES = ("tube_coral_block", "brain_coral_block", "bubble_coral_block", "fire_coral_block", "horn_coral_block")


def h(u, v, sal):
    return U.dispersion(u, v, sal)


def puerta(v, u, y, w, mira, material=PUERTA, bisagra="left"):
    """Puerta cerrada; mira = hacia dónde mira quien sale por ella (cara exterior)."""
    v.set(u, y, w, f"{material}[facing={mira},half=lower,hinge={bisagra},open=false]")
    v.set(u, y + 1, w, f"{material}[facing={mira},half=upper,hinge={bisagra},open=false]")


def columna(v, u, w, y1, y2):
    v.set(u, y1, w, CUARZO)
    v.fill(u, y1 + 1, w, u, y2 - 1, w, PILAR)
    v.set(u, y2, w, "chiseled_quartz_block")


def cubierta(v, w, d, y, estilo):
    """Cubierta sobre el forjado y: 0 = azotea con peto, 1 = escalonada."""
    if estilo == 0:
        for u in range(w):
            for z in range(d):
                if (u in (0, w - 1) or z in (0, d - 1)) and (u + z) % 2 == 0:
                    v.set(u, y + 1, z, OSCURA)
    else:
        k = 1
        while 2 * k < min(w, d) - 1 and k <= 3:
            v.fill(k, y + k, k, w - 1 - k, y + k, d - 1 - k, OSCURA if k % 2 else LADRILLO)
            k += 1
        v.set(w // 2, y + k, d // 2, LINTERNA)


def mobiliario(v, w, d, y, sal):
    """Planta seca: muebles pegados a los muros, centro libre. Devuelve la celda del cofre (o None)."""
    tipo = h(v.ox, v.oz, sal) % 3
    if tipo == 0:      # dormitorio
        v.set(1, y, d - 2, "cyan_bed[facing=south,part=head]")
        v.set(1, y, d - 3, "cyan_bed[facing=south,part=foot]")
        v.set(2, y, d - 2, "barrel[facing=up]", {"id": "minecraft:barrel"})
    elif tipo == 1:    # taller
        v.set(1, y, d - 2, "crafting_table")
        v.set(2, y, d - 2, "smithing_table")
        v.set(3, y, d - 2, "barrel[facing=up]", {"id": "minecraft:barrel"})
    else:              # estudio
        v.fill(1, y, d - 2, 3, y + 1, d - 2, "bookshelf")
        v.set(w - 2, y, d - 2, "lectern[facing=north]", {"id": "minecraft:lectern"})
    v.set(w - 2, y, 1, "decorated_pot", {"id": "minecraft:decorated_pot"})
    return (w - 2, y, d - 3)


def casa(v, w, d, seca=True, sal=0, cofre=None, nombre="casa"):
    """Casa de dos plantas (5 de alto cada una). seca: planta alta seca por piscina lunar o baja seca con puerta."""
    y1, y2 = 5, 10
    v.shell(0, 0, 0, w - 1, y2, d - 1, LADRILLO, floor=OSCURA, roof=OSCURA)
    v.fill(0, y1, 0, w - 1, y1, d - 1, OSCURA)
    for u, z in ((0, 0), (w - 1, 0), (0, d - 1), (w - 1, d - 1)):          # esquinas de cuarzo
        v.fill(u, 1, z, u, y2 - 1, z, CUARZO)
    cu = w // 2
    variante = h(v.ox, v.oz, sal + 1) % 2 if seca else 0
    for lado in (0, w - 1):                                               # ventanas altas
        v.fill(lado, y1 + 2, d // 2 - 1, lado, y1 + 3, d // 2 + 1, CRISTAL)
    v.fill(cu - 1, y1 + 2, 0, cu + 1, y1 + 3, 0, CRISTAL)
    v.set(cu, 3, 0, LINTERNA)                                             # dintel iluminado
    if seca and variante == 1:
        # planta baja seca con puerta a la calle y escalera de mano a la alta
        v.air(1, 1, 1, w - 2, y1 - 1, d - 2)
        v.air(1, y1 + 1, 1, w - 2, y2 - 1, d - 2)
        puerta(v, cu, 1, 0, "north")
        v.air(w - 2, y1, d - 2, w - 2, y1, d - 2)
        for y in range(1, y1 + 1):
            v.set(w - 2, y, d - 2, "ladder[facing=north]")
        v.set(1, y1 - 1, 1, LINTERNA)
        v.set(1, y2 - 1, 1, LINTERNA)
        libre = mobiliario(v, w, d - 1, y1 + 1, sal)
        v.set(1, 1, d - 2, "barrel[facing=up]", {"id": "minecraft:barrel"})
        v.marca("seca", 1, 1, 1)
        v.marca("seca", cu, y1 + 1, 2)
    elif seca:
        # planta baja inundada y abierta; alta seca por piscina lunar
        v.quitar(cu, 1, 0, cu, 2, 0)
        v.air(1, y1 + 1, 1, w - 2, y2 - 1, d - 2)
        v.quitar(cu, y1, 2, cu + 1, y1, 3)
        v.fill(cu, y1, 2, cu + 1, y1, 3, "water")
        v.set(1, y2 - 1, 1, LINTERNA)
        v.set(w - 2, y2 - 1, d - 2, LINTERNA)
        libre = mobiliario(v, w, d, y1 + 1, sal)
        v.marca("seca", cu, y1 + 1, 4)
        v.marca("agua", cu, y1, 2)
    else:
        # inundada: portal abierto, hueco en el forjado, sin cristales (se nada por dentro)
        v.quitar(cu, 1, 0, cu, 2, 0)
        v.quitar(cu - 1, y1, d // 2 - 1, cu + 1, y1, d // 2 + 1)
        v.quitar(cu - 1, y1 + 2, 0, cu + 1, y1 + 3, 0)
        v.set(1, y1 - 1, 1, LINTERNA)
        v.set(w - 2, y2 - 1, d - 2, LINTERNA)
        libre = (w - 2, y1 + 1, d - 2)
    cubierta(v, w, d, y2, h(v.ox, v.oz, sal + 2) % 2)
    if cofre:
        C.cofre(v, *libre, "north" if libre[2] > 1 else "south", cofre)
    v.sitio(nombre, 0, 0, 0, w - 1, y2 + 4, d - 1)
    return libre


def ruina(v, w, d, sal=0, cofre=None):
    """Casa derruida e inundada: muros a media altura, escombros, coral y algas."""
    y2 = 10
    for u in range(w):
        for z in range(d):
            borde = u in (0, w - 1) or z in (0, d - 1)
            v.set(u, 0, z, OSCURA if h(u + v.ox, z + v.oz, sal) % 5 else "gravel")
            if borde:
                alto = 2 + h((u + v.ox) >> 1, (z + v.oz) >> 1, sal + 3) % 7
                for y in range(1, min(alto, y2) + 1):
                    r = h(u + v.ox + y * 31, z + v.oz, sal + 4) % 10
                    v.set(u, y, z, LADRILLO if r < 6 else PRISMARINA if r < 9 else "mossy_cobblestone")
            else:
                r = h(u + v.ox, z + v.oz, sal + 5) % 40
                if r < 3:
                    v.set(u, 1, z, CORALES[r % 5])
                elif r < 6:
                    alto = 2 + r
                    for y in range(1, alto):
                        v.set(u, y, z, "kelp_plant")
                    v.set(u, alto, z, "kelp[age=25]")
                elif r < 8:
                    v.set(u, 1, z, "sea_pickle[pickles=3,waterlogged=true]")
                elif r < 10:
                    v.set(u, 1, z, LADRILLO)
    v.quitar(w // 2, 1, 0, w // 2, 3, 0)
    if cofre:
        C.cofre(v, w - 2, 1, d - 2, "north", cofre)
    v.sitio("ruina", 0, 0, 0, w - 1, y2, d - 1, ruinoso=True)


def torre(v, r=5, sal=0, cofre=None):
    """Torre redonda de tres cuerpos con cúpula; arriba, sala seca a la que se sube buceando por el hueco central."""
    c = r
    alto = 16
    v.disco(c, c, r, 0, 0, OSCURA)
    v.disco(c, c, r, 1, alto, LADRILLO, hueco=r - 1)
    for y in (5, 10):
        v.disco(c, c, r, y, y, OSCURA, hueco=r - 1)
    v.disco(c, c, r - 1, 11, 11, OSCURA)                      # forjado de la sala alta
    v.disco(c, c, r - 1, alto, alto, OSCURA)
    v.quitar(c, 1, 0, c, 2, 0)                                # portal
    v.set(c, 3, 0, LINTERNA)
    for u in range(c - r + 1, c + r):
        for z in range(c - r + 1, c + r):
            if (u - c) ** 2 + (z - c) ** 2 <= (r - 1 + 0.3) ** 2:
                v.air(u, 12, z, u, alto - 1, z)
    v.fill(c, 11, c, c, 11, c, "water")                       # piscina lunar (1 x 1 basta para subir)
    v.fill(c + 1, 11, c, c + 1, 11, c, "water")
    for lado in ((c, 13, 0), (c, 13, 2 * r), (0, 13, c), (2 * r, 13, c)):
        v.set(*lado, CRISTAL)
        v.set(lado[0], 14, lado[2], CRISTAL)
    v.set(c, alto, c, LINTERNA)
    v.cupula(c, c, r, alto + 1, OSCURA, nervio=LADRILLO)
    v.set(c, alto + r + 1, c, LINTERNA)
    if cofre:
        C.cofre(v, c, 12, c + r - 2, "north", cofre)
    v.marca("seca", c - 1, 12, c - 1)
    v.marca("agua", c, 11, c)
    v.sitio("torre", 0, 0, 0, 2 * r, alto + r + 2, 2 * r)


def plazuela(v, lado=9, sal=0):
    """Templete abierto: cuatro columnas, linterna central y una fuente de coral."""
    c = lado // 2
    v.fill(0, 0, 0, lado - 1, 0, lado - 1, LADRILLO)
    v.fill(1, 0, 1, lado - 2, 0, lado - 2, OSCURA)
    for u, z in ((1, 1), (lado - 2, 1), (1, lado - 2), (lado - 2, lado - 2)):
        columna(v, u, z, 1, 6)
    v.fill(0, 7, 0, lado - 1, 7, lado - 1, OSCURA)
    v.fill(2, 8, 2, lado - 3, 8, lado - 3, LADRILLO)
    v.set(c, 7, c, LINTERNA)
    v.set(c, 1, c, CORALES[h(v.ox, v.oz, sal) % 5])
    v.set(c, 2, c, LINTERNA)
    v.sitio("plazuela", 0, 0, 0, lado - 1, 8, lado - 1)


def ornamentar(v, u1, w1, u2, w2, y1, y2, paso=6, peto=True):
    """Articula una caja lisa sin tocar su estanqueidad: pilastras de cuarzo en esquinas y cada «paso», zócalo oscuro y
    peto almenado. Solo sustituye ladrillo de muro (respeta puertas, cristales y mecanismos)."""
    def muro(u, y, w):
        return v.built(u, y, w) == "minecraft:prismarine_bricks"
    for u in range(u1, u2 + 1):
        for w in range(w1, w2 + 1):
            if not (u in (u1, u2) or w in (w1, w2)):
                continue
            esquina = u in (u1, u2) and w in (w1, w2)
            a = (u - u1) if w in (w1, w2) else (w - w1)
            largo = (u2 - u1) if w in (w1, w2) else (w2 - w1)
            pilastra = esquina or (a % paso == 0 and 0 < a < largo)
            for y in range(y1 + 1, y2):
                if muro(u, y, w):
                    if pilastra:
                        v.set(u, y, w, CUARZO)
                    elif y == y1 + 1:
                        v.set(u, y, w, OSCURA)
            if peto and (pilastra or (a % 2 == 0)) and v.built(u, y2 + 1, w) is None:
                v.set(u, y2 + 1, w, OSCURA if not pilastra else CUARZO)


def ventanas(v, fijo, eje, a, b, y1, y2, paso=6):
    """Ventanas de cristal macizo de 2 de ancho en un muro (eje 'u': muro w = fijo, de u = a a b; eje 'w': muro u = fijo)."""
    for t in range(a + 3, b - 2, paso):
        for k in (0, 1):
            for y in range(y1, y2 + 1):
                u, w = (t + k, fijo) if eje == "u" else (fijo, t + k)
                if v.built(u, y, w) == "minecraft:prismarine_bricks":
                    v.set(u, y, w, CRISTAL)
