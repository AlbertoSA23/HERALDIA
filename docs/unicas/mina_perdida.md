# Mina perdida de Hondavena (`heraldia:unicas/mina_perdida`)

Una colonia minera de la Corona excavada en una gran caverna bajo las cuevas. Tizón, el capataz, encontró un filón de
oro y prometió que haría ricos a todos; cuando el frente viejo se hundió y la Corona cerró la mina, los mineros subieron
por el pozo y él se quedó abajo, junto al filón. Es **la primera única subterránea**: desde fuera solo se ve el
castillete de madera sobre el pozo maestro.

Es una estructura original: no copia ninguna mina ni colonia de otro juego o mod. Se distingue de la Ciudadela enana
(también excavada) en que no está en una montaña ni tiene fachada: es una colonia de mineros humanos en una caverna,
con el oficio de la mina (pozo y malacate, vagonetas, fundición, entibos, vetas) como tema.

## Bioma, altura y colocación

- Biomas: **cuevas exuberantes** y **cuevas de espeleotemas** (`minecraft:lush_caves`, `minecraft:dripstone_caves`),
  medidos **a la altura de la caverna**, no en la superficie. No el abismo (`deep_dark`, de las ciudades antiguas) ni
  `#c:is_cave` (lo incluye). Sin etiquetas convencionales.
- **Altura**: la capa de suelo de la gran caverna está a **y = 20** (`obra.PISO`); el filón madre baja a y = 9 y el
  fondo de la sima a y = 4; la cara superior de la colonia queda a y = 46. Por qué:
  - por debajo del nivel del mar (63), así que incluso en terreno bajo hay roca de sobra encima de la bóveda;
  - por encima de y ≈ 8, donde empieza la pizarra abismal, el abismo y las ciudades antiguas (y ≈ -51) y las cámaras
    de desafío (y -40 a -20); el casco por debajo de y = 8 es de pizarra abismal para que no se note el cambio;
  - es la franja donde más abundan las cuevas exuberantes y de espeleotemas;
  - el pozo queda de 10 a 80 bloques (más, y la escalera se haría eterna: entonces no sale en esa casilla).
- **Rejilla**: `heraldia:rejilla` con `bioma` (la etiqueta de la estructura) y el nuevo campo `bioma_y` = 26 (el centro
  de la caverna): la candidata de cada casilla es el punto de la malla de 128 bloques más metido en esas cuevas **a esa
  altura** (`GridPlacement`; sin `bioma_y` se mira a y = 64, como el laboratorio). Una cada 3.000-5.000 bloques por
  defecto, configurable como todas (`unicas.mina_perdida.activada`, `unicas.mina_perdida.separacion_bloques`).
- **Tipo propio `heraldia:mina`** (`unicas/mina/MinaStructure.java`): en el chunk candidato prueba una malla de 5 x 5
  puntos (cada 16 bloques) con el centro de la caverna en el bioma y cuenta cuántos de cuatro puntos de muestra (a 15-20
  bloques) también lo están (solo lee el ruido de biomas, ~20 µs por punto). Para los tres mejores mira el terreno sobre
  el pozo y las cuatro esquinas del castillete con `OCEAN_FLOOR_WG`/`WORLD_SURFACE_WG` (`comun/Alturas`, 5 columnas):
  seco (ni mar, ni río, ni lago), con menos de 5 bloques de desnivel y un pozo de 0 a 80 bloques. El primero que cumple
  da las piezas: la **colonia** a y fija, los **tramos del pozo** (8 bloques, y 1 para el resto) desde la cara superior
  de la colonia y el **castillete** con su suelo en el terreno. Si ninguno cumple, no se genera. `/place structure` (que
  acepta cualquier bioma) la pone en el chunk tal cual.
- Adaptación `none` y paso `underground_structures`. El castillete trae su propio cimiento de 6 bloques de adoquín
  (absorbe el desnivel) y aire explícito encima de toda su huella (14 x 9, hasta 12 bloques).

## La colonia no es una caja: el casco

