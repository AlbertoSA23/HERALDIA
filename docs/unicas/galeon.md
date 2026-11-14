# Galeón varado (`heraldia:unicas/galeon`)

Un galeón de tres palos (62 bloques de eslora, 17 de manga, palo mayor de 40 m sobre la quilla) encallado de costado en la
orilla, con la banda de tierra reventada por la varada, el campamento de los náufragos en la arena y, detrás, un peñón con
la cueva donde escondieron el tesoro del capitán. Una sola variante, diseñada a mano (`tools/gen/unicas/galeon/`).

Diferencias con el naufragio vanilla: diez veces su volumen; cuatro cubiertas habitables con 16 estancias amuebladas;
campamento y cueva; puzles, trampas, generadores y guardián; botín repartido por 18 cofres y 3 bloques de arqueología.

## Situación en la orilla (Java)

El jigsaw no ve el agua, así que la estructura usa un tipo propio, `heraldia:galeon`
(`io.github.albertosa23.heraldia.unicas.galeon`), que reutiliza `JigsawPlacement` para la pieza y decide antes el sitio y el giro:

1. Descarte barato: si ningún punto de una rejilla de 16 bloques (radio 64) cae en una playa, no hay galeón.
2. Rejilla de candidatos cada 8 bloques (radio 56) x 4 giros. Para cada uno se miden las **sondas** que escribe el generador
   en el JSON (posiciones de la plantilla, todas múltiplos de 8): la altura del fondo (`OCEAN_FLOOR_WG`) respecto al nivel
   del mar debe caer en un intervalo. Banda de mar del casco: agua de 2 a 9 de fondo; mar abierto: agua; banda de tierra del
   casco, campamento y peñón: tierra entre el nivel del mar y +4 (+12 en el peñón). Las del casco son obligatorias; del resto se
   admiten 3 fallos. Gana el candidato con menos fallos y terreno más llano. Las alturas se cachean por columna.
3. Se llama a `JigsawPlacement.addPieces` con `maxDepth` 1 (con 0 no añade ni la pieza central). El giro de `JigsawPlacement` es la primera tirada de `context.random()`. Se le pasa un `GenerationContext` copia con un
   `WorldgenRandom` sembrado de forma determinista cuya primera tirada da el giro elegido: el resultado no depende de que el
   juego cambie su semilla interna.
4. La pieza se coloca sin proyección: el ancla de la plantilla (línea de flotación en crujía) queda a `seaLevel`. El bioma se
   valida en el ancla (playa o playa nevada) y no en el centro de la caja, que cae bajo tierra.
5. `/place structure` (predicado de bioma que acepta cualquiera): si no hay orilla, se coloca igualmente en el centro del chunk
   para poder probarla.

Adaptación al terreno: `none`. Cada parte trae su propio asiento: lecho de arena con base de arenisca bajo el casco, suelo de
arena de 4 de grosor y volumen de aire de 6 sobre el campamento (rebaja dunas), y una coraza de roca de 2 bloques alrededor de
todo hueco de la cueva. Así no hay `beard` que hunda el terreno sobre los sótanos. Agua: todo aire bajo el nivel del mar está
rodeado por bloques de la plantilla (comprobado), de modo que el mar no entra por ningún hueco. Se usa
`IGNORE_WATERLOGGING`: los cofres y escaleras de la bodega no quedan anegados.

Bioma: `#minecraft:is_beach` (playa y playa nevada). No toca costa rocosa (`stony_shore`), que queda libre para el faro.

## Plantas por nivel (y = altura de los pies; 0 = nivel del mar)

Ejes de la plantilla: X de tierra (0) a mar; Z de proa (norte) a popa. Crujía del barco en X = 64.

| Nivel | Estancias (de proa a popa) |
|---|---|
| Bodega (-4) | bodega de proa (generador de ahogados, cofre) · bodega mayor con la arena entrando por la brecha, carga estibada y **pañol oculto** tras un laberinto de barriles (cofre) · pañol de pólvora (barril) · **santabárbara** (cofre con trampa de TNT) |
| Cubierta de cañones (1) | pañol del contramaestre (barril) · batería de 10 cañones, rancho y la **brecha** por donde se entra desde la playa · enfermería del cirujano (cofre, alambique) |
| Cubierta principal (5) | castillo de proa: cocina (barril) y coyes · combés con escotillas, cabrestante y el mastelero caído · castillo de popa: **cámara de oficiales** (mesa, cofre) |
| Castillo de proa (9) | cubierta con la campana y el bauprés |
| Alcázar (10) | antecámara · **camarote del capitán** (cofre, mesa de cartas, atril) · **cámara del tesorero** tras una estantería falsa (cofre) |
| Toldilla (15) | tres faroles de popa |
| Cofa (23) | cofa del palo mayor (cofre), por escala de mano |
| Playa (1) | campamento: tiendas de vela, hoguera apagada, choza del vigía (cofre), tumbas, bote, 3 bloques de arena sospechosa |
| Cueva (1 a -7) | boca en el peñón · galería en bajada con **trampa de cable** · cueva de los huesos (generador de esqueletos) con **nicho oculto** tras telarañas (cofre) · antecámara del **puzle de los faroles** · **cámara del tesoro** (cofre premium y guardián) |

Planos con las celdas alcanzables a pie: `docs/unicas/galeon/plantas.txt`. Renders: `docs/unicas/galeon/*.png`.

## Recorrido del jugador

Playa → campamento (cofres modestos, arqueología) → la brecha lleva a la cubierta de cañones → escaleras a la bodega
(generadores, pañol oculto, santabárbara) y a la cubierta principal → castillos, alcázar, camarote y cámara secreta →
cofa. Desde el campamento, la cueva: galería con trampa, cueva de los huesos, puzle y cámara del tesoro con el capitán.

