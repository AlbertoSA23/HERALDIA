# Isla del corsario (`heraldia:unicas/isla_corsario`)

Un islote en mar abierto con el fuerte de **Roque Salitre**, el corsario de la bandera negra. Recogió a Ysolda del agua
con su bergantín, copió sus cartas y juró no volver a hacerse a la mar mientras guardara su pliego: sigue en su isla,
en la cámara del tesoro bajo el nivel del mar, contando su oro.

Es una estructura original: no recrea ninguna isla, fuerte ni barco de otro juego o mod. Se distingue del **Galeón
varado** (un galeón de tres palos encallado en una playa, con su campamento de náufragos) y del **Faro de los
contrabandistas** (en la costa, con su cueva) en que es una isla entera en mitad del mar, con su roca, su arena y sus
palmeras: un fuerte en el cerro, un puerto con un bergantín de dos palos **a flote**, amarrado al muelle, y las cuevas
marinas bajo el cerro, con una ensenada a la que se entra en barca.

## Bioma y colocación

- Biomas: **océano, océano templado y océano cálido** (los no profundos). Los profundos los busca la Atlántida y en los
  fríos y helados no pega una isla de palmeras. No hay etiqueta convencional tan estrecha (`#c:is_shallow_ocean` incluye
  los fríos y helados), así que queda solo la lista vanilla (`biomas.py`).
- Rareza: `spacing` 250 chunks por defecto (una cada ~3.000-5.000 bloques), configurable como las demás
  (`unicas.isla_corsario.activada`, `unicas.isla_corsario.separacion_bloques`).
- **Candidata en el bioma** (`candidata_en_bioma`, como el Laboratorio del micólogo): la candidata de cada casilla de la
  rejilla es el punto de una malla de 128 bloques más metido en esos océanos (`GridPlacement` con `bioma`, a y = 62).
  Así cae en mar abierto, lejos de la costa, y `/locate`, los mapas y `UniqueSeparation` funcionan igual.
- **Tipo propio `heraldia:isla`** (Java, `unicas/isla/IslaStructure`): el jigsaw no ve el agua. Alrededor del chunk
  candidato (9 puntos cada 16 bloques, de dentro afuera) busca uno cuyo bioma valga en toda la huella y un anillo
  exterior (33 muestras del ruido de biomas, baratas) y cuyo fondo (`OCEAN_FLOOR_WG`, con la caché de `comun/Alturas`)
  quede entre 34 y 7 bloques bajo el nivel del mar en un círculo de 54 bloques (la isla y el bergantín) y bajo el mar
  en el anillo de 78 (agua alrededor: nada de costa cerca). Si nada cumple no se genera. Coloca la plantilla con su
  fila del nivel del mar (la primera capa de aire sobre el agua) a y = 63 y un giro al azar. Con `/place structure`
  (que acepta cualquier bioma) se coloca en el chunk tal cual.
- **Fuera de la Atlántida**: `AtlantisAnchor.excludes` (en `ChunkGeneratorMixin` y `StructureCheckMixin`) ya rechaza
  toda estructura ajena cuyo inicio cae dentro de la zona de la ciudad, y `UniqueSeparation` la separa de las demás
  únicas, la Atlántida incluida. La prueba de servidor lo comprueba con `/locate`.
- **Nada ajeno dentro de la isla** (`unicas/isla/IslaZona`, en los mismos dos mixins, sin mixins nuevos): un naufragio,
  una ruina oceánica o un portal en ruinas cuyo inicio cae a menos de 7 chunks de la candidata de la isla de su casilla
  se rechaza si la isla sale allí de verdad (la misma viabilidad que la distancia mínima entre únicas). Lo caro solo se
  calcula junto a una candidata (unos pocos chunks por casilla) y queda en memoria; para el resto, una búsqueda en una
  tabla y la candidata de la casilla (ya en memoria en `GridPlacement`). Las fortalezas no se excluyen (como en la
  Atlántida). La prueba de servidor busca con `/locate` el naufragio y la ruina oceánica más cercanos a la isla.