La colonia es una sola plantilla (108 x 45 x 82) que **solo lleva lo excavado** (aire y agua), su **forro** en cada cara
que da a lo excavado y **dos capas de roca maciza** alrededor (`obra.forro` y `obra.casco`); fuera, nada (structure_void),
así que se conserva el terreno. Por eso:

- una cueva vanilla que pase cerca ve roca irregular, no las caras planas de una caja;
- ningún hueco de la colonia toca el exterior: la auditoría comprueba que cada celda excavada tiene sus 6 vecinas en la
  plantilla (salvo el hueco del pozo, que sigue en el tramo de encima), así que **no entra agua ni lava natural** de los
  acuíferos ni de las cuevas, y los pasillos no se abren a ellas;
- **los forros nunca son bloques naturales** (adoquín, adoquín de pizarra, ladrillo de piedra, tablas, ladrillo,
  baldosas de pizarra): dentro no nacen manantiales de agua ni de lava, liquen luminoso (que daría luz a los
  generadores), musgo ni charcas de arcilla de las cuevas exuberantes (`#base_stone_overworld`, `#moss_replaceable`,
  `#lush_ground_replaceable`). La auditoría falla si un bloque natural da a una celda seca (se admiten la grava del
  escombro y del fondo del lago y la arena del lecho). Las menas vanilla sí pueden aparecer en la roca del casco. En las
  cuevas exuberantes pueden colgar enredaderas con bayas luminosas del techo (piden techo macizo, no bloque natural).
- El pozo atraviesa cuevas y acuíferos con 1 bloque de piedra por fuera del forro de tablas.
- Estructuras vanilla del mismo paso (minas abandonadas) que se crucen: se generan antes y la colonia escribe encima de
  su casco; un pasillo vanilla puede acabar contra la roca del casco. Deducido del orden de los pasos; no visto en un mundo
  real.

## Recorrido (pies a y = 1 en la caverna)

Coordenadas de la obra: x de oeste a este, z de norte a sur; el pozo baja por x = 44, z = 7. Planos por nivel en
[`mina_perdida/planos.txt`](mina_perdida/planos.txt); renders `colonia.png`, `colonia_corte.png` y `castillete.png`.

- **Castillete** (superficie): cuatro pies derechos de abeto con vigas, tornapuntas y un tejadillo; de la viga maestra
  cuelga la cadena de la cubeta, que baja hasta el fondo. Brocal de adoquín con la escalera de mano, la **casa del
  malacate** (el tambor del torno, cofre `malacate`) y la escombrera. Cartel: «Mina de Hondavena. Pozo maestro. Cerrada
  por orden de la Corona».
- **Pozo maestro**: hueco de 3 x 3 con la escalera de mano y la cadena, forro de tablas con un marco de troncos cada 4
  bloques. Abajo, la cubeta (un caldero) en la **estación del pozo** (cofre `estacion`, toneles, el cartel del pozo).
- **La gran caverna** (superelipse de 55 x 43, bóveda de 5 a 16 bloques con ruido): suelo de adoquín, plaza de andesita
  pulida alrededor del **pilar maestro** (la roca que los mineros dejaron para sostener la bóveda) con los carteles de la
  colonia; faroles colgados de la bóveda y derrumbes sueltos junto a las paredes.
- Al norte: el **almacén** (toneles, dos cofres `almacen`) y la **fundición** (cuatro altos hornos bajo una campana de
  ladrillo, dos calderos de lava, yunque, carbón y mineral en bruto, cofre `fundicion`).
- Al oeste, las **casas de los mineros** excavadas en la roca, con fachada recta de ladrillo de piedra, puerta, ventanas
  y porche: tres viviendas (cofres `vivienda`; la del sur con el techo hundido) y la **casa del capataz**.
- Al este, la **herrería** y la **carpintería** (cofres `herreria` y `carpinteria`).
- Al sur, el **lago subterráneo** (agua de 3 de hondo con lecho de grava y arena) con su **embarcadero** de tablas sobre
  pilotes (cofre `embarcadero`, una barca amarrada) y, en la orilla sur, el **cobertizo de las barcas**.
