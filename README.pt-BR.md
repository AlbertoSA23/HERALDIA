# Heraldia

[English](README.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · **Português (Brasil)** · [Català](README.ca.md) · [Galego](README.gl.md)

Um mod de Fabric para o **Minecraft 26.3** que enche a Superfície de lugares que valem a viagem: vilas cheias de vida ligadas por caminhos, ruínas com história, guardiões com nome e um tesouro no fim do mapa. Tudo é feito com blocos e itens do vanilla, então combina direitinho com o seu mundo.

## O que você vai encontrar no seu mundo

- 🏘️ **Vilas cheias de vida.** 72 vilas desenhadas à mão: 36 estilos, um para cada tipo de bioma (uma vila castelhana nas planícies, palafitas no pântano, uma vila japonesa entre as cerejeiras...), cada um em tamanho padrão e grande, agrupados em 12 famílias. Praça com fonte e sino, igreja, mercado, taverna, ferraria, biblioteca, estalagem e vinte ou trinta casas. Cada estilo tem suas próprias trocas, o quadro de tarefas do meirinho paga por colheitas, lenha e por livrar os caminhos de monstros, e os cartógrafos vendem mapas do tesouro.
- 🛤️ **Caminhos.** Trilhas com postes de luz e pontes de madeira ligam as vilas vizinhas. Perto de cada vila, uma placa diz o nome da próxima e quantos blocos faltam.
- 🏕️ **Beira da estrada.** 8 tipos de estruturas médias entre as vilas: torres de vigia, estalagens de estrada, acampamentos de bandidos, ermidas, moinhos, cabanas de pescador, postos de caçadores e oratórios em ruínas, cada um no estilo do seu bioma, com saque modesto e, às vezes, um pequeno desafio.
- 🏰 **19 estruturas únicas**, muito raras e cada uma em seu bioma: um castelo com fosso, uma catedral gótica, uma cidadela anã escavada na montanha, um galeão encalhado, uma mansão assombrada, um palácio oriental, uma torre de mago, uma mina perdida nas profundezas, um forte de piratas em sua própria ilha em mar aberto... Lá dentro: salas ocultas, enigmas de redstone, armadilhas e geradores de criaturas e, no fim, um **guardião com nome** protegendo a câmara do tesouro.
- ⚔️ **Guardiões que lutam em fases.** Ao perder vida, eles se enfurecem e chamam reforços da própria estrutura, com barra de chefe enquanto durar o combate. Cada um solta seu próprio troféu.
- ⛏️ **Minas.** Em encostas de verdade se abrem bocas de mina, acampamentos mineiros e complexos mineiros com torre de extração, em 3 tamanhos e no estilo de cada bioma, que descem a galerias com trilhos, cruzamentos e salas. As minas abandonadas do vanilla também ficam mais comuns.
- 🔱 **Atlântida.** Só uma por mundo: uma cidade enorme afundada no oceano profundo, com salões secos, três selos com suas chaves e o Guardião de Poseidon, que guarda o maior tesouro de Heraldia.
- 🏟️ **Arena de hordas.** Um coliseu perto do spawn: toque o sino e resista a hordas cada vez mais fortes, com um campeão a cada cinco hordas, recordes e recompensas. Se você cair na arena, mantém o seu inventário.

## Como jogar

- 📖 **O Guia do Arauto.** Todo jogador o recebe ao entrar: um livro que explica o que procurar e guarda o seu diário, com as estruturas únicas que você descobriu e pistas das que ainda faltam. Peça uma cópia atualizada quando quiser com `/heraldia guia`.
- 📊 **O que o servidor já encontrou.** `/heraldia status` mostra quantas vilas, estruturas únicas, estruturas médias e minas os jogadores descobriram, os guardiões derrotados e o recorde da arena.
- 🏆 **Progressos.** Uma aba Heraldia com 94 progressos: uma vila de cada família, cada estrutura única com seu guardião e seu tesouro, as minas, as estruturas médias, o quadro de tarefas e a arena.
- 🗿 **Troféus.** Cada um dos 20 guardiões solta seu troféu, um item com nome e história. Reúna todos para completar a Sala de troféus.
- 🗺️ **Mapas do tesouro.** Cada mapa marca a estrutura única mais próxima do seu tipo. Eles aparecem nos baús épicos das vilas e os cartógrafos os vendem.
- 📜 **A Crônica dos Arautos.** Cada estrutura única guarda um fólio da crônica escrita por Ysolda, a última dos arautos da Atlântida. Cada fólio aponta o seguinte: reúna os 20 e você saberá como ela termina.

Os textos do mod estão em 8 idiomas: inglês, espanhol, francês, alemão, italiano, português do Brasil, catalão e galego.

## Instalação

1. Você precisa do **Minecraft 26.3**, do **Fabric Loader** 0.20.1 ou superior e da **Fabric API**.
2. Coloque `heraldia-<version>.jar` na pasta `mods` do **servidor** e reinicie-o.
3. **Os jogadores não precisam do mod**: eles podem entrar com um cliente vanilla. Os textos que o cliente não conhece aparecem em espanhol, exceto o Guia do Arauto, que chega no idioma de cada jogador. Se instalarem o mod também, verão tudo no próprio idioma e terão a tela de configuração (com o Mod Menu).

**Um mundo já existente** funciona bem: as novas estruturas aparecem nos chunks que ainda não foram gerados (explore terras novas). Se o seu mundo foi criado com o Heraldia **0.1.0**, defina `unicas.rejilla_compatible` como `true` antes de iniciar o servidor, para que `/locate`, os mapas do tesouro e o Guia continuem encontrando as estruturas únicas que você já tem.

## Opções mais úteis

O arquivo `config/heraldia.json` é criado na primeira inicialização do servidor, com um texto de ajuda para cada opção. As mudanças entram em vigor quando o servidor é reiniciado, nos chunks gerados depois. As que não afetam a geração (dificuldade, chefes, saque, arena, Guia...) podem ser aplicadas sem reiniciar com `/heraldia reload`.

| Opção | Padrão | O que faz |
| --- | --- | --- |
| `perfil` | `estandar` | Perfil de jogo: `casual`, `estandar`, `hardcore` ou `personalizado`; as opções escritas no arquivo prevalecem. |
| `aldeas.separacion_bloques` | 1500 | Distância média entre vilas (1000-10000). |
| `aldeas.maximo` | 100 | Número máximo de vilas no mundo. |
| `aldeas.caminos.activado` | `true` | Caminhos entre vilas. |
| `unicas.<id>.activada` | `true` | Ativa ou desativa uma estrutura única. |
| `unicas.rejilla_compatible` | `false` | `true` só para mundos criados com o Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | Quantidade de estruturas médias (200 = o dobro). |
| `dificultad.nivel` | `normal` | Guardiões e monstros: `facil`, `normal`, `dificil` ou `heroica`. |
| `botin.reponer.activado` | `false` | Os baús do Heraldia são repostos depois de alguns dias. |
| `arena.activado` | `true` | A arena de hordas perto do spawn. |
| `guia.entregar_al_entrar` | `true` | Dá o Guia do Arauto a cada jogador ao entrar. |

## Saiba mais

- [Referência completa do conteúdo](docs/CONTENT.md) (em inglês): cada estilo de vila, estrutura única, estrutura média e mina, as lutas contra os guardiões, os progressos, a arena e mais.
- [Instalação, comandos e configuração](docs/CONFIGURATION.md) (em inglês): comandos de teste e de administração (`/heraldia info`, `/heraldia review`, `/heraldia status`, `/heraldia reload`, `/heraldia llave`...), todas as opções e a tela de configuração no jogo.
- [Compatibilidade com outros mods](docs/COMPATIBILITY.md) (em inglês): mods de biomas, mods de estruturas, Lootr e os demais.
- [Compilação e testes](docs/BUILDING.md) (em inglês), [guia de desenvolvimento](docs/DESARROLLO.md) (em espanhol) e [registro de mudanças](CHANGELOG.md) (em inglês).

## Licença e créditos

Sem licença: todos os direitos reservados. O código está visível, mas não se concede permissão para usá-lo, copiá-lo ou redistribuí-lo.
Todo o conteúdo usa apenas blocos e itens do Minecraft; nenhum recurso de terceiros está incluído.
