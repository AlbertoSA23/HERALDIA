# Generador de estructuras de Heraldia

Scripts en Python que generan los recursos de datos del mod (plantillas NBT, pools jigsaw, estructuras, botín, funciones y textos). Gradle lo ejecuta al compilar; no hace falta lanzarlo a mano.

Requisitos: Python 3.11+, `pip install -r requirements.txt`.

- `python3 main.py --out <carpeta> --registries <resumen mcmeta 26.3>` → genera, valida y audita; no escribe nada si hay errores o avisos.
- `themes.py` → los 36 estilos (materiales, tejados, tipo de iglesia, decoración).
- `houses.py`, `specials.py`, `streets.py`, `fillers.py` → constructores de piezas.
- `pack.py` → pools y pesos (incluida la proporción de aldeanos y camas).
- `writer.py` → tamaño de las aldeas, frecuencia y JSON de las estructuras.
- `logros.py` → pestaña de logros «Heraldia» (aldeas por familia y, por cada única del registro, descubrir, guardián y tesoro; desafíos de los trofeos y de la crónica).
- Trofeos de los guardianes: `TROFEO` de cada única → `unicas/_comun/botin.trofeo` (`heraldia:trofeos/<id>`) y `guardian_tabla` (`heraldia:guardianes/<id>/<mob>`, la DeathLootTable que pone `pack.tag_guardians`).
- Crónica de los Heraldos (`docs/historia.md`): `HISTORIA` de cada única → `unicas/_comun/botin.historia_*` (`heraldia:historia/<id>`, que anida la tabla de su cofre; cadena en `historia_cadena`) y `writer.history_tables`; desafío `unicas/cronista` en `logros.py`.
- `tratos.py` → todos los tratos de aldeano (`trato`, `predicado`): los mapas de los cartógrafos maestros (`mapas.trade`), los tratos con carácter de cada estilo (`ESTILOS`), el mapa de la única de la zona de cada familia y la botella del asedio de las aldeas fortificadas; escribe las etiquetas `#minecraft:<oficio>/level_N`.
- `tablon.py` → tablón de encargos de la plaza (atril con libro y alguacil con sus tratos fijos) y logros de las hazañas con su recompensa.
- `sim.py` → simulador del ensamblado jigsaw para contar casas, aldeanos y gólems sin abrir el juego.
- `validate.py` → comprueba bloques, propiedades, objetos y entidades contra los registros de la 26.3 (necesita el resumen de misode/mcmeta, rama `26.3-summary`) y, sobre los JSON escritos, el límite de radio y tamaño de las estructuras jigsaw.
