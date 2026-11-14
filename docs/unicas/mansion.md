# Mansión encantada (`heraldia:unicas/mansion`)

Mansión victoriana decadente en el pantano: finca amurallada de 62 × 72 bloques con jardín delantero, casa de
tres plantas con buhardilla bajo un tejado a dos aguas muy inclinado, torreón cuadrado de cinco niveles con chapitel en la esquina noroeste, invernadero de cristal arruinado al este, cementerio familiar con panteón
detrás y, bajo la casa, bodega, osario, laboratorio oculto y cámara del tesoro.

Se distingue de la mansión del bosque vanilla en todo lo visible: ladrillo de pizarra profunda oscuro con
remates de abeto (no roble oscuro y abedul), tejado de tejas de pizarra profunda a dos aguas con torreón y
chimeneas, finca abierta con cementerio, luz de almas casi inexistente y un sótano con mecanismos.

## Bioma y colocación

- Bioma: `#heraldia:pantano` (pantano y manglar). El pantano es llano: la finca cabe sin desmontes.
- Rareza: `spacing` 250 / `separation` 190 chunks (una cada ~3.000-5.000 bloques, valor por defecto del contrato).
- Dos piezas rígidas unidas por un jigsaw vertical: `casa` (finca, casa, invernadero, cementerio; su capa y=0 es el
  suelo) y `sotano` (todo lo que queda por debajo de y=0). `size` 2, `max_distance` 48.
- Adaptación `beard_thin`: el terreno se ajusta a la base de la casa (y=0) y la finca queda en una isla llana.
  El sótano es una pieza aparte, por debajo de la casa, que **rellena por completo su caja** con piedra y tierra
  (no deja huecos de terreno sin decidir), así que el `beard` no puede abrir un foso alrededor ni dejar cavidades
  junto a sus muros. El panteón no tiene cripta subterránea: va sobre un túmulo y su cripta está dentro del túmulo.

## Alturas (coordenadas de la plantilla `casa`; el sótano usa las mismas)

| Nivel | Suelo (bloque) | Pies | Salas |
|---|---|---|---|
| Sótano | -6 | -5 | -5..-2 (techo -1) |
| Planta baja | 1 | 2 | 2..6 |
| Primera | 7 | 8 | 8..11 |
| Segunda | 12 | 13 | 13..16 |
| Buhardilla | 17 | 18 | bajo el tejado (cumbrera en y=31) |
| Mirador del torreón | 23 | 24 | 24..26, chapitel hasta y=37 |

## Plantas

Casa principal x 12..49, z 14..40 (fachada al norte, z=14). Entrada de la finca por la verja de z=0.

**Planta baja**
- Porche con columnas y peldaño; puerta doble al **vestíbulo** (x 25..36, z 15..29, doble altura) con
  **escalera doble**: dos tramos de 6 peldaños pegados a los muros este y oeste que suben hacia el fondo hasta un
  rellano-galería (z 25..29) en la primera planta, con barandilla. Lámpara de almas colgada en el centro.
- Oeste delante: **biblioteca** (x 13..23, z 15..26) con estanterías del suelo al techo, mesas de lectura y la
  puerta al torreón. En su muro sur, entre dos cuerpos de estantería salientes, está la **estantería secreta**.
- Oeste detrás: franja oculta (z 28..30) con el mecanismo y la escalera secreta; **cocina** (x 13..23, z 32..39)
  con hogar de almas, despensa, escalera de servicio a la bodega y escala de servicio a las plantas altas.
- Centro detrás: **comedor** (x 25..36, z 31..39) con mesa larga y sillas con el respaldo hacia fuera; puerta
  acristalada a la terraza trasera.
- Este: **salón de baile** (x 38..48, z 15..39) de suelo ajedrezado, chimenea en el muro sur y puertas al
  **invernadero arruinado** (x 51..59, z 19..35): cristal roto, enredaderas, bancales secos y un barril.

**Primera planta**: rellano; al oeste pasillo con **dormitorio principal** (con puerta al torreón) y
**dormitorio de invitados**; al centro el **estudio del señor**; al este la **galería de retratos** (cuadros
reales de vanilla a lo largo de 25 bloques).

