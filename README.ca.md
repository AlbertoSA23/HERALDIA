# Heraldia

[English](README.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · **Català** · [Galego](README.gl.md)

Un mod de Fabric per a **Minecraft 26.3** que omple la superfície de llocs que valen el viatge: pobles vius units per camins, ruïnes amb història, guardians amb nom i un tresor al final del mapa. Tot està fet amb blocs i objectes vanilla, així que encaixa de ple en el teu món.

## Què trobaràs al teu món

- 🏘️ **Pobles vius.** 72 pobles dissenyats a mà: 36 estils, un per a cada mena de bioma (un poble castellà a les planes, palafits a l'aiguamoll, un poble japonès entre els cirerers...), cadascun en mida estàndard i gran, agrupats en 12 famílies. Una plaça amb font i campana, una església, un mercat, una taverna, una ferreria, una biblioteca, un hostal i vint o trenta cases. Cada estil té els seus propis intercanvis, el tauler d'encàrrecs de l'agutzil paga collites, llenya i netejar els camins, i els cartògrafs venen mapes del tresor.
- 🛤️ **Camins.** Senders amb fanals i ponts de fusta uneixen els pobles veïns. Prop de cada poble, un rètol et diu el nom del següent i quants blocs falten.
- 🏕️ **Vora el camí.** 8 tipus d'estructures mitjanes entre els pobles: torres de guaita, hostals de camí, campaments de bandits, ermites, molins, cabanes de pescador, refugis de caçadors i templets en ruïnes, cadascuna amb l'estil del seu bioma, amb un botí modest i, de tant en tant, un petit repte.
- 🏰 **19 estructures úniques**, molt rares i cadascuna al seu bioma: un castell amb fossat, una catedral gòtica, una ciutadella nana excavada a la muntanya, un galió encallat, una mansió encantada, un palau oriental, una torre de mag, una mina perduda a les profunditats, un fort pirata en una illa enmig del mar... A dins: sales ocultes, trencaclosques de redstone, paranys i generadors, i al final, un **guardià amb nom** que vigila la cambra del tresor.
- ⚔️ **Guardians que lluiten per fases.** Quan perden vida s'enfureixen i criden reforços de la seva pròpia estructura, amb una barra de cap mentre dura el combat. Cadascun deixa anar el seu propi trofeu.
- ⛏️ **Mines.** En vessants de debò s'obren boques de mina, campaments miners i complexos miners amb castellet d'extracció, en 3 mides i amb l'estil de cada bioma, que baixen a galeries amb vies, cruïlles i sales. Les mines abandonades vanilla també són més freqüents.
- 🔱 **L'Atlàntida.** Només n'hi ha una per món: una ciutat enorme enfonsada a l'oceà profund, amb sales seques, tres segells amb les seves claus i el Guardià de Posidó, que custodia el tresor més gran d'Heraldia.
- 🏟️ **Arena d'onades.** Un colosseu prop del punt d'aparició: toca la campana i resisteix onades cada cop més fortes, amb un campió cada cinc onades, rècords i recompenses. Si caus a la pista, conserves l'inventari.

## Com es juga

- 📖 **La Guia de l'Herald.** Tots els jugadors la reben en entrar: un llibre que explica què has de buscar i porta el teu diari, amb les estructures úniques que has descobert i pistes de les que et falten. Demana'n una còpia al dia quan vulguis amb `/heraldia guia`.
- 🏆 **Assoliments.** Una pestanya Heraldia amb 94 assoliments: un poble de cada família, cada estructura única amb el seu guardià i el seu tresor, les mines, les estructures mitjanes, el tauler d'encàrrecs i l'arena.
- 🗿 **Trofeus.** Cadascun dels 20 guardians deixa anar el seu trofeu, un objecte amb nom i història. Reuneix-los tots per completar la Sala de trofeus.
- 🗺️ **Mapes del tresor.** Cada mapa marca l'estructura única més propera del seu tipus. Surten als cofres èpics dels pobles i els venen els cartògrafs.
- 📜 **La Crònica dels Heralds.** Cada estructura única guarda un plec de la crònica escrita per Ysolda, l'última herald de l'Atlàntida. Cada plec assenyala el següent: reuneix-ne els 20 i sabràs com acaba.

Els textos del mod estan en 8 llengües: anglès, castellà, francès, alemany, italià, portuguès del Brasil, català i gallec.

## Instal·lació

1. Necessites **Minecraft 26.3**, **Fabric Loader** 0.20.1 o posterior i **Fabric API**.
2. Posa `heraldia-<version>.jar` a la carpeta `mods` del **servidor** i reinicia'l.
3. **Els jugadors no necessiten el mod**: poden entrar amb un client vanilla. Els textos que el client no coneix surten en castellà, excepte la Guia de l'Herald, que arriba en la llengua de cada jugador. Si també instal·len el mod, ho veuen tot en la seva llengua i tenen la pantalla de configuració (amb Mod Menu).

**Un món ja existent** funciona sense problemes: les estructures noves apareixen als chunks que encara no s'han generat (explora terres noves). Si el teu món es va crear amb Heraldia **0.1.0**, posa `unicas.rejilla_compatible` a `true` abans d'engegar el servidor, perquè `/locate`, els mapes del tresor i la Guia continuïn trobant les estructures úniques que ja tens.

## Opcions més útils

El fitxer `config/heraldia.json` es crea en la primera arrencada del servidor, amb un text d'ajuda per a cada opció. Els canvis s'apliquen en reiniciar el servidor, als chunks que es generin de nou.

| Opció | Per defecte | Què fa |
| --- | --- | --- |
| `perfil` | `estandar` | Perfil de joc: `casual`, `estandar`, `hardcore` o `personalizado`; les opcions escrites al fitxer hi manen. |
| `aldeas.separacion_bloques` | 1500 | Distància mitjana entre pobles (1000-10000). |
| `aldeas.maximo` | 100 | Nombre màxim de pobles al món. |
| `aldeas.caminos.activado` | `true` | Camins entre pobles. |
| `unicas.<id>.activada` | `true` | Activa o desactiva una estructura única. |
| `unicas.rejilla_compatible` | `false` | `true` només per a mons creats amb Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | Quantitat d'estructures mitjanes (200 = el doble). |
| `dificultad.nivel` | `normal` | Guardians i monstres: `facil`, `normal`, `dificil` o `heroica`. |
| `botin.reponer.activado` | `false` | Els cofres d'Heraldia es tornen a omplir al cap d'uns dies. |
| `arena.activado` | `true` | L'arena d'onades prop del punt d'aparició. |
| `guia.entregar_al_entrar` | `true` | Dona la Guia de l'Herald a cada jugador en entrar. |

## Per saber-ne més

- [Referència completa del contingut](docs/CONTENT.md) (en anglès): tots els estils de poble, les estructures úniques, les mitjanes i les mines, els combats amb els guardians, els assoliments, l'arena i més.
- [Instal·lació, ordres i configuració](docs/CONFIGURATION.md) (en anglès): ordres de prova i d'administració (`/heraldia info`, `/heraldia llave`...), totes les opcions i la pantalla de configuració del joc.
- [Compatibilitat amb altres mods](docs/COMPATIBILITY.md) (en anglès): mods de biomes, mods d'estructures, Lootr i la resta.
- [Compilació i proves](docs/BUILDING.md) (en anglès), [guia de desenvolupament (en castellà)](docs/DESARROLLO.md) i [registre de canvis](CHANGELOG.md).

## Llicència i crèdits

Sense llicència: tots els drets reservats. El codi és visible, però no es concedeix cap permís per utilitzar-lo, copiar-lo ni redistribuir-lo.
Tot el contingut fa servir només blocs i objectes de Minecraft; no s'hi inclou cap recurs de tercers.
