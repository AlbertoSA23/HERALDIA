# Faro con cueva de contrabandistas (`heraldia:unicas/faro`)

Una sola variante, diseñada a mano. Faro blanco y rojo sobre un promontorio rocoso de la costa con la casa del
farero; bajo el promontorio, al nivel del mar, la cueva de unos contrabandistas con muelle escondido. Se entra a pie
por la casa (pasadizo secreto) o por mar, por la boca de la cueva.

## Situación junto al mar (por qué hace falta Java)

El jigsaw no sabe dónde hay agua y gira la pieza al azar, así que no puede garantizar ni que haya mar ni que la boca
de la cueva mire hacia él. Se registra un tipo de estructura propio, `heraldia:faro`
(`io.github.albertosa23.heraldia.unicas.faro.FaroStructure`), que:

1. Busca en una rejilla de 7 x 7 puntos (cada 8 bloques alrededor del centro de la casilla) los que caen en un bioma
   de la estructura (`#heraldia:unicas/faro`: costa pedregosa y playa). Si ninguno cae, termina sin consultar alturas:
   las casillas de interior y las búsquedas de mapas y `/locate` son baratas.
2. Para cada candidato y cada una de las 4 direcciones consulta los mapas de alturas de generación
   (`OCEAN_FLOOR_WG` y `WORLD_SURFACE_WG`, con caché): detrás tiene que haber tierra entre el nivel del mar + 4 y + 16;
   delante, a 24-40 bloques, agua con al menos 3 de fondo; y en toda la huella nada más alto que la cima del
   promontorio (para que el terreno no tape la casa).
3. Coloca la plantilla girada para que la boca de la cueva mire al mar, centrada en el punto elegido y con la fila de
   agua del muelle en el nivel del mar (`sea_row`). Adaptación al terreno `none`: el promontorio trae su propia roca y
   por encima de ella no se toca el terreno natural.
4. Con `/place structure` (el predicado de bioma acepta cualquiera) y sin costa a la vista, se coloca igualmente en el
   centro del chunk, para probar.

Estado del agua: todo el interior de la cueva está por encima del nivel del mar (el suelo de los muelles es la fila
del agua), así que el mar no puede inundarla; el agua del canal es de fuentes colocadas por la plantilla, a ras del mar.

## Medidas

Plantilla de 44 x 52 x 48 (x, y, z), una sola pieza. y=8 es la fila del agua (nivel del mar - 1); la cima del
promontorio (hierba) está en y=21 (13 bloques sobre el mar) y el pararrayos del faro en y=51. La boca mira a +z (sur
de la plantilla) y la entrada a pie está en z=0.

## Plantas por nivel (pies del jugador)

**Cima, y=22.** Camino de tierra desde la entrada (z=0) hasta la puerta norte de la casa del farero (15 x 11, muros
de piedra y abeto, tejado a dos aguas). Dentro: dormitorio (cama, arcón), cocina (ahumador, horno, mesa con dos sillas)
y estudio (estantería, atril, mesa de cartografía); **cofre `casa`**; escalera de mano al sótano. Al sur, pasillo
cubierto hasta el faro.

**Faro.** Torre de 9 x 9, bandas blancas y rojas, núcleo macizo de 5 x 5 y escalera de caracol de 17 peldaños contra
los muros, con ventanas al mar. Sala de guardia (y=39): atril, **cofre `faro`**, barril, ventanas en los cuatro lados.
Escalera de mano a la linterna (y=44): cristal alrededor, dos bombillas de cobre encendidas (no necesitan
alimentación), galería exterior con barandilla y ménsulas.

**Sótano, y=17** (bajo la casa). Barriles de vino (**barril `bodega`**), cartel con la pista y una **trampilla de
hierro** en el suelo. **Puzle 1:** la trampilla se abre con la palanca escondida entre los barriles (la palanca
alimenta el bloque del suelo pegado a la trampilla). Debajo, escalera de mano hasta la cueva.

**Cueva, y=9** (nivel del mar).
- Pasadizo secreto (1 de ancho) desde la escalera hasta el corredor. **Trampa 1** (como el templo de la jungla):
  cable trampa entre dos ganchos; cada gancho dispara el dispensador que tiene encima (flechas en cruz a la altura de
  la cabeza).
- Corredor este-oeste que une las salas del norte con la gran gruta.
- Gruta del muelle: canal de agua de 5 de ancho hasta la boca, muelles de abeto con norays, cajas y un **bote con
  cofre (`bote`)** amarrado.
- Almacén oeste: barriles y cajas, **cofre `almacen`**, **generador de esqueletos** al fondo. Detrás de una pila de
  barriles queda una rendija que lleva a la **gruta del alijo** (sala oculta, **cofre `oculto`**).
- Almacén este: **cofre `almacen`**, derrumbe en una esquina, y en un nicho un **cofre señuelo** con placa de presión
  y TNT debajo (**trampa 2**, como el templo del desierto).
