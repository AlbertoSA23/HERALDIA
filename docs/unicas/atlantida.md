# Atlántida — Fase 0: análisis y preguntas

Estado: **construida y probada en servidor dedicado**; el aspecto visual está pendiente de capturas del juego de Alberto. Abajo quedan el análisis de la fase 0, las respuestas y, al final, lo construido y lo comprobado.
Id `heraldia:unicas/atlantida`, generador en `tools/gen/unicas/atlantida/`, Java en `io.github.albertosa23.heraldia.unicas.atlantida`.

Cómo se ha comprobado cada cosa:
- **Código**: leído en las fuentes de Minecraft 26.3 que genera Loom (`./gradlew genSources`); se cita clase y método.
- **Servidor**: probado en un servidor dedicado Fabric 26.3 real con el `.jar` del mod (misma base que la prueba de humo).
- **Estimación**: cálculo propio, sin medir. Se indica expresamente.

## 1. Tamaño máximo real

Lo que dice el código:
- `ChunkGenerator.createReferences`: cada chunk busca inicios de estructura en los chunks de **±8** alrededor (`range = 8`), y `ChunkPyramid` exige `STRUCTURE_STARTS` a radio 8. Una pieza que caiga a más de 8 chunks de su chunk de inicio **no se coloca nunca** (ningún chunk la ve), sin error.
- Por tanto, un inicio cubre como mucho **17 × 17 chunks = 272 × 272 bloques**. El jigsaw se queda en 116 de radio (≈ 232-248 de lado). Un tipo propio en Java gana poco por inicio (272 frente a ~240).
- El límite real se supera con **varios inicios**: una colocación propia que marque como chunk de estructura una retícula de chunks alrededor de un ancla (un «distrito» cada 16 chunks = 256 bloques, con el inicio en el centro, de modo que todo queda dentro de ±8). Los distritos encajan sin costuras porque el plano completo se diseña en Python de una vez y se reparte. Con esto **no hay límite horizontal del motor**; el límite es de contenido, tamaño del `.jar` y océano disponible.
- Vertical: el mundo va de y = −64 a 319 (384). Bajo el agua hay de y ≈ 62 (nivel del mar 63) al fondo (océano profundo ≈ y 30-45), y se puede excavar bajo el lecho hasta y ≈ −55. Útil sumergido: **≈ 100-115 bloques de alto**.

Tamaños posibles:

| Opción | Distritos | Huella | Chunks | Referencia |
|---|---|---|---|---|
| A | 1 | ≈ 270 × 270 | ≈ 290 | algo mayor que una ciudad antigua |
| B | 3 × 3 | ≈ 770 × 770 | ≈ 2.300 | ~13 veces el lado de un monumento oceánico (58) |
| C | 5 × 5 | ≈ 1.280 × 1.280 | ≈ 6.400 | necesita un océano de > 1.500 de ancho |

Coste (estimación, sin medir):
- Generación: el coste es por chunk y solo al generarlo. Cada chunk recorre los bloques de las plantillas que lo tocan; con plantillas de hasta 48 × 48 es comparable a una ciudad antigua o unas cámaras de prueba. No hay trabajo por tick.
- Memoria en ejecución: la lista de piezas se guarda en el chunk de inicio de cada distrito (cientos de piezas por distrito, como una aldea grande). Las plantillas se cargan al usarse; no he comprobado si el gestor de plantillas las libera después.
- Tamaño del mod: hoy el `.jar` pesa 4,2 MB con 1.854 plantillas. Con un kit modular (salas y pasillos que se repiten) la opción B debería añadir unos MB; una ciudad sin repetición alguna sería bastante más pesada.
- Mundo: B ocupa ≈ 2.300 chunks si se explora entera (como cualquier zona explorada de ese tamaño).

## 2. Exactamente una por mundo, en un océano grande

