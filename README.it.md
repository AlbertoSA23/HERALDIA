# Heraldia

[English](README.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · **Italiano** · [Português (Brasil)](README.pt-BR.md) · [Català](README.ca.md) · [Galego](README.gl.md)

Una mod per Fabric per **Minecraft 26.3** che riempie l'Overworld di luoghi che valgono il viaggio: villaggi pieni di vita uniti da strade, rovine con una storia, guardiani con un nome e un tesoro alla fine della mappa. Tutto è costruito con blocchi e oggetti vanilla, così si inserisce alla perfezione nel tuo mondo.

## Cosa troverai nel tuo mondo

- 🏘️ **Villaggi pieni di vita.** 72 villaggi disegnati a mano: 36 stili, uno per ogni tipo di bioma (un borgo castigliano in pianura, palafitte nella palude, un villaggio giapponese tra i ciliegi...), ciascuno in versione standard e grande, raggruppati in 12 famiglie. Una piazza con fontana e campana, una chiesa, un mercato, una taverna, una fucina, una biblioteca, una locanda e venti o trenta case. Ogni stile ha i suoi scambi, la bacheca degli incarichi del balivo paga raccolti, legna e strade ripulite, e i cartografi vendono mappe del tesoro.
- 🛤️ **Strade.** Sentieri con lampioni e ponti di legno uniscono i villaggi vicini. Presso ogni villaggio un cartello ti dice il nome del prossimo e quanti blocchi mancano.
- 🏕️ **Lungo la strada.** 8 tipi di strutture medie tra un villaggio e l'altro: torri di guardia, locande di strada, accampamenti di banditi, eremi, mulini, capanne di pescatori, capanni di cacciatori e tempietti in rovina, ciascuno nello stile del suo bioma, con un bottino modesto e ogni tanto una piccola sfida.
- 🏰 **19 strutture uniche**, rarissime e ognuna nel suo bioma: un castello con il fossato, una cattedrale gotica, una cittadella nanica scavata nella montagna, un galeone arenato, una villa infestata, un palazzo orientale, una torre del mago, una miniera perduta nelle profondità, un forte di pirati sulla sua isola in mare aperto... All'interno: sale nascoste, enigmi di redstone, trappole e generatori di mostri e, alla fine, un **guardiano con un nome** a difesa della camera del tesoro.
- ⚔️ **Guardiani che combattono a fasi.** Perdendo salute si infuriano e chiamano rinforzi dalla loro struttura, con una barra del boss finché dura lo scontro. Ognuno lascia il proprio trofeo.
- ⛏️ **Miniere.** Su veri pendii si aprono imbocchi, accampamenti minerari e complessi minerari con castelletto di estrazione, in 3 dimensioni e nello stile di ogni bioma, che scendono a gallerie con binari, incroci e sale. Anche le miniere abbandonate vanilla sono più frequenti.
- 🔱 **Atlantide.** Una sola per mondo: un'immensa città sommersa nell'oceano profondo, con sale asciutte, tre sigilli con le loro chiavi e il Guardiano di Poseidone, custode del più grande tesoro di Heraldia.
- 🏟️ **Arena a ondate.** Un colosseo vicino allo spawn: suona la campana e resisti a ondate sempre più forti, con un campione ogni quinta ondata, record e ricompense. Se cadi nell'arena, conservi l'inventario.

## Come si gioca

- 📖 **La Guida dell'Araldo.** Ogni giocatore la riceve entrando: un libro che spiega cosa cercare e tiene il tuo diario, con le strutture uniche che hai scoperto e indizi su quelle che ti mancano. Chiedine una copia aggiornata quando vuoi con `/heraldia guia`.
- 🏆 **Progressi.** Una scheda Heraldia con 94 progressi: un villaggio di ogni famiglia, ogni struttura unica con il suo guardiano e il suo tesoro, le miniere, le strutture medie, la bacheca degli incarichi e l'arena.
- 🗿 **Trofei.** Ognuno dei 20 guardiani lascia il suo trofeo, un oggetto con un nome e una storia. Raccoglili tutti per completare la Sala dei trofei.
- 🗺️ **Mappe del tesoro.** Ogni mappa indica la struttura unica più vicina del suo tipo. Si trovano nei forzieri epici dei villaggi e le vendono i cartografi.
- 📜 **La Cronaca degli Araldi.** Ogni struttura unica custodisce un foglio della cronaca scritta da Ysolda, l'ultima degli araldi di Atlantide. Ogni foglio indica il successivo: raccoglili tutti e 20 e saprai come finisce.

I testi della mod sono in 8 lingue: inglese, spagnolo, francese, tedesco, italiano, portoghese brasiliano, catalano e galiziano.

## Installazione

1. Ti servono **Minecraft 26.3**, **Fabric Loader** 0.20.1 o successivo e **Fabric API**.
2. Metti `heraldia-<version>.jar` nella cartella `mods` del **server** e riavvialo.
3. **I giocatori non hanno bisogno della mod**: possono entrare con un client vanilla. I testi che il client non conosce appaiono in spagnolo, tranne la Guida dell'Araldo, che arriva nella lingua di ciascun giocatore. Se installano anche loro la mod, vedono tutto nella propria lingua e hanno la schermata di configurazione (con Mod Menu).

**Un mondo già esistente** va benissimo: le nuove strutture compaiono nei chunk non ancora generati (esplora nuove terre). Se il tuo mondo è stato creato con Heraldia **0.1.0**, imposta `unicas.rejilla_compatible` a `true` prima di avviare il server, così `/locate`, le mappe del tesoro e la Guida continuano a trovare le strutture uniche che hai già.

## Le opzioni più utili

Il file `config/heraldia.json` viene creato al primo avvio del server, con un testo di aiuto per ogni opzione. Le modifiche si applicano al riavvio del server, nei chunk generati da quel momento.

| Opzione | Predefinito | Cosa fa |
| --- | --- | --- |
| `aldeas.separacion_bloques` | 1500 | Distanza media tra i villaggi (1000-10000). |
| `aldeas.maximo` | 100 | Numero massimo di villaggi nel mondo. |
| `aldeas.caminos.activado` | `true` | Strade tra i villaggi. |
| `unicas.<id>.activada` | `true` | Attiva o disattiva una struttura unica. |
| `unicas.rejilla_compatible` | `false` | `true` solo per i mondi creati con Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | Quante strutture medie (200 = il doppio). |
| `dificultad.nivel` | `normal` | Guardiani e mostri: `facil`, `normal`, `dificil` o `heroica`. |
| `botin.reponer.activado` | `false` | I forzieri di Heraldia si riempiono di nuovo dopo qualche giorno. |
| `arena.activado` | `true` | L'arena a ondate vicino allo spawn. |
| `guia.entregar_al_entrar` | `true` | Dà la Guida dell'Araldo a ogni giocatore quando entra. |

## Per saperne di più

- [Riferimento completo dei contenuti](docs/CONTENT.md) (in inglese): ogni stile di villaggio, struttura unica, struttura media e miniera, gli scontri con i guardiani, i progressi, l'arena e altro ancora.
- [Installazione, comandi e configurazione](docs/CONFIGURATION.md) (in inglese): comandi di prova e di amministrazione (`/heraldia info`, `/heraldia llave`...), tutte le opzioni e la schermata di configurazione nel gioco.
- [Compatibilità con altre mod](docs/COMPATIBILITY.md) (in inglese): mod di biomi, mod di strutture, Lootr e le altre.
- [Compilazione e test](docs/BUILDING.md) (in inglese), [guida allo sviluppo](docs/DESARROLLO.md) (in spagnolo) e [registro delle modifiche](CHANGELOG.md) (in inglese).

## Licenza e riconoscimenti

Nessuna licenza: tutti i diritti riservati. Il codice è visibile, ma non si concede alcun permesso di usarlo, copiarlo o ridistribuirlo.
Tutti i contenuti usano solo blocchi e oggetti di Minecraft; non sono inclusi asset di terze parti.
