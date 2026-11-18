"""Nombres de los comandos del mod: en inglés desde T35b, con los antiguos en español como alias ocultos (Java:
comando/Alias.ANTIGUOS, que test_comandos compara con este). Sirve para comprobar que ningún texto ni botón (run_command,
suggest_command) del mod manda al jugador a un nombre antiguo.

Regla permanente (docs/DEVELOPMENT.md): todo comando nuevo va en inglés; los textos que ve el jugador siguen traducidos.
"""
import itertools
import re

# ruta canónica bajo /heraldia -> nombre antiguo de su último tramo (el mismo mapa que comando/Alias.ANTIGUOS)
OLD = {
    "guide": "guia",
    "key": "llave",
    "info nearby": "cerca",
    "info here": "aqui",
    "arena leave": "salir",
    "arena place": "colocar",
    "arena place confirm": "confirmar",
    "arena move": "mover",
    "arena move confirm": "confirmar",
    "arena remove": "quitar",
    "arena remove confirm": "confirmar",
    "arena start": "empezar",
    "arena stop": "parar",
}
# valores de argumento antiguos: (ruta del comando, antiguo, nuevo)
OLD_VALUES = [("key", "todas", "all")]
# los subcomandos literales con su nombre canónico (los argumentos, entre <>), para comprobar el árbol de Java
CANONICAL = [
    "info", "info nearby", "info nearby <radius>", "info here", "guide", "key", "key <players>", "key <players> <key>",
    "arena", "arena leave", "arena place", "arena place confirm", "arena move", "arena move confirm", "arena remove",
    "arena remove confirm", "arena start", "arena stop",
    "arena start coop", "arena start timeattack", "arena start survival",   # T41: modos de la arena
    "arena leaderboard", "arena leaderboard coop", "arena leaderboard coop <week>", "arena leaderboard timeattack",
    "arena leaderboard timeattack <week>", "arena leaderboard survival", "arena leaderboard survival <week>",
    "arena season", "arena season reset",
    "review", "review next", "review previous", "review skip", "review skip <note>", "review goto", "review goto <id>",
    "review goto <id> generate", "review mark", "review mark checked", "review mark checked <note>", "review mark problem",
    "review mark problem <note>", "review list", "review status", "review reset",
    "status", "status <page>", "reload", "update", "update check",
    "profile",                                   # T36: el perfil de juego
    "webmap", "webmap refresh",
    "treasure", "treasure give", "treasure give <players>", "treasure info",   # T40: búsqueda del tesoro (operadores)
    "quest", "quest list", "quest accept", "quest accept <number>", "quest abandon", "quest abandon <number>",
    "quest turnin",                              # T38: los encargos del tablón
    "caravan", "caravan spawn", "caravan spawn raid", "caravan spawn peaceful", "caravan raid", "caravan list",
    "caravan clear",                             # T39: las caravanas (operadores)
    "wizard", "wizard reveal",                   # T43: las chozas de mago (operadores)
    # T46: panel de configuración en diálogos, idioma de cada jugador y actualizaciones seguras
    "config", "config menu", "config menu <menu>", "config profile", "config profile <profile>", "config save",
    "config save <menu>", "config save <menu> <values>", "config set", "config set <option>", "config set <option> <value>",
    "language", "language <language>",
    "update analyze", "update apply", "update apply confirm", "update apply confirm <id>", "update apply confirm <id> backup",
    "update apply confirm <id> nobackup", "update apply confirm <id> nobackup risk", "update undo", "update undo confirm",
    "update undo confirm <id>", "update repair", "update repair dry-run",
]


def old_paths():
    """Todas las rutas (sin «/heraldia») en las que al menos un tramo usa el nombre antiguo: «guia», «arena colocar
    confirmar», «arena place confirmar», «arena colocar confirm»..."""
    out = set()
    for route in OLD:
        segments = route.split()
        options = []
        for i in range(len(segments)):
            partial = " ".join(segments[:i + 1])
            options.append([segments[i]] + ([OLD[partial]] if partial in OLD else []))
        for combo in itertools.product(*options):
            if list(combo) != segments:
                out.add(" ".join(combo))
    return sorted(out, key=lambda r: (-len(r), r))


def _pattern():
    routes = "|".join(re.escape(r) for r in old_paths())
    values = "|".join(rf"(?:{re.escape(c)}|{re.escape(OLD.get(c, c))}) \S+ {re.escape(v)}" for c, v, _ in OLD_VALUES)
    return re.compile(rf"\bheraldia (?:{routes})(?!\w|\.\w)|\bheraldia (?:{values})(?!\w|\.\w)")


PATTERN = _pattern()


def old_in(text):
    """Las menciones de un comando con un nombre antiguo («/heraldia guia», «heraldia arena colocar»...) en un texto."""
    return [m.group(0) for m in PATTERN.finditer(text)]


def text_errors(texts, where=""):
    """[error] por cada texto de {clave: texto} que nombra un comando antiguo."""
    return [f"{where}{k}: «{m}» es un nombre antiguo" for k, t in texts.items() if isinstance(t, str) for m in old_in(t)]


def click_orders(obj):
    """[(acción, orden)] de todos los click_event / clickEvent run_command y suggest_command de un JSON (componentes de
    texto de tellraw, libros, carteles...)."""
    out = []
    if isinstance(obj, dict):
        for k in ("click_event", "clickEvent"):
            ev = obj.get(k)
            if isinstance(ev, dict) and ev.get("action") in ("run_command", "suggest_command"):
                out.append((ev["action"], str(ev.get("command", ev.get("value", "")))))
        for v in obj.values():
            out += click_orders(v)
    elif isinstance(obj, list):
        for v in obj:
            out += click_orders(v)
    elif isinstance(obj, str) and ("run_command" in obj or "suggest_command" in obj):
        # un componente escrito como texto JSON dentro de otro (SNBT de los carteles, tellraw de las funciones)
        for m in re.finditer(r'"(?:command|value)"\s*:\s*"([^"]*)"', obj):
            out.append(("texto", m.group(1)))
    return out


def click_errors(obj, where=""):
    """[error] por cada botón (run_command / suggest_command) que manda a un comando con un nombre antiguo."""
    return [f"{where}{action} «{order}» usa un nombre antiguo" for action, order in click_orders(obj) if old_in(order)]
