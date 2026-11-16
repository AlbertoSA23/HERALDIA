# Guía de desarrollo de Heraldia (leer antes de tocar nada)

Mod de Fabric para Minecraft 26.3 solo de estructuras, para el servidor privado de Alberto (mundo ya existente,
modpack de CurseForge con Fabric API 0.166.2+26.3). El mod va en servidor y clientes. Contenido **solo vanilla**.
Repositorio público, **sin licencia (todos los derechos reservados)**. Hay CI en GitHub Actions (`.github/workflows/ci.yml`, ver «Entorno»); las comprobaciones también se pueden ejecutar a mano.

## Flujo de ramas
- Rama común: `develop`. Cada sesión trabaja en su propia rama creada desde `develop` y abre su PR **contra `develop`** (nunca contra `main`).
- Los PR contra `develop` **no necesitan autorización de Alberto**: cuando tus comprobaciones estén en verde, haz el merge de tu propio PR en `develop`. Si tus reglas de sesión no te dejan hacerlo, envía un mensaje al orquestador (session_01XFkUTbYXFfbMazJnFH8g53) con el enlace del PR y su head: él hace el merge en tu nombre y borra la rama.
- Sincronízate para no pisar a nadie: justo antes de hacer el merge, `git merge origin/develop` en tu rama, resuelve los conflictos (en `CHANGELOG.md`, `README.md` y `docs/APRENDIZAJES.md` se suman las entradas de todos), vuelve a pasar las comprobaciones y haz push. Si `develop` cambia entre tanto, repítelo. Nunca reescribas el historial de `develop` ni el de las ramas ajenas.
- Si tu cambio toca algo compartido (`writer.py`, `lint.py`, `core.py`, `Heraldia.java`, la prueba de humo), haz el merge pronto y en un PR pequeño para que las demás lo reciban cuanto antes.
- Solo `develop` se lleva a `main`, y lo hace la sesión orquestadora.

## Entorno (contenedor nuevo)
- Java 25: `curl -sSL -o /tmp/jdk.tgz "https://api.adoptium.net/v3/binary/latest/25/ga/linux/x64/jdk/hotspot/normal/eclipse" && mkdir -p ~/jdk25 && tar xzf /tmp/jdk.tgz -C ~/jdk25 --strip-components=1 && export JAVA_HOME=~/jdk25 PATH=~/jdk25/bin:$PATH`
- Python: `pip install -r tools/gen/requirements.txt`
- Compilar (genera, valida y audita; falla ante cualquier aviso): `./gradlew build`
- Prueba de humo en servidor dedicado 26.3 real: `python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-<versión>.jar`
- Registro de cambios: `python3 tools/changelog.py check`
- CI (`.github/workflows/ci.yml`): en cada PR contra `develop` o `main`, en cada push a `develop` y a mano (`workflow_dispatch`). Jobs: `seleccion` (pytest del generador y elección de las pruebas de servidor con `tools/test.py`), `compilar` (Java 25 y Python 3.12 con la acción común `.github/actions/preparar`; `tools/changelog.py check` y `./gradlew build -x testGen -x testPesado --build-cache`), `junit-pesado` (`./gradlew testPesado`, a la vez que la compilación), `humo` (`server_smoke.py` con el `.jar`; los datos generados se sacan del `.jar` y el clon de mcmeta hace falta porque `atlantida/humo.py` rehace su plano) y `servidor` (grupos de pruebas de servidor en paralelo, cada grupo en serie en su máquina, con `--work build/smoke`). Cachés: Gradle (y su caché de construcción), pip, el servidor Fabric de prueba, los mods de Modrinth de las pruebas (`build/smoke/modrinth`, una por grupo; la lista fijada con su sha512 está en `tools/smoke/modrinth.py`) y el clon de mcmeta (`build/mcmeta-summary`). Si una prueba falla, el `logs/latest.log` de cada prueba del grupo se sube como artefacto. Una prueba de servidor nueva (`tools/smoke/*.py` o `tools/gen/unicas/<id>/prueba_*.py`, que acepte `--jar` y `--work`) entra sola en la batería; ver «Política de pruebas». `publish.yml` (en `main`) no cambia. La CI no sustituye las capturas de Alberto.

