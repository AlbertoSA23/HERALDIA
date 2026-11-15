# Heraldia

[English](README.md) · **Español**

Mod de Fabric para **Minecraft 26.3** dedicado solo a generar estructuras nuevas en el Overworld.
Todo el contenido actual es vanilla (bloques, objetos y botín del juego base).

Guía para desarrollar: [docs/DESARROLLO.md](docs/DESARROLLO.md).

Contenido:

- **Aldeas enormes**: 72 estructuras (36 estilos por bioma, cada uno en tamaño estándar y grande).
- **La Atlántida**: una única ciudad sumergida por mundo (ver abajo).
- **Estructuras únicas** (una cada 3.000-5.000 bloques, cada una en sus biomas):
  - **Palacio oriental** (`heraldia:unicas/palacio`, cerezales y junglas de bambú): recinto amurallado de 81 × 123 con tres patios en eje, salón del trono sobre plataforma de tres gradas, biblioteca con estudio secreto, tesorería con cámara acorazada, jardín con estanque, pagoda de cinco pisos y pabellones de las concubinas; bajo el trono, la cámara del tesoro con su guardián. Puertas secretas de pistones, trampas de flechas y dos generadores. Diseño y planos en [docs/unicas/palacio.md](docs/unicas/palacio.md).
  - **Fortaleza de hielo** (`heraldia:unicas/fortaleza_hielo`): picos de hielo, llanura nevada y taiga nevada. Murallas y
    torres de hielo sobre un zócalo con criptas, dos puertas secretas de pistones, trampas, generadores de strays y
    esqueletos, el guardián Rey Escarcha y 11 cofres. Diseño: [docs/unicas/fortaleza_hielo.md](docs/unicas/fortaleza_hielo.md).
  - **Ciudadela enana** (`heraldia:unicas/ciudadela`): picos pedregosos y dentados. Ciudad excavada en una montaña con
    la puerta en la ladera: salón de columnas, trono, forjas, cervecería, minas, puente sobre un abismo y bóveda del tesoro;
    cuatro salas ocultas, dos puzles de redstone, dos trampas, tres generadores y el guardián Borin Barbahierro.
    Diseño: [docs/unicas/ciudadela.md](docs/unicas/ciudadela.md).
  - **Templo-pirámide** (`heraldia:unicas/piramide`): jungla y jungla dispersa. Pirámide escalonada mesoamericana con
    templo y crestería, juego de pelota, escalera oculta, cenote interior con cámara sumergida y la tumba del Rey Jaguar
    tras una puerta secreta de pistones; trampas de cable, foso y dardos, 4 generadores y 13 cofres.
    Diseño: [docs/unicas/piramide.md](docs/unicas/piramide.md).
  - **Faro con cueva de contrabandistas** (`heraldia:unicas/faro`, costa pedregosa y playas): faro y casa del farero sobre un promontorio; pasadizo secreto a una cueva al nivel del mar con muelle, almacenes, calabozo, despacho del capitán y cámara del tesoro. Se coloca siempre en la línea de costa, con la boca de la cueva hacia el mar. Diseño en [docs/unicas/faro.md](docs/unicas/faro.md).
  - **Torre de mago** (`heraldia:unicas/torre_mago`): bosque oscuro y jardín pálido. Torre de ocho plantas con
    biblioteca de doble altura, laboratorio, invernadero y observatorio, estudio oculto tras una estantería cincelada,
    sótano de experimentos con generadores y trampas, el guardián Archimago Malvarius y 16 cofres. Diseño:
    [docs/unicas/torre_mago.md](docs/unicas/torre_mago.md).
  - **Coliseo en ruinas** (`heraldia:unicas/coliseo`, sabana y meseta de sabana): anfiteatro elíptico con graderíos, palcos e hipogeo con celdas de fieras, armería, dos puzles de redstone, dos trampas, cuatro generadores, el Campeón de la Arena y una cámara del tesoro oculta. Diseño: [docs/unicas/coliseo.md](docs/unicas/coliseo.md).
  - **Castillo** (`heraldia:unicas/castillo`): llanuras, llanuras de girasoles y praderas. Fortaleza de 100 x 100 con foso,
    muralla, barbacana, patio de armas, torre del homenaje y mazmorra con calabozos, trampas, tres generadores, el guardián
    Sir Aldric y la cámara del tesoro oculta; 36 cofres. Diseño: [docs/unicas/castillo.md](docs/unicas/castillo.md).
  - **Monasterio de montaña** (`heraldia:unicas/monasterio`; prados de montaña y arboledas): terrazas sobre un risco, iglesia, claustro y cuevas con puzles, trampas, guardián y cofre premium. Diseño en [docs/unicas/monasterio.md](docs/unicas/monasterio.md).
  - **Observatorio** (`heraldia:unicas/observatorio`): colinas ventosas y meseta de sabana ventosa. Cúpula de cobre con
    telescopio, planetario, taller de óptica, reloj de sol y, bajo la roca, archivo con dos salas ocultas, puzle de las fases
    lunares, dos trampas, tres generadores y el guardián Custodio de las Estrellas. Diseño: [docs/unicas/observatorio.md](docs/unicas/observatorio.md).
  - **Mansión encantada** (`heraldia:unicas/mansion`): pantano y manglar. Finca victoriana con torreón, invernadero
    arruinado y cementerio con panteón; bajo la casa, tras una estantería secreta, un sótano con laboratorio y cámara del
    tesoro cerrada por una combinación de palancas; dos trampas, tres generadores, el guardián El Conde Malaquías y 33 cofres.
    Diseño: [docs/unicas/mansion.md](docs/unicas/mansion.md).
  - **Catedral gótica** (`heraldia:unicas/catedral`): bosques y bosques de flores. Fachada con dos torres y rosetón, nave con
    triforio y arbotantes, crucero con aguja, girola con capillas, sacristía, biblioteca, claustro y, bajo tierra, cripta,
    osarios y cámara del tesoro; dos puertas secretas, una trampilla oculta, dos trampas, tres generadores, el guardián
    Fray Osmundo y 19 cofres. Diseño: [docs/unicas/catedral.md](docs/unicas/catedral.md).
  - **Acueducto en ruinas** (`heraldia:unicas/acueducto`, desierto y badlands): acueducto de dos pisos, ciudad romana abandonada, cisterna y cloacas con la cámara del tesoro. Diseño en [docs/unicas/acueducto.md](docs/unicas/acueducto.md).
  - **Galeón varado** (`heraldia:unicas/galeon`, playas y playas nevadas): galeón de tres palos encallado en la orilla
    (se sitúa buscando el agua), con bodega, cubierta de cañones, castillos, camarote y cámara secreta del tesorero;
    campamento de náufragos con arqueología y una cueva con el puzle de los faroles, trampas, cuatro generadores y el
    guardián El capitán ahogado; 18 cofres. Diseño: [docs/unicas/galeon.md](docs/unicas/galeon.md).