- Dormitorio: cuatro literas, mesa, **cofre `dormitorio`**.
- Calabozo: celdas con barrotes (una rota), **generador de zombis**, **cofre `calabozo`** en una celda.
- Despacho del capitán: escritorio, sillas, atril, mapa, **cofre `despacho`**, estanterías. **Puzle 2:** tres
  palancas en el muro norte y un cartel ("Ni proa ni popa: manda el centro"). La puerta de hierro de la cámara solo se
  abre con la central subida y las otras dos bajadas. Circuito escondido tras el muro: la palanca A y la C alimentan
  una línea de polvo; la B pasa por una antorcha inversora; la línea alimenta el bloque de una segunda antorcha, que
  es la que abre la puerta. En reposo (A subida, B y C bajadas) la puerta está cerrada.
- Cámara del tesoro (5 de alto): **guardián con nombre** ("Capitán Bruma", ahogado con espada de hierro y cota de
  malla, 40 de vida, `PersistenceRequired`, sin soltar el equipo), **cofre premium** sobre un estrado y dos
  **barriles `tesoro`**.

Recorrido: casa → sótano (puzle 1) → pasadizo (trampa 1) → corredor → salas del norte y gruta → almacenes (generador,
sala oculta, trampa 2) → despacho (puzle 2) → cámara (guardián, premium). Por mar se llega a la gruta sin pasar por
la casa, pero el despacho y la cámara solo se abren con los puzles.

## Ruina (80-85 % en buen estado)

Procesador: un 10 % de ladrillos de piedra agrietados y un 8 % musgosos; un 15 % del adoquín musgoso. Huecos con
sentido: dos cristales rotos en la casa, un hueco en la barandilla de la galería del lado del mar, derrumbe de grava y
adoquín en el almacén este, barrotes rotos en una celda y telarañas en el calabozo. La auditoría estima el porcentaje
de superficie alterada y lo exige entre el 15 y el 20 %.

Aldeanos o gólems: ninguno. El faro está abandonado y la cueva tomada por los muertos de la banda; un aldeano solo
tendría sentido si el faro siguiera en uso.

## Botín (solo vanilla; cada cofre con su grupo extra `solo_sin_lootr`)

| Tabla | Dónde | Contenido |
|---|---|---|
| `casa` | casa | comida, velas, papel, hilo; brújula rara |
| `faro` | sala de guardia | catalejo, brújula, mapa vacío, papel, tinta luminosa, farol, lingotes de hierro |
| `bodega` | sótano | pan, manzanas, botellas de miel, bayas, bacalao |
| `almacen` | almacenes | cuero, lana, hilo, pólvora, azúcar, lingotes de hierro, pepitas de oro, esmeraldas sueltas |
| `senuelo` | señuelo (trampa) | huesos, carne podrida, hilo, pólvora |
| `dormitorio` | dormitorio | comida, pepitas de oro, armadura de cuero gastada, libro, reloj raro |
| `calabozo` | calabozo | huesos, pepitas de hierro, cadenas, rienda, etiqueta rara |
| `despacho` | despacho | mapa, brújula, lingotes de oro, esmeraldas, libro encantado (20 %), frascos de experiencia |
| `oculto` | gruta del alijo | oro, esmeraldas, diamante (15 %), pieza de hierro encantada (5-15), manzana de oro (10 %) |
| `bote` | bote con cofre | pólvora, esmeraldas, salmón, caparazón de nautilo, corazón del mar (5 %) |
| `tesoro` | cámara | pepitas y lingotes de oro, oro en bruto, esmeraldas |
| `premium` | cámara | 90 %: objetos con nombre (sable del capitán, catalejo, brújula), plantilla de adorno *costa*, disco, libro encantado, manzana de oro; 10 %: espada de diamante encantada (20-30), tridente, manzana de oro encantada o 3-5 diamantes |

Sin netherita en equipo ni élitros.

## Verificado en el servidor

`/locate structure heraldia:unicas/faro` encontró una en la semilla de prueba y la generación natural la colocó;
guardián y bote presentes, agua delante de la boca y aire dentro de la gruta. Puzle 1 abre la trampilla; puzle 2 solo
abre la puerta con (A, B, C) = (bajada, subida, bajada) entre cinco combinaciones probadas. Planos y renders:
`docs/unicas/faro/`. El aspecto visual no está validado con capturas del juego.

## Contraste con el criterio de diseño

- Escaleras completas y sin saltos: caracol de peldaños; las escaleras de mano terminan en suelo (la trampilla
  abierta sobre la escalera cuenta como escalón, igual que en el juego).
- Puertas con salida y nada inaccesible: lo comprueba el recorrido a pie con los puzles resueltos.
- Muebles contra los muros, centro libre salvo mesas con sillas; faroles colgados de cadenas o techo.
- Simetría en el faro y la casa; la cueva, natural e irregular salvo las salas construidas.
- Cada elemento con función: norays, cajas en el muelle, literas, celdas, estrado del tesoro.

## Comprobaciones propias del módulo

`tools/gen/unicas/faro/checks.py` (se ejecutan al construir y fallan la generación):
- Recorrido a pie con los puzles resueltos (estado abierto declarado por la plantilla, que también usa `lint.py`).
- Simulación de redstone de los dos puzles y las trampas: estado de reposo coherente con lo colocado (nada depende de
  una actualización que no ocurra al generar) y la puerta solo se abre con la combinación buena (8 combinaciones).
- Cueva estanca: ninguna celda de aire del interior bajo la cima toca el exterior salvo la boca.
- Porcentaje de superficie alterada entre el 15 y el 20 %.
