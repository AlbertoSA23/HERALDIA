# Torre de mago (`heraldia:unicas/torre_mago`)

Torre esbelta de piedra de pizarra (diámetro 17, unos 63 bloques sobre el suelo hasta la punta del tejado cónico)
con un torreón adosado y dos sótanos. Bosque oscuro y jardín pálido (`#heraldia:oscuro`), una cada ~4.000 bloques
(rejilla 250/190 chunks). Una sola plantilla rígida (`unicas/torre_mago/torre`, 27 × 79 × 25), diseñada a mano.

Planos con celdas alcanzables: [`torre_mago/plantas.txt`](torre_mago/plantas.txt). Renders: [`exterior.png`](torre_mago/exterior.png)
y [`cortes.png`](torre_mago/cortes.png) (un corte por planta). Se regeneran con `python3 tools/gen/unicas/torre_mago/planos.py`.

## Adaptación al terreno
- `start_height` −14 y `terrain_adaptation: none`: el suelo del vestíbulo queda a ras del terreno y los sótanos bajo
  tierra sin que el beard excave un cráter alrededor (con `beard_thin` la caja que baja hunde el terreno).
- Terraza circular de 12 bloques de radio con cimiento de 4 bloques y 5 bloques de aire encima: absorbe pendientes suaves
  (en cuesta se ve como un zócalo o un desmonte, con sentido). Muro bajo con la entrada al norte.

## Plantas (pies a la altura indicada de la plantilla)
| Nivel | Uso | Contenido |
|---|---|---|
| Sótano 2 (y 2) | Cámara del tesoro | Corredor con losa trampa, cámara con 4 columnas, **cofre premium**, cofre `tesoro`, guardián |
| Sótano 1 (y 8) | Experimentos fallidos | Vestíbulo inferior, celdas con barrotes, ala oeste (trampa de hilo), ala este (arañas), ala sur (cráter), puerta de hierro con puzle |
| Planta 0 (y 14) | Vestíbulo | Puerta norte, alfombra, estandartes, bancos, atril con el diario (pistas), barril |
| Planta 1 (y 20) | Biblioteca baja | Estanterías bajo la galería, atriles, mesa con sillas, cofre |
| Planta 2 (y 26) | Galería | Galería perimetral con barandilla sobre el atrio, dos pasarelas, cofre, **puerta secreta al estudio** del torreón |
| Planta 3 (y 32) | Laboratorio | Encimera con soportes de pociones, calderos (uno lleno), dos cofres, suelo chamuscado y ventana rota |
| Planta 4 (y 38) | Encantamientos | Mesa de encantamientos con estanterías, amatista, cofre, atril |
| Planta 5 (y 44) | Invernadero | Ventanales, arriates de musgo con plantas raras (antorchaflor, planta odre, ojos pálidos, azaleas), esporas colgantes |
| Planta 6 (y 50) | Dormitorio | Cama contra el muro, mesillas, librería, escritorio |
| Planta 7 (y 56) | Observatorio | Telescopio sobre el machón, mesa de cartografía, cofre; rendija de observación al norte en el tejado |

Escalera de caracol continua alrededor de un machón de roble oscuro, del sótano 1 al observatorio (6 peldaños por
planta, rellano de dos casillas, barandilla en el hueco de cada forjado). El sótano 2 solo se alcanza tras la puerta de hierro.

## Recorrido del jugador
Terraza → vestíbulo (el diario da las tres pistas) → escalera hacia arriba: biblioteca, galería (estantería incompleta →
estudio oculto), laboratorio (agua para el caldero), encantamientos, invernadero, dormitorio, observatorio. Hacia abajo:
sótano 1 con generadores (aldeano zombi en el pasillo de las celdas, araña de cueva en el ala este), trampa de hilo en el
ala oeste, escondrijo tras las telarañas, puzle del caldero → tramo recto → losa trampa → cámara del tesoro y guardián.

## Puzles, trampas y generadores
- **Estudio oculto (galería, oeste)**: en una hornacina, estantería cincelada con cinco libros y el sexto hueco vacío.
  Comparador → 6 de polvo → bloque de una antorcha de redstone que alimenta dos pistones pegajosos extendidos que sujetan
  dos estanterías (la puerta). Solo el hueco 6 da señal 6, que llega con 1 al final: la antorcha se apaga y los pistones
  retiran las estanterías. Cualquier otro hueco (señal 1-5) no llega. Cartel en la hornacina: «el sexto también».
