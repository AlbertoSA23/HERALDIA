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
  - **Salón del Jarl** (`heraldia:unicas/salon_jarl`): taiga y taigas ancestrales. Asentamiento nórdico fortificado de
    74 × 74 con empalizada de troncos, cuatro torres y puerta con sala de guardia, casa larga con hogar central, estrado y
    dos tronos, herrería, establos, astillero con un barco largo a medio hacer, casas de los guerreros, despensa y piedras
    rúnicas; tras un tapiz, la alcoba oculta del jarl. Bajo la casa larga, el túmulo de los reyes: galería de nichos,
    osario, sala de las ofrendas, el muro de las runas (puzle) y la cámara del jarl Ulfgrim, el Insepulto, con el tesoro;
    puerta secreta a la cámara del escaldo, trampas de cable y de dinamita, 3 generadores y 18 cofres.
    Diseño: [docs/unicas/salon_jarl.md](docs/unicas/salon_jarl.md).
  - **Santuario druídico** (`heraldia:unicas/santuario`): bosque de abedules y bosque de abedules antiguo. Un claro
    rodeado de menhires alrededor de un abedul sagrado enorme, cuyo tronco hueco guarda una escalera de caracol hasta una
    plataforma bajo la copa y hasta las raíces; cabañas redondas de los druidas (tras un tapiz, la alcoba oculta del
    archidruida), huerto de hierbas con colmenas, estanque de piedra y observatorio de piedras alineadas. Bajo el árbol: la
    sala de las raíces, la biblioteca con una estantería secreta al archivo, el herbolario, un osario, el nicho de las
    ofrendas, la cámara del sol (puzle: enciende los solsticios) y la cámara del rito del archidruida Cadoc, el Marchito,
    con el tesoro; trampas de cable y de placas, 3 generadores y 18 cofres. Diseño: [docs/unicas/santuario.md](docs/unicas/santuario.md).
  - **Laboratorio del micólogo** (`heraldia:unicas/laboratorio_micelio`): campos de champiñones. Un antiguo jardín
    botánico construido entre y dentro de tres champiñones gigantes: la casa del micólogo en el sombrero del rojo grande
    (tras un tapiz, su alcoba oculta), con una escalera de caracol por el tallo; el dormitorio de los ayudantes en un
    sombrero rojo pequeño y la biblioteca de esporas en el tallo de uno pardo, con el secadero en su sombrero, todos
    unidos por pasarelas; un invernadero de cristal con cultivos raros (verruga del Nether, flor antorcha, cacao, coro),
    una destilería de pociones y el corral de los champiñocas. Bajo el micelio, galerías húmedas y luminosas: los
    criaderos, el laboratorio con un panel secreto de tallo al cepario, un pasillo con cable trampa, la sala de los
    capullos, los experimentos fallidos, la sala de los reactivos (puzle: mezcla la cura) y la cámara de la cepa madre con
    Maese Ambrosio, el Esporado, y el tesoro; trampas de cable y de placas, 3 generadores y 22 cofres.
    Diseño: [docs/unicas/laboratorio_micelio.md](docs/unicas/laboratorio_micelio.md).
  - **Mina perdida de Hondavena** (`heraldia:unicas/mina_perdida`): la primera única **subterránea**, bajo las cuevas
    exuberantes y de espeleotemas (el bioma se mira a la altura de la caverna, y ≈ 26; una cada 3.000-5.000 bloques).
    En la superficie solo asoma el castillete de madera sobre el pozo maestro; el pozo (escalera de mano y cadena del
    malacate) baja a una colonia minera de la Corona excavada en una gran caverna a y = 20: estación del pozo, almacén,
    fundición con altos hornos, casas de los mineros en la roca, herrería y carpintería, un lago subterráneo con
    embarcadero y barca, una sima con puente colgante, el cargadero con el **puzle de las agujas** (llevar la vagoneta
    por dos agujas hasta la báscula, que abre la cámara del filón), el frente viejo con las vetas a la vista y un sector
    derrumbado e inundado. El despacho secreto del capataz (tras una estantería), el alijo de los contrabandistas tras
    un tapiz, un cable trampa y una carga de dinamita olvidada, 3 generadores, el guardián Tizón, el último capataz, y
    21 cofres. La colonia está excavada en roca maciza con su propio casco: no entra agua ni lava y las cuevas vanilla
    cercanas solo ven roca irregular. Diseño: [docs/unicas/mina_perdida.md](docs/unicas/mina_perdida.md).
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
  - **Isla del corsario** (`heraldia:unicas/isla_corsario`): océanos templados y cálidos, en mar abierto, lejos de la
    costa y fuera de la Atlántida (se busca con el ruido de biomas y el fondo marino). Un islote propio de unos 84 × 74
    bloques con su roca, su arena y sus palmeras: en el cerro, el fuerte de Roque Salitre (muralla con camino de ronda,
    baluarte con cuatro cañones, casa del corsario, cuartel y aljibe); en el sur, el puerto con el muelle y un bergantín
    a flote amarrado, la taberna de La Sirena Ahorcada (con un escondite tras un tapiz de la bodega), los almacenes y la
    horca, y en la punta oeste un faro pequeño. Bajo el cerro, las cuevas marinas: la ensenada oculta (se entra en barca
    por el acantilado), el cuerpo de guardia, la sala del mapa con el **puzle de la rosa de los vientos**, la armería con
    la santabárbara secreta, los calabozos y, bajo el nivel del mar y en seco, la cámara del tesoro con Roque Salitre, el
    corsario; trampas de cable y de placas, 3 generadores y 21 cofres. Diseño: [docs/unicas/isla_corsario.md](docs/unicas/isla_corsario.md).
