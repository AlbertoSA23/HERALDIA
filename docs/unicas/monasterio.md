# Monasterio de montaña (`heraldia:unicas/monasterio`)

Monasterio encaramado en un risco: tres terrazas escalonadas unidas por escalinatas, la iglesia en lo alto
y, excavadas en la roca, cuevas con ermitas, un osario, un archivo secreto y el relicario.

## Adaptación a la pendiente (decisión)

El jigsaw no sabe hacia dónde sube la ladera (la rotación es aleatoria) y `beard_thin`/`beard_box` solo
rellenan bajo la base de cada pieza o hunden el terreno alrededor. Por eso el monasterio **trae su propio
risco**: una sola plantilla rígida de 59 × 88 bloques en planta que incluye el macizo de roca desde las
cuevas (y = 0) hasta cada terraza, con faldón de derrubios irregular alrededor, y aire explícito sobre las
terrazas para que la ladera no las entierre.

- `terrain_adaptation: none`: la plantilla define todo su volumen; fuera de ella el terreno queda intacto.
- `start_height: -25` con proyección a `WORLD_SURFACE_WG`: la terraza baja (y = 24 de la plantilla)
  queda a ras del terreno en el centro de la huella.
- En llano el risco se levanta sobre el prado (12 bloques hasta el claustro); en ladera, cuesta arriba
  la plantilla corta el monte como un desmonte y cuesta abajo deja a la vista la roca del risco.
- Caras del macizo que dan a una terraza: sillería con contrafuertes; caras exteriores: roca natural
  (piedra, andesita, toba y canto) con talud.
- Una sola pieza: el recorrido a pie de la auditoría cubre el monasterio entero desde la entrada.

Biomas: `meadow` y `grove`. Rareza: `spacing` 250 / `separation` 190 chunks (una cada ~3.000-5.000 bloques).

## Niveles (coordenadas de plantilla; la entrada está en z = 0, se sube hacia z creciente)

| Nivel | Suelo (y) | z | Contenido |
|---|---|---|---|
| Camino | 24 | 0-5 | camino empedrado con faroles; conector de entrada |
| T0 Atrio | 24 | 6-27 | portería (porteros y limosnas), atrio, cementerio, hospedería en ruinas, escalinata a T1 |
| T1 Huerto/refectorio | 30 | 28-49 | huerto en dos bancales con acequias, cobertizo, refectorio, cocina; bodega debajo (y 24) |
| T2 Claustro | 36 | 50-72 | claustro con pozo, dormitorio con celdas, biblioteca, sala capitular |
| Iglesia | 37-38 | 73-87 | nave con columnas, coro, presbiterio elevado, sacristía en la base del campanario |
| Campanario | 38-70 | 73-79 | escala interior, rellano, campana |
| Cripta | 30 | 75-85 | bajo el presbiterio: sepulcros, generador de zombis, puzle 1 |
| Cuevas | 13 | 20-86 | gruta de los eremitas, 3 ermitas, cueva de arañas, osario, archivo, catacumbas, relicario (y 5) |

## Recorrido del jugador

1. Camino → arco de la portería → atrio. A los lados: portería (barril), sala de limosnas, cementerio y
   la hospedería derruida (cofre entre escombros).
2. Escalinata de 6 peldaños → T1. Huerto (cobertizo con cofre), refectorio y cocina (barril). Escalera
   de la cocina a la **bodega** (barril). En un rincón de la bodega, tras las cubas, una trampilla y una
   escala bajan a la **despensa secreta del cillerero** (sala oculta, cofre medio).
3. Escalinata → T2. Claustro con galerías y pozo; biblioteca (cofre) con un **hueco tras una estantería**
   que da a una escala hasta el **escritorio oculto** bajo cubierta (cofre medio); sala capitular;
   dormitorio con celdas (dos cofres de celda y el del prior).
4. Iglesia: nave, coro, presbiterio. Sacristía en la base del campanario (cofre) y escala hasta la
   campana (cofre en el rellano).
5. Escalera de la nave lateral a la **cripta** (generador de zombis, oscura). **Puzle 1**: dos palancas
   encendidas con sus lámparas mantienen cerrada una lápida en un nicho; el letrero dice que hay que
   apagar las luces de los difuntos. Con las dos apagadas, los pistones retiran la lápida.
6. Pasadizo secreto de 17 peldaños hasta la **gruta de los eremitas** (y 13). Desde la gruta:
   ermitas 1 y 2 (cofres de ermita), pasillo a la ermita 3 con **trampa 1** (cable trampa → dos
   dispensadores de flechas, como el templo de la jungla), cueva de arañas (generador de arañas de cueva,
   cofre menor) y **osario** (generador de esqueletos).
7. **Puzle 2** en el osario: tres palancas en tres nichos y una puerta de hierro. El letrero: «velan
   el primero y el último; el del medio duerme». Solo con 1 y 3 subidas y 2 bajada se abre el
   **archivo secreto** (dos cofres ricos).
8. Del archivo, escalera a las **catacumbas** (generador de zombis, cofre en un nicho) y la antecámara con
   la **trampa 2** (losas de presión sobre dispensadores con pociones arrojadizas de veneno y flechas,
   como las losas del templo del desierto pero sin TNT). Al fondo, el **relicario**: guardián con nombre
   y cofre premium sobre el altar.

## Redstone (todo estable al colocarse)

