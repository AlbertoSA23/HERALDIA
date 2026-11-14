# Heraldia

Mod de Fabric para **Minecraft 26.3** dedicado solo a generar estructuras nuevas en el Overworld.
Todo el contenido actual es vanilla (bloques, objetos y botín del juego base).

Guía para desarrollar: [docs/DESARROLLO.md](docs/DESARROLLO.md).

Contenido:

- **Aldeas enormes**: 72 estructuras (36 estilos por bioma, cada uno en tamaño estándar y grande).
- **Estructuras únicas** (una cada 3000-5000 bloques por defecto, cada una en su bioma):
  - **Observatorio** (colinas ventosas y meseta de sabana ventosa): cúpula con telescopio, planetario, reloj de sol, archivo subterráneo con salas ocultas, puzle de fases lunares, trampas y guardián. Diseño en `docs/unicas/observatorio.md`.

## Instalación

Requisitos: Minecraft 26.3, Fabric Loader 0.20.1 o superior y Fabric API (probado con 0.166.2+26.3).

1. Compila `heraldia-<versión>.jar` (ver abajo).
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

Por defecto, una aldea cada 1000-2000 bloques (separación media 1500), como mucho 100 por mundo (las más cercanas al 0,0) y nunca a menos de 10 chunks de una aldea vanilla. La versión estándar sale 3 veces más que la grande. Todo ello se cambia en la [configuración](#configuración).

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
La función `heraldia:golems` revisa cada 30 s las aldeas cargadas y retira un gólem natural cada vez que hay 8 o más (estándar) o 9 o más (grande); no toca los construidos por jugadores. Límites y limpieza se cambian en la [configuración](#configuración).

## Mapas del tesoro

Cada estructura única tiene su mapa del tesoro, que marca la más cercana con una X (u otra marca propia de la estructura) y lleva su nombre traducido:

- En los cofres épicos de las aldeas: un 5 % de los cofres lleva uno (de una estructura única al azar).
- A la venta en los cartógrafos maestros (nivel 5) **de las aldeas Heraldia** (no en las vanilla): 24 esmeraldas y una brújula, 2 por reposición. Los aldeanos de aldeas generadas antes de esta versión no lo ofrecen.
- La búsqueda abarca unos 10.000 bloques y no salta chunks ya explorados (así no traba el servidor). Si no hay ninguna estructura de ese tipo al alcance, no sale el mapa (el cofre lo deja vacío y el cartógrafo no ofrece ese trato).
- Para probar: `/loot give @s loot heraldia:mapas/<id>` da el mapa de la estructura `heraldia:unicas/<id>` desde donde estés.

Limitaciones conocidas: el puerto sale recto desde la calle sin buscar el agua; en laderas puede haber escalones y cimientos altos; no se ha comprobado el solape con estructuras de otros mods.

## Configuración

Fichero `config/heraldia.json` del servidor (en un mundo de un jugador, el de la carpeta del juego). Se crea al arrancar con todos los valores por defecto
y se reescribe en cada arranque con los valores en uso y una ayuda (`_ayuda`) en español e inglés. Un valor que no sea válido (fuera de rango o de otro tipo)
se avisa en el log y se sustituye por el de por defecto; una opción desconocida se avisa y se ignora. El campo `version` permite migrar el fichero
cuando cambie su formato. Se lee solo al arrancar el servidor y afecta a los chunks que se generen después (no a lo ya generado).

| Opción | Por defecto | Rango | Qué hace |
| --- | --- | --- | --- |
| `aldeas.separacion_bloques` | 1500 | 1000-10000 | Separación media entre aldeas; la mínima guarda la proporción 62/94 de la rejilla. |
| `aldeas.maximo` | 100 | 0-100 | Máximo de aldeas por mundo: solo valen las casillas de la rejilla más cercanas al 0,0 (determinista, sin datos guardados). |
| `aldeas.porcentaje_grandes` | 25 | 0-100 | Porcentaje de aldeas grandes; el resto son estándar. |
| `aldeas.distancia_aldeas_vanilla_bloques` | 160 | 0-256 | Distancia mínima a una aldea vanilla (se redondea a chunks); 0 la desactiva. |
| `aldeas.familias.<familia>` | `true` | `true`/`false` | Activa una familia entera (sus 3 estilos). |
| `aldeas.estilos.<estilo>` | `true` | `true`/`false` | Activa un estilo (estándar y grande). Si una casilla elige uno desactivado, se prueba otro estilo de su bioma. |
| `golems.limpieza` | `true` | `true`/`false` | Activa la retirada periódica de gólems naturales. |
| `golems.limite_estandar` | 8 | 1-64 | Con tantos gólems naturales o más, una aldea estándar retira uno cada 30 s. |
| `golems.limite_grande` | 9 | 1-64 | Igual para las aldeas grandes. |
| `unicas.<id>.activada` | `true` | `true`/`false` | Activa una estructura única. Aparece una entrada por cada estructura única del mod. |
| `unicas.<id>.separacion_bloques` | la de la estructura (4000) | 1000-10000 | Separación media entre estructuras de ese tipo (por defecto, una cada 3000-5000 bloques). |

La Atlántida no aparece: es siempre una sola por mundo.

## Compilar

Requisitos: Java 25, Python 3.11+ y `pip install -r tools/gen/requirements.txt`, git.

```bash
./gradlew build
```

El `.jar` queda en `build/libs/`. La compilación ejecuta el generador `tools/gen/main.py`, que crea las estructuras, las valida contra los registros de 26.3 y las audita; si hay un solo error o aviso, la compilación falla.

Los registros de 26.3 (resumen de [misode/mcmeta](https://github.com/misode/mcmeta), rama `26.3-summary`) no se incluyen en el repositorio porque son datos de Mojang. Se clonan solos en `build/mcmeta-summary`; para usar otra copia: `-Pmcmeta_summary=<ruta>` o la variable `MCMETA_SUMMARY`.

Comprobaciones antes de publicar:

```bash
python3 tools/changelog.py check
```

```bash
python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-0.1.0.jar
```

La segunda descarga un servidor Fabric 26.3 real en `build/smoke`, arranca con el mod y comprueba que las 72 estructuras estén registradas, que `/place structure` coloque una aldea con aldeanos y que las funciones existan.

Versiones fijadas en `gradle.properties`. Herramientas del generador: `tools/gen/sim.py` (simula el ensamblado jigsaw), `tools/gen/render.py` (renders isométricos), `tools/gen/lint.py` (auditoría de diseño).

## Licencia y créditos

Sin licencia: todos los derechos reservados. El código es visible pero no se concede permiso para usarlo, copiarlo ni redistribuirlo.
Todo el contenido usa solo bloques y objetos de Minecraft; no se incluyen recursos de terceros.
