# Palacio oriental (`heraldia:unicas/palacio`)

Palacio imperial de inspiración oriental, amurallado, con tres patios sucesivos en un eje norte-sur estrictamente
simétrico. Una sola variante, diseñada a mano (`tools/gen/unicas/palacio/`), en una única pieza rígida de 81 × 123 bloques.

- Biomas: `minecraft:cherry_grove` y `minecraft:bamboo_jungle` (la jungla normal y la dispersa son del templo-pirámide).
- Rareza: `spacing` 250 / `separation` 190 chunks (una cada ~3.000-5.000 bloques).
- Adaptación: `beard_box`. Todo el palacio se apoya en un zócalo de piedra (y=0) y **no tiene sótanos bajo el terreno**:
  la «cámara secreta bajo el salón del trono» está dentro de la plataforma escalonada de tres gradas (y=1-7), por
  encima del suelo. Así la caja de la pieza empieza en el zócalo, el terreno se rellena por debajo y nada hunde el
  entorno. El volumen interior se rellena de aire para que una ladera no asome dentro de los patios.
- Diferencia con las aldeas «cerezos»: allí casas sueltas de cerezo con tejados de pagoda en torres; aquí un único
  recinto ceremonial de muros rojos, terrazas de mármol (cuarzo), tejados amarillos imperiales (mosaico de bambú) en el
  eje y verdes vidriados (prismarina) en los edificios secundarios, con estanque, puerta de luna y pagoda de cinco pisos.

## Plantas (coordenadas de plantilla: x este, z sur desde la puerta, y=1 pavimento, pies a y=2)

| Zona | Huella | Notas |
|---|---|---|
| Escalinata y muralla | z=0-4, muralla de 3 de grueso en todo el perímetro, y=2-10 | zócalo de ladrillo de piedra, cuerpo rojo, albardilla amarilla |
| Puerta del Mediodía | x=32-48, z=2-8, macizo y=1-9 | paso de 3 × 4, dos cuerpos de guardia con escalera de mano al pabellón superior (y=10) |
| Patio exterior | z=5-27 | río de agua dorada (z=15-17) con tres puentes arqueados, cerezos, linternas de piedra |
| Puerta de la Armonía | muro z=28-30, salón x=28-52, z=26-32 sobre zócalo | paso central con columnas; sala de guardia (oeste) y despensa (este) |
| Patio del trono | z=31-79 | biblioteca (oeste, x=4-17) y tesorería (este, x=63-76), simétricas por fuera |
| Plataforma del trono | gradas x=22-58/24-56/26-54, z=36-76/38-74/40-72; pies 4, 6 y 8 | escalinatas en el eje (delante y detrás) |
| Salón del trono | x=29-51, z=44-66, pies 8, doble alero | trono sobre estrado, biombo, pasillo trasero, muro trasero de 3 |
| Bajo el salón (dentro de la plataforma) | x=28-52, z=42-70, pies 2-5 | antecámara, pasillo de trampas, sala de los guerreros, cámara del tesoro |
| Muro del jardín | z=80-82 | puerta de luna (círculo de radio 3) en el eje y dos portillos |
| Jardín | z=83-119 | estanque (x=27-53, z=88-102) con puente y pabellón del lago; pagoda (x=35-45, z=106-116), cuatro pabellones de las concubinas (x=4-16 y x=64-76) |

## Recorrido del jugador
1. Escalinata → Puerta del Mediodía. Cuerpos de guardia a ambos lados del paso (cofre `guardia` en cada uno); escaleras de mano al pabellón de la puerta (barril `torre`).
2. Patio exterior: puentes sobre el río; la brecha de la esquina noreste es la parte en ruinas.
3. Puerta de la Armonía: sala de guardia (cofre `guardia`) y despensa (barriles `almacen`).
4. Patio del trono: biblioteca (cofre `biblioteca`, estudio secreto) y tesorería (barriles `tesoreria_menor`, cámara acorazada con puerta de hierro y botón, cofre trampa `tesoreria`). Escalinata al salón del trono (cofre `salon` en el pasillo trasero).
5. Detrás del biombo, dos columnas gemelas con palanca: una abre la puerta secreta, la otra dispara una flecha. La puerta da a un pozo con escalera de mano que baja al interior de la plataforma.
6. Antecámara → pasillo de las trampas (dos cables trampa con dispensadores enfrentados) → sala de los guerreros de terracota (dos generadores, a oscuras) → cerradura de dos palancas → **cámara del tesoro** bajo el trono: guardián con nombre, cofre `premium` y dos cofres `boveda`.
7. Puerta de luna → jardín: pabellón del lago (barril `jardin`), cuatro pabellones de las concubinas (cofre `pabellon` en cada uno; el del sureste en ruinas), pagoda de cinco pisos con escaleras de mano y cofre `pagoda` arriba.