Lo que dice el código:
- `ChunkGenerator.findNearestMapStructure` (lo usan `/locate` y los mapas del tesoro) **solo atiende colocaciones `ConcentricRingsStructurePlacement` o `RandomSpreadStructurePlacement`** (`instanceof`). Una colocación propia de otro tipo generaría bien pero `/locate` no la encontraría nunca.
- `RandomSpreadStructurePlacement.getPotentialStructureChunk(seed, x, z)` es público y sobrescribible, y solo recibe la semilla.
- `ChunkGeneratorStructureState.hasBiomesForStructureSet` descarta el conjunto en dimensiones sin sus biomas (Nether y End no tienen océanos).
- `Structure.generate` valida el bioma en el punto de inicio contra `biomes` de la estructura.

Diseño propuesto:
1. Tipo de colocación propio `heraldia:mundial`, **subclase de `RandomSpreadStructurePlacement`**: `isPlacementChunk` devuelve verdadero solo en los chunks de inicio de los distritos; `getPotentialStructureChunk` devuelve siempre el distrito central, así `/locate` y los mapas la encuentran en el primer paso. Sin frecuencia, sin configuración: siempre 1.
2. Búsqueda del ancla, una vez por mundo y fuera del hilo del servidor: se muestrean los biomas en una rejilla (cada 64 bloques) con la fuente de biomas real del mundo (vale también con mods de biomas), se calcula para cada celda de océano la distancia a la costa y se elige la cuenca de **océano profundo** más cercana al 0,0 que cumpla: ancho suficiente para la huella más margen, distancia mínima al origen y **chunks sin generar** (se mira si existen los ficheros de región de la huella; es lo que hace que funcione en un mundo ya existente). Estimación: ~100.000 muestras, del orden de un segundo.
3. La posición elegida se **guarda en los datos del mundo**. Motivo: si cambia el modpack (biomas) o el mapa explorado, un cálculo «sin memoria» podría dar otro sitio y aparecería una segunda Atlántida. Guardada, es exactamente una para siempre.
4. Si no hay cuenca válida cerca: se amplía el radio por anillos (hasta ~12.000 bloques), luego se relajan criterios (océano normal, cuenca más pequeña) y, como último recurso, se toma el mejor océano encontrado y se avisa en el log. Siempre se genera una.
5. Mundo existente: solo aparece en chunks nuevos (por eso el filtro de regiones). `/locate structure heraldia:unicas/atlantida` funciona desde cualquier punto y dimensión con océano.

Sin comprobar todavía (se probará al construir): que el ancla esté calculada antes de que se genere el primer chunk al arrancar (se obtiene la fuente de biomas al cargar el mundo; los hilos de generación esperan al resultado), y `/locate` de punta a punta con la colocación propia.

El generador ya lo permite: `STRUCTURE["placement"]` sustituye a la rejilla configurable (está en `develop`).

## 3. Zonas estancas bajo el agua

Código (`StructureTemplate.placeInWorld`, `JigsawStructure`): por defecto las piezas usan `apply_waterlogging`: todo bloque anegable colocado donde había agua queda **anegado** (y un bloque anegado es una fuente que inunda el aire vecino). Con `liquid_settings: ignore_waterlogging` se respeta el estado de la plantilla.

**Prueba en servidor real** (generación natural, no `/place`): dos estructuras de prueba idénticas en océano profundo, una con cada ajuste: caja de prismarina de 11 × 9 × 11 con sala seca (escalera de mano, escalera, losa, cofre, antorcha, farol), sala inundada contigua separada por una puerta, ventana de panel de cristal, «piscina lunar» en el suelo (agua debajo, aire encima) y hueco al océano. Se localizó con `/locate`, se generó con `forceload` y se leyeron los bloques a los 30 s y a los 2 min:

