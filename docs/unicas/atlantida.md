# Atlántida — Fase 0: análisis y preguntas

Estado: **análisis terminado, nada construido**. Pendiente de las respuestas de Alberto (al final).
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

Cambio genérico necesario en el generador: `writer.write_unique` fija hoy la colocación `random_spread`; hay que permitir que el módulo aporte la suya (cambio pequeño, compatible).

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
