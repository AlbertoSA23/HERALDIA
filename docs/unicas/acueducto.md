# Acueducto con ciudad en ruinas (`heraldia:unicas/acueducto`)

Colonia romana abandonada en el desierto. Un acueducto de arcos de dos pisos cruza el terreno durante 86 bloques
hasta el *castellum* (depósito del agua), pegado a la muralla norte de una ciudad de 96 x 92 bloques. Debajo, la
cisterna del foro y las cloacas, donde se esconde la cámara del tesoro.

- Bioma: `desert`, `badlands`, `wooded_badlands` (no `eroded_badlands`: sus agujas rompen el acueducto).
  El coliseo va en sabana y la pirámide en su propio bioma; aquí nada se pisa.
- Rareza: la del contrato (`spacing` 250 / `separation` 190 chunks: una cada ~3.000-5.000 bloques).
- Coordenadas de este documento: x hacia el este, z hacia el sur, y = 0 el enlosado de la ciudad
  (un bloque por encima del terreno natural). La estructura entera gira al azar como un bloque.

## Piezas jigsaw y adaptación al terreno

Una sola variante: cada pool tiene un único elemento, así que el ensamblado es determinista.

| Pieza | Caja (x, z, y) | Padre | Notas |
|---|---|---|---|
| `castellum` (inicio) | 72-86, -12..4, 0..17 | — | centro de la estructura: todo queda a menos de 116 bloques |
| `acueducto` | 77-81, -98..-13, 0..17 | castellum (cara norte) | procesador Java `heraldia:acueducto_hasta_el_suelo` |
| `ciudad` | 0-95, 5..97, 0..19 | castellum (cara sur) | procesador de desgaste (arenisca agrietada) |
| `cloaca` | 64-92, -5..44, -11..-1 | castellum (suelo, vertical) | cloacas, trampas y cámara del tesoro |
| `cisterna` | 33-63, 42..60, -9..-1 | ciudad (suelo del foro, vertical) | cisterna abovedada |

- **Adaptación `beard_box`.** Las piezas de superficie tienen la base en y = 0: el juego vacía el terreno dentro de su
  caja y lo rellena debajo (unos 12 bloques). Así las dunas no entran en las casas y el enlosado queda apoyado.
- **Sótanos sin hundimiento.** El problema de `beard_thin` con piezas que bajan (el terreno se ajusta a la base de la
  caja) se resuelve así: lo subterráneo va en **piezas aparte** colgadas por jigsaw vertical, cuya caja está entera
  bajo tierra y **rellena bloque a bloque** (arenisca y piedra donde no hay sala). El vaciado de `beard_box` dentro
  de esa caja queda sobrescrito por la plantilla y la pieza de superficie no baja de y = 0.
- **Pilares hasta el suelo.** El acueducto es rígido (el canal debe ser horizontal), pero el terreno no lo es.
  Ni `beard_box` ni la proyección `terrain_matching` resuelven un valle de más de ~6 bloques, así que hay un
  procesador propio (Java, `finalizeProcessing`): cada bloque de `smooth_sandstone` de la fila y = 0 de la pieza se
  prolonga hacia abajo, solo dentro del chunk que se está generando, hasta encontrar suelo firme (no aire, no
  fluido, no reemplazable, no hojas; máximo 64). Los cimientos de los 13 pilares llegan siempre al suelo.

## Recorrido del jugador

1. **Llegada.** El acueducto se ve de lejos (18 de alto). Su extremo norte está roto: los dos últimos vanos perdieron
   el piso alto y el vano 9-10 se ha desplomado. Siguiéndolo se llega al castellum, fuera de la muralla norte.
2. **Ciudad.** Puertas al sur (cardo), este y oeste (decumano), con rampa de losas. Calles de basalto pulido
   (andesita) con aceras. Insulae con casas y tiendas; la villa del gobernador al oeste del foro, las termas al este.
