# Castillo (`heraldia:unicas/castillo`)

Fortaleza medieval de 100 x 100 bloques en llanuras, llanuras de girasoles y praderas, una cada 3.000-5.000 bloques
(rejilla configurable, `spacing` 250 / `separation` 190 chunks). Una sola variante, diseñada a mano.
Código: `tools/gen/unicas/castillo/` (piezas comunes en `tools/gen/unicas/_comun/piezas.py`) · Planos por nivel: [`castillo/planos.md`](castillo/planos.md) · Renders: `castillo/*.png`.

## Adaptación al terreno
- Dos plantillas rígidas: el castillo (x, z 0..99, y 0..27; terreno en y=5, pies a y=6) y la mazmorra (48 x 56 x 16)
  bajo la torre del homenaje, unidas por un jigsaw vertical en el machón del caracol (`down_south` / `up_south`, alineado).
- `start_height` -6 con proyección a `WORLD_SURFACE_WG`: la capa y=5 de la plantilla coincide con la superficie, y foso y
  cimientos (y 0..4) quedan enterrados. `beard_thin` centra su núcleo en la base de cada pieza: en superficie el castillo
  solo hunde el borde 1 bloque como mucho, y la mazmorra (techo 6 bloques bajo el patio, 13 de alto) no llega a la superficie.
- Toda la huella del castillo bajo la superficie y toda la caja de la mazmorra van con bloques explícitos: lo que el
  adaptador excava dentro de la caja se rellena con la plantilla. Patio y orillas llevan aire explícito hasta 3-4 bloques.
- Sin verificar en generación real: las cavidades que el adaptador pueda abrir alrededor de la mazmorra (fuera de su caja).

## Plantas
**Exterior y muralla.** Orilla de hierba (anillo 0-3) con escollera de piedra, foso de agua de 6 de ancho y 3 de hondo,
muralla de 3 de grueso con adarve a y=17 y almenas. Cuatro torres redondas en las esquinas (planta baja con puerta al patio,
planta del adarve con puertas a los dos lienzos, terraza almenada, escaleras de mano) y dos bastiones a media muralla
este y oeste por los que pasa el adarve. Escaleras de piedra del patio al adarve junto a los muros oeste y este.
**Barbacana (sur).** Puente levadizo tendido sobre el foso (falta un tablón), arco con rastrillo alzado colgado de cadenas
del torno de la sala alta, cuerpo de guardia y almacén a los lados del paso, sala del torno con camas y azotea; dos
cubos flanquean la entrada.
**Patio de armas.** Camino de la puerta a la torre del homenaje, pozo cubierto en el centro, caballerizas con cinco cuadras
(oeste), herrería con forja, yunque y pilón (este), capilla con bancos, altar y vidrieras (noreste), huerto con acequia junto
a la cocina (noroeste), liza con dianas y estafermos (suroeste), farolas.
**Torre del homenaje** (40 x 32, muros de 3, cuatro torreones): planta baja con gran salón de doble altura (mesa larga,
mesa alta bajo la tribuna, chimenea, escalera principal a la tribuna), cocina, despensa y bodega al oeste, armería y cuartel
al este. Planta alta: estudio, biblioteca y antecámara al oeste; alcoba del señor y solana al este, unidas por la tribuna.
Caracol de losas (3 x 3) en un hueco cerrado desde la mazmorra (y=-13) hasta la azotea (y=22), con salidas al salón,
a la antecámara y a la azotea.
**Mazmorra** (pies a y=-13): cuerpo de guardia al pie del caracol; al este, pasillo con ocho calabozos (puertas de hierro
abiertas); al oeste, la cripta; al norte, la cisterna con estanques, puente e isla; al noreste, la falsa tesorería; al sur,
el pasillo de las saetas y la sala del guardián (bóveda de 7, pilares, trono); tras ella, la cámara del tesoro.

## Recorrido del jugador
Puente → barbacana (guardia, almacén, sala del torno, azotea) → patio (caballerizas, herrería, capilla, pozo, huerto, liza,
torres y adarve completo) → torre del homenaje (salón, cocina, despensa, bodega, armería, cuartel; escalera a la tribuna y a
la planta alta) → caracol → mazmorra: guardia → calabozos → paso a la falsa tesorería → cisterna → cripta → guardia
(circuito cerrado) → pasillo de las saetas → sala del guardián → acertijo → cámara del tesoro.
La auditoría lo comprueba entero con las salas secretas abiertas: cada celda alcanzada tiene vuelta, y cada cofre, barril,
mueble de trabajo, palanca, generador, puerta (por los dos lados) y escalera de mano está al lado de una celda alcanzable.
Con los mecanismos cerrados, el gabinete secreto, la cámara del tesoro y el nicho no se alcanzan.

## Puzles, trampas, generadores y guardián
- **Puerta secreta del estudio** (planta alta): en el rincón noroeste, una palanca en el suelo; al accionarla, dos librerías del
  muro oeste se retiran al rincón (pistones pegajosos extendidos que alimenta una antorcha; la palanca la apaga). Detrás, un
  pasadizo en el grueso del muro oeste (saeteras y antorchas) lleva al **gabinete secreto** del torreón suroeste.
