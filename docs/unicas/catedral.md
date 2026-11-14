# Catedral gótica (`heraldia:unicas/catedral`)

Estructura única al estilo de Notre-Dame, diseñada a mano en `tools/gen/unicas/catedral/` (una sola variante).
Bioma: bosque y bosque de flores (`minecraft:forest`, `minecraft:flower_forest`). Rareza por defecto: rejilla de 250 chunks
(separación 190), una cada ~3.000-5.000 bloques.

## Tamaño y piezas

- 117 × 84 bloques de planta (x 0..116, z 4..87) y 77 de alto (y -8..68; la aguja llega a 68).
- Dos piezas rígidas unidas por un jigsaw vertical bajo el crucero (`size` 2, radio 80):
  - **catedral** (y ≥ 0): todo lo que está sobre el suelo. Su base es el suelo (y = 0), así que `beard_thin` asienta
    y suaviza el terreno alrededor de la huella como en las aldeas.
  - **cripta** (y -8..-1): cripta, osarios y cámara del tesoro, bajo el crucero, el coro y el ábside. Al ser una pieza
    aparte, su base no arrastra a la de la superficie (lección de `DESARROLLO.md`: una pieza que baja hunde el terreno);
    su barba queda a 8 bloques de profundidad, en roca, y está rodeada de un muro de dos bloques.
- Degradación: procesador de reglas (ladrillo de piedra agrietado 11 % y musgoso 8 %, tejas de pizarra agrietadas 10 %,
  andesita pulida 4 %) más daños explícitos con sentido. La auditoría calcula la parte dañada de la superficie exterior:
  **15,8 %** (objetivo 15-20 %, es decir, 80-85 % en buen estado).

## Plantas por nivel (planos completos en `catedral/planos.txt`)

Ejes: x crece de la fachada oeste (x = 6) al ábside; z de norte a sur; eje de simetría z = 30. Pies del jugador en y.

| Nivel (pies) | Qué hay |
|---|---|
| -7 | Cripta del crucero (pilares, sepulcros de obispos, altar) con dos cofres; cámara oeste con generador de zombis; osario (eje y dos bucles con calaveras en hornacinas); osario de los esqueletos (generador); galería hundida con arañas de cueva (generador, telarañas); pasadizo estrecho con trampa; antecámara de los sellos; cámara del tesoro; relicario oculto bajo el altar. |
| 1 | Atrio con escalinata; tres portadas (central con parteluz y dos en las torres); nártex bajo la tribuna; nave de 7 tramos con bancos, púlpito y arañas; colaterales; crucero con portadas norte y sur y las dos escaleras a la cripta; coro con sillería; altar mayor sobre estrado en el ábside; girola con tres capillas radiales; sacristía (al norte); claustro con jardín, pozo y árbol; sala capitular; refectorio en ruinas. |
| 9 | Biblioteca sobre la sacristía (estanterías, mesa de lectura, atriles) y gabinete secreto. |
| 12 | Triforio (tribunas) sobre los colaterales, la girola y el coro; pasarelas altas que cruzan los brazos del crucero; tribuna del órgano sobre el nártex. |
| 17 | Terrazas sobre los colaterales y la girola (cubiertas accesibles), bajo los arbotantes; cubierta de la sacristía. |
| 28 | Canalón a lo largo de la nave con pretil; terraza de la fachada con la galería de columnas; desván sobre las bóvedas (nave, crucero, coro y ábside). |
| 40 | Campanario (torre norte, dos campanas en una viga); torre sur con el tejado hundido. |
| 56 | Azoteas de las torres con pretil almenado. |

## Recorrido del jugador

1. Atrio y portada central → nave. Por los colaterales se llega al crucero y, por la girola, a las capillas.
2. Torres: escalera de caracol (losas, 0,5 bloques por paso) en cada torre, con salidas a la planta baja, la tribuna del
   órgano y el triforio (12), la terraza de los colaterales (17), la terraza de la fachada (28), el campanario (40) y la azotea (56).
3. Desde la terraza de la fachada: canalón de la nave y lucarnas al desván; el desván une nave, crucero, coro y ábside.
4. Triforio: de la torre al crucero, por la pasarela alta del brazo, al triforio del coro y de la girola (anillo completo).
5. Sacristía por la puerta de la girola norte; escalera a la biblioteca; torreta de servicio desde la sacristía al
   triforio del coro y a la terraza (cubierta de la sacristía).
6. Claustro por el paso del colateral sur; sala capitular por la panda este; refectorio por la panda sur.
7. Cripta por cualquiera de las dos escaleras de los brazos del crucero → osario → pasadizo estrecho (trampa) →
   antecámara de los sellos → (puzle) → cámara del tesoro.
8. Secretos: palanca escondida entre las estanterías de la biblioteca (gabinete); palanca en el estrado del altar mayor
   (trampilla de hierro y escala al relicario).

## Cofres (19) y botín

