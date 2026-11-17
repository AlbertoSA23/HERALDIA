# Heraldia: instalación, comandos y configuración

[English](CONFIGURATION.md) · **Español**

Volver al [README](../README.es.md).

## Instalación

Requisitos: Minecraft 26.3, Fabric Loader 0.20.1 o superior y Fabric API (probado con 0.166.2+26.3). Opcional en el cliente: Mod Menu (compilado contra la 21.0.1), para la [pantalla de configuración](#pantalla-de-configuración-cliente).

1. Compila `heraldia-<versión>.jar` (ver abajo).
2. Cópialo en la carpeta `mods` del servidor. En los clientes es opcional: con el cliente vanilla se juega igual (los textos que no conoce salen en español, salvo la Guía, que llega en el idioma de cada jugador); con el mod, todo sale en su idioma y está la pantalla de configuración.
3. Arranca el servidor. En `logs/latest.log` debe aparecer `Heraldia: 142 estructuras registradas`.

En un mundo existente las estructuras solo aparecen en chunks que todavía no se han generado.
`/reload` no recarga la generación del mundo: hay que reiniciar el servidor (o salir y volver a entrar al mundo en un solo jugador).

## Comandos de prueba

- Colocar una aldea donde estés: `/place structure heraldia:llanuras_castellana` (o `..._grande`). Funciona aunque no estés en su bioma.
- Buscar la más cercana: `/locate structure heraldia:llanuras_castellana`
- Colocar una pieza suelta: `/place template heraldia:llanuras_castellana/specials/church`
- `/function heraldia:muestrario`: coloca las 72 aldeas en cuadrícula a partir de donde estés (cada fila, hacia el sur, es una familia; en cada fila van los 3 estilos y luego sus versiones grandes, hacia el este, separadas 300 bloques). Te pone en espectador y te lleva de una a otra, una cada 8 s (unos 10 min). Al terminar vuelves a creativo.
- `/function heraldia:familia/<familia>` (`llanuras`, `bosque`, `oscuro`, `taiga`, `nieve`, `desierto`, `sabana`, `jungla`, `pantano`, `cerezos`, `badlands`, `costa`): lo mismo con las 6 aldeas de una familia, en fila hacia el este.
- `/function heraldia:muestrario/parar`: lo detiene.
- `/heraldia llave <jugadores> <llave>` (operadores, nivel 2): da las llaves de los cofres cerrados de las estructuras únicas, el mismo objeto que se consigue en el juego. `<llave>` se autocompleta: `todas`, una estructura (`atlantida`: sus cuatro llaves) o una llave suelta (`atlantida.arsenal`, `atlantida.academia`, `atlantida.anfiteatro`, `atlantida.poseidon`). Si el inventario está lleno, la llave cae al suelo a nombre del jugador.
- `/heraldia info` (operadores, nivel 2): resumen de la configuración en uso (aldeas, estructuras únicas activadas y su separación, distancia mínima, cofre por jugador, si está instalado Lootr, estructuras medianas, entradas a mina y el multiplicador de las minas vanilla) y de cuántas estructuras hay registradas.
- `/heraldia info cerca [radio]`: la estructura única y la mediana más cercanas de cada tipo, la entrada a mina más cercana de cada tamaño y la aldea Heraldia más cercana, con distancia, rumbo y coordenadas (al pulsarlas se propone un `/tp`). Usa la misma comprobación que `/locate`, así que nunca señala una estructura que la distancia mínima descarta, pero no carga ni genera chunks: lo que aún no se ha generado sale como «prevista» (de una aldea prevista solo se sabe la familia). Radio por defecto 3.000 bloques, máximo 10.000; el mensaje dice cuánto ha tardado la búsqueda.
- `/heraldia guia` (cualquier jugador, sin permisos): te da una copia al día de la [Guía del Heraldo](CONTENIDO.md#guía-del-heraldo) (si llevas una en el inventario, la cambia por la nueva).
- `/heraldia info aqui`: en qué estructura Heraldia estás (nombre e id) y, en una única, si su guardián vive (solo se responde si toda la estructura está cargada).

Usa el muestrario solo en un mundo de prueba: lo colocado se queda.

## Configuración

Fichero `config/heraldia.json` del servidor (en un mundo de un jugador, el de la carpeta del juego). Se crea al arrancar con todos los valores por defecto
y se reescribe en cada arranque con los valores en uso y una ayuda (`_ayuda`) en español e inglés. Un valor que no sea válido (fuera de rango o de otro tipo)
se avisa en el log y se sustituye por el de por defecto; una opción desconocida se avisa y se ignora. El campo `version` permite migrar el fichero
cuando cambie su formato. Se lee solo al arrancar el servidor y afecta a los chunks que se generen después (no a lo ya generado).

| Opción | Por defecto | Rango | Qué hace |
| --- | --- | --- | --- |
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
| `unicas.rejilla_compatible` | `false` | `true`/`false` | **Ponlo a `true` en un mundo creado con una versión anterior de Heraldia (0.1.0)**; déjalo en `false` en un mundo nuevo. Las rejillas de colocación de las únicas cambiaron después de la 0.1.0 (el origen de la rejilla de cada tipo va desplazado y la separación interna es la distancia mínima), así que en un mundo antiguo `/locate`, los mapas del tesoro, los pliegos de la Crónica, `/heraldia info cerca` y la distancia mínima ya no encuentran las únicas ya generadas en lo explorado (aunque siguen ahí). Activada, las 14 únicas que ya estaban en la 0.1.0 (acueducto, castillo, catedral, ciudadela, coliseo, faro, fortaleza de hielo, galeón, mansión, monasterio, observatorio, palacio, pirámide y torre de mago) vuelven a la rejilla de esa versión, bit a bit, para la misma semilla y configuración y con el mismo coste. Las añadidas después (Salón del Jarl, Santuario druídico, Laboratorio del micólogo, Mina perdida e Isla del corsario) siguen con la rejilla nueva, y las antiguas tienen prioridad sobre ellas: una nueva se descarta si cae a menos de la distancia mínima de una antigua que sale, así que nunca aparece encima de una ya generada. No afecta a las aldeas ni a la Atlántida (su colocación no cambió; la Atlántida conserva su posición guardada). |
| `unicas.distancia_minima.activada` | `true` | `true`/`false` | Impide que dos estructuras únicas distintas (también la Atlántida) salgan a menos de la distancia mínima. |
| `unicas.distancia_minima.bloques` | 1000 | 100-3000 | Distancia mínima entre los chunks de inicio de dos estructuras únicas distintas. Si dos candidatas quedan demasiado cerca, un sorteo determinista (semilla y posición) se queda con una; si la ganadora no puede salir ahí (bioma o terreno), se conserva la otra. `/locate` y los mapas del tesoro siguen la misma regla. |
| `unicas.atlantida.cofre_unico_por_jugador` | `false` | `true`/`false` | Cofre premium de la Atlántida por jugador. La primera apertura convierte su contenido en una plantilla guardada en el propio cofre (que queda vacío: romperlo o vaciarlo con una tolva no duplica nada) y cada jugador abre su propia copia: la recibe entera la primera vez y después encuentra lo que dejó. Sigue haciendo falta la llave de Poseidón. Con Lootr o sin él funciona igual (Lootr no convierte este cofre porque no tiene tabla de botín). Si se desactiva después, el contenido vuelve al cofre una vez (la primera vez que alguien lo usa) y se comporta como antes. |
| `jefes.fases.activado` | `true` | `true`/`false` | Fases de los guardianes al bajar del 66 % y del 33 % de vida: efectos, partículas, sonido y aviso en la barra de acción ([Combates contra los guardianes](CONTENIDO.md#combates-contra-los-guardianes)); también los de las estructuras ya generadas. |
| `jefes.refuerzos.activado` | `true` | `true`/`false` | Refuerzos de los guardianes: 2 o 3 mobs de su estructura una vez por fase, como mucho 4 vivos a la vez; no sueltan el botín del guardián. Funciona aunque las fases estén desactivadas (entonces sin efectos y con otro aviso). |
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
| `guia.entregar_al_entrar` | `true` | `true`/`false` | Da la [Guía del Heraldo](CONTENIDO.md#guía-del-heraldo) a cada jugador la primera vez que entra con cada versión del mod. Desactivada, nadie la recibe al entrar, pero `/heraldia guia` sigue dándola. |
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

La Atlántida no tiene opciones de colocación: es siempre una sola por mundo.

### Pantalla de configuración (cliente)

En el cliente el fichero también se puede editar desde una pantalla del juego. Con [Mod Menu](https://modrinth.com/mod/modmenu) instalado (opcional; sin él el mod funciona igual, solo que la pantalla no tiene botón) se abre desde el botón de configuración de Heraldia en la lista de mods. Se construye con la misma lista de opciones que el fichero, así que las opciones nuevas aparecen solas:

- Secciones: Aldeas, Familias de aldeas, Estilos de aldea, Vida de las aldeas, Caminos entre aldeas, Gólems, Estructuras únicas, Distancia mínima entre únicas, Atlántida, Estructuras medianas, Compatibilidad con otros mods, Botín y Dificultad, con un buscador (por nombre, clave, ayuda o sección).
- Cada opción muestra su valor (botón sí/no, casilla numérica o un botón que recorre los valores de una opción de lista como `dificultad.nivel`). Su tooltip da la clave, la ayuda (la misma de `_ayuda`) y el valor por defecto y el rango. Un número no válido se pone en rojo, el tooltip dice por qué y **Guardar** queda desactivado hasta corregirlo.
- **Guardar** escribe `config/heraldia.json` con el mismo formato que al arrancar (con `version` y `_ayuda`); **Valores por defecto** devuelve todas las opciones a su valor por defecto (no se escribe nada hasta guardar); **Cancelar** descarta los cambios.
- Los cambios se aplican al volver a abrir el mundo o reiniciar el servidor, y solo en los chunks que se generen después; la pantalla lo avisa. Sin ningún mundo abierto se usan desde el siguiente mundo que abras (sin reiniciar el juego); con un mundo de un jugador abierto, al salir y volver a entrar.
- Conectado a un servidor, la pantalla edita **el fichero local del cliente** (tus mundos de un jugador), no el del servidor: la pantalla lo avisa. La configuración del servidor se sigue editando en su propio `config/heraldia.json`. No se envía nada por la red.
