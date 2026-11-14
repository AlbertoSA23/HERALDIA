# Registro de cambios

Formato: cada versión es `## [X.Y.Z]` (con ` - AAAA-MM-DD` al publicarla) y lleva dos apartados:
`### Jugadores` (lo que nota quien juega) y `### Técnico` (cambios internos). La versión de arriba
coincide con `mod_version` de `gradle.properties`; `tools/changelog.py` lo comprueba y extrae las notas de publicación.

## [0.1.0]

### Jugadores

- Primera versión del mod: 72 aldeas enormes (36 estilos por bioma, cada uno en tamaño estándar y grande) que aparecen en chunks nuevos del Overworld, una cada 1000-2000 bloques.
- Comandos de prueba `/function heraldia:muestrario` y `/function heraldia:familia/<familia>` para ver los estilos colocados en fila; sus mensajes salen en español o inglés según el idioma del cliente.
- Mapas del tesoro hacia cada estructura única: en el 5 % de los cofres épicos de las aldeas y a la venta en los cartógrafos maestros de las aldeas Heraldia (24 esmeraldas y una brújula); con nombre en español o inglés.

- Nueva estructura única: **Palacio oriental**, en cerezales y junglas de bambú. Muralla con puerta monumental, patios con río y puentes, salón del trono sobre una plataforma de mármol, biblioteca con estudio secreto, tesorería con cámara acorazada, jardín con estanque y pagoda de cinco pisos. Detrás del trono hay dos palancas gemelas (una abre un pasadizo, la otra dispara); bajo el salón esperan un pasillo con trampas, la sala de los guerreros de terracota y la cámara del tesoro con su guardián, el Comandante de la Guardia Imperial. Un 15 % del palacio está en ruinas.
- Fichero de configuración `config/heraldia.json`: separación entre aldeas (1000-10000 bloques, por defecto 1500), máximo de aldeas por mundo (hasta 100, las más cercanas al 0,0), porcentaje de grandes, distancia a las aldeas vanilla, familias y estilos activables, límites y limpieza de gólems, y activación y separación de cada estructura única. Los valores no válidos se avisan en el log y se cambian por los de por defecto.

### Técnico

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
- Palacio oriental (`tools/gen/unicas/palacio/`): una pieza rígida de 81 × 123 con `beard_box`, sin sótanos bajo el terreno (la cámara está dentro de la plataforma); aire explícito en todo el volumen; procesador de desgaste en línea en el pool. Auditoría propia como condición para generar: modelo de redstone sin polvo (coherencia de pistones y dispensadores al colocarse, puertas que solo abren con sus palancas), recorrido con los puzles cerrados y abiertos, nada flotando (conexión por caras con el zócalo) y ruina entre el 15 y el 20 % de la superficie. Planos y renders en `docs/unicas/palacio/`; prueba en servidor de sus mecanismos en `tools/smoke/palacio_redstone.py`.
- `lint.py`: `tripwire` y `lever` cuentan como atravesables, y una pieza puede declarar `audit_open` (estado de sus mecanismos abiertos) para auditar el recorrido. `writer.py` suma al idioma las claves `LANG` opcionales de cada módulo único.
- Corregida la condición `heraldia:sin_lootr` en el botín: en 26.3 un grupo lleva `"condition": {"type": ...}`, no la lista `conditions`.
- La prueba de humo mide cada mapa (máximo 30 s, con o sin destino), tira 20 veces el cofre épico y comprueba el filtro de cartógrafos con un aldeano de la aldea y otro vanilla.
- Configuración: esquema de opciones (por defecto, rango y ayuda en `es_es`/`en_us`) generado por `tools/gen/opciones.py` en `heraldia/opciones.json` del `.jar`; `HeraldiaConfig` lo lee al iniciar el mod, valida, migra por `version` y queda inmutable.
- Tipo de colocación `heraldia:rejilla` (hereda de `random_spread`, así `/locate` la recorre): separación, activación, máximo de casillas más cercanas al 0,0 y zona de exclusión salen de la configuración; lo usan `heraldia:aldeas` y cada `heraldia:unicas/<id>` (salvo las que traigan `STRUCTURE["placement"]` propio).
- Dos mixins (último recurso: un `structure_set` no permite saltarse entradas ni elegir el tamaño): `ChunkGenerator.tryGenerateStructure` y `StructureCheck.canCreateStructure` rechazan estilos desactivados y el tamaño que no toca en la casilla, así el set prueba el siguiente y `/locate` coincide con la generación. Los pesos estándar/grande del set pasan a 1:1.
- Las funciones de gólems leen la limpieza y los límites del marcador `heraldia_cfg`, que el mod rellena al arrancar. Etiqueta nueva `heraldia:aldeas` con todas las aldeas.
- La prueba de humo escribe una configuración de prueba (sin versión, con un valor fuera de rango, una opción desconocida, una familia desactivada y máximo 12) y comprueba la migración, la corrección, el fichero reescrito, el marcador de gólems y que `/locate` desde 20000, 20000 solo encuentra aldeas activadas dentro de las casillas permitidas.
