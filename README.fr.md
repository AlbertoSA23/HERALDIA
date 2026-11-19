# Heraldia

[English](README.md) · [Español](README.es.md) · **Français** · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Català](README.ca.md) · [Galego](README.gl.md)

Un mod Fabric pour **Minecraft 26.3** qui remplit l'Overworld de lieux qui valent le voyage : des villages vivants reliés par des chemins, des ruines chargées d'histoire, des gardiens qui ont un nom et un trésor au bout de la carte. Tout est construit avec des blocs et des objets vanilla, pour se fondre naturellement dans votre monde.

## Ce que vous trouverez dans votre monde

- 🏘️ **Des villages vivants.** 72 villages dessinés à la main : 36 styles, un pour chaque type de biome (un village castillan dans les plaines, des maisons sur pilotis dans le marais, un village japonais parmi les cerisiers...), chacun en taille standard et en grande taille, regroupés en 12 familles. Une place avec fontaine et cloche, une église, un marché, une taverne, une forge, une bibliothèque, une auberge et vingt ou trente maisons. Chaque style a ses propres échanges, le tableau des contrats du bailli paie récoltes, bois et chemins purgés de leurs monstres, et les cartographes vendent des cartes au trésor. Ici et là, quelqu'un travaillait il y a un instant : une maison à moitié construite avec ses échafaudages, du linge qui sèche, une charrette qu'on décharge, un feu avec la marmite dessus.
- 🛤️ **Des chemins.** Des sentiers bordés de lampadaires, avec des ponts de bois, relient les villages voisins. Près de chaque village, un panneau vous indique le nom du suivant et la distance en blocs.
- 🏕️ **Au bord du chemin.** 16 types de structures moyennes entre les villages : tours de guet, auberges de bord de route, camps de brigands, ermitages, moulins, cabanes de pêcheur, relais de chasseurs, petits temples en ruine et huttes de mage, chacun au style de son biome, avec un butin modeste et parfois un petit défi. L'aubergiste, le meunier, le pêcheur, les chasseurs, la vigie et l'ermite y vivent : ils dorment dans leur lit, travaillent le jour et ont leurs propres échanges. Et de l'autre côté des portails, le Nether a des avant-postes de piglins renégats, des autels de magma, des tours de guet de basalte et des sanctuaires des champignons, et les îles extérieures de l'End, des observatoires du Vide, des mausolées de purpur et des quais des shulkers déchus.
- 🏰 **21 structures uniques**, très rares et chacune dans son biome : un château entouré de douves, une cathédrale gothique, une citadelle naine creusée dans la montagne, un galion échoué, un manoir hanté, un palais oriental, une tour de mage, une mine perdue au plus profond du sous-sol, un fort de corsaires sur son île en haute mer... À l'intérieur : salles cachées, énigmes de redstone, pièges et générateurs de créatures, et au bout, un **gardien nommé** qui veille sur la salle du trésor. Deux d'entre elles se trouvent de l'autre côté des portails : la Citadelle de Cendre dans le Nether et le Sanctuaire du Vide sur les îles extérieures de l'End, loin du dragon.
- ⚔️ **Des gardiens qui combattent par phases.** En perdant de la vie, ils entrent en fureur et appellent des renforts de leur propre structure, avec une barre de boss pendant tout le combat. Chacun lâche son propre trophée.
- ⛏️ **Des mines.** Sur de vrais flancs de colline s'ouvrent des bouches de mine, des camps de mineurs et des complexes miniers avec chevalement, en 3 tailles et au style de chaque biome, qui descendent vers des galeries avec rails, croisements et salles. Les puits de mine abandonnés vanilla sont aussi plus fréquents.
- 🗼 **Phares et épaves.** Des phares sur la terre ferme au bord de la mer, à la lumière toujours allumée, avec la maison du gardien et un ponton, et des galions brisés, échoués sur la plage ou à moitié coulés sur les hauts-fonds, avec leur cale et la cabine du capitaine. Chacun au style de sa côte : tempérée, chaude, froide ou enneigée.
- 🔱 **L'Atlantide.** Une seule par monde : une immense cité engloutie dans l'océan profond, avec des salles au sec, trois sceaux et leurs clés, et le Gardien de Poséidon, qui veille sur le plus grand trésor de Heraldia.
- 🏟️ **L'arène des vagues.** Un colisée près du point d'apparition : sonnez la cloche et tenez bon face à des vagues toujours plus fortes, avec un champion toutes les cinq vagues, des records et des récompenses. Si vous tombez sur la piste, vous gardez votre inventaire. Trois modes (coopératif, contre-la-montre et survie) avec un classement hebdomadaire, `/heraldia arena leaderboard` : les champions de la semaine précédente s'affichent sur les panneaux du panthéon de l'arène et dans le Guide du Héraut.
- 🏯 **La Maison du Héraut.** La première chose que vous voyez dans un nouveau monde : une ville fortifiée de 128 × 128 blocs au point d'apparition, avec ses tours et sa porte fortifiée, une place avec sa cloche, une tour de l'horloge, le monument au Héraut et le tableau des commandes, un hôtel de ville, une auberge à deux étages, une chapelle, une bibliothèque, une forge, une boulangerie et d'autres boutiques où vivent et travaillent 18 villageois, une écurie, une ferme, des jardins, un puits et un portail du Nether que seul un opérateur peut allumer. Personne d'autre qu'un opérateur ne peut construire ni casser à moins de 50 blocs de ses remparts, et aucun monstre n'y apparaît. Son marché a des étals que les joueurs louent avec des émeraudes quand le serveur les active. Dans un monde qui existe déjà, un opérateur la place avec `/heraldia herald place`.