| Comprobación | `ignore_waterlogging` | `apply_waterlogging` |
|---|---|---|
| Celdas de aire que siguen secas (2 min) | **7 de 7** | 4 de 7 (inundada) |
| Muebles anegables secos | todos | el farol quedó anegado e inundó la sala |
| Puerta cerrada entre sala inundada y sala seca | aguanta | aguanta |
| Piscina lunar (agua bajo aire) | el agua no sube | — |
| Sala inundada y escalera anegada de la plantilla | con agua | con agua |
| Tras romper un bloque del techo (60 s) | 3 de 7 celdas con agua | más agua |

Conclusiones:
- El aire colocado **se mantiene seco** con `ignore_waterlogging`, muros de bloque completo y agua explícita en la plantilla donde se quiera agua. Las piezas inundadas llevan su agua y sus bloques `waterlogged=true` en la plantilla.
- **No hacen falta esclusas mecánicas.** Las transiciones agua/aire se resuelven con piscinas lunares (subir desde el agua a una sala seca), puertas (no son anegables: retienen el agua) y sifones. Son además el recurso natural para puzles.
- Romper un muro exterior **inunda la sala** (comportamiento vanilla, no evitable sin mixins). Mitigación de diseño: doble muro en salas clave y fatiga minera del guardián anciano (ver 4).
- Matices de la prueba: la caja quedó parcialmente encajada en el lecho; el techo sí estaba bajo agua (por eso inundó al romperlo), pero no garantizo que la ventana diera a agua abierta. La puerta y la piscina lunar sí estaban contra agua de la plantilla. Los bloques sin soporte y la arena o grava sobre huecos se vigilarán en la auditoría.

## 4. Mobs defensores

Código:
- `Guardian.checkGuardianSpawnRules`: aparece en agua con agua debajo; con generador vale aunque el bloque no sea agua. `Drowned.checkDrownedSpawnRules`: con generador siempre válido. Los generadores vanilla funcionan bajo el agua para ambos.
- `ElderGuardian`: cada 60 s aplica **fatiga minera III durante 5 min a los jugadores en 50 bloques** y se queda en un radio de 16 de su sitio.
- `spawn_overrides` de la estructura (como el monumento): aparición natural de guardianes dentro de la caja, **limitada por el tope de mobs del servidor**, así que no puede colapsarlo; a cambio reaparecen (y son granjeables, igual que en un monumento).

Propuesta (para la opción B; se escala con el tamaño):
- Aparición natural de guardianes en las zonas inundadas (`spawn_overrides`), sin coste fijo.
- **40-60 generadores** en grupos (guardianes en salas inundadas, ahogados en pasillos y salas secas), solo activos con un jugador a 16 bloques.
- **80-120 defensores colocados** con nombre y persistentes: ahogados con tridente (en vanilla solo el 6 % lo lleva), algunos con armadura; guardianes en puntos de paso. Solo existen en chunks cargados.
- **3-5 guardianes ancianos** en los distritos clave (no en toda la ciudad: cubrirla entera pediría ~40).
- **Guardián final**: jefe con nombre en la antesala de la cámara del tesoro (guardián anciano reforzado por atributos, escoltado por ahogados de élite con tridente). Todo con NBT vanilla.

Sin comprobar: generadores de prueba (`trial_spawner`) con mobs acuáticos; se probará antes de decidir si se usan en vez de los clásicos.

## 5. Botín

Comprobado contra los registros de 26.3: existen `trident`, `conduit`, `heart_of_the_sea`, `nautilus_shell`, `diamond_nautilus_armor`, `diamond_spear`, `turtle_helmet`, `tide_armor_trim_smithing_template`, `vault`, y los encantamientos usados.

Cofre premium (propuesta):
- **Tridente «de Poseidón»**: Lealtad III, Canalización, Empalamiento V, Irrompible III, Reparación.
- **Tridente «de las Mareas»**: Propulsión acuática III, Empalamiento V, Irrompible III, Reparación.
- A su altura: conducto ya fabricado, 2-3 corazones del mar, 2 manzanas doradas encantadas, tótem de la inmortalidad, casco de tortuga con Respiración III + Afinidad acuática + Protección IV, botas de diamante con Agilidad acuática III, armadura de nautilo de diamante, lanza de diamante encantada, plantillas de adorno Marea, disco y esponjas.
- **Sin netherita ni élitros.** Tampoco maza ni núcleo pesado (propuesta).

