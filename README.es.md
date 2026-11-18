# Heraldia

[English](README.md) · **Español** · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Català](README.ca.md) · [Galego](README.gl.md)

Un mod de Fabric para **Minecraft 26.3** que llena el Overworld de sitios por los que merece la pena viajar: aldeas vivas unidas por caminos, ruinas con historia, guardianes con nombre y un tesoro al final del mapa. Todo está hecho con bloques y objetos vanilla, así que encaja en tu mundo como si siempre hubiera estado ahí.

## Qué encontrarás en tu mundo

- 🏘️ **Aldeas vivas.** 72 aldeas diseñadas a mano: 36 estilos, uno para cada tipo de bioma (una aldea castellana en la llanura, palafitos en el pantano, una aldea japonesa entre cerezos...), cada uno en tamaño estándar y grande, agrupados en 12 familias. Plaza con fuente y campana, iglesia, mercado, taberna, herrería, biblioteca, posada y veinte o treinta casas. Cada estilo tiene sus propios tratos, el tablón del alguacil paga cosechas, leña y limpiar los caminos, y los cartógrafos venden mapas del tesoro. Aquí y allá, alguien estaba trabajando hace un momento: una casa a medio construir con sus andamios, ropa tendida, un carro a medio descargar, una hoguera con el puchero puesto.
- 🛤️ **Caminos.** Senderos con farolas y puentes de madera unen las aldeas vecinas. Cerca de cada aldea, un cartel te dice el nombre de la siguiente y cuántos bloques faltan.
- 🏕️ **Junto al camino.** 16 tipos de estructuras medianas entre aldea y aldea: torres de vigía, posadas de camino, campamentos de bandidos, ermitas, molinos, cabañas de pescador, puestos de cazadores, templetes en ruinas y chozas de mago, cada una al estilo de su bioma, con botín modesto y, a veces, un pequeño reto. Y al otro lado de los portales, el Nether tiene puestos de piglins renegados, altares de magma, atalayas de basalto y santuarios de los hongos, y las islas exteriores del End, observatorios del vacío, mausoleos púrpura y embarcaderos de los shulkers caídos.
- 🏰 **21 estructuras únicas**, muy raras y cada una en su bioma: un castillo con foso, una catedral gótica, una ciudadela enana excavada en la montaña, un galeón varado, una mansión encantada, un palacio oriental, una torre de mago, una mina perdida bajo tierra, el fuerte de un corsario en su propia isla en mar abierto... Dentro: salas ocultas, puzles de redstone, trampas y generadores y, al final, un **guardián con nombre** que custodia la cámara del tesoro. Dos de ellas están al otro lado de los portales: la Ciudadela de Ceniza en el Nether y el Sagrario del Vacío en las islas exteriores del End, lejos del dragón.
- ⚔️ **Guardianes que pelean por fases.** Al perder vida se enfurecen y llaman a refuerzos de su propia estructura, con barra de jefe mientras dura el combate. Cada uno suelta su propio trofeo.
- ⛏️ **Minas.** En laderas de verdad se abren bocas de mina, campamentos mineros y complejos con torre de extracción, en 3 tamaños y al estilo de cada bioma, que bajan a galerías con vías, cruces y salas. Además, las minas abandonadas vanilla salen más a menudo.
- 🗼 **Faros y naufragios.** Faros en tierra firme junto al mar, con la luz siempre encendida, la casa del farero y un embarcadero, y galeones partidos, encallados en la playa o semihundidos en los bajíos, con su bodega y el camarote del capitán. Cada uno al estilo de su costa: templada, cálida, fría o nevada.
- 🔱 **La Atlántida.** Solo hay una en el mundo: una ciudad enorme hundida en el océano profundo, con salas secas, tres sellos con sus llaves y el Guardián de Poseidón, que custodia el mayor tesoro de Heraldia.
- 🏟️ **Arena de oleadas.** Un coliseo cerca del spawn: toca la campana y aguanta oleadas cada vez más fuertes, con un campeón cada cinco, récords y recompensas. Si caes en el ruedo, conservas tu inventario. Tres modos (cooperativo, contrarreloj y supervivencia) con clasificación semanal, `/heraldia arena leaderboard`: los campeones de la semana anterior salen en los carteles del salón de la fama de la arena y en la Guía del Heraldo.
- 🏯 **La Casa del Heraldo.** Lo primero que ves en un mundo nuevo: un pueblo amurallado de 96 × 96 bloques en el spawn, con su campana, el tablón de encargos, una posada y un hostal, una capilla, tiendas con sus aldeanos, jardines, un establo, un pozo y un portal al Nether que solo enciende un operador. Nadie salvo un operador puede construir ni romper a menos de 50 bloques de sus murallas, y allí no aparecen monstruos. Su mercado tiene puestos que los jugadores alquilan con esmeraldas cuando el servidor los activa. En un mundo que ya existe, la coloca un operador con `/heraldia herald place`.