## Comment jouer

- 📖 **Le Guide du Héraut.** Chaque joueur le reçoit en se connectant : un livre qui explique quoi chercher et tient votre journal, avec les structures uniques que vous avez découvertes et des indices sur celles qui manquent. Demandez un exemplaire à jour quand vous voulez avec `/heraldia guide`.
- 📊 **Ce que le serveur a trouvé.** `/heraldia status` indique combien de villages, de structures uniques, de structures moyennes et de mines les joueurs ont découverts, les gardiens vaincus, le record de l'arène et les missions remises.
- 🧭 **Votre journal.** `/heraldia journal` affiche dans le chat, type par type et avec une barre de progression, ce que vous avez trouvé et ce qui vous manque : familles de villages, structures uniques, structures moyennes, tailles de mine, phares et épaves, le Nether et l'End. Cliquez sur un type pour voir les noms. Pas de coordonnées : à vous de les trouver.
- 📋 **Missions des villages.** Touche le lutrin du tableau sur la place d'un village (ou utilise `/heraldia quest` sur place) : 2 à 4 missions apparaissent dans le chat (apporter des objets, vaincre un gardien, explorer, aller au village voisin, l'arène) et changent tous les quelques jours. Elles paient en émeraudes, expérience et réputation auprès de ce village : connu, ami et héros du village, ses villageois baissent leurs prix de 10, 20 et 30 %. Attaquer ses villageois ou ses golems la fait baisser.
- 🐪 **Caravanes.** De temps en temps, près de toi, un marchand d'Heraldia avec ses lamas (et parfois un garde) parcourt la route entre deux villages voisins. Si des brigands l'attaquent, défends-le : à l'arrivée, il te paie en émeraudes et en réputation avec son village de destination. Si le marchand meurt, la caravane est perdue.
- 🚶 **Gens de passage.** De la vie sur les routes, près de toi aussi : un pèlerin en route vers un monastère ou une cathédrale, un berger avec son troupeau, un messager pressé, un duo de gardes en patrouille ou un chasseur qui rentre avec son chien, selon la région. Ils parcourent un tronçon et s'en vont ; le berger et le chasseur font du commerce, et si tu leur fais du mal, leur village le saura.
- 🎪 **Il se passe des choses dans les villages.** De temps en temps, la place du village où tu te trouves accueille un jour de marché, un mariage, des funérailles ou une fête pendant quelques minutes : étals et marchands, une arche et les mariés, un cercueil et la cloche, un feu de joie avec des musiciens et des danseurs. Achète, offre un cadeau, demande une chanson : le village s'en souvient. Puis tout s'en va et la place reste comme elle était.
- 💬 **Parle aux villageois.** Fais un clic droit sur un villageois d'un village d'Heraldia et il te parle dans le chat : des phrases selon son métier, sa terre, l'heure, le temps et ce que le village sait de toi, avec des boutons pour continuer, demander les nouvelles ou commercer (accroupi + clic droit pour commercer directement ; les villageois vanilla commercent comme toujours). Un sur dix a voyagé et, si le village te fait confiance, te dit une fois dans quelle direction et à quelle distance se trouve une structure.
- 🏆 **Progrès.** Un onglet Heraldia avec 124 progrès : un village de chaque famille, chaque structure unique avec son gardien et son trésor, les mines, les phares et épaves, les structures moyennes, le tableau des contrats, l'arène et les caravanes.
- 🗿 **Trophées.** Chacun des 22 gardiens lâche son trophée, un objet avec un nom et une histoire. Réunissez-les tous pour compléter la Salle des trophées.
- 🗺️ **Cartes au trésor.** Chaque carte indique la structure unique de son type la plus proche. On les trouve dans les coffres épiques des villages, et les cartographes en vendent.
- 🧭 **Chasse au trésor.** Parfois, un coffre cache un fragment de carte au trésor. Utilise-le et il devient une carte avec une marque : chaque marque est une vraie structure de Heraldia qui cache l'indice suivant, et la dernière mène à un coffre enterré par Ysolda, avec un beau butin et un souvenir.
- 📜 **La Chronique des Hérauts.** Chaque structure unique garde un feuillet de la chronique écrite par Ysolda, dernière héraut de l'Atlantide. Chaque feuillet mène au suivant : réunissez les 22 et vous saurez comment elle s'achève. Vainquez tous les gardiens du monde principal et Ysolda vous laissera son dernier feuillet, le titre de Héraut de l'Atlantide et l'étendard des Hérauts, à dresser où vous voudrez.

