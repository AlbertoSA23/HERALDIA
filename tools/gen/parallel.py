"""Distribution of the generator's work among processes (fork), with results in the same order as in serial.

The children inherit the parent's memory when created (fork): the templates are neither copied nor serialised on the way there, only the
results come back. Without fork (Windows, macOS with spawn) or with HERALDIA_PROCESOS=1, everything runs in serial, the same.
The output does not depend on the number of processes: tools/gen/tests/test_parallel.py and the comparison of the
decompressed generations (docs/DEVELOPMENT.md) verify it.
"""
import multiprocessing as mp
import os

_TASK = None      # (function, items) that the children see after the fork


def _nbt_list(subkind, elements):
    from nbtlib.tag import List
    return List[subkind](elements)


def _serializable_nbt():
    """nbtlib lists are classes created on the fly (List[Int], List[Float]...) that pickle cannot rebuild: they are
    returned as (subtype, items). Needed to bring templates back from the children."""
    from nbtlib.tag import List
    List.__reduce__ = lambda self: (_nbt_list, (self.subtype, list(self)))


_serializable_nbt()


def processes():
    """Processes to use: HERALDIA_PROCESOS or the available cores."""
    n = os.environ.get("HERALDIA_PROCESOS")
    if n:
        return max(1, int(n))
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except AttributeError:
        return max(1, os.cpu_count() or 1)


def _one(i):
    fn, items = _TASK
    return fn(items[i])


def map_obj(fn, items, chunksize=4, new_item=False):
    """[fn(x) for x in items], distributed among processes. fn and the items do not need to be serialisable (they arrive
    by fork); the result of each fn does. nuevo=True: each item in a freshly created process (parent state)."""
    global _TASK
    items = list(items)
    n = min(processes(), len(items))
    if n <= 1 or "fork" not in mp.get_all_start_methods():
        return [fn(x) for x in items]
    if new_item:
        return _children(fn, items, n)
    _TASK = (fn, items)
    try:
        pool = mp.get_context("fork").Pool(n)
        try:
            out = pool.map(_one, range(len(items)), chunksize=chunksize)
            pool.close()
        except BaseException:
            pool.terminate()
            raise
        finally:
            pool.join()       # no distribution threads alive: the next fork does not inherit any half-finished
        return out
    finally:
        _TASK = None


def _children(fn, items, n):
    """One fork per item from the main thread (no auxiliary threads, unlike Pool with
    maxtasksperchild), at most n at a time; each child leaves its result in a temporary file."""
    import pickle, shutil, tempfile, traceback
    tmp = tempfile.mkdtemp(prefix="heraldia-gen-")
    alive, out, err = {}, [None] * len(items), []
    try:
        pending = list(range(len(items)))
        while pending or alive:
            while pending and len(alive) < n and not err:
                i = pending.pop(0)
                pid = os.fork()
                if pid == 0:                                   # hijo
                    code = 0
                    try:
                        r = ("ok", fn(items[i]))
                    except BaseException:
                        r, code = ("error", traceback.format_exc()), 1
                    try:
                        with open(os.path.join(tmp, f"{i}.pkl"), "wb") as f:
                            pickle.dump(r, f, protocol=pickle.HIGHEST_PROTOCOL)
                    except BaseException:
                        traceback.print_exc()
                        code = 2
                    os._exit(code)
                alive[pid] = i
            if not alive:
                break
            pid, status = os.wait()
            i = alive.pop(pid)
            try:
                with open(os.path.join(tmp, f"{i}.pkl"), "rb") as f:
                    kind, r = pickle.load(f)
            except (OSError, EOFError, pickle.UnpicklingError):
                kind, r = "error", f"el proceso de {items[i]!r} terminó sin resultado (estado {status})"
            if kind == "ok":
                out[i] = r
            else:
                err.append(r)
        if err:
            raise RuntimeError("a part of the generator failed in parallel:\n" + err[0])
        return out
    finally:
        for pid in alive:
            try:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
            except OSError:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ module state (build_all in parallel)
# A build() may leave data in its module (STRUCTURE["json"] of the galleon, LANG, reports, lru_cache caches) that the
# parent reads later when writing. When the build runs in a child, those changes are returned and applied in the parent.
_OWN = os.path.dirname(os.path.abspath(__file__))