**Segunda planta**: pasillo transversal (z 26..28) que une seis estancias: dos **dormitorios de invitados**,
**cuarto de los niños**, **cuarto de costura**, **sala de música** y **habitaciones del servicio** (donde
llega la escala de servicio).

**Buhardilla**: todo el bajo cubierta con vigas, trastos, telarañas, un gato negro y un agujero en el tejado.

**Torreón** (x 8..14, z 10..16): escalera de caracol de 22 peldaños alrededor de un machón central, con
rellano y puerta en cada planta, la buhardilla y el mirador; cofre en el mirador.

**Sótano** (y -5): bodega bajo la cocina (llega la escalera de servicio); almacén bajo el comedor; y la parte
oculta, solo por la escalera secreta: **antecámara** bajo la biblioteca → corredor con trampa → **osario** bajo
el vestíbulo → **laboratorio** bajo el salón de baile → puerta de hierro con combinación → **cámara del tesoro**.
Desde el osario, una puerta de hierro de un solo sentido (botón solo en el lado del osario) da al almacén para
volver por la bodega.

**Exterior**: verja con pilares y faroles de almas, camino de entrada con árboles muertos y farolas, muro
perimetral bajo con tramos caídos; detrás, terraza, **cementerio** vallado con tumbas (algunas rotas) y el
**panteón** sobre un túmulo con capilla y cripta.

## Recorrido del jugador

Verja → jardín → porche → vestíbulo. Libres: biblioteca, cocina, comedor, salón, invernadero, terraza y
cementerio. Escalera doble → primera planta. Torreón (desde la biblioteca o el dormitorio principal) o escala
de servicio (cocina) → segunda planta y buhardilla; torreón → mirador. Escalera de servicio → bodega → almacén
(callejón: la puerta de hierro no se abre desde aquí). Panteón → cripta (trampa). Estantería secreta → escalera
→ antecámara → corredor con cable trampa → osario → laboratorio → combinación → cámara final.

## Mecanismos (todos en reposo y coherentes al generarse)

Al colocar una plantilla no hay actualizaciones de bloque, así que cada circuito se guarda en su estado
estable: antorchas encendidas, polvo con su potencia y forma, repetidores y pistones extendidos con su cabeza,
tal como quedarían tras actualizarse. Nada se mueve hasta que el jugador acciona algo. Lo comprueba el
simulador de redstone del módulo (ver Auditoría).

1. **Estantería secreta (biblioteca)**: palanca en la estantería (x 18) → la antorcha del otro lado se
   apaga → el polvo y el repetidor dejan de alimentar dos pistones pegajosos (el de abajo por
   cuasiconectividad) → recogen las dos estanterías de la puerta (x 22) y se abre un paso de 1 × 2. Los pistones
   quedan ocultos tras un cuerpo de estantería saliente. Volver a bajar la palanca la cierra.
2. **Combinación del laboratorio**: cuatro palancas en el muro sur. Bajo cada una, una vela: encendida bajo la
   1.ª y la 4.ª. La puerta de hierro (x 47) se abre solo con 1.ª y 4.ª arriba y 2.ª y 3.ª abajo
   (abierta = A ∧ ¬B ∧ ¬C ∧ D: dos inversores, un bus de polvo O y un inversor de salida).
3. **Puerta de un solo sentido**: botón en el osario junto a la puerta de hierro al almacén.

## Trampas

- **Cable trampa** (como el templo de la jungla) en el corredor antecámara → osario: dos ganchos, el hilo y dos
  dispensadores con flechas en los muros, que disparan a la altura de la cabeza.
- **Placa de presión con dinamita** (como el templo del desierto) delante del cofre de la cripta del panteón:
  cinco bloques de dinamita bajo el suelo.

## Enemigos

- **Tres generadores**, todos en el sótano: zombi en la bodega, esqueleto en el osario y araña en el laboratorio
  (con telarañas). La cripta del panteón no lleva generador: sus monstruos pisarían la placa de la dinamita.
- Guardián final en la cámara del tesoro: **esqueleto wither «El Conde Malaquías»** (`PersistenceRequired`,
  60 de vida, armadura de cuero teñida de negro que no suelta; el juego le da su espada de piedra al generarse).
- Sin aldeanos ni gólems: la casa está abandonada. Solo un gato negro en la buhardilla.

## Cofres (33) y botín

