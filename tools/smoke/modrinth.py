"""Mods de Modrinth de las pruebas de servidor: versión fijada para Minecraft 26.3 + Fabric y sha512 de cada .jar.

No es una prueba (tools/test.py la excluye de la batería): lo importan trofeos.py (Carpet), terralith_biomas.py y
compat_mods.py. Cada .jar se descarga una vez en <work>/modrinth/ (la CI guarda esa carpeta en caché) y se comprueba su
sha512 antes de usarlo: una descarga distinta de la fijada hace fallar la prueba, no la cambia por otra.

Uso para mantener la lista (consulta la API de Modrinth, no descarga nada):
  python3 tools/smoke/modrinth.py --comprobar          # ¿hay versiones 26.3 + Fabric más nuevas que las fijadas?
  python3 tools/smoke/modrinth.py --buscar <slug>...   # versión 26.3 + Fabric más reciente de esos proyectos
"""
import argparse, collections, hashlib, json, os, shutil, sys, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_smoke as s

API = "https://api.modrinth.com/v2"
MC, LOADER = "26.3", "fabric"
CARPETA = "modrinth"

Mod = collections.namedtuple("Mod", "slug version file url sha512")

# Versiones fijadas (las publicadas en Modrinth para 26.3 + Fabric al escribir la prueba). Para cambiar una, usa
# --buscar y copia versión, fichero, url y sha512; la caché de la CI cambia sola (su clave es el hash de este fichero).
MODS = {m.slug: m for m in [
    # prueba de jugador simulado (trofeos, historia, aldeas_vida)
    Mod("carpet", "26.3+v260915", "fabric-carpet-26.3+v260915.jar",
        "https://cdn.modrinth.com/data/TQTTVgYE/versions/yt9oDFOj/fabric-carpet-26.3%2Bv260915.jar",
        "7a479ba69eb5049cb94365d5044bd58c9f970c50b3484861fe3675f1917f7c99c1b1f50a5e01bdd9ded940d76a995539009a3656e05be2f513f20ec14de991a7"),
    # terreno y biomas
    Mod("terralith", "2.6.5+26.3", "Terralith_26.3_v2.6.5+26.3.jar",
        "https://cdn.modrinth.com/data/8oi3bsk5/versions/aGE3hYAA/Terralith_26.3_v2.6.5%2B26.3.jar",
        "918b232df7a855bae89c7fa85affb5ce134e236c4726fa14a5bdaa179eb1e010f040a9fa981f006a0e26e421a2a961bc29a75e99a4500fd18361a8ba81478071"),
    Mod("lithostitched", "2.0.6-fabric-26.3", "lithostitched-2.0.6-fabric-26.3.jar",
        "https://cdn.modrinth.com/data/XaDC71GB/versions/pZgI6b2t/lithostitched-2.0.6-fabric-26.3.jar",
        "d7ffe9bb3ea653ae70317f8621c546e3331369c0dd3cd6cadb374cc71283ca1fae1e7de7d2d16eb5724e96f7159c8b043e15a618f32dad88c8e70a7d8d1db4ee"),
    Mod("tectonic", "3.1.0+beta2-fabric-26.3", "tectonic-3.1.0+beta2-fabric-26.3.jar",
        "https://cdn.modrinth.com/data/lWDHr9jE/versions/rKBGygwM/tectonic-3.1.0%2Bbeta2-fabric-26.3.jar",
        "e91888863558781746b3708809ae09e67c14bec6cfefd633f1c9eaf2d19ad7dc9a4bcbab6ff25024e33741e8af51579ca0accbd92df66beb855060934f4820dc"),
    Mod("biomes-o-plenty", "26.3.0.0.16", "BiomesOPlenty-fabric-26.3-26.3.0.0.16.jar",
        "https://cdn.modrinth.com/data/HXF82T3G/versions/sbAVJ5Mn/BiomesOPlenty-fabric-26.3-26.3.0.0.16.jar",
        "e58e1eab4e16498fb36c685b5d5a9ca12ad3cc2c75a35e051a61993137e5e862a457f06a2b47488f37256fb1ebb9175ff3e5c39b3ef1711e897d63e292035d2c"),
    Mod("glitchcore", "26.3.0.0.5", "GlitchCore-fabric-26.3-26.3.0.0.5.jar",
        "https://cdn.modrinth.com/data/s3dmwKy5/versions/kfFeDnrp/GlitchCore-fabric-26.3-26.3.0.0.5.jar",
        "f975535e561285898163e7512008fe61ffaac66b6fc60a4e4763d0f2279617f75900d7a2ab2708d8dc348337119df61d2783aa101a9f1a24020f99888aa0d457"),
    Mod("terrablender", "26.3.0.0.9", "TerraBlender-fabric-26.3-26.3.0.0.9.jar",
        "https://cdn.modrinth.com/data/kkmrDlKT/versions/xirJYe1V/TerraBlender-fabric-26.3-26.3.0.0.9.jar",
        "183f809fe992aaaaf4d84c594730b95b392338caf17b690debbb14434b23b46f5923cfcc5aecb81368ea06a299503a3738dcf942b7f179abd000f1312cf2cbdb"),
    Mod("wwoo", "3.0.1", "wwoo-fabric-26.3-3.0.1.jar",
        "https://cdn.modrinth.com/data/II7t6llZ/versions/23VeM3qz/wwoo-fabric-26.3-3.0.1.jar",
        "7e5aa11034a6ded04ece168c031753b3e464a55835b73fd46815fb2833b2d541cf362d5d0dc384f89dc8dc5afe7fbb7848d264c42928fb865a48f4e6b233cc4f"),
    Mod("cristel-lib", "fabric-26.3-3.1.13", "cristellib-fabric-26.3-3.1.13.jar",
        "https://cdn.modrinth.com/data/cl223EMc/versions/rWxmPrGC/cristellib-fabric-26.3-3.1.13.jar",
        "96198dfc067ce7003cad9b211286e58e36efcaa29729af3c09c643d3e8bd8a54e5814eb8d88680a38caf9e6328a541151b6c6b1bd9ac117d9c7278d93d6de88c"),
    Mod("cloth-config", "26.3.159+fabric", "cloth-config-fabric-26.3.159.jar",
        "https://cdn.modrinth.com/data/9s6osm5g/versions/fg2uyxOW/cloth-config-fabric-26.3.159.jar",
        "8924e19d41845096724fa10f3717bc51964a0edbbbcad0ff1e6c6187a398b08f356e49579a657c2dc44a7f92e3850771f3ca70bf8c1f654de60425163b91dbb1"),
    # estructuras
    Mod("dungeons-and-taverns", "6.1.0+mod", "dungeons-and-taverns-6.1.0.jar",
        "https://cdn.modrinth.com/data/tpehi7ww/versions/hn5CugpP/dungeons-and-taverns-6.1.0.jar",
        "b143a1780d8eda2b548307f6cbd22b9e8b7a8b34e7f65de63179c94331ce875d72a2bdc0e01b885cfdeb09c13f215dfb8016d00f4511270ba9dd3c0744fcff9e"),
    Mod("towns-and-towers", "1.13.13", "t_and_t-fabric-neoforge-1.13.13.jar",
        "https://cdn.modrinth.com/data/DjLobEOy/versions/vHZIKy6e/t_and_t-fabric-neoforge-1.13.13.jar",
        "bd0469d23a80d1bbbb0a3696b3c1a62f90cc5ad16e4cc58fe9e0e08e7453c3015ff7619b1d429106a034279b46fe909a0962b6dc9e970920f717fc518d9e292d"),
    Mod("structory", "1.3.18+26.3", "Structory_26.3_v1.3.18+26.3.jar",
        "https://cdn.modrinth.com/data/aKCwCJlY/versions/GjOkOVW4/Structory_26.3_v1.3.18%2B26.3.jar",
        "a9b7c7ce45a38c4be68563337e413adbf486a8e47fecc450d3ee59dadf807faee39d49a098c2dbfc2a466f0d36c71ca8e051f161efdbfc19b069f0c70e6b4223"),
    Mod("structory-towers", "1.0.19+26.3", "Structory_Towers_26.3_v1.0.19+26.3.jar",
        "https://cdn.modrinth.com/data/j3FONRYr/versions/5ntmnN83/Structory_Towers_26.3_v1.0.19%2B26.3.jar",
        "d3e3ddeb9a4f93e1b30ebfe0756ddcc2aa87cea24568104df90fc65274dcc5eba19255a0385b7d90e201191ae4105368d7bd77307a50bfd73cd356f0f8b5e15a"),
    Mod("explorify", "v1.6.6", "Explorify v1.6.6.mod.jar",
        "https://cdn.modrinth.com/data/HSfsxuTo/versions/oyrAnNG8/Explorify%20v1.6.6.mod.jar",
        "d4368c83b493c6fcf9b489cd91b4d1e468d695d099d9df3845a6fcee07ef58dc35074557d0108627b98c9941b1e6a6c0bcdbbcd121e8915514a21b91e9d38530"),
    # rendimiento y generación
    Mod("lithium", "mc26.3-0.26.3-fabric", "lithium-fabric-0.26.3+mc26.3.jar",
        "https://cdn.modrinth.com/data/gvQqBUqZ/versions/fWv5bnZk/lithium-fabric-0.26.3%2Bmc26.3.jar",
        "2ca92fb530135d2baddf0ba4cc4f93976234876a38c4aa02b487b2552400f005afcfbeebf5373fb4396fe2020537a42d7597b8da5a52b904355ef51d5fef07ad"),
    Mod("c2me-fabric", "0.4.2-alpha.0.119+26.3", "c2me-fabric-mc26.3-0.4.2-alpha.0.119.jar",
        "https://cdn.modrinth.com/data/VSNURh3q/versions/W9HllAiU/c2me-fabric-mc26.3-0.4.2-alpha.0.119.jar",
        "ba50c585ac92588bbe40ed77d2bdac3c22bc2a543165feebe19684730479da52fa8e5bffaebe8801b90d8f7616fd57703b2f2b447807a65061919fb86f887821"),
    Mod("ferrite-core", "9.0.0-fabric", "ferritecore-9.0.0-fabric.jar",
        "https://cdn.modrinth.com/data/uXXizFIs/versions/d5ddUdiB/ferritecore-9.0.0-fabric.jar",
        "d81fa97e11784c19d42f89c2f433831d007603dd7193cee45fa177e4a6a9c52b384b198586e04a0f7f63cd996fed713322578bde9a8db57e1188854ae5cbe584"),
    Mod("scalablelux", "0.3.0-alpha.0.6+26.3", "ScalableLux-fabric-mc26.3-0.3.0-alpha.0.6-all.jar",
        "https://cdn.modrinth.com/data/Ps1zyz6x/versions/g4eqNSKd/ScalableLux-fabric-mc26.3-0.3.0-alpha.0.6-all.jar",
        "ded5a939fb20ab81c1f33b147ca9b98050773dbb28dff16df939c7d567b626809522994ec8dbfb99e7f498dc6a4e62f25e141a87d18efb43f73fc5ad1569ccc9"),
    Mod("chunky", "1.5.66", "Chunky-Fabric-1.5.66.jar",
        "https://cdn.modrinth.com/data/fALzjamp/versions/86FKD9qx/Chunky-Fabric-1.5.66.jar",
        "6f0323daa69d61bd3b3fbe9d8b713664d9b7c69182183f8dcff6362b43783639778a96e32215dbfd329588f06b60a5d93656dbb1d391c660db203482aa972d5e"),
    # servidor: botín por jugador, Distant Horizons y mapas
    Mod("lootr", "1.25.42.124", "lootr-fabric-26.3-1.25.42.124.jar",
        "https://cdn.modrinth.com/data/EltpO5cN/versions/gVwn7m2v/lootr-fabric-26.3-1.25.42.124.jar",
        "290786fd4af4011c4f09c425d262bacc80f6ef47e23fbf6424193c719b6045a70cae70308c95d30c5ab78bf1f5a3d089cc3b01db8cc4dacc1a74c0f2d70c245d"),
    Mod("distanthorizons", "3.3.4-26.3", "DistantHorizons-3.3.4-26.3-fabric-neoforge.jar",
        "https://cdn.modrinth.com/data/uCdwusMi/versions/TGgEbP9A/DistantHorizons-3.3.4-26.3-fabric-neoforge.jar",
        "0b90b1b08d99974bfc3c8e86b2ceb252e2f91715ed66b925004c28335fb44e1bddbbb6b8043e4d4d53c87ed247789cd1788b1ba4e3f4394efe154e0c59cff236"),
    Mod("xaeros-minimap", "fabric-26.3-26.6.2", "xaerominimap-fabric-26.3-26.6.2.jar",
        "https://cdn.modrinth.com/data/1bokaNcj/versions/MfxfgXaO/xaerominimap-fabric-26.3-26.6.2.jar",
        "edf57b80cfe0e0fe229728a6babc3b25c364c07a0406bcdb3a21f73fc225b98954c68ff456c7b1af3182c48512f29d47238ddc501dbfd5eaca0a4609fddcc280"),
    Mod("xaeros-world-map", "fabric-26.3-1.47.2", "xaeroworldmap-fabric-26.3-1.47.2.jar",
        "https://cdn.modrinth.com/data/NcUtCpym/versions/VM8lNSSM/xaeroworldmap-fabric-26.3-1.47.2.jar",
        "cac3c0fb3121ddebc7f073571dcbce5f1811ca001ea94ef03c1da667e8a3413144f570c4b593f632358eff98fa138631ed7907fd1bd5da7d43c037ea782125fb"),
    Mod("journeymap", "26.3-6.0.10+fabric", "journeymap-fabric-26.3-6.0.10.jar",
        "https://cdn.modrinth.com/data/lfHFW1mp/versions/2zmj8ela/journeymap-fabric-26.3-6.0.10.jar",
        "d461b24b3eeaf74ecc75911542cfbfeefe7148a2a260453f15af047d1a895f6484b8e21816de990dc25987d747cc1cccdd5386e8c51a5dcc72a1356b39139bf2"),
]}

