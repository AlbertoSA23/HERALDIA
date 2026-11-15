"""Trofeos de los guardianes en un servidor dedicado 26.3 real, con un jugador simulado (complementa server_smoke.py).

Uso: python3 tools/smoke/trofeos.py --jar build/libs/heraldia-X.jar --work "$PWD/build/smoke"
Sin cliente no hay jugadores y la condición killed_by_player no se cumple nunca desde la consola: esta prueba añade
Carpet (versión fijada de Modrinth, comprobada con su sha512) y crea con /player un jugador simulado. Para cada
guardián (tablas heraldia:guardianes/<id>/<mob> del .jar) invoca su tipo de mob con esa DeathLootTable y:
  - lo mata con /kill (sin jugador): no cae el trofeo;
  - lo mata el jugador (damage ... by <jugador>): cae un solo trofeo con su custom_data, su nombre traducible, su lore
    y su rareza;
  - el jugador lo recoge: progresa el desafío heraldia:unicas/trofeos, que solo se concede con todos.
Que el guardián colocado con /place structure conserve esa DeathLootTable lo comprueba server_smoke.py.
"""
import argparse, json, os, queue, shutil, subprocess, sys, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s
from terralith_biomas import fetch

CARPET = ("fabric-carpet-26.3+v260915.jar",
          "https://cdn.modrinth.com/data/TQTTVgYE/versions/yt9oDFOj/fabric-carpet-26.3%2Bv260915.jar",
          "7a479ba69eb5049cb94365d5044bd58c9f970c50b3484861fe3675f1917f7c99c1b1f50a5e01bdd9ded940d76a995539009a3656e05be2f513f20ec14de991a7")
PLAYER = "Testigo"
X, Y, Z = 0, 101, 0            # jugador sobre una plataforma; los mobs a MOB_DZ bloques (no recoge lo que cae)
MOB_DZ = 6
ATTEMPTS, RETRY_S = 20, 0.5
ADV = "heraldia:unicas/trofeos"
ITEMS = "@e[type=minecraft:item]"