## Cómo se juega

- 📖 **La Guía del Heraldo.** Cada jugador la recibe al entrar: un libro que explica qué buscar y lleva tu diario, con las estructuras únicas que has descubierto y pistas de las que te faltan. Pide una copia al día cuando quieras con `/heraldia guide`.
- 📊 **Lo que ha encontrado el servidor.** `/heraldia status` dice cuántas aldeas, estructuras únicas, medianas y minas han descubierto los jugadores, los guardianes vencidos, el récord de la arena y los encargos entregados.
- 🧭 **Tu diario.** `/heraldia journal` te enseña en el chat, tipo por tipo y con una barra de progreso, lo que has encontrado y lo que te falta: familias de aldea, estructuras únicas, medianas, tamaños de mina, faros y naufragios, el Nether y el End. Haz clic en un tipo para ver los nombres. Sin coordenadas: encontrarlas es cosa tuya.
- 📋 **Encargos de las aldeas.** Toca el atril del tablón de la plaza de una aldea (o usa allí `/heraldia quest`): salen en el chat de 2 a 4 encargos (traer objetos, vencer a un guardián, explorar, viajar a una aldea vecina, la arena) que cambian cada pocos días. Pagan esmeraldas, experiencia y reputación con esa aldea: como conocido, amigo y héroe de la aldea, sus aldeanos rebajan los precios un 10, 20 y 30 %. Atacar a sus aldeanos o gólems la baja.
- 🐪 **Caravanas.** De vez en cuando, cerca de ti, un mercader de Heraldia con sus llamas (y a veces un guardia) recorre el camino entre dos aldeas vecinas. Si lo asaltan los bandidos, defiéndelo: al llegar te paga esmeraldas y reputación con su aldea de destino. Si el mercader muere, la caravana se pierde.
- 🚶 **Gente de paso.** Vida en los caminos, también cerca de ti: un peregrino camino de un monasterio o de la catedral, un pastor con su rebaño, un mensajero con prisa, una pareja de guardias de patrulla o un cazador que vuelve con su perro, según la zona. Recorren un tramo y se van; el pastor y el cazador comercian, y si les haces daño se sabe en su aldea.
- 💬 **Habla con los aldeanos.** Haz clic derecho sobre un aldeano de una aldea de Heraldia y te habla en el chat: frases según su oficio, su tierra, la hora, el tiempo y lo que la aldea te conoce, con botones para seguir hablando, preguntar qué se cuenta o comerciar (agacharse + clic derecho comercia directamente; los aldeanos vanilla comercian como siempre). Uno de cada diez ha viajado y, si la aldea se fía de ti, te cuenta una vez hacia dónde y a qué distancia queda una estructura.
- 🏆 **Logros.** Una pestaña Heraldia con 124 logros: una aldea de cada familia, cada estructura única con su guardián y su tesoro, las minas, los faros y naufragios, las estructuras medianas, el tablón de encargos, la arena y las caravanas.
- 🗿 **Trofeos.** Cada uno de los 22 guardianes suelta su trofeo, un objeto con nombre e historia. Reúnelos todos para completar la Sala de trofeos.
- 🗺️ **Mapas del tesoro.** Cada mapa marca la estructura única más cercana de su tipo. Salen en los cofres épicos de las aldeas y los venden los cartógrafos.
- 🧭 **Caza del tesoro.** A veces un cofre guarda un fragmento de mapa del tesoro. Úsalo y se volverá un mapa con una marca: cada marca es una estructura real de Heraldia que esconde la siguiente pista, y la última lleva a un cofre que enterró Ysolda, con buen botín y un recuerdo.
- 📜 **La Crónica de los Heraldos.** Cada estructura única guarda un pliego de la crónica que escribió Ysolda, la última heraldo de la Atlántida. Cada pliego señala el siguiente: reúne los 22 y sabrás cómo acaba. Vence a todos los guardianes del mundo principal e Ysolda te dejará su último pliego, el título de Heraldo de la Atlántida y el estandarte de los Heraldos, para alzarlo donde quieras.

