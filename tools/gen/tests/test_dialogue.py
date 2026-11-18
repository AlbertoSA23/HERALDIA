"""dialogue.py and the villagers' line files (tools/gen/dialogue/<code>/<group>.json, P9a).

The check that lets several sessions write lines in parallel and be merged with confidence: every language that ships
a group file has, in it, exactly the Spanish pools and ids (not one more or fewer), with the same format slots in each
line, and only the slots its pool allows. A language may still lack a whole group file (its players get the English
line); `test_report_missing_files` prints which ones, and `test_every_language_complete` fails while any is missing:
it only runs with `HERALDIA_FRASES_COMPLETAS=1` (`HERALDIA_FRASES_COMPLETAS=1 python3 -m pytest
tools/gen/tests/test_dialogue.py -q`), to check that the content sessions have finished.
"""
import json
import os

import pytest

import dialogue
import languages


def _write(tmp_path, code, group, data):
    os.makedirs(tmp_path / code, exist_ok=True)
    with open(tmp_path / code / f"{group}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


@pytest.fixture
def folder(tmp_path, monkeypatch):
    """A clean line folder with a small reference (es_es) for the synthetic cases."""
    monkeypatch.setattr(dialogue, "FOLDER", str(tmp_path))
    es_village = {p: {"1": "x"} for p in dialogue.REQUIRED}
    es_village["general"] = {"1": "Hola, %1$s.", "2": "Bienvenido a %2$s."}
    es_village["hint.unique"] = {"1": "%1$s, al %2$s, a unos %3$s bloques."}
    _write(tmp_path, "es_es", "village", es_village)
    _write(tmp_path, "es_es", "professions", {"profession.farmer": {"1": "Trigo."}})
    _write(tmp_path, "es_es", "events", {f"event.{k}.{m}": {"1": "a", "2": "b", "3": "c"}
                                         for k, ms in dialogue.EVENT_POOLS.items() for m in ms})
    return tmp_path


def test_files_are_valid():
    assert dialogue.errors() == []


def test_reference_and_english_are_there():
    for code in ("es_es", "en_us"):
        for g in dialogue.GROUPS:
            assert dialogue.load(code, g) is not None, f"{code}/{g}.json"


def test_english_has_every_spanish_line():
    for g in dialogue.GROUPS:
        es, en = dialogue.load("es_es", g), dialogue.load("en_us", g)
        assert {(p, i) for p, v in es.items() for i in v} == {(p, i) for p, v in en.items() for i in v}


def test_every_present_language_matches_the_spanish():
    """The same as the generation, language by language, so a failure names the file."""
    for code in dialogue.codes():
        for g in dialogue.GROUPS:
            data = dialogue.load(code, g)
            if data is None or code == dialogue.REFERENCE:
                continue
            assert dialogue._compare(dialogue.load(dialogue.REFERENCE, g), data, f"{code}/{g}") == []


def test_report_missing_files(capsys):
    missing = dialogue.missing_files()
    with capsys.disabled():
        if missing:
            print(f"\nfrases de los aldeanos: faltan {len(missing)} archivos (usan el inglés): "
                  + ", ".join(f"{c}/{g}.json" for c, g in missing))


@pytest.mark.skipif(not os.environ.get("HERALDIA_FRASES_COMPLETAS"), reason="the 8 languages are not required yet")
def test_every_language_complete():
    assert dialogue.missing_files() == []


def test_every_pool_has_a_known_group():
    known = dialogue.pools()
    for p in known:
        assert known[p][0] in dialogue.GROUPS
    for prof in dialogue.PROFESSIONS:
        assert known[f"profession.{prof}"][0] == "professions"
    assert {p for p, (g, _) in known.items() if g == "professions"} == {f"profession.{x}" for x in dialogue.PROFESSIONS}


def test_ok_translation(folder):
    _write(folder, "fr_fr", "village", {**{p: {"1": "y"} for p in dialogue.REQUIRED},
                                        "general": {"1": "Salut, %1$s.", "2": "Bienvenue à %2$s."},
                                        "hint.unique": {"1": "%1$s, au %2$s, à %3$s blocs."}})
    assert dialogue.errors() == []
    assert ("fr_fr", "professions") in dialogue.missing_files()
    assert ("fr_fr", "village") not in dialogue.missing_files()


def test_missing_line_fails(folder):
    _write(folder, "fr_fr", "professions", {"profession.farmer": {}})
    e = dialogue.errors()
    assert any("fr_fr/professions: falta la frase profession.farmer.1" in x for x in e), e


def test_missing_pool_fails(folder):
    _write(folder, "de_de", "professions", {})
    assert any("falta el grupo de frases profession.farmer" in x for x in dialogue.errors())


def test_extra_line_and_pool_fail(folder):
    _write(folder, "it_it", "professions", {"profession.farmer": {"1": "Grano.", "2": "In più."},
                                             "profession.mason": {"1": "Pietra."}})
    e = dialogue.errors()
    assert any("sobra la frase profession.farmer.2" in x for x in e), e
    assert any("sobra el grupo de frases profession.mason" in x for x in e), e


def test_different_slots_fail(folder):
    _write(folder, "pt_br", "village", {**{p: {"1": "y"} for p in dialogue.REQUIRED},
                                        "general": {"1": "Olá.", "2": "Bem-vindo a %2$s."},
                                        "hint.unique": {"1": "%1$s, ao %2$s, a %3$s blocos."}})
    e = dialogue.errors()
    assert any("pt_br/village: general.1 usa los huecos" in x for x in e), e


def test_slot_not_allowed_in_its_pool(folder):
    _write(folder, "es_es", "professions", {"profession.farmer": {"1": "Trigo a %3$s bloques."}})
    assert any("solo valen [1, 2]" in x for x in dialogue.errors())


def test_unknown_marker_and_unknown_pool_and_wrong_file(folder):
    _write(folder, "es_es", "professions", {"profession.farmer": {"1": "100%d"}, "profession.wizard": {"1": "?"},
                                            "general": {"1": "?"}})
    e = dialogue.errors()
    assert any("marcador desconocido" in x for x in e), e
    assert any("profession.wizard no existe" in x for x in e), e
    assert any("general va en village.json" in x for x in e), e


def test_empty_line_and_required_pool(folder):
    _write(folder, "es_es", "village", {"general": {"1": " "}})
    e = dialogue.errors()
    assert any("general.1 está vacía" in x for x in e), e
    assert any("farewell necesita al menos una frase" in x for x in e), e


def test_write_merges_each_language(folder, tmp_path):
    out = {}
    dialogue.write(str(tmp_path / "out"), lambda o, path, data: out.__setitem__(path, data))
    assert set(out) == {"heraldia/dialogos/es_es.json"}
    assert out["heraldia/dialogos/es_es.json"]["profession.farmer"] == {"1": "Trigo."}


def test_ui_texts_have_both_languages_and_same_slots():
    lang = dialogue.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for k in lang["es_es"]:
        assert languages.markers(lang["es_es"][k]) == languages.markers(lang["en_us"][k]), k


def test_the_java_knows_the_same_pools():
    """Names shared with the Java (dialogue/Context, Hints, Dialogue): moments, weathers, hint kinds, the fixed pools."""
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src", "main", "java", "io", "github",
                        "albertosa23", "heraldia", "dialogue")
    java = "".join(open(os.path.join(root, f), encoding="utf-8").read() for f in os.listdir(root))
    for name in (*dialogue.MOMENTS, *dialogue.WEATHERS):
        assert f'"{name}"' in java, name
    for kind in dialogue.HINT_KINDS:
        assert f'"{kind}"' in java, kind
    for pool in ("general", "rumor", "busy", "farewell", "hint.withheld", "hint.told", "hint.nothing"):
        assert f'"{pool}"' in java, pool
    for prefix in ("profession.", "family.", "time.", "weather.", "reputation.", "greeting.", "hint."):
        assert f'"{prefix}"' in java, prefix
