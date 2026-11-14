# Fortaleza de hielo (`heraldia:unicas/fortaleza_hielo`)

Fortaleza de hielo compacto y hielo azul sobre un zócalo de piedra nevada, en picos de hielo, llanura nevada y taiga
nevada. Abandonada: la guardan esqueletos glaciales (strays) y su antiguo señor, **el Rey Escarcha**. Una sola pieza
rígida diseñada a mano (51 × 65 bloques de planta, 46 de alto) y una sola variante.

## Adaptación al terreno (sótanos)

Las criptas y la cámara del tesoro no se hunden en el terreno: están **dentro de un zócalo macizo de 10 bloques** sobre el
que se alza la fortaleza (y = 0 a 10 de la plantilla). Así la caja de la pieza empieza a ras de suelo y `beard_thin` solo
rellena por debajo, sin excavar el terreno vecino. Se sube al patio por una escalinata de 11 peldaños encajada entre dos
pretiles (con media losa de acceso en el primer escalón, porque la pieza rígida queda un bloque por encima del suelo).

## Plantas por nivel (coordenadas de la plantilla: x de oeste a este, z de norte a sur; «pie» = altura de los pies)

| Nivel | Pie | Contenido |
|---|---|---|
| Cámara del tesoro | 1 | antecámara, pasillo de la trampa de placa, cámara final con el cofre premium |
| Criptas | 6 | vestíbulo, pasillo del cable trampa, osario (generador de strays), sala de ofrendas (generador de esqueletos), cripta del Rey (guardián) |
| Patio y planta baja | 11 | patio con fuente helada, puerta fortificada, barracones, cocinas, perrera, galería de esculturas, gran salón con trono, panteón, sala oculta del rey |
| Adarve | 20 | camino de ronda sobre las cuatro murallas, sala del rastrillo, plantas medias de las torres |
| Atalayas | 26 | sala alta de las cuatro torres, bajo las agujas |

Planos generados con las celdas alcanzables: `docs/unicas/fortaleza_hielo/plantas.txt`; renders: `docs/unicas/fortaleza_hielo/*.png`.

## Recorrido del jugador

1. Escalinata norte → puerta fortificada (paso de 5 de ancho bajo el rastrillo alzado) → patio.
2. Patio: a poniente los **barracones** (2 cofres) y la **galería de esculturas de hielo** (caballero, lobo, oso, dragón; 1 cofre
   tras la última escultura); a levante las **cocinas** (hogueras bajo el tiro del tejado, ahumador, 1 cofre, toneles) y la
   **perrera** (corrales con tres lobos de las nieves, 1 tonel); al sur el **gran salón** con el trono de hielo.
3. Torres de esquina con escaleras de mano hasta el adarve y la sala alta. El adarve une las cuatro torres y la **sala del
   rastrillo** (1 cofre). La atalaya noreste guarda 1 cofre. Las torres del sur se entran por la galería y por el panteón.
4. **Sala oculta del rey** (puzle 1): de las dos hornacinas que flanquean el trono, la derecha es una puerta de pistones. Se
   abre bajando la palanca que hay en el muro del fondo, a tres bloques. Dentro, el cofre `tesoro_real`.
5. **Panteón** (a levante del salón) → escalera a las **criptas**: vestíbulo → pasillo con **cable trampa** (4 dispensadores
   con flechas en los muros) → osario al norte (**generador de strays**, foso de nieve polvo, 1 cofre) y sala de ofrendas al
   sur (**generador de esqueletos**, derrumbe, 1 cofre) → **cripta del Rey** (guardián con nombre).
6. **Puerta secreta de la cripta** (puzle 2): en el muro oeste hay dos hornacinas; la del sur es otra puerta de pistones. La
   palanca está escondida entre el muro y un pilar (solo se ve de lado). Tras ella, una escalera baja a la **cámara del
   tesoro**: antecámara → pasillo de un bloque con **placa de presión y dos dispensadores** → cámara final con el cofre premium.

## Mecanismos (todos funcionan al colocarse, sin actualizaciones de bloque)