def _modules():
    import sys
    for name, m in list(sys.modules.items()):
        f = getattr(m, "__file__", None) or ""
        if name in ("__main__", "__mp_main__") or "tests" in name.split("."):
            continue
        if f and os.path.abspath(f).startswith(_OWN + os.sep):
            yield name, m


def _is_data(v):
    import types
    return not isinstance(v, (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type)) and not callable(v)


def snapshot():
    """{(module, name): bytes} of the generator's module-level data (whatever can be serialised)."""
    import pickle
    out = {}
    for mn, m in _modules():
        for k, v in vars(m).items():
            if k.startswith("__") or not _is_data(v):
                continue
            try:
                out[(mn, k)] = pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)
            except Exception:
                pass
    return out


def _caches():
    """Functions without arguments with an lru_cache already computed: {(module, name): function}."""
    out = {}
    for mn, m in _modules():
        for k, v in vars(m).items():
            if hasattr(v, "cache_info") and v.cache_info().currsize and getattr(v, "__wrapped__", None) is not None:
                import inspect
                try:
                    if not inspect.signature(v.__wrapped__).parameters:
                        out[(mn, k)] = v
                except (TypeError, ValueError):
                    pass
    return out


def changes(before, caches_before):
    """What has changed since `before` (snapshot) and the caches computed since then: {(module, name): value}."""
    import pickle, sys
    out = {}
    # Only the modules that were already imported in the parent: one that the child imports during the build is seen by no one
    # in the parent until it imports it itself (and then it computes it the same, everything is deterministic).
    modules = {mn for mn, _ in before}
    for key, b in snapshot().items():
        if key[0] in modules and before.get(key) != b:
            out[key] = ("dato", getattr(sys.modules[key[0]], key[1]))
    for key, fn in _caches().items():
        if key[0] in modules and key not in caches_before:
            out[key] = ("cache", fn())
    return out


def apply(changed):
    """Applies in this process the changes returned by a child. dicts, lists and sets are changed in place (other
    modules may hold a reference to the same object); caches return the value computed in the child again."""
    import functools, sys
    for (mn, k), (kind, v) in changed.items():
        m = sys.modules[mn]
        current = getattr(m, k, None)
        if kind == "cache":
            constant = functools.lru_cache(maxsize=1)(lambda v=v: v)
            constant.__wrapped__ = getattr(current, "__wrapped__", None)
            setattr(m, k, constant)
        elif isinstance(current, dict) and isinstance(v, dict) and type(current) is type(v):
            current.clear()
            current.update(v)
        elif isinstance(current, list) and isinstance(v, list):
            current[:] = v
        elif isinstance(current, set) and isinstance(v, set):
            current.clear()
            current.update(v)
        else:
            setattr(m, k, v)


def map_with_state(fn, items, priority=None):
    """Like mapa(fn, items), but fn may change data of the generator's modules: in the children those
    changes are measured and applied in the parent in the order of `items` (as in serial). `prioridad(x)`: those with the highest value are
    distributed first (the long ones first shorten the total); the result stays in the order of `items`."""
    items = list(items)
    if min(processes(), len(items)) <= 1 or "fork" not in mp.get_all_start_methods():
        return [fn(x) for x in items]
    order = sorted(range(len(items)), key=lambda i: -(priority(items[i]) if priority else 0))
    base, caches = snapshot(), set(_caches())

    import time
    t0 = time.monotonic()

    def task(i):
        t = time.monotonic()
        r = fn(items[i])
        t1 = time.monotonic()
        c = changes(base, caches)
        return r, c, (t - t0, t1 - t, time.monotonic() - t1)
    done_items = dict(zip(order, map_obj(task, order, new_item=True)))    # each task in a new child: it only brings back its own
    who = {}
    for i in range(len(items)):
        for key in done_items[i][1]:
            if key in who:
                raise RuntimeError(f"{items[who[key]]} y {items[i]} cambian los dos {key[0]}.{key[1]}: en paralelo se "
                                   "perdería uno de los cambios (HERALDIA_PROCESOS=1 para generar en serie)")
            who[key] = i
    out = []
    for i in range(len(items)):
        r, changed, timings = done_items[i]
        if os.environ.get("HERALDIA_TIEMPOS"):
            print(f"  {items[i]}: empieza a {timings[0]:.1f} s, {timings[1]:.1f} s (+{timings[2]:.1f} s de estado, "
                  f"{len(changed)} cambios)")
        apply(changed)
        out.append(r)
    return out