Más ricos cuanto más escondidos. Cada tabla tiene un grupo base y un grupo extra marcado `solo_sin_lootr`.

| Tabla | Dónde | Contenido |
|---|---|---|
| `jardin` (2) | cobertizo del jardín, invernadero | semillas, harina de hueso, herramientas gastadas |
| `cocina` (5) | despensa (2), aparador del comedor, bodega (2) | comida, botellas, miel, azúcar |
| `menor` (13) | comedor, salón, dormitorios (5), cuarto de los niños, costura (2), música, servicio, almacén (2) | velas, cuerda, papel, lana, algo de hierro y oro, esmeraldas sueltas |
| `biblioteca` (2) | biblioteca, estudio | libros, papel, plumas, tinta, «Diario de la Condesa», un libro encantado a veces |
| `desvan` (3) | buhardilla (2), mirador del torreón | trastos con algo mejor: catalejo, brújula, discos 11/13 raros |
| `oculto` (4) | antecámara, osario, cámara del tesoro (2) | hierro, oro, diamante suelto, libro encantado, manzana dorada |
| `laboratorio` | laboratorio (2) | ingredientes y pociones (curación, visión nocturna, resistencia al fuego), frascos |
| `panteon` | cripta del panteón | oro, esmeraldas, una pieza con nombre, plantilla de adorno |
| `premium` | cámara del tesoro | ver abajo |

**Premium**: 90 % vistoso y 10 % algo más fuerte. Siempre 3-5 piezas vistosas: «Reloj de bolsillo del Conde»
(reloj con nombre), «Retrato de familia» (cuadro), «Hoja del Conde» (espada de hierro) y «Arco de caza de la
familia» con encantamientos de nivel 10-20, plantillas de adorno (anfitrión, criador,
moldeador, guía), discos 11, 13 y mall, oro y esmeraldas. Un grupo aparte de una tirada: 90 % nada, 10 % una
pieza fuerte (peto de diamante o espada de diamante con encantamientos 20-30, manzana dorada encantada o tótem).
Sin netherita en equipo ni élitros.

## Ruina (15-20 % de la superficie)

- Procesador del elemento: ladrillo de pizarra → agrietado (40 %), pizarra pulida → adoquín (20 %), adoquín y
  ladrillo de piedra → musgoso (35-40 %), cristal → nada (30 %, ventanas rotas), tejas → nada (4 %, goteras).
  Calculado sobre la superficie visible de la casa: ~12 % de bloques cambiados, más la ruina a mano: ~15-17 %.
- A mano: invernadero con media cubierta caída y paneles rotos, agujero del tejado de la buhardilla con
  escombros debajo, tramos del muro perimetral derribados, lápidas caídas, una lámpara caída en el salón.
- Huecos solo donde no rompen el recorrido ni dejan nada colgando.

## Auditoría (condición para generar)

`build()` añade a `reg.warnings` (y así la compilación falla) cualquier fallo de:
- `lint.py` sobre cada pieza (apoyos, faroles, cadenas, escaleras de mano, puertas con salida, jigsaws).
- Recorrido a pie sobre las dos piezas unidas desde la verja: cada puerta, cofre, barril, escalera, generador y
  palanca alcanzable; las zonas ocultas solo con los mecanismos abiertos (y no antes).
- Nada flotando: todo bloque conectado al suelo.
- Simulador de redstone: estado de reposo coherente; la palanca abre la estantería; solo la combinación correcta
  abre la cámara; el gancho dispara los dos dispensadores; la placa ceba la dinamita; el botón abre la puerta.

Planos por nivel (`planos.md`) y renders en `docs/unicas/mansion/`; se regeneran con `python3 -m unicas.mansion.planos`
desde `tools/gen`. La prueba en servidor (`prueba_servidor.py`) acciona en el juego la estantería y la combinación.

## Contraste con el criterio de diseño

- Escaleras completas sin saltos (caracol con peldaño de llegada a cada rellano), ninguna puerta sin salida,
  ninguna estancia inaccesible (lo comprueba el recorrido).
- Muebles contra los muros sin tapar ventanas; centro libre salvo mesas con sillas de respaldo hacia fuera.
- Faroles colgados con cadena, nada de agua suelta (no hay agua colocada).
- Simetría en fachada, vestíbulo, escalera doble, comedor y salón; el torreón rompe la simetría a propósito.