- **Estructuras medianas** (entre todos los tipos, una cada 650-700 bloques, cada uno en sus biomas): torres de vigía,
  posadas de camino, campamentos de bandidos y ermitas, con un estilo por bioma. Ver [Estructuras medianas](#estructuras-medianas).

## Instalación

Requisitos: Minecraft 26.3, Fabric Loader 0.20.1 o superior y Fabric API (probado con 0.166.2+26.3). Opcional en el cliente: Mod Menu (compilado contra la 21.0.1), para la [pantalla de configuración](#pantalla-de-configuración-cliente).

1. Compila `heraldia-<versión>.jar` (ver abajo).
2. Cópialo en la carpeta `mods` del servidor y en la de cada cliente.
3. Arranca el servidor. En `logs/latest.log` debe aparecer `Heraldia: 103 estructuras registradas`.

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
- `/heraldia info` (operadores, nivel 2): resumen de la configuración en uso (aldeas, estructuras únicas activadas y su separación, distancia mínima, cofre por jugador, si está instalado Lootr, estructuras medianas) y de cuántas estructuras hay registradas.
- `/heraldia info cerca [radio]`: la estructura única y la mediana más cercanas de cada tipo y la aldea Heraldia más cercana, con distancia, rumbo y coordenadas (al pulsarlas se propone un `/tp`). Usa la misma comprobación que `/locate`, así que nunca señala una estructura que la distancia mínima descarta, pero no carga ni genera chunks: lo que aún no se ha generado sale como «prevista» (de una aldea prevista solo se sabe la familia). Radio por defecto 3.000 bloques, máximo 10.000; el mensaje dice cuánto ha tardado la búsqueda.
- `/heraldia info aqui`: en qué estructura Heraldia estás (nombre e id) y, en una única, si su guardián vive (solo se responde si toda la estructura está cargada).

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
- Cuatro avenidas con los edificios especiales: iglesia o templo según el estilo (con cementerio y cripta), ayuntamiento, mercado, taberna, herrería, biblioteca, granja con molino y posada. Cada edificio especial tiene tres variantes por estilo, con distinta planta y silueta y la misma función (por ejemplo, la iglesia con torre delantera, con crucero y espadaña o con pórtico y la torre en la cabecera; el mercado al aire libre, como lonja cubierta o como plaza porticada), que se sortean en cada aldea: dos aldeas del mismo estilo se distinguen por sus edificios principales. Láminas: [docs/aldeas/variantes.md](docs/aldeas/variantes.md). En la costa, además, un puerto (caseta y muelle con pilotes, grúa y botes) en la orilla libre más cercana a la plaza, con el muelle hacia mar abierto; se prueban todas las orillas a unos 96 bloques a lo largo de la costa y, si solo estorban casas, rellenos o torres, el puerto ocupa su lugar. Si no cabe en ninguna (todas las ocupan la plaza, edificios especiales o calles que llegan al mar, o no hay agua cerca), la aldea sale sin puerto.
- Unas 20 casas en la estándar y unas 30 en la grande, amuebladas, con cofres en algunas y botín de común a épico (tablas `heraldia:cofres/comun`, `poco_comun`, `raro`, `epico`).
- Torres de vigilancia y puertas de muralla al final de las calles; decoración temática entre casas.
- Aldeanos: la mitad del número de casas, más del 80 % con oficio. Gólems: al menos uno por cada 3 aldeanos.

Límites de población: hay unas 1,25 camas por aldeano inicial, así que la población crece como mucho un 25 %.
La función `heraldia:golems` revisa cada 30 s las aldeas cargadas y retira un gólem natural cada vez que hay 8 o más (estándar) o 9 o más (grande); no toca los construidos por jugadores. Límites y limpieza se cambian en la [configuración](#configuración).

## Vida de las aldeas

Las aldeas Heraldia tienen comercio con carácter, un tablón de encargos y, en las fortificadas, asedios. Todo se desactiva en la [configuración](#configuración) (`aldeas.vida.*`).

- **Tratos propios del estilo** (`aldeas.vida.tratos_estilo`, activado): en cada estilo, un oficio ofrece un trato con su carácter (solo objetos vanilla con nombre, adornos o encantamientos moderados): la Espada de la mesnada del armero castellano, la Copia de la Crónica de los Heraldos del bibliotecario de la abadía, el Peto de las dunas (cuero teñido de arena con adorno de oro) del herrero del obelisco, el Hidromiel del jarl del carnicero nórdico, la Caña del patrón de los pescadores... Además, el cartógrafo de cada familia vende en el nivel 3 (16 esmeraldas y una brújula) el mapa de la estructura única de su zona (castillo en las llanuras, Salón del Jarl en la taiga, Galeón varado en la costa...). Los tratos se sortean como los vanilla al subir de nivel: un aldeano de ese oficio y nivel lo ofrece con una probabilidad de 1/2 a 2/3 (o siempre, en los niveles con un solo trato vanilla), así que en una aldea grande suele haber alguno. Solo los aldeanos de Heraldia dentro de una aldea de ese estilo; también en las aldeas ya generadas, en los aldeanos que suban de nivel desde ahora.
- **Tablón de encargos** (`aldeas.vida.tablon`, activado): en la plaza, junto a la fuente, un atril con el libro «Tablón de encargos» y, detrás, el **alguacil** (aldeano con nombre que no se mueve ni recibe daño) que paga los encargos de entrega con sus tratos: *Cosecha para el granero* (32 del cultivo de la familia: trigo, patatas, bayas, cactus, cacao... por 4 esmeraldas), *Leña para el invierno* (32 troncos de la madera del estilo por 3) y *Limpia los caminos* (16 de carne podrida y 8 huesos por la Capa de la ronda, un peto de cuero del color del estandarte con protección II). Le queda trabajo para unas pocas entregas (no repone). Las hazañas las paga la aldea una vez a cada jugador al conseguir su logro: *Ronda nocturna* (matar una amenaza dentro de una aldea Heraldia: 3 esmeraldas) y *Defiende la aldea* (ser héroe de la aldea tras un asedio en una aldea Heraldia: 8 esmeraldas y el Cuerno del defensor). **Solo en las aldeas nuevas.**
- **Asedios** (`aldeas.vida.asedios`, **desactivado**: cambia el equilibrio): en las aldeas fortificadas (`oscuro_fortificada`, `nieve_fortaleza`, `badlands_canon`) el armero vende en el nivel 3 el «Desafío del asedio», una botella ominosa de nivel I (10 esmeraldas, una vez): quien la bebe y vuelve a la aldea provoca un asalto de saqueadores del juego. No hay puesto de saqueadores junto a la aldea: los saqueadores atacan a los aldeanos a 32 bloques aunque no los vean, así que tendría que quedar fuera de la aldea, y una aldea grande ya llega casi a los 8 chunks de su inicio, el máximo al que el juego coloca piezas; además serían mobs persistentes cargados todo el tiempo.

Coste: una entidad más por aldea (el alguacil, sin IA) y ninguna función periódica; los tratos y las hazañas solo se evalúan cuando un aldeano sube de nivel o un jugador mata, gana un asalto o recoge algo (criterios de logros del juego).

## Caminos entre aldeas

Las aldeas Heraldia cercanas quedan unidas por senderos (`aldeas.caminos.*` en la [configuración](#configuración)):

- **Qué aldeas**: cada aldea con sus vecinas más cercanas a menos de `aldeas.caminos.distancia_maxima_bloques` (2000 por defecto); dos aldeas se unen si ninguna tercera está más cerca de las dos que ellas entre sí, así que no hay triángulos ni caminos que se crucen. Con la separación por defecto (1500) casi toda aldea tiene dos o tres caminos.
- **Trazado**: serpentea suavemente entre las dos plazas, sigue la altura del terreno y, si encaja, pasa a unos 110 bloques de una estructura única que quede a mitad de camino (con la rejilla en uso, también la antigua de `unicas.rejilla_compatible`). Se para al llegar a las piezas de una aldea o de cualquier estructura de superficie, sin atravesarlas.
- **Firme según el terreno**: camino de tierra (con algo de tierra gruesa y grava) en la hierba y la tierra, losas de arenisca en el desierto y la playa, de arenisca roja en las badlands, grava y adoquín en la piedra y la nieve, barro compacto en los manglares. Ancho `aldeas.caminos.ancho` (3 por defecto), con los bordes mellados.
- **Agua**: un río o un tramo de agua corto (hasta unos 64 bloques) se cruza con un puente de tablas un bloque por encima del agua, con postes hasta el fondo; una marisma poco honda (2 bloques), con una pasarela a ras del agua; el agua larga y honda (lagos, mar) corta el camino en la orilla. Nunca pasa por la lava.
- **Farolas y carteles**: cada unos 48 bloques, a un lado y otro, un poste de valla con farol o con antorcha (según el camino), de la madera del bioma; a unos 128 bloques de cada aldea, un cartel con el nombre de la aldea de destino (un topónimo como «Torre del Roble» o «Vado de la Encina», el mismo en todos sus carteles) y los bloques que faltan, con una flecha hacia donde queda.

Todo sale de la semilla y de la rejilla de las aldeas, chunk a chunk, sin cargar ni esperar a ningún otro chunk: los dos lados de una frontera de chunk casan siempre. **En un mundo ya creado, solo en los chunks nuevos**: lo ya generado no cambia y los tramos que caerían en lo explorado no existen (el camino empieza en el borde). Coste, medido en el servidor de prueba (`tools/smoke/caminos.py`, unos 1.000 chunks): la mitad de los chunks pagan menos de 32 µs y el 90 %, menos de 128 µs; lo único caro se calcula una vez por arranque del servidor y queda en memoria: saber si una casilla de la rejilla tiene aldea (unos 1,5 ms; como mucho 100 casillas con aldea), el punto de paso de cada ruta (unos 30 ms) y el fondo en los vértices que caen en el agua (unos 0,4 ms cada uno). El mod escribe estas cifras en el log al parar el servidor.

## La Atlántida

Una sola por mundo, siempre, sin opción de configuración. Es una ciudad amurallada de unos 770 × 770 bloques, totalmente sumergida, en la cuenca de océano profundo más cercana al origen que esté a 1.500 bloques o más y sin explorar (en un mundo ya existente solo aparece en chunks nuevos). La posición se calcula la primera vez que se carga el mundo y se guarda en `data/heraldia/atlantida.json`.

- Se encuentra con `/locate structure heraldia:unicas/atlantida` o con su mapa del tesoro.
- Calles y plazas inundadas, y más de 200 casas, torres y salas **secas** a las que se entra por puertas o buceando desde abajo. Si se rompe un muro, la sala se inunda.
- Ocho distritos (ágora, lonja, termas, arsenal, puerto hundido, jardines de coral, academia y anfiteatro), un templo en el centro, galerías subterráneas y, al fondo, el guardián final.
- Defensores: guardianes, ahogados con tridente, 48 generadores, guardianes ancianos en los distritos clave y el Guardián de Poseidón.
- Tres sellos con sus llaves, puertas de combinación, trampas de flechas, agua y TNT.
- 185 cofres con botín avanzado y un cofre único, oculto y cerrado con la llave del guardián final, con dos tridentes legendarios. Su contenido es fijo: el primer grupo que llegue se lo lleva, salvo que se active `unicas.atlantida.cofre_unico_por_jugador` (ver Configuración): entonces cada jugador abre su propia copia.
- Dentro de la ciudad no nacen otras estructuras (monumentos, naufragios, ruinas), salvo las fortalezas, que el juego necesita para llegar al End.

Detalle, planos y qué se ha comprobado: [docs/unicas/atlantida.md](docs/unicas/atlantida.md).

## Estructuras medianas

Más pequeñas que una única (de 15 × 15 a 21 × 21 bloques) y mucho más frecuentes: entre las aldeas y las únicas quedaba mucho vacío. Por defecto, entre todos los tipos sale **una cada 650-700 bloques** (medido, ver abajo), cada tipo solo en sus biomas y con un estilo propio del bioma. Botín modesto (sin cofre premium; con Lootr, el de cada jugador), pocas entidades y, en algunas, un pequeño reto. Lote 1:

| Tipo | Id | Estilos (biomas) | Variantes |
| --- | --- | --- | --- |
| **Torre de vigía** | `heraldia:medianas/torre_vigia/<estilo>` | colinas ventosas y pradera (piedra); taigas (piedra y abeto) | tres plantas y atalaya cubierta con un arquero esqueleto (con casco, no arde), o dos plantas con un cobertizo de leña y sin mobs; siempre con la hoguera en lo alto |
| **Posada de camino** | `heraldia:medianas/posada/<estilo>` | llanuras (roble); bosques de robles, abedules y flores (abedul y roble oscuro); sabanas (acacia y terracota) | sala común con hogar, mesas y mostrador, el posadero (un aldeano sin IA que vende pan, cerdo asado y una cama, y compra trigo), un cuarto con dos camas y un cofre; con corral de paja y abrevadero o con huerto |
| **Campamento de bandidos** | `heraldia:medianas/campamento/<estilo>` | bosques; taigas; badlands | tiendas de lona alrededor de una fogata con bancos de troncos, un tonel con lo robado y un estandarte; dos saqueadores, o una empalizada, tres tiendas, un vindicador jefe y un saqueador. Son persistentes y anclados (se quedan en el campamento hasta que los atacan), no forman patrulla y no vuelven a salir |
| **Ermita** | `heraldia:medianas/ermita/<estilo>` | arboledas y laderas nevadas (ladrillo de piedra); bosque oscuro y jardín pálido (piedra musgosa); cerezales (cerezo y terracota blanca) | capilla con espadaña y campana, bancos, altar con velas y la celda del ermitaño (cama, atril y el cofre con su diario, un libro escrito en el idioma de cada jugador); huerto vallado con acequia y, en una variante, un pequeño camposanto |

- Nunca salen dentro de una aldea, una única, la Atlántida o la isla del corsario: no a menos de `medianas.distancia_aldeas_unicas_bloques` (256) del inicio de una aldea o una única de Heraldia que sale ahí, ni a menos de `medianas.distancia_minima.bloques` (192) de otra mediana de otro tipo (un sorteo determinista deja una, la misma regla que la distancia mínima entre únicas), ni a menos de 128 bloques de una candidata de aldea vanilla. Además ceden el sitio a las estructuras que asoman a la superficie, vanilla o de otros mods (puestos de saqueadores, templos, portales en ruinas, aldeas de otros mods...): se descarta una si sale una de esas a menos de 80 bloques (vanilla) o de 128 (de otro mod).
- Se encuentran con `/locate structure #heraldia:medianas/<tipo>` (o `heraldia:medianas/<tipo>/<estilo>`) y `/heraldia info cerca`; `/heraldia info` resume su configuración. Para probar una: `/place structure heraldia:medianas/<tipo>/<estilo>`.
- Frecuencia, medida con `MedianasFrecuenciaTest` (las rejillas sobre el ruido de biomas real del mundo principal de 26.3, con las aldeas, las únicas y las estructuras vanilla alrededor, 3 semillas, 16.000 × 16.000 bloques): las cifras por tipo, en el [registro de cambios](CHANGELOG.md) y el PR. Cada rejilla busca su candidata dentro de los biomas del tipo (el sitio de la casilla más metido en ellos), así que un tipo aparece allí donde están sus biomas, como mucho una vez por casilla.
- Configuración: opciones `medianas.*` (ver [Configuración](#configuración)). Logros: **Al borde del camino** y **Caminante** (ver [Logros](#logros)). **En un mundo ya creado, solo en los chunks nuevos.**

## Biomas de otros mods

Cada familia de aldeas y cada estructura única busca sus biomas con una etiqueta propia (`#heraldia:<familia>` y `#heraldia:unicas/<id>`): los biomas vanilla de las tablas de arriba más las etiquetas convencionales de Fabric/NeoForge (`#c:...`) y `#minecraft:is_*` en las que los mods de biomas (Terralith, Biomes O' Plenty...) meten los suyos. Solo se usan las que en vanilla no añaden ningún bioma a la lista, así que **sin mods de biomas todo sale exactamente donde antes**; todas van con `"required": false` (si un mod no está, el paquete carga igual).

| Etiqueta | Además de sus biomas vanilla |
| --- | --- |
| `llanuras`, `unicas/castillo` | `#c:is_plains` |
| `bosque` | `#c:is_birch_forest`, `#c:is_flower_forest` |
| `oscuro` (y la torre de mago) | `#c:is_dark_forest` |
| `nieve`, `unicas/fortaleza_hielo` | `#c:is_snowy_plains` |
| `desierto`, `unicas/acueducto` | `#c:is_desert` |
| `jungla` | `#minecraft:is_jungle`, `#c:is_jungle` |
| `pantano` (y la mansión) | `#c:is_swamp` |
| `badlands` | `#minecraft:is_badlands`, `#c:is_badlands` |
| `costa` | `#minecraft:is_beach`, `#c:is_beach`, `#c:is_stony_shores` |
| `unicas/catedral` | `#c:is_flower_forest` |
| `unicas/santuario` | `#c:is_birch_forest` |
| `unicas/laboratorio_micelio` | `#c:is_mushroom` |
| `unicas/faro` | `#c:is_stony_shores` |
| `unicas/galeon` | `#minecraft:is_beach`, `#c:is_beach` |
| `unicas/atlantida` | `#minecraft:is_ocean`, `#c:is_ocean` |

Taiga, sabana, cerezos y las únicas coliseo, observatorio, pirámide, monasterio, ciudadela, palacio, salón del jarl, mina perdida e isla del corsario se quedan solo con sus biomas vanilla: no hay ninguna etiqueta convencional lo bastante estrecha (por ejemplo, `#c:is_cave` incluye el abismo; `#c:is_taiga` incluye la taiga nevada, de la familia nieve, y `#c:is_savanna` la sabana ventosa, del observatorio). Qué bioma de un mod entra en cada etiqueta lo decide ese mod (con Terralith, por ejemplo, la llanura incluye sus estepas y tierras altas, y el bosque, sus bosques de lavanda y de cerezos). La búsqueda de la Atlántida acepta también los océanos de `#c:is_ocean` y `#c:is_deep_ocean`. Probado con Terralith 2.6.5 (`tools/smoke/terralith_biomas.py`).

## Compatibilidad con otros mods

Probado en un servidor dedicado 26.3 real con las versiones de Modrinth para Minecraft 26.3 + Fabric de la tabla (fijadas con su sha512 en `tools/smoke/modrinth.py`), por grupos de mods que funcionan juntos (`python3 tools/smoke/compat_mods.py --grupo <grupo>`; `--listar` muestra los grupos). En cada grupo: el servidor arranca sin errores de registro ni excepciones que pasen por código de Heraldia, se registran todas las estructuras de Heraldia, `/locate` encuentra una aldea y cuatro estructuras únicas, `/place` coloca la torre de mago con su guardián y se generan (Chunky) tres zonas de 21 × 21 chunks alrededor de la aldea y de dos únicas, midiendo chunks/s y «Can't keep up!». Después se leen los inicios de estructura guardados en las regiones para buscar piezas de Heraldia cruzadas con piezas de estructuras de otros mods.

**Estructuras de otros mods junto a las de Heraldia**: una estructura de otro mod que asoma a la superficie (aldeas de Towns and Towers, ruinas de Structory, tabernas de Dungeons and Taverns...) no nace a menos de `compatibilidad.zona_estructuras_ajenas_bloques` bloques (224 por defecto, 0 lo desactiva) del inicio de una aldea o una única de Heraldia que sale de verdad ahí; Heraldia gana siempre, así que ninguna queda encima de la otra. Antes, la prueba encontró una aldea del bosque de Towns and Towers encima de la catedral y una aldea de playa dentro de una aldea de Heraldia. No cubre: las estructuras subterráneas de otros mods (minas, mazmorras: no se ven, pero pueden cruzar un sótano o la Mina perdida), las vanilla y los mods que sustituyen a las vanilla con su nombre `minecraft:` (las aldeas vanilla conservan su propia zona de exclusión) y estructuras muy grandes cuyas piezas llegan más lejos que esa distancia.

| Mod | Versión probada | Estado | Notas |
| --- | --- | --- | --- |
| Terralith (+ Lithostitched) | 2.6.5+26.3 (2.0.6) | probado | Biomas por las etiquetas convencionales ([Biomas de otros mods](#biomas-de-otros-mods)); sus estructuras propias se apartan de las de Heraldia. 33,8 chunks/s (52,6 sin mods). |
| Tectonic (+ Lithostitched) | 3.1.0+beta2 | con limitaciones | Funciona (27,3 chunks/s), pero Tectonic 3 se declara incompatible con Terralith: con los dos el servidor no arranca («Mod resolution failed»). |
| Biomes O' Plenty (+ GlitchCore, TerraBlender) | 26.3.0.0.16 | probado | 42,6 chunks/s. |
| William Wythers' Overhauled Overworld (+ Cristel Lib, Cloth Config) | 3.0.1 | probado | 15,4 chunks/s: su terreno cuesta más de generar (también sin Heraldia). |
| Oh The Biomes We've Gone | — | no probado: sin versión 26.3 | Última versión para Fabric: 1.21.11. |
| Dungeons and Taverns | 6.1.0 | probado | Con la zona de exclusión, sin solapes. |
| Towns and Towers (+ Cristel Lib) | 1.13.13 | probado | Se solapaba antes de la zona de exclusión; ahora no. |
| Structory, Structory: Towers | 1.3.18, 1.0.19 | probado | |
| Explorify | 1.6.6 | probado | 41,2 chunks/s con todo el grupo de estructuras. |
| YUNG's Better Dungeons, Mineshafts, Strongholds, Ocean Monuments, Desert Temples, Jungle Temples, Witch Huts, Bridges, Extras (YUNG's API) | — | no probado: sin versión 26.3 | Última: 26.1.2. |
| Lithium | 0.26.3 | probado | |
| C2ME | 0.4.2-alpha.0.119 | probado | Generación multihilo: 63,7 chunks/s, sin errores. Los mixins y cachés de Heraldia son seguros entre hilos (revisados, con tests unitarios concurrentes). |
| FerriteCore | 9.0.0 | probado | |
| ScalableLux | 0.3.0-alpha.0.6 | probado | Sustituye a Starlight. |
| ModernFix | — | no probado: sin versión 26.3 | Última: 1.21.1. |
| Starlight | — | no probado: sin versión 26.3 | Abandonado (última 1.20.4); lo sustituye ScalableLux. |
| Noisium | — | no probado: sin versión 26.3 | Tampoco NoisiumForked (última 26.2). |
| Chunky | 1.5.66 | probado | Hace la pregeneración en todos los grupos. |
| Lootr | 1.25.42.124 | probado | Detectado (`/heraldia info`): cada cofre da un botín más modesto, porque cada jugador abre el suyo. |
| Distant Horizons (servidor) | 3.3.4 | con limitaciones | Funciona con Heraldia (zonas generadas con `forceload`), pero junto con Chunky el servidor se queda parado al preparar el spawn, también sin Heraldia: no pregeneres con Chunky mientras esté instalado. |
| Xaero's Minimap, Xaero's World Map | 26.6.2, 1.47.2 | probado (servidor) | Cargan en el servidor; sin probar con un cliente. |
| JourneyMap | 6.0.10 | probado (servidor) | Igual. |

En la CI estas pruebas van en cada push a `develop`, a mano y en los PR que cambian sus ficheros, los mods fijados o el código común de colocación. `python3 tools/smoke/modrinth.py --comprobar` dice si hay versiones 26.3 más nuevas.

## Mapas del tesoro

Cada estructura única tiene su mapa del tesoro, que marca la más cercana con una X (u otra marca propia de la estructura) y lleva su nombre traducido:

- En los cofres épicos de las aldeas: un 5 % de los cofres lleva uno (de una estructura única al azar).
- A la venta en los cartógrafos maestros (nivel 5) **de las aldeas Heraldia** (no en las vanilla): 24 esmeraldas y una brújula, 2 por reposición. Los aldeanos de aldeas generadas antes de esta versión no lo ofrecen.
- La búsqueda abarca unos 10.000 bloques y no salta chunks ya explorados (así no traba el servidor). Si no hay ninguna estructura de ese tipo al alcance, no sale el mapa (el cofre lo deja vacío y el cartógrafo no ofrece ese trato).
- Para probar: `/loot give @s loot heraldia:mapas/<id>` da el mapa de la estructura `heraldia:unicas/<id>` desde donde estés.

En laderas, los cimientos de los edificios (y los pilotes de los estilos sobre pilotes) bajan hasta el suelo con el material del estilo, hasta 16 bloques.

Limitaciones conocidas: en laderas las calles siguen el terreno con peldaños de un bloque y, en un risco de más de 16 bloques, un cimiento puede quedar al aire; una aldea de la costa aún puede salir sin puerto si todas las orillas a unos 96 bloques las ocupan la plaza, edificios especiales o calles que llegan al mar (con las semillas de prueba, 21 de 21 aldeas naturales de la costa lo tienen); no se ha comprobado el solape con estructuras de otros mods (los biomas de otros mods sí, ver [Biomas de otros mods](#biomas-de-otros-mods)).

## Trofeos de los guardianes

Cada guardián con nombre de una estructura única (y el Guardián de Poseidón de la Atlántida) suelta al morir su **trofeo**, un objeto vanilla con nombre propio, una o dos líneas de historia, rareza (color del nombre) y, a veces, un adorno de armadura o un escudo con blasón. La mayoría son de adorno; unos pocos (el Tridente de Poseidón, el Hacha de Borin Barbahierro) son algo mejores que un objeto normal, sin romper la progresión. Solo cae si lo mata un jugador (con `/kill` o una trampa sin jugador, no) y hay uno por guardián: colocar la estructura otra vez con `/place` crea otro guardián y, por tanto, otro trofeo. Los guardianes zombis, husks y ahogados (y los ahogados de la Atlántida) salen siempre adultos, con su propia arma y sin montura.

| Estructura | Trofeo | Objeto | Encantamientos |
|---|---|---|---|
| Acueducto en ruinas | Lorica del Centurión Aquilio | `iron_chestplate` | protección 1 |
| La Atlántida | Tridente de Poseidón | `trident` | lealtad 2, empalamiento 2 |
| Castillo | Yelmo de Sir Aldric | `iron_helmet` | protección 1 |
| Catedral gótica | Brújula de ánimas de Fray Osmundo | `recovery_compass` | — |
| Ciudadela enana | Hacha de Borin Barbahierro | `iron_axe` | eficiencia 3, irrompibilidad 2 |
| Coliseo en ruinas | Escudo del Campeón de la Arena | `shield` | irrompibilidad 2 |
| Faro de los contrabandistas | Alfanje del Capitán Bruma | `iron_sword` | filo 1, irrompibilidad 1 |
| Fortaleza de hielo | Corona de escarcha | `golden_helmet` | irrompibilidad 2 |
| Galeón varado | Catalejo del capitán ahogado | `spyglass` | — |
| Isla del corsario | Arco de Roque Salitre | `bow` | poder 2, irrompibilidad 2 |
| Laboratorio del micólogo | Tijeras de Maese Ambrosio | `shears` | eficiencia 2, irrompibilidad 2 |
| Mansión encantada | Reloj del Conde Malaquías | `clock` | — |
| Mina perdida de Hondavena | Pico de Tizón | `iron_pickaxe` | eficiencia 2, irrompibilidad 2 |
| Monasterio de montaña | Lágrima del relicario | `amethyst_shard` | — |
| Observatorio | Astrolabio del Custodio | `compass` | — |
| Palacio oriental | Espada ceremonial de la Guardia Imperial | `golden_sword` | filo 2, irrompibilidad 3 |
| Templo-pirámide | Pectoral del Rey Jaguar | `golden_chestplate` | protección 1 |
| Salón del Jarl | Rompeescudos de Ulfgrim | `iron_axe` | filo 2, irrompibilidad 2 |
| Santuario druídico | Hoz de oro de Cadoc | `golden_hoe` | eficiencia 2, irrompibilidad 2 |
| Torre de mago | Báculo del Archimago Malvarius | `blaze_rod` | — |

Todos llevan `custom_data` `{heraldia_trofeo:"<id>"}`. Para probar: `/loot give @s loot heraldia:trofeos/<id>`. El desafío **Sala de trofeos** (ver [Logros](#logros)) pide tenerlos todos.

## Crónica de los Heraldos

Un hilo narrativo opcional une las estructuras únicas (trasfondo completo en [`docs/historia.md`](docs/historia.md)): Ysolda, la última heraldo de la Atlántida, escribió el camino de vuelta a la ciudad hundida en pliegos y confió cada uno al guardián de una estructura, que juró custodiarlo. Cada única guarda su **pliego**, un libro escrito («Crónica de los Heraldos: <estructura>») en un cofre que ya tenía, que cuenta su parte de la historia y termina señalando la siguiente estructura con una pista de bioma y rasgo; a veces (10 %) viene con su mapa del tesoro. La cadena pasa por todas y la de la Torre de mago señala la Atlántida, cuyo pliego vuelve a señalar la primera.

| Estructura | Cofre del pliego | Señala |
|---|---|---|
| Acueducto en ruinas | cisterna | Castillo |
| Castillo | capilla | Catedral gótica |
| Catedral gótica | biblioteca | Ciudadela enana |
| Ciudadela enana | cámara real | Coliseo en ruinas |
| Coliseo en ruinas | despacho del lanista | Faro de los contrabandistas |
| Faro de los contrabandistas | despacho del capitán | Fortaleza de hielo |
| Fortaleza de hielo | galería | Galeón varado |
| Galeón varado | camarote del capitán | Isla del corsario |
| Isla del corsario | sala del mapa | Laboratorio del micólogo |
| Laboratorio del micólogo | biblioteca de esporas | Mansión encantada |
| Mansión encantada | biblioteca | Mina perdida de Hondavena |
| Mina perdida de Hondavena | despacho oculto del capataz | Monasterio de montaña |
| Monasterio de montaña | biblioteca | Observatorio |
| Observatorio | sala oculta | Palacio oriental |
| Palacio oriental | biblioteca secreta | Templo-pirámide |
| Templo-pirámide | tumba | Salón del Jarl |
| Salón del Jarl | sala de las ofrendas | Santuario druídico |
| Santuario druídico | biblioteca | Torre de mago |
| Torre de mago | escondite | La Atlántida |
| La Atlántida | sello de la Academia | Acueducto en ruinas |

Las páginas se leen en el idioma de cada jugador (español si el cliente no tiene el mod). Con Lootr cada jugador encuentra su propio pliego. Todos llevan `custom_data` `{heraldia_historia:"<id>"}`; para probar: `/loot give @s loot heraldia:historia/<id>`. El desafío **Cronista** (ver [Logros](#logros)) pide tenerlos todos. **En un mundo ya creado, solo salen en los cofres que aún no se hayan abierto.**

## Logros

Pestaña de logros **Heraldia** (84 logros), con textos en español e inglés. Solo dan experiencia, salvo las dos hazañas del tablón de encargos:

- **Heraldia** (raíz): entrar en cualquier aldea Heraldia, estructura única o mediana.
- [Estructuras medianas](#estructuras-medianas): **Al borde del camino**, encontrar una cualquiera (10), y **Caminante**, una de cada tipo (150).
- Una aldea de cada familia (12 logros, 20 de experiencia) y el desafío **Trotamundos de Heraldia**: las 12 familias (250).
- Por cada estructura única: descubrirla (50), derrotar a su guardián con nombre (100) y abrir su cofre del tesoro (50).
- La Atlántida, además: sus tres sellos (abrir el cofre del sello o tener su llave, 30 cada uno); el guardián es el Guardián de Poseidón y el tesoro cuenta al coger uno de los objetos con nombre del cofre único.
- Encargos del [tablón](#vida-de-las-aldeas): **Ronda nocturna** (matar una amenaza dentro de una aldea Heraldia: 3 esmeraldas y 30 de experiencia) y **Defensor de la aldea** (ser héroe de una aldea Heraldia tras un asedio: 8 esmeraldas, el Cuerno del defensor y 100 de experiencia).
- Desafío final **Cartógrafo de leyendas**: descubrir todas las estructuras únicas (500).
- Desafío **Sala de trofeos**: conseguir el [trofeo](#trofeos-de-los-guardianes) de cada guardián de las estructuras únicas (500); cuenta al tenerlo en el inventario.
- Desafío **Cronista**: reunir los pliegos de la [Crónica de los Heraldos](#crónica-de-los-heraldos), uno por estructura única (500); cuenta al tenerlo en el inventario.

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
| `aldeas.vida.tratos_estilo` | `true` | `true`/`false` | Tratos propios de cada estilo y mapa de la única de la zona en los cartógrafos de cada familia ([Vida de las aldeas](#vida-de-las-aldeas)). |
| `aldeas.vida.tablon` | `true` | `true`/`false` | Tablón de encargos y alguacil en la plaza de las aldeas nuevas. |
| `aldeas.vida.asedios` | `false` | `true`/`false` | El armero de las aldeas fortificadas vende una botella ominosa para provocar un asalto de saqueadores. |
| `aldeas.caminos.activado` | `true` | `true`/`false` | Caminos entre aldeas cercanas, con puentes, farolas y carteles ([Caminos entre aldeas](#caminos-entre-aldeas)); solo en los chunks nuevos. Desactivado, el rasgo ni se añade a los biomas. |
| `aldeas.caminos.distancia_maxima_bloques` | 2000 | 500-4000 | Solo se unen aldeas a menos de esta distancia. Dos aldeas nunca están a menos de unos 670 bloques (con la separación mínima, 1000), así que con menos de eso no habría ningún camino. |
| `aldeas.caminos.ancho` | 3 | 1-5 | Ancho de los caminos, en bloques. |
| `golems.limpieza` | `true` | `true`/`false` | Activa la retirada periódica de gólems naturales. |
| `golems.limite_estandar` | 8 | 1-64 | Con tantos gólems naturales o más, una aldea estándar retira uno cada 30 s. |
| `golems.limite_grande` | 9 | 1-64 | Igual para las aldeas grandes. |
| `unicas.<id>.activada` | `true` | `true`/`false` | Activa una estructura única. Aparece una entrada por cada estructura única del mod. |
| `unicas.<id>.separacion_bloques` | la de la estructura (4000) | 1000-10000 | Separación media entre estructuras de ese tipo (por defecto, una cada 3000-5000 bloques). Cada tipo se reparte por toda su casilla de la rejilla (con el origen desplazado por tipo) y dos del mismo tipo nunca quedan a menos de `unicas.distancia_minima.bloques`. En el Laboratorio del micólogo (campos de champiñones, un bioma muy raro) la candidata de cada casilla no se sortea: es el sitio de la casilla más metido en ese bioma, así que sale en buena parte de las islas de champiñones (como mucho una por casilla). La Mina perdida hace lo mismo con las cuevas exuberantes y de espeleotemas, mirando a la altura de la caverna (y = 26) en vez de al nivel del mar, y la Isla del corsario con sus océanos (el sitio más metido en mar abierto). |
| `unicas.rejilla_compatible` | `false` | `true`/`false` | **Ponlo a `true` en un mundo creado con una versión anterior de Heraldia (0.1.0)**; déjalo en `false` en un mundo nuevo. Las rejillas de colocación de las únicas cambiaron después de la 0.1.0 (el origen de la rejilla de cada tipo va desplazado y la separación interna es la distancia mínima), así que en un mundo antiguo `/locate`, los mapas del tesoro, los pliegos de la Crónica, `/heraldia info cerca` y la distancia mínima ya no encuentran las únicas ya generadas en lo explorado (aunque siguen ahí). Activada, las 14 únicas que ya estaban en la 0.1.0 (acueducto, castillo, catedral, ciudadela, coliseo, faro, fortaleza de hielo, galeón, mansión, monasterio, observatorio, palacio, pirámide y torre de mago) vuelven a la rejilla de esa versión, bit a bit, para la misma semilla y configuración y con el mismo coste. Las añadidas después (Salón del Jarl, Santuario druídico, Laboratorio del micólogo, Mina perdida e Isla del corsario) siguen con la rejilla nueva, y las antiguas tienen prioridad sobre ellas: una nueva se descarta si cae a menos de la distancia mínima de una antigua que sale, así que nunca aparece encima de una ya generada. No afecta a las aldeas ni a la Atlántida (su colocación no cambió; la Atlántida conserva su posición guardada). |
| `unicas.distancia_minima.activada` | `true` | `true`/`false` | Impide que dos estructuras únicas distintas (también la Atlántida) salgan a menos de la distancia mínima. |
| `unicas.distancia_minima.bloques` | 1000 | 100-3000 | Distancia mínima entre los chunks de inicio de dos estructuras únicas distintas. Si dos candidatas quedan demasiado cerca, un sorteo determinista (semilla y posición) se queda con una; si la ganadora no puede salir ahí (bioma o terreno), se conserva la otra. `/locate` y los mapas del tesoro siguen la misma regla. |
| `unicas.atlantida.cofre_unico_por_jugador` | `false` | `true`/`false` | Cofre premium de la Atlántida por jugador. La primera apertura convierte su contenido en una plantilla guardada en el propio cofre (que queda vacío: romperlo o vaciarlo con una tolva no duplica nada) y cada jugador abre su propia copia: la recibe entera la primera vez y después encuentra lo que dejó. Sigue haciendo falta la llave de Poseidón. Con Lootr o sin él funciona igual (Lootr no convierte este cofre porque no tiene tabla de botín). Si se desactiva después, el contenido vuelve al cofre una vez (la primera vez que alguien lo usa) y se comporta como antes. |
| `medianas.activadas` | `true` | `true`/`false` | Activa las [estructuras medianas](#estructuras-medianas). |
| `medianas.frecuencia_porcentaje` | 100 | 25-400 | Frecuencia de todas las medianas, en % de la de por defecto: 200 = el doble (la separación de cada tipo se divide por la raíz). |
| `medianas.distancia_minima.bloques` | 192 | 64-1024 | Distancia mínima entre dos medianas de tipos distintos (y entre dos del mismo, como mucho media casilla de su rejilla). |
| `medianas.distancia_aldeas_unicas_bloques` | 256 | 128-1024 | Una mediana no sale a menos de esta distancia del inicio de una aldea o una única de Heraldia que sale ahí. |
| `medianas.<id>.activada` | `true` | `true`/`false` | Activa un tipo de mediana (`torre_vigia`, `posada`, `campamento`, `ermita`). |
| `medianas.<id>.separacion_bloques` | la del tipo (640-768) | 256-4000 | Separación media entre dos de ese tipo (con la frecuencia al 100 %); cada casilla busca su candidata dentro de los biomas del tipo. |
| `compatibilidad.zona_estructuras_ajenas_bloques` | 224 | 0-512 | Las estructuras de otros mods que asoman a la superficie no nacen a menos de esta distancia del inicio de una aldea o una única de Heraldia que sale ahí; 0 lo desactiva ([Compatibilidad con otros mods](#compatibilidad-con-otros-mods)). |

La Atlántida no tiene opciones de colocación: es siempre una sola por mundo.

### Pantalla de configuración (cliente)

En el cliente el fichero también se puede editar desde una pantalla del juego. Con [Mod Menu](https://modrinth.com/mod/modmenu) instalado (opcional; sin él el mod funciona igual, solo que la pantalla no tiene botón) se abre desde el botón de configuración de Heraldia en la lista de mods. Se construye con la misma lista de opciones que el fichero, así que las opciones nuevas aparecen solas:

- Secciones: Aldeas, Familias de aldeas, Estilos de aldea, Vida de las aldeas, Caminos entre aldeas, Gólems, Estructuras únicas, Distancia mínima entre únicas, Atlántida, Estructuras medianas y Compatibilidad con otros mods, con un buscador (por nombre, clave, ayuda o sección).
- Cada opción muestra su valor (botón sí/no o casilla numérica). Su tooltip da la clave, la ayuda (la misma de `_ayuda`) y el valor por defecto y el rango. Un número no válido se pone en rojo, el tooltip dice por qué y **Guardar** queda desactivado hasta corregirlo.
- **Guardar** escribe `config/heraldia.json` con el mismo formato que al arrancar (con `version` y `_ayuda`); **Valores por defecto** devuelve todas las opciones a su valor por defecto (no se escribe nada hasta guardar); **Cancelar** descarta los cambios.
- Los cambios se aplican al volver a abrir el mundo o reiniciar el servidor, y solo en los chunks que se generen después; la pantalla lo avisa. Sin ningún mundo abierto se usan desde el siguiente mundo que abras (sin reiniciar el juego); con un mundo de un jugador abierto, al salir y volver a entrar.
- Conectado a un servidor, la pantalla edita **el fichero local del cliente** (tus mundos de un jugador), no el del servidor: la pantalla lo avisa. La configuración del servidor se sigue editando en su propio `config/heraldia.json`. No se envía nada por la red.

## Compilar

Requisitos: Java 25, Python 3.11+ y `pip install -r tools/gen/requirements.txt`, git.

```bash
./gradlew build
```

El `.jar` queda en `build/libs/`. La compilación ejecuta el generador `tools/gen/main.py`, que crea las estructuras y los logros, los valida contra los registros de 26.3 y audita las estructuras; si hay un solo error o aviso, la compilación falla.

Los registros de 26.3 (resumen de [misode/mcmeta](https://github.com/misode/mcmeta), rama `26.3-summary`) no se incluyen en el repositorio porque son datos de Mojang. Se clonan solos en `build/mcmeta-summary`; para usar otra copia: `-Pmcmeta_summary=<ruta>` o la variable `MCMETA_SUMMARY`.

`./gradlew build` pasa también las pruebas unitarias: las del generador (pytest, `tools/gen/tests`, también con `python3 -m pytest tools/gen/tests`, unos segundos), las JUnit (`./gradlew test`) y las simulaciones JUnit largas (`./gradlew testPesado`, unos minutos). El generador reparte su trabajo entre procesos (`HERALDIA_PROCESOS=1` lo hace en serie, con la misma salida).

`python3 tools/test.py --afectados` pasa las pruebas unitarias y solo las pruebas de servidor afectadas por los ficheros cambiados frente a `origin/develop` (`--listar` solo las enumera); `python3 tools/test.py --todo` pasa la batería completa. El mapa de rutas es el mismo que usa la CI (ver `docs/DESARROLLO.md`, «Política de pruebas»).

Comprobaciones antes de publicar (la CI de GitHub Actions, `.github/workflows/ci.yml`, las ejecuta en cada PR contra `develop` o `main`, con solo las pruebas de servidor afectadas por el PR, y todas en cada push a `develop`, a mano o en un PR con la etiqueta `bateria-completa`):

```bash
python3 tools/changelog.py check
```

```bash
python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-0.1.0.jar
```

La segunda descarga un servidor Fabric 26.3 real en `build/smoke`, arranca con el mod y comprueba que las 103 estructuras estén registradas y los 84 logros cargados, que `/place structure` coloque una aldea con aldeanos y que las funciones existan.

Pruebas en servidor de cada estructura única (mismo argumento `--jar`): `tools/smoke/coliseo_redstone.py`, `observatorio_smoke.py`, `palacio_redstone.py`, `ciudadela_check.py` y `galeon_test.py`, y en `tools/gen/unicas/`: `castillo/prueba_redstone.py`, `torre_mago/prueba_redstone.py`, `catedral/prueba_juego.py` y `prueba_servidor.py` de `fortaleza_hielo`, `mansion`, `monasterio`, `piramide`, `salon_jarl`, `santuario`, `laboratorio_micelio`, `mina_perdida` e `isla_corsario`. La Atlántida se comprueba dentro de la prueba de humo (`atlantida/humo.py`). `tools/smoke/trofeos.py` añade Carpet (versión fijada) y, con un jugador simulado, mata a cada guardián y comprueba que suelta su trofeo (y que con `/kill` no) y que el desafío de los trofeos se concede con el último. `tools/smoke/historia.py` (también con Carpet) comprueba que la cadena de la Crónica pasa por todas las únicas y que el cofre de cada una suelta su pliego, y que el jugador simulado consigue el desafío Cronista con el último. `tools/smoke/aldeas_variantes.py` coloca varias aldeas del mismo estilo, lee las regiones guardadas e identifica, comparando los bloques con las plantillas del `.jar`, qué variante de cada edificio especial ha salido; comprueba que cada uno coincide con una sola variante y que salen variantes distintas, y mide cada `/place`. `tools/smoke/guardianes_adultos.py` coloca 200 veces, por el mismo camino que la generación, cada mob de tipo zombi de las plantillas (zombi, husk, ahogado) y comprueba que ninguno sale bebé, con otra arma o montado. `tools/smoke/guardianes_anclados.py` (con Carpet) coloca 30 veces, por el mismo camino, cada mob de las plantillas con la etiqueta `heraldia_anclado` (los guardianes y los ahogados de la Atlántida) y comprueba que ninguno puede recoger objetos y que tras 200 ticks, y otra vez tras descargar y volver a cargar los chunks, todos siguen donde aparecieron (un lote de control sin la etiqueta debe pasear y recoger objetos); luego, que cada uno ataca al jugador simulado a 8 bloques, y que cada guardián sigue en su sala 200 ticks después de colocar su plantilla real de día. `tools/smoke/rejilla_compatible.py` activa `unicas.rejilla_compatible` y comprueba que `/locate` de varias únicas de la 0.1.0 da exactamente las coordenadas del `.jar` de la 0.1.0 (fijadas en el script, con cómo se sacaron).

Todas las pruebas de servidor comparten las utilidades de `tools/smoke/server_smoke.py` (`Context`): comprobaciones que siempre responden (`test` rechaza un `execute` con `as`/`at` o con más de una condición, que puede no responder nada en la consola), esperas por condición con un límite holgado (`until`, `wait_entity`, que si se rinde imprime dónde están las entidades de ese tipo o etiqueta), esperas contadas en ticks del juego (`ticks`, con `/time query gametime`) y `pos` (lee `Pos` con `data get entity`). Los guardianes y demás mobs con IA se buscan por su etiqueta, no en una caja junto a su sitio. Cada servidor de prueba elige un puerto libre, así que se pueden lanzar varias pruebas a la vez en la misma máquina.

Versiones fijadas en `gradle.properties`. Herramientas del generador: `tools/gen/sim.py` (simula el ensamblado jigsaw; `python3 tools/gen/sim.py [estilo ...]` cuenta las variantes de los especiales, casas, aldeanos, gólems y camas), `tools/gen/render.py` (renders isométricos; `python3 tools/gen/render.py <carpeta> [estilo ...]` dibuja las láminas de variantes), `tools/gen/lint.py` (auditoría de diseño).

## Licencia y créditos

Sin licencia: todos los derechos reservados. El código es visible pero no se concede permiso para usarlo, copiarlo ni redistribuirlo.
Todo el contenido usa solo bloques y objetos de Minecraft; no se incluyen recursos de terceros.