- Puzle 1 (OR): palanca encendida → bloque con potencia fuerte → polvo en una cámara oculta del muro →
  pistones pegajosos **extendidos** que sostienen la lápida. Las lámparas están junto al bloque de cada
  palanca. Al colocarse, todos los estados son coherentes (palancas `powered=true`, lámparas `lit=true`,
  polvo con su nivel, pistones extendidos con su cabeza): cualquier actualización los deja igual.
- Puzle 2 (Y con negación): palanca 1 y 3 → antorcha (inversor) que se apaga; palanca 2 → polvo; las
  tres salidas se suman en una línea de polvo que alimenta el bloque de la antorcha final, que abre la
  puerta. Estado inicial coherente: antorchas 1 y 3 encendidas, línea con potencia, antorcha final
  apagada, puerta cerrada.
- Trampas: todo sin potencia al colocarse (gancho y cable sin activar, losas sin pulsar).
- La comprobación propia del módulo recalcula los niveles de polvo, el estado de antorchas, pistones,
  lámparas y puertas a partir de las palancas y exige que coincidan con lo colocado.

## Generadores y guardián

- Zombi: cripta y catacumbas. Esqueleto: osario. Araña de cueva: cueva de arañas.
  Todos en zonas oscuras de mazmorra; ninguno en la superficie habitada.
- Guardián: esqueleto «Fray Tenebrio, guardián del relicario» con espada de hierro, casco de oro y
  peto de cota de malla, 40 de vida, `PersistenceRequired`, botín de equipo con probabilidad baja.

## Habitantes

Tres monjes (aldeanos con profesión fija): clérigo (soporte de pociones en la sacristía), bibliotecario
(atril de la biblioteca) y granjero (compostador del cobertizo). Camas en las celdas.

## Estado (80-85 % en buen estado)

Ruinas con sentido: hospedería sin tejado con muros caídos, tramo del muro del cementerio caído,
cobertizo con el tejado hundido, esquina noroeste de las galerías del claustro hundida con escombros,
dos celdas del dormitorio sin techo, media cubierta de la sala capitular caída, esquina rota del
campanario y huecos en los pretiles. Procesador: ladrillo de piedra agrietado (8 %) y musgoso (8 %),
canto musgoso (15 %). El módulo calcula la proporción de huella en ruinas (objetivo 15-20 %).

## Botín (solo vanilla; el grupo extra de cada cofre lleva `solo_sin_lootr`)

| Tabla | Dónde | Contenido |
|---|---|---|
| `menor` | portería, limosnas, hospedería, cocina, cobertizo, campanario, cueva de arañas | pan, manzanas, velas, papel, semillas, pepitas de hierro, alguna esmeralda |
| `bodega` | bodega | miel, bayas, manzanas, frascos, azúcar, trigo |
| `celda` | celdas | velas, libro y pluma, papel, pan, cuerda |
| `biblioteca` | biblioteca | libros, papel, tinta, plumas, brújula, mapa vacío, libro encantado raro |
| `oculto` | despensa secreta, escritorio, celda del prior, sacristía | esmeraldas, oro, libro encantado, manzana dorada rara |
| `ermita` | ermitas | esmeraldas, amatista, libros encantados de nivel bajo, lingotes de oro |
| `archivo` | archivo secreto | libros encantados (10-20), esmeraldas, diamante raro, etiqueta, frascos de experiencia |
| `catacumba` | catacumbas | huesos, oro, hierro, armadura de hierro encantada baja, manzana dorada |
| `premium` | relicario | 90 % `premium_vistoso` (objetos con nombre, encantamientos moderados, adornos de armadura, discos), 10 % `premium_fuerte` (equipo de diamante encantado 20-30 o manzana dorada encantada); más un grupo de valores y el extra sin Lootr |

Nada de netherita en equipo ni élitros. Los nombres de objeto y del guardián usan claves de traducción
`heraldia.unicas.monasterio.*` con respaldo en español.

## Contraste con el criterio de Alberto

- Escaleras completas y sin saltos: todo desnivel es de peldaños o escala; la auditoría recorre a pie.
- Ninguna puerta sin salida: la auditoría comprueba las dos caras de cada puerta (las secretas, abiertas).
- Muebles contra muro, sillas con respaldo hacia fuera, faroles colgados con cadena.
- Simetría en iglesia, claustro, portería y refectorio; cada estancia con su función.
- Nada flotando: comprobación propia de bloques sueltos (todo debe tocar el macizo).

## Comprobado

- Auditoría propia (condición para generar): estados de redstone coherentes al colocarse, las 4 y 8 combinaciones de
  palancas de los dos puzles (solo la solución abre), ganchos y losas con su dispensador, nada flotando, ruinas al 15,7 %
  de la huella, cofres con tabla existente, generadores y guardián. `lint.py` sobre la vista con las puertas secretas
  abiertas: recorrido a pie desde la entrada hasta cada puerta, cofre, mueble y escala; jigsaw intacto.
- Servidor dedicado 26.3 (`prueba_servidor.py`): la plantilla se coloca; pistones extendidos, lámparas encendidas,
  antorchas y puerta en su estado; generador y guardián presentes; el puzle 1 abre solo con las dos palancas
  apagadas y el 2 solo con 1 y 3 subidas.
- Sin comprobar en el juego: que las trampas disparen al pisarlas o cruzarlas, que los generadores saquen mobs, el
  encaje en laderas reales y el aspecto (faltan capturas de Alberto).

## Planos y renders

En `docs/unicas/monasterio/`: planos por nivel en texto (`planos.txt`, celdas alcanzables marcadas) y
renders isométricos (`exterior.png`, `cuevas.png`).