Les textes du mod existent en 8 langues : anglais, espagnol, français, allemand, italien, portugais du Brésil, catalan et galicien.

## Installation

1. Il vous faut **Minecraft 26.3**, **Fabric Loader** 0.20.1 ou plus récent et **Fabric API**.
2. Placez `heraldia-<version>.jar` dans le dossier `mods` du **serveur** et redémarrez-le.
3. **Les joueurs n'ont pas besoin du mod** : ils peuvent se connecter avec un client vanilla. Les textes que le client ne connaît pas s'affichent en espagnol, sauf le Guide du Héraut, les missions, l'arène, les caravanes et les avis de Heraldia, qui arrivent dans la langue de chaque joueur. S'ils installent aussi le mod, ils voient tout dans leur langue et ont accès à l'écran de configuration (avec Mod Menu).

**Un monde existant** fonctionne très bien : les nouvelles structures apparaissent dans les chunks qui n'ont pas encore été générés (explorez de nouvelles terres). Si votre monde a été créé avec Heraldia **0.1.0**, mettez `unicas.rejilla_compatible` à `true` avant de démarrer le serveur, pour que `/locate`, les cartes au trésor et le Guide continuent de trouver les structures uniques que vous avez déjà.

Les **commandes** sont en anglais sur tous les serveurs : `/heraldia guide`, `/heraldia key`, `/heraldia arena place`... Les anciens noms en espagnol (`/heraldia guia`...) fonctionnent encore pour l'instant : ils font la même chose et vous donnent le nouveau nom.

**Nouvelles versions :** le serveur vérifie une fois par jour s'il existe une nouvelle version de Heraldia pour son Minecraft et prévient les opérateurs à leur connexion, avec le lien de téléchargement. **Faites une sauvegarde du serveur avant de mettre à jour.** Se désactive avec `update_check.activado`.

**Mettre à jour le serveur :** rien de ce qui est déjà construit ne change lors d'une mise à jour. Pour apporter les nouveautés aux terres déjà générées, `/heraldia update analyze` montre (sans rien modifier) ce qui serait régénéré ou placé, toujours avec une marge de 50 blocs autour de ce que les joueurs ont construit, et `/heraldia update apply` le fait après confirmation, avec une sauvegarde facultative et `/heraldia update undo`. Pas à pas : [Updating a server](docs/CONFIGURATION.md#updating-a-server) (en anglais).

