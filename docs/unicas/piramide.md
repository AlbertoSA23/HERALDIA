# Templo-pirámide (`heraldia:unicas/piramide`)

Gran pirámide escalonada de estilo mesoamericano en la selva, con escalinata central, templo en la cima,
dos plataformas laterales y un juego de pelota adosado. Por dentro baja en espiral de salas hasta un cenote
interior y, en lo más hondo, la tumba del Rey Jaguar y la cámara del tesoro.

- Biomas: `minecraft:jungle` y `minecraft:sparse_jungle` (la jungla de bambú queda fuera: el bambú la taparía).
- Rareza: la del contrato (`spacing` 250 / `separation` 190 chunks, una cada ~3.000-5.000 bloques).
- Tamaño: 79 × 70 bloques de huella; 36 de alto sobre el suelo y 27 de sótano. Dos piezas jigsaw (radio 80).

## En qué se distingue de las vanilla

| | Templo de la jungla | Pirámide del desierto | Templo-pirámide |
|---|---|---|---|
| Forma | caja de piedra de 3 pisos | pirámide lisa con 2 torres | 6 cuerpos en talud-tablero con escalinata saliente, templo con crestería, juego de pelota |
| Material | adoquín y adoquín musgoso | arenisca | toba (ladrillos, pulida, cincelada), estuco rojo de terracota; sótano de ladrillo de piedra, roca natural y pizarra profunda |
| Interior | un pasillo, 2 cofres | una cámara con TNT | 6 niveles, 13 cofres, 4 generadores, guardián, 3 salas ocultas |

## Piezas y terreno

- `superficie` (rígida, `beard_thin`): todo lo que está de y = 0 hacia arriba. El pavimento de la plaza está en
  y = 0, de modo que el terreno se rellena hasta él. Todo el volumen de la huella hasta y = 20 (y hasta la cima
  sobre la pirámide) va explícitamente en aire: una loma no puede atravesar la pirámide.
- `subsuelo` (rígida): de y = -1 a -27, colgada de la primera con un jigsaw vertical (`down_north` → `up_north`,
  unión `aligned`, misma rotación). Es un bloque macizo de roca con las salas talladas: el ajuste del terreno de
  esa pieza actúa a 27 bloques de profundidad (donde la densidad del terreno es alta) y no hunde la superficie;
  lo que haya alrededor no puede abrir agujeros porque cada sala está rodeada de roca de la propia plantilla.

## Plantas por nivel (cota = altura de los pies)

**Exterior (cota 1).** Plaza de toba con calzada (sacbé) hacia la escalinata. Dos plataformas laterales de 9 × 9
(cota 4) delante de la pirámide: la del oeste con el altar de las ofrendas y un cofre; la del este con un
*tzompantli* (empalizada de cráneos). Dos estelas. Al este, el juego de pelota: callejón de 7 entre dos taludes
con banco inclinado, muro y aro de piedra en cada lado; en lo alto del talud oeste, un pequeño adoratorio con
cofre. El extremo sur del talud este está derrumbado.

**Pirámide.** Seis cuerpos de 4 de alto (mitad 24, 21, 18, 15, 12, 9) en talud-tablero: talud de escalones,
moldura, tablero rehundido con relieves y cornisa. Escalinata de 9 de ancho que sobresale 7 bloques, con alfardas
y cabezas de serpiente al pie. Cima a cota 24.

**Templo de la cima (cota 24).** Pórtico con tres vanos y santuario con altar, cofre de ofrendas y la boca de la
Escalera de las Inscripciones (hueco con pretil). Crestería calada sobre el techo, rota en su extremo este.

**Escalera de las Inscripciones.** Tramo A (3 de ancho) hacia el norte de cota 24 a 12; rellano; tramo B central
hacia el sur de cota 12 a 1. Del rellano salen la Cámara de las Ofrendas (oeste, cofre) y la **Cámara tapiada**
(este): su puerta está cegada con adoquín y una grava sospechosa; quien la abre encuentra un cofre oculto.

