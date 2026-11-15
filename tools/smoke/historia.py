"""Crónica de los Heraldos en un servidor dedicado 26.3 real, con un jugador simulado (complementa server_smoke.py).

Uso: python3 tools/smoke/historia.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Lee del .jar (en la CI no hay build/generated) el pliego de cada estructura única (heraldia:historia/<id>), la tabla del
cofre que lo anida (heraldia:unicas/<id>/<cofre>) y el desafío heraldia:unicas/cronista, y comprueba:
  - sin servidor: la cadena es un solo ciclo que pasa por todas las únicas, la única final la cierra (señala la primera)
    y cada pliego viene con el mapa del tesoro de la única que señala;
  - en el servidor: `/loot spawn` de la tabla del cofre de cada única suelta un solo pliego con su custom_data, sus
    páginas traducibles (las de su relato y la que señala la siguiente) y su nombre traducible; el jugador simulado
    (Carpet, como trofeos.py) lo recoge y progresa el desafío, que solo se concede con el último.
"""
import argparse, json, os, queue, shutil, subprocess, sys, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomas import fetch
from trofeos import CARPET

PLAYER = "Testigo"          # el de trofeos.py (Carpet toma la grafía del perfil de Mojang)
X, Y, Z = 0, 101, 0            # jugador sobre una plataforma; los objetos a ITEM_DZ bloques (no los recoge solo)
ITEM_DZ = 6
ATTEMPTS, RETRY_S = 20, 0.5
ADV = "heraldia:unicas/cronista"
MARK = "heraldia_historia"


def chronicle(jar):
    """{id: {"cofre": tabla del cofre, "libro": componentes del pliego, "mapa": entrada del mapa, "siguiente": id}},
    textos en_us y el logro, leídos del .jar."""
    out = {}
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        lang = json.loads(z.read("assets/heraldia/lang/en_us.json"))
        pre = "data/heraldia/loot_table/historia/"
        for n in names:
            if n.startswith(pre) and n.endswith(".json"):
                sid = n[len(pre):-5]
                t = json.loads(z.read(n))
                book = t["pools"][0]["entries"][0]["modifier"][0]["components"]
                last = book["minecraft:written_book_content"]["pages"][-1]["raw"]
                nxt = last["with"][2]["translate"].split(".")[2]
                chest = [c for c in names if c.startswith(f"data/heraldia/loot_table/unicas/{sid}/") and
                         f'"heraldia:historia/{sid}"' in z.read(c).decode()]
                out[sid] = {"cofre": [c[len("data/heraldia/loot_table/"):-5] for c in chest], "libro": book,
                            "mapa": t["pools"][1]["entries"][0] if len(t["pools"]) > 1 else None, "siguiente": nxt,
                            "final": last["translate"] == "heraldia.historia.final"}
        adv = json.loads(z.read("data/heraldia/advancement/unicas/cronista.json"))
    return dict(sorted(out.items())), lang, adv