3. **Foro.** Plaza con pórticos a los lados, templo hexástilo sobre podio al norte, fuente central, puestos de
   mercado y la casa de la fuente (SO) con la escalera a la **cisterna**.
4. **Templo.** En la cella, junto al altar, la inscripción con la pista del puzle 1. Detrás del altar, una trampilla
   en el suelo baja a la **favissa** (sala oculta dentro del podio, cofre `oculto`).
5. **Termas.** Apodyterium, frigidarium, tepidarium y caldarium elevado sobre el hipocausto. Desde el praefurnium
   (horno) una boca baja al **hipocausto** (sala oculta, cofre `oculto`).
6. **Castellum.** Planta baja con la pila de reparto y tres palancas bajo los rótulos AQVA, IGNIS y TERRA; primer piso
   con la oficina del curator aquarum (cofre `menor`); azotea con el depósito y vistas.
   **Puzle 1** abre la hornacina secreta: escalera oculta que baja a las cloacas.
7. **Cloacas.** Galería de entrada con **trampa 1** (cable trampa y dos dispensadores de flechas, como el templo de
   la jungla). Colector principal con canal de agua. **Sala de los generadores** (dos generadores) con cofre
   `cloaca`. Un ramal tapado de telarañas lleva al **lararium oculto** (cofre `oculto`). Pozo con escalera de
   mano y reja de hierro que se abre desde abajo con una palanca: salida de un solo sentido a la calle norte.
8. **Antecámara.** Pasillo de un bloque con **trampa 2** (placas de presión flanqueadas por dispensadores, como el
   templo del desierto pero sin TNT) y vestíbulo con la fuente de las ofrendas: **puzle 2**.
9. **Cámara del tesoro.** El guardián *Centurión Aquilio*, el cofre `premium` sobre el altar y dos cofres `oculto`.
   Un botón junto a la puerta de hierro abre desde dentro (nadie se queda encerrado).

## Plantas por nivel

Los planos en texto con las celdas alcanzables (`·` = se pisa desde la entrada; `o` = solo con los puzles
resueltos) se generan con la auditoría: `docs/unicas/acueducto/plano_*.txt`.

- **Subsuelo -8 (cloacas, pies en y = -8).** Escalera secreta (x 73, z -6..3) → galería de entrada (x 72-74, z 4..11,
  trampa 1 en z 8) → colector (z 12-14, x 60-90, canal en z 13) → sala de generadores (x 68-82, z 16-26) → pasillo de la
  antecámara (x 79, z 27-31, trampa 2) → vestíbulo (x 78-80, z 32-33) → puerta de hierro (79, z 34) → cámara
  (x 73-85, z 36-43, paso en z 35). Lararium: x 65-69, z 6-10, tras el paso de telarañas (x 67, z 11). Pozo de salida con escalera de mano en (79, z 20).
- **Subsuelo -7 (cisterna, pies en y = -7).** Sala de 27 x 15 con 8 pilares, andén perimetral y cruz central, cuatro
  estanques de 1 de hondo. Generador sobre isleta en el centro con cofre `cisterna`.
- **Planta 0 (ciudad).** Ver plano. Muralla de 5 con almenas, torres en las esquinas, dos tramos derrumbados.
- **Castellum.** P0 (pies 1), P1 (pies 8), azotea (pies 15).
- **Templo.** Podio (pies 4), favissa dentro del podio (pies 1).
- **Caldarium.** Suelo elevado (pies 4); hipocausto debajo (pies 1, 2 de alto).

## Puzles (redstone; todo funciona tal como se coloca)

