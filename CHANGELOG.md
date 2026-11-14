# Registro de cambios

Formato: cada versión es `## [X.Y.Z]` (con ` - AAAA-MM-DD` al publicarla) y lleva dos apartados:
`### Jugadores` (lo que nota quien juega) y `### Técnico` (cambios internos). La versión de arriba
coincide con `mod_version` de `gradle.properties`; `tools/changelog.py` lo comprueba y extrae las notas de publicación.

## [0.1.0]

### Jugadores

- Nueva estructura única: el Coliseo en ruinas, en sabanas y mesetas de sabana. Anfiteatro elíptico con galerías, graderíos, palco imperial y palco del editor; bajo la arena, un hipogeo con montacargas, celdas de fieras, barracones y armería, y una parte oculta (despacho del lanista, pasadizo de Cómodo y cámara del tesoro) a la que se llega resolviendo uno de sus dos puzles. Trampas de flechas, generadores de monstruos y el Campeón de la Arena guardando el cofre premium.
- Primera versión del mod: 72 aldeas enormes (36 estilos por bioma, cada uno en tamaño estándar y grande) que aparecen en chunks nuevos del Overworld, una cada 1000-2000 bloques.
- Comandos de prueba `/function heraldia:muestrario` y `/function heraldia:familia/<familia>` para ver los estilos colocados en fila; sus mensajes salen en español o inglés según el idioma del cliente.
- Mapas del tesoro hacia cada estructura única: en el 5 % de los cofres épicos de las aldeas y a la venta en los cartógrafos maestros de las aldeas Heraldia (24 esmeraldas y una brújula); con nombre en español o inglés.

- Fichero de configuración `config/heraldia.json`: separación entre aldeas (1000-10000 bloques, por defecto 1500), máximo de aldeas por mundo (hasta 100, las más cercanas al 0,0), porcentaje de grandes, distancia a las aldeas vanilla, familias y estilos activables, límites y limpieza de gólems, y activación y separación de cada estructura única. Los valores no válidos se avisan en el log y se cambian por los de por defecto.
- Nueva estructura única: la **Fortaleza de hielo**, en picos de hielo, llanuras nevadas y taigas nevadas. Murallas, torres afiladas, gran salón con trono de hielo, barracones, cocinas, perrera con lobos de las nieves, galería de esculturas de hielo, criptas con generadores de strays y esqueletos, el guardián Rey Escarcha y una cámara del tesoro tras una puerta secreta. Dos puzles de palanca y pistones, trampas de cable y de placa, y botín creciente hasta el cofre final.
- Estructura única **Ciudadela enana** (picos pedregosos y dentados): ciudad excavada en la montaña con la gran puerta en la ladera; salón de columnas, barracones, almacén, salón del trono, forjas con lava contenida, cervecería, minas con vías y vagonetas, puente sobre un abismo de lava y bóveda del tesoro. Cuatro salas ocultas, puerta secreta de pistones con palanca señuelo, cerradura de cuatro palancas, trampas de TNT y de flechas, tres generadores y un guardián con nombre (Borin Barbahierro).

### Técnico