- **Acertijo de las tres palancas** (sala del guardián): tres palancas bajo estandartes verde, rojo y negro; los estandartes del
  castillo son rojos. La roja apaga la antorcha de una puerta secreta igual en el rincón noreste y abre la cámara del tesoro;
  la verde y la negra disparan tres dispensadores de flechas cada una contra quien tira.
- **Pasillo de las saetas**: cable trampa con seis dispensadores (templo de la jungla).
- **Falsa tesorería**: cofre en un estrado y placa de presión delante con cinco dinamitas bajo el suelo (templo del desierto).
- **Nicho oculto**: tras ladrillos agrietados al fondo del segundo calabozo sur (hay que picar).
- **Generadores**: zombi (calabozo con los barrotes arrancados), esqueleto (cripta), araña (isla de la cisterna).
- **Guardián**: Sir Aldric, el Castellano Maldito (zombi con nombre traducible, 60 de vida, 5 de ataque, 0,4 de resistencia al
  empuje, yelmo y grebas de hierro, cota y botas de malla, espada de hierro; `PersistenceRequired`).
- Todo en reposo es estable: antorchas encendidas, pistones extendidos con su cabeza, palancas y polvo apagados.
- Sin aldeanos ni gólems: el castillo está abandonado y tomado por muertos vivientes.

## Botín (`heraldia:unicas/castillo/<tabla>`, solo vanilla; cada tabla con grupo extra `solo_sin_lootr`)
| Tabla | Dónde | Contenido |
|---|---|---|
| `menor` | almacén de la puerta, torres, bastiones, cuartel, falsa tesorería | comida y materiales básicos |
| `cocina` | cocina, despensa, bodega, almacén | comida cocinada y víveres |
| `armeria` | cuerpo de guardia, sala del torno, torres, armería, liza | flechas, hierro, armas y armaduras gastadas |
| `herreria` | herrería | hierro, carbón, herramientas, yunque mellado |
| `establo` | caballerizas | trigo, ronzales, silla, bardas de cuero o hierro |
| `capilla` | capilla | velas, papel, lapislázuli, libros |
| `aposentos` | estudio, biblioteca, alcoba | oro, esmeraldas, reloj, brújula, libro encantado (5-15) |
| `mazmorra` | guardia, calabozos, cripta, cisterna, falsa tesorería | huesos, pepitas, cadenas, algo de hierro y oro |
| `oculto` | fondo del pozo, gabinete secreto, nicho, cámara del tesoro | oro, esmeraldas, diamante raro, libro (10-20), perlas |
| `premium` | cámara del tesoro | ver abajo |

**Premium**: 3-4 objetos vistosos (Espada del Castellano, Yelmo de la Guardia, Arco del Montero con encantamientos 10-25;
Escudo de Heraldia; Llave de la Cámara; adornos centinela, salvaje, costero y anfitrión; discos 13, cat, mall y strad; oro,
esmeraldas, frascos de experiencia, barda de oro) y una joya: 90 % vistosa (Corona del Señor, Reloj de la Torre, Catalejo del
Vigía, etiqueta, disco Pigstep, manzanas de oro) y 10 % fuerte (manzana encantada, Hoja de Aldric o peto de diamante 20-30,
3-5 diamantes, libro de nivel 30). Sin netherita ni élitros.

## Ruina (83 % en buen estado)
Torre noreste desmochada (sin terraza, suelo alto hundido en el centro, enredaderas, escombros dentro y al pie), parapeto
norte sin almenas junto a ella, tejado de las caballerizas hundido con telarañas y viga caída, vidriera rota en la capilla,
tablón perdido en el puente, telarañas en bodega y mazmorra; y un procesador que pone musgo (15 %) y grietas (10 %) en los
ladrillos de piedra y musgo (20 %) en el adoquín. `auditoria.ruin_share` estima un 17 % de la superficie vista en mal estado.

## Contraste con el criterio de Alberto
Escaleras completas sin saltos (losas de media altura en el caracol, escaleras de bloque con su relleno); ninguna puerta sin
salida ni sala inaccesible (auditado); muebles contra los muros y mesas con sillas de respaldo hacia fuera; faroles colgados
de techo o cadena; agua siempre contenida (foso, pozo, acequia, estanques); simetría en muralla, barbacana y torre del
homenaje; cada elemento con función (rastrillo con torno, forja con chimenea, pilón, acequia).

## Comprobaciones
- Generación: `lint.py` (apoyos, jigsaws) y `auditoria.py` (recorrido, salas ocultas, redstone en reposo, nada flotando).
- `prueba_redstone.py`: en servidor dedicado 26.3 coloca las plantillas con `/place template`, fuerza actualizaciones junto a
  antorchas y pistones, y comprueba puertas cerradas, apertura y cierre del estudio, palanca verde (dispara, no abre), roja
  (abre, no dispara), cable trampa, placa con dinamita, guardián (nombre, equipo, vida 60) y cofres.
- Pendiente de capturas en el juego de Alberto: aspecto, iluminación y adaptación al terreno en generación real.
