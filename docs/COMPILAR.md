# Heraldia: compilar y probar

[English](BUILDING.md) · **Español**

Volver al [README](../README.es.md).

## Compilar

Requisitos: Java 25, Python 3.11+ y `pip install -r tools/gen/requirements.txt`, git.

```bash
./gradlew build
```

El `.jar` queda en `build/libs/`. La compilación ejecuta el generador `tools/gen/main.py`, que crea las estructuras y los logros, los valida contra los registros de 26.3 y audita las estructuras; si hay un solo error o aviso, la compilación falla.

Los registros de 26.3 (resumen de [misode/mcmeta](https://github.com/misode/mcmeta), rama `26.3-summary`) no se incluyen en el repositorio porque son datos de Mojang. Se clonan solos en `build/mcmeta-summary`; para usar otra copia: `-Pmcmeta_summary=<ruta>` o la variable `MCMETA_SUMMARY`.

`./gradlew build` pasa también las pruebas unitarias: las del generador (pytest, `tools/gen/tests`, también con `python3 -m pytest tools/gen/tests`, unos segundos), las JUnit (`./gradlew test`) y las simulaciones JUnit largas (`./gradlew testPesado`, unos minutos). El generador reparte su trabajo entre procesos (`HERALDIA_PROCESOS=1` lo hace en serie, con la misma salida).

`python3 tools/test.py --affected` pasa las pruebas unitarias y solo las pruebas de servidor afectadas por los ficheros cambiados frente a `origin/develop` (`--list-only` solo las enumera); `python3 tools/test.py --all` pasa la batería completa. El mapa de rutas es el mismo que usa la CI (ver `docs/DEVELOPMENT.md` (en inglés), «Testing policy»).

Comprobaciones antes de publicar (la CI de GitHub Actions, `.github/workflows/ci.yml`, las ejecuta en cada PR contra `develop` o `main`, con solo las pruebas de servidor afectadas por el PR, y todas en cada push a `develop`, a mano o en un PR con la etiqueta `bateria-completa`):

```bash
python3 tools/changelog.py check
```

```bash
python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-0.1.0.jar
```

La segunda descarga un servidor Fabric 26.3 real en `build/smoke`, arranca con el mod y comprueba que las 180 estructuras estén registradas y los 122 logros cargados, que `/place structure` coloque una aldea con aldeanos y que las funciones existan.

Pruebas en servidor de cada estructura única (mismo argumento `--jar`): `tools/smoke/colosseum_redstone.py`, `observatory_smoke.py`, `palace_redstone.py`, `citadel_check.py` y `galleon_test.py`, y en `tools/gen/uniques/`: `castle/smoke_redstone.py`, `wizard_tower/smoke_redstone.py`, `cathedral/smoke_game.py` y `smoke_server.py` de `ice_fortress`, `mansion`, `monastery`, `pyramid`, `jarl_hall`, `sanctuary`, `mycelium_lab`, `lost_mine` e `corsair_island`. La Atlántida se comprueba dentro de la prueba de humo (`atlantis/smoke.py`). `tools/smoke/trophies.py` añade Carpet (versión fijada) y, con un jugador simulado, mata a cada guardián y comprueba que suelta su trofeo (y que con `/kill` no) y que el desafío de los trofeos se concede con el último. `tools/smoke/boss_phases.py` (con Carpet) invoca guardianes con sus etiquetas, como uno ya generado, les quita vida con `/damage` hasta cada umbral y comprueba las etiquetas de fase, los efectos, los refuerzos (cuántos, de qué tipo, con su equipo y sus etiquetas, adultos, sin la tabla del guardián, sin repetirse y con el tope de 4), la barra (por el log: al primer golpe, al irse y volver el jugador y al morir) y, en un segundo arranque con las tres opciones desactivadas, que no pasa nada de eso. `tools/smoke/story.py` (también con Carpet) comprueba que la cadena de la Crónica pasa por todas las únicas y que el cofre de cada una suelta su pliego, y que el jugador simulado consigue el desafío Cronista con el último. `tools/smoke/village_variants.py` coloca varias aldeas del mismo estilo, lee las regiones guardadas e identifica, comparando los bloques con las plantillas del `.jar`, qué variante de cada edificio especial ha salido; comprueba que cada uno coincide con una sola variante y que salen variantes distintas, y mide cada `/place`. `tools/smoke/adult_guardians.py` coloca 200 veces, por el mismo camino que la generación, cada mob de tipo zombi de las plantillas (zombi, husk, ahogado) y comprueba que ninguno sale bebé, con otra arma o montado. `tools/smoke/anchored_guardians.py` (con Carpet) coloca 30 veces, por el mismo camino, cada mob de las plantillas con la etiqueta `heraldia_anclado` (los guardianes y los ahogados de la Atlántida) y comprueba que ninguno puede recoger objetos y que tras 200 ticks, y otra vez tras descargar y volver a cargar los chunks, todos siguen donde aparecieron (un lote de control sin la etiqueta debe pasear y recoger objetos); luego, que cada uno ataca al jugador simulado a 8 bloques, y que cada guardián sigue en su sala 200 ticks después de colocar su plantilla real de día. `tools/smoke/compatible_grid.py` activa `unicas.rejilla_compatible` y comprueba que `/locate` de varias únicas de la 0.1.0 da exactamente las coordenadas del `.jar` de la 0.1.0 (fijadas en el script, con cómo se sacaron). `tools/smoke/generation_cost.py` mide el coste de generación: genera las mismas zonas del mismo mundo (semilla fija) con y sin Heraldia, tres pasadas de cada, y compara la CPU del servidor por chunk con la referencia de `tools/smoke/cost_reference.json` (falla ante una regresión; informa también de los pasos de cada chunk, el MSPT, la memoria y los tiempos de `/locate`; ver `DEVELOPMENT.md`, en inglés). Medido en la CI (4 núcleos): +9,3 % de CPU por chunk con Heraldia. Con `-Dheraldia.perfil=true` en la JVM del servidor, Heraldia escribe en el log al pararlo cuánto han tardado sus pasos de generación más caros (reglas de colocación, búsqueda de ladera de las minas, de la orilla del puerto, caminos...); sin ella no mide nada.

Todas las pruebas de servidor comparten las utilidades de `tools/smoke/server_smoke.py` (`Context`): comprobaciones que siempre responden (`test` rechaza un `execute` con `as`/`at` o con más de una condición, que puede no responder nada en la consola), esperas por condición con un límite holgado (`until`, `wait_entity`, que si se rinde imprime dónde están las entidades de ese tipo o etiqueta), esperas contadas en ticks del juego (`ticks`, con `/time query gametime`) y `pos` (lee `Pos` con `data get entity`). Los guardianes y demás mobs con IA se buscan por su etiqueta, no en una caja junto a su sitio. Cada servidor de prueba elige un puerto libre, así que se pueden lanzar varias pruebas a la vez en la misma máquina.

Versiones fijadas en `gradle.properties`. Herramientas del generador: `tools/gen/sim.py` (simula el ensamblado jigsaw; `python3 tools/gen/sim.py [estilo ...]` cuenta las variantes de los especiales, casas, aldeanos, gólems y camas), `tools/gen/render.py` (renders isométricos; `python3 tools/gen/render.py <carpeta> [estilo ...]` dibuja las láminas de variantes), `tools/gen/lint.py` (auditoría de diseño).
