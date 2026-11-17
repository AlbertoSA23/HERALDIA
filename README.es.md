# Heraldia

[English](README.md) · **Español** · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Català](README.ca.md) · [Galego](README.gl.md)

Un mod de Fabric para **Minecraft 26.3** que llena el Overworld de sitios por los que merece la pena viajar: aldeas vivas unidas por caminos, ruinas con historia, guardianes con nombre y un tesoro al final del mapa. Todo está hecho con bloques y objetos vanilla, así que encaja en tu mundo como si siempre hubiera estado ahí.

## Qué encontrarás en tu mundo

- 🏘️ **Aldeas vivas.** 72 aldeas diseñadas a mano: 36 estilos, uno para cada tipo de bioma (una aldea castellana en la llanura, palafitos en el pantano, una aldea japonesa entre cerezos...), cada uno en tamaño estándar y grande, agrupados en 12 familias. Plaza con fuente y campana, iglesia, mercado, taberna, herrería, biblioteca, posada y veinte o treinta casas. Cada estilo tiene sus propios tratos, el tablón del alguacil paga cosechas, leña y limpiar los caminos, y los cartógrafos venden mapas del tesoro.
- 🛤️ **Caminos.** Senderos con farolas y puentes de madera unen las aldeas vecinas. Cerca de cada aldea, un cartel te dice el nombre de la siguiente y cuántos bloques faltan.
- 🏕️ **Junto al camino.** 8 tipos de estructuras medianas entre aldea y aldea: torres de vigía, posadas de camino, campamentos de bandidos, ermitas, molinos, cabañas de pescador, puestos de cazadores y templetes en ruinas, cada una al estilo de su bioma, con botín modesto y, a veces, un pequeño reto.
- 🏰 **19 estructuras únicas**, muy raras y cada una en su bioma: un castillo con foso, una catedral gótica, una ciudadela enana excavada en la montaña, un galeón varado, una mansión encantada, un palacio oriental, una torre de mago, una mina perdida bajo tierra, el fuerte de un corsario en su propia isla en mar abierto... Dentro: salas ocultas, puzles de redstone, trampas y generadores y, al final, un **guardián con nombre** que custodia la cámara del tesoro.
- ⚔️ **Guardianes que pelean por fases.** Al perder vida se enfurecen y llaman a refuerzos de su propia estructura, con barra de jefe mientras dura el combate. Cada uno suelta su propio trofeo.
- ⛏️ **Minas.** En laderas de verdad se abren bocas de mina, campamentos mineros y complejos con torre de extracción, en 3 tamaños y al estilo de cada bioma, que bajan a galerías con vías, cruces y salas. Además, las minas abandonadas vanilla salen más a menudo.
- 🔱 **La Atlántida.** Solo hay una en el mundo: una ciudad enorme hundida en el océano profundo, con salas secas, tres sellos con sus llaves y el Guardián de Poseidón, que custodia el mayor tesoro de Heraldia.
- 🏟️ **Arena de oleadas.** Un coliseo cerca del spawn: toca la campana y aguanta oleadas cada vez más fuertes, con un campeón cada cinco, récords y recompensas. Si caes en el ruedo, conservas tu inventario.

## Cómo se juega

- 📖 **La Guía del Heraldo.** Cada jugador la recibe al entrar: un libro que explica qué buscar y lleva tu diario, con las estructuras únicas que has descubierto y pistas de las que te faltan. Pide una copia al día cuando quieras con `/heraldia guia`.
- 🏆 **Logros.** Una pestaña Heraldia con 94 logros: una aldea de cada familia, cada estructura única con su guardián y su tesoro, las minas, las estructuras medianas, el tablón de encargos y la arena.
- 🗿 **Trofeos.** Cada uno de los 20 guardianes suelta su trofeo, un objeto con nombre e historia. Reúnelos todos para completar la Sala de trofeos.
- 🗺️ **Mapas del tesoro.** Cada mapa marca la estructura única más cercana de su tipo. Salen en los cofres épicos de las aldeas y los venden los cartógrafos.
- 📜 **La Crónica de los Heraldos.** Cada estructura única guarda un pliego de la crónica que escribió Ysolda, la última heraldo de la Atlántida. Cada pliego señala el siguiente: reúne los 20 y sabrás cómo acaba.

Los textos del mod están en 8 idiomas: inglés, español, francés, alemán, italiano, portugués de Brasil, catalán y gallego.

## Instalación

1. Necesitas **Minecraft 26.3**, **Fabric Loader** 0.20.1 o posterior y **Fabric API**.
2. Pon `heraldia-<version>.jar` en la carpeta `mods` del **servidor** y reinícialo.
3. **Los jugadores no necesitan el mod**: pueden entrar con el cliente vanilla. Los textos que el cliente no conoce salen en español, salvo la Guía del Heraldo, que llega en el idioma de cada jugador. Si también instalan el mod, lo ven todo en su idioma y tienen la pantalla de configuración (con Mod Menu).

**Un mundo existente** sirve: las estructuras nuevas salen en los chunks que aún no se han generado (explora tierras nuevas). Si tu mundo se creó con Heraldia **0.1.0**, pon `unicas.rejilla_compatible` a `true` antes de arrancar el servidor, para que `/locate`, los mapas del tesoro y la Guía sigan encontrando las estructuras únicas que ya tienes.

## Opciones más útiles

El fichero `config/heraldia.json` se crea en el primer arranque del servidor, con una ayuda para cada opción. Los cambios se aplican al reiniciar el servidor, en los chunks que se generen después.

| Opción | Por defecto | Qué hace |
| --- | --- | --- |
| `perfil` | `estandar` | Perfil de juego: `casual`, `estandar`, `hardcore` o `personalizado`; lo escrito en el fichero manda sobre él. |
| `aldeas.separacion_bloques` | 1500 | Distancia media entre aldeas (1000-10000). |
| `aldeas.maximo` | 100 | Número máximo de aldeas en el mundo. |
| `aldeas.caminos.activado` | `true` | Caminos entre aldeas. |
| `unicas.<id>.activada` | `true` | Activa o desactiva una estructura única. |
| `unicas.rejilla_compatible` | `false` | `true` solo en mundos creados con Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | Cuántas estructuras medianas (200 = el doble). |
| `dificultad.nivel` | `normal` | Guardianes y monstruos: `facil`, `normal`, `dificil` o `heroica`. |
| `botin.reponer.activado` | `false` | Los cofres de Heraldia se reponen al cabo de unos días. |
| `arena.activado` | `true` | La arena de oleadas cerca del spawn. |
| `guia.entregar_al_entrar` | `true` | Da la Guía del Heraldo a cada jugador al entrar. |

## Para saber más

- [Referencia completa del contenido](docs/CONTENIDO.md): cada estilo de aldea, estructura única, estructura mediana y mina, los combates contra los guardianes, los logros, la arena y más.
- [Instalación, comandos y configuración](docs/CONFIGURACION.md): comandos de prueba y de administración (`/heraldia info`, `/heraldia llave`...), todas las opciones y la pantalla de configuración del juego.
- [Compatibilidad con otros mods](docs/COMPATIBILIDAD.md): mods de biomas, de estructuras, Lootr y los demás.
- [Compilar y probar](docs/COMPILAR.md), [guía de desarrollo](docs/DESARROLLO.md) y [registro de cambios](CHANGELOG.md).

## Licencia y créditos

Sin licencia: todos los derechos reservados. El código es visible, pero no se concede permiso para usarlo, copiarlo ni redistribuirlo.
Todo el contenido usa solo bloques y objetos de Minecraft; no se incluyen recursos de terceros.
