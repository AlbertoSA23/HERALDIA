# Heraldia

[English](README.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · **Català** · [Galego](README.gl.md)

Un mod de Fabric per a **Minecraft 26.3** que omple la superfície de llocs que valen el viatge: pobles vius units per camins, ruïnes amb història, guardians amb nom i un tresor al final del mapa. Tot està fet amb blocs i objectes vanilla, així que encaixa de ple en el teu món.

## Què trobaràs al teu món

- 🏘️ **Pobles vius.** 72 pobles dissenyats a mà: 36 estils, un per a cada mena de bioma (un poble castellà a les planes, palafits a l'aiguamoll, un poble japonès entre els cirerers...), cadascun en mida estàndard i gran, agrupats en 12 famílies. Una plaça amb font i campana, una església, un mercat, una taverna, una ferreria, una biblioteca, un hostal i vint o trenta cases. Cada estil té els seus propis intercanvis, el tauler d'encàrrecs de l'agutzil paga collites, llenya i netejar els camins, i els cartògrafs venen mapes del tresor. Aquí i allà, algú estava treballant fa un moment: una casa a mig construir amb les bastides, roba estesa, un carro a mig descarregar, una foguera amb l'olla posada.
- 🛤️ **Camins.** Senders amb fanals i ponts de fusta uneixen els pobles veïns. Prop de cada poble, un rètol et diu el nom del següent i quants blocs falten.
- 🏕️ **Vora el camí.** 16 tipus d'estructures mitjanes entre els pobles: torres de guaita, hostals de camí, campaments de bandits, ermites, molins, cabanes de pescador, refugis de caçadors, templets en ruïnes i cabanes de mag, cadascuna amb l'estil del seu bioma, amb un botí modest i, de tant en tant, un petit repte. Hi viuen l'hostaler, el moliner, el pescador, els caçadors, el guaita i l'ermità: dormen al seu llit, treballen de dia i tenen els seus propis tractes. I a l'altra banda dels portals, el Nether té llocs avançats de piglins renegats, altars de magma, talaies de basalt i santuaris dels fongs, i les illes exteriors de l'End, observatoris del Buit, mausoleus de purpur i embarcadors dels shulkers caiguts.
- 🏰 **21 estructures úniques**, molt rares i cadascuna al seu bioma: un castell amb fossat, una catedral gòtica, una ciutadella nana excavada a la muntanya, un galió encallat, una mansió encantada, un palau oriental, una torre de mag, una mina perduda a les profunditats, un fort pirata en una illa enmig del mar... A dins: sales ocultes, trencaclosques de redstone, paranys i generadors, i al final, un **guardià amb nom** que vigila la cambra del tresor. Dues d'elles són a l'altra banda dels portals: la Ciutadella de Cendra al Nether i el Sagrari del Buit a les illes exteriors de l'End, lluny del drac.
- ⚔️ **Guardians que lluiten per fases.** Quan perden vida s'enfureixen i criden reforços de la seva pròpia estructura, amb una barra de cap mentre dura el combat. Cadascun deixa anar el seu propi trofeu.
- ⛏️ **Mines.** En vessants de debò s'obren boques de mina, campaments miners i complexos miners amb castellet d'extracció, en 3 mides i amb l'estil de cada bioma, que baixen a galeries amb vies, cruïlles i sales. Les mines abandonades vanilla també són més freqüents.
- 🗼 **Fars i naufragis.** Fars a terra ferma vora el mar, amb la llum sempre encesa, la casa del faroner i un embarcador, i galions trencats, encallats a la platja o mig enfonsats als baixos, amb la bodega i la cabina del capità. Cadascun amb l'estil de la seva costa: temperada, càlida, freda o nevada.
- 🔱 **L'Atlàntida.** Només n'hi ha una per món: una ciutat enorme enfonsada a l'oceà profund, amb sales seques, tres segells amb les seves claus i el Guardià de Posidó, que custodia el tresor més gran d'Heraldia.
- 🏟️ **Arena d'onades.** Un colosseu prop del punt d'aparició: toca la campana i resisteix onades cada cop més fortes, amb un campió cada cinc onades, rècords i recompenses. Si caus a la pista, conserves l'inventari. Tres modes (cooperatiu, contrarellotge i supervivència) amb classificació setmanal, `/heraldia arena leaderboard`: els campions de la setmana anterior surten als cartells del saló de la fama de l'arena i a la Guia de l'Herald.
- 🏯 **La Casa de l'Herald.** El primer que veus en un món nou: un poble emmurallat de 96 × 96 blocs al punt d'aparició, amb la seva campana, el tauler d'encàrrecs, un hostal i una fonda, una capella, botigues amb els seus vilatans, jardins, un estable, un pou i un portal al Nether que només encén un operador. Ningú excepte un operador pot construir ni trencar a menys de 50 blocs de les seves muralles, i allà no hi apareixen monstres. El seu mercat té parades que els jugadors lloguen amb maragdes quan el servidor les activa. En un món que ja existeix, la col·loca un operador amb `/heraldia herald place`.

## Com es juga

- 📖 **La Guia de l'Herald.** Tots els jugadors la reben en entrar: un llibre que explica què has de buscar i porta el teu diari, amb les estructures úniques que has descobert i pistes de les que et falten. Demana'n una còpia al dia quan vulguis amb `/heraldia guide`.
- 📊 **El que ha trobat el servidor.** `/heraldia status` diu quants pobles, estructures úniques, estructures mitjanes i mines han descobert els jugadors, els guardians vençuts, el rècord de l'arena i els encàrrecs lliurats.
- 🧭 **El teu diari.** `/heraldia journal` et mostra al xat, tipus per tipus i amb una barra de progrés, el que has trobat i el que et falta: famílies de pobles, estructures úniques, estructures mitjanes, mides de mina, fars i naufragis, el Nether i l'End. Fes clic en un tipus per veure'n els noms. Sense coordenades: trobar-les és cosa teva.
- 📋 **Encàrrecs dels pobles.** Toca el faristol del tauler de la plaça d'un poble (o fes-hi servir `/heraldia quest`): surten al xat de 2 a 4 encàrrecs (portar objectes, vèncer un guardià, explorar, viatjar a un poble veí, l'arena) que canvien cada pocs dies. Paguen maragdes, experiència i reputació amb aquell poble: com a conegut, amic i heroi del poble, els seus vilatans rebaixen els preus un 10, 20 i 30 %. Atacar els seus vilatans o gòlems la fa baixar.
- 🐪 **Caravanes.** De tant en tant, a prop teu, un mercader d'Heraldia amb les seves llames (i a vegades un guarda) recorre el camí entre dos pobles veïns. Si l'assalten els bandits, defensa'l: en arribar et paga maragdes i reputació amb el seu poble de destinació. Si el mercader mor, la caravana es perd.
- 🚶 **Gent de pas.** Vida als camins, també a prop teu: un pelegrí camí d'un monestir o d'una catedral, un pastor amb el seu ramat, un missatger amb pressa, una parella de guardes de patrulla o un caçador que torna amb el seu gos, segons la zona. Recorren un tram i se'n van; el pastor i el caçador comercien, i si els fas mal se sabrà al seu poble.
- 🎪 **Als pobles passen coses.** De tant en tant, la plaça del poble on ets acull durant uns minuts un dia de mercat, un casament, un funeral o una festa: parades i mercaders, un arc i els nuvis, un fèretre i la campana, una foguera amb músics i balladors. Compra, fes un regal, demana una cançó: el poble se'n recorda. Després tot se'n va i la plaça queda com era.
- 💬 **Parla amb els vilatans.** Fes clic dret sobre un vilatà d'un poble d'Heraldia i et parla al xat: frases segons el seu ofici, la seva terra, l'hora, el temps i el que el poble et coneix, amb botons per continuar parlant, preguntar què es diu o comerciar (ajupit + clic dret comercia directament; els vilatans vanilla comercien com sempre). Un de cada deu ha viatjat i, si el poble es fia de tu, t'explica una vegada cap a on i a quina distància hi ha una estructura.
- 🏆 **Assoliments.** Una pestanya Heraldia amb 124 assoliments: un poble de cada família, cada estructura única amb el seu guardià i el seu tresor, les mines, els fars i naufragis, les estructures mitjanes, el tauler d'encàrrecs, l'arena i les caravanes.
- 🗿 **Trofeus.** Cadascun dels 22 guardians deixa anar el seu trofeu, un objecte amb nom i història. Reuneix-los tots per completar la Sala de trofeus.
- 🗺️ **Mapes del tresor.** Cada mapa marca l'estructura única més propera del seu tipus. Surten als cofres èpics dels pobles i els venen els cartògrafs.
- 🧭 **Caça del tresor.** De vegades un cofre amaga un fragment de mapa del tresor. Fes-lo servir i es tornarà un mapa amb una marca: cada marca és una estructura real de Heraldia que amaga la pista següent, i l'última porta a un cofre que va enterrar l'Ysolda, amb un bon botí i un record.
- 📜 **La Crònica dels Heralds.** Cada estructura única guarda un plec de la crònica escrita per Ysolda, l'última herald de l'Atlàntida. Cada plec assenyala el següent: reuneix-ne els 22 i sabràs com acaba. Venç tots els guardians del món principal i Ysolda et deixarà el seu últim plec, el títol d'Herald de l'Atlàntida i l'estendard dels Heralds, per alçar-lo on vulguis.

Els textos del mod estan en 8 llengües: anglès, castellà, francès, alemany, italià, portuguès del Brasil, català i gallec.

## Instal·lació

1. Necessites **Minecraft 26.3**, **Fabric Loader** 0.20.1 o posterior i **Fabric API**.
2. Posa `heraldia-<version>.jar` a la carpeta `mods` del **servidor** i reinicia'l.
3. **Els jugadors no necessiten el mod**: poden entrar amb un client vanilla. Els textos que el client no coneix surten en castellà, excepte la Guia de l'Herald, els encàrrecs, l'arena, les caravanes i els avisos de Heraldia, que arriben en la llengua de cada jugador. Si també instal·len el mod, ho veuen tot en la seva llengua i tenen la pantalla de configuració (amb Mod Menu).

**Un món ja existent** funciona sense problemes: les estructures noves apareixen als chunks que encara no s'han generat (explora terres noves). Si el teu món es va crear amb Heraldia **0.1.0**, posa `unicas.rejilla_compatible` a `true` abans d'engegar el servidor, perquè `/locate`, els mapes del tresor i la Guia continuïn trobant les estructures úniques que ja tens.

Les **ordres** són en anglès a tots els servidors: `/heraldia guide`, `/heraldia key`, `/heraldia arena place`... Els noms antics en castellà (`/heraldia guia`...) encara funcionen de moment: fan el mateix i et diuen el nom nou.

**Versions noves:** el servidor mira un cop al dia si hi ha una versió nova de Heraldia per al seu Minecraft i ho diu als operadors en entrar, amb l'enllaç de baixada. **Fes una còpia de seguretat del servidor abans d'actualitzar.** Es desactiva amb `update_check.activado`.

**Actualitzar el servidor:** en actualitzar no canvia res del que ja s'ha construït. Per portar les novetats al que ja està generat, `/heraldia update analyze` mostra (sense canviar res) què es regeneraria o col·locaria, sempre amb un marge de 50 blocs al voltant del que hagin construït els jugadors, i `/heraldia update apply` ho fa després d'una confirmació, amb còpia de seguretat opcional i `/heraldia update undo`. Pas a pas: [Updating a server](docs/CONFIGURATION.md#updating-a-server) (en anglès).

**Mapes web:** si el servidor té BlueMap, Dynmap o squaremap, les estructures de Heraldia surten al mapa web, cada tipus a la seva capa (úniques, pobles, mitjanes, mines, fars i naufragis i l'arena), només quan algun jugador les ha descobertes. Els operadors l'actualitzen amb `/heraldia webmap refresh`.

## Opcions més útils

El fitxer `config/heraldia.json` es crea en la primera arrencada del servidor, amb un text d'ajuda per a cada opció. Els canvis s'apliquen en reiniciar el servidor, als chunks que es generin de nou. Les que no afecten la generació (dificultat, caps, botí, arena, Guia...) es poden aplicar sense reiniciar amb `/heraldia reload`. Els operadors també poden canviar les més útils al joc, sense el mod al client, amb `/heraldia config` (un menú amb el perfil i set apartats). Cada jugador pot triar l'idioma dels textos de Heraldia amb `/heraldia language`.

| Opció | Per defecte | Què fa |
| --- | --- | --- |
| `perfil` | `estandar` | Perfil de joc: `casual`, `estandar`, `hardcore`, `ligero` (equips modestos: generació del món més lleugera; millor en un món nou) o `personalizado`; les opcions escrites al fitxer hi manen. |
| `aldeas.separacion_bloques` | 1500 | Distància mitjana entre pobles (1000-10000). |
| `aldeas.maximo` | 100 | Nombre màxim de pobles al món. |
| `aldeas.caminos.activado` | `true` | Camins entre pobles. |
| `unicas.<id>.activada` | `true` | Activa o desactiva una estructura única. |
| `unicas.rejilla_compatible` | `false` | `true` només per a mons creats amb Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | Quantitat d'estructures mitjanes (200 = el doble). |
| `faros.activado`, `naufragios.activado` | `true` | Fars i galions naufragats a la costa. |
| `dificultad.nivel` | `normal` | Guardians i monstres: `facil`, `normal`, `dificil` o `heroica`. |
| `botin.reponer.activado` | `false` | Els cofres d'Heraldia es tornen a omplir al cap d'uns dies. |
| `arena.activado` | `true` | L'arena d'onades prop del punt d'aparició. |
| `arena.temporada.dia_reinicio` | `lunes` | Dia en què es tanca la classificació setmanal de l'arena i se n'anuncien els campions (a mitjanit, hora del servidor). |
| `encargos.activado` | `true` | Encàrrecs del tauler (`/heraldia quest`). |
| `reputacion.activado` | `true` | Reputació per poble i els seus descomptes. |
| `reputacion.aldea_visible` | `true` | El poble mostra la seva millor reputació amb blocs vanilla: flors, estendards, fanals (o porticons tancats); mai sobre el bloc d'un jugador. |
| `dialogos.activado` | `true` | Converses amb els vilatans d'Heraldia (ajupit + clic dret comercia directament). |
| `caravanas.activado` | `true` | Caravanes pels camins (operadors: `/heraldia caravan`). |
| `viajeros.activado` | `true` | Gent de pas pels camins, cada tipus amb la seva opció (operadors: `/heraldia caravan wayfarer`). |
| `chozas_mago.prob_malvado` | 20 | Probabilitat (%) que el mag d'una cabana de mag sigui un mag malvat disfressat. |
| `ambiente.activado` | `true` | Efectes d'ambient amb els sons del joc: la campana del poble a l'alba i en fer-se fosc, la sirena del far amb pluja i els degotalls de les mines (cadascun té també la seva opció). |
| `guia.entregar_al_entrar` | `true` | Dona la Guia de l'Herald a cada jugador en entrar. |
| `update_check.activado` | `true` | Avisa els operadors quan hi ha una versió nova. |
| `actualizar.margen_bloques` | 50 | Marge de seguretat al voltant del que construeixen els jugadors per a `/heraldia update`. |
| `mapas_web.solo_descubiertas` | `true` | Al mapa web només surten les estructures ja descobertes. |
| `tesoro.probabilidad` | 3.0 | Probabilitat (%) d'un fragment de mapa del tresor a cada cofre de les estructures mitjanes i les mines. |
| `casa_heraldo.activado` | `true` | La Casa de l'Herald al punt d'aparició i la seva protecció. |
| `casa_heraldo.mercado.activado` | `false` | Parades de lloguer al mercat de la Casa de l'Herald (preus: `casa_heraldo.mercado.*`). |
| `eventos.activado` | `true` | Esdeveniments als pobles: dia de mercat, casament, funeral i festa a les places (operadors: `/heraldia event`; més rars amb `eventos.espera_minutos`; desactivats al perfil lleuger). |

## Per saber-ne més

- [Referència completa del contingut](docs/CONTENT.md) (en anglès): tots els estils de poble, les estructures úniques, les mitjanes i les mines, els combats amb els guardians, els assoliments, l'arena i més.
- [Instal·lació, ordres i configuració](docs/CONFIGURATION.md) (en anglès): ordres de prova i d'administració (`/heraldia info`, `/heraldia review`, `/heraldia status`, `/heraldia reload`, `/heraldia key`...), totes les opcions i la pantalla de configuració del joc.
- [Compatibilitat amb altres mods](docs/COMPATIBILITY.md) (en anglès): mods de biomes, mods d'estructures, Lootr i la resta.
- [Compilació i proves](docs/BUILDING.md) (en anglès), [guia de desenvolupament (en anglès)](docs/DEVELOPMENT.md) i [registre de canvis](CHANGELOG.md).

## Llicència i crèdits

Sense llicència: tots els drets reservats. El codi és visible, però no es concedeix cap permís per utilitzar-lo, copiar-lo ni redistribuir-lo.
Tot el contingut fa servir només blocs i objectes de Minecraft; no s'hi inclou cap recurs de tercers.