def trophies(jar):
    """{id: (mob, tabla de muerte, objeto, rareza)} y textos en_us, leídos del .jar (en la CI no hay build/generated)."""
    out = {}
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        lang = json.loads(z.read("assets/heraldia/lang/en_us.json"))
        for n in names:
            pre = "data/heraldia/loot_table/guardianes/"
            if n.startswith(pre) and n.endswith(".json"):
                sid, mob = n[len(pre):-5].split("/")
                trophy = json.loads(z.read(f"data/heraldia/loot_table/trofeos/{sid}.json"))
                entry = trophy["pools"][0]["entries"][0]
                rarity = next(m["components"]["minecraft:rarity"] for m in entry["modifier"] if m["type"].endswith("set_components"))
                out[sid] = (mob, f"heraldia:guardianes/{sid}/{mob}", entry["name"], rarity)
        adv = json.loads(z.read("data/heraldia/advancement/unicas/trofeos.json"))
    return dict(sorted(out.items())), lang, adv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--work", default=os.path.join(s.ROOT, "build", "smoke-trofeos"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    found, lang, adv = trophies(a.jar)
    fails, ok = [], 0
    if sorted(adv["criteria"]) != sorted(found) or len(adv["requirements"]) != len(found):
        fails.append(f"el desafío {ADV} no pide exactamente los {len(found)} trofeos: {sorted(adv['criteria'])}")
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

    def settle():
        """El jugador, en el suelo, sin golpe reciente y de vuelta en (X, Y, Z): ya no se desliza ni vuela."""
        quiet = f"execute if entity @a[name={PLAYER},nbt={{OnGround:1b,HurtTime:0s}}]"
        if not until(quiet):
            return False
        ctx.run(f"tp {PLAYER} {X + 0.5} {Y} {Z + 0.5}", r"Teleported")
        return until(f"execute if entity @a[name={PLAYER},x={X + 0.5},y={Y},z={Z + 0.5},distance=..0.01]") and until(quiet)

    try:
        s.wait_for(lines, r"Heraldia: (\d+) estructuras registradas", s.START_TIMEOUT_S, seen)
        ctx.run(f"forceload add {X} {Z}", r"Marked|force|already")
        for _ in range(s.PLACE_ATTEMPTS):
            m = ctx.run(f"fill {X - 3} {Y - 1} {Z - 3} {X + 3} {Y - 1} {Z + MOB_DZ + 3} minecraft:stone", r"Successfully filled|No blocks")
            if "not loaded" not in m.string:
                break
            time.sleep(s.PLACE_RETRY_S)
        ctx.run(f"player {PLAYER} spawn at {X} {Y} {Z}", r"joined the game|Player .* spawn|Unknown|Incorrect")
        if not until(f"execute if entity @a[name={PLAYER}]"):
            raise SystemExit(f"no aparece el jugador simulado {PLAYER} (Carpet)")
        ctx.run(f"gamemode survival {PLAYER}", r"Set .* game mode|game mode")
        mz = Z + MOB_DZ
        for i, (sid, (mob, table, item, rarity)) in enumerate(found.items()):
            mark = f'{{"minecraft:custom_data":{{heraldia_trofeo:"{sid}"}}}}'
            near = f"@e[type=minecraft:item,x={X},y={Y},z={mz},distance=..3,nbt={{Item:{{components:{mark}}}}}]"
            summon = (f'summon minecraft:{mob} {X} {Y} {mz} {{NoAI:1b,PersistenceRequired:1b,Tags:["heraldia_prueba"],'
                      f'DeathLootTable:"{table}"}}')
            # 1) sin jugador: /kill no suelta el trofeo
            ctx.run(f"kill {ITEMS}", r"Killed|No entity was found")
            ctx.run(summon, r"Summoned")
            ctx.run("kill @e[tag=heraldia_prueba]", r"Killed|No entity was found")
            time.sleep(1)
            if test(f"execute if entity {near}"):
                fails.append(f"{sid}: /kill (sin jugador) suelta el trofeo")
            else:
                ok += 1
            # 2) lo mata el jugador: un solo trofeo con su nombre, lore, rareza y custom_data
            ctx.run(f"kill {ITEMS}", r"Killed|No entity was found")
            ctx.run(summon, r"Summoned")
            ctx.run(f"damage @e[tag=heraldia_prueba,limit=1] 2000 minecraft:player_attack by {PLAYER}", r"Applied|damage")
            if not until(f"execute if entity {near}"):
                fails.append(f"{sid}: matado por el jugador no suelta el trofeo")
                continue
            m = ctx.run(f"execute if entity {near}", r"Test passed\. Count: (\d+)|Test failed")
            if m.group(1) != "1":
                fails.append(f"{sid}: {m.group(1)} trofeos en el suelo (debe ser 1)")
            m = ctx.run(f"data get entity {near.replace(']', ',limit=1]')} Item", r"has the following entity data: (.*)|No entity")
            data = (m.group(1) or "").replace("\\", "")
            key = f"heraldia.trofeo.{sid}"
            want = [f'id: "{item}"', f'"{key}"', f'"{key}.lore1"', 'heraldia_trofeo: "' + sid]
            missing = [w for w in want if w not in data]
            # la rareza se mira en los componentes efectivos (si es la de serie del objeto no sale en los datos)
            if not test(f'execute if items entity {near.replace("]", ",limit=1]")} contents {item}[minecraft:rarity="{rarity}"]'):
                missing.append(f"rareza {rarity}")
            if missing or key not in lang:
                fails.append(f"{sid}: trofeo sin {missing or 'texto en_us'}: {data[:300]}")
            else:
                ok += 1
            # 3) el jugador lo recoge (el mensaje de /tp muestra el nombre que ve el jugador: item_name en en_us) y el
            #    desafío solo se concede con el último trofeo
            # Las espinas del guardián anciano (Guardian.hurtServer: 2 de daño al atacante cuerpo a cuerpo si no se
            # mueve, siempre con NoAI) empujan al jugador ~2 bloques: antes de acercarle el trofeo, se espera a que
            # aterrice y pase su invulnerabilidad (HurtTime 0) y se le devuelve a su sitio, quieto.
            if not settle():
                fails.append(f"{sid}: el jugador no queda quieto tras el golpe")
                continue
            m = ctx.run(f"tp {near} {PLAYER}", r"Teleported (.+) to |No entity")
            if m.group(1) != lang.get(key):
                fails.append(f"{sid}: el trofeo se ve como «{m.group(1)}», no «{lang.get(key)}»")
            if not until(f"execute if entity @a[name={PLAYER},advancements={{{ADV}={{{sid}=true}}}}]"):
                fails.append(f"{sid}: recogido, no cuenta para {ADV}")
                mark_sel = f"@e[type=minecraft:item,nbt={{Item:{{components:{mark}}}}},limit=1]"
                for q in (f"data get entity {mark_sel}", f"data get entity {PLAYER} Pos", f"data get entity {PLAYER} Inventory",
                          f"data get entity {PLAYER} Health"):
                    print("DIAG", ctx.run(q, r"entity data: .*|No entity").group(0)[:300])
            elif test(f"execute if entity @a[name={PLAYER},advancements={{{ADV}=true}}]") != (i == len(found) - 1):
                fails.append(f"{sid}: {ADV} concedido antes de tiempo o no concedido al final")
            else:
                ok += 1
            print(f"trofeo {sid}: {lang.get(f'heraldia.trofeo.{sid}')} ({item}, {mob})")
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
    print("TROFEOS:", f"OK ({len(found)} trofeos, {ok} comprobaciones)" if not fails else fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
