"""Idiomas del mod: es_es y en_us salen de los módulos (tuplas (es, en) y diccionarios LANG); los demás, de las
traducciones de tools/gen/idiomas/<código>.json ({clave: texto}).

Fuente única de las claves: el es_es que arma el generador (writer.textos). Cada traducción debe tener exactamente esas
claves (ni una de más ni de menos), los mismos huecos de formato que el inglés (%s, %1$s, %%: los mismos argumentos, en
el orden que pida la frase) y caber en las páginas de libro donde se usa (botin.lineas_libro). Si algo falla, la
generación se detiene (writer.write) y los tests lo dicen (tests/test_idiomas.py).

Clientes sin el mod (Textos.idioma en Java): heraldia/idiomas.json dice qué código del .jar corresponde a cada lengua de
Minecraft (la parte antes de «_»: fr_ca -> fr_fr, pt_pt -> pt_br, es_mx -> es_es); una lengua sin idioma propio, inglés.

Para comprobar una traducción a mano (tras generar con ./gradlew build): python3 tools/gen/idiomas.py fr_fr
"""
import json
import os
import re
import sys

BASE = ("es_es", "en_us")
# código del .jar -> nombre del idioma (en su lengua). El orden es el de los README y de /heraldia info.
TRADUCCIONES = {
    "fr_fr": "Français",
    "de_de": "Deutsch",
    "it_it": "Italiano",
    "pt_br": "Português (Brasil)",
    "ca_es": "Català",
    "gl_es": "Galego",
}
NOMBRES = {"en_us": "English", "es_es": "Español", **TRADUCCIONES}
# README homólogo de cada idioma en el repositorio (el inglés es el principal); tests/test_readme.py los mantiene
# sincronizados y con el selector de idiomas, en este orden.
README = {"en_us": "README.md", "es_es": "README.es.md", "fr_fr": "README.fr.md", "de_de": "README.de.md",
          "it_it": "README.it.md", "pt_br": "README.pt-BR.md", "ca_es": "README.ca.md", "gl_es": "README.gl.md"}
# Lenguas de Minecraft cuyo código no empieza por la de su idioma en el mod: valenciano (val_es) y andaluz (esan).
ALIAS = {"val": "ca_es", "esan": "es_es"}
CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idiomas")
RELLENO = "X" * 24        # texto de un traducible que no es del mod (p. ej. el nombre vanilla de un objeto): peor caso

_MARCA = re.compile(r"%(?:(\d+)\$)?([a-zA-Z%])")


def todos():
    """Todos los códigos de idioma del mod, los base primero."""
    return list(BASE) + list(TRADUCCIONES)


def lengua(codigo):
    return codigo.split("_", 1)[0]


def lenguas():
    """{lengua: código del .jar} para heraldia/idiomas.json (lo lee Textos.codigo en Java)."""
    out = {lengua(c): c for c in todos()}
    out.update(ALIAS)
    return out


def ruta(codigo):
    return os.path.join(CARPETA, f"{codigo}.json")


def cargar(codigo):
    """{clave: texto} de una traducción (tools/gen/idiomas/<código>.json); {} si aún no existe."""
    if not os.path.exists(ruta(codigo)):
        return {}
    with open(ruta(codigo), encoding="utf-8") as f:
        return json.load(f)


def marcadores(texto):
    """Argumentos que usa un texto de formato de Minecraft (TranslatableContents): ([índices 1..n], nº de %%) o
    None si tiene un marcador que el juego no entiende (solo %s, %n$s y %%)."""
    indices, literales, siguiente = [], 0, 1
    for m in _MARCA.finditer(texto):
        pos, tipo = m.groups()
        if tipo == "%":
            literales += 1
        elif tipo != "s":
            return None
        elif pos:
            indices.append(int(pos))
        else:
            indices.append(siguiente)
            siguiente += 1
    return sorted(indices), literales