¿Rompe la progresión? Los tridentes no se fabrican (8,5 % de los ahogados que lo llevan) y esos encantamientos se consiguen con yunque: el cofre **ahorra una granja larga, no da nada inalcanzable**. Lo más fuerte es el tótem y las manzanas, ambos ya obtenibles. Es más alto que el resto de estructuras únicas, como se pidió.

Cofres menores: botín avanzado de tema marino (diamantes, esmeraldas, libros de Respiración/Agilidad acuática/Afinidad, conchas de nautilo, pociones de respiración, prismarina, algún tridente sin encantar muy raro), con el extra de cada cofre marcado `solo_sin_lootr`.

Lootr y el cofre «único»: Lootr convierte los cofres con tabla de botín en cofres por jugador. Un cofre con **contenido fijo** (sin tabla) no se convierte: es único de verdad. Ver pregunta 3.

## 6. Resumen de riesgos

- La colocación mundial y la estructura por distritos son Java propio (colocación, tipo de estructura y búsqueda de océano): es la parte con más riesgo y la primera que se construirá y probará.
- Sin capturas del juego de Alberto el aspecto no se da por bueno.
- La prueba de humo habrá que ampliarla: `/locate`, generación natural de al menos un distrito y comprobación de salas secas.

## Preguntas para Alberto

1. **Tamaño.** A (≈ 270 × 270), **B (≈ 770 × 770, recomendada)** o C (≈ 1.280 × 1.280). B es enorme, cabe en la mayoría de océanos grandes y se puede llenar de contenido con calidad; C obliga a mucho relleno repetido y a veces no habrá océano donde quepa.
2. **Visibilidad.** ¿Totalmente sumergida (**recomendado**: techo bajo el agua, solo se intuye de noche por el resplandor de las cúpulas; se llega con `/locate` o mapa) o con una aguja o faro que asome sobre el mar como hito?
3. **Cofre premium y Lootr.** (a) **Cofre de contenido fijo, único de verdad: el primer grupo que llegue se lo lleva (recomendado, es lo que pediste)**; (b) tabla de botín: con Lootr cada jugador recibiría sus 2 tridentes; (c) cámara acorazada vanilla (`vault`) con llave escondida: cada jugador la abre una vez.
4. **Muros y fatiga minera.** Romper un muro inunda la sala y no se puede impedir en vanilla. ¿Vale con **guardianes ancianos en los distritos clave** (fatiga minera: allí no se puede picar, hay que resolver los puzles) y aceptar que en el resto se pueda picar e inundar (**recomendado**), o prefieres ancianos por toda la ciudad?
5. **Botín legendario.** ¿Conforme con la lista del punto 5 (tridentes al máximo, conducto, tótem, manzanas encantadas, equipo de diamante acuático; **sin netherita, élitros ni maza**)? Di si quieres quitar o añadir algo.
6. **Ubicación.** Recomiendo: a **1.500 bloques o más del 0,0**, en la cuenca de océano profundo válida más cercana (puede quedar lejos, hasta ~12.000 bloques si la semilla no tiene océanos grandes cerca), solo en zona sin explorar, y **guardando la posición en los datos del mundo** para garantizar que nunca haya dos. ¿De acuerdo con esas tres cosas?

## Respuestas (14-11-2026, transmitidas por el orquestador y confirmadas por Alberto en la sesión)

1. Tamaño **B**, ≈ 770 × 770 (3 × 3 distritos). 2. **Totalmente sumergida.** 3. Cofre premium de **contenido fijo y único**.
4. Guardianes ancianos **solo en distritos clave**. 5. Botín legendario: la lista del punto 5 **tal cual**.
6. Ubicación: a ≥ 1.500 bloques del 0,0, cuenca válida más cercana en zona sin explorar, posición **guardada en los datos del mundo**.

