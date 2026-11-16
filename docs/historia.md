# La Crónica de los Heraldos

Hilo narrativo común, ligero y opcional, que une las estructuras únicas de Heraldia. No cambia nada del juego salvo un
libro escrito (un «pliego») en un cofre que cada única ya tenía. Los textos de cada pliego están en el `HISTORIA` de su
módulo (`tools/gen/unicas/<id>`); este documento es la referencia para escribir los de las únicas futuras sin
contradecir lo que ya cuentan sus carteles, guardianes, trofeos y objetos con nombre.

## Trasfondo

La **Orden de los Heraldos** nació en la Atlántida: sus heraldos eran cartógrafos y mensajeros, trazaban los mapas del
mundo y guardaban los blasones de cada reino (de ahí el nombre del mod). Cuando el mar se tragó la ciudad, la última
heraldo, **Ysolda**, salvó lo único que el océano no debía guardar: **el camino de vuelta**.

Lo escribió en pliegos, con una tinta que el agua no borra (se la dio el archimago Malvarius), y viajó por el mundo
confiando cada pliego a un guardián que juró custodiarlo hasta que llegara alguien digno. **Los juramentos
sobrevivieron a quienes los hicieron**: por eso los guardianes de las únicas siguen en su puesto, malditos, ahogados,
helados o insomnes, y por eso hay que vencerlos o burlarlos. El último pliego se quedó en casa, en la Academia de la
Atlántida.

Cada pliego cuenta qué encontró Ysolda en ese lugar, con quién dejó el pliego y dónde lo escondieron, y termina con una
página que **señala la siguiente única** con una pista de bioma y rasgo (sin nombrarla). A veces (10 %) viene con el
mapa del tesoro de esa única (el mismo sistema que los cofres épicos y los cartógrafos, `tools/gen/mapas.py`).

Reglas para no contradecir lo existente: el guardián de cada única es quien hizo el juramento (o lo heredó); el sitio
donde se guardó el pliego es el del cofre que lo lleva; los nombres propios son los de los carteles, guardianes, trofeos
y objetos de la estructura.

## La cadena

Se calcula sola a partir de las únicas registradas (`_comun/botin.historia_cadena`): por id, con la única final (la
Atlántida, `"final": True`) al cabo. Cada pliego señala el siguiente y el de la Atlántida vuelve a señalar el primero,
así que es un solo ciclo: se puede empezar por cualquiera y se llega a todas. Una única nueva entra sola en su sitio
(por su id) y las páginas se renumeran («Pliego N de M»).

| Pliego | Única | Cofre (tabla) | Con quién | Señala |
|---|---|---|---|---|
| 1 | Acueducto en ruinas | `cisterna` | el centurión Aquilio, por la tierra y el agua | Castillo |
| 2 | Castillo | `capilla` | Sir Aldric, sobre su espada (su juramento es la maldición) | Catedral gótica |
| 3 | Catedral gótica | `biblioteca` | Fray Osmundo, que no quiso saber qué contenía | Ciudadela enana |
| 4 | Ciudadela enana | `real` | Borin Barbahierro, que juró ser el último en salir | Coliseo en ruinas |
| 5 | Coliseo en ruinas | `lanista` | el Campeón de la Arena, que prefirió el pliego a la libertad | Faro de los contrabandistas |
| 6 | Faro de los contrabandistas | `despacho` | el capitán Bruma, por oro y no por honor | Fortaleza de hielo |
| 7 | Fortaleza de hielo | `galeria` | el Rey Escarcha: el hielo lo conserva | Galeón varado |
| 8 | Galeón varado | `capitan` | el capitán ahogado, que sigue al timón | Isla del corsario |
| 9 | Isla del corsario | `cartas` | el corsario Roque Salitre, entre sus cartas de la sala del mapa; juró no hacerse a la mar mientras lo tuviera | Laboratorio del micólogo |
| 10 | Laboratorio del micólogo | `biblioteca` | Maese Ambrosio, entre los frascos de su biblioteca de esporas (probó en sí mismo su último remedio) | Mansión encantada |
| 11 | Mansión encantada | `biblioteca` | el conde Malaquías, hasta la medianoche del fin del mundo | Mina perdida de Hondavena |
| 12 | Mina perdida de Hondavena | `despacho` | Tizón, el último capataz, tras la estantería de su despacho; se quedó picando junto al filón | Monasterio de montaña |
| 13 | Monasterio de montaña | `biblioteca` | Fray Tenebrio, junto al relicario | Observatorio |
| 14 | Observatorio | `oculto` | el Custodio de las Estrellas, mientras haya estrellas | Palacio oriental |
| 15 | Palacio oriental | `biblioteca_secreta` | el emperador y el comandante de la Guardia Imperial | Templo-pirámide |
| 16 | Templo-pirámide | `tumba` | el Rey Jaguar, como ofrenda | Salón del Jarl |
| 17 | Salón del Jarl | `ofrendas` | el jarl Ulfgrim, por sus antepasados; ni muerto lo suelta | Santuario druídico |
| 18 | Santuario druídico | `biblioteca` | el archidruida Cadoc, por las raíces del árbol (se corrompió al secarse el árbol) | Torre de mago |
| 19 | Torre de mago | `escondite` | el archimago Malvarius (que lo abrió y busca el resto) | La Atlántida |
| 20 | La Atlántida | `sello_academia` | Ysolda, en casa: prólogo y epílogo | Acueducto (vuelve a empezar) |