def errores_claves(base, trad, codigo):
    """Claves que faltan o sobran en la traducción `trad` frente a `base` (el es_es)."""
    e = [f"{codigo}: falta la clave {k}" for k in base if k not in trad]
    e += [f"{codigo}: sobra la clave {k}" for k in trad if k not in base]
    e += [f"{codigo}: {k} está vacía" for k, v in trad.items() if k in base and not str(v).strip()]
    return e


def errores_marcadores(en, trad, codigo):
    """Huecos de formato distintos de los del inglés (que son los mismos que los del español)."""
    e = []
    for k, t in trad.items():
        if k in en:
            m, esperado = marcadores(t), marcadores(en[k])
            if m is None:
                e.append(f"{codigo}: {k} tiene un marcador desconocido: {t!r}")
            elif m != esperado:
                e.append(f"{codigo}: {k} usa los huecos {m}, el inglés {esperado}: {t!r}")
    return e


def formatear(fmt, args):
    """Como TranslatableContents: %s, %n$s y %%."""
    it = iter(range(len(args)))

    def sub(m):
        pos, tipo = m.groups()
        if tipo == "%":
            return "%"
        i = int(pos) - 1 if pos else next(it, len(args))
        return args[i] if 0 <= i < len(args) else ""
    return _MARCA.sub(sub, fmt)


def texto(comp, textos):
    """Texto plano de un componente en el idioma `textos` (lo que pinta un cliente con el mod)."""
    if isinstance(comp, (int, float)):
        return str(comp)
    if isinstance(comp, str):
        return comp
    if isinstance(comp, list):
        return "".join(texto(c, textos) for c in comp)
    if "translate" in comp:
        fmt = textos.get(comp["translate"])
        s = RELLENO if fmt is None else formatear(fmt, [texto(a, textos) for a in comp.get("with", [])])
    else:
        s = str(comp.get("text", ""))
    return s + "".join(texto(c, textos) for c in comp.get("extra", []))


def paginas_de_libros(objetos):
    """[(dónde, página)] de todos los libros escritos (written_book_content) que haya dentro de `objetos` (tablas de
    botín, tratos, NBT de bloques...), con la página como componente."""
    out = []

    def ver(o, donde):
        if isinstance(o, dict):
            libro = o.get("minecraft:written_book_content")
            if isinstance(libro, dict):
                for i, p in enumerate(libro.get("pages", [])):
                    out.append((f"{donde} p{i + 1}", p.get("raw", p) if isinstance(p, dict) else p))
            for v in o.values():
                ver(v, donde)
        elif isinstance(o, (list, tuple)):
            for v in o:
                ver(v, donde)
    for donde, o in objetos:
        ver(o, donde)
    return out


def errores_libros(paginas, textos, codigo):
    """Páginas de libro que no caben en este idioma (14 líneas de 114 px, como el juego)."""
    from unicas._comun import botin
    e = []
    for donde, p in paginas:
        t = texto(p, textos)
        if botin.lineas_libro(t) > botin.LIBRO_LINEAS:
            e.append(f"{codigo}: la página de libro {donde} no cabe ({botin.lineas_libro(t)} de {botin.LIBRO_LINEAS} "
                     f"líneas): {t[:60]}…")
    return e


CARTEL_ANCHO = 90          # SignBlockEntity: ancho máximo de una línea de cartel, en px