- Coliseo (`tools/gen/unicas/coliseo/`): dos piezas (principal a ras de suelo y un hipogeo hijo que rellena toda su caja, unido por un jigsaw vertical), 11 cofres con tablas propias y grupo `solo_sin_lootr`, procesadores de meteorización. Auditoría propia como condición para generar (recorrido sin saltos con vuelta a la entrada, puzles abiertos y cerrados, nada flotando, luz 0 en los generadores, redstone coherente, 15-20 % de ruina), planos y renders en `docs/unicas/coliseo/` y prueba en servidor real de puzles y trampas (`tools/smoke/coliseo_redstone.py`).
- `writer.py`: se quita la segunda mezcla duplicada de los textos `LANG` de las estructuras únicas, que había entrado por dos PR paralelos.
- Proyecto Fabric para Minecraft 26.3 (Loom 1.19-SNAPSHOT, Loader 0.20.1, Fabric API 0.166.2+26.3, Java 25), id `heraldia`.
- El generador del datapack "Aldeas enormes" pasa a `tools/gen/` y escribe sus recursos en el `.jar` durante la compilación; namespace `aldeas` cambiado a `heraldia` en estructuras, pools, botín, funciones y etiquetas.
- La ruta de los registros de 26.3 para validar es configurable (`--registries`, `MCMETA_SUMMARY` o `-Pmcmeta_summary`); por defecto se clona `misode/mcmeta` rama `26.3-summary` en `build/` y no se sube al repositorio.
- La validación comprueba sobre los JSON escritos el límite `max_distance_from_center` + 12 <= 128 y `size` <= 20.
- Al arrancar el servidor, el log indica cuántas estructuras `heraldia` hay registradas.
- Comprobaciones locales: `tools/changelog.py check` valida este registro y `tools/smoke/server_smoke.py` arranca un servidor dedicado 26.3 real con el mod como prueba de humo.
- Sin licencia: todos los derechos reservados.
- Base para estructuras únicas: el generador descubre los módulos de `tools/gen/unicas/` y escribe su estructura, su rejilla de colocación, su etiqueta (para mapas) y su botín bajo `heraldia:unicas/<id>`.
- Condición de botín `heraldia:sin_lootr`: los grupos marcados `solo_sin_lootr` se omiten si Lootr está cargado.
- La prueba de humo coloca también cada estructura única y abre todas las tablas de botín.
- `tools/gen/mapas.py`: por cada estructura única escribe `item_modifier` y `loot_table` `heraldia:mapas/<id>` (exploración hacia `#heraldia:unicas/<id>`, radio limitado a ~10.000 bloques y 8 anillos, `skip_existing_chunks` falso, descarte si no hay destino) y el trato `heraldia:cartografo/<id>`, añadido a `#minecraft:cartographer/level_5` con `merchant_predicate` que exige la etiqueta de entidad `heraldia`; los aldeanos de las plantillas la llevan. Contrato de `unicas/` ampliado con `NOMBRE` y `MAPA` opcionales.
- Corregida la condición `heraldia:sin_lootr` en el botín: en 26.3 un grupo lleva `"condition": {"type": ...}`, no la lista `conditions`.
- La prueba de humo mide cada mapa (máximo 30 s, con o sin destino), tira 20 veces el cofre épico y comprueba el filtro de cartógrafos con un aldeano de la aldea y otro vanilla.
- Configuración: esquema de opciones (por defecto, rango y ayuda en `es_es`/`en_us`) generado por `tools/gen/opciones.py` en `heraldia/opciones.json` del `.jar`; `HeraldiaConfig` lo lee al iniciar el mod, valida, migra por `version` y queda inmutable.
- Tipo de colocación `heraldia:rejilla` (hereda de `random_spread`, así `/locate` la recorre): separación, activación, máximo de casillas más cercanas al 0,0 y zona de exclusión salen de la configuración; lo usan `heraldia:aldeas` y cada `heraldia:unicas/<id>` (salvo las que traigan `STRUCTURE["placement"]` propio).
- Dos mixins (último recurso: un `structure_set` no permite saltarse entradas ni elegir el tamaño): `ChunkGenerator.tryGenerateStructure` y `StructureCheck.canCreateStructure` rechazan estilos desactivados y el tamaño que no toca en la casilla, así el set prueba el siguiente y `/locate` coincide con la generación. Los pesos estándar/grande del set pasan a 1:1.
- Las funciones de gólems leen la limpieza y los límites del marcador `heraldia_cfg`, que el mod rellena al arrancar. Etiqueta nueva `heraldia:aldeas` con todas las aldeas.
- La prueba de humo escribe una configuración de prueba (sin versión, con un valor fuera de rango, una opción desconocida, una familia desactivada y máximo 12) y comprueba la migración, la corrección, el fichero reescrito, el marcador de gólems y que `/locate` desde 20000, 20000 solo encuentra aldeas activadas dentro de las casillas permitidas.
- Fortaleza de hielo (`tools/gen/unicas/fortaleza_hielo/`): una pieza rígida de 51 × 65 × 46 sobre zócalo macizo (sin excavar el terreno), procesador de degradación y auditoría propia (redstone simulada en reposo y accionada, luz de bloque para hielo y generadores, superficie dañada 15-20 %, recorrido con las puertas secretas abiertas). Planos y renders en `docs/unicas/fortaleza_hielo/`; prueba de mecanismos en servidor con `prueba_servidor.py`.
- `lint.py` admite `lint_view` (recorrido sobre la pieza con sus mecanismos accionados) y trata ganchos de cable trampa y palancas como transitables; `writer.py` añade los textos `LANG` de cada estructura única; `render.py` colorea hielo y nieve.
- Ciudadela enana (`tools/gen/unicas/ciudadela/`): una sola plantilla de 74 x 45 x 83 con piel de roca y `structure_void` fuera de las salas; tipo de estructura propio `heraldia:ciudadela` (Java) que elige rotación y posición para que la puerta dé a la ladera y la ciudad quede bajo roca (rejilla de techos escrita por el generador); con `/place` se coloca aunque el terreno no encaje. Auditoría propia (recorrido de todos los cofres, palancas, generadores y entidades; redstone simulado con las reglas del juego, incluidas las 16 combinaciones de la cerradura; lava contenida; generadores a oscuras; 15-20 % de ruina; salas cerradas inalcanzables sin resolver el puzle), planos por nivel y renders en `docs/unicas/ciudadela/`; prueba en servidor `tools/smoke/ciudadela_check.py`.
- `lint.py`: el cable trampa es transitable y una plantilla puede declarar `lint_open` (estados abiertos de sus puertas secretas para el recorrido). `writer.py`: cada estructura única puede aportar textos (`LANG`).