**Sala del Cenote (cota 1).** Sala de columnas de 25 × 17 en el corazón de la pirámide. En el centro, la boca del
pozo (octógono de radio 4) con pretil, que cae 15 bloques hasta el agua del cenote. Desde aquí se llega también por
la **Brecha oeste**: el muro de la base está reventado y una galería lleva a la sala; a media galería, un cable
trampa dispara dos dispensadores de flechas. En la esquina sureste baja la escalera al subsuelo.

**Galerías del inframundo (cota -6).** Corredor en U alrededor del pozo con tres ventanas a él. Salidas:
- Norte: pasillo con **trampa de foso**: tres placas de presión abren tres trampillas de hierro; el foso (3 de
  hondo, sin daño) tiene salida propia por una escalera al corredor. Al fondo, la Cámara del Juicio (cofre).
- Oeste: guarida de arañas (generador de arañas de cueva, telarañas, cofre).
- Este: osario (generador de esqueletos, huesos, cofre).
- Suroeste: escalera al cenote.

**Cenote (cota -14).** Caverna natural de radio 9 con bóveda, estalactitas y raíces; poza de radio 6 y 5 de hondo
con pepinos de mar en el fondo; cornisa transitable alrededor. Bajo el agua, al este, un túnel (los pepinos lo
señalan) lleva a la **Cámara sumergida**: sala seca con cofre oculto. Al norte de la cornisa baja la escalera a la
tumba.

**Tumba (cota -24).** Sala de los Guardianes (generador de zombis, estatuas, cofre), pasillo de **losas de dardos**
(seis placas sobre dispensadores que disparan hacia arriba) y Tumba del Rey: sarcófago, ajuar (cofre) y el
**guardián «El Rey Jaguar»** (zombi con corona y pectoral de oro y espada de hierro; 40 de vida, daño 5,
armadura 4, sin refuerzos ni botín de equipo, `PersistenceRequired`). En el muro norte, un nicho ciego: es la
**puerta secreta**. Una palanca escondida a ras de suelo en un rebaje del mismo muro apaga una antorcha de
redstone; los dos pistones pegajosos que sostienen los bloques de la puerta se retraen y se abren al
**Cámara del Tesoro** (cofre premium).

## Recorrido del jugador

Plaza → plataformas (2 cofres) → juego de pelota (1) → escalinata → templo (1) → Escalera de las Inscripciones
→ Cámara de las Ofrendas (1) y Cámara tapiada (oculta, 1) → Sala del Cenote (1). Alternativa: Brecha oeste con la
trampa de cable → Sala del Cenote. Bajada a las galerías: Cámara del Juicio tras la trampa de foso (1), arañas
(1), osario (1) → cenote: buceo a la Cámara sumergida (oculta, 1) → Sala de los Guardianes (1) → losas de dardos →
Tumba (ajuar, 1; guardián) → palanca → Cámara del Tesoro (premium). Atajo para valientes: saltar al pozo desde la
Sala del Cenote (cae en 5 bloques de agua).

## Redstone: por qué funciona al generarse

Todo circuito está en un estado de reposo coherente y nada necesita una actualización de bloque al colocarse:
- Cable trampa: ganchos `attached=true` y cuerda `attached=true` (como el templo de la jungla); el gancho activa
  con fuerza su bloque de apoyo y el dispensador está pegado a ese bloque.
- Foso: la placa activa con fuerza el bloque que pisa y ese bloque toca la trampilla de hierro; en reposo nada
  tiene corriente.
- Dardos: la placa está encima del dispensador, que la recibe directamente.
- Puerta secreta: el único circuito con corriente en reposo. Antorcha encendida, bloque de encima con carga
  fuerte, pistones extendidos con su cabeza pegajosa y los bloques de la puerta delante. La palanca carga el
  bloque de la antorcha → se apaga → los pistones se retraen tirando de la puerta. Al bajar la palanca, se cierra.

Se comprueba en la auditoría (estados y adyacencias) y en un servidor real (`prueba_servidor.py`, que coloca las
plantillas y fuerza cada circuito).

## Generadores y enemigos

Arañas de cueva (guarida), esqueletos (osario), zombis (Sala de los Guardianes) y esqueletos cenagosos (Cámara del Juicio),
todos en el subsuelo. Guardián final en la tumba. Sin aldeanos ni gólems: es una ruina sellada.