## Política de pruebas (decisión de Alberto)
1. **Cada sesión prueba y verifica solo el trabajo que ha hecho**, sin pasar la batería completa ni preocuparse de lo que hagan las demás: los tests unitarios de su código (obligatorios: los máximos razonables) y las pruebas de servidor de las partes que toca. Así cada código nuevo llega con sus pruebas mínimas.
2. **Una sesión auditora final** pasa la batería completa y garantiza que todo funciona junto.
3. Se escriben **los máximos tests unitarios** posibles, y se prefiere un test unitario rápido a una prueba de servidor cuando los dos comprueban lo mismo. Si algo no se puede probar sin el juego, se separa la lógica pura (refactor mínimo, sin cambiar el comportamiento) y se prueba esa.

Cómo:
- Tests unitarios del generador: `python3 -m pytest tools/gen/tests -q` (o `./gradlew testGen`, que va dentro de `check`), segundos y sin generar el datapack. Uno por módulo en `tools/gen/tests/test_<módulo>.py`; `conftest.py` trae `plantilla(...)` y un resumen de mcmeta sintético (`mcmeta`) para `validate`/`biomas`. Para una única nueva basta con que cumpla el contrato (`test_unicas.py` la recorre sola); sus comprobaciones propias, en `tests/test_<id>.py`.
- JUnit: `./gradlew test` (lo rápido) y `./gradlew testPesado` (simulaciones de minutos, hoy `UniqueSeparationTest`; las clases van en `junitPesadas` de `build.gradle`). `./gradlew build` pasa las dos. Una clase que toque clases del juego hace `SharedConstants.tryDetectVersion()` y `Bootstrap.bootStrap()` en `@BeforeAll` (ver APRENDIZAJES).
- Lo de cada sesión: `python3 tools/test.py --afectados` (tests unitarios y las pruebas de servidor de lo cambiado frente a `origin/develop`, con el `.jar` de `./gradlew build`; `--listar` solo dice cuáles). La sesión auditora: `python3 tools/test.py --todo` (unitarios, humo y todas las de servidor, en serie: dos servidores a la vez en una máquina pequeña se estorban) o la CI con `workflow_dispatch`.
- Mapa ruta → pruebas (`tools/test.py`, el mismo en la CI; gana la primera regla que casa): documentación, tests, cliente y `render.py`, ninguna de servidor; `tools/gen/unicas/<id>/` (o `unicas/<id>.py`) y el Java de `unicas/<paquete>/`, las pruebas de esa única (las de su carpeta y las de `SMOKE_DE_UNICA`) más `trofeos`, `historia`, `guardianes_adultos` y `guardianes_anclados`; una prueba de servidor, solo ella; el generador de aldeas y `aldeas/` en Java, las tres `aldeas_*`; `tablon.py` y `tratos.py`, `aldeas_vida`; `biomas.py`, `terralith_biomas`; los mixins de los zombis, `guardianes_adultos`; `comun/Anclaje.java` y los mixins `DrownedAgua`/`DrownedPlaya`, `guardianes_anclados`; **lo común** (`_comun/`, `unicas/__init__.py`, `writer.py`, `core.py`, `pack.py`, `lint.py`, `validate.py`, `build.py`, `opciones.py`, `server_smoke.py`, `tools/test.py`, la CI, Gradle, recursos y el resto del Java) y **cualquier ruta que no esté en el mapa**, la batería completa. La prueba de humo va siempre. Las de compatibilidad con otros mods (`tools/smoke/compat_mods.py`, una por grupo de mods: `compat_mods.py::<grupo>`) solo van en un PR si cambia algo de `COMPAT_RUTAS` (la propia prueba, `modrinth.py`, `gradle.properties`, las etiquetas de biomas y el Java común de colocación: `GridPlacement`, `UniqueSeparation`, `VillageRules`, los mixins de `ChunkGenerator` y `StructureCheck`, `ZonaAjenas`, `IslaZona`, `AtlantisAnchor`), aunque lo cambiado pida la batería completa; en push a `develop` y con `workflow_dispatch`, siempre. Si añades una prueba en `tools/smoke/` que sea de una única, ponla en `SMOKE_DE_UNICA`; si es de otra cosa, añade su regla a `MAPA` (y su duración a `DURACION_S`); `tools/gen/tests/test_selector.py` comprueba el mapa.
- En la CI: un PR pasa la compilación, todos los tests unitarios, la de humo y solo las pruebas de servidor afectadas; la batería completa va en cada push a `develop`, con `workflow_dispatch` (la sesión auditora) y en un PR con la etiqueta `bateria-completa` o con `[bateria completa]` en el título. Un PR que cambia lo común (p. ej. `ci.yml`) la pasa entera por el mapa.
- Tiempos medidos (T20). Generador en local (4 núcleos): unos 250 s antes, unos 57 s ahora (construcción 65 → 25 s, auditoría 31 → 9 s, escritura 149 → 18 s), con la salida descomprimida idéntica. `./gradlew build` en local: 10 min antes (casi 5 de ellos `UniqueSeparationTest`), 66 s sin `testPesado`. CI con la batería completa: 15 min 15 s antes (PR #56: compilación y humo en un job de 11 min 47 s, con 538 s de `./gradlew build`), 6 min 32 s ahora (PR #58: `compilar` 2 min 58 s, de ellos 147 s de `./gradlew build`; `junit-pesado` 6 min 9 s, en paralelo desde el principio; `humo` 3 min 15 s y 11 grupos de servidor de 1 min 45 s a 3 min 30 s, en paralelo tras la compilación). Un PR pequeño tiene el mismo camino crítico (compilación + humo y `junit-pesado`, unos 6 min) y menos máquinas; no está medido aparte.
- Generador en paralelo (`tools/gen/paralelo.py`): `HERALDIA_PROCESOS=N` fija los procesos (1 = en serie, misma salida) y `HERALDIA_TIEMPOS=1` imprime lo que tarda cada parte. Un `build()` de una única puede dejar datos en su propio módulo (los trae al padre); si dos partes cambian el mismo dato de un módulo, la generación falla en vez de perder uno. Para comparar dos generaciones, el contenido descomprimido de los `.nbt` (ahora también los bytes: el gzip va sin hora).

## Estructuras únicas: dónde va cada cosa
- Una estructura = un módulo `tools/gen/unicas/<id>.py` (o paquete `tools/gen/unicas/<id>/`). El contrato está en `tools/gen/unicas/__init__.py`. No hace falta tocar `main.py` ni `writer.py`.
- Ids: estructura `heraldia:unicas/<id>`, plantillas y pools `heraldia:unicas/<id>/...`, botín `heraldia:unicas/<id>/<nombre>`, etiqueta `heraldia:unicas/<id>`.
- Botín con Lootr: marca con `"solo_sin_lootr": True` el grupo extra de cada cofre.
- Si necesitas Java propio, ponlo en el paquete `io.github.albertosa23.heraldia.unicas.<id>` y regístralo desde una clase propia llamada en `Heraldia.onInitialize` con una sola línea.
- Si la auditoría de `lint.py` no cubre algo de tu estructura, añade sus comprobaciones en tu módulo; los cambios en `lint.py` deben ser genéricos y pequeños.

## Memoria compartida: `docs/APRENDIZAJES.md`
- Léela antes de empezar y vuelve a mirarla tras cada `git merge origin/develop`.
- Todo lo que aprendas que sirva para diseñar mejores estructuras o evite un fallo (comportamiento del juego verificado, error que te costó tiempo, técnica de diseño que funcionó, comprobación nueva del auditor) va ahí en el mismo PR, como una viñeta breve en su apartado, con cómo se verificó.
- Si un aprendizaje revela un fallo en algo ya hecho (aldeas u otra estructura), corrígelo si es pequeño y está claro; si no, apúntalo en el apartado «Fallos pendientes».
- No borres ni reescribas viñetas ajenas; si una resulta falsa, márcala como corregida y explica por qué.

## Código común (`tools/gen/unicas/_comun/`): turno único
- Solo hay un módulo por función: `redstone.py` (simulación y puzles), `botin.py` (tablas, objetos con nombre, libros, pociones) y `piezas.py` (generador, guardián, cofre, cartel, puertas de pistones, trampas, escalera de caracol, conexiones). Si hace falta un recorrido de auditoría común, va en `recorrido.py`.
- Nunca crees otro módulo que haga lo mismo. Amplía el existente y conserva la compatibilidad con quien ya lo usa.
- Los PR que tocan `_comun/` se fusionan **de uno en uno y por turno**: antes de empezar, `git fetch origin develop && git merge origin/develop`, y construye sobre lo que haya en ese momento. Si al terminar `develop` ha cambiado en `_comun/`, vuelve a fusionar y adapta tu código, no el de develop.

## Rendimiento: requisito obligatorio
Toda sesión de desarrollo y toda auditoría verifican que el código esté optimizado al máximo para que el rendimiento del juego no se resienta. Lo que no lo cumpla no se fusiona.
- **Generación del mundo:** sin búsquedas ni recorridos innecesarios por chunk, colocaciones y comprobaciones de bioma baratas, nada de cálculos pesados repetidos (si un valor no cambia, se calcula una vez y se guarda), y plantillas sin bloques ni entidades sobrantes. Mide el tiempo de generación de tu estructura en el servidor de prueba y anótalo en el PR.
- **Por tick:** ningún trabajo por tick que recorra el mundo o entidades. Las funciones periódicas (mcfunction) con selectores acotados y la frecuencia mínima que cumpla su función.
- **Entidades:** pocas, y solo las que tienen sentido. Generadores con un radio y un límite razonables. Nada de mobs persistentes de sobra que carguen el servidor.
- **Java y mixins:** nada en el hilo del servidor que bloquee. Sin reservas de memoria en rutas calientes. Los mixins con el punto de inyección más estrecho posible y salida temprana barata.
- **Comprobación:** en el PR, di qué has medido (tiempo de generación, número de entidades, coste de los mixins) y cómo.

## Reglas del proyecto
- **Reutiliza siempre que se pueda.** Antes de escribir una función o una clase, busca si ya existe algo que haga lo mismo (en `tools/gen/core.py`, `build.py`, `loot.py`, `lint.py`, `render.py`, en otros módulos de `tools/gen/unicas/` o en el Java del mod) e impórtalo. Si lo que necesitas es casi igual que algo de otra estructura, saca lo común a un módulo compartido (por ejemplo `tools/gen/unicas/_comun/` o `build.py`; en Java, un paquete común) y haz que las dos lo usen, en lugar de copiarlo. Sin duplicados: escaleras de caracol, puertas secretas, trampas, generadores, guardianes, cofres y tablas de botín deben salir de piezas comunes y parametrizadas.
- Todo cambio en `src/`, recursos o generador va en `CHANGELOG.md` en el mismo commit: viñeta para jugadores si se nota en el juego, viñeta técnica siempre que sea interno. No reescribas viñetas ajenas.
- README al día si cambian funciones, comandos, configuración o cifras.
- `README.md` (inglés) y `README.es.md` (español) se mantienen sincronizados en cada cambio: mismas secciones, mismo orden y mismos datos.
- Datos primero (JSON, datapack, generador en Python); Java solo donde los datos no llegan. Mixins solo como último recurso, justificados en una línea.
- Todo texto para el jugador con clave de traducción en `es_es` y `en_us` (con `fallback` en español en `tellraw`).
- Registros con ids bajo `heraldia`; no se renombra un id publicado.
- Nada de trabajo por tick que recorra el mundo; nada que bloquee el hilo del servidor; la generación ocurre en varios hilos.
- No subas datos de Mojang (mcmeta) al repositorio.
- Di siempre qué has comprobado y cómo (compilado, cargado en servidor, validado, auditado, simulado) y qué no. El aspecto visual no se da por bueno sin capturas del juego de Alberto.

## Decisiones de Alberto (14-11-2026)
Aldeas (configurables, fichero de configuración del mod con valores por defecto y rangos validados):
- Separación entre aldeas configurable de **1.000 a 10.000 bloques**, por defecto **1.500**.
- Máximo **100 aldeas** por mundo: solo valen las 100 casillas de la rejilla de colocación más cercanas al 0,0 (determinista, sin datos guardados).
- Configurables también: proporción estándar/grande, límite de gólems (y activar/desactivar la limpieza), activar/desactivar familias y estilos, distancia mínima a aldeas vanilla.

Estructuras únicas:
- Enemigos: generadores en mazmorras **y** guardián final.
- Puzles **y** trampas de redstone.
- Estado: 80-85 % de la superficie en buen estado; el resto, detalles ruinosos.
- Lootr: el mod detecta si Lootr está cargado; si lo está, botín más modesto por cofre (cada jugador abre el suyo). Si no se pudiera detectar, se supone que no está.
- Rareza por defecto: una cada **3.000-5.000 bloques**, cada tipo en su bioma; configurable.
- Mapas del tesoro hacia las estructuras únicas: en cofres épicos de las aldeas **y** a la venta en cartógrafos.
- Aldeanos o gólems dentro: según la estructura.
- Cofre premium: 90 % vistoso y no poderoso (objetos con nombre, encantamientos moderados, adornos de armadura, discos) y 10 % algo más fuerte sin romper la progresión. Nada de netherita en equipo ni élitros. Solo vanilla.
- Por dentro bien construidas, exploración minuciosa: cofres menores repartidos, salas ocultas y cámara final con el cofre premium.
- Atlántida: una sola por mundo (siempre 1, no configurable), sumergida en un océano grande, la mayor que permita el juego (ver su propia sesión).

## Lecciones técnicas de 26.3 (todas costaron un fallo real)
- Pack format 121; DataVersion 5023 en los NBT.
- El juego rechaza el paquete entero si una estructura no se puede leer. `max_distance_from_center` + 12 no puede pasar de 128 (máximo 116). Síntoma: "Registry loading errors" en `logs/latest.log`. La validación lo comprueba.
- `/reload` no recarga worldgen. En un mundo existente solo aparecen en chunks nuevos; para probar, `/place structure <id>` (necesita los chunks cargados: `forceload`).
- Un `fill` posterior puede sobrescribir un jigsaw sin ningún error: coloca los jigsaws al final y comprueba que siguen ahí.
- Todo conector horizontal debe estar en la cara de la caja envolvente de la pieza.
- Las piezas de la profundidad máxima solo procesan jigsaws a través del `fallback` del pool.
- Una pieza rígida queda con y=0 un bloque por encima del terreno; la calle (`terrain_matching`) a ras de suelo. Hace falta un peldaño de acceso.
- Con `beard_thin` el terreno se ajusta a la base de la caja: una pieza que baja hunde el terreno alrededor. Para sótanos de verdad hay que resolverlo a propósito (otra adaptación, piezas subterráneas separadas, relleno de la huella; mira cámaras de prueba y ciudad antigua).
- El jigsaw no detecta agua; situar algo respecto al agua requiere Java.
- Jigsaw con `final_state` `structure_void` no coloca nada: solo donde quieras conservar el terreno.
- Bloques sin soporte válido desaparecen sin aviso. No está verificado que el agua colocada fluya.
- Valida nombres contra los registros (la cadena es `iron_chain`). Compara nombres de bloque exactos: "stairs" contiene "air".
- Semántica: en escaleras `facing` es el lado alto; escalera de mano `facing=east` va pegada al muro oeste; cabecera de la cama hacia `facing`; trampilla abierta `facing=north` queda en el borde sur.

## Criterio de diseño (Alberto: "diseñador profesional y minimalista")
- Ninguna escalera sin terminar ni saltos; ninguna puerta sin salida ni estancia inaccesible.
- Muebles pegados a un muro, sin tapar ventanas; centro libre salvo mesa con sillas (respaldo hacia fuera).
- Nada flotando: faroles colgados de algo, cadenas con enganche, agua nunca suelta.
- Simetría donde el edificio la pide; cada elemento con una función reconocible.
- Método: auditoría automática como condición para generar (`tools/gen/lint.py`), planos de planta por nivel con celdas alcanzables, renders isométricos (`tools/gen/render.py`).
