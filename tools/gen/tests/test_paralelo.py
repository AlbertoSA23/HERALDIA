"""paralelo.py: el reparto entre procesos da lo mismo que en serie y trae al padre lo que cambia en los módulos."""
import os, sys, types
import pytest
import paralelo


@pytest.fixture(params=["1", "3"])
def procesos(request, monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", request.param)
    return int(request.param)


def test_mapa_en_orden(procesos):
    datos = [object() for _ in range(23)]              # no serializables: llegan a los hijos por fork
    ids = {id(o): i for i, o in enumerate(datos)}
    assert paralelo.mapa(lambda o: ids[id(o)] ** 2, datos) == [i * i for i in range(23)]
    assert paralelo.mapa(lambda x: x, []) == []


def test_mapa_en_hijos_nuevos(procesos):
    pids = paralelo.mapa(lambda _: os.getpid(), range(6), nuevo=True)
    if procesos > 1:
        assert os.getpid() not in pids and len(set(pids)) == 6
    else:
        assert set(pids) == {os.getpid()}


def test_procesos_por_variable(monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", "2")
    assert paralelo.procesos() == 2
    monkeypatch.setenv("HERALDIA_PROCESOS", "0")
    assert paralelo.procesos() == 1


def test_listas_nbt_serializables():
    import pickle
    from nbtlib import List, Float, Int
    x = pickle.loads(pickle.dumps(List[Float]([Float(1.5)])))
    assert type(x).__name__ == "List[Float]" and x == [1.5] and type(pickle.loads(pickle.dumps(List[Int]([])))) is List[Int]


@pytest.fixture
def modulo(monkeypatch):
    """Módulo del generador falso (como un unicas/<id>) con datos que un build cambia."""
    m = types.ModuleType("unicas._prueba_paralelo")
    m.__file__ = os.path.join(os.path.dirname(paralelo.__file__), "unicas", "_prueba_paralelo.py")
    m.LANG = {"es_es": {}}
    m.STRUCTURE = {"spacing": 1}
    m.LISTA = []
    m.N = 0
    monkeypatch.setitem(sys.modules, m.__name__, m)
    return m


def test_mapa_con_estado_trae_los_cambios(procesos, modulo):
    alias = modulo.LANG                                   # otro módulo con una referencia al mismo dict

    # cada cambio en una sola tarea (si no, ver test_conflicto)
    def solo(i):
        if i == 2:
            modulo.LANG["es_es"]["k2"] = "v2"
        elif i == 1:
            modulo.STRUCTURE["json"] = {"tipo": "propio"}
            modulo.LISTA.append("x")
        elif i == 3:
            modulo.N = 7
        return i * 10
    assert paralelo.mapa_con_estado(solo, range(4), prioridad=lambda i: i) == [0, 10, 20, 30]
    assert modulo.LANG == {"es_es": {"k2": "v2"}} and alias is modulo.LANG      # cambiado en su sitio
    assert modulo.STRUCTURE["json"] == {"tipo": "propio"} and modulo.LISTA == ["x"] and modulo.N == 7


def test_conflicto(modulo, monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", "2")

    def build(i):
        modulo.LISTA.append(i)
    with pytest.raises(RuntimeError, match="cambian los dos"):
        paralelo.mapa_con_estado(build, range(2))


def test_error_en_un_hijo(monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", "2")

    def falla(i):
        if i == 3:
            raise ValueError("pieza rota")
        return i
    with pytest.raises(RuntimeError, match="pieza rota"):
        paralelo.mapa(falla, range(6), nuevo=True)
    with pytest.raises(Exception, match="pieza rota"):
        paralelo.mapa(falla, range(6))