## Estado (80-85 % en buen estado)

Procesadores de la pieza: ladrillo y toba pulida → toba (erosión), terracota roja → terracota (estuco lavado),
ladrillo de piedra → musgoso o agrietado, pizarra → agrietada. Huecos con sentido hechos a mano: esquina sureste de
los cuerpos 4-6 desplomada con escombro en la terraza de abajo, brecha de la base oeste, crestería rota, alfarda
este mellada, extremo del juego de pelota derrumbado, enredaderas y musgo. La auditoría calcula la fracción de
superficie exterior intacta (esperada, con las probabilidades de los procesadores) y exige 0,80-0,85.

## Botín (solo vanilla; el grupo extra de cada cofre lleva `solo_sin_lootr`)

| Tabla | Dónde | Contenido |
|---|---|---|
| `menor` | plataformas, juego de pelota, templo, ofrendas, sala | comida, cacao, flechas, velas, pepitas y lingotes de oro, esmeralda suelta |
| `galeria` | juicio, arañas, osario, guardianes | lo anterior más hierro, oro, lapislázuli, botella de experiencia, libro encantado modesto |
| `oculto` | cámara tapiada, cámara sumergida | oro, esmeraldas, diamante suelto, manzana de oro, fragmentos de cerámica, adorno de armadura salvaje, libro encantado |
| `tumba` | ajuar del rey | oro, esmeraldas, equipo de oro encantado, adorno salvaje, disco |
| `premium` | cámara del tesoro | base de oro, esmeraldas y experiencia; y un lote: 90 % vistoso (corona y cetro con nombre, encantamientos moderados, adornos de armadura, discos, fragmentos) o 10 % algo más fuerte (espada o pectoral de diamante con nombre y encantamientos 20-30, manzana de oro encantada) |

Sin netherita en equipo, sin élitros, sin tótems.

## Contraste con el criterio de diseño

- Escaleras completas (escalinata, tres tramos interiores y tres escaleras de sótano, todas de peldaño en peldaño);
  la única caída es el foso de la trampa, de 3 bloques y con salida.
- Ninguna puerta ni sala sin salida; las tres salas ocultas tienen acceso real (romper el tapiado, bucear, palanca).
- Nada flotando: la auditoría exige que todo bloque esté unido al suelo; faroles con cadena; el agua está encerrada
  por todos los lados salvo por arriba.
- Simetría en la pirámide, el templo, las plataformas y el juego de pelota; los derrumbes rompen la simetría a
  propósito.

## Resultado y comprobaciones

- Auditoría (condición para generar): 13 cofres y 4 generadores alcanzables a pie desde la plaza (10.854 celdas),
  con la palanca, las trampas, el guardián y las tres salas ocultas; sin abrir la puerta secreta el tesoro no se
  alcanza y sin romper el tapiado la cámara tapiada tampoco; desde el fondo del foso se vuelve a la plaza; nada
  flota; el agua está encerrada; ningún bloque tiene corriente salvo la antorcha de la puerta. Superficie exterior
  en buen estado: 0,825 (erosión del ladrillo y la toba pulida calculada para el centro del intervalo: 13,7 %).
- Servidor dedicado 26.3 (`prueba_servidor.py`, plantillas sin rotación): guardián con 40 de vida; puerta cerrada
  en reposo, abierta al cargar el bloque de la antorcha y cerrada otra vez; cable trampa, placas del foso y losas
  de dardos disparan con un soporte de armadura encima; el agua no se sale; el cofre premium lleva su tabla.
- Prueba de humo: la estructura se coloca con `/place structure` y todas sus tablas de botín se abren.
- Sin comprobar: el aspecto en el juego (faltan capturas de Alberto) y el ajuste del terreno en una jungla real
  con `/place structure` en distintos relieves.

Planos de planta por nivel en [`piramide/planos.txt`](piramide/planos.txt) (`.` alcanzable a pie) y renders en
`piramide/*.png`. Se regeneran con `python3 tools/gen/unicas/piramide/planos.py`.