## Lo construido

Planos y renders en `docs/unicas/atlantida/` (se regeneran con `cd tools/gen && python3 -m unicas.atlantida.planos ../../docs/unicas/atlantida`).
En los planos: azul = agua, amarillo = aire (zona seca), verdes = prismarina, gris = zócalo de piedra.

### Cómo se genera
- **Colocación `heraldia:mundial`** (Java, hereda de `random_spread`): son chunks de estructura los nueve inicios de distrito (ancla ± 16 chunks). `/locate` y los mapas reciben siempre el distrito central.
- **Ancla** (`AtlantisAnchor`): al cargar el Overworld, en un hilo propio, se muestrean los biomas cada 64 bloques en ±12.288 y se elige el centro más cercano al 0,0, a 1.500 bloques o más, por niveles: todo océano en ±448 con el centro profundo y sin explorar; todo océano sin explorar; casi todo océano sin explorar; casi todo océano; el que más océano tenga. Se guarda en `data/heraldia/atlantida.json` del mundo. «Sin explorar» = no existe ningún fichero de región bajo la huella.
- **Estructura `heraldia:atlantida`**: cada distrito coloca primero la **pieza base** (por columnas, sin plantillas: agua sobre el suelo hasta y = 62, pavimento con las avenidas en cruz, zócalo de piedra hasta el lecho, muralla circular de radio 372 con cuatro puertas y un 18 % de tramos derruidos) y después las **teselas** de 32 × 32 que le tocan. Sin comprobación de bioma: siempre sale entera.
- **Plano** (`tools/gen/unicas/atlantida/`): la ciudad se construye en un único mapa de vóxeles (731.000 bloques, 104 entidades) y se corta en 391 teselas alineadas con los distritos, así ninguna pieza cruza un límite. `liquid_settings` es siempre `ignore_waterlogging`; cada bloque anegable se marca según su entorno (anegado si toca agua y no toca aire).
- **Otras estructuras**: los dos mixins que ya tenía el mod rechazan cualquier otra estructura cuyo inicio caiga a menos de 444 bloques del centro (en la primera prueba nació un monumento oceánico vanilla dentro de la ciudad).

### Niveles (y absoluta)
| Nivel | y | Contenido |
|---|---|---|
| N1 | 37-58 | plantas altas secas, cúpulas, torres, templo (su cúpula llega a y = 58) |
| N0 | 31-36 | pavimento (y = 31), calles y plazas inundadas, plantas bajas |
| N−1 | 13-20 | vestíbulo seco bajo el templo y galerías: cuatro radiales bajo las avenidas y un anillo cuadrado de 312 de lado, en tramos alternos secos e inundados de 24 bloques separados por puertas |
| N−2 | −14-5 | escalera seca, antecámara, sala del guardián final (inundada, 33 × 33 × 12), tesoro (seco) y cripta oculta del cofre premium |

### Trazado
- Centro: **acrópolis** (basamento de tres gradas de radio 62, columnata de 24 columnas, cella con cúpula de cristal y pozo de cristal que baja al vestíbulo).
- Ocho distritos singulares, uno por rumbo: **N ágora** (plaza porticada, estatuas del tridente, casa del consejo seca con los carteles que explican los sellos, mercado en ruinas), **NE lonja de artesanos** (seca, con sótano oculto bajo una trampilla tapada), **E termas** (frigidario inundado con cúpula, tepidario seco, caldario con suelo de magma y ascensor de burbujas a una galería seca), **SE arsenal** (recinto con torres, patio inundado, torre del homenaje seca con pasillo de trampas, armería, cofre bomba y cámara del sello tras una palanca escondida bajo un tapiz), **S puerto hundido** (muelles rotos, cuatro pecios), **SO jardines de coral** (cinco cúpulas rotas y un invernadero seco intacto), **O academia** (dos alas secas de biblioteca; cámara del sello tras una puerta de combinación cuyas cuatro pistas están repartidas por las alas), **NO anfiteatro** (graderío, arena con seis generadores bajo rejas y el cofre del sello).
- Entre ellos, **372 solares** en retícula de 24 bloques, simétrica respecto a los dos ejes: 204 casas secas (planta baja seca con puerta, o planta alta seca a la que se sube buceando por una piscina lunar), 29 casas inundadas, 46 torres con sala alta seca, 51 templetes y 42 ruinas.
- Estado: **19,3 % de la superficie construida en ruinas** (auditado entre 15 y 20), concentrado hacia el puerto y los jardines.