## Instalación

Requisitos: Minecraft 26.3, Fabric Loader 0.20.1 o superior y Fabric API (probado con 0.166.2+26.3).

1. Compila `heraldia-<versión>.jar` (ver abajo).
2. Cópialo en la carpeta `mods` del servidor y en la de cada cliente.
3. Arranca el servidor. En `logs/latest.log` debe aparecer `Heraldia: 87 estructuras registradas`.

En un mundo existente las estructuras solo aparecen en chunks que todavía no se han generado.
`/reload` no recarga la generación del mundo: hay que reiniciar el servidor (o salir y volver a entrar al mundo en un solo jugador).

## Comandos de prueba

- Colocar una aldea donde estés: `/place structure heraldia:llanuras_castellana` (o `..._grande`). Funciona aunque no estés en su bioma.
- Buscar la más cercana: `/locate structure heraldia:llanuras_castellana`
- Colocar una pieza suelta: `/place template heraldia:llanuras_castellana/specials/church`
- `/function heraldia:muestrario`: coloca las 72 aldeas en cuadrícula a partir de donde estés (cada fila, hacia el sur, es una familia; en cada fila van los 3 estilos y luego sus versiones grandes, hacia el este, separadas 300 bloques). Te pone en espectador y te lleva de una a otra, una cada 8 s (unos 10 min). Al terminar vuelves a creativo.
- `/function heraldia:familia/<familia>` (`llanuras`, `bosque`, `oscuro`, `taiga`, `nieve`, `desierto`, `sabana`, `jungla`, `pantano`, `cerezos`, `badlands`, `costa`): lo mismo con las 6 aldeas de una familia, en fila hacia el este.
- `/function heraldia:muestrario/parar`: lo detiene.
- `/heraldia llave <jugadores> <llave>` (operadores, nivel 2): da las llaves de los cofres cerrados de las estructuras únicas, el mismo objeto que se consigue en el juego. `<llave>` se autocompleta: `todas`, una estructura (`atlantida`: sus cuatro llaves) o una llave suelta (`atlantida.arsenal`, `atlantida.academia`, `atlantida.anfiteatro`, `atlantida.poseidon`). Si el inventario está lleno, la llave cae al suelo a nombre del jugador.

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

