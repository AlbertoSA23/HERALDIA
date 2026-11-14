# Coliseo en ruinas (`heraldia:unicas/coliseo`)

Anfiteatro elíptico de 87 × 73 bloques y 27 de alto sobre un hipogeo de dos niveles (14 bloques bajo la arena).
Bioma: sabana y meseta de sabana (lista explícita `minecraft:savanna`, `minecraft:savanna_plateau`; la sabana
azotada queda fuera por su relieve). Rareza por defecto del contrato (`spacing` 250 / `separation` 190 chunks).

Coordenadas de este documento: `(dx, dz)` respecto al centro de la arena (+x este, +z sur) y `y` respecto al suelo de
la arena (arena en y=0; el jugador pisa y=1). "Anillo r" = distancia constante desde el borde de la arena
(elipses concéntricas de semiejes 16,5 + r y 9,5 + r).

## Piezas y adaptación al terreno

- `unicas/coliseo/coliseo` (inicio, rígida, proyectada a `WORLD_SURFACE_WG`): todo lo que está de y=0 hacia arriba.
  Su base está a ras de suelo, así que `beard_thin` solo allana alrededor (como en las aldeas) y un anillo de losas
  (r 25-26) hace de peldaño de acceso.
- `unicas/coliseo/hipogeo` (hija, rígida): de y=-14 a y=-1, unida por un jigsaw vertical bajo la arena.
  La pieza rellena **toda** su caja (roca donde no hay salas), de modo que el rebaje de `beard_thin` bajo su base no
  abre huecos visibles: el terreno de alrededor queda por debajo de y=-2 y fuera de la vista. Así el sótano no hunde
  el terreno de superficie (el problema de la guía).

## Plantas por nivel

| Nivel | Pisa en | Contenido |
|---|---|---|
| Ático y terraza superior | y=19 | Terraza r 20-21 tras el ático (ventanas), nicho del velario con cofre, mástiles del velario en la coronación. |
| Graderío II | y=12-19 | 8 filas de asientos (r 12-19), escaleras que suben del pasillo I a la terraza. Tramo derrumbado al noroeste. |
| Galería alta G2 | y=8 | Anillo r 19-21 tras la segunda arcada (con balaustrada). Seis vomitorios suben de G2 al pasillo I. |
| Pasillo I (praecinctio) | y=11 | Anillo r 10-11 entre graderíos, con las bocas de los vomitorios. |
| Graderío I y podio | y=5-11 | Podio de mármol (r 1-3) con palco imperial (sur) y palco del editor (norte); 6 filas (r 4-9). |
| Planta baja G1 | y=1 | Anillo r 19-21 tras 40 arcos; túneles este (Puerta Triunfal) y oeste (Libitinaria) a la arena; pasos norte y sur a los palcos; dos tabernas; cuatro escaleras a G2; escalera oeste al hipogeo. |
| Arena | y=1 | Arena con trampillas de los montacargas y el pozo central abierto con escalera de mano. |
| Hipogeo H1 | y=-6 | Corredor central este-oeste, dos corredores laterales, 8 montacargas, 12 celdas de fieras, barracones (oeste), armería (este). |
| Hipogeo H2 (oculto) | y=-13 | Despacho del lanista, pasillo de las placas, cámara del tesoro, tramo bajo del pasadizo de Cómodo. |

Los planos en texto (celdas alcanzables) y los renders están en [`coliseo/`](coliseo/); se regeneran con
`python3 tools/gen/unicas/coliseo/auditoria.py --planos`.

## Recorrido del jugador

1. Cualquier arco de la planta baja da a G1. Desde G1: tabernas, túneles a la arena, pasos a los palcos y escaleras a G2.
2. G2 → vomitorio → pasillo I → graderíos → terraza superior (vista y cofre del velario).
3. Arena: el pozo central baja por escalera de mano al corredor central del hipogeo; también se baja por la escalera
   que sale de G1 al oeste (junto a la Puerta Libitinaria) y desemboca en el vestíbulo de los barracones.
4. H1: barracones (cofre, generador de esqueletos), celdas de fieras (cofre del domador, generadores de arañas y de
   zombis), corredor de la armería con la trampa de cable, armería (cofre).
5. Puzle 1 en la armería → trampilla de hierro → escalera al despacho del lanista (H2, cofre raro) → pasillo con
   trampa de placas → cámara del tesoro.
6. Alternativa: puzle 2 en el palco imperial → pasadizo de Cómodo (capilla con cofre raro, generador) → cámara del tesoro
   por el sur.
7. Cámara del tesoro: el Campeón de la Arena y el cofre premium sobre el estrado.

## Cofres (11)

| Cofre | Dónde | Tabla |
|---|---|---|
| Taberna NE / Taberna SO | G1, salas bajo el graderío II | `taberna` |
| Velario | Nicho del ático en la terraza superior | `velario` |
| Palco del editor | Palco norte | `palco_menor` |
| Palco imperial | Junto al trono, palco sur | `palco` |
| Barracones | H1 oeste | `barracones` |
| Domador | Celda de fieras sur-este | `fieras` |
| Armería | H1 este | `armeria` |
| Capilla de Cómodo (oculto) | Rellano del pasadizo, H1 | `cripta` |
| Lanista (oculto) | H2 bajo la armería | `lanista` |
| Premium | Estrado de la cámara del tesoro | `premium` |

