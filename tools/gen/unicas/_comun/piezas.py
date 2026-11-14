"""Piezas comunes y parametrizadas de las estructuras únicas: puerta de pistones enrasada, trampas de flechas,
generador, guardián con nombre y cofre (uso: from unicas._comun import piezas).

Todas reciben `put(x, y, z, estado, nbt=None)` (por ejemplo Template.set o un envoltorio con coordenadas propias)
y colocan estados ya estables al generarse (ver _comun/redstone.py para comprobarlo). Las que tienen mecanismo
devuelven un dict con sus posiciones y el estado "resuelto" (pos -> estado) para auditar el recorrido abierto.
Verificadas en un servidor dedicado 26.3 con tools/smoke/coliseo_redstone.py.
"""
from core import B, F

DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}


def _off(p, d, n=1, dy=0):
    x, y, z = p
    ax, az = DIRS[d]
    return (x + ax * n, y + dy, z + az * n)


def puerta_pistones(put, puerta, lado, cara, bloque, muro, antorcha_lado="minecraft:quartz_bricks"):
    """Puerta secreta de 1 x 2 enrasada en el fondo de un nicho, abierta por una palanca.

    puerta: posición del bloque inferior de la puerta (en el plano del muro, detrás del nicho).
    lado:   dirección hacia la que se recogen los bloques (dentro del muro, a lo largo de él).
    cara:   dirección hacia la sala desde la que se ve el nicho y se acciona la palanca.
    bloque: material de la puerta (empujable); muro: material del muro que oculta el mecanismo.
    Mecanismo: dos pistones pegajosos extendidos a dos bloques de la puerta, alimentados por una antorcha de
    redstone (en la cara oculta del bloque de la palanca) y por el bloque macizo de encima. Palanca encendida ->
    antorcha apagada -> los pistones recogen la puerta. El muro alrededor (plano de la puerta y capa de la sala,
    salvo el nicho) debe ser macizo y lo pone quien llama.
    """
    up = lambda p: (p[0], p[1] + 1, p[2])
    head = _off(puerta, lado)
    piston = _off(puerta, lado, 2)
    torch = _off(puerta, lado, 3)
    apoyo = _off(torch, cara)
    lever = _off(apoyo, cara)
    nicho = _off(puerta, cara)
    for p in (puerta, up(puerta)):
        put(*p, bloque)
    for p in (nicho, up(nicho)):
        put(*p, "minecraft:air")
    f = OPP[lado]
    for p in (head, up(head)):
        put(*p, f"minecraft:piston_head[facing={f},short=false,type=sticky]")
    for p in (piston, up(piston)):
        put(*p, f"minecraft:sticky_piston[extended=true,facing={f}]")
    put(*torch, f"minecraft:redstone_wall_torch[facing={OPP[cara]},lit=true]")
    put(*up(torch), muro)
    put(*apoyo, muro)
    put(*lever, f"minecraft:lever[face=wall,facing={cara},powered=false]")
    solved = {puerta: "minecraft:air", up(puerta): "minecraft:air", head: bloque, up(head): bloque,
              piston: f"minecraft:sticky_piston[extended=false,facing={f}]",
              up(piston): f"minecraft:sticky_piston[extended=false,facing={f}]",
              torch: f"minecraft:redstone_wall_torch[facing={OPP[cara]},lit=false]",
              lever: f"minecraft:lever[face=wall,facing={cara},powered=true]"}
    return dict(puerta=puerta, palanca=lever, antorcha=torch, apoyo=apoyo, piston=piston, nicho=nicho, solved=solved)


def dispensador(facing, flechas=8, objeto="minecraft:arrow"):
    return (f"minecraft:dispenser[facing={facing},triggered=false]",
            {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": objeto, "count": flechas}]})


def trampa_cable(put, gancho, hacia, largo, flechas=9):
    """Cable trampa de `largo` bloques entre dos ganchos (gancho: posición del primero, `hacia`: dirección al otro).
    Cada gancho activa el bloque al que está sujeto, y este el dispensador que tiene encima, que dispara al pasillo.
    Los dos bloques de sujeción deben ser macizos (los pone quien llama)."""
    g2 = _off(gancho, hacia, largo + 1)
    axis_ns = hacia in ("north", "south")
    put(*gancho, f"minecraft:tripwire_hook[attached=true,facing={hacia},powered=false]")
    put(*g2, f"minecraft:tripwire_hook[attached=true,facing={OPP[hacia]},powered=false]")
    for i in range(1, largo + 1):
        st = "north=true,south=true,east=false,west=false" if axis_ns else "north=false,south=false,east=true,west=true"
        put(*_off(gancho, hacia, i), f"minecraft:tripwire[attached=true,disarmed=false,{st},powered=false]")
    for g, d in ((gancho, OPP[hacia]), (g2, hacia)):
        a = _off(g, d)
        put(a[0], a[1] + 1, a[2], *dispensador(OPP[d], flechas))
    return dict(ganchos=(gancho, g2))


def trampa_placas(put, placas, lado, flechas=6, placa="minecraft:stone_pressure_plate"):
    """Placas de presión en el suelo; a cada lado (`lado` y su opuesto) un dispensador a ras de suelo que dispara
    a la placa vecina. Las placas necesitan suelo macizo debajo."""
    for p in placas:
        put(*p, f"{placa}[powered=false]")
        for d in (lado, OPP[lado]):
            put(*_off(p, d), *dispensador(OPP[d], flechas))
    return dict(placas=list(placas))


def generador(mob, rango=4, jugador=16, retraso=20):
    """(estado, nbt) de un generador de monstruos vanilla. Necesita luz de bloque 0 alrededor."""
    return "minecraft:spawner", {"id": "minecraft:mob_spawner", "SpawnData": {"entity": {"id": f"minecraft:{mob}"}},
                                 "SpawnRange": rango, "RequiredPlayerRange": jugador, "Delay": retraso}


def guardian(mob, clave, nombre, vida=40.0, equipo=None, caida=None, extra_atributos=None):
    """NBT de un guardián con nombre traducible (clave de idioma + respaldo en español), persistente y con
    atributos moderados. equipo: {ranura: objeto}; caida: {ranura: probabilidad} (0,05 por defecto)."""
    equipo = equipo or {}
    caida = caida or {}
    attrs = [{"id": "minecraft:max_health", "base": float(vida)}] + list(extra_atributos or [])
    return {"id": f"minecraft:{mob}", "PersistenceRequired": B(1), "CustomNameVisible": B(1),
            "CustomName": {"translate": clave, "fallback": nombre}, "Health": F(float(vida)), "attributes": attrs,
            "equipment": {k: {"id": f"minecraft:{v}", "count": 1} for k, v in equipo.items()},
            "drop_chances": {k: F(caida.get(k, 0.05)) for k in equipo}}


def cofre(tabla, facing, tipo="chest"):
    """(estado, nbt) de un cofre o barril con tabla de botín."""
    if tipo == "barrel":
        return f"minecraft:barrel[facing={facing}]", {"id": "minecraft:barrel", "LootTable": tabla}
    return f"minecraft:{tipo}[facing={facing}]", {"id": f"minecraft:{tipo}", "LootTable": tabla}


def marco(x, y, z, facing_byte, objeto=None):
    """NBT de un marco (entidad colgada): sin block_pos el juego lo descarta al colocar la plantilla."""
    n = {"id": "minecraft:item_frame", "Facing": B(facing_byte), "block_pos": [x, y, z]}
    if objeto:
        n["Item"] = {"id": f"minecraft:{objeto}", "count": 1}
    return n
