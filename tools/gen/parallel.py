"""Reparto del trabajo del generador entre procesos (fork), con resultados en el mismo orden que en serie.

Los hijos heredan la memoria del padre al crearse (fork): las plantillas no se copian ni se serializan para ir, solo
vuelven los resultados. Sin fork (Windows, macOS con spawn) o con HERALDIA_PROCESOS=1, todo va en serie, igual.
La salida no depende del número de procesos: tools/gen/tests/test_parallel.py y la comparación de las generaciones
descomprimidas (docs/DEVELOPMENT.md) lo comprueban.
"""
import multiprocessing as mp
import os

_TAREA = None      # (función, elementos) que ven los hijos tras el fork


def _nbt_list(subkind, elements):
    from nbtlib.tag import List
    return List[subkind](elements)


def _serializable_nbt():
    """Las listas de nbtlib son clases creadas al vuelo (List[Int], List[Float]...) que pickle no sabe rehacer: se
    devuelven como (subtipo, elementos). Hace falta para traer plantillas de los hijos."""
    from nbtlib.tag import List
    List.__reduce__ = lambda self: (_nbt_list, (self.subtype, list(self)))


_serializable_nbt()


def processes():
    """Procesos a usar: HERALDIA_PROCESOS o los núcleos disponibles."""
    n = os.environ.get("HERALDIA_PROCESOS")
    if n:
        return max(1, int(n))
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except AttributeError:
        return max(1, os.cpu_count() or 1)


def _one(i):
    fn, items = _TAREA
    return fn(items[i])


def map_obj(fn, items, chunksize=4, new_item=False):
    """[fn(x) for x in items], repartido entre procesos. fn y los elementos no tienen que poder serializarse (llegan
    por fork); el resultado de cada fn sí. nuevo=True: cada elemento en un proceso recién creado (estado del padre)."""
    global _TAREA
    items = list(items)
    n = min(processes(), len(items))
    if n <= 1 or "fork" not in mp.get_all_start_methods():
        return [fn(x) for x in items]
    if new_item:
        return _children(fn, items, n)
    _TAREA = (fn, items)
    try:
        pool = mp.get_context("fork").Pool(n)
        try:
            out = pool.map(_one, range(len(items)), chunksize=chunksize)
            pool.close()
        except BaseException:
            pool.terminate()
            raise
        finally:
            pool.join()       # sin hilos del reparto vivos: el siguiente fork no hereda ninguno a medias
        return out
    finally:
        _TAREA = None


def _children(fn, items, n):
    """Un fork por elemento desde el hilo principal (sin hilos auxiliares, a diferencia de Pool con
    maxtasksperchild), como mucho n a la vez; cada hijo deja su resultado en un fichero temporal."""
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
            raise RuntimeError("falló una parte del generador en paralelo:\n" + err[0])
        return out
    finally:
        for pid in alive:
            try:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
            except OSError:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ estado de los módulos (build_all en paralelo)
# Un build() puede dejar datos en su módulo (STRUCTURE["json"] del galeón, LANG, informes, cachés con lru_cache) que el
# padre lee después al escribir. Cuando el build va en un hijo, esos cambios se devuelven y se aplican en el padre.
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
    """{(módulo, nombre): bytes} de los datos de nivel de módulo del generador (lo que se pueda serializar)."""
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
    """Funciones sin argumentos con lru_cache ya calculadas: {(módulo, nombre): función}."""
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


def changes(before, caches_antes):
    """Lo que ha cambiado desde `antes` (foto) y las cachés calculadas desde entonces: {(módulo, nombre): valor}."""
    import pickle, sys
    out = {}
    # Solo los módulos que ya estaban importados en el padre: uno que el hijo importe durante el build no lo ve nadie
    # del padre hasta que lo importe él mismo (y entonces lo calcula igual, todo es determinista).
    modules = {mn for mn, _ in before}
    for key, b in snapshot().items():
        if key[0] in modules and before.get(key) != b:
            out[key] = ("dato", getattr(sys.modules[key[0]], key[1]))
    for key, fn in _caches().items():
        if key[0] in modules and key not in caches_antes:
            out[key] = ("cache", fn())
    return out


def apply(changed):
    """Aplica en este proceso los cambios devueltos por un hijo. Los dict, list y set se cambian en su sitio (otros
    módulos pueden tener una referencia al mismo objeto); las cachés vuelven a dar el valor calculado en el hijo."""
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
    """Como mapa(fn, items), pero fn puede cambiar datos de los módulos del generador: en los hijos se miden esos
    cambios y se aplican en el padre en el orden de `items` (como en serie). `prioridad(x)`: los de valor más alto se
    reparten antes (los largos primero acortan el total); el resultado sigue en el orden de `items`."""
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
    done_items = dict(zip(order, map_obj(task, order, new_item=True)))    # cada tarea en un hijo nuevo: solo trae lo suyo
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