- Al este, la **sima** (5 x 23, de y = 4 a y = 28) con el **puente colgante**: tablas, barandillas y cadenas hasta el
  techo; le faltan tablas y barandilla en el borde. Una escalera de mano baja al fondo, con los huesos de los que cayeron,
  un **generador de esqueletos** y el cofre `sima`.
- Tras el puente, la galería del cargadero con la **trampa 1** (cable trampa entre las jambas, dos dispensadores de
  flechas encima de los ganchos) y el **cargadero** (cofre `cargadero`), con el **puzle de las agujas**.
- Al sur del cargadero, el **frente viejo**: galería con vía (le faltan traviesas) y una sala de trabajo con **vetas a la
  vista** (carbón, hierro, cobre, oro, redstone y lapislázuli), escombro, telarañas, un **generador de zombis** y el cofre
  `frente`. Cartel: «Frente viejo. Cerrado por el derrumbe».
- Al suroeste, el **sector derrumbado**: la galería vieja con vía rota, un entibo caído y un derrumbe que deja un paso por
  el centro; la **trampa 2** (una placa sobre dinamita, «la carga olvidada», con baldosas agrietadas de aviso); la cámara
  del derrumbe (telarañas, **generador de arañas de cueva**, cofre `derrumbe`) y una escalera de 6 peldaños al **sector
  inundado**: una galería anegada de 3 de hondo con una pasarela de tablas (rota en un tramo) y el cofre `inundada` en el
  fondo, bajo el agua.
- **Filón madre** (tras la compuerta, pies a y = -10): una escalera de 11 peldaños baja a una cámara de pizarra con vetas de
  oro, una columna de oro en bruto y geodas de amatista, donde espera **Tizón, el último capataz** (cofre `filon`); al
  oeste, la **cámara del tesoro** con el cofre `premium` entre dos bloques de oro.

## Puzles, salas ocultas y trampas

1. **Las agujas del cargadero** (`vias.py`). Una vagoneta espera en la salida, un raíl propulsor apagado contra el muro
   este; la palanca «Arranque» la lanza al oeste. Tres propulsores con un bloque de redstone debajo la mantienen en marcha
   (una vagoneta vacía frena mucho). La vía pasa por dos **agujas** (cruces en T) con su palanca de suelo:
   - sin tocar nada, la aguja 1 la lleva al sur, a la **escombrera**;
   - con la aguja 1 al norte y la aguja 2 con señal, al oeste, a la **vía muerta de la fundición**;
   - solo con la aguja 1 al norte y la 2 sin señal (al este) llega, por una rampa y una **rendija de 1 x 1 en el muro**
     (no cabe una persona), a la **báscula**: un raíl detector. Mientras la vagoneta pesa sobre ella, su bloque de apoyo
     apaga la antorcha inversora que sostiene la **compuerta** del filón madre (dos pistones pegajosos extendidos, como
     `piezas.lever_door`), y la compuerta se abre; si se quita la vagoneta, se cierra.
   La pista está en el despacho del capataz («A la báscula: aguja 1, norte; aguja 2, este»). Regla de las agujas en 26.3
   (`RailState.place`, leída en el bytecode): con tres vecinos, sin señal gana la última de NO, NE, SO, SE con sus dos
   vecinos; con señal, la última de SE, SO, NE, NO. La auditoría la reproduce (`vias.forma_aguja`), sigue a la vagoneta
   por la vía en las 4 combinaciones (`vias.recorrer`) y exige que solo la buena llegue a la báscula; el simulador común
   (`_comun/redstone`, que ahora trata el raíl detector como una placa) comprueba el reposo de la compuerta, que la
   báscula la abre y que ninguna palanca del cargadero la toca. La prueba de servidor lo hace con una vagoneta de verdad.
2. **El despacho del capataz** (sala oculta con puzle): en el muro oeste de su casa (de dos de grueso), un panel de
   ladrillo se recoge hacia el norte por dentro del muro al bajar la palanca de la estantería empotrada del rincón
   (`piezas.lever_door`). Dentro, el cofre `despacho` con el **pliego de la Crónica**, atril, estanterías y el cartel con la
   pista de las agujas.
