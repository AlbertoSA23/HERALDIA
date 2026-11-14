"""Piezas parametrizadas que comparten las estructuras únicas."""
from core import B, F


def door(t, x, y, z, facing, hinge="left", kind="spruce_door"):
    for half, dy in (("lower", 0), ("upper", 1)):
        t.set(x, y + dy, z, f"{kind}[facing={facing},half={half},hinge={hinge},open=false,powered=false]")


def hang(t, x, y, z, soul=False):
    """Farol colgado (pack.fix_supports añade la cadena hasta el techo si hace falta)."""
    t.set(x, y, z, f"{'soul_lantern' if soul else 'lantern'}[hanging=true,waterlogged=false]")


def chair(t, x, y, z, back, wood="spruce"):
    """Silla: el respaldo (lado alto de la escalera) mira hacia `back`."""
    t.set(x, y, z, f"{wood}_stairs[facing={back},half=bottom,shape=straight]")


def table(t, x, y, z, chairs=(), wood="spruce"):
    """Mesa de valla y placa; chairs = [(x, z, respaldo)]."""
    t.set(x, y, z, f"{wood}_fence")
    t.set(x, y + 1, z, f"{wood}_pressure_plate[powered=false]")
    for cx, cz, back in chairs:
        chair(t, cx, y, cz, back, wood)


def sign(t, x, y, z, facing, keys, lang, wood="spruce"):
    """Cartel de pared con hasta 4 líneas traducibles (claves de `lang`, con el español de fallback)."""
    msgs = [{"translate": k, "fallback": lang["es_es"][k]} if k else {"text": ""} for k in keys]
    msgs += [{"text": ""}] * (4 - len(msgs))
    side = lambda m: {"messages": m, "has_glowing_text": B(0), "color": "black"}
    t.set(x, y, z, f"{wood}_wall_sign[facing={facing},waterlogged=false]",
          {"id": "minecraft:sign", "is_waxed": B(1), "front_text": side(msgs), "back_text": side([{"text": ""}] * 4)})


def spawner(t, x, y, z, mob, **extra):
    """Generador de monstruos; `extra` añade campos del bloque (SpawnRange, Delay...)."""
    t.set(x, y, z, "spawner", {"id": "minecraft:mob_spawner", "SpawnData": {"entity": {"id": "minecraft:" + mob}}, **extra})


def guardian(mob, key, fallback, health, equipment, drops=None, **extra):
    """Guardián con nombre y persistente. equipment: {hueco: id o pila completa}; drops: {hueco: probabilidad}."""
    eq = {k: ({"id": "minecraft:" + v, "count": 1} if isinstance(v, str) else v) for k, v in equipment.items()}
    n = {"id": "minecraft:" + mob, "PersistenceRequired": B(1),
         "CustomName": {"translate": key, "fallback": fallback},
         "Health": F(float(health)), "attributes": [{"id": "minecraft:max_health", "base": float(health)}],
         "equipment": eq, "drop_chances": {k: F((drops or {}).get(k, 0.0)) for k in eq}}
    n.update(extra)
    return n


def dispenser(t, x, y, z, facing, item="arrow", count=9, stacks=1):
    """Dispensador cargado (trampas): `stacks` pilas de `count`."""
    t.set(x, y, z, f"dispenser[facing={facing},triggered=false]",
          {"id": "minecraft:dispenser",
           "Items": [{"Slot": B(s), "id": "minecraft:" + item, "count": count} for s in range(stacks)]})


def tripwire(t, a, b):
    """Cable trampa tenso entre dos ganchos enfrentados a y b (misma y, alineados en x o en z)."""
    (x0, y, z0), (x1, _, z1) = sorted([a, b])
    along_x = z0 == z1
    f0, f1 = ("east", "west") if along_x else ("south", "north")
    t.set(x0, y, z0, f"tripwire_hook[attached=true,facing={f0},powered=false]")
    t.set(x1, y, z1, f"tripwire_hook[attached=true,facing={f1},powered=false]")
    ew, ns = ("true", "false") if along_x else ("false", "true")
    for k in range(1, (x1 - x0 if along_x else z1 - z0)):
        x, z = (x0 + k, z0) if along_x else (x0, z0 + k)
        t.set(x, y, z, f"tripwire[attached=true,disarmed=false,east={ew},north={ns},powered=false,south={ns},west={ew}]")
