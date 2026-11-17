# Heraldia: instalación, comandos y configuración

[English](CONFIGURATION.md) · **Español**

Volver al [README](../README.es.md).

## Instalación

Requisitos: Minecraft 26.3, Fabric Loader 0.20.1 o superior y Fabric API (probado con 0.166.2+26.3). Opcional en el cliente: Mod Menu (compilado contra la 21.0.1), para la [pantalla de configuración](#pantalla-de-configuración-cliente).

1. Compila `heraldia-<versión>.jar` (ver abajo).
2. Cópialo en la carpeta `mods` del servidor. En los clientes es opcional: con el cliente vanilla se juega igual (los textos que no conoce salen en español, salvo la Guía, que llega en el idioma de cada jugador); con el mod, todo sale en su idioma y está la pantalla de configuración.
3. Arranca el servidor. En `logs/latest.log` debe aparecer `Heraldia: 164 estructuras registradas`.

En un mundo existente las estructuras solo aparecen en chunks que todavía no se han generado.
`/reload` no recarga la generación del mundo: hay que reiniciar el servidor (o salir y volver a entrar al mundo en un solo jugador).

## Comandos de prueba

- Colocar una aldea donde estés: `/place structure heraldia:llanuras_castellana` (o `..._grande`). Funciona aunque no estés en su bioma.
- Buscar la más cercana: `/locate structure heraldia:llanuras_castellana`
- Colocar una pieza suelta: `/place template heraldia:llanuras_castellana/specials/church`
- `/function heraldia:muestrario`: coloca las 72 aldeas en cuadrícula a partir de donde estés (cada fila, hacia el sur, es una familia; en cada fila van los 3 estilos y luego sus versiones grandes, hacia el este, separadas 300 bloques). Te pone en espectador y te lleva de una a otra, una cada 8 s (unos 10 min). Al terminar vuelves a creativo.
- `/function heraldia:familia/<familia>` (`llanuras`, `bosque`, `oscuro`, `taiga`, `nieve`, `desierto`, `sabana`, `jungla`, `pantano`, `cerezos`, `badlands`, `costa`): lo mismo con las 6 aldeas de una familia, en fila hacia el este.
- `/function heraldia:muestrario/parar`: lo detiene.
- `/heraldia key <players> <key>` (operadores, nivel 2): da las llaves de los cofres cerrados de las estructuras únicas, el mismo objeto que se consigue en el juego. `<key>` se autocompleta: `all` (todas), una estructura (`atlantida`: sus cuatro llaves) o una llave suelta (`atlantida.arsenal`, `atlantida.academia`, `atlantida.anfiteatro`, `atlantida.poseidon`). Si el inventario está lleno, la llave cae al suelo a nombre del jugador.
- `/heraldia info` (operadores, nivel 2): resumen de la configuración en uso (aldeas, estructuras únicas activadas y su separación, distancia mínima, cofre por jugador, si está instalado Lootr, estructuras medianas, entradas a mina y el multiplicador de las minas vanilla) y de cuántas estructuras hay registradas.
- `/heraldia info nearby [radius]`: la estructura única y la mediana más cercanas de cada tipo, la entrada a mina más cercana de cada tamaño y la aldea Heraldia más cercana, con distancia, rumbo y coordenadas (al pulsarlas se propone un `/tp`). Usa la misma comprobación que `/locate`, así que nunca señala una estructura que la distancia mínima descarta, pero no carga ni genera chunks: lo que aún no se ha generado sale como «prevista» (de una aldea prevista solo se sabe la familia). Radio por defecto 3.000 bloques, máximo 10.000; el mensaje dice cuánto ha tardado la búsqueda.
- `/heraldia quest [list | accept <number> | abandon <number> | turnin]` (cualquier jugador, sin permisos): dentro de una aldea de Heraldia, sin argumentos, su [tablón de encargos](CONTENIDO.md#vida-de-las-aldeas) (lo mismo que tocar el atril); fuera, tus encargos. `accept <number>` coge el encargo número N del tablón de la aldea en la que estás; `list`, tus encargos (hasta 5), cómo van y tu reputación con cada aldea; `abandon <number>` deja uno de los tuyos; `turnin` entrega, en la aldea que los dio, los cumplidos (los de traer, si llevas los objetos). Los botones del tablón ejecutan estas mismas órdenes.
- `/heraldia wizard [reveal]` (operadores, nivel 2): las [chozas de mago](CONTENIDO.md#chozas-de-mago). Sin nada, los magos a menos de 32 bloques con su estado (bondadoso, malvado sin revelar, aún sin decidir); `reveal` revela el más cercano sin revelar aunque sea bondadoso (para probar el Mago Malvado y su botín).
- `/heraldia caravan [spawn [raid | peaceful] | raid | list | clear]` (operadores, nivel 2): las [caravanas](CONTENIDO.md#caravanas). `spawn` saca una junto a ti (a menos de 80 bloques de un camino de Heraldia, con su salida en chunks cargados y el camino de verdad en el mundo; sin esperar al sorteo de `caravanas.frecuencia`, pero con `caravanas.activado` y `caravanas.max_activas`); `spawn raid` la saca con asalto seguro y `spawn peaceful`, sin asalto. `raid` fuerza ya el asalto de la más cercana; `list`, las que están en camino (de qué aldea a cuál, si la asaltan, por qué vértice van y dónde está el mercader); `clear` las quita todas, con sus entidades.
- `/heraldia guide` (cualquier jugador, sin permisos): te da una copia al día de la [Guía del Heraldo](CONTENIDO.md#guía-del-heraldo) (si llevas una en el inventario, la cambia por la nueva).
- `/heraldia profile` (operadores, nivel 2): el [perfil de juego](#perfiles-de-juego) en uso (el efectivo y el elegido en el fichero) y el valor que da a cada una de sus opciones, marcando las fijadas a mano en el fichero, que mandan sobre él.
- `/heraldia info here`: en qué estructura Heraldia estás (nombre e id) y, en una única, si su guardián vive (solo se responde si toda la estructura está cargada).

Usa el muestrario solo en un mundo de prueba: lo colocado se queda.

Todos los comandos y subcomandos del mod tienen nombre en inglés, para que sean los mismos en cualquier servidor sea
cual sea su idioma (lo que lee el jugador sigue traducido). Los nombres en español de antes (`/heraldia guia`, `llave`,
`info cerca`, `info aqui`, `arena colocar`/`mover`/`quitar` [`confirmar`], `arena empezar`/`parar`/`salir` y la llave
`todas`) siguen funcionando como alias ocultos: hacen lo mismo, no salen en el autocompletado y avisan de que están
obsoletos, con el nombre nuevo. Se quitarán en una versión futura.

| Nombre antiguo | Nombre nuevo |
|---|---|
| `/heraldia guia` | `/heraldia guide` |
| `/heraldia llave <jugadores> <todas\|...>` | `/heraldia key <players> <all\|...>` |
| `/heraldia info cerca [radio]` | `/heraldia info nearby [radius]` |
| `/heraldia info aqui` | `/heraldia info here` |
| `/heraldia arena colocar [confirmar]` | `/heraldia arena place [confirm]` |
| `/heraldia arena mover [confirmar]` | `/heraldia arena move [confirm]` |
| `/heraldia arena quitar [confirmar]` | `/heraldia arena remove [confirm]` |
| `/heraldia arena empezar` | `/heraldia arena start` |
| `/heraldia arena parar` | `/heraldia arena stop` |
| `/heraldia arena salir` | `/heraldia arena leave` |

## Herramientas de administración

### Ruta de revisión: `/heraldia review`

Para operadores (nivel 2). Una ruta guiada para validar en una tarde todo el contenido visual del mod, parada a parada: una aldea de cada familia, cada estructura única (con la Atlántida y la Isla del corsario), cada tipo de estructura mediana, una entrada a mina de cada tamaño, la arena (si está activada) y un tramo de camino (si hay caminos). Lo desactivado en la configuración no sale.

- `/heraldia review`: va a la parada en la que estás (la primera, la primera vez). En cada parada sale un título en pantalla, la lista de qué mirar en el chat (traducida, como todo) y botones para marcarla: **Revisada**, **+ Nota** (revisada con una nota) y **Problema** (escribe qué falla detrás de la orden), además de **Saltar**, **Anterior**, **Siguiente** y **Lista**.
- `/heraldia review next`, `previous`, `skip [note]` (la deja como saltada y pasa a la siguiente), `goto <id>` (p. ej. `goto unica/castillo`; se autocompleta), `list` (todas las paradas con su estado; al pulsar una vas a ella), `reset` (borra tus marcas) y `status` (el resumen: cuántas revisadas, con problema, saltadas y pendientes, y la lista de problemas).
- `/heraldia review mark checked [note]` y `/heraldia review mark problem [note]`: lo que hacen los botones.
- La búsqueda va fuera del hilo del servidor, con las mismas reglas que `/heraldia info nearby` (desde el punto de aparición, hasta 10.000 bloques; la Atlántida, en todo el mundo), y nunca carga ni genera chunks: prefiere una estructura ya generada, aunque esté más lejos, a una prevista. Si la más cercana aún no se ha generado, te avisa de que ir allí genera terreno nuevo y espera a que pulses **Ir y generar** (`goto <id> generate`).
- El teletransporte carga el destino sin bloquear el servidor y te deja encima del suelo, sin asfixia: pies y cabeza libres, suelo firme o agua debajo (flotando en el mar en la Atlántida o la isla), nunca en lava, fuego, magma, cactus ni nieve polvo, buscando en espiral hasta 8 bloques alrededor. Si no hay ningún sitio seguro, no te mueve.
- El progreso es de cada jugador y se guarda en `heraldia_revision.json`, en la carpeta del mundo (sobrevive a los reinicios). Cada cambio escribe también `heraldia_revision.md` en la misma carpeta: por jugador, todas las paradas con su estado, su nota y la fecha, primero las que tienen un problema.

### Estado del servidor: `/heraldia status [page]`

Para cualquier jugador, traducido y paginado (8 líneas por página, con botones para pasar de página): la versión de Heraldia, cuántas estructuras de cada clase ha descubierto algún jugador frente al total (aldeas, una de cada familia; únicas; medianas, por tipo; minas, por tamaño), los guardianes vencidos, el estado de la arena con el récord del servidor, los encargos del tablón entregados entre todos y por ti (con cuántas aldeas te tienen por amigo y de cuántas eres héroe), las caravanas en camino (con su máximo y sus probabilidades) y cuántas han llegado o se han perdido desde el arranque, si está activado el botín que se repone y si está Lootr. Los operadores ven además la dificultad, las opciones clave de la generación, de los jefes y de la Guía, qué falta por descubrir de cada clase y los otros mods cargados. Lo descubierto sale de los logros: los de los jugadores conectados, de memoria; los de los demás, de sus ficheros en la carpeta del mundo (leídos fuera del hilo del servidor).

### Aviso de versión nueva: `/heraldia update check`

Al arrancar el servidor y cada 24 horas, en un hilo propio (nunca retrasa el arranque ni el servidor), el mod pregunta a
la API de GitHub Releases del proyecto (donde se publica, junto con CurseForge) si hay una versión más nueva de Heraldia
para la versión de Minecraft del servidor: comparación semántica de versiones, sin las pre-publicaciones (salvo con
`update_check.prereleases`), y la versión de Minecraft de cada publicación sacada del `gradle.properties` de su etiqueta.
Si la hay, lo dice en la consola y, en el chat, a cada operador al entrar (una vez por sesión del servidor), en su
idioma, con un enlace clicable a la descarga y la recomendación de **hacer una copia de seguridad del servidor antes de
actualizar**. `/heraldia update check` (operadores, nivel 2) lo comprueba en el momento y responde en el chat.

Sin telemetría: una petición GET con un `User-Agent` genérico y sin datos del servidor ni de sus jugadores, con tiempos
de espera cortos (5 s para conectar, 10 s para responder). Sin red o con una respuesta rara, solo deja una línea en el
log. Se desactiva con `update_check.activado = false`.

### Mapas web: `/heraldia webmap refresh`

Si el servidor tiene [BlueMap](https://modrinth.com/plugin/bluemap), [Dynmap](https://modrinth.com/plugin/dynmap) o [squaremap](https://modrinth.com/plugin/squaremap) (dependencias opcionales: sin ninguno no cambia nada), Heraldia pone en el mapa web sus estructuras, cada clase en su propia capa que se puede ocultar: estructuras únicas, aldeas, estructuras medianas, entradas de mina y la arena de oleadas. Cada marcador lleva el icono de su capa, el nombre de la estructura en el idioma de `mapas_web.idioma` y una descripción breve. Detalles y versiones probadas en [Compatibilidad](COMPATIBILIDAD.md#mapas-web-bluemap-dynmap-y-squaremap).

- Qué sale: las estructuras de Heraldia de los chunks que se han cargado alguna vez desde que hay un mapa web (se apuntan al cargarse cada chunk y se guardan en `heraldia_mapas_web.json`, en la carpeta del mundo) y la arena colocada. Con `mapas_web.solo_descubiertas` (por defecto), solo las de un tipo que algún jugador ya ha descubierto, con los mismos logros que cuenta [`/heraldia status`](#estado-del-servidor-heraldia-status-page): una aldea, cuando alguien tiene el logro de su familia; una única, el de descubrirla; una mediana, el criterio de su tipo; una entrada de mina, el de su tamaño. La arena sale siempre.
- Cuándo se actualiza: al arrancar, en cuanto alguien consigue un logro de Heraldia, al aparecer una estructura nueva, tras [`/heraldia reload`](#recarga-en-caliente-heraldia-reload) (las opciones `mapas_web.*` se recargan) y con `/heraldia webmap refresh` (operadores, nivel 2: vuelve a leer los logros de todos los jugadores y dice cuántos marcadores ha puesto). Todo va en un hilo propio, como mucho una actualización cada 2 s; en el hilo del servidor solo se mira la lista de inicios de estructura de cada chunk que se carga.

### Búsqueda del tesoro: `/heraldia treasure`

Para operadores (nivel 2), para probar la [caza del tesoro](CONTENIDO.md#caza-del-tesoro):

- `/heraldia treasure give [players]`: da un fragmento de mapa del tesoro sin descifrar (la tabla `heraldia:tesoro/fragmento`) a los jugadores (sin argumento, a quien lo ejecuta).
- `/heraldia treasure info`: la cadena del mapa que llevas en la mano principal: semilla, marca en curso y cada destino (tipo, coordenadas clicables, estructura o bioma, generada o prevista) y, si ya está, dónde se enterró el cofre. También la deja en el log («Heraldia: tesoro: info {…}»).

El jugador no necesita comandos: usa el fragmento y el mapa con clic derecho. El log dice cuánto tardó en elegirse cada cadena (fuera del hilo del servidor) y en buscarse el sitio de cada cofre.

### Recarga en caliente: `/heraldia reload`

Para operadores (nivel 2). Vuelve a leer `config/heraldia.json` sin reiniciar el servidor (sin reescribirlo) y aplica lo que no afecta a la generación:

- `dificultad.*`: se recalculan los modificadores de vida y daño de los mobs de Heraldia ya cargados (los demás, al cargarse), conservando la proporción de su vida actual.
- `jefes.*`, `botin.*`, `guia.*`, `aldeas.vida.tratos_estilo`, `aldeas.vida.asedios` (los tratos se sortean al subir de nivel un aldeano), `unicas.atlantida.cofre_unico_por_jugador`, `mapas_web.*` (los marcadores se rehacen al recargar), `tesoro.*` (al tirar el botín y al usar una pista), `encargos.*`, `reputacion.*`, `chozas_mago.*` (al decidir cada choza) y `caravanas.*` (con `caravanas.activado` a `false`, la caravana en camino se va): se leen cada vez que se usan.
- `perfil` (el [perfil de juego](#perfiles-de-juego)): se aplica entero, con lo fijado a mano encima (todas sus opciones son de estas).
- `golems.*`: se publican otra vez los límites a las funciones de los gólems.
- `arena.*` (salvo `arena.generar_en_mundos_nuevos`, que solo cuenta al arrancar un mundo nuevo): incrementos, máximo de vivos, experiencia, modos y si está activada. Con una partida en marcha no cambian hasta que acabe (vuelve a recargar entonces), salvo `arena.temporada.*`, que se aplica siempre (el histórico se recorta en el acto; el día y la hora cuentan desde ese momento).

Todo lo demás (rejillas y separaciones, aldeas, familias y estilos, el tablón, los caminos, las únicas, las medianas, las minas, la compatibilidad y la distancia mínima) afecta a la generación: si cambiara a medias, dos chunks vecinos se generarían con reglas distintas y `/locate` y los mapas dejarían de coincidir con lo generado. Esas opciones no se aplican: la respuesta las lista con su valor en uso y el del fichero, y se aplican al reiniciar. Una opción nueva del mod es de este grupo salvo que se declare recargable.

### Panel de configuración en el juego: `/heraldia config`

Para operadores (nivel 2), **sin el mod en el cliente**: abre un diálogo vanilla (la Dialog API del servidor). Arriba, el perfil de juego en uso y un botón por perfil (casual, estándar, hardcore); debajo, siete apartados con 5 a 8 opciones cada uno: **Mundo y generación**, **Aldeas y caminos**, **Combate y jefes**, **Botín**, **Arena**, **Jugadores y Guía** y **Avanzado**. Cada opción lleva una frase que la explica, el valor recomendado (el del perfil elegido o el de por defecto) y, si no se aplica en caliente, el aviso «[se aplica al reiniciar]». **Guardar** escribe `config/heraldia.json` y aplica por el mismo camino que [`/heraldia reload`](#recarga-en-caliente-heraldia-reload): lo recargable ya, lo demás queda guardado y se dice que espera al reinicio. Lo que no está en los apartados se cambia en el fichero.

Desde la consola, `/heraldia config` lista lo mismo en texto y `/heraldia config set <opción> <valor>` cambia cualquier opción (con el mismo camino de recarga).

### Idioma de cada jugador: `/heraldia language`

Para todos. `/heraldia language` dice en qué idioma te escribe Heraldia y da un botón por idioma (los 8 del mod); `/heraldia language <código>` (`es_es`, `en_us`, `fr_fr`, `de_de`, `it_it`, `pt_br`, `ca_es`, `gl_es`) lo fija y `/heraldia language auto` vuelve al de tu juego. Se guarda con el jugador y manda sobre el idioma del cliente en los textos del mod (Guía, encargos, arena, caravanas, avisos). Un cliente sin el mod los ve en el idioma elegido; uno con el mod traduce las claves con su propio idioma.

## Actualizar un servidor

Guía para administradores (política permanente: ninguna versión cambia lo ya construido sin tu permiso).

1. **Antes de actualizar**: para el servidor y haz una copia del mundo y de `config/`. Cambia el `.jar` de Heraldia y arranca.
2. **Al arrancar** con la versión nueva, nada cambia en lo ya generado: lo nuevo de la generación sale en los chunks nuevos. El mod guarda en el mundo con qué versión se generó y con cuál se abrió (lo dice el log: «mundo generado con la versión …»; un mundo de antes de esto queda como `anterior`), migra `config/heraldia.json` si su formato cambió (dejando `heraldia.json.v<versión>.bak` con el de antes) y aplica, una sola vez por mob al cargarse, los **arreglos** de fallos ya corregidos que pudieran quedar de versiones anteriores: guardianes de la 0.1.0 sin marcas (se anclan para no pasear fuera de su sala, no recogen objetos y pasan a ser jefes), bebés, ahogados montados en nautilos zombis. El de las armas cambiadas solo avisa (no se sabe cuál era). `/heraldia update repair dry-run` dice qué cambiaría en lo cargado; `/heraldia update repair` lo fuerza.
3. **`/heraldia update analyze`** (operadores): informe de qué haría llevar lo nuevo a lo ya generado. **No cambia nada.** Lee las regiones del mundo principal en un hilo propio (unos minutos en un mundo grande) y deja en `<mundo>/heraldia/actualizar/` el informe (`analisis-<fecha>.txt`), un mapa en texto y una imagen (`mapa-<fecha>.txt` y `.png`: `#` construcción, `P` protegido, `R` se regenera, `v` virgen que se conserva, `E` estructura nueva, `.` generado, `S` spawn). Detecta las construcciones de los jugadores combinando:
   - bloques típicos de jugador (camas, cofres, barriles, carteles, mesas, hornos, raíles, vallas, puertas, antorchas, tablones, cristal…) fuera de las piezas de las estructuras guardadas;
   - diferencias con la regeneración con la misma semilla (la cima de 16 columnas por chunk frente al terreno del generador, sin contar árboles, nieve, fluidos ni plantas) en los chunks por donde ha pasado alguien;
   - el InhabitedTime (desde 1 hora de jugadores cerca, el chunk cuenta como construcción);
   - el spawn del mundo, las camas y puntos de reaparición y la última posición de cada jugador (también de los desconectados);
   - las zonas reclamadas con mods de protección: si hay uno conocido (Flan, GOML, FTB Chunks, Open Parties and Claims…), no se pueden leer, el informe lo dice y `apply` no se ejecuta.
   Alrededor de cada construcción hay un **margen de 50 bloques** (`actualizar.margen_bloques`, de 16 a 256): ahí no se borra ni se coloca nada.
   - **Vía A**: los chunks **vírgenes** (generados del todo, con menos de 1 minuto de jugadores cerca y sin construcciones ni margen) se borran para que se vuelvan a generar con lo nuevo cuando alguien se acerque. Solo los que no dejarían una estructura cortada: si lo que saldría ahora en ese chunk (o lo que había) toca un chunk que se queda, el chunk se conserva.
   - **Vía B**: las estructuras nuevas de Heraldia que hoy saldrían en un chunk ya generado se colocan solo en sitios seguros: toda su caja fuera de cualquier chunk protegido y sin pisar otra estructura.
4. **`/heraldia update apply`**: el mismo análisis y un diálogo (en la consola, las órdenes) para confirmar:
   - **Copia y aplicar**: copia antes los ficheros de región, entidades y PDI afectados a `heraldia/actualizar/copia-<id>/`.
   - **Aplicar sin copia**: pide una segunda confirmación explícita del riesgo (no se podrá deshacer).
   Al confirmar, se avisa a los jugadores y **el servidor se para** a los 10 s. **Arráncalo tú a mano**: al arrancar, antes de cargar el mundo, se hace la copia y se borran los chunks vírgenes (si alguien pasó por uno desde el análisis, se deja); con el servidor en marcha se colocan las estructuras nuevas y queda el informe `informe-<id>.txt`.
5. **Deshacer**: `/heraldia update undo` (si hubo copia) pide confirmación, para el servidor y, al arrancarlo a mano, restaura las regiones copiadas. Lo que cambió en ellas desde el apply se pierde.

Limitaciones: solo el mundo principal; las estructuras colocadas en chunks ya generados no ajustan el terreno a su alrededor (como `/place structure`); si el mundo se generó con otra versión de Minecraft, los chunks regenerados pueden no casar con el terreno de al lado.

## Configuración

Fichero `config/heraldia.json` del servidor (en un mundo de un jugador, el de la carpeta del juego). Se crea al arrancar con todos los valores por defecto
y se reescribe en cada arranque con los valores en uso y una ayuda (`_ayuda`) en español e inglés (las opciones del [perfil de juego](#perfiles-de-juego), solo si están fijadas a mano; el bloque `_perfil`, informativo, dice el perfil efectivo y sus valores). Un valor que no sea válido (fuera de rango o de otro tipo)
se avisa en el log y se sustituye por el de por defecto; una opción desconocida se avisa y se ignora. El campo `version` permite migrar el fichero
cuando cambie su formato. Se lee al arrancar el servidor y afecta a los chunks que se generen después (no a lo ya generado); lo que no afecta a la generación se puede aplicar sin reiniciar con [`/heraldia reload`](#recarga-en-caliente-heraldia-reload).

| Opción | Por defecto | Rango | Qué hace |
| --- | --- | --- | --- |
| `perfil` | `estandar` | `casual`, `estandar`, `hardcore`, `personalizado` | [Perfil de juego](#perfiles-de-juego): fija de golpe la dificultad, los refuerzos, el botín que se repone y la arena; nunca la generación del mundo. |
| `aldeas.separacion_bloques` | 1500 | 1000-10000 | Separación media entre aldeas; la mínima guarda la proporción 62/94 de la rejilla. |
| `aldeas.maximo` | 100 | 0-100 | Máximo de aldeas por mundo: solo valen las casillas de la rejilla más cercanas al 0,0 (determinista, sin datos guardados). |
| `aldeas.porcentaje_grandes` | 25 | 0-100 | Porcentaje de aldeas grandes; el resto son estándar. |
| `aldeas.distancia_aldeas_vanilla_bloques` | 160 | 0-256 | Distancia mínima a una aldea vanilla (se redondea a chunks); 0 la desactiva. |
| `aldeas.familias.<familia>` | `true` | `true`/`false` | Activa una familia entera (sus 3 estilos). |
| `aldeas.estilos.<estilo>` | `true` | `true`/`false` | Activa un estilo (estándar y grande). Si una casilla elige uno desactivado, se prueba otro estilo de su bioma. |
| `aldeas.vida.tratos_estilo` | `true` | `true`/`false` | Tratos propios de cada estilo y mapa de la única de la zona en los cartógrafos de cada familia ([Vida de las aldeas](CONTENIDO.md#vida-de-las-aldeas)). |
| `aldeas.vida.tablon` | `true` | `true`/`false` | Tablón de encargos y alguacil en la plaza de las aldeas nuevas. |
| `aldeas.vida.asedios` | `false` | `true`/`false` | El armero de las aldeas fortificadas vende una botella ominosa para provocar un asalto de saqueadores. |
| `aldeas.caminos.activado` | `true` | `true`/`false` | Caminos entre aldeas cercanas, con puentes, farolas y carteles ([Caminos entre aldeas](CONTENIDO.md#caminos-entre-aldeas)); solo en los chunks nuevos. Desactivado, el rasgo ni se añade a los biomas. |
| `aldeas.caminos.distancia_maxima_bloques` | 2000 | 500-4000 | Solo se unen aldeas a menos de esta distancia. Dos aldeas nunca están a menos de unos 670 bloques (con la separación mínima, 1000), así que con menos de eso no habría ningún camino. |
| `aldeas.caminos.ancho` | 3 | 1-5 | Ancho de los caminos, en bloques. |
| `golems.limpieza` | `true` | `true`/`false` | Activa la retirada periódica de gólems naturales. |
| `golems.limite_estandar` | 8 | 1-64 | Con tantos gólems naturales o más, una aldea estándar retira uno cada 30 s. |
| `golems.limite_grande` | 9 | 1-64 | Igual para las aldeas grandes. |
| `unicas.<id>.activada` | `true` | `true`/`false` | Activa una estructura única. Aparece una entrada por cada estructura única del mod. |
| `unicas.<id>.separacion_bloques` | la de la estructura (4000) | 1000-10000 | Separación media entre estructuras de ese tipo (por defecto, una cada 3000-5000 bloques). Cada tipo se reparte por toda su casilla de la rejilla (con el origen desplazado por tipo) y dos del mismo tipo nunca quedan a menos de `unicas.distancia_minima.bloques`. En el Laboratorio del micólogo (campos de champiñones, un bioma muy raro) la candidata de cada casilla no se sortea: es el sitio de la casilla más metido en ese bioma, así que sale en buena parte de las islas de champiñones (como mucho una por casilla). La Mina perdida hace lo mismo con las cuevas exuberantes y de espeleotemas, mirando a la altura de la caverna (y = 26) en vez de al nivel del mar, y la Isla del corsario con sus océanos (el sitio más metido en mar abierto). |
| `unicas.rejilla_compatible` | `false` | `true`/`false` | **Ponlo a `true` en un mundo creado con una versión anterior de Heraldia (0.1.0)**; déjalo en `false` en un mundo nuevo. Las rejillas de colocación de las únicas cambiaron después de la 0.1.0 (el origen de la rejilla de cada tipo va desplazado y la separación interna es la distancia mínima), así que en un mundo antiguo `/locate`, los mapas del tesoro, los pliegos de la Crónica, `/heraldia info nearby` y la distancia mínima ya no encuentran las únicas ya generadas en lo explorado (aunque siguen ahí). Activada, las 14 únicas que ya estaban en la 0.1.0 (acueducto, castillo, catedral, ciudadela, coliseo, faro, fortaleza de hielo, galeón, mansión, monasterio, observatorio, palacio, pirámide y torre de mago) vuelven a la rejilla de esa versión, bit a bit, para la misma semilla y configuración y con el mismo coste. Las añadidas después (Salón del Jarl, Santuario druídico, Laboratorio del micólogo, Mina perdida e Isla del corsario) siguen con la rejilla nueva, y las antiguas tienen prioridad sobre ellas: una nueva se descarta si cae a menos de la distancia mínima de una antigua que sale, así que nunca aparece encima de una ya generada. No afecta a las aldeas ni a la Atlántida (su colocación no cambió; la Atlántida conserva su posición guardada). |
| `unicas.distancia_minima.activada` | `true` | `true`/`false` | Impide que dos estructuras únicas distintas (también la Atlántida) salgan a menos de la distancia mínima. |
| `unicas.distancia_minima.bloques` | 1000 | 100-3000 | Distancia mínima entre los chunks de inicio de dos estructuras únicas distintas. Si dos candidatas quedan demasiado cerca, un sorteo determinista (semilla y posición) se queda con una; si la ganadora no puede salir ahí (bioma o terreno), se conserva la otra. `/locate` y los mapas del tesoro siguen la misma regla. |
| `unicas.atlantida.cofre_unico_por_jugador` | `false` | `true`/`false` | Cofre premium de la Atlántida por jugador. La primera apertura convierte su contenido en una plantilla guardada en el propio cofre (que queda vacío: romperlo o vaciarlo con una tolva no duplica nada) y cada jugador abre su propia copia: la recibe entera la primera vez y después encuentra lo que dejó. Sigue haciendo falta la llave de Poseidón. Con Lootr o sin él funciona igual (Lootr no convierte este cofre porque no tiene tabla de botín). Si se desactiva después, el contenido vuelve al cofre una vez (la primera vez que alguien lo usa) y se comporta como antes. |
| `jefes.fases.activado` | `true` | `true`/`false` | Fases de los guardianes al bajar del 66 % y del 33 % de vida: efectos, partículas, sonido y aviso en la barra de acción ([Combates contra los guardianes](CONTENIDO.md#combates-contra-los-guardianes)); también los de las estructuras ya generadas. |
| `jefes.refuerzos.activado` | `true` | `true`/`false` | Refuerzos de los guardianes: 2 o 3 mobs de su estructura una vez por fase, como mucho `jefes.refuerzos.maximo_vivos` vivos a la vez; no sueltan el botín del guardián. Funciona aunque las fases estén desactivadas (entonces sin efectos y con otro aviso). |
| `jefes.refuerzos.porcentaje` | 100 | 0-300 | Cuántos refuerzos por fase, en % de los del guardián (redondeando; por encima de 100 su lista se repite): 150 = uno o dos más. |
| `jefes.refuerzos.maximo_vivos` | 4 | 1-12 | Refuerzos vivos a la vez junto a un guardián como mucho. |
| `jefes.barra.activado` | `true` | `true`/`false` | Barra de jefe con el nombre del guardián para los jugadores a menos de 32 bloques mientras dura el combate. |
| `medianas.activadas` | `true` | `true`/`false` | Activa las [estructuras medianas](CONTENIDO.md#estructuras-medianas). |
| `medianas.frecuencia_porcentaje` | 100 | 25-400 | Frecuencia de todas las medianas, en % de la de por defecto: 200 = el doble (la separación de cada tipo se divide por la raíz). |
| `medianas.distancia_minima.bloques` | 192 | 64-1024 | Distancia mínima entre dos medianas de tipos distintos (y entre dos del mismo, como mucho media casilla de su rejilla). |
| `medianas.distancia_aldeas_unicas_bloques` | 256 | 128-1024 | Una mediana no sale a menos de esta distancia del inicio de una aldea o una única de Heraldia que sale ahí. |
| `medianas.<id>.activada` | `true` | `true`/`false` | Activa un tipo de mediana (`torre_vigia`, `posada`, `campamento`, `ermita`, `molino`, `pescador`, `cazadores`, `templete`). |
| `medianas.<id>.separacion_bloques` | la del tipo (576-832) | 256-4000 | Separación media entre dos de ese tipo (con la frecuencia al 100 %); cada casilla busca su candidata dentro de los biomas del tipo. |
| `minas.entradas.activado` | `true` | `true`/`false` | Activa las [entradas a mina](CONTENIDO.md#entradas-a-mina) (solo en chunks nuevos). |
| `minas.entradas.separacion_bloques` | 768 | 256-4000 | Separación media entre dos entradas a mina pequeñas; las medianas y las grandes guardan la proporción (x1,5 y x2,5). |
| `minas.vanilla.multiplicador` | 2.0 | 1-5 | Multiplica la frecuencia de las minas abandonadas vanilla en los chunks nuevos (1 = vanilla; admite decimales, p. ej. 1.5). No cambia los chunks ya generados ni otras estructuras. |
| `faros.activado` | `true` | `true`/`false` | Activa los [faros](CONTENIDO.md#faros-y-naufragios) de la costa (solo en chunks nuevos). |
| `faros.separacion_bloques` | 1024 | 256-4000 | Separación media entre dos faros (solo salen donde hay costa: en la práctica, menos). |
| `naufragios.activado` | `true` | `true`/`false` | Activa los [galeones naufragados](CONTENIDO.md#faros-y-naufragios) (solo en chunks nuevos). |
| `naufragios.separacion_bloques` | 768 | 256-4000 | Separación media entre dos galeones naufragados (solo salen donde hay costa: en la práctica, menos). |
| `guia.entregar_al_entrar` | `true` | `true`/`false` | Da la [Guía del Heraldo](CONTENIDO.md#guía-del-heraldo) a cada jugador la primera vez que entra con cada versión del mod. Desactivada, nadie la recibe al entrar, pero `/heraldia guide` sigue dándola. |
| `update_check.activado` | `true` | `true`/`false` | [Aviso de versión nueva](#aviso-de-versión-nueva-heraldia-update-check): mira GitHub Releases al arrancar y cada 24 h y avisa a los operadores al entrar. Se aplica al reiniciar. |
| `update_check.prereleases` | `false` | `true`/`false` | Avisa también de las pre-publicaciones (alfa, beta, candidatas). |
| `actualizar.margen_bloques` | `50` | 16-256 | Margen de seguridad (bloques) alrededor de cada construcción que detecta [`/heraldia update analyze`](#actualizar-un-servidor): ahí no se regenera ni se coloca nada. |
| `compatibilidad.zona_estructuras_ajenas_bloques` | 224 | 0-512 | Las estructuras de otros mods que asoman a la superficie no nacen a menos de esta distancia del inicio de una aldea o una única de Heraldia que sale ahí; 0 lo desactiva ([Compatibilidad con otros mods](COMPATIBILIDAD.md#compatibilidad-con-otros-mods)). |
| `botin.reponer.activado` | `false` | `true`/`false` | [Botín que se repone](CONTENIDO.md#botín-que-se-repone-y-dificultad): los cofres y barriles de Heraldia se rellenan al abrirlos pasados los días indicados, sin otro jugador cerca y si están vacíos o casi; también los ya generados. Nada con Lootr. |
| `botin.reponer.dias` | 7 | 1-60 | Días de juego (24.000 ticks del reloj del mundo) desde un saqueo hasta que el cofre se repone. |
| `dificultad.nivel` | `normal` | `facil`, `normal`, `dificil`, `heroica` | [Dificultad](CONTENIDO.md#botín-que-se-repone-y-dificultad) de los guardianes y mobs de plantilla de Heraldia (vida y daño); también los ya generados, al cargarse. `normal` es lo de antes. |
| `dificultad.escalar_por_jugadores` | `false` | `true`/`false` | +25 % de vida por cada jugador de más a 32 bloques (hasta +100 %), al recibir un golpe. |
| `dificultad.escalar_botin` | `true` | `true`/`false` | Con `facil`, `dificil` o `heroica`, los objetos sencillos apilables del botín de los cofres de Heraldia salen en cantidad x0,75, x1,25 o x1,5 (en `normal` no cambia nada). |
| `arena.activado` | `true` | `true`/`false` | [Arena de oleadas](CONTENIDO.md#arena-de-oleadas) cerca del spawn. Desactivada, no hay partidas ni protección (la arena colocada se queda como está). |
| `arena.generar_en_mundos_nuevos` | `true` | `true`/`false` | En un mundo nuevo, la arena se construye sola a 200-300 bloques del spawn; en uno existente, nunca (la coloca un operador). |
| `arena.oleada.mobs_incremento` | 50 | 10-200 | Enemigos de más en cada oleada, en % de los de la primera (4, 6, 8, 10... con 50), redondeando hacia arriba. |
| `arena.oleada.stats_incremento` | 10 | 1-100 | Vida y daño de más en cada oleada, en %; si pasa de `mobs_incremento`, se usa ese (los enemigos crecen más que su fuerza). |
| `arena.max_mobs_vivos` | 20 | 4-64 | Enemigos vivos a la vez en el ruedo; si una oleada trae más, salen en tandas. |
| `arena.experiencia_porcentaje` | 15 | 0-100 | Experiencia de los enemigos de la arena, en % de la normal (sobre la ya escalada por el juego); no sueltan objetos. |
| `arena.modos.cooperativo` | `true` | `true`/`false` | [Modo](CONTENIDO.md#arena-de-oleadas) cooperativo de la arena (el de siempre). |
| `arena.modos.contrarreloj` | `true` | `true`/`false` | Modo contrarreloj: `arena.modos.oleadas_contrarreloj` oleadas contra el reloj. |
| `arena.modos.supervivencia` | `true` | `true`/`false` | Modo supervivencia: oleadas sin pausa hasta que caen todos. |
| `arena.modos.oleadas_contrarreloj` | 10 | 1-50 | Oleadas del contrarreloj (sus logros piden al menos 10). |
| `arena.temporada.dia_reinicio` | `lunes` | `lunes`, `martes`, `miercoles`, `jueves`, `viernes`, `sabado`, `domingo` | Día en que se cierra la clasificación semanal de la arena (hora del servidor): se anuncian los campeones y se ponen al día los carteles y la Guía. |
| `arena.temporada.hora_reinicio` | 0 | 0-23 | Hora (del servidor) a la que se cierra. |
| `arena.temporada.historico` | 8 | 1-52 | Semanas cerradas que se guardan en el mundo (`/heraldia arena leaderboard <modo> <semana>`); al bajarlo se recortan en el acto. |
| `encargos.activado` | `true` | `true`/`false` | [Encargos del tablón](CONTENIDO.md#vida-de-las-aldeas) (`/heraldia quest`), en todas las aldeas de Heraldia (también las ya generadas). Desactivado, el atril solo abre su libro y las órdenes lo dicen; lo que lleva cada jugador se conserva. |
| `encargos.rotacion_dias` | 3 | 1-30 | Días de juego que dura cada tablón antes de cambiar sus encargos (los aceptados se conservan). |
| `caravanas.activado` | `true` | `true`/`false` | [Caravanas](CONTENIDO.md#caravanas) por los caminos entre aldeas, solo con jugadores cerca y en chunks cargados. Desactivadas, no sale ninguna y la que esté en camino se va. |
| `caravanas.frecuencia` | 10 | 0-100 | Probabilidad (%) de que salga una caravana en cada sorteo (uno por minuto, junto a un jugador a menos de 80 bloques de un camino, al menos 2 min después de la anterior). 0: solo con `/heraldia caravan spawn`. |
| `caravanas.prob_asalto` | 35 | 0-100 | Probabilidad (%) de que la asalten los bandidos a media ruta. La fija el [perfil](#perfiles-de-juego). |
| `caravanas.max_activas` | 1 | 1-3 | Caravanas en camino a la vez en todo el servidor. |
| `chozas_mago.prob_malvado` | 20 | 0-100 | Probabilidad (%) de que el mago de una [choza de mago](CONTENIDO.md#chozas-de-mago) sea malvado; por choza, siempre igual, y se guarda en el mago al cargarse. 0: todos comercian. La fija el [perfil](#perfiles-de-juego). |
| `chozas_mago.prob_botin_premium` | 30 | 0-100 | Probabilidad (%) de que el Mago Malvado lleve además el premio (Reparación, pociones difíciles, tótem o un libro alto); por choza, al revelarse. |
| `reputacion.activado` | `true` | `true`/`false` | Reputación por aldea: sube con los encargos y baja al atacar a sus aldeanos o gólems; conocido, amigo y héroe de la aldea rebajan sus tratos un 10, 20 y 30 % (sin sumarse a Héroe de la aldea). Desactivada, ni descuentos ni cambios (la reputación ganada se conserva). |
| `mapas_web.activado` | `true` | `true`/`false` | [Marcadores en los mapas web](#mapas-web-heraldia-webmap-refresh) (BlueMap, Dynmap o squaremap); sin ninguno de ellos no hace nada. Desactivado, quita las capas de Heraldia del mapa. |
| `mapas_web.solo_descubiertas` | `true` | `true`/`false` | Solo salen las de un tipo que algún jugador ha descubierto (los logros de `/heraldia status`); con `false`, todas las ya generadas en chunks que se han cargado. |
| `mapas_web.idioma` | `auto` | `auto`, `es_es`, `en_us`, `fr_fr`, `de_de`, `it_it`, `pt_br`, `ca_es`, `gl_es` | Idioma de los nombres, descripciones y capas; `auto` usa el del sistema del servidor (la JVM). |
| `mapas_web.capas.<capa>` | `true` | `true`/`false` | Una por capa (`unicas`, `aldeas`, `medianas`, `minas`, `costa`, `arena`): apagada, la capa no sale. |
| `tesoro.activado` | `true` | `true`/`false` | [Caza del tesoro](CONTENIDO.md#caza-del-tesoro): fragmentos de mapa en el botín que llevan por varias estructuras reales hasta un cofre enterrado. Desactivada, no salen fragmentos y los que haya no hacen nada. |
| `tesoro.probabilidad` | 3.0 | 0-100 (admite decimales) | Probabilidad, en %, de un fragmento en cada cofre de medianas y minas; en los de las únicas, la mitad; en las recompensas de las hazañas del tablón, cinco veces más. |
| `tesoro.radio_max` | 1500 | 300-4000 | Distancia máxima de cada marca del mapa a la anterior (o a donde se descifra el fragmento), en bloques. |

La Atlántida no tiene opciones de colocación: es siempre una sola por mundo.

### Perfiles de juego

La opción `perfil` fija de golpe un conjunto de opciones de juego (nunca de la generación del mundo: dónde y cómo salen las estructuras, o la arena que se construye sola en un mundo nuevo, no los toca ningún perfil). `estandar`, el de por defecto, es exactamente el comportamiento de antes.

| Opción | `casual` | `estandar` | `hardcore` |
| --- | --- | --- | --- |
| `dificultad.nivel` | `facil` | `normal` | `heroica` |
| `dificultad.escalar_por_jugadores` | `false` | `false` | `true` |
| `dificultad.escalar_botin` | `false` | `true` | `true` |
| `botin.reponer.activado` | `true` | `false` | `false` |
| `botin.reponer.dias` | 3 | 7 | 14 |
| `jefes.fases.activado` | `true` | `true` | `true` |
| `jefes.refuerzos.activado` | `true` | `true` | `true` |
| `jefes.refuerzos.porcentaje` | 50 | 100 | 150 |
| `jefes.refuerzos.maximo_vivos` | 2 | 4 | 6 |
| `arena.oleada.mobs_incremento` | 30 | 50 | 75 |
| `arena.oleada.stats_incremento` | 5 | 10 | 20 |
| `arena.max_mobs_vivos` | 12 | 20 | 28 |
| `arena.experiencia_porcentaje` | 30 | 15 | 5 |
| `caravanas.prob_asalto` | 15 | 35 | 60 |
| `chozas_mago.prob_malvado` | 10 | 20 | 35 |

- **Una opción escrita en el fichero manda sobre el perfil** (está «fijada a mano»). Si su valor no es el del perfil, el perfil pasa a ser **personalizado** (`personalizado`): lo dice el log al arrancar, con las opciones que difieren y lo que daría el perfil, y también `/heraldia profile` y el bloque `_perfil` del fichero. El resto de las opciones siguen con los valores del perfil.
- Las opciones que fija un perfil solo se escriben en el fichero si están fijadas a mano; así, cambiar `perfil` en el fichero las cambia de verdad. Para volver al valor del perfil, borra la opción del fichero.
- `personalizado` no fija nada: cada opción toma su valor del fichero o, si no está, el de por defecto.
- Los ficheros de la 0.1.0 (`version` 1) se migran sin cambiar nada: el mod escribía todas las opciones, así que las del perfil que tenían su valor por defecto se quitan (con `estandar` dan lo mismo) y las que tenían otro se quedan como fijadas a mano.
- Se aplica siempre que se lee el fichero (al arrancar y con `/heraldia reload`), nunca a mitad de un chunk; los mobs ya generados toman la dificultad al cargarse, como antes.

### Pantalla de configuración (cliente)

En el cliente el fichero también se puede editar desde una pantalla del juego. Con [Mod Menu](https://modrinth.com/mod/modmenu) instalado (opcional; sin él el mod funciona igual, solo que la pantalla no tiene botón) se abre desde el botón de configuración de Heraldia en la lista de mods. Se construye con la misma lista de opciones que el fichero, así que las opciones nuevas aparecen solas:

- Secciones: Perfil de juego, Aldeas, Familias de aldeas, Estilos de aldea, Vida de las aldeas, Caminos entre aldeas, Gólems, Estructuras únicas, Distancia mínima entre únicas, Atlántida, Estructuras medianas, Compatibilidad con otros mods, Botín, Dificultad, Mapas web y Búsqueda del tesoro, con un buscador (por nombre, clave, ayuda o sección).
- Cada opción muestra su valor (botón sí/no, casilla numérica o un botón que recorre los valores de una opción de lista como `dificultad.nivel`). Su tooltip da la clave, la ayuda (la misma de `_ayuda`) y el valor por defecto y el rango. Un número no válido se pone en rojo, el tooltip dice por qué y **Guardar** queda desactivado hasta corregirlo.
- Perfil de juego: al cambiarlo, las opciones que tenían el valor del perfil anterior pasan al del nuevo; las que tenían otro (fijadas a mano) se quedan como estaban, con el nombre en dorado, y su tooltip dice el valor del perfil y que mandan sobre él. El tooltip del propio perfil dice el perfil efectivo y qué opciones difieren. Al guardar, solo se escriben como fijadas a mano las que no tienen el valor del perfil.
- **Guardar** escribe `config/heraldia.json` con el mismo formato que al arrancar (con `version` y `_ayuda`); **Valores por defecto** devuelve todas las opciones a su valor por defecto (no se escribe nada hasta guardar); **Cancelar** descarta los cambios.
- Los cambios se aplican al volver a abrir el mundo o reiniciar el servidor, y solo en los chunks que se generen después; la pantalla lo avisa. Sin ningún mundo abierto se usan desde el siguiente mundo que abras (sin reiniciar el juego). Con un mundo de un jugador abierto, al guardar se recarga en caliente lo que no afecta a la generación, por el mismo camino que [`/heraldia reload`](#recarga-en-caliente-heraldia-reload) (el informe sale en el chat); lo demás, al salir y volver a entrar.
- Conectado a un servidor, la pantalla edita **el fichero local del cliente** (tus mundos de un jugador), no el del servidor: la pantalla lo avisa. La configuración del servidor se sigue editando en su propio `config/heraldia.json`. No se envía nada por la red.