3. **El alijo** (sala oculta sin puzle): tras el tapiz azul del fondo del cobertizo de las barcas, un paso de 1 x 2 lleva al
   escondite de los contrabandistas del oro (cofre `alijo`).
4. Trampas: el **cable trampa** de la boca del cargadero y la **carga olvidada** (placa sobre dinamita) del sector
   derrumbado.

## Enemigos y botín

- Tres generadores (esqueletos en el fondo de la sima, zombis en el frente viejo, arañas de cueva en la cámara del
  derrumbe), a oscuras: la auditoría propaga la luz de bloque y exige 0 en su volumen.
- Guardián: **Tizón, el último capataz**, un vindicador (el hacha se la da el juego al aparecer) con casco de hierro y
  mandil de cuero teñido, 70 de vida, armadura 6. Trofeo: **Pico de Tizón** (eficiencia 2, irrompibilidad 2).
- **21 cofres** (20 en la colonia y uno en el castillete), cada vez más ricos: provisiones y herramientas de mina arriba;
  minerales en bruto, lingotes y herramientas con encantamientos moderados en las galerías; oro, diamantes y objetos con
  nombre en las salas ocultas y en el filón; el **cofre premium** (90 % vistoso: Lingote de la Corona, Farol de la última
  guardia, Casco de minero, Pico de entibador, Brújula del pocero, adornos de armadura, discos; 10 % algo más fuerte:
  pico, pala o peto de diamante encantados, manzana dorada encantada o tótem). Nada de netherita ni élitros. Con Lootr,
  cada tabla pierde su grupo extra (`solo_sin_lootr`).
- Pliego de la Crónica en el cofre `despacho`.

## Estado de conservación

Un 16 % de la superficie a la vista está dañada (auditoría, `auditoria.estado`: caras que dan a lo excavado, sin contar
los suelos): derrumbes de grava y adoquín, la casa con el techo hundido, el entibo caído, tablas y barandilla que faltan en
el puente y la pasarela, traviesas arrancadas, una vía caída en el fondo de la sima, y el procesador de la colonia (ladrillo
agrietado o musgoso, adoquín musgoso). Nada que sostenga un mecanismo se cae: el procesador solo cambia el aspecto.

## Rendimiento

- Generación: `findGenerationPoint` lee hasta 25 + 100 puntos del ruido de biomas y, como mucho, 3 x 5 columnas de alturas
  (con caché); la candidata de la rejilla ya cae en el bioma. Plantillas: colonia 83.000 bloques escritos (el casco
  incluido; sin caja maciza), castillete 2.400, tramos del pozo 392 y 49. Entidades: el guardián, la vagoneta del puzle y
  una barca. Nada por tick, sin mixins nuevos. Tiempos medidos en el PR (prueba de servidor).
- Generación del datapack: ~3 s la obra entera con su auditoría.

## Comprobaciones

- Auditoría propia (`auditoria.py`, condición para generar): reposo de la redstone; las 4 combinaciones de las agujas;
  la compuerta, el despacho y las trampas con el simulador común; recorrido a pie con los puzles cerrados y resueltos
  (`lint.walk` y `recorrido.andar`, sin caídas de más de un bloque y nadando, con vuelta a la entrada desde cualquier
  sitio y subida por la escalera del pozo hasta arriba); apoyos, puertas, escaleras (`lint`); luz de los generadores;
  bloques naturales a la vista; casco cerrado; bloques sueltos; superficie dañada; número de cofres; el castillete (se
  llega al cofre y a la escalera del pozo). Probada con fallos provocados (solución cambiada, antorcha quitada, panel
  abierto, farol junto a un generador).
- `prueba_servidor.py` (en la matriz de la CI): `/locate` y generación natural (el guardián en su sitio, la caverna en
  su bioma de cueva, la cadena del pozo de la colonia al castillete y aire libre encima), `/place structure` con su
  tiempo y sus entidades, y las plantillas sin girar: cofres, generadores, agua, el puzle de las agujas con una vagoneta
  de verdad en las tres salidas, el despacho y las dos trampas.
- Sin capturas del juego: el aspecto no está confirmado.