## Puzles, trampas, generadores y guardián

- **Puzle 1, "la ofrenda"** (armería): pedestal con un marco vacío; detrás, un comparador lee el marco y alimenta una
  trampilla de hierro del suelo. Cualquier objeto en el marco la abre. Todo está apagado al generarse (marco vacío,
  comparador sin señal, trampilla cerrada): no depende de ninguna actualización.
- **Puzle 2, "el nicho del emperador"** (palco imperial): en la pared oeste hay un nicho ciego y, en la misma pared,
  una palanca. La pared del fondo del nicho es una puerta de pistones enrasada: dos pistones pegajosos extendidos la
  sujetan, alimentados por una antorcha de redstone en la cara oculta del bloque de la palanca. Al bajar la palanca la
  antorcha se apaga, los pistones recogen los dos bloques y se abre el pasadizo de Cómodo; al subirla se cierra.
  Se guardan los estados coherentes (antorcha encendida, pistones extendidos con cabeza, palanca apagada), así que
  nada cambia al generarse. La prueba `tools/smoke/coliseo_redstone.py` lo comprueba en un servidor real.
- **Trampa 1** (corredor de la armería): cable trampa de lado a lado; cada gancho activa el bloque al que está
  sujeto y este el dispensador con flechas que tiene encima, que dispara a la altura del pecho.
- **Trampa 2** (pasillo de las placas, H2): tres placas de piedra; cada una activa los dos dispensadores de las paredes
  que tiene al lado, a ras de suelo.
- **Generadores**: arañas (celda de fieras norte), zombis (celda de fieras sur), esqueletos (barracones), esqueletos
  (tramo bajo del pasadizo de Cómodo). Están lejos de toda luz (la auditoría calcula la luz de bloque y exige 0 en su
  radio de aparición).
- **Guardián**: el Campeón de la Arena, un husk (no arde al sol y encaja con la sabana) con `PersistenceRequired`,
  40 de vida, casco de oro, peto y botas de hierro, grebas de cota, espada de hierro y escudo; poca probabilidad de
  soltar el equipo.
- Sin aldeanos ni gólems: es una ruina abandonada.

## Ruina (objetivo 80-85 % en buen estado)

- Tramo derrumbado: 5 de los 40 vanos al noroeste. El ático y el tercer orden caen a una línea quebrada, el graderío II
  y la terraza se convierten en un talud de escombros (adoquín, arenisca, tierra gruesa con arbustos secos) que deja a
  la vista la bóveda de G2.
- Cornisas: faltan tramos de las impostas (y=6, 12, 18) y de la cornisa superior, y hay muescas en la coronación.
- Asientos sueltos rotos o desaparecidos (pocos, deterministas).
- Procesador de piezas: arenisca lisa y tallada se meteoriza a arenisca (6 %); en el hipogeo los ladrillos de piedra
  se agrietan (15 %) o crían musgo (6 %).
- La auditoría mide la superficie expuesta (cara superior de cada columna y fachada) y el porcentaje dañado.

## Botín

Menores modestos, más ricos cuanto más escondidos; cada cofre tiene un grupo extra `solo_sin_lootr`.
Solo objetos vanilla, sin netherita en equipo ni élitros.

- `taberna`, `barracones`, `fieras`, `velario`: comida, cuerda, cuero, huesos, pepitas de hierro, cubos, riendas.
- `palco_menor`, `palco`, `armeria`: oro y esmeraldas en poca cantidad, equipo de hierro o cota gastado, escudo,
  flechas, zanahorias doradas.
- `cripta`, `lanista`: lingotes, esmeraldas, libro encantado al azar, manzana dorada, armadura de caballo, etiqueta.
- `premium` (90 % vistoso): un trofeo con nombre propio (Gladius del Campeón, Yelmo de la Victoria, Escudo del
  Coliseo o Corona de Laurel) con encantamientos moderados, dos de entre adornos de armadura (centinela, explorador,
  modelador, anfitrión, criador) y discos, oro, esmeraldas y algún diamante; **10 %**: algo más fuerte (Espada del
  Emperador de diamante encantada o una manzana dorada encantada).

## Contraste con el criterio de Alberto

- Escaleras: todos los cambios de nivel son peldaños o escaleras de mano completas; la auditoría propia recorre a pie
  sin saltos y exige poder volver desde cada celda alcanzada.
- Puertas: solo puertas con salida; las secretas se comprueban abiertas (camino) y cerradas (la cámara no se alcanza).
- Nada flotando: faroles con cadena o techo, cadenas con enganche, comprobación de bloques sólidos sin apoyo tras la ruina.
- Simetría: planta elíptica simétrica en los dos ejes salvo la ruina y los palcos (imperial al sur, editor al norte).
- Cada elemento con función: arcos y galerías de circulación, vomitorios, montacargas, celdas, barracones, armería.
