# Ciudadela enana (`heraldia:unicas/ciudadela`)

Ciudad excavada dentro de una montaña. Una sola variante, diseñada a mano. Módulo: `tools/gen/unicas/ciudadela/`
(geometría en `plano.py`, botín en `botin.py`, redstone en `redstone.py`, auditoría propia en `auditoria.py`);
colocación en Java: `io.github.albertosa23.heraldia.unicas.ciudadela`.

## Colocación en la ladera (por qué Java)
- El jigsaw elige la rotación al azar y no sabe dónde baja la ladera; `bury` y `beard_box` entierran o vacían
  la caja entera, incluida la puerta (la ciudad antigua y las cámaras de prueba están enteras bajo tierra y no
  tienen fachada). Por eso la ciudadela usa un tipo de estructura propio, `heraldia:ciudadela`, con
  `terrain_adaptation: none`.
- La plantilla es una sola pieza (`PoolElementStructurePiece` de un pool de un elemento, con sus procesadores).
  Fuera de las salas solo lleva `structure_void`: la roca natural se conserva. Cada sala tiene una piel propia de
  dos bloques (ladrillo de pizarra profunda por dentro, piedra por fuera) para que una cueva o un acuífero no la
  atraviesen; la piedra exterior se confunde con la montaña y admite menas.
- El tipo Java prueba 4 rotaciones x 25 posiciones (rejilla de 16 bloques alrededor del chunk) y mide el terreno
  con el mapa de alturas de generación:
  - delante de la puerta (5 puntos a 2 bloques del pórtico): terreno casi llano (diferencia <= 5) y sin agua;
    la puerta se coloca a la altura mediana de esos puntos;
  - más adelante (3 puntos a 10 bloques): no sube más de 3 (la puerta no da a un muro);
  - sobre la ciudad: una rejilla de techos (cada 8 bloques, la altura máxima de la plantilla en esa columna,
    sin el pórtico) que escribe el generador en el JSON; se exige roca hasta el techo menos 1 en el 75 % de las
    celdas.
  Se queda con la mejor opción; si ninguna cumple, no se genera en esa celda de la rejilla. Con `/place`
  (que acepta cualquier bioma) se coloca en la mejor opción aunque no cumpla, para poder probarla.
- El punto que se comprueba contra el bioma es el centro de la ciudad a la altura de la puerta (bajo la montaña),
  no la puerta, que puede caer en el bioma del pie de la ladera.
- Biomas: `stony_peaks` y `jagged_peaks`. Paso `underground_structures`. Rareza: `spacing` 250 / `separation`
  190 chunks (una cada ~4.000 bloques en la rejilla; menos en la práctica, porque exige bioma y ladera).

## Niveles (coordenadas de diseño: x hacia el este, z hacia dentro de la montaña; la puerta mira al norte, z=0)
Suelo de cada nivel (el jugador pisa en suelo+1):

| Nivel | Suelo | Salas |
|---|---|---|
| N0 | y=30 (trono y=33) | pórtico, salón de columnas, barracones, vestíbulo, almacén, salón del trono, cámara real oculta |
| N1 | y=21 | rellano, forjas, pasillo, cervecería |
| Bodega | y=15 | bodega oculta del cervecero |
| N2 | y=12 | estación de vagonetas, túnel oeste, cubil de arañas, galería hundida y escondite del minero, abismo con puente, rellano del abismo, pasillo de la trampa |
| N3 | y=3 | antecámara de la cerradura, bóveda del tesoro |

### N0
- **Pórtico** (x 25-45, z 0-7): terraza tallada de 14 de alto con dos estatuas de guardianes enanos y braseros.
  Cimiento de piedra debajo para que no quede en el aire si la ladera baja.
- **Gran puerta** (z 8-10): arco de 5 x 7 en una fachada de 3 de grueso.
- **Salón de columnas** (x 18-52, z 11-44, 12 de alto): dos filas de 5 pilares de basalto con capiteles,
  pasillo central de baldosas con incrustaciones de oro, faroles colgados con cadena, bancos junto a los muros.
  Ruina: un pilar derrumbado con escombros.
- **Barracones** (oeste): literas (camas), soportes de armadura, armero, mesa con bancos, 2 cofres menores.
  Ruina: esquina del techo hundida con escombros y telarañas.
