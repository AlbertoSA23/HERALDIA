# Observatorio (`heraldia:unicas/observatorio`)

Observatorio astronómico abandonado en una cumbre ventosa. Una sola variante, diseñada a mano en
`tools/gen/unicas/observatorio.py`. Planos de planta y renders en `docs/unicas/observatorio/`.

## Colocación
- Biomas: `windswept_hills`, `windswept_gravelly_hills`, `windswept_savanna` (colinas ventosas, colinas
  pedregosas ventosas y meseta de sabana ventosa; ninguna otra estructura única las usa).
- Rejilla por defecto: `spacing` 250 / `separation` 190 chunks (una cada ~3.000-5.000 bloques).
- Dos piezas rígidas unidas por un jigsaw vertical: **superficie** (planta baja, planta alta, azotea y
  cúpula; 41 × 35 × 23) y **subsuelo** (archivo y cámara del tesoro). Adaptación `beard_thin`: el terreno
  se allana alrededor de la base de la pieza de superficie. El subsuelo es una pieza aparte para que su
  caja no hunda el terreno (la corrección de `beard_thin` solo actúa a ±12 bloques de la base de cada
  pieza y a esa profundidad el terreno es macizo); sus salas van envueltas en roca propia (dos bloques) y
  solo se colocan bloques donde hay salas, de modo que no aparece un cubo de piedra en la ladera.

## Coordenadas
x crece hacia el este, z hacia el sur, y = 0 es la losa de la planta baja (se pisa a y = 1).
La entrada está al norte (z = 0). Rotonda centrada en (20, 20), radio 9.

## Plantas
### Planta baja (y 1-5)
| Sala | Zona | Contenido |
|---|---|---|
| Camino y escalinata | x 18-22, z 0-5 | Pavimento, farolas sobre pilares |
| Vestíbulo | x 12-28, z 7-10 | Bancos, faroles; puertas a biblioteca, taller y planetario |
| Planetario (rotonda) | r < 8,5 | Planetario mecánico colgado del techo (sol de piedra luminosa y planetas de cobre con cadenas), techo de estrellas, mesas de cartografía y atriles en el muro |
| Biblioteca de los astrónomos | x 2-10, z 7-19 | Estanterías entre ventanas, atriles bajo las ventanas, mesa de lectura con sillas; **alfombra con trampilla oculta** (sala oculta 1) |
| Taller de óptica | x 30-38, z 7-19 | Vidrieras de cristal tintado, hornos, mesa de trabajo, muela, caldero, cristales expuestos; cofre menor |
| Antesala del archivo | x 2-10, z 21-33 | Almacén con barriles; escalera que baja al archivo; cofre menor |
| Escalera este | x 30-38, z 21-33 | Tramos a la planta alta y a la azotea |
| Galería sur | x 12-28, z 31-33 | Une las dos alas y entra al planetario por el sur |

### Planta alta (y 7-11)
| Sala | Zona | Contenido |
|---|---|---|
| Sala del telescopio | r < 8,5, abierta a la cúpula | Gran telescopio de cobre sobre pedestal apuntando a la rendija norte de la cúpula; cofre menor |
| Galería norte | x 12-28, z 7-10 | Catalejos sobre trípode junto a las ventanas |
| Dormitorio de los astrónomos | x 2-10, z 7-19 | 4 camas contra el muro oeste (sin tapar ventanas), mesillas, cofre menor |
| Comedor | x 2-10, z 21-33 | Mesa con sillas (respaldo hacia fuera), ahumador, barriles |
| Gabinete del astrónomo jefe | x 30-38, z 7-19 | Escritorio, estanterías, mesa de cartografía, cofre menor |
| Galería sur alta y rellano | x 12-38, z 21-33 | Unión con la escalera este |

### Azotea (y 13)
Pretil de muro de piedra, **reloj de sol** sobre la ala oeste (esfera de piedra lisa, gnomon y marcas
horarias con sensores de luz solar), catalejos en trípode sobre el ala este, cúpula de cobre oxidado en el
centro con una rendija de observación al norte.

