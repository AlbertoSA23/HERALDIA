# Registro de cambios

Formato: cada versión es `## [X.Y.Z]` (con ` - AAAA-MM-DD` al publicarla) y lleva dos apartados:
`### Jugadores` (lo que nota quien juega) y `### Técnico` (cambios internos). La versión de arriba
coincide con `mod_version` de `gradle.properties`; `tools/changelog.py` lo comprueba y extrae las notas de publicación.

## [0.1.0]

### Jugadores

- Primera versión del mod: 72 aldeas enormes (36 estilos por bioma, cada uno en tamaño estándar y grande) que aparecen en chunks nuevos del Overworld, una cada 1000-2000 bloques.
- Comandos de prueba `/function heraldia:muestrario` y `/function heraldia:familia/<familia>` para ver los estilos colocados en fila; sus mensajes salen en español o inglés según el idioma del cliente.
- Nueva estructura única: la **Fortaleza de hielo**, en picos de hielo, llanuras nevadas y taigas nevadas. Murallas, torres afiladas, gran salón con trono de hielo, barracones, cocinas, perrera con lobos de las nieves, galería de esculturas de hielo, criptas con generadores de strays y esqueletos, el guardián Rey Escarcha y una cámara del tesoro tras una puerta secreta. Dos puzles de palanca y pistones, trampas de cable y de placa, y botín creciente hasta el cofre final.

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
- Fortaleza de hielo (`tools/gen/unicas/fortaleza_hielo/`): una pieza rígida de 51 × 65 × 46 sobre zócalo macizo (sin excavar el terreno), procesador de degradación y auditoría propia (redstone simulada en reposo y accionada, luz de bloque para hielo y generadores, superficie dañada 15-20 %, recorrido con las puertas secretas abiertas). Planos y renders en `docs/unicas/fortaleza_hielo/`; prueba de mecanismos en servidor con `prueba_servidor.py`.
- `lint.py` admite `lint_view` (recorrido sobre la pieza con sus mecanismos accionados) y trata ganchos de cable trampa y palancas como transitables; `writer.py` añade los textos `LANG` de cada estructura única; `render.py` colorea hielo y nieve.