- **Vestíbulo y almacén** (este): escalera principal al N1. Almacén con hileras de barriles (botín de almacén).
  **Sala oculta 1**: tras la última hilera, un hueco de un bloque junto al muro lleva a un cuarto con cofre oculto.
- **Salón del trono** (x 24-46, z 46-64, suelo 33): tres peldaños desde el salón, estrado con trono de oro,
  alfombra, estandartes, braseros. El muro del fondo tiene hornacinas entre pilastras.
  **Puzle 1 (puerta secreta de pistones)**: dos hornacinas bajas con palanca a cada lado de la hornacina central.
  La de la izquierda (bajada) mantiene extendidos dos pistones pegajosos ocultos tras la pilastra; al subirla,
  los pistones retiran los dos bloques del fondo de la hornacina central y se abre el paso a la
  **cámara real (sala oculta 2)**: cama, mesa y cofre real. La palanca de la derecha es un señuelo.

### N1
- **Escalera** desde el vestíbulo (9 peldaños) al rellano.
- **Forjas** (x 36-64, z 49-70, 9 de alto): cuatro hornos con campana de piedra negra y crisol de lava contenida
  (lava rodeada por todos los lados), altos hornos, yunques, mesas de herrería, afiladoras, calderos de lava,
  2 cofres de forja. Ruina: un crisol frío (magma) y yunques dañados.
- **Cervecería** (x 8-25, z 46-64): cubas gigantes de madera, barriles, calderos con agua, soportes para pociones,
  mesa larga con sillas, 2 cofres de cervecería. **Sala oculta 3**: trampilla cerrada en un rincón oscuro entre
  dos cubas; escalera de mano hasta la bodega del cervecero (cofre oculto).
- **Escalera** desde las forjas (9 peldaños) a la estación de las minas.

### N2
- **Estación** (x 30-46, z 26-39): vías, vagonetas (una con cofre de mina), puntales de madera.
- **Túnel oeste** con vía y marcos de madera cada 4 bloques hasta el **cubil de arañas**: veta con menas,
  telarañas, **generador de arañas de cueva** y vagoneta con cofre de mina.
- **Galería hundida** (rama norte): derrumbe parcial con paso de un bloque entre escombros y telarañas.
  **Trampa 1 (placa con TNT, como el templo del desierto)**: placa de piedra con TNT dos bloques debajo, lejos de
  los cofres. Detrás, el **escondite del minero (sala oculta 4)** con cofre oculto.
- **Abismo** (x 48-58, z 20-56): sima de 15 de hondo con lava al fondo. **Puente** de 3 de ancho con barandillas
  y cadenas al techo. Ruina: un tramo de barandilla caído y losas agrietadas.
- **Rellano del abismo**: **generador de esqueletos** (zona oscura).
- **Pasillo de la trampa**. **Trampa 2 (cable trampa con dispensadores, como el templo de la jungla)**: cable entre
  dos ganchos y cuatro dispensadores con flechas en los muros.
- **Escalera** de 9 peldaños al N3.

### N3
- **Antecámara**: **generador de zombis** (oscura). **Puzle 2 (cerradura de combinación)**: cuatro palancas en
  el muro, dos sobre oro y dos sobre pizarra. La puerta de hierro de la bóveda solo se abre con las dos de oro
  subidas y las dos de pizarra bajadas (puerta = A y B y no C y no D, con inversores de antorcha tras el muro).
- **Bóveda del tesoro** (x 59-69, z 69-80): pasillo de 4 por el muro grueso, montones de oro, 2 cofres de bóveda
  a los lados y el **cofre premium** en un estrado al fondo. **Guardián**: Borin Barbahierro (vindicador con
  nombre, 60 de vida, hacha de hierro, casco y peto de hierro, `PersistenceRequired`).

## Recorrido del jugador
Pórtico → salón de columnas (barracones al oeste, almacén y sala oculta 1 al este, trono y sala oculta 2 al
norte) → vestíbulo → escalera → forjas (cervecería y sala oculta 3 al oeste) → escalera → estación → túnel oeste
(cubil) y galería hundida (trampa 1, sala oculta 4) → puente sobre el abismo → rellano → pasillo de la trampa 2 →
escalera → antecámara (puzle 2) → bóveda.