### Archivo (subsuelo, y −6 a −2)
| Sala | Zona | Contenido |
|---|---|---|
| Rellano de la escalera | x 4-8, z 29-33 | Final de la escalera desde la antesala |
| Pasillo del hilo | x 9-13, z 30-33 | **Trampa 1**: cable trampa con dos dispensadores de flechas (como el templo de la jungla) |
| Archivo | x 14-26, z 20-33 | Estanterías en pasillos, **2 generadores** (zombi y araña) a oscuras, 2 cofres de archivo, telarañas. **Puzle de las fases** en el muro este. **Sala oculta 2** tras la estantería del muro norte |
| Gabinete del bibliotecario (sala oculta 1) | x 3-9, z 12-17 | Se llega solo por la trampilla bajo la alfombra de la biblioteca; cofre oculto |
| Gabinete de instrumentos (sala oculta 2) | x 17-23, z 13-16 | Puerta de pistones tras la estantería del nicho; palanca junto al nicho; cofre oculto |

### Cámara del tesoro (subsuelo, y −13 a −9)
| Sala | Zona | Contenido |
|---|---|---|
| Escalera | x 28, z 15-21 | Tras la puerta de hierro del puzle |
| Cámara de las horas | x 25-31, z 7-14 | Sensores de luz y relojes de piedra; barril de archivo |
| Pasillo de las losas | x 18-24, z 10 | **Trampa 2**: placas de presión con dispensadores de flechas a ambos lados |
| Sala del guardián | x 8-17, z 5-15 | Columnas, **1 generador** (esqueleto) y el **guardián** |
| Cámara del tesoro | x 2-6, z 8-12 | Puerta de hierro con botones; **cofre premium** |

## Recorrido del jugador
Entrada → vestíbulo → biblioteca, taller y planetario (cofres menores a la vista) → escalera este →
planta alta (dormitorio, comedor, gabinete, telescopio) → azotea (reloj de sol, pista del puzle) →
de vuelta abajo, antesala → archivo (trampa del hilo, generadores) → salas ocultas → puzle de las fases →
cámara de las horas → pasillo de las losas (trampa) → guardián → cofre premium.
El recorrido completo lo comprueba la auditoría a pie en estado «resuelto» (palanca y puzle accionados,
trampilla abierta).

## Puzle de las fases
Cuatro palancas en el muro este del archivo, cada una bajo un glifo de fase lunar: luna nueva (bloque de
carbón), creciente, llena (luz perla) y menguante. La puerta de hierro se abre solo con **luna nueva y
luna llena** levantadas y las dos crecientes bajadas. Pista: el suelo del planetario y la esfera del
reloj de sol marcan esas dos fases con los mismos bloques.
Circuito (todo en reposo y coherente al colocarse, sin depender de actualizaciones):
- Palancas de las fases «buenas» → bloque → antorcha de redstone (NO) → línea O.
- Palancas «malas» → bloque → polvo → línea O.
- Línea O → (el último polvo entra por el lado del soporte) → bloque → antorcha de salida (NO) junto a la hoja
  superior de la puerta. Si el polvo fuera encima de ese bloque, la antorcha encendida alimentaría el bloque de encima y
  este al polvo: reloj de redstone y antorcha fundida (fallo real encontrado en la prueba en servidor).
- En reposo la línea O está alimentada por las dos antorchas encendidas, con la potencia calculada en
  cada polvo; la antorcha de salida está apagada y la puerta cerrada. La auditoría simula el circuito
  para las 16 combinaciones y exige que solo una abra.

## Sala oculta 2: puerta de pistones
Dos pistones pegajosos extendidos (alimentados por una antorcha de redstone y casi-conectividad)
sujetan dos estanterías en el fondo de un nicho. La palanca junto al nicho apaga la antorcha: los pistones
se retraen, tiran de las estanterías y abren el paso. La auditoría comprueba la geometría del circuito.

## Trampas
1. Cable trampa en el pasillo del archivo: los ganchos alimentan el bloque al que están sujetos y este
   activa un dispensador con flechas sobre cada gancho, a la altura del pecho.