## Puzles (todo colocado en estado estable: nada espera una actualización de bloque)
- **Estudio secreto de la biblioteca**: muro de estanterías al norte con una puerta de dos bloques movida por dos pistones
  pegajosos escondidos tras una columna de estanterías. Cerrada = pistones extendidos y alimentados por una palanca
  encendida en la cara de la columna (bloque de la columna con energía fuerte → pistón superior directo, inferior por
  cuasiconectividad). Apagar la palanca abre; encenderla cierra.
- **Puerta secreta tras el trono**: el mismo mecanismo en el muro trasero, oculto tras la columna izquierda. La columna
  derecha, gemela, lleva una palanca señuelo (apagada) cuyo bloque alimenta un dispensador con flechas al pie de la columna.
- **Cerradura de la cámara**: la puerta de dos bloques la mueven dos pistones independientes (el bloque bajo hacia el
  oeste y el alto hacia el este), cada uno con su palanca; solo se abre con las dos apagadas.

## Trampas
- Pasillo de trampas (bajo el salón): dos cables trampa; cada gancho da energía fuerte al muro en el que se apoya y
  ese bloque activa un dispensador a la altura de la cabeza que dispara a través del cable (como en el templo de la jungla).
- Cámara acorazada de la tesorería: placa de presión delante del cofre trampa, con dos dispensadores a ras de suelo a
  sus lados que disparan sobre la placa.
- Palanca señuelo del salón del trono (arriba).

## Enemigos
- Sala de los guerreros: dos generadores (zombi y esqueleto), sin luz.
- Cámara del tesoro: guardián «Comandante de la Guardia Imperial» (vindicador con hacha de hierro y coraza de cota de
  malla, 40 de vida, `PersistenceRequired`, sin soltar el equipo).

## Estado (80-85 % en buen estado)
Ruina con sentido: brecha en la esquina noreste de la muralla con escombros, albardilla caída en el muro este del
jardín, pabellón de las concubinas del sureste medio hundido (tejado y muro abiertos, escombros, musgo), linterna de
piedra derribada y tejas sueltas en la Puerta de la Armonía. Además un procesador desgasta al azar la piedra (ladrillo
agrietado y musgoso, andesita). La auditoría del módulo mide la superficie expuesta y exige 15-20 % de ruina.

## Botín (`heraldia:unicas/palacio/<tabla>`; el grupo extra de cada cofre va marcado `solo_sin_lootr`)
| Tabla | Dónde | Contenido |
|---|---|---|
| `guardia` | 3 cofres en cuerpos de guardia | comida, flechas, antorchas, pepitas de hierro; extra: lingote de hierro, esmeralda |
| `almacen`, `torre`, `jardin` | barriles | comida, cuerda, velas, papel; poco valor |
| `pabellon` | 4 pabellones | tintes, velas, pétalos, fragmentos de amatista, pepitas de oro, esmeraldas |
| `biblioteca` | biblioteca | papel, libros, tinta, plumas, mapa; raro: libro encantado |
| `tesoreria_menor` | 2 barriles de la tesorería | pepitas de oro y hierro, cobre, alguna esmeralda |
| `salon` | pasillo del salón del trono | velas, oro, esmeraldas, zanahorias doradas, catalejo |
| `tesoreria` | cofre trampa acorazado | lingotes de oro, esmeraldas, oro en bruto; diamante poco probable |
| `biblioteca_secreta` | estudio secreto | libros encantados (niveles 10-20), botellas de experiencia, lapislázuli |
| `pagoda` | último piso de la pagoda | perlas de ender, amatista, libro encantado, manzana dorada |
| `boveda` | 2 cofres de la cámara | diamantes (1-3), oro, esmeraldas, equipo de hierro encantado |
| `premium` | cofre de la cámara | joya: 90 % vistosa (objetos de oro y hierro con nombre y encantamientos 15-30) y 10 % fuerte (diamante encantado, manzana dorada encantada, tótem); adornos de armadura, discos, riqueza |

Nada de netherita en equipo, plantilla de mejora de netherita ni élitros.

## Contraste con el criterio de diseño
- Simetría axial en muralla, puertas, patios, plataforma, salón, biblioteca/tesorería (iguales por fuera), pabellones y pagoda; las únicas asimetrías son los mecanismos ocultos y la ruina.
- Ninguna escalera sin terminar: escalinatas continuas de un bloque por paso; las escaleras de mano llegan siempre a un suelo.
- Muebles contra los muros, centros libres; faroles colgados con cadena o de pie sobre piedra; agua siempre en vasos cerrados.
- Cada sala tiene función reconocible (guardia, despensa, biblioteca, estudio, tesorería, cámara acorazada, salón, aposentos, pagoda).
- Auditoría como condición para generar: `lint.py` (con los mecanismos en estado abierto) más las comprobaciones del módulo (redstone, recorrido con todo cerrado, nada flotando, porcentaje de ruina).