**Cartes web :** si le serveur a BlueMap, Dynmap ou squaremap, les structures de Heraldia apparaissent sur la carte web, chaque type sur son calque (structures uniques, villages, structures moyennes, mines, phares et épaves et l'arène), seulement quand un joueur les a découvertes. Les opérateurs la mettent à jour avec `/heraldia webmap refresh`.

## Options les plus utiles

Le fichier `config/heraldia.json` est créé au premier démarrage du serveur, avec un texte d'aide pour chaque option. Les modifications s'appliquent au redémarrage du serveur, dans les chunks nouvellement générés. Celles qui ne touchent pas à la génération (difficulté, boss, butin, arène, Guide...) peuvent s'appliquer sans redémarrer avec `/heraldia reload`. Les opérateurs peuvent aussi modifier les plus utiles en jeu, sans le mod sur leur client, avec `/heraldia config` (un menu avec le profil et sept sections). Chaque joueur peut choisir la langue des textes de Heraldia avec `/heraldia language`.

| Option | Par défaut | Effet |
| --- | --- | --- |
| `perfil` | `estandar` | Profil de jeu : `casual`, `estandar`, `hardcore`, `ligero` (machines modestes : génération du monde plus légère ; mieux dans un monde neuf) ou `personalizado` ; les options écrites dans le fichier l'emportent. |
| `aldeas.separacion_bloques` | 1500 | Distance moyenne entre villages (1000-10000). |
| `aldeas.maximo` | 100 | Nombre maximal de villages dans le monde. |
| `aldeas.caminos.activado` | `true` | Chemins entre villages. |
| `unicas.<id>.activada` | `true` | Active ou désactive une structure unique. |
| `unicas.rejilla_compatible` | `false` | `true` uniquement pour les mondes créés avec Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | Quantité de structures moyennes (200 = deux fois plus). |
| `faros.activado`, `naufragios.activado` | `true` | Phares et galions naufragés sur la côte. |
| `dificultad.nivel` | `normal` | Gardiens et monstres : `facil`, `normal`, `dificil` ou `heroica`. |
| `botin.reponer.activado` | `false` | Les coffres de Heraldia se remplissent à nouveau au bout de quelques jours. |
| `arena.activado` | `true` | L'arène des vagues près du point d'apparition. |
| `arena.temporada.dia_reinicio` | `lunes` | Jour de clôture du classement hebdomadaire de l'arène et d'annonce de ses champions (à minuit, heure du serveur). |
| `encargos.activado` | `true` | Missions du tableau (`/heraldia quest`). |
| `reputacion.activado` | `true` | Réputation par village et ses réductions. |
| `reputacion.aldea_visible` | `true` | Le village montre sa meilleure réputation avec des blocs vanilla : fleurs, bannières, lanternes (ou volets fermés) ; jamais sur un bloc d'un joueur. |
| `dialogos.activado` | `true` | Conversations avec les villageois d'Heraldia (accroupi + clic droit pour commercer directement). |
| `caravanas.activado` | `true` | Caravanes sur les routes (opérateurs : `/heraldia caravan`). |
| `viajeros.activado` | `true` | Gens de passage sur les routes, chaque type avec son option (opérateurs : `/heraldia caravan wayfarer`). |
| `chozas_mago.prob_malvado` | 20 | Probabilité (%) que le mage d'une hutte de mage soit un mage maléfique déguisé. |
| `ambiente.activado` | `true` | Effets d'ambiance avec les sons du jeu : la cloche du village à l'aube et à la tombée de la nuit, la sirène du phare sous la pluie et les gouttes dans les mines (chacun a aussi sa propre option). |
| `guia.entregar_al_entrar` | `true` | Donne le Guide du Héraut à chaque joueur à sa connexion. |
| `update_check.activado` | `true` | Prévient les opérateurs quand une nouvelle version existe. |
| `actualizar.margen_bloques` | 50 | Marge de sécurité autour des constructions des joueurs pour `/heraldia update`. |
| `mapas_web.solo_descubiertas` | `true` | Sur la carte web, seulement les structures déjà découvertes. |
| `tesoro.probabilidad` | 3.0 | Probabilité (%) d'un fragment de carte au trésor dans chaque coffre des structures moyennes et des mines. |
| `casa_heraldo.activado` | `true` | La Maison du Héraut au point d'apparition et sa protection. |
| `casa_heraldo.mercado.activado` | `false` | Étals à louer au marché de la Maison du Héraut (prix : `casa_heraldo.mercado.*`). |
| `eventos.activado` | `true` | Événements de village : jour de marché, mariage, funérailles et fête sur les places (opérateurs : `/heraldia event` ; plus rares avec `eventos.espera_minutos` ; désactivés dans le profil léger). |

## En savoir plus

- [Référence complète du contenu](docs/CONTENT.md) (en anglais) : chaque style de village, structure unique, structure moyenne et mine, les combats de gardiens, les progrès, l'arène et plus encore.
- [Installation, commandes et configuration](docs/CONFIGURATION.md) (en anglais) : commandes de test et d'administration (`/heraldia info`, `/heraldia review`, `/heraldia status`, `/heraldia reload`, `/heraldia key`...), toutes les options et l'écran de configuration en jeu.
- [Compatibilité avec d'autres mods](docs/COMPATIBILITY.md) (en anglais) : mods de biomes, mods de structures, Lootr et les autres.
- [Compilation et tests](docs/BUILDING.md) (en anglais), [guide de développement](docs/DEVELOPMENT.md) (en anglais) et [journal des modifications](CHANGELOG.md) (en anglais).

## Licence et crédits

Aucune licence : tous droits réservés. Le code est visible, mais aucune autorisation n'est accordée pour l'utiliser, le copier ou le redistribuer.
Tout le contenu utilise uniquement des blocs et objets de Minecraft ; aucune ressource de tiers n'est incluse.