### Progresión, puzles y trampas
1. Tres **sellos** (arsenal, academia, anfiteatro): cada cofre da una llave con nombre y hay un cartel con una cifra; la cuarta cifra está en la galería alta de las termas.
2. En la cella del templo se baja por el pozo al **vestíbulo**: las tres llaves abren tres **arcas** cerradas (`lock`) con botín para el combate, y las cuatro cifras son la posición de las **cuatro palancas** que abren la puerta de hierro hacia N−2.
3. **Guardián de Poseidón** (guardián anciano con 240 de vida, escala 1,5 y cuatro hoplitas ahogados): al morir suelta la **Llave de Poseidón**.
4. Tras su sala está el tesoro; en la esquina, una trampilla bajo una alfombra baja a la cripta del **cofre premium**, cerrado con esa llave.
- Mecanismos: dos puertas de combinación (antorchas inversoras y línea común de «algo está mal»), puerta por palanca oculta, dispensadores de flechas y de agua junto a placas de presión (en el arsenal y en las galerías secas), cofre trampa sobre TNT, columnas de burbujas de magma (arrastran) y de arena de almas (suben).
- Salas ocultas: sótano de la lonja y cripta del premium (las dos por trampilla tapada: no hay que romper nada).

### Defensores
- Aparición natural de guardianes en toda la caja (`spawn_overrides`, limitada por el tope del servidor).
- Colocados y persistentes: 62 vigías (guardianes), 33 ahogados con tridente (los «hoplitas», con 40 de vida y armadura), 3 guardianes ancianos (arsenal, anfiteatro, templo) y el guardián final.
- 48 generadores (ahogados en zonas secas y casas inundadas, guardianes en zonas inundadas).

### Botín
- 185 cofres y barriles. Tablas `menor`, `media`, `tesoro`, `arca` y `sello_*`, todas con un grupo extra `solo_sin_lootr`.
- **Cofre premium, contenido fijo (no lleva tabla: Lootr no puede convertirlo)**: Tridente de Poseidón (Lealtad III, Canalización, Empalamiento V, Irrompible III, Reparación), Tridente de las Mareas (Propulsión acuática III, Empalamiento V, Irrompible III, Reparación), conducto, 3 corazones del mar, 2 manzanas doradas encantadas, tótem, Yelmo de las Profundidades (tortuga), Botas de la Corriente (diamante), Lanza de Tritón (diamante), armadura de nautilo de diamante, 2 plantillas Marea, disco, 8 esponjas, 16 conchas de nautilo, 12 diamantes, 4 bloques de esmeralda, 8 de oro y 32 frascos de experiencia. Sin netherita, élitros ni maza. Con la opción `unicas.atlantida.cofre_unico_por_jugador` (por defecto `false`) cada jugador abre su propia copia (`loot/CofrePorJugador.java`; el cofre lleva la marca `custom_data` `heraldia_cofre_unico`).

