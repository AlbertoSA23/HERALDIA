# Heraldia

Mod de Fabric para **Minecraft 26.3** dedicado solo a generar estructuras nuevas en el Overworld.
Todo el contenido actual es vanilla (bloques, objetos y botín del juego base).

Contenido:

- **Aldeas enormes**: 72 estructuras (36 estilos por bioma, cada uno en tamaño estándar y grande).
- **Estructuras únicas** (castillos, catedrales...): pendientes de diseño.

## Instalación

Requisitos: Minecraft 26.3, Fabric Loader 0.20.1 o superior y Fabric API (probado con 0.166.2+26.3).

1. Descarga `heraldia-<versión>.jar` (de los artefactos de la CI en GitHub Actions o compilándolo, ver abajo).
2. Cópialo en la carpeta `mods` del servidor y en la de cada cliente.
3. Arranca el servidor. En `logs/latest.log` debe aparecer `Heraldia: 72 estructuras registradas`.

En un mundo existente las estructuras solo aparecen en chunks que todavía no se han generado.
`/reload` no recarga la generación del mundo: hay que reiniciar el servidor (o salir y volver a entrar al mundo en un solo jugador).

## Comandos de prueba

- Colocar una aldea donde estés: `/place structure heraldia:llanuras_castellana` (o `..._grande`). Funciona aunque no estés en su bioma.
- Buscar la más cercana: `/locate structure heraldia:llanuras_castellana`
- Colocar una pieza suelta: `/place template heraldia:llanuras_castellana/specials/church`
- `/function heraldia:muestrario`: coloca las 72 aldeas en cuadrícula a partir de donde estés (cada fila, hacia el sur, es una familia; en cada fila van los 3 estilos y luego sus versiones grandes, hacia el este, separadas 300 bloques). Te pone en espectador y te lleva de una a otra, una cada 8 s (unos 10 min). Al terminar vuelves a creativo.
- `/function heraldia:familia/<familia>` (`llanuras`, `bosque`, `oscuro`, `taiga`, `nieve`, `desierto`, `sabana`, `jungla`, `pantano`, `cerezos`, `badlands`, `costa`): lo mismo con las 6 aldeas de una familia, en fila hacia el este.
- `/function heraldia:muestrario/parar`: lo detiene.

Usa el muestrario solo en un mundo de prueba: lo colocado se queda.

## Aldeas enormes

Una aldea cada 1000-2000 bloques (nunca a menos de 10 chunks de una aldea vanilla). La versión estándar sale 3 veces más que la grande.

| Familia | Biomas | Estilos (ID `heraldia:<estilo>` y `heraldia:<estilo>_grande`) |
| --- | --- | --- |
| Llanuras | llanura, girasoles, pradera | `llanuras_castellana`, `llanuras_gallega`, `llanuras_entramado` |
| Bosque templado | bosque, de flores, abedules (y antiguo), bosque moteado | `bosque_lenadores`, `bosque_elfica`, `bosque_abadia` |
| Bosque oscuro | bosque oscuro, jardín pálido | `oscuro_gotica`, `oscuro_alquimistas`, `oscuro_fortificada` |
| Taiga | taiga, taigas ancestrales | `taiga_nordica`, `taiga_eslava`, `taiga_cazadores` |
| Nieve | llanura y taiga nevadas, arboleda, picos de hielo | `nieve_alpina`, `nieve_fortaleza`, `nieve_pastores` |
| Desierto | desierto | `desierto_andalusi`, `desierto_obelisco`, `desierto_caravanera` |
| Sabana | sabana, meseta de sabana | `sabana_paja`, `sabana_terracota`, `sabana_pastores` |
| Jungla | jungla, dispersa, bambú | `jungla_arboles`, `jungla_templos`, `jungla_bambu` |
| Pantano | pantano, manglar | `pantano_palafitos`, `pantano_brujas`, `pantano_turba` |
| Cerezos | cerezal | `cerezos_japonesa`, `cerezos_templo`, `cerezos_artesanos` |
| Badlands | badlands, erosionadas, boscosas | `badlands_minera`, `badlands_roca`, `badlands_canon` |
| Costa | playa, playa nevada, costa pedregosa | `costa_pescadores`, `costa_mercante`, `costa_mediterranea` |

Cada aldea tiene:

- Plaza mayor con fuente, bancos, árboles, campana y dos gólems.
- Cuatro avenidas con los edificios especiales: iglesia o templo según el estilo (con cementerio y cripta), ayuntamiento, mercado, taberna, herrería, biblioteca, granja con molino y posada (o puerto en la costa).
- Unas 20 casas en la estándar y unas 30 en la grande, amuebladas, con cofres en algunas y botín de común a épico (tablas `heraldia:cofres/comun`, `poco_comun`, `raro`, `epico`).
- Torres de vigilancia y puertas de muralla al final de las calles; decoración temática entre casas.
- Aldeanos: la mitad del número de casas, más del 80 % con oficio. Gólems: al menos uno por cada 3 aldeanos.

Límites de población: hay unas 1,25 camas por aldeano inicial, así que la población crece como mucho un 25 %.
La función `heraldia:golems` revisa cada 30 s las aldeas cargadas y retira los gólems naturales por encima de 8 (estándar) o 9 (grande); no toca los construidos por jugadores.

Limitaciones conocidas: el puerto sale recto desde la calle sin buscar el agua; en laderas puede haber escalones y cimientos altos; no se ha comprobado el solape con estructuras de otros mods.

## Compilar

Requisitos: Java 25, Python 3.11+ y `pip install -r tools/gen/requirements.txt`, git.

```bash
./gradlew build
```

El `.jar` queda en `build/libs/`. La compilación ejecuta el generador `tools/gen/main.py`, que crea las estructuras, las valida contra los registros de 26.3 y las audita; si hay un solo error o aviso, la compilación falla.

Los registros de 26.3 (resumen de [misode/mcmeta](https://github.com/misode/mcmeta), rama `26.3-summary`) no se incluyen en el repositorio porque son datos de Mojang. Se clonan solos en `build/mcmeta-summary`; para usar otra copia: `-Pmcmeta_summary=<ruta>` o la variable `MCMETA_SUMMARY`.

Comprobaciones (las mismas que la CI):

```bash
python3 tools/changelog.py check
```

```bash
python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-0.1.0.jar
```

La segunda descarga un servidor Fabric 26.3 real en `build/smoke`, arranca con el mod y comprueba que las 72 estructuras estén registradas, que `/place structure` coloque una aldea con aldeanos y que las funciones existan.

Versiones fijadas en `gradle.properties`. Herramientas del generador: `tools/gen/sim.py` (simula el ensamblado jigsaw), `tools/gen/render.py` (renders isométricos), `tools/gen/lint.py` (auditoría de diseño).

## Licencia y créditos

El repositorio aún no tiene licencia: hasta que se elija una, el código no es de uso libre.
Todo el contenido usa solo bloques y objetos de Minecraft; no se incluyen recursos de terceros.