def claves_de_carteles(objetos):
    """Claves traducibles de las líneas de cartel (front_text/back_text) que haya dentro de `objetos` (NBT de bloques)."""
    out = set()

    def ver(o):
        if isinstance(o, dict):
            for lado in ("front_text", "back_text"):
                for m in (o.get(lado) or {}).get("messages", []) if isinstance(o.get(lado), dict) else []:
                    if isinstance(m, dict) and "translate" in m:
                        out.add(m["translate"])
            for v in o.values():
                ver(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                ver(v)
    for o in objetos:
        ver(o)
    return out


def errores_carteles(claves, textos, codigo):
    """Líneas de cartel más anchas que el cartel (90 px) en este idioma, también en es/en: el cliente (SignRenderer)
    corta la línea por palabras a 90 px y lo que sobra no se ve."""
    from unicas._comun import botin
    e = []
    for k in sorted(claves):
        if k in textos and botin.ancho(textos[k]) > CARTEL_ANCHO:
            e.append(f"{codigo}: la línea de cartel {k} no cabe ({botin.ancho(textos[k])} de {CARTEL_ANCHO} px): "
                     f"{textos[k]!r}")
    return e


def ordenar(base, trad):
    """La traducción con las claves en el orden del es_es (las que no están en él, al final)."""
    return {**{k: trad[k] for k in base if k in trad}, **{k: v for k, v in trad.items() if k not in base}}


def completar(base, paginas=(), carteles=()):
    """{código: textos} de todos los idiomas a partir de los base ({"es_es": ..., "en_us": ...}) y las traducciones.
    `paginas`: las de los libros escritos (paginas_de_libros), que deben caber en cada idioma; `carteles`: claves de
    las líneas de cartel (claves_de_carteles). Lanza SystemExit con todos los errores si una traducción no está
    completa o no cabe."""
    es, en = base["es_es"], base["en_us"]
    out, e = {"es_es": es, "en_us": en}, []
    for codigo in BASE:
        e += errores_libros(paginas, base[codigo], codigo) + errores_carteles(carteles, base[codigo], codigo)
    for codigo in TRADUCCIONES:
        trad = cargar(codigo)
        e += errores_claves(es, trad, codigo) + errores_marcadores(en, trad, codigo)
        e += errores_libros(paginas, {**en, **trad}, codigo) + errores_carteles(carteles, trad, codigo)
        out[codigo] = ordenar(es, trad)
    if e:
        raise SystemExit("IDIOMAS:\n" + "\n".join(e[:200]) + (f"\n… y {len(e) - 200} más" if len(e) > 200 else ""))
    return out


def _comprobar(codigos):
    """Uso a mano: compara cada traducción con el es_es/en_us ya generados (build/generated/heraldia)."""
    raiz = os.path.join(os.path.dirname(CARPETA), "..", "..", "build", "generated", "heraldia")
    lang = os.path.join(raiz, "assets", "heraldia", "lang")
    base = {}
    for c in BASE:
        with open(os.path.join(lang, f"{c}.json"), encoding="utf-8") as f:
            base[c] = json.load(f)
    paginas = []
    for d, _, fs in os.walk(os.path.join(raiz, "data")):
        for f in fs:
            if f.endswith(".json"):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    paginas += paginas_de_libros([(f, json.load(fh))])
    # los libros de los atriles de las plantillas (tablón, torre del mago) no están en data/: por su clave
    paginas += [(k, {"translate": k, "with": [RELLENO] * 3}) for k in base["es_es"]
                if re.fullmatch(r"heraldia\.(tablon\.p\d+|unicas\.torre_mago\.diario\.\d+)", k)]
    carteles = {k for k in base["es_es"] if ".cartel." in k}
    import guia, unicas
    malos = 0
    for c in BASE:
        e = errores_carteles(carteles, base[c], c)
        print("\n".join(e) if e else f"{c}: carteles bien")
        malos += len(e)
    for c in codigos or TRADUCCIONES:
        trad = cargar(c)
        e = (errores_claves(base["es_es"], trad, c) + errores_marcadores(base["en_us"], trad, c)
             + errores_libros(paginas, {**base["en_us"], **trad}, c)
             + errores_carteles(carteles, trad, c))
        if not errores_claves(base["es_es"], trad, c):
            e += guia.errores(unicas.modules(), {c: trad})
        print("\n".join(e) if e else f"{c}: bien ({len(trad)} claves)")
        malos += len(e)
    return 1 if malos else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(_comprobar(sys.argv[1:]))