| Sitio | Tabla | Riqueza |
|---|---|---|
| Capillas radiales (4 barriles) | `capilla` | velas, pepitas de oro, papel |
| Claustro, sala capitular, refectorio | `menor` | pan, velas, carbón, pepitas |
| Sacristía (2) | `sacristia` | velas, oro en pepitas, lana, libros |
| Biblioteca | `biblioteca` | libros, papel, tinta; libro encantado al azar en el extra |
| Campanario | `campanario` | cuerda, cadenas, farolillos; «Campana de la torre norte» en el extra |
| Cripta (2) | `cripta` | huesos, oro, hierro; algún diamante o manzana dorada |
| Osario | `osario` | huesos, flechas; calavera, «Hueso de santo» |
| Gabinete secreto y relicario | `oculto` | libro encantado (10-20), oro, esmeraldas, diamantes, «Salterio iluminado», discos |
| Cámara del tesoro (2) | `tesoro` | oro, esmeraldas, 1-3 diamantes, equipo de hierro encantado, «Cáliz de oro» |
| Cámara del tesoro, principal | `premium` | ver abajo |

Premium: un objeto principal (90 % vistoso: «Espada del cabildo» de oro, «Yelmo del capitán de la guardia», «Báculo del obispo
Ermengol», «Arco de Fray Osmundo», «Cáliz de oro»; 10 % algo más fuerte: «Peto de los mártires» de diamante Protección III,
espada de diamante Filo IV o manzana de oro encantada), 2-3 vistosos (discos, plantillas de adorno host/raiser/shaper/wayfinder,
libro encantado 15-25, «Salterio»), 3-5 de valor (oro, esmeraldas, 1-3 diamantes) y un extra. Sin netherita ni élitros.
Cada tabla tiene su grupo extra marcado `solo_sin_lootr`.

## Puzles, trampas, generadores y guardián

- **Puzle de los sellos** (antecámara → tesoro): cuatro palancas en el muro, cada una bajo un cartel: Fe, Esperanza, Codicia,
  Caridad; un cartel lateral dice «Tres virtudes abren / y la codicia sella». La puerta es un bloque doble de piedra cincelada
  sujeto por dos pistones pegajosos extendidos dentro de un muro de tres de grueso. Tras cada palanca correcta hay una antorcha
  de redstone (inversor) y las tres alimentan una línea de polvo que mantiene los pistones extendidos; la palanca de la codicia
  alimenta la línea directamente. Se abre solo con las tres virtudes activadas y la codicia en reposo.
- **Gabinete secreto** (biblioteca): el mismo mecanismo con una palanca entre las estanterías del rincón noreste; la puerta es
  una estantería que retrocede dentro del muro.
- **Relicario**: trampilla de hierro en el estrado del altar mayor, abierta por la palanca de suelo de al lado; escala hasta el relicario.
- **Trampas** como en los templos vanilla: cable trampa en el eje del osario (dos dispensadores con flechas justo encima de los
  ganchos) y placa de presión en el pasadizo estrecho (dos dispensadores a ras de suelo).
- Todo se coloca en reposo coherente sin depender de actualizaciones: pistones extendidos y alimentados, antorchas encendidas,
  polvo con su potencia y sus conexiones escritas, palancas, ganchos, cable y dispensadores apagados.
- **Generadores** (solo en la cripta, a oscuras): zombis (cámara oeste), esqueletos (osario norte), arañas de cueva (galería hundida).
- **Guardián**: «Fray Osmundo, custodio del tesoro», esqueleto en la cámara del tesoro con 40 de vida, armadura 4, arco con
  Poder II, yelmo de malla y peto de oro, `PersistenceRequired`.
- Sin aldeanos ni gólems: la catedral está abandonada (en parte en ruinas) y su tesoro custodiado.

## Ruina (15-20 % de la superficie)

Además del procesador: torre sur con el tejado hundido sobre el campanario y el pretil mellado; cuatro vidrieras rotas en el
claristorio sur; huecos en el pretil de la terraza sur; boquete en la cubierta de la nave (con escombros en el desván); panda
sur del claustro hundida en parte con dos columnas caídas; refectorio sin cubierta, muros mellados, escombros y musgo;
galería hundida de la cripta.

## Contraste con el criterio de Alberto

- Escaleras: de caracol completas de la planta baja a la azotea; tramos rectos con apoyo; ninguna termina en el vacío.
- Puertas y vanos: la auditoría comprueba que cada puerta tiene paso a ambos lados y que no queda ninguna estancia sin acceso.
- Muebles contra los muros: bancos y sillería en filas con pasillo central, estanterías sin tapar ventanas, mesa con sillas
  de respaldo hacia fuera.
- Nada flotando: faroles colgados con cadena hasta la bóveda, campanas en viga, arbotantes y cubiertas unidos por caras
  (la auditoría busca grupos de bloques que no lleguen al suelo).
- Simetría respecto al eje de la nave salvo lo que tiene función propia (sacristía al norte, claustro al sur, campanario).
- Luz: ninguna celda cubierta transitable de la superficie queda a oscuras (no aparecen monstruos dentro); la cripta sí está a oscuras.

## Comprobaciones

- `tools/gen/unicas/catedral/auditoria.py` (condición para generar): recorrido a pie desde el atrio con los mecanismos
  accionados, acceso a cofres, generadores, palancas, campanas, atriles, puertas y peldaños; estancias sin acceso; bloques
  flotando; luz; coherencia estática de la redstone; proporción de ruina. Además pasa `lint.py` y la validación de registros.
- `tools/gen/unicas/catedral/prueba_juego.py`: servidor dedicado 26.3 real; coloca las dos piezas con `/place template`,
  comprueba el reposo tras las actualizaciones, acciona cada mecanismo (palanca simulada con un bloque de redstone en su apoyo)
  y revisa trampas, generadores, cofres y guardián.
- `python3 -m unicas.catedral.planos <carpeta> render` (desde `tools/gen`) regenera planos y renders.