## Puzles y trampas (sin polvo de redstone; todo en estado estable al colocarse)

- **Estantería falsa** (camarote → cámara del tesorero): dos pistones pegajosos extendidos en la esquina oculta del mamparo
  sujetan dos estanterías. Los alimenta una antorcha de redstone en una cavidad cerrada (inversor). Una palanca en la esquina
  del camarote apaga la antorcha: los pistones retiran las estanterías y se abre el paso.
- **Puzle de los faroles** (cueva): tres palancas bajo lana roja (babor), verde (estribor) y blanca (popa) y un cartel:
  «Babor encendido, estribor apagado; el de popa, nunca». La roja abre la primera puerta de hierro; la verde (encendida al
  llegar) apaga una antorcha que abre la segunda; la blanca dispara una flecha desde un dispensador.
- **Santabárbara**: placa de presión ante el cofre con 4 TNT bajo el suelo (como el templo del desierto).
- **Cable trampa** en la galería de la cueva: dos ganchos y dos dispensadores con flechas a la altura de la cabeza.

El generador comprueba con el simulador común (`unicas/_comun/redstone.py`) que el estado colocado es estable y que cada acción
produce su efecto (pistones retraídos, puertas abiertas, dispensadores y TNT activados). Si falla, no se genera nada.

## Enemigos

- Generadores: 2 de ahogados en la bodega (reglas de luz propias, bloque y cielo 0-7, para que funcionen fuera del agua),
  1 de esqueletos en la cueva de los huesos, 1 de zombis en la galería.
- Guardián: **El capitán ahogado** (ahogado, 50 de vida, 4 de armadura, sable de hierro, casco de oro, caracola de nautilo
  que suelta siempre; persistente) en la cámara del tesoro.

Sin aldeanos ni gólems: el campamento está abandonado (las tumbas cuentan qué pasó) y los generadores los matarían.

## Estado (80-85 % en buen estado)

Ruina a mano: la brecha del costado de tierra (casco y cañones arrancados, arena en la bodega), mastelero de trinquete
partido y caído, velas rasgadas, tramos de barandilla rotos, cristales de popa rotos, percebes (coral muerto) en el casco.
Procesador: 10 % de las tablas exteriores del casco desaparecen; 20 % del adoquín de la cueva se cubre de musgo. La auditoría
calcula el porcentaje de superficie dañada y exige 15-20 % (resultado actual: 15,3 %: 337 celdas a mano —brecha, tracas arrancadas, velas rasgadas, tablas partidas, percebes— más el 10 % esperado del procesador sobre 953 tablas, de 2.833 celdas de superficie).

## Botín (solo vanilla; extra por cofre marcado `solo_sin_lootr`)

| Tabla | Dónde | Contenido |
|---|---|---|
| `nafrago` | campamento (3) | comida de playa, cuerda, palos, carbón, caña gastada |
| `arena` | arena sospechosa (3) | fragmentos de cerámica (pescador, refugio, hocico), pepitas, esmeralda |
| `bodega`, `cocina` | bodega y cocina | víveres, trigo, azúcar, botellas, papel |
| `polvora` | pañol de pólvora | pólvora, pedernal, carga ígnea, 1-2 TNT |
| `cirujano` | enfermería | papel, botellas, pociones de curación y regeneración |
| `oficiales` | cámara de oficiales | esmeraldas, oro, libros, brújula, mapa, reloj |
| `cofa` | cofa | catalejo, mapa, plumas, cuerda |
| `santabarbara` | santabárbara | pólvora, hierro, flechas, ballesta, esmeraldas |
| `capitan` | camarote | esmeraldas, oro, catalejo, libro encantado (bajo), etiqueta |
| `contrabando`, `cueva` | salas ocultas | oro, esmeraldas, diamante (raro), manzana dorada, libro encantado |
| `tesorero` | cámara secreta | más oro y esmeraldas, 1-2 diamantes, manzana dorada, adorno de costa |
| `premium` | cámara del tesoro | 90 %: objetos con nombre (sable, catalejo, brújula, casco), encantamientos moderados, adornos de costa y de marea, discos; 10 %: tridente con nombre, corazón del mar o manzana de oro encantada |

Nada de netherita ni élitros. Cuanto más escondido, más rico: playa < cubiertas < camarote < salas ocultas < tesoro.

## Contraste con el criterio de diseño

- Escaleras: todas las cubiertas se unen con tramos completos (o escala de mano a la cofa); la auditoría recorre a pie desde la
  entrada y exige alcanzar cada puerta, cofre, barril, atril, horno y campana.
- Simetría: tramos de escalera dobles a babor y estribor en ambos castillos, batería simétrica (salvo la brecha), faroles de popa.
- Muebles contra los mamparos; mesas con sillas de respaldo hacia fuera; faroles colgados de vigas.
- Nada flotando: la auditoría exige que todo bloque esté unido al suelo y que la arena tenga apoyo.

## Qué se ha comprobado

- Generación con auditoría (`lint.py` + `auditoria.py` del módulo) sin avisos; el simulador detecta una antorcha o palanca mal colocada (prueba de mutación hecha a mano).
- Prueba de humo en servidor dedicado 26.3: se registra, `/place` la coloca y las 14 tablas de botín se abren.
- `tools/smoke/galeon_test.py` en servidor dedicado: `/locate` encuentra un galeón natural (búsqueda de orilla en 0,5 s), `/place` lo
  coloca en ese sitio con el mar a 20 bloques hacia fuera y arena a 24 hacia tierra, y están el capitán ahogado y el bote.
- Sin comprobar: el aspecto en el juego (falta captura de Alberto), que los ahogados de los generadores aparezcan fuera del agua y el
  comportamiento de los circuitos en el juego (solo simulados).