## Cofres y botín (`heraldia:unicas/ciudadela/<tabla>`; cada tabla tiene un grupo extra `solo_sin_lootr`)
| Tabla | Dónde | Contenido |
|---|---|---|
| `menor` | salón, vestíbulo, estación | comida, antorchas, carbón, pepitas, cuerda; extra: lingote de hierro, pepitas de oro, esmeralda |
| `barracones` | 2 en barracones | flechas, arco y espada de hierro gastados, escudo, malla; extra: casco encantado (5-10), ballesta |
| `almacen` | barriles del almacén | carbón, antorchas, raíles, cuero, flechas, pepitas; extra: lingotes de hierro |
| `forja` | 2 en forjas | lingotes de hierro, carbón, oro, herramientas de hierro, cubo, escudo; extra: diamante (raro), peto encantado |
| `cerveceria` | 2 en cervecería | trigo, pan, azúcar, miel, botellas, bayas, setas; extra: zanahoria dorada, esmeraldas |
| `mina` | vagonetas con cofre | hierro y oro en bruto, carbón, lapislázuli, redstone, raíles, pico gastado; extra: diamante (raro), manzana dorada |
| `oculto` | salas ocultas 1, 3 y 4 | lingotes de oro, esmeraldas, diamantes (pocos), libro encantado, manzana dorada, frascos de experiencia; extra: diamantes, libro (10-20) |
| `real` | cámara real | diamantes, esmeraldas, corona (casco de oro con nombre, Protección II), libro (15-25), disco, plantilla de adorno; extra: manzana dorada, oro |
| `boveda` | 2 en la bóveda | lingotes y bloque de oro, oro en bruto, esmeraldas, diamantes, manzana dorada; extra: diamantes, libro |
| `premium` | cámara final | 90 %: objetos con nombre (hacha de Borin, yelmo del rey, jarra de la última cerveza), discos, plantillas de adorno (moldeador, anfitrión, explorador), oro; 10 %: pico de diamante con nombre (Eficiencia III, Irrompibilidad II), peto de diamante (Protección II), manzana de oro encantada, libro de Fortuna III |

Sin netherita en equipo ni élitros; solo objetos vanilla.

## Generadores, trampas y puzles
- Generadores (3, en zonas sin luz): arañas de cueva (cubil), esqueletos (rellano del abismo), zombis (antecámara).
- Guardián final con nombre en la bóveda.
- Trampas: placa con TNT (galería hundida), cable trampa con 4 dispensadores de flechas (pasillo).
- Puzles: puerta de pistones con palanca oculta y señuelo (trono); cerradura de 4 palancas (bóveda).
- Todo el redstone se coloca en un estado estable: la auditoría (`redstone.py`) recalcula como el juego las
  conexiones de cada cable y la señal de cada antorcha, pistón, puerta, dispensador y TNT, comprueba que el
  estado colocado coincide con el calculado (nada depende de una actualización que no ocurre al generar) y
  simula la solución: la puerta de pistones se abre al subir la palanca buena y no con el señuelo; la de la
  bóveda se abre con la combinación correcta y con ninguna de las otras 15.

## Estado
- 80-85 % en buen estado: procesador de degradación (ladrillo y baldosa agrietados, pulida a adoquín) y
  ruinas a mano con sentido (pilar caído, techo hundido en barracones, galería derrumbada, crisol frío,
  barandilla caída). La auditoría mide la proporción de superficie visible degradada y exige 15-20 %.
- Sin aldeanos ni gólems: es una ciudad abandonada; solo queda el guardián.

## Contraste con el criterio de Alberto
- Escaleras completas (9 peldaños por nivel, sin saltos); ninguna puerta sin salida: la auditoría recorre a
  pie desde la entrada todas las puertas, cofres, barriles, palancas, generadores y escaleras de mano.
- Muebles contra los muros; centro de las salas libre salvo mesas con sillas.
- Nada flotando: faroles con cadena, lava contenida, sin agua suelta (solo en calderos).
- Simetría en el pórtico, el salón y el trono; asimetría solo donde tiene función (almacén, minas).
- Planos por nivel con celdas alcanzables y renders: `docs/unicas/ciudadela/`.