# Pedidos por Alberto que no tienen versión para 26.3 + Fabric en Modrinth (comprobado con --buscar el 16-11-2026);
# la tabla de compatibilidad del README los da por «no probado». Se vuelven a mirar con --comprobar.
SIN_VERSION = ["oh-the-biomes-weve-gone", "yungs-api", "yungs-better-dungeons", "yungs-better-mineshafts",
               "yungs-better-strongholds", "yungs-better-ocean-monuments", "yungs-better-desert-temples",
               "yungs-better-jungle-temples", "yungs-better-witch-huts", "yungs-bridges", "yungs-extras",
               "modernfix", "starlight", "noisium", "noisiumforked"]


def sha512(path):
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(work, name, url, sha):
    """Ruta del .jar `name` en <work>/modrinth/, descargado si falta; falla si su sha512 no es el fijado."""
    folder = os.path.join(work, CARPETA)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    for intento in range(2):      # una copia vieja en caché con otro contenido se descarga otra vez
        s.download(url, path)
        got = sha512(path)
        if got == sha:
            return path
        os.remove(path)
    raise SystemExit(f"{name}: sha512 distinto ({got[:16]}...); descarga incorrecta")


def jar(work, slug):
    m = MODS[slug]
    return fetch(work, m.file, m.url, m.sha512)