def static_checks(found, adv):
    fails = []
    if sorted(adv["criteria"]) != sorted(found) or len(adv["requirements"]) != len(found):
        fails.append(f"el desafío {ADV} no pide exactamente los {len(found)} pliegos: {sorted(adv['criteria'])}")
    finals = [sid for sid, d in found.items() if d["final"]]
    if len(finals) != 1:
        fails.append(f"debe haber un solo pliego final: {finals}")
    seen, sid = [], next(iter(found))
    while sid in found and sid not in seen:   # recorre la cadena desde cualquier pliego
        seen.append(sid)
        sid = found[sid]["siguiente"]
    if sorted(seen) != sorted(found):
        fails.append(f"la cadena no pasa por todas las únicas: {seen}")
    for sid, d in found.items():
        if len(d["cofre"]) != 1:
            fails.append(f"{sid}: el pliego debe ir en la tabla de un cofre de la única, no en {d['cofre']}")
        dest = ((d["mapa"] or {}).get("modifier") or [{}])[0].get("destination")
        if dest != f"#heraldia:unicas/{d['siguiente']}":
            fails.append(f"{sid}: el mapa del pliego no lleva a {d['siguiente']} ({dest})")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-historia"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    found, lang, adv = chronicle(a.jar)
    fails = static_checks(found, adv)
    ok = 0
    launcher = s.prepare(a.work, os.path.abspath(a.jar), s.gradle_properties())
    shutil.copy(fetch(a.work, *CARPET), os.path.join(a.work, "mods"))
    proc = subprocess.Popen(["java", "-Xmx2G", "-jar", launcher, "nogui"], cwd=a.work, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines, seen = queue.Queue(), []
    threading.Thread(target=s.reader, args=(proc, lines), daemon=True).start()
    ctx = s.Context(proc, lines, seen)

    def test(cmd):
        return "passed" in ctx.run(cmd, r"Test passed|Test failed").group(0)

    def until(cmd, want=True):
        for _ in range(ATTEMPTS):
            if test(cmd) == want:
                return True
            time.sleep(RETRY_S)
        return False

    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        for _ in range(s.PLACE_ATTEMPTS):
            m = ctx.run(f"fill {X - 3} {Y - 1} {Z - 3} {X + 3} {Y - 1} {Z + ITEM_DZ + 3} minecraft:stone", r"Successfully filled|No blocks")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        ctx.run(f"player {PLAYER} spawn at {X} {Y} {Z}", r"joined the game|Player .* spawn|Unknown|Incorrect")
        if not until(f"execute if entity @a[name={PLAYER}]"):
            raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
        ctx.run(f"gamemode survival {PLAYER}", r"Set .* game mode|game mode")
        iz = Z + ITEM_DZ
        for i, (sid, d) in enumerate(found.items()):
            mark = f'{{"minecraft:custom_data":{{{MARK}:"{sid}"}}}}'
            near = f"@e[type=minecraft:item,x={X},y={Y},z={iz},distance=..3,nbt={{Item:{{components:{mark}}}}}]"
            # 1) el cofre de la única (su tabla real) suelta un solo pliego
            ctx.run("kill @e[type=minecraft:item]", r"Killed|No entity was found")
            ctx.run(f"loot spawn {X} {Y} {iz} loot heraldia:{d['cofre'][0]}", r"Dropped|No ")
            if not until(f"execute if entity {near}"):
                fails.append(f"{sid}: el cofre heraldia:{d['cofre'][0]} no suelta su pliego")
                continue
            m = ctx.run(f"execute if entity {near}", r"Test passed\. Count: (\d+)|Test failed")
            if m.group(1) != "1":
                fails.append(f"{sid}: {m.group(1)} pliegos (debe ser 1)")
            # 2) sus páginas traducibles: las del relato y la que señala la siguiente, con su pista
            m = ctx.run(f"data get entity {near.replace(']', ',limit=1]')} Item", r"has the following entity data: (.*)|No entity")
            data = (m.group(1) or "").replace("\\", "")
            k = f"heraldia.historia.{sid}"
            want = ['id: "minecraft:written_book"', f'"{k}.pagina1"', f'"heraldia.historia.{d["siguiente"]}.pista"',
                    '"heraldia.historia.nombre"', 'author: "Ysolda"', f'{MARK}: "{sid}"']
            missing = [w for w in want if w not in data] + [t for t in (f"{k}.pagina1", f"{k}.pista") if t not in lang]
            if missing:
                fails.append(f"{sid}: pliego sin {missing}: {data[:300]}")
            else:
                ok += 1
            # 3) el jugador lo recoge: se ve con su nombre traducido (en_us del mod en el servidor) y cuenta para el
            #    desafío, que solo se concede con el último
            name = lang["heraldia.historia.nombre"] % lang[f"heraldia.unicas.{sid}.nombre"]
            m = ctx.run(f"tp {near} {PLAYER}", r"Teleported (.+) to |No entity")
            if m.group(1) != name:
                fails.append(f"{sid}: el pliego se ve como «{m.group(1)}», no «{name}»")
            if not until(f"execute if entity @a[name={PLAYER},advancements={{{ADV}={{{sid}=true}}}}]"):
                fails.append(f"{sid}: recogido, no cuenta para {ADV}")
            elif test(f"execute if entity @a[name={PLAYER},advancements={{{ADV}=true}}]") != (i == len(found) - 1):
                fails.append(f"{sid}: {ADV} concedido antes de tiempo o no concedido al final")
            else:
                ok += 1
            print(f"pliego {sid} (cofre {d['cofre'][0]}) -> {d['siguiente']}")
        ctx.run(f"player {PLAYER} kill", r"left the game|Unknown|Incorrect|.")
    finally:
        if proc.poll() is None:
            s.send(proc, "stop")
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
    log = os.path.join(a.work, "logs", "latest.log")
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else "".join(seen)
    for bad in ("Registry loading errors", "Failed to load datapacks", "Couldn't load", "Failed to parse",
                "Found validation problems"):
        if bad in text:
            fails.append(f"el log contiene {bad!r}")
    print("CRÓNICA:", f"OK ({len(found)} pliegos, {ok} comprobaciones)" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
