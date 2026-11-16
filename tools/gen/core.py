"""Núcleo: plantillas de estructura (NBT 26.3), jigsaws y entidades."""
import gzip, io, json, os, re
import nbtlib
from nbtlib import Compound, List, Int, String, Double, Byte, Float, File

DATA_VERSION = 5023          # Minecraft 26.3
NS = "heraldia"

_STATE_RE = re.compile(r"^([a-z0-9_:./]+)(?:\[(.*)\])?$")


def norm_id(i):
    return i if ":" in i else "minecraft:" + i


def parse_state(s):
    m = _STATE_RE.match(s.strip())
    if not m:
        raise ValueError("estado inválido: " + s)
    bid = norm_id(m.group(1))
    props = {}
    if m.group(2):
        for kv in m.group(2).split(","):
            k, v = kv.split("=")
            props[k.strip()] = v.strip()
    return bid, props


def state_str(bid, props):
    if not props:
        return bid
    return bid + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def with_props(s, **kw):
    bid, p = parse_state(s)
    p.update({k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in kw.items()})
    return state_str(bid, p)


# Direcciones
DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west", "up": "down", "down": "up"}
CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
CCW = {v: k for k, v in CW.items()}


class Template:
    def __init__(self, name):
        self.name = name          # ruta relativa: <tema>/houses/h1
        self.blocks = {}          # (x,y,z) -> (estado, nbt|None)
        self.entities = []        # (x,y,z, nbt dict)
        self.jigsaws = []         # info para el simulador
        self.min_size = (1, 1, 1)

    # --- bloques ---
    def set(self, x, y, z, state, nbt=None, keep=False):
        if state is None:
            return
        if keep and (x, y, z) in self.blocks and not self.blocks[(x, y, z)][0].startswith("minecraft:air"):
            return
        bid, props = parse_state(state)
        self.blocks[(x, y, z)] = (state_str(bid, props), nbt)

    def get(self, x, y, z):
        b = self.blocks.get((x, y, z))
        return b[0] if b else None

    def is_free(self, x, y, z):
        b = self.get(x, y, z)
        return b is None or b == "minecraft:air"

    def clear(self, x, y, z):
        self.blocks.pop((x, y, z), None)

    def fill(self, x1, y1, z1, x2, y2, z2, state, keep=False):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, state, keep=keep)

    def air(self, x1, y1, z1, x2, y2, z2):
        self.fill(x1, y1, z1, x2, y2, z2, "air")

    # --- bloques con entidad ---
    def chest(self, x, y, z, facing, loot, kind="chest"):
        st = f"{kind}[facing={facing}]"
        nbt = {"id": norm_id(kind), "LootTable": loot}
        self.set(x, y, z, st, nbt)

    def barrel(self, x, y, z, facing="up", loot=None):
        nbt = {"id": "minecraft:barrel"}
        if loot:
            nbt["LootTable"] = loot
        self.set(x, y, z, f"barrel[facing={facing}]", nbt)

    def jigsaw(self, x, y, z, orientation, name, target, pool, final_state="minecraft:air",
               joint="aligned", sel=0, place=0):
        fb, fp = parse_state(final_state)
        final_state = state_str(fb, fp)
        nbt = {"id": "minecraft:jigsaw", "name": nsid(name), "target": nsid(target),
               "pool": nsid(pool), "final_state": final_state, "joint": joint,
               "selection_priority": sel, "placement_priority": place}
        self.set(x, y, z, f"jigsaw[orientation={orientation}]", nbt)
        self.jigsaws.append(dict(pos=(x, y, z), orientation=orientation, name=nsid(name),
                                 target=nsid(target), pool=nsid(pool), joint=joint,
                                 sel=sel, place=place))

    def edge_jigsaw(self, side, along, y, name, target, pool, final_state="minecraft:structure_void", **kw):
        """Jigsaw horizontal en la cara exterior de la caja envolvente actual."""
        x0, y0, z0, x1, y1, z1 = self.bounds()
        pos = {"east": (x1, y, along), "west": (x0, y, along), "south": (along, y, z1), "north": (along, y, z0)}[side]
        self.jigsaw(*pos, f"{side}_up", name, target, pool, final_state=final_state, **kw)

    # --- entidades ---
    def entity(self, x, y, z, nbt):
        self.entities.append((x, y, z, nbt))

    # --- utilidades ---
    def bounds(self):
        xs = [p[0] for p in self.blocks] + [e[0] for e in self.entities]
        ys = [p[1] for p in self.blocks] + [e[1] for e in self.entities]
        zs = [p[2] for p in self.blocks] + [e[2] for e in self.entities]
        return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)

    def normalize(self):
        """Desplaza todo a coordenadas >= 0."""
        x0, y0, z0, *_ = self.bounds()
        if (x0, y0, z0) == (0, 0, 0):
            return
        self.blocks = {(x - x0, y - y0, z - z0): v for (x, y, z), v in self.blocks.items()}
        self.entities = [(x - x0, y - y0, z - z0, n) for x, y, z, n in self.entities]
        for j in self.jigsaws:
            x, y, z = j["pos"]
            j["pos"] = (x - x0, y - y0, z - z0)

    def size(self):
        x0, y0, z0, x1, y1, z1 = self.bounds()
        return (max(x1 + 1, self.min_size[0]), max(y1 + 1, self.min_size[1]), max(z1 + 1, self.min_size[2]))

    def to_nbt(self):
        x0, y0, z0, *_ = self.bounds()
        assert (x0, y0, z0) >= (0, 0, 0) and min(x0, y0, z0) >= 0, (self.name, x0, y0, z0)
        palette, index = [], {}
        blocks = []
        for pos in sorted(self.blocks, key=lambda p: (p[1], p[2], p[0])):
            st, nbt = self.blocks[pos]
            if st not in index:
                index[st] = len(palette)
                bid, props = parse_state(st)
                e = {"id": String(bid)}
                if props:
                    e["properties"] = Compound({k: String(v) for k, v in props.items()})
                palette.append(Compound(e))
            b = {"pos": List[Int]([Int(c) for c in pos]), "state": Int(index[st])}
            if nbt:
                b["nbt"] = to_tag(nbt)
            blocks.append(Compound(b))
        ents = []
        for x, y, z, n in self.entities:
            fx, fz = x + 0.5, z + 0.5
            n = dict(n)
            n.setdefault("Pos", [float(fx), float(y), float(fz)])
            ents.append(Compound({
                "pos": List[Double]([Double(fx), Double(y), Double(fz)]),
                "blockPos": List[Int]([Int(x), Int(y), Int(z)]),
                "nbt": to_tag(n)}))
        sx, sy, sz = self.size()
        root = Compound({
            "DataVersion": Int(DATA_VERSION),
            "size": List[Int]([Int(sx), Int(sy), Int(sz)]),
            "palette": List[Compound](palette),
            "blocks": List[Compound](blocks),
            "entities": List[Compound](ents),
        })
        return root

    def save(self, root_dir):
        path = os.path.join(root_dir, "data", NS, "structure", self.name + ".nbt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        f = File(self.to_nbt(), gzipped=True)
        f.save(path)
        return path


def nsid(s):
    if s.startswith("minecraft:") or ":" in s:
        return s
    return f"{NS}:{s}"


class B(int):
    """Marca un byte NBT."""


class F(float):
    """Marca un float NBT."""


def to_tag(v):
    if isinstance(v, nbtlib.tag.Base):      # cualquier etiqueta NBT ya construida (p. ej. IntArray)
        return v
    if isinstance(v, B):
        return Byte(int(v))
    if isinstance(v, bool):
        return Byte(1 if v else 0)
    if isinstance(v, F):
        return Float(float(v))
    if isinstance(v, int):
        return Int(v)
    if isinstance(v, float):
        return Double(v)
    if isinstance(v, str):
        return String(v)
    if isinstance(v, dict):
        return Compound({k: to_tag(x) for k, x in v.items()})
    if isinstance(v, list):
        if not v:
            return List([])
        tags = [to_tag(x) for x in v]
        return List[type(tags[0])](tags)
    raise TypeError(type(v))


# --- entidades comunes ---
# Los mobs de una plantilla pasan por finalizeSpawn al colocarse. El de los zombis sortea un bebé (5 %, con jinete de
# gallina) sin mirar el IsBaby del NBT: el mod (ZombieMixin) lo evita en los que llevan ADULTO_TAG, y validate.py exige
# la etiqueta en todo mob de BEBE_ZOMBI de las plantillas. Hoglin y zoglin salen bebés el 20 % sin remedio en el mod: no
# se pueden poner en plantillas. Los animales y aldeanos (AgeableMob) no: con un grupo nuevo el primero nunca es bebé.
ADULTO_TAG = "heraldia_adulto"
BEBE_ZOMBI = {"minecraft:" + m for m in ("zombie", "husk", "drowned", "zombie_villager", "zombified_piglin")}
BEBE_SIN_PROTECCION = {"minecraft:hoglin", "minecraft:zoglin"}


def adulto(n):
    """Pone ADULTO_TAG al NBT de un mob que podría salir bebé (BEBE_ZOMBI); devuelve el mismo NBT."""
    if n["id"] in BEBE_ZOMBI and ADULTO_TAG not in n.get("Tags", []):
        n["Tags"] = list(n.get("Tags", [])) + [ADULTO_TAG]
    return n


def villager(prof, vtype, employed=True):
    n = {"id": "minecraft:villager", "PersistenceRequired": B(1), "Tags": ["heraldia"],   # los tratos de mapas (mapas.py) la piden
         "VillagerData": {"profession": "minecraft:" + (prof if employed else "none"),
                          "level": 1, "type": "minecraft:" + vtype}}
    if employed:
        n["Xp"] = 1           # bloquea la profesión
    return n


def golem():
    return {"id": "minecraft:iron_golem", "PlayerCreated": B(0), "PersistenceRequired": B(1)}


def animal(kind, **extra):
    n = {"id": "minecraft:" + kind, "PersistenceRequired": B(1)}
    n.update(extra)
    return n


def center_marker(tags):
    return {"id": "minecraft:armor_stand", "Invisible": B(1), "Marker": B(1), "NoGravity": B(1),
            "Invulnerable": B(1), "Silent": B(1), "Tags": list(tags)}