### Auditoría (condición para generar; `auditoria.py`, unos 15 s)
- **Estanqueidad**: ninguna celda de aire, ni de bloque que el agua arranca (redstone, palancas, placas, alfombras), toca agua o un bloque anegado por los lados o por arriba, ni terreno natural.
- **Apoyos**: escaleras de mano, carteles, tapices, palancas y antorchas con pared detrás; puertas, polvo, placas y camas sobre macizo; arena y grava con suelo; algas con base; columnas de burbujas con su bloque.
- **Alcanzabilidad**: recorrido desde el mar abierto nadando, andando, saltando un bloque, por escaleras de mano, puertas y trampillas, sin romper nada: llegan a todas las celdas secas marcadas, los 185 cofres, los generadores, las dos salas ocultas, el guardián final y el premium.
- Objetos de los cofres fijos válidos y porcentaje de ruina entre 15 y 20.
- La auditoría genérica de `lint.py` no se aplica a las teselas (verían medio edificio): por eso el plano se audita entero.

## Qué se ha comprobado y cómo

En un servidor dedicado Fabric 26.3 real, con el `.jar` compilado y un mundo nuevo (semilla `heraldia`):
- Ancla calculada en unos 2 s; al reiniciar se lee la guardada. `/locate structure heraldia:unicas/atlantida` devuelve el ancla.
- **Ciudad entera generada por worldgen** (los 9 distritos, unos 2.300 chunks forzados a la vez) en 56 s; el servidor avisa de retraso mientras tanto, como con cualquier generación masiva.
- **Las 364 celdas secas marcadas siguen siendo aire y las 154 de piscina lunar siguen siendo agua** un minuto después de generarse.
- **Las dos puertas de combinación** (academia y vestíbulo) solo se abren con la combinación correcta y se cierran al estropearla; la puerta del arsenal se abre con su palanca.
- Cofre premium: contenido y cerradura leídos con `data get`. Guardián final presente; al matarlo aparece la llave con su dato.
- Con la exclusión, dentro de la ciudad hay exactamente los 4 guardianes ancianos del plano (antes, 7: tres eran de un monumento vanilla).
- La prueba de humo oficial repite lo esencial en el distrito central (`tools/gen/unicas/atlantida/humo.py`).

No comprobado:
- **Nada se ha visto dentro del juego**: aspecto, escala, iluminación y jugabilidad necesitan capturas y una partida de Alberto.
- Las cerraduras y los mecanismos no se han accionado con un jugador: las cerraduras se han leído como datos y las palancas se han movido con `setblock` «tocando» después los bloques contiguos (lo que hace el juego al accionarlas). Trampas de flechas, de agua y de TNT, ascensor de burbujas y generadores: generados y auditados, no disparados.
- Lootr: no se ha probado con el mod instalado que deje intacto el cofre de contenido fijo.
- Cofre por jugador (`unicas.atlantida.cofre_unico_por_jugador`): la lógica se ha probado con dos y tres jugadores simulados (`CofrePorJugadorTest`) y la marca del cofre en el servidor (prueba de humo), pero no se ha abierto con jugadores reales ni con Lootr instalado.
- Mundo ya existente: el filtro de regiones exploradas está escrito pero solo se ha probado en mundo nuevo. Tampoco se han probado semillas sin océanos grandes (niveles 1 a 4 de la búsqueda) ni mods de biomas.
- En la prueba aparecen algas sueltas flotando (unas 170 en toda la zona, también fuera de la ciudad); no he determinado si son del juego o del corte de la pieza base en el borde.
- Rendimiento con jugadores reales y memoria con toda la ciudad cargada: sin medir.

## Cambios respecto a la propuesta
- Los distritos no son las nueve casillas de 256 × 256 (las de las esquinas quedan casi fuera del círculo): son ocho sectores por rumbos alrededor de la acrópolis. Las nueve casillas siguen siendo los inicios de estructura.
- Las galerías no enlazan con sótanos de cada distrito: se entra por nueve pozos con templete (ocho nudos del anillo y el del templo).
- No se audita la longitud máxima de buceo sin aire: la ciudad está pensada para ir con respiración acuática o usando las casas secas como refugio.
