# Auditoría final de la 0.1.0 (16-17/11/2026)

Sesión auditora tras integrar en `develop`, por este orden, T23 muelles (#62), T24 medianas 1 (#61), T25 caminos (#63),
T26 medianas 2 (#64), T27 Guía (#65), T28 jefes con fases (#66), T29 botín que se repone y dificultad (#67), T30 minas
(#68), T31 arena (#70), T33 idiomas y README (#71) y T32 coste de generación en CI (#69), sobre T1-T22. Base auditada:
`develop` en `a15df3f`. Arreglos: PR #72 (rama `claude/heraldia-auditoria`). `mod_version` sigue en 0.1.0; no se toca
`main` ni `publish.yml`.

## Resultados de la batería

| Qué | Dónde | Resultado |
|---|---|---|
| CI completa de `develop` (a15df3f, push) | GitHub, run 43972960402 | ✅ 16 jobs |
| `./gradlew build` completo (con `testPesado`), develop | local, 4 núcleos | ✅ 8 min 30 s |
| `./gradlew build` completo, rama de la auditoría | local | ✅ 8 min 5 s |
| pytest del generador | local y CI | ✅ 622 en develop; 637 en la rama |
| `tools/changelog.py check` | local y CI | ✅ |
| Batería de servidor completa (45 pruebas: humo, 43 de servidor —con los 9 grupos de `compat_mods`— y la nueva `mundo_existente`), `.jar` de develop | local, 2 carriles con `--work` distintos | 43 ✅, 2 ❌ esperados (abajo) |
| Pruebas afectadas por los arreglos, `.jar` de la rama: humo, `arena`, `guia`, `botin_reponer`, `dificultad`, `entradas_mina`, Salón del Jarl, `mundo_existente` | local | ✅ todas |
| Coste de generación, `.jar` de la rama (3 pasadas) | local, solo en la máquina | ✅ **+3,4 %** (referencia +9,3 %, límite +19,7 %) |
| CI completa de la PR (`[bateria completa]`) | GitHub | ✅ 16 jobs en 76f116c (ver el head final en la PR) |

Fallos vistos y por qué:
- `arena.py` con el `.jar` de develop: las dos comprobaciones **nuevas** del dispensador (un dispensador pegado a la arena
  vaciaba un cubo de lava en ella). Es el fallo real que arregla la PR; con el `.jar` de la rama pasa (local y CI).
- `mundo_existente.py` (nueva): primero fallos de la propia prueba (los arrays de NBT y la paleta de 26.3, el límite de
  256 chunks de `/forceload`), y luego 78 diferencias que **no son del mod** (lava y agua que siguen fluyendo en las
  cuevas de los bordes, puertas que abren los aldeanos, `server_data` de las bóvedas): con el mundo congelado
  (`/tick freeze`) en los arranques 2 y 3, 0 diferencias. Pasa en local y en la CI.
- De entorno, no del mod: una descarga de Fabric API cortada por la red se quedó en la caché de una carpeta de prueba y
  hacía fallar en 1 s todo lo que venía detrás (arreglado: ver abajo); y una tanda que arranqué por error con Java 21.
- El Salón del Jarl («dispensadores del cable trampa cargados») **no se ha reproducido**: 6 de 6 en local (una en la
  batería con otro servidor a la vez, cuatro seguidas mientras compilaba y una con el `.jar` de la rama) y en las CI.

Coste (local, mediana de 3 pasadas): CPU por chunk 50,8 → 52,5 ms (+3 %), pasos de estructuras 5,72 → 6,35 ms por
chunk, memoria máx. tras GC 368 → 390 MB, MSPT p99 2,8 → 10,0 ms (durante la generación con Chunky; máx. 10,8 ms).
`/locate`: aldea 259 ms, única 288 ms, mediana 39 ms, **mina 4.277 ms** (documentado).

## Revisión cruzada (lo que ninguna sesión probó junto)

| Cruce | Cómo se comprobó | Resultado |
|---|---|---|
| Caminos frente a minas | código (`CaminoFeature.cajas`: piezas de estructuras `surface_structures` en 3D; las bocas de mina lo son, las galerías no tapan la superficie) | ✅ el camino se para en la boca y pasa sobre las galerías |
| Caminos frente a arena | código (`Obras.nivelar`, `Estructuras.ocupado`) | ⚠️ la arena no sabe de caminos: si se coloca sobre uno lo corta (riesgo abajo) |
| Medianas frente a minas | `entradas_mina.py` (ninguna mediana a menos de `medianas.distancia_minima.bloques` de una mina) y `MinasTest` | ✅ |
| Dificultad y fases de jefe frente a la arena | código (`Juego.crear/preparar`: modificadores propios que se suman a los de la dificultad; el mini-jefe lleva `heraldia_guardian`) y `arena.py` (fases y refuerzos del mini-jefe) | ✅ |
| Reposición de botín frente a minas y arena | `ReposicionTest` (todas las tablas de cofre de las plantillas se reponen; ahora exige también las de minas) | ✅ reposición; ❌→✅ la **dificultad** no escalaba el botín de las minas (arreglado) |
| Guía, todas sus páginas, en los 8 idiomas | `GuiaTest.libroEnCadaIdioma` (8 idiomas), comprobación del generador (cada página cabe en cada idioma) y `guia.py` | ✅ |
| `rejilla_compatible` con lo nuevo | `rejilla_compatible.py` (coordenadas de main) y `CaminoFeature`/`Caminos` (usan la rejilla en uso) | ✅ |
| Mundo existente: nada cambia en lo ya generado | **prueba nueva** `mundo_existente.py`: genera la zona A con lo nuevo apagado, apaga, arranca con la configuración por defecto (fichero borrado) y luego con casi todo cambiado; compara A (y B) leyendo las regiones; comprueba que en el anillo nuevo sí sale camino (16 chunks, 159 columnas) | ✅ 64 de 64 chunks idénticos, ninguna entidad perdida, la arena dice «mundo existente» |
| Rendimiento global | `coste_generacion.py` local y en la CI | ✅ +3,4 % |
| Compatibilidad con mods | los 9 grupos de `compat_mods.py` (local y CI) | ✅ |

## Arreglos (PR #72), cada uno con su test

1. **Cubos por dispensador junto a la arena**: `ArenaCuboMixin` (`BucketItem`/`SolidBucketItem.emptyContents`, salida
   temprana sin arena) con la lógica pura en `Zona.cuboNegado` (`ZonaTest`); en `arena.py`, un dispensador con lava
   pegado a la arena no la vacía (la suelta como objeto) y otro lejos sí.
2. **Botín de las minas y la dificultad**: `dificultad.escalar_botin` no tocaba `heraldia:minas/` (T29 se fusionó antes
   que T30). `DificultadMobs.esBotinDeCofre` usa la misma lista que la reposición (`DificultadTest`, `ReposicionTest`).
3. **Carteles**: unas 110 líneas en los 8 idiomas pasaban de 90 px (la lista de «Fallos pendientes» estaba incompleta) y
   el juego corta las palabras que no caben. Reescritas sin cambiar claves ni bloques; la generación falla ahora con
   cualquier línea de más de 90 px en cualquier idioma, contando la negrita (+1 px por carácter) (`test_idiomas.py`).
4. **Prueba nueva `tools/smoke/mundo_existente.py`** (arriba), con sus funciones puras en `test_smoke_descarga.py`.
5. **Descargas de las pruebas**: `server_smoke.download` repite una descarga cortada y no deja un `.jar` roto en la caché
   (`test_smoke_descarga.py`).
6. **Salón del Jarl**: diagnóstico («DIAG trampa»: entidades a 24 bloques del cable y contenido de los dispensadores) si
   vuelve a fallar. No se ha cambiado la comprobación.
7. **Documentación**: el mod en los clientes es opcional (`DESARROLLO`, `CONFIGURACION`/`CONFIGURATION` decían que iba
   en cada cliente); aviso del `/locate` lento de las minas en `CONTENIDO`/`CONTENT`; aprendizajes y estado de cada
   fallo pendiente en `APRENDIZAJES`; `CHANGELOG` (0.1.0 sin publicar) con todo lo anterior. Los README de los 8 idiomas
   ya estaban al día con lo integrado (`test_readme.py`).

## Riesgos que quedan

- `/locate structure #heraldia:minas` para el servidor ~4 s desde un sitio sin minas cerca (documentado; el juego normal
  no pasa por ahí: no hay mapas de minas y `/heraldia info cerca` busca fuera del hilo).
- La arena, al colocarse, solo evita las estructuras de los chunks ya guardados y no sabe de caminos: en un mundo nuevo
  podría pisar una estructura que se genera durante la obra, y en cualquiera corta un camino que pase por su sitio. En
  el mundo de Alberto (ya existente) solo se coloca a mano con `/heraldia arena colocar`, que enseña el sitio antes.
- El fallo intermitente del Salón del Jarl sigue sin causa conocida (solo la prueba; el resto de esa prueba pasa siempre).
- Los caminos solo salen en chunks nuevos: en un mundo existente, uno entre una aldea vieja y una nueva se queda en el
  borde de lo ya generado. Es lo esperado (documentado), pero se verá.
- Lo visual (carteles reescritos, Guía en el cliente, barras de jefe, arena) no se da por bueno sin capturas.

## Opciones recomendadas para el mundo de Alberto

Haz antes una copia de seguridad del mundo. Con los valores por defecto el mundo existente no cambia en lo ya generado
(lo comprueba `mundo_existente.py`), y:
- `unicas.rejilla_compatible`: **`true` solo si el mundo ya tuvo Heraldia 0.1.0** (la de `main`); si nunca lo tuvo,
  `false` (por defecto).
- `arena.*`: por defecto. En un mundo existente no se construye sola (lo comprueba el log «mundo existente»); si se
  quiere, `/heraldia arena colocar` (mirar el sitio antes de `confirmar`: despeja y nivela).
- `botin.reponer.activado`: `false` (por defecto) salvo que se quiera; `dificultad.nivel`: `normal`.
- `guia.entregar_al_entrar`: `true` (por defecto): cada jugador recibe la Guía una vez.
- Lo demás, por defecto (caminos, medianas, minas x2, jefes con fases).

## Qué probar a mano (necesita cliente real o capturas)

1. **Carteles reescritos**, con un cliente vanilla (texto en español) y con el mod en otro idioma: que ninguna línea se
   corte. Los más largos: ágora y academia de la Atlántida, sello de la catedral, runas y vestíbulo del Salón del Jarl,
   despacho del faro, castillete de la mina perdida y el título en negrita del sello del templo de la Atlántida.
2. **Guía del Heraldo** en un cliente vanilla con el idioma en francés, alemán, catalán...: que llega en ese idioma,
   que las páginas no se salen y que el diario se ordena bien.
3. **Arena**: colocarla con `/heraldia arena colocar` (partículas visibles), una partida hasta la oleada 5 con el
   mini-jefe (barra de jefe, títulos, marcador lateral), morir en el ruedo (reaparecer en la entrada con el inventario,
   que en la prueba no se puede: el jugador simulado se desconecta al morir) y un dispensador con lava junto al muro.
4. **Jefes con fases**: la barra de jefe, el aviso en la barra de acción, partículas y sonido al cambiar de fase.
5. **Caminos y medianas en un mundo existente**: explorar tierras nuevas y ver cómo acaba un camino en el borde de lo
   ya generado; farolas, puentes y el cartel con el nombre de la aldea siguiente.
6. **Minas**: bajar por una boca de cada tamaño (vías, cruces, vagoneta, arañas y generador).
7. **Muelles** de las aldeas de costa: que el muelle llega al agua.
8. **Pantalla de configuración** (con Mod Menu, cliente con el mod): las secciones nuevas (arena, dificultad, botín).
9. Con el **modpack de CurseForge** de verdad: arrancar el servidor y mirar el log (`Heraldia: 142 estructuras
   registradas`, sin errores de registro) y el MSPT al explorar.
