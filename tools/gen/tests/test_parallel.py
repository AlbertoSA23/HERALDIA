"""paralelo.py: the distribution among processes gives the same as in serial and brings back to the parent what changes in the modules."""
import os, sys, types
import pytest
import parallel


@pytest.fixture(params=["1", "3"])
def processes(request, monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", request.param)
    return int(request.param)


def test_map_in_order(processes):
    dataset = [object() for _ in range(23)]              # not serialisable: they reach the children by fork
    ids = {id(o): i for i, o in enumerate(dataset)}
    assert parallel.map_obj(lambda o: ids[id(o)] ** 2, dataset) == [i * i for i in range(23)]
    assert parallel.map_obj(lambda x: x, []) == []


def test_map_in_new_children(processes):
    pids = parallel.map_obj(lambda _: os.getpid(), range(6), new_item=True)
    if processes > 1:
        assert os.getpid() not in pids and len(set(pids)) == 6
    else:
        assert set(pids) == {os.getpid()}


def test_processes_per_variable(monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", "2")
    assert parallel.processes() == 2
    monkeypatch.setenv("HERALDIA_PROCESOS", "0")
    assert parallel.processes() == 1


def test_nbt_lists_serializable():
    import pickle
    from nbtlib import List, Float, Int
    x = pickle.loads(pickle.dumps(List[Float]([Float(1.5)])))
    assert type(x).__name__ == "List[Float]" and x == [1.5] and type(pickle.loads(pickle.dumps(List[Int]([])))) is List[Int]


@pytest.fixture
def module(monkeypatch):
    """Fake generator module (like a unicas/<id>) with data that a build changes."""
    m = types.ModuleType("uniques._parallel_test")
    m.__file__ = os.path.join(os.path.dirname(parallel.__file__), "uniques", "_parallel_test.py")
    m.LANG = {"es_es": {}}
    m.STRUCTURE = {"spacing": 1}
    m.ITEM_LIST = []
    m.N = 0
    monkeypatch.setitem(sys.modules, m.__name__, m)
    return m


def test_map_with_state_brings_the_changes(processes, module):
    alias = module.LANG                                   # another module with a reference to the same dict

    # each change in a single task (otherwise, see test_conflicto)
    def only(i):
        if i == 2:
            module.LANG["es_es"]["k2"] = "v2"
        elif i == 1:
            module.STRUCTURE["json"] = {"tipo": "propio"}
            module.ITEM_LIST.append("x")
        elif i == 3:
            module.N = 7
        return i * 10
    assert parallel.map_with_state(only, range(4), priority=lambda i: i) == [0, 10, 20, 30]
    assert module.LANG == {"es_es": {"k2": "v2"}} and alias is module.LANG      # changed in place
    assert module.STRUCTURE["json"] == {"tipo": "propio"} and module.ITEM_LIST == ["x"] and module.N == 7


def test_conflict(module, monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", "2")

    def build(i):
        module.ITEM_LIST.append(i)
    with pytest.raises(RuntimeError, match="cambian los dos"):
        parallel.map_with_state(build, range(2))


def test_error_in_a_child(monkeypatch):
    monkeypatch.setenv("HERALDIA_PROCESOS", "2")

    def failing(i):
        if i == 3:
            raise ValueError("pieza rota")
        return i
    with pytest.raises(RuntimeError, match="pieza rota"):
        parallel.map_obj(failing, range(6), new_item=True)
    with pytest.raises(Exception, match="pieza rota"):
        parallel.map_obj(failing, range(6))