- **Puerta de hierro (sótano 1)**: caldero → comparador → 3 de polvo → puerta. Solo el caldero lleno (señal 3) abre.
  Agua: caldero lleno del laboratorio (con un cubo de cualquier cofre o propio).
- **Trampa de hilo** (como en el templo de la jungla): hilo de lado a lado del ala oeste; los ganchos alimentan el muro
  y dos dispensadores con flechas disparan a la altura de la cabeza.
- **Losa trampa** (como en el templo del desierto): placa de piedra en el corredor del sótano 2 con TNT debajo; las
  losas agrietadas de alrededor avisan.
- Todo se coloca en estado coherente (pistones extendidos con su antorcha encendida, polvo a 0, comparadores apagados,
  hilos sin pisar): nada depende de actualizaciones de bloque al generarse. Comprobado en un servidor real (ver PR).
- **Generadores**: aldeano zombi (pasillo de las celdas) y araña de cueva (ala este), en zonas oscuras.
- **Guardián**: «Archimago Malvarius», evocador persistente con 48 de vida y 4 de armadura; suelta el botín de una bruja
  en vez del tótem (no regala un tótem).

## Cofres (más ricos cuanto más escondidos)
| Cofre | Dónde | Tabla |
|---|---|---|
| Barril | Vestíbulo | `vestibulo` (comida, antorchas) |
| Cofre | Biblioteca baja y galería | `biblioteca` (libros, papel; extra: libro encantado) |
| 2 cofres | Laboratorio | `laboratorio` (ingredientes, pociones sencillas) |
| Cofre | Encantamientos | `encantamientos` (lapislázuli, libros) |
| Barril | Invernadero | `invernadero` (semillas raras, musgo) |
| Cofre | Dormitorio | `dormitorio` (objetos personales) |
| Cofre | Observatorio | `observatorio` (mapas, brújulas, amatista) |
| 2 cofres + barril | Sótano 1 | `experimentos` |
| Cofre | Escondrijo tras telarañas (sótano 1) | `escondite` (oro, esmeraldas; extra: diamante, disco) |
| Cofre | Estudio oculto | `estudio` (libros encantados, diamante raro) |
| Cofre | Cámara del tesoro | `tesoro` |
| Cofre | Cámara del tesoro | `premium` |

Premium: un objeto principal, 90 % vistoso (Báculo de Malvarius, grimorio, capucha, catalejo, reloj, daga, botas con
caída de pluma, plantilla de adorno «vex», discos *strad* y *far*) y 10 % algo más fuerte (espada de diamante Filo III,
coraza de diamante Protección II, manzana de oro encantada); más oro, esmeraldas, lapislázuli, experiencia, amatista y
un elixir de regeneración. Sin netherita ni élitros. Cada cofre tiene un grupo extra marcado `solo_sin_lootr`.

## Estado (80-85 % en buen estado)
Procesador: 12 % de ladrillos de pizarra agrietados, 21 % de ladrillos de piedra con musgo o grietas en los sótanos,
10 % de piedra de pizarra con musgo en la terraza. Huecos con sentido: muro de la terraza caído al sudoeste, tejas
caídas en el sudeste del tejado (escombros en el observatorio), ventana rota y suelo quemado en el laboratorio, cráter
en el ala sur del sótano, barrote arrancado en una celda, telarañas, enredaderas y musgo pálido.

## Contraste con el criterio de diseño
- Escaleras completas y sin saltos (auditadas con el recorrido a pie); toda puerta con salida; nada inaccesible salvo las
  celdas, que se ven a través de los barrotes (una tiene el barrote arrancado).
- Muebles contra el muro sin tapar ventanas (los frentes de ventana quedan libres); centro libre (la escalera).
- Faroles colgados del forjado, cadenas con enganche, agua solo en calderos.
- Simetría en vestíbulo, biblioteca y encantamientos; cada elemento con función (bancos, atriles, arriates, telescopio).
- Sin aldeanos ni gólems: la torre está abandonada.

## Auditoría
`lint.py` (recorrido a pie desde la entrada a cada puerta, cofre y escalera; apoyos; jigsaw) con la puerta secreta
considerada abierta (`lint_open`), y `auditar()` del módulo: estado de pistones, antorcha y polvo, piezas de los puzles y
trampas, presencia del guardián. Prueba en servidor real: `tools/gen/unicas/torre_mago/prueba_redstone.py`.
