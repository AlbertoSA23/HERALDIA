"""End of the Chronicle (chronicle_ending.py): texts in both languages and in the 6 translations, every page of the last leaf
fits a vanilla book page in every language, the two advancements are granted by the Java side, and the data the Java reads."""
import json
import os
import re
import chronicle_ending as ce
import languages
import options
from uniques._common import chest_loot

LANGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "languages")


def translations():
    out = {}
    for code in languages.TRANSLATIONS:
        with open(os.path.join(LANGS, f"{code}.json"), encoding="utf-8") as f:
            out[code] = json.load(f)
    return out


def test_everything_fits_in_every_language():
    assert ce.errors(translations()) == []


def test_same_keys_and_gaps_in_both_languages():
    lang = ce.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for k, es in lang["es_es"].items():
        assert es.strip() and lang["en_us"][k].strip(), k
        assert es.count("%s") == lang["en_us"][k].count("%s"), k


def test_every_translation_has_every_key_with_its_gaps():
    en = ce.lang()["en_us"]
    for code, t in translations().items():
        for k, v in en.items():
            assert k in t, f"{code}: {k}"
            assert t[k].count("%s") == v.count("%s"), f"{code}: {k}"
    opt = "heraldia.config.guia.final_cronica"
    assert all(opt in t and opt + ".nombre" in t for t in translations().values())


def test_a_page_that_does_not_fit_fails():
    long_text = {k: v for k, v in ce.lang()["en_us"].items()}
    long_text[ce.page_key("camino")] = "word " * 200
    assert any("camino" in e for e in ce.errors({"xx_xx": long_text}))


def test_advancements_are_granted_by_the_java_side():
    advs = ce.advancements()
    assert set(advs) == {"cronica/final", "cronica/mas_alla"}
    for path, a in advs.items():
        assert a["criteria"] == {"hecho": {"trigger": "minecraft:impossible"}}
        assert a["display"]["frame"] == "challenge"
        assert a["display"]["title"]["translate"] == f"advancements.heraldia.{path.replace('/', '.')}.title"
    assert advs["cronica/final"]["parent"] == "heraldia:raiz"
    assert advs["cronica/mas_alla"]["parent"] == "heraldia:cronica/final"


def test_dataset_matches_the_pages():
    d = ce.dataset()
    assert d["paginas"] == [pid for pid, _, _ in ce.PAGES]
    assert set(d["con_titulo"]) == {"juramento", "coda.hecho"}
    assert d["coda"] == {"pendiente": "coda.pendiente", "hecho": "coda.hecho"}
    assert d["logros"] == {"final": "cronica/final", "mas_alla": "cronica/mas_alla"}
    assert len(ce.TEXTS["libro"][0]) <= ce.TITLE_MAX and len(ce.TEXTS["libro"][1]) <= ce.TITLE_MAX


def test_names_from_the_story_and_no_coordinates():
    """The last leaf names the guardians as the trophies and leaves do, and never gives a place."""
    en = " ".join(t for _, _, (es, t) in ce.PAGES)
    for name in ("Aquilius", "Aldric", "Borin", "Frost King"):
        assert name in en
    assert not re.search(r"\d{2,}", en)


def test_option_on_by_default():
    o = next(x for x in options._FIXED if x[0] == "guia.final_cronica")
    assert o[1] is True
