# Variantes de los edificios especiales de las aldeas

Cada estilo tiene tres versiones de cada edificio especial (la `a` es la original). Comparten materiales, paleta y
detalles del estilo, el acceso por la avenida y la función: los mismos huecos de aldeano y gólem, las mismas tablas de
botín, campanas y puestos de trabajo (lo comprueba `pack.variant_errors` al generar). El pool de cada especial las
sortea con pesos 2 : 1 : 1, de forma determinista como el resto del ensamblado.

| Edificio | a (original) | b | c |
|---|---|---|---|
| Iglesia | torre delantera | crucero y espadaña en la fachada (cúpula sobre el crucero en el estilo de cúpula) | pórtico y torre en la cabecera |
| Templo escalonado | tres cuerpos anchos | cuatro cuerpos empinados, escalinata tallada y crestería | templo de pilonos: patio porticado y sala de columnas |
| Templo de pagoda | sala y pagoda al lado | pagoda de cinco cuerpos en el patio y sala al fondo | sala con dos alas y pabellón del farol |
| Cementerio | mausoleo al fondo | seto, caminos en cruz con crucero, cipreses y cripta en un rincón | hileras de tumbas y capilla de ánimas |
| Ayuntamiento | pórtico con balcón | soportales bajo la planta alta, tejado a dos aguas | torre mirador sobre el tejado |
| Mercado | puestos y pozo | lonja cubierta | plaza porticada en U con fuente |
| Herrería | vivienda y fragua bajo un tejado | patio de fragua delante y vivienda detrás | taller de piedra con vivienda arriba |
| Taberna y posada | dos plantas con chimenea exterior | más estrecha, con terraza bajo una pérgola | planta alta en voladizo y hastial a la calle |
| Biblioteca | sala alargada con altillo | sala cuadrada de doble altura con linterna | claustro: alas delante, sala al fondo y jardín |
| Granja | bancales delante | corral y granero delante, bancales detrás | huerta en franjas, frutales y granero largo |
| Molino | torre casi cuadrada | torre redonda encalada con tejado cónico | torre con la casa del molinero delante |

Láminas (filas: iglesia, cementerio, ayuntamiento, mercado, herrería, taberna, posada, biblioteca, granja y molino;
columnas: a, b, c; vista desde la entrada). Se regeneran con `python3 tools/gen/render.py docs/aldeas <estilo ...>`.

- [Llanuras, medieval castellana](llanuras_castellana.png)
- [Desierto, obelisco](desierto_obelisco.png)
- [Cerezos, japonesa](cerezos_japonesa.png)
- [Taiga, nórdica](taiga_nordica.png)

El aspecto en el juego no está confirmado con capturas.