Los textos del mod están en 8 idiomas: inglés, español, francés, alemán, italiano, portugués de Brasil, catalán y gallego.

## Instalación

1. Necesitas **Minecraft 26.3**, **Fabric Loader** 0.20.1 o posterior y **Fabric API**.
2. Pon `heraldia-<version>.jar` en la carpeta `mods` del **servidor** y reinícialo.
3. **Los jugadores no necesitan el mod**: pueden entrar con el cliente vanilla. Los textos que el cliente no conoce salen en español, salvo la Guía del Heraldo, los encargos, la arena, las caravanas y los avisos de Heraldia, que llegan en el idioma de cada jugador. Si también instalan el mod, lo ven todo en su idioma y tienen la pantalla de configuración (con Mod Menu).

**Un mundo existente** sirve: las estructuras nuevas salen en los chunks que aún no se han generado (explora tierras nuevas). Si tu mundo se creó con Heraldia **0.1.0**, pon `unicas.rejilla_compatible` a `true` antes de arrancar el servidor, para que `/locate`, los mapas del tesoro y la Guía sigan encontrando las estructuras únicas que ya tienes.

Los **comandos** están en inglés en todos los servidores: `/heraldia guide`, `/heraldia key`, `/heraldia arena place`... Los nombres antiguos en español (`/heraldia guia`...) siguen funcionando por ahora: hacen lo mismo y te dicen el nombre nuevo.

**Versiones nuevas:** el servidor mira una vez al día si hay una versión nueva de Heraldia para su Minecraft y avisa a los operadores al entrar, con el enlace de descarga. **Haz una copia de seguridad del servidor antes de actualizar.** Se desactiva con `update_check.activado`.

