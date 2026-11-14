# Generador de estructuras de Heraldia

Scripts en Python que generan los recursos de datos del mod (plantillas NBT, pools jigsaw, estructuras, botín, funciones y textos). Gradle lo ejecuta al compilar; no hace falta lanzarlo a mano.

Requisitos: Python 3.11+, `pip install -r requirements.txt`.

- `python3 main.py --out <carpeta> --registries <resumen mcmeta 26.3>` → genera, valida y audita; no escribe nada si hay errores o avisos.
- `themes.py` → los 36 estilos (materiales, tejados, tipo de iglesia, decoración).
- `houses.py`, `specials.py`, `streets.py`, `fillers.py` → constructores de piezas.
- `pack.py` → pools y pesos (incluida la proporción de aldeanos y camas).
- `writer.py` → tamaño de las aldeas, frecuencia y JSON de las estructuras.
- `sim.py` → simulador del ensamblado jigsaw para contar casas, aldeanos y gólems sin abrir el juego.
- `validate.py` → comprueba bloques, propiedades, objetos y entidades contra los registros de la 26.3 (necesita el resumen de misode/mcmeta, rama `26.3-summary`) y, sobre los JSON escritos, el límite de radio y tamaño de las estructuras jigsaw.
