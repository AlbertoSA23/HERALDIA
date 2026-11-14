"""Piezas parametrizadas: escalera de caracol, generador, cofre, guardián con nombre y cuadro."""
from nbtlib import Compound, String, Byte, IntArray, Float, Int, List, Double

DIR = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}


def S(name, **p):
    """Estado de bloque con propiedades: S("chest", facing="north")."""
    if not p:
        return name
    return name + "[" + ",".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in p.items()) + "]"


def escalera_caracol(t, anillo, y0, n, material="spruce", apoyo="stripped_spruce_wood"):
    """n peldaños desde y0 recorriendo `anillo` (celdas contiguas alrededor de un machón, 8 por vuelta).
    Cada peldaño mira hacia donde se llega (así se entra siempre por el lado bajo, también en las esquinas), y los de
    esquina, que no tocan el machón, llevan un apoyo debajo para no quedar sueltos. Devuelve [(x, y, z)]."""
    out = []
    k = len(anillo)
    for i in range(n):
        x, z = anillo[i % k]
        px, pz = anillo[(i - 1) % k]
        t.set(x, y0 + i, z, S(material + "_stairs", facing=DIR[(x - px, z - pz)], half="bottom"))
        nx, nz = anillo[(i + 1) % k]
        if i and (nx - x, nz - z) != (x - px, z - pz) and apoyo:
            t.set(x, y0 + i - 1, z, apoyo)
        out.append((x, y0 + i, z))
    return out


def generador(mob, **extra):
    """NBT de un generador de monstruos (valores por defecto del juego salvo lo que se pase)."""
    e = {"entity": {"id": "minecraft:" + mob}}
    return dict({"id": "minecraft:mob_spawner", "SpawnData": e, "SpawnPotentials": [{"data": e, "weight": 1}]}, **extra)


def cofre(t, x, y, z, facing, loot, kind="chest"):
    """Cofre o barril con tabla de botín (id completo)."""
    if kind == "barrel":
        t.set(x, y, z, S("barrel", facing=facing, open=False), {"id": "minecraft:barrel", "LootTable": loot})
    else:
        t.set(x, y, z, S(kind, facing=facing, type="single", waterlogged=False), {"id": "minecraft:" + kind, "LootTable": loot})


def guardian(mob, key, fallback, salud=40.0, equipo=None, tag=None, color=None):
    """Mob con nombre traducible, persistente y sin soltar su equipo. `equipo`: {ranura: id} y `color` tiñe el cuero.
    Ojo: al colocarse pasa por finalizeSpawn y algunos mobs reciben su arma de vanilla (ver APRENDIZAJES)."""
    eq = {}
    for slot, iid in (equipo or {}).items():
        d = {"id": String("minecraft:" + iid), "count": Int(1)}
        if color is not None and iid.startswith("leather_"):
            d["components"] = Compound({"minecraft:dyed_color": Int(color)})
        eq[slot] = Compound(d)
    n = {"id": String("minecraft:" + mob), "PersistenceRequired": Byte(1), "CustomNameVisible": Byte(1),
         "CustomName": Compound({"translate": String(key), "fallback": String(fallback)}),
         "Health": Float(salud), "equipment": Compound(eq), "drop_chances": Compound({k: Float(0.0) for k in eq}),
         "attributes": List[Compound]([Compound({"id": String("minecraft:max_health"), "base": Double(salud)})])}
    if tag:
        n["Tags"] = List[String]([String(tag)])
    return Compound(n)


def cuadro(x, y, z, facing, variante):
    """Cuadro para Template.entity: facing en código 2D y block_pos como IntArray (verificado en 26.3)."""
    f2d = {"south": 0, "west": 1, "north": 2, "east": 3}[facing]
    return Compound({"id": String("minecraft:painting"), "variant": String("minecraft:" + variante),
                     "facing": Byte(f2d), "block_pos": IntArray([x, y, z])})