## Cómo se juega

- Cada pliego es un libro escrito («Crónica de los Heraldos: <estructura>», autora Ysolda, rareza poco común) con
  `custom_data` `{heraldia_historia:"<id>"}`, en la tabla del cofre elegido de cada única (`HISTORIA["cofre"]`), que lo
  anida desde `heraldia:historia/<id>`. Sale siempre (también con Lootr: cada jugador encuentra el suyo).
- El desafío **Cronista** (pestaña Heraldia) pide tenerlos todos en el inventario (500 de experiencia).
- Para probar: `/loot give @s loot heraldia:historia/<id>` (el pliego, a veces con el mapa) o `/loot give @s loot
  heraldia:unicas/<id>/<cofre>` (el cofre entero).

## Única nueva

`HISTORIA` es obligatorio en el contrato de `tools/gen/unicas/__init__.py` (como `TROFEO`): sin él, con un cofre que no
está en sus plantillas o con páginas que no caben en un libro (14 líneas de 114 px, calculado con los anchos de la
fuente), la compilación falla. Basta con escribir su parte y su pista:

```python
HISTORIA = {"cofre": "biblioteca",            # un cofre menor o de sala oculta que ya esté en sus plantillas
            "relato": [(es, en), (es, en)],    # 1-2 páginas: qué encontró Ysolda y con quién dejó el pliego
            "pista": (es, en)}                 # «el <bioma>, donde <rasgo>»: la usa el pliego anterior
```

La pista va tras «El siguiente pliego lo llevé hasta…» / «The next leaf I carried to…» y tras «…que busque el primer
pliego en…» / «…seek the first leaf in…»: empieza por artículo («el desierto, donde…», «a beach, where…»).

---

## Summary (English)

**The Chronicle of the Heralds** is a light, optional story thread linking every unique structure. The **Order of
Heralds** were the cartographers and messengers of Atlantis, who mapped the world and kept the arms of every realm.
When the sea swallowed the city, the last herald, **Ysolda**, saved the way back: she wrote it on leaves and entrusted
each to a guardian sworn to keep it until someone worthy came. The oaths outlived those who swore them, which is why
the guardians still keep watch. The last leaf stayed home, in the Academy of Atlantis.

Each unique structure keeps one leaf (a written book, `custom_data` `{heraldia_historia:"<id>"}`) in a chest it already
had; it tells that place's part of the story and ends with a page pointing to the next structure by biome and feature
(sometimes, 10 %, with its treasure map). The chain is computed from the registered uniques (by id, Atlantis last,
pointing back to the first), so it is a single cycle. Pages are translatable components (Spanish fallback), translated
by each client when the book is opened. The **Chronicler** challenge asks for all of them. `HISTORIA` is mandatory for
every unique: the build fails without it, with a chest that is not in its templates, or with a page that does not fit.