## La Atlántida

Una sola por mundo, siempre, sin opción de configuración. Es una ciudad amurallada de unos 770 × 770 bloques, totalmente sumergida, en la cuenca de océano profundo más cercana al origen que esté a 1.500 bloques o más y sin explorar (en un mundo ya existente solo aparece en chunks nuevos). La posición se calcula la primera vez que se carga el mundo y se guarda en `data/heraldia/atlantida.json`.

- Se encuentra con `/locate structure heraldia:unicas/atlantida` o con su mapa del tesoro.
- Calles y plazas inundadas, y más de 200 casas, torres y salas **secas** a las que se entra por puertas o buceando desde abajo. Si se rompe un muro, la sala se inunda.
- Ocho distritos (ágora, lonja, termas, arsenal, puerto hundido, jardines de coral, academia y anfiteatro), un templo en el centro, galerías subterráneas y, al fondo, el guardián final.
- Defensores: guardianes, ahogados con tridente, 48 generadores, guardianes ancianos en los distritos clave y el Guardián de Poseidón.
- Tres sellos con sus llaves, puertas de combinación, trampas de flechas, agua y TNT.
- 185 cofres con botín avanzado y un cofre único, oculto y cerrado con la llave del guardián final, con dos tridentes legendarios. Su contenido es fijo: el primer grupo que llegue se lo lleva.
- Dentro de la ciudad no nacen otras estructuras (monumentos, naufragios, ruinas), salvo las fortalezas, que el juego necesita para llegar al End.

Detalle, planos y qué se ha comprobado: [docs/unicas/atlantida.md](docs/unicas/atlantida.md).

## Mapas del tesoro

Cada estructura única tiene su mapa del tesoro, que marca la más cercana con una X (u otra marca propia de la estructura) y lleva su nombre traducido:

- En los cofres épicos de las aldeas: un 5 % de los cofres lleva uno (de una estructura única al azar).
- A la venta en los cartógrafos maestros (nivel 5) **de las aldeas Heraldia** (no en las vanilla): 24 esmeraldas y una brújula, 2 por reposición. Los aldeanos de aldeas generadas antes de esta versión no lo ofrecen.
- La búsqueda abarca unos 10.000 bloques y no salta chunks ya explorados (así no traba el servidor). Si no hay ninguna estructura de ese tipo al alcance, no sale el mapa (el cofre lo deja vacío y el cartógrafo no ofrece ese trato).
- Para probar: `/loot give @s loot heraldia:mapas/<id>` da el mapa de la estructura `heraldia:unicas/<id>` desde donde estés.

Limitaciones conocidas: el puerto sale recto desde la calle sin buscar el agua; en laderas puede haber escalones y cimientos altos; no se ha comprobado el solape con estructuras de otros mods.

## Logros

Pestaña de logros **Heraldia** (63 logros), con textos en español e inglés. Solo dan experiencia, nunca objetos:

- **Heraldia** (raíz): entrar en cualquier aldea Heraldia o estructura única.
- Una aldea de cada familia (12 logros, 20 de experiencia) y el desafío **Trotamundos de Heraldia**: las 12 familias (250).
- Por cada estructura única: descubrirla (50), derrotar a su guardián con nombre (100) y abrir su cofre del tesoro (50).
- La Atlántida, además: sus tres sellos (abrir el cofre del sello o tener su llave, 30 cada uno); el guardián es el Guardián de Poseidón y el tesoro cuenta al coger uno de los objetos con nombre del cofre único.
- Desafío final **Cartógrafo de leyendas**: descubrir todas las estructuras únicas (500).