2. Placas de presión de piedra en el pasillo de las losas: cada placa activa los dispensadores que tiene
   a cada lado.

## Enemigos
- Generadores: zombi y araña en el archivo, esqueleto en la sala del guardián (zonas sin luz).
- Guardián: esqueleto «Custodio de las Estrellas» (`PersistenceRequired`), 40 de vida, arco con Poder II,
  casco de oro y cota de malla; probabilidad de soltar el equipo baja.
- Sin aldeanos ni gólems: el observatorio está abandonado e infestado.

## Botín (solo vanilla; `solo_sin_lootr` en el grupo extra de cada cofre)
| Tabla | Cofres | Contenido |
|---|---|---|
| `menor` | 7 en superficie | Papel, libros, velas, comida, carbón, cobre, cristal, fragmentos de amatista; a veces brújula, reloj o catalejo |
| `archivo` | 3 en el subsuelo | Libros, mapas, lapislázuli, oro, botellas de experiencia, un libro encantado al azar, etiqueta |
| `oculto` | 2 salas ocultas | Esmeraldas, diamante (1-2), libro encantado (10-20), manzana de oro, catalejo, estandarte del globo |
| `premium` | 1, cámara final | 90 % vistoso: catalejo, reloj y brújula con nombre, casco de hierro con nombre y encantamiento moderado, adornos *wayfinder* y *shaper*, disco *far* o *mall*, estandarte del globo, oro y amatista. 10 %: diamantes, libro encantado 25-30 o peto de diamante encantado 15-25. Sin netherita ni élitros |

## Estado (80-85 % en buen estado)
- Procesador en la pieza de superficie: ladrillo de piedra → agrietado (14 %) o, del resto, musgoso (9 %). En el subsuelo: ladrillo y baldosa de pizarra agrietados y algo de andesita en la roca.
- Ruina diseñada con sentido: paneles de cobre caídos en el sureste de la cúpula (con escombros sobre el
  suelo del telescopio, no colgando), esquina noreste del pretil derrumbada con cascotes en la azotea,
  ventanas rotas en las fachadas oeste y este, tramo del pretil sur caído, telarañas en el subsuelo.
- La auditoría calcula la fracción dañada de la envolvente exterior (bloques visibles desde fuera) y exige
  que quede entre el 15 y el 20 % (resultado: 84,0 % en buen estado sobre 2.976 bloques visibles).

## Contraste con el criterio de Alberto
- Escaleras completas sin saltos; cada puerta con salida; ninguna sala inaccesible (auditoría a pie).
- Muebles contra muro, sin tapar ventanas; centro libre salvo mesas con sillas de respaldo hacia fuera.
- Faroles colgados con cadena hasta el techo; el planetario mecánico cuelga de cadenas; escombros en el suelo.
- Simetría en la fachada, la rotonda y las alas; cada elemento tiene función (telescopio, reloj de sol,
  catalejos, vidrieras de taller, archivo).

## Comprobaciones
- Construcción con `_comun/piezas.py` (puertas, generadores, guardián, trampa de cable y de losas, conexiones),
  botín con `_comun/botin.py`, circuito con `_comun/redstone.py` y recorrido con sótano con `_comun/recorrido.py`.
- `build(reg)` audita la plantilla completa antes de partirla y cualquier aviso detiene la generación: apoyos
  (`lint.support_issues`), recorrido a pie en estado resuelto (puertas, cofres, barriles, palancas, botones,
  escaleras de mano y cada peldaño de los tramos), salas ocultas inalcanzables sin resolver, simulación del
  circuito con `redstone.check_static` y `check_puzzle` (16 combinaciones; estado colocado estable), puerta de pistones,
  nada flotando (todo bloque unido al resto) y estado exterior entre 80 y 85 %.
- `tools/smoke/observatorio_smoke.py`: en un servidor dedicado 26.3 coloca el subsuelo y comprueba reposo, puzle,
  pistones, trampas, cámara del tesoro y guardián, y que `/place structure` coloca también el subsuelo.
- No comprobado: el aspecto en el juego (faltan capturas de Alberto) ni la colocación natural en los biomas.