**Puzle 1 — Las palancas del castellum.** Tres palancas en el muro oeste de la sala (rótulos AQVA, IGNIS, TERRA).
Pista en el templo: *«El agua y la tierra sostienen la ciudad; el fuego la consume»*. La hornacina se abre solo con
AQVA y TERRA bajadas e IGNIS subida.
Mecanismo (dentro del muro doble x 75-76 y del pasillo oculto x 73-74): dos pistones pegajosos apilados (75, 1-2, -7)
mirando al norte, **extendidos al colocarse** y sujetando los dos bloques de la hornacina (75, 1-2, -9). Están
alimentados por una línea de polvo (x 74, z -5..1) que sube por un peldaño (75, 1, -5) → (75, 2, -6) y llega a los dos
pistones (el de abajo por el bloque que hay bajo el polvo, el de arriba directamente). Fuentes de la línea: antorcha
de redstone tras AQVA, antorcha tras TERRA (inversores: encendidas con la palanca subida) y la palanca IGNIS
directamente. La puerta queda cerrada mientras haya alguna fuente: abierta ⇔ AQVA ∧ ¬IGNIS ∧ TERRA. Al quitar la
energía los pistones se retraen y arrastran los bloques un paso al sur: la hornacina queda abierta.
El estado colocado ya es el estable (antorchas encendidas, polvo con su nivel de señal calculado, pistones extendidos
con su cabeza), así que no depende de ninguna actualización de bloque durante la generación.

**Puzle 2 — La fuente de las ofrendas.** Puerta de hierro (79, -8..-7, 34). En el muro, junto a la hoja de arriba, una
hornacina de 1 x 1 a la altura del pecho con una placa de presión de madera (80, -7, 34). Rótulo: *«OBOLVM AQVIS — Da
tu óbolo a las aguas»*. Ningún jugador cabe en la hornacina: hay que lanzar un objeto (o una flecha) sobre la placa.
La placa da energía fuerte al bloque de debajo (80, -8, 34), contiguo a la hoja inferior, y señal a la hoja superior:
la puerta se abre mientras haya algo encima. Por dentro, un botón en el paso (79, -7, 35) abre la puerta.

**Salida de las cloacas.** Trampilla de hierro en la calle norte (79, 0, 20) sobre un pozo con escalera de mano. La
palanca del techo (80, -1, 20) carga el enlosado contiguo y abre la trampilla; desde la calle no se puede abrir.

## Trampas

- **Trampa 1** (galería de entrada, z 8): cable trampa de lado a lado (x 72-74) con ganchos en hornacinas de los dos
  muros. Cada gancho da energía fuerte al bloque al que está sujeto y el dispensador que hay encima (y -7, a la
  altura de la cabeza) dispara flechas a través de la hornacina.
- **Trampa 2** (pasillo de la antecámara): dos placas de presión de piedra (z 29 y 31) en un pasillo de un bloque; cada
  placa tiene un dispensador de flechas a cada lado, a la altura de los pies.

## Enemigos

- Generadores: araña en la cisterna; zombi momificado (husk) y esqueleto en la sala de generadores.
- Guardián final: **Centurión Aquilio** (husk, `PersistenceRequired`): 60 de vida, 5 de ataque, 0,4 de resistencia
  al empuje; casco de oro, peto de hierro, grebas de malla, botas de hierro, espada de hierro y escudo; el equipo no
  cae (probabilidad 0). Husk porque el desierto es su sitio y no arde al sol si sale.
- Sin aldeanos ni gólems: la ciudad está abandonada desde hace siglos.

## Cofres y botín (solo vanilla)

Cada tabla tiene un grupo extra con `solo_sin_lootr` (con Lootr cada jugador abre su propio cofre y recibe solo lo base).