**Actualizar el servidor:** al actualizar no cambia nada de lo ya construido. Para llevar lo nuevo a lo ya generado, `/heraldia update analyze` enseña (sin cambiar nada) qué se regeneraría o colocaría, siempre con un margen de 50 bloques alrededor de lo que hayan construido los jugadores, y `/heraldia update apply` lo hace tras una confirmación, con copia de seguridad opcional y `/heraldia update undo`. Paso a paso: [Actualizar un servidor](docs/CONFIGURACION.md#actualizar-un-servidor).

**Mapas web:** si el servidor tiene BlueMap, Dynmap o squaremap, las estructuras de Heraldia salen en el mapa web, cada clase en su capa (únicas, aldeas, medianas, minas, faros y naufragios y la arena), solo cuando algún jugador las ha descubierto. Los operadores lo actualizan con `/heraldia webmap refresh`.

## Opciones más útiles

El fichero `config/heraldia.json` se crea en el primer arranque del servidor, con una ayuda para cada opción. Los cambios se aplican al reiniciar el servidor, en los chunks que se generen después. Las que no afectan a la generación (dificultad, jefes, botín, arena, Guía...) se pueden aplicar sin reiniciar con `/heraldia reload`. Los operadores también pueden cambiar las más útiles en el juego, sin el mod en su cliente, con `/heraldia config` (un menú con el perfil y siete apartados). Cada jugador puede elegir el idioma de los textos de Heraldia con `/heraldia language`.

| Opción | Por defecto | Qué hace |
| --- | --- | --- |
| `perfil` | `estandar` | Perfil de juego: `casual`, `estandar`, `hardcore`, `ligero` (equipos modestos: generación del mundo más ligera; mejor en un mundo nuevo) o `personalizado`; lo escrito en el fichero manda sobre él. |
| `aldeas.separacion_bloques` | 1500 | Distancia media entre aldeas (1000-10000). |
| `aldeas.maximo` | 100 | Número máximo de aldeas en el mundo. |
| `aldeas.caminos.activado` | `true` | Caminos entre aldeas. |
| `unicas.<id>.activada` | `true` | Activa o desactiva una estructura única. |
| `unicas.rejilla_compatible` | `false` | `true` solo en mundos creados con Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | Cuántas estructuras medianas (200 = el doble). |
| `faros.activado`, `naufragios.activado` | `true` | Faros y galeones naufragados en la costa. |
| `dificultad.nivel` | `normal` | Guardianes y monstruos: `facil`, `normal`, `dificil` o `heroica`. |
| `botin.reponer.activado` | `false` | Los cofres de Heraldia se reponen al cabo de unos días. |
| `arena.activado` | `true` | La arena de oleadas cerca del spawn. |
| `arena.temporada.dia_reinicio` | `lunes` | Día en que se cierra la clasificación semanal de la arena y se anuncian sus campeones (a medianoche, hora del servidor). |
| `encargos.activado` | `true` | Encargos del tablón (`/heraldia quest`). |
| `reputacion.activado` | `true` | Reputación por aldea y sus descuentos. |
| `reputacion.aldea_visible` | `true` | La aldea muestra su mejor reputación con bloques vanilla: flores, estandartes, faroles (o contraventanas cerradas); nunca sobre un bloque de un jugador. |
| `dialogos.activado` | `true` | Conversaciones con los aldeanos de Heraldia (agacharse + clic derecho comercia directamente). |
| `caravanas.activado` | `true` | Caravanas por los caminos (operadores: `/heraldia caravan`). |
| `viajeros.activado` | `true` | Gente de paso por los caminos, cada tipo con su opción (operadores: `/heraldia caravan wayfarer`). |
| `chozas_mago.prob_malvado` | 20 | Probabilidad (%) de que el mago de una choza de mago sea un mago malvado disfrazado. |
| `ambiente.activado` | `true` | Efectos de ambiente con los sonidos del juego: la campana de la aldea al amanecer y al anochecer, la sirena del faro con lluvia y los goteos de las minas (cada uno tiene además su opción). |
| `guia.entregar_al_entrar` | `true` | Da la Guía del Heraldo a cada jugador al entrar. |
| `update_check.activado` | `true` | Avisa a los operadores cuando hay una versión nueva. |
| `actualizar.margen_bloques` | 50 | Margen de seguridad alrededor de lo que construyen los jugadores para `/heraldia update`. |
| `mapas_web.solo_descubiertas` | `true` | En el mapa web solo salen las estructuras ya descubiertas. |
| `tesoro.probabilidad` | 3.0 | Probabilidad (%) de un fragmento de mapa del tesoro en cada cofre de medianas y minas. |
| `casa_heraldo.activado` | `true` | La Casa del Heraldo en el spawn y su protección. |
| `casa_heraldo.mercado.activado` | `false` | Puestos de alquiler en el mercado de la Casa del Heraldo (precios: `casa_heraldo.mercado.*`). |

## Para saber más

- [Referencia completa del contenido](docs/CONTENIDO.md): cada estilo de aldea, estructura única, estructura mediana y mina, los combates contra los guardianes, los logros, la arena y más.
- [Instalación, comandos y configuración](docs/CONFIGURACION.md): comandos de prueba y de administración (`/heraldia info`, `/heraldia review`, `/heraldia status`, `/heraldia reload`, `/heraldia key`...), todas las opciones y la pantalla de configuración del juego.
- [Compatibilidad con otros mods](docs/COMPATIBILIDAD.md): mods de biomas, de estructuras, Lootr y los demás.
- [Compilar y probar](docs/COMPILAR.md), [guía de desarrollo](docs/DEVELOPMENT.md) (en inglés) y [registro de cambios](CHANGELOG.md) (en inglés).

## Licencia y créditos

Sin licencia: todos los derechos reservados. El código es visible, pero no se concede permiso para usarlo, copiarlo ni redistribuirlo.
Todo el contenido usa solo bloques y objetos de Minecraft; no se incluyen recursos de terceros.