- Puertas de pistones: dos pistones pegajosos **ya extendidos** sujetan los dos bloques de la hornacina; la palanca está
  **encendida** de serie y alimenta los pistones (directamente un polvo en cruz encima de un bloque que queda débilmente
  alimentado). Todo el estado guardado es coherente (palanca encendida, polvo a 15, pistones extendidos con su cabeza), así
  que nada cambia al generarse. Al apagar la palanca los pistones retraen los bloques al interior del muro y la hornacina se
  vuelve paso; volver a encenderla cierra (el paso queda abierto desde dentro si nadie toca la palanca).
- Trampas: cable trampa (ganchos `attached`, sin alimentar) y placa de piedra en reposo; los dispensadores, sin disparar,
  están junto al bloque que alimenta el gancho o junto a la placa. Foso de nieve polvo de un bloque de hondo junto al generador.
- La auditoría del módulo simula la redstone: estados guardados = estados calculados, pistones extendidos ⇔ alimentados, y
  que al pisar la placa o el cable los dispensadores reciben señal y al apagar cada palanca se abre la puerta.

## Generadores y guardián

- Osario: generador de strays; sala de ofrendas: generador de esqueletos. Ambos a oscuras (luz de bloque 0 calculada).
- **El Rey Escarcha**: stray con `PersistenceRequired`, nombre traducible, 40 de vida, arco con Poder II, casco de hierro y
  cota de malla (probabilidad de soltar el equipo moderada).
- Sin aldeanos ni gólems: la fortaleza está abandonada. Los lobos de las nieves de la perrera son la única vida pacífica.

## Hielo y luz

Solo se usa hielo compacto y hielo azul (no se derriten). La auditoría calcula la luz de bloque y falla si hay hielo normal
o capas de nieve con luz > 11 o si un generador recibe luz. Ninguna superficie superior expuesta es bloque de nieve
(los picos de hielo del bioma nacen sobre bloques de nieve).

## Estado (80-85 % en buen estado)

Procesador de degradación: ladrillos de piedra agrietados, almenas caídas y parches de nieve en el hielo compacto. Ruinas
hechas a mano: punta de la aguja noreste caída, brecha en el parapeto este, hueco en el tejado de la perrera con escombros,
estatua de la fuente rota y derrumbe en la sala de ofrendas. La auditoría estima la proporción de superficie dañada.

## Cofres y botín (solo vanilla, sin netherita en equipo ni élitros)

Cada tabla lleva un grupo extra `solo_sin_lootr` (con Lootr cada jugador recibe solo la parte modesta).

| Cofre | Dónde | Botín |
|---|---|---|
| `barracones` ×2 | barracones | pan, flechas, cuero, pepitas de hierro, armadura de cuero gastada |
| `cocina` | cocinas | carne cocinada, estofados, bayas, carbón |
| `perrera` (tonel) | perrera | huesos, correas, cuero, alguna etiqueta |
| `garita` | sala del rastrillo | flechas, ballesta gastada, antorchas, catalejo raro |
| `atalaya` | sala alta noreste | mapa, brújula, catalejo, esmeraldas |
| `galeria` | galería de esculturas | hielo compacto, lapislázuli, velas, libros |
| `cripta` ×2 | osario y ofrendas | huesos, pepitas de oro, hierro, esmeraldas, libro encantado raro |
| `tesoro_real` | sala oculta del rey | oro, esmeraldas, diamante, libro encantado, manzana dorada |
| `premium` | cámara del tesoro | 90 %: objetos con nombre y encantamientos moderados, adornos de armadura, discos; 10 %: espada o peto de diamante bien encantados, manzana encantada o tótem |

## Contraste con el criterio de diseño

- Escaleras completas y sin saltos (auditoría de recorrido); ninguna puerta sin salida; cada sala alcanzable (las ocultas,
  con su mecanismo abierto).
- Muebles contra los muros; centros libres salvo mesas con sillas de respaldo hacia fuera.
- Faroles colgados de techo o cadena; nada de agua.
- Simetría en la puerta fortificada, el gran salón, las torres y las hornacinas; cada elemento tiene función
  (hornacinas = puertas o señuelo del puzle, pilares = escondite de la palanca).