Notas: una estructura cuenta al entrar en sus piezas, no basta con verla. Si se desactiva una familia o una estructura en la [configuración](#configuración), su logro y el desafío correspondiente no se pueden conseguir. Con Lootr, el logro del tesoro depende de que Lootr avise al juego al abrir el cofre (sin comprobar). Los logros de las estructuras únicas se generan solos a partir del registro de únicas, así que una estructura nueva trae los suyos.

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
| `unicas.<id>.separacion_bloques` | la de la estructura (4000) | 1000-10000 | Separación media entre estructuras de ese tipo (por defecto, una cada 3000-5000 bloques). Cada tipo se reparte por toda su casilla de la rejilla (con el origen desplazado por tipo) y dos del mismo tipo nunca quedan a menos de `unicas.distancia_minima.bloques`. |
| `unicas.distancia_minima.activada` | `true` | `true`/`false` | Impide que dos estructuras únicas distintas (también la Atlántida) salgan a menos de la distancia mínima. |
| `unicas.distancia_minima.bloques` | 1000 | 100-3000 | Distancia mínima entre los chunks de inicio de dos estructuras únicas distintas. Si dos candidatas quedan demasiado cerca, un sorteo determinista (semilla y posición) se queda con una; si la ganadora no puede salir ahí (bioma o terreno), se conserva la otra. `/locate` y los mapas del tesoro siguen la misma regla. |

La Atlántida no aparece: es siempre una sola por mundo.

## Compilar

Requisitos: Java 25, Python 3.11+ y `pip install -r tools/gen/requirements.txt`, git.

```bash
./gradlew build
```

El `.jar` queda en `build/libs/`. La compilación ejecuta el generador `tools/gen/main.py`, que crea las estructuras y los logros, los valida contra los registros de 26.3 y audita las estructuras; si hay un solo error o aviso, la compilación falla.

Los registros de 26.3 (resumen de [misode/mcmeta](https://github.com/misode/mcmeta), rama `26.3-summary`) no se incluyen en el repositorio porque son datos de Mojang. Se clonan solos en `build/mcmeta-summary`; para usar otra copia: `-Pmcmeta_summary=<ruta>` o la variable `MCMETA_SUMMARY`.

Comprobaciones antes de publicar (la CI de GitHub Actions, `.github/workflows/ci.yml`, las ejecuta todas, también las de cada estructura única, en cada PR contra `develop` o `main` y en cada push a `develop`):

```bash
python3 tools/changelog.py check
```

```bash
python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-0.1.0.jar
```

La segunda descarga un servidor Fabric 26.3 real en `build/smoke`, arranca con el mod y comprueba que las 87 estructuras estén registradas y los 63 logros cargados, que `/place structure` coloque una aldea con aldeanos y que las funciones existan.

Pruebas en servidor de cada estructura única (mismo argumento `--jar`): `tools/smoke/coliseo_redstone.py`, `observatorio_smoke.py`, `palacio_redstone.py`, `ciudadela_check.py` y `galeon_test.py`, y en `tools/gen/unicas/`: `castillo/prueba_redstone.py`, `torre_mago/prueba_redstone.py`, `catedral/prueba_juego.py` y `prueba_servidor.py` de `fortaleza_hielo`, `mansion`, `monasterio` y `piramide`. La Atlántida se comprueba dentro de la prueba de humo (`atlantida/humo.py`).

Versiones fijadas en `gradle.properties`. Herramientas del generador: `tools/gen/sim.py` (simula el ensamblado jigsaw), `tools/gen/render.py` (renders isométricos), `tools/gen/lint.py` (auditoría de diseño).

## Licencia y créditos

Sin licencia: todos los derechos reservados. El código es visible pero no se concede permiso para usarlo, copiarlo ni redistribuirlo.
Todo el contenido usa solo bloques y objetos de Minecraft; no se incluyen recursos de terceros.