| Tabla | Dónde | Contenido |
|---|---|---|
| `menor` | casas, tiendas, castellum P1 (cofres y barriles) | pan, pescado seco, huesos, cuerda, papel, pepitas de hierro y oro, ladrillos, alguna esmeralda |
| `tienda` | tabernae y puestos del foro | tinte, lana, cuero, cuencos, esmeraldas, vasijas |
| `termas` / `villa` | termas y villa | lingotes de oro y hierro, libro, etiqueta, botella de experiencia |
| `cisterna`, `cloaca` | mazmorras | huesos, carne podrida, hierro, oro, redstone, flechas, poción de curación |
| `oculto` | favissa, hipocausto, lararium, cámara (x2) | diamante (1-2), libro encantado, manzana de oro, plantilla de adorno *dune*, ámbar de oro |
| `premium` | cámara del tesoro | 90 %: *Gladius del Prefecto* (espada de hierro con nombre, Filo II), *Copa del Curator* (bloque de oro con nombre), discos (*relic*, *far*, *mall*), plantillas de adorno (*dune*, *coast*, *wild*), libros moderados, esmeraldas. 10 %: espada o peto de diamante encantados (nivel 20-30), manzana de oro encantada. Nada de netherita ni élitros. |

## Ruina (80-85 % en buen estado)

La ruina se concentra en sitios con sentido: tejados hundidos con escombros (losas de ladrillo, arena, arena
sospechosa con el botín de arqueología del templo del desierto) en cuatro casas, una casa reducida a muros bajos,
dos tramos de muralla caídos, una columna del foro derribada, el vano 9-10 del acueducto desplomado y los dos últimos
vanos sin piso alto. La auditoría mide la superficie construida en planta y exige que la parte dañada esté entre el
15 y el 20 %. El procesador de desgaste solo cambia texturas (arenisca agrietada, ladrillo musgoso en las cloacas).

## Contraste con el criterio de diseño de Alberto

- Escaleras completas, sin saltos; puertas con salida; ninguna estancia inaccesible (las ocultas tienen acceso).
- Muebles contra los muros, ventanas altas (y = 3) que no tapa nada; centro libre salvo mesas.
- Faroles colgados del techo o con cadena; agua siempre contenida (estanques con brocal, canal cerrado).
- Simetría en templo, castellum, termas y foro; cada elemento con su función (pila de reparto, hipocausto, pórticos).
- Auditoría automática previa a la generación (ver abajo).

## Auditoría propia (`tools/gen/unicas/acueducto/auditoria.py`)

Se ejecuta en `build()` y cualquier fallo detiene la generación:
- Recorrido a pie (`lint.walk`) sobre la estructura completa montada desde la puerta sur: con los puzles resueltos
  se alcanzan todas las puertas, cofres, barriles, escaleras, palancas, botones y el guardián; con los puzles sin
  resolver la cámara del tesoro y las cloacas **no** se alcanzan (los puzles cierran de verdad).
- Nada flotando: todo bloque está unido al suelo (y = 0 o subsuelo) por bloques vecinos.
- Simulador de redstone: tabla de verdad del puzle 1 (8 combinaciones), estado colocado = estado estable, trampas,
  puzle 2, botón interior y salida de las cloacas.
- Jigsaws intactos y en la cara de su caja; las cajas de las piezas no se solapan y caben en el radio de 116.
- Porcentaje de ruina entre 15 y 20 %.

## Verificación hecha

- `./gradlew build`: genera, valida contra los registros de 26.3 y audita (lint genérico + auditoría propia) sin avisos.
- Auditoría propia: 0 fallos; ruina medida 15,9 % (85 % en buen estado).
- Servidor dedicado 26.3 real (`place template` y `place structure`): puzle 1 cerrado al colocar, abierto solo con
  AQVA + TERRA, cerrado al añadir IGNIS o con TERRA sola (palancas puestas con `setblock` y actualización forzada en
  un bloque vecino, porque no hay jugador); trampa 1 dispara los dos dispensadores al cruzar un soporte de armadura;
  trampa 2 dispara con un zombi encima; un objeto lanzado a la hornacina abre la puerta de hierro; el guardián está en
  la cámara; con la estructura completa colocada (girada 180°), los 52 cimientos de los 13 pilares tienen bloque debajo.
- No verificado: el aspecto en el juego (sin capturas de Alberto), el comportamiento de `beard_box` sobre dunas altas
  y valles profundos concretos, y la salida por la reja (solo con el simulador).