def instalar(work, slugs):
    """Copia a <work>/mods los .jar de esos proyectos (descargados y comprobados)."""
    for slug in slugs:
        shutil.copy(jar(work, slug), os.path.join(work, "mods"))


def _api(path, **query):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode({k: json.dumps(v) for k, v in query.items()}) if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": "heraldia-pruebas"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def ultima(slug):
    """Mod con la versión 26.3 + Fabric más reciente del proyecto, o None si no hay ninguna."""
    versions = _api(f"project/{slug}/version", game_versions=[MC], loaders=[LOADER])
    if not versions:
        return None
    v = versions[0]
    f = next((x for x in v["files"] if x["primary"]), v["files"][0])
    return Mod(slug, v["version_number"], f["filename"], f["url"], f["hashes"]["sha512"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--comprobar", action="store_true", help="compara las fijadas con las más recientes de Modrinth")
    g.add_argument("--buscar", nargs="+", metavar="SLUG", help="versión 26.3 + Fabric más reciente de esos proyectos")
    a = ap.parse_args(argv)
    for slug in a.buscar or list(MODS) + SIN_VERSION:
        m = ultima(slug)
        fijada = MODS.get(slug)
        if a.buscar:
            print(f"{slug}: sin versión {MC} + {LOADER}" if m is None else
                  f'    Mod("{m.slug}", "{m.version}", "{m.file}",\n        "{m.url}",\n        "{m.sha512}"),')
        elif m is None:
            print(f"{slug}: sin versión {MC} + {LOADER}" + (" (¡la fijada ya no está!)" if fijada else ""))
        elif fijada is None:
            print(f"{slug}: ahora tiene {m.version} (antes sin versión)")
        else:
            print(f"{slug}: {'al día' if m.version == fijada.version else f'fijada {fijada.version}, nueva {m.version}'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
