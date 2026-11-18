"""light_profile.py: the light profile's texts (suggestion, seams, /heraldia profile note and the client screen) in the 8
languages, equal in the module and in languages/<code>.json, with the same placeholders, without copied English, and the
Java asks only for keys that exist; and the option texts of the new profile value in every language."""
import os
import re
import pytest
import light_profile as lp
import languages
import options
import updates

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
JAVA = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
CLIENT = os.path.join(ROOT, "src", "client", "java", "io", "github", "albertosa23", "heraldia")
FILES = [os.path.join(JAVA, "command", "ProfileNotice.java"), os.path.join(JAVA, "command", "ProfileCommand.java"),
         os.path.join(CLIENT, "client", "ConfigScreen.java")]
TEXTS = lp.lang()


def test_es_and_en_with_the_same_keys_and_gaps():
    es, en = TEXTS["es_es"], TEXTS["en_us"]
    assert es.keys() == en.keys()
    for k in es:
        assert k.startswith("heraldia.ligero."), k
        assert languages.markers(es[k]) == languages.markers(en[k]), k


@pytest.mark.parametrize("lang_code", list(languages.TRANSLATIONS))
def test_each_translation_is_in_its_file(lang_code):
    translated = languages.load_data(lang_code)
    for k, v in lp.translation(lang_code).items():
        assert translated.get(k) == v, f"{lang_code} {k}: run python3 tools/gen/light_profile.py"
    for k, en in TEXTS["en_us"].items():
        assert languages.markers(translated[k]) == languages.markers(en), f"{lang_code} {k}"
    opt = options.lang()["en_us"]
    for k in ("heraldia.config.perfil", "heraldia.config.perfil.ligero", "heraldia.config.perfil_ligero"):
        assert languages.markers(translated[k]) == languages.markers(opt[k]), f"{lang_code} {k}"


@pytest.mark.parametrize("lang_code", list(languages.TRANSLATIONS))
def test_translations_are_not_copied_english(lang_code):
    translated, en = lp.translation(lang_code), {**TEXTS["en_us"], **options.lang()["en_us"]}
    copied = [k for k in translated if translated[k] == en.get(k) and re.search(r"[A-Za-z]{4,}", re.sub(r"Heraldia|config/heraldia\.json", "", en[k]))]
    assert not copied, f"{lang_code}: {copied}"


def test_the_java_requests_keys_that_exist():
    src = "".join(open(f, encoding="utf-8").read() for f in FILES)
    requested = set(re.findall(r'"(heraldia\.ligero\.[a-z_.]*[a-z_])"', src))
    assert requested == set(TEXTS["es_es"]), requested ^ set(TEXTS["es_es"])


def test_the_new_profile_value_has_its_names():
    es, en = options.lang()["es_es"], options.lang()["en_us"]
    assert es["heraldia.config.perfil.ligero"] == "Ligero" and en["heraldia.config.perfil.ligero"] == "Light"
    assert "%s" in es["heraldia.config.perfil_ligero"] and "%s" in en["heraldia.config.perfil_ligero"]
    assert "ligero" in es["heraldia.config.perfil"] and "light" in en["heraldia.config.perfil"]
    assert "ligero" in updates.PROFILES
    for k in ("heraldia.panel.perfil.ligero", "heraldia.panel.ligero.titulo", "heraldia.panel.ligero.aviso",
              "heraldia.panel.ligero.aplicar", "heraldia.panel.ligero.aplicar.ayuda"):
        assert k in updates.lang()["es_es"], k