- **El islote nunca cuelga**: la plantilla baja hasta 18 bloques bajo el nivel del mar (`BASE`) y su fila inferior se
  prolonga hasta el fondo al colocarse (`heraldia:acueducto_hasta_el_suelo`, 24 bloques como mucho, solo con roca,
  arena, grava, arenisca y los pilotes del muelle). Alrededor de la costa, un talud de arena y grava baja hasta esa fila:
  ni cráter ni costa cortada. El resto de la caja es `structure_void` (el mar se queda donde está).
- Adaptación del terreno `none`; `liquid_settings` `ignore_waterlogging`: el aire de las salas bajo el nivel del mar
  queda seco y el agua que se quiere (la ensenada, el canal, el aljibe) va en la plantilla.

## La superficie (y = 0 es la primera capa sobre el agua)

Coordenadas de diseño: x de oeste a este (0..111), z de norte a sur (0..109). El islote es una superelipse ondulada de
unos 84 × 74 bloques: playa a ras del agua, hierba a un bloque y, al norte y al este, el **cerro** del fuerte (meseta a
y = 7) con acantilados al mar. Palmeras (tronco de jungla inclinado, hojas persistentes, cocos de cacao).

- **Fuerte** (meseta del cerro, 25 × 22): muralla de ladrillo de piedra con almenas y camino de ronda (subidas al oeste y
  al este), puerta doble al sur con el cartel del fuerte, **baluarte** de cinco lados al norte con cuatro **cañones**
  (dispensadores decorativos, vacíos) y el polvorín (cofre `polvorin`). En el patio empedrado: la **casa del corsario**
  (planta baja con la mesa larga, la chimenea, la mesa de cartografía y el cofre `casa`; arriba su alcoba con el cofre
  `corsario`), el **cuartel** (literas, cofre `cuartel`), el aljibe, el mástil de la bandera negra y la **torre de la
  bajada**, con la escalera a las cuevas.
- **Puerto** (explanada del sur, a y = 1): la **taberna de La Sirena Ahorcada** (barra, mesas, chimenea, cofre
  `taberna`), con su bodega bajo el suelo (escala, toneles, cofre `bodega`) y, tras el **tapiz** rojo de la bodega, el
  **escondite** del tabernero (cofre `escondite`); dos **almacenes** (toneles, cofre `almacen`); la **horca** en la
  plaza; la escalinata al fuerte y los caminos (con peldaños donde suben un bloque).
- **Muelle** en T sobre pilotes que llegan al fondo y el **bergantín** amarrado a su cabeza: casco de roble oscuro, dos
  palos con velas cuadras (algunas rasgadas), bauprés, cubierta con escotilla a la **bodega** (cofre `bergantin`),
  castillo de popa con el **camarote del capitán** (cama, mesa, cofre `camarote` y el cartel de la bitácora con la pista
  del puzle) y la toldilla con el timón; la cadena del ancla baja hasta el talud.
- **Faro** de la punta oeste: torre de ladrillo de terracota a franjas sobre un peñón, escala hasta la linterna (linterna
  marina) y el cofre `faro`.

## Las cuevas (pies a y = 1, bajo el cerro)

Todas forradas (ladrillo de piedra o adoquín) donde dan a la roca: ni manantiales ni liquen dentro.

- **Ensenada oculta**: una boca de 3 de ancho en el acantilado norte, al nivel del agua, y un canal que cruza el talud y
  el acantilado hasta una laguna bajo el baluarte, con muelles de piedra al sur y al oeste, la **barca** y el cofre
  `ensenada`. Bajo el agua, un generador de **ahogados**. El agua es de fuentes a ras del mar y todo el aire queda por
  encima: no se inunda (lección del faro).
- **Cuerpo de guardia**: al pie de la bajada del fuerte (7 peldaños); mesa, cofre `guardia` y el cartel con las salidas.
  Al oeste, el pasillo del **cable trampa** (trampa 1: dos dispensadores a la altura de la cabeza).
- **Sala del mapa**: suelo ajedrezado con la **rosa de los vientos**, mesa de cartografía, atril y el cofre `cartas`, que
  guarda el **pliego de la Crónica**. **Puzle de la rosa**: cuatro palancas en el muro norte con sus carteles (Norte,
  Levante, Sur, Poniente); solo **norte y poniente** abren la puerta de pistones del tesoro (`piezas.combo_door`), y
  levante y sur la vuelven a cerrar (polvo directo a la línea, como en el santuario). La pista está en la bitácora del
  camarote del bergantín: «Del puerto al tesoro: norte y poniente; nunca levante ni sur».
- **Armería** (oeste): toneles, cofre `armeria`, mesa de herrería, afiladora y un generador de **esqueletos**. Junto al
  armero, una palanca abre la **santabárbara** (puerta secreta de pistones, `piezas.lever_door`): pólvora, dinamita y el
  cofre `santabarbara`.
- **Calabozos** (sur): pasillo con cinco celdas de barrotes, el cofre `calabozo`, un cartel y un generador de
  **esqueletos**.
- Tras la puerta de la rosa, una bajada de 7 peldaños hasta los pies -6 (bajo el nivel del mar, en seco): la
  **antecámara** con la **trampa de placas** (trampa 2: dispensadores a ras de suelo a los lados) y la **cámara del
  tesoro**: dos cofres `tesoro`, el cofre `premium` entre bloques de oro y **Roque Salitre, el corsario** (esqueleto con
  arco, cota de malla en la cabeza, 60 de vida y 6 de armadura; un esqueleto para que nunca salga «bebé», ver
  aprendizajes).

## Botín (21 cofres)

Modesto en el puerto y el fuerte, mejor en el bergantín y las cuevas, más en las salas ocultas (escondite, santabárbara)
y el cofre premium en la cámara del tesoro (90 % vistoso: sable, catalejo, tricornio y brújula con nombre, lingotes,
adornos de costa y de centinela, discos; 10 % algo más fuerte: tridente, espada de diamante, manzana encantada, tótem o
peto de diamante con encantamientos moderados). Nada de netherita ni élitros. Cada tabla lleva su grupo extra solo sin
Lootr. Objetos con nombre: Ron de la Sirena, Real de plata, Carta de corso, Mecha de cañón, Bitácora del bergantín...

Trofeo del guardián: **Arco de Roque Salitre** (poder 2, irrompibilidad 2, raro). Pliego: cofre `cartas` de la sala del
mapa, entre el del Galeón varado y el del Laboratorio del micólogo.

## Estado y auditoría

- 80-85 % en buen estado: procesador de reglas (ladrillo de piedra agrietado o musgoso, adoquín musgoso, tablas de abeto
  descortezadas, cristales caídos) y ruina a mano (almenas caídas, tejas rotas, velas rasgadas). La auditoría mide la obra
  a la vista sin contar el islote natural ni la vegetación (`recorrido.superficie_danada`): 16 %.
- `auditoria.py` (condición para generar): estado de reposo de la redstone, las 16 combinaciones de la rosa, la
  santabárbara, las dos trampas y que los cañones no tengan señal; recorrido a pie (`lint.walk`) con los puzles cerrados
  y resueltos y recorrido estricto (`recorrido.andar`, sin saltos ni caídas de más de un bloque, nadando en el mar y la
  ensenada) con vuelta a la entrada desde cualquier sitio; salas ocultas solo con los puzles; generadores, palancas y los
  21 cofres al alcance; luz de los generadores (llevan `custom_spawn_rules` hasta luz 11); nada flotando (todo unido a la
  fila inferior); el mar no entra (todo aire bajo el nivel del agua tiene sus 6 vecinas en la plantilla) y el agua de la
  plantilla no se escapa; forro de las cuevas.
- Prueba de servidor: `isla_corsario/prueba_servidor.py` (generación natural con `/locate`, distancia a la Atlántida,
  cámara del tesoro seca, tiempo de `/place`, entidades, mecanismos y trampas).
