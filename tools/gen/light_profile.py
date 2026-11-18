"""Texts of the light profile ("ligero", options.LIGHT_OPTIONS): the first-start suggestion for operators, the seam warning
when world generation changes in a world already started, the note of /heraldia profile and the client screen's warning
(Java: config/ProfileAdvice, command/ProfileNotice, command/ProfileCommand and client/ConfigScreen). The panel's own texts
(heraldia.panel.*) are in updates.py.

Each text goes in all 8 languages in the order of updates.LANGUAGES: es_es and en_us come from lang(); the others are copied
to languages/<code>.json with `python3 tools/gen/light_profile.py` (checked by tests/test_light_profile.py). OPTION has
the 6 translations of the option texts whose es_es and en_us are in options.py.
"""
import json
import os

from updates import LANGUAGES, NS

_T = {
    "ligero.sugerencia": (
        "Heraldia: este servidor tiene %s GB de memoria para Java y %s núcleos. Para equipos así se recomienda el perfil "
        "ligero: la misma partida con una generación del mundo más ligera.",
        "Heraldia: this server has %s GB of memory for Java and %s cores. For machines like this the light profile is "
        "recommended: the same game with lighter world generation.",
        "Heraldia : ce serveur a %s Go de mémoire pour Java et %s cœurs. Pour une machine comme celle-ci, le profil léger "
        "est conseillé : la même partie avec une génération du monde plus légère.",
        "Heraldia: Dieser Server hat %s GB Speicher für Java und %s Kerne. Für solche Rechner wird das leichte Profil "
        "empfohlen: dasselbe Spiel mit einer leichteren Weltgenerierung.",
        "Heraldia: questo server ha %s GB di memoria per Java e %s core. Per macchine così si consiglia il profilo "
        "leggero: la stessa partita con una generazione del mondo più leggera.",
        "Heraldia: este servidor tem %s GB de memória para o Java e %s núcleos. Para máquinas assim recomenda-se o perfil "
        "leve: o mesmo jogo com uma geração do mundo mais leve.",
        "Heraldia: aquest servidor té %s GB de memòria per a Java i %s nuclis. Per a equips així es recomana el perfil "
        "lleuger: la mateixa partida amb una generació del món més lleugera.",
        "Heraldia: este servidor ten %s GB de memoria para Java e %s núcleos. Para equipos así recoméndase o perfil "
        "lixeiro: a mesma partida cunha xeración do mundo máis lixeira."),
    "ligero.sugerencia.boton": (
        "[Aplicar el perfil ligero]", "[Apply the light profile]", "[Appliquer le profil léger]", "[Leichtes Profil anwenden]",
        "[Applica il profilo leggero]", "[Aplicar o perfil leve]", "[Aplica el perfil lleuger]", "[Aplicar o perfil lixeiro]"),
    "ligero.sugerencia.ayuda": (
        "Lo guarda en config/heraldia.json; la generación cambia al reiniciar, solo en los chunks nuevos",
        "Saves it in config/heraldia.json; generation changes after a restart, in new chunks only",
        "L'enregistre dans config/heraldia.json ; la génération change au redémarrage, seulement dans les nouveaux chunks",
        "Speichert es in config/heraldia.json; die Generierung ändert sich nach einem Neustart, nur in neuen Chunks",
        "Lo salva in config/heraldia.json; la generazione cambia al riavvio, solo nei chunk nuovi",
        "Salva em config/heraldia.json; a geração muda ao reiniciar, só nos chunks novos",
        "Ho desa a config/heraldia.json; la generació canvia en reiniciar, només als chunks nous",
        "Gárdao en config/heraldia.json; a xeración cambia ao reiniciar, só nos chunks novos"),
    "ligero.sugerencia.ignorar": (
        "Es solo una sugerencia: si prefieres el perfil actual, no hagas nada (no se vuelve a sugerir).",
        "It is only a suggestion: if you prefer the current profile, do nothing (it is not suggested again).",
        "Ce n'est qu'une suggestion : si vous préférez le profil actuel, ne faites rien (elle ne sera plus proposée).",
        "Das ist nur ein Vorschlag: Wenn dir das aktuelle Profil lieber ist, tu nichts (es wird nicht erneut vorgeschlagen).",
        "È solo un suggerimento: se preferisci il profilo attuale, non fare nulla (non verrà più proposto).",
        "É só uma sugestão: se preferir o perfil atual, não faça nada (não será sugerido de novo).",
        "És només un suggeriment: si prefereixes el perfil actual, no facis res (no es tornarà a suggerir).",
        "É só unha suxestión: se prefires o perfil actual, non fagas nada (non se volve suxerir)."),
    "ligero.costuras": (
        "Heraldia: la generación del mundo ha cambiado desde el último arranque (%s). Lo ya generado no cambia: solo los chunks "
        "nuevos siguen la configuración nueva, y junto al terreno ya explorado puede haber costuras (una zona densa junto a otra "
        "vacía, caminos que acaban en el borde). Detalles en el registro del servidor.",
        "Heraldia: world generation has changed since the last start (%s). What is already generated does not change: only "
        "new chunks follow the new configuration, and next to the land already explored there may be seams (a dense zone "
        "next to an empty one, roads ending at the edge). Details in the server log.",
        "Heraldia : la génération du monde a changé depuis le dernier démarrage (%s). Ce qui est déjà généré ne change pas : "
        "seuls les nouveaux chunks suivent la nouvelle configuration, et à côté des terres déjà explorées il peut y avoir des "
        "coutures (une zone dense à côté d'une zone vide, des chemins qui s'arrêtent au bord). Détails dans le journal du serveur.",
        "Heraldia: Die Weltgenerierung hat sich seit dem letzten Start geändert (%s). Bereits Generiertes ändert sich nicht: "
        "Nur neue Chunks folgen der neuen Konfiguration, und neben dem schon erkundeten Land kann es Nähte geben (eine dichte "
        "Zone neben einer leeren, Wege, die am Rand enden). Einzelheiten im Serverprotokoll.",
        "Heraldia: la generazione del mondo è cambiata dall'ultimo avvio (%s). Ciò che è già generato non cambia: solo i "
        "chunk nuovi seguono la nuova configurazione, e accanto alle terre già esplorate possono esserci cuciture (una zona "
        "densa accanto a una vuota, sentieri che finiscono sul bordo). Dettagli nel registro del server.",
        "Heraldia: a geração do mundo mudou desde a última inicialização (%s). O que já foi gerado não muda: só os chunks "
        "novos seguem a nova configuração, e junto ao terreno já explorado pode haver costuras (uma zona densa ao lado de "
        "outra vazia, caminhos que acabam na borda). Detalhes no log do servidor.",
        "Heraldia: la generació del món ha canviat des de l'última arrencada (%s). El que ja s'ha generat no canvia: només "
        "els chunks nous segueixen la configuració nova, i al costat del terreny ja explorat hi pot haver costures (una zona "
        "densa al costat d'una de buida, camins que acaben a la vora). Detalls al registre del servidor.",
        "Heraldia: a xeración do mundo cambiou desde o último arranque (%s). O xa xerado non cambia: só os chunks novos "
        "seguen a configuración nova, e xunto ao terreo xa explorado pode haber costuras (unha zona densa xunto a outra "
        "baleira, camiños que rematan no bordo). Detalles no rexistro do servidor."),
    "ligero.perfil_generacion": (
        "El perfil %s también cambia la generación del mundo: solo en los chunks que se generen después de reiniciar; en un "
        "mundo ya empezado deja costuras junto a lo ya generado.",
        "The %s profile also changes world generation: only in the chunks generated after a restart; in a world already "
        "started it leaves seams next to what is already generated.",
        "Le profil %s change aussi la génération du monde : seulement dans les chunks générés après un redémarrage ; dans "
        "un monde déjà commencé, il laisse des coutures à côté de ce qui est déjà généré.",
        "Das Profil %s ändert auch die Weltgenerierung: nur in den Chunks, die nach einem Neustart generiert werden; in "
        "einer schon begonnenen Welt hinterlässt es Nähte neben dem bereits Generierten.",
        "Il profilo %s cambia anche la generazione del mondo: solo nei chunk generati dopo un riavvio; in un mondo già "
        "iniziato lascia cuciture accanto a ciò che è già generato.",
        "O perfil %s também muda a geração do mundo: só nos chunks gerados depois de reiniciar; num mundo já começado "
        "deixa costuras junto ao que já foi gerado.",
        "El perfil %s també canvia la generació del món: només als chunks que es generin després de reiniciar; en un món "
        "ja començat deixa costures al costat del que ja s'ha generat.",
        "O perfil %s tamén cambia a xeración do mundo: só nos chunks que se xeren despois de reiniciar; nun mundo xa "
        "comezado deixa costuras xunto ao xa xerado."),
    "ligero.pantalla": (
        "Este perfil cambia la generación del mundo: en un mundo ya empezado, solo los chunks nuevos, y junto a lo ya "
        "generado quedan costuras (una zona densa junto a otra vacía). Mejor elegirlo antes de crear el mundo.",
        "This profile changes world generation: in a world already started, only new chunks, and next to what is already "
        "generated there are seams (a dense zone next to an empty one). Best chosen before creating the world.",
        "Ce profil change la génération du monde : dans un monde déjà commencé, seulement les nouveaux chunks, et à côté de "
        "ce qui est déjà généré il reste des coutures (une zone dense à côté d'une zone vide). Mieux vaut le choisir avant "
        "de créer le monde.",
        "Dieses Profil ändert die Weltgenerierung: in einer schon begonnenen Welt nur neue Chunks, und neben dem bereits "
        "Generierten bleiben Nähte (eine dichte Zone neben einer leeren). Am besten vor dem Erstellen der Welt wählen.",
        "Questo profilo cambia la generazione del mondo: in un mondo già iniziato, solo i chunk nuovi, e accanto a ciò che "
        "è già generato restano cuciture (una zona densa accanto a una vuota). Meglio sceglierlo prima di creare il mondo.",
        "Este perfil muda a geração do mundo: num mundo já começado, só os chunks novos, e junto ao que já foi gerado ficam "
        "costuras (uma zona densa ao lado de outra vazia). Melhor escolhê-lo antes de criar o mundo.",
        "Aquest perfil canvia la generació del món: en un món ja començat, només els chunks nous, i al costat del que ja "
        "s'ha generat queden costures (una zona densa al costat d'una de buida). Millor triar-lo abans de crear el món.",
        "Este perfil cambia a xeración do mundo: nun mundo xa comezado, só os chunks novos, e xunto ao xa xerado quedan "
        "costuras (unha zona densa xunto a outra baleira). Mellor escollelo antes de crear o mundo."),
}

# Option texts (es_es and en_us in options.py): the 6 translations, in the order of updates.LANGUAGES[2:].
OPTION = {
    "config.perfil": (
        "Profil de jeu : fixe d'un coup la difficulté, les renforts des gardiens, le butin qui se renouvelle, l'arène et les "
        "attaques des caravanes (casual, plus facile et avec le butin qui se renouvelle ; standard, comme toujours ; hardcore, "
        "héroïque, avec plus de renforts et moins d'expérience ; léger, le jeu standard avec une génération du monde plus légère "
        "pour les machines modestes ; personnalisé, chaque option avec sa valeur). Une de ces options écrite dans le fichier "
        "l'emporte sur le profil. Seul léger change la génération du monde, et dans un monde déjà commencé seulement dans les "
        "nouveaux chunks",
        "Spielprofil: legt auf einmal die Schwierigkeit, die Verstärkung der Hüter, die sich auffüllende Beute, die Arena und "
        "die Überfälle auf Karawanen fest (casual: leichter und mit sich auffüllender Beute; standard: wie immer; hardcore: "
        "heroisch, mit mehr Verstärkung und weniger Erfahrung; leicht: das Standardspiel mit einer leichteren Weltgenerierung "
        "für bescheidene Rechner; benutzerdefiniert: jede Option mit ihrem eigenen Wert). Eine dieser Optionen, die in der "
        "Datei steht, hat Vorrang vor dem Profil. Nur leicht ändert die Weltgenerierung, und in einer schon begonnenen Welt "
        "nur in neuen Chunks",
        "Profilo di gioco: fissa in un colpo la difficoltà, i rinforzi dei guardiani, il bottino che si rifornisce, l'arena e "
        "gli assalti alle carovane (casual, più facile e con il bottino che si rifornisce; standard, come sempre; hardcore, "
        "eroica, con più rinforzi e meno esperienza; leggero, il gioco standard con una generazione del mondo più leggera per "
        "macchine modeste; personalizzato, ogni opzione con il suo valore). Una di queste opzioni scritta nel file prevale sul "
        "profilo. Solo leggero cambia la generazione del mondo, e in un mondo già iniziato solo nei chunk nuovi",
        "Perfil de jogo: define de uma vez a dificuldade, os reforços dos guardiões, o saque que se repõe, a arena e os "
        "assaltos às caravanas (casual, mais fácil e com o saque que se repõe; padrão, como sempre; hardcore, heroica, com mais "
        "reforços e menos experiência; leve, o jogo padrão com uma geração do mundo mais leve para máquinas modestas; "
        "personalizado, cada opção com seu valor). Uma dessas opções escrita no arquivo prevalece sobre o perfil. Só o leve "
        "muda a geração do mundo, e num mundo já começado só nos chunks novos",
        "Perfil de joc: fixa d'un cop la dificultat, els reforços dels guardians, el botí que es reposa, l'arena i els assalts "
        "a les caravanes (casual, més fàcil i amb el botí que es reposa; estàndard, com sempre; hardcore, heroica, amb més "
        "reforços i menys experiència; lleuger, el joc estàndard amb una generació del món més lleugera per a equips modestos; "
        "personalitzat, cada opció amb el seu valor). Una d'aquestes opcions escrita al fitxer mana sobre el perfil. Només "
        "lleuger canvia la generació del món, i en un món ja començat només als chunks nous",
        "Perfil de xogo: fixa dunha vez a dificultade, os reforzos dos gardiáns, o botín que se repón, a area e os asaltos ás "
        "caravanas (casual, máis doado e co botín que se repón; estándar, o de sempre; hardcore, heroica, con máis reforzos e "
        "menos experiencia; lixeiro, o xogo estándar cunha xeración do mundo máis lixeira para equipos modestos; "
        "personalizado, cada opción co seu valor). Unha destas opcións escrita no ficheiro manda sobre o perfil. Só lixeiro "
        "cambia a xeración do mundo, e nun mundo xa comezado só nos chunks novos"),
    "config.perfil.ligero": ("Léger", "Leicht", "Leggero", "Leve", "Lleuger", "Lixeiro"),
    "config.perfil_ligero": ("léger %s", "leicht %s", "leggero %s", "leve %s", "lleuger %s", "lixeiro: %s"),
}


def _all():
    """{full key: (text per language, in the order of LANGUAGES)}."""
    out = {f"{NS}.{k}": v for k, v in _T.items()}
    for k, v in out.items():
        assert len(v) == len(LANGUAGES), k
    return out


def lang():
    """{"es_es": {...}, "en_us": {...}} with the light profile's texts (those of the option are in options.py)."""
    out = {"es_es": {}, "en_us": {}}
    for k, v in _all().items():
        out["es_es"][k], out["en_us"][k] = v[0], v[1]
    return out


def translation(lang_code):
    """The texts of one language in languages/ (fr_fr, de_de...), including those of the option."""
    i = LANGUAGES.index(lang_code)
    out = {k: v[i] for k, v in _all().items()}
    for k, v in OPTION.items():
        assert len(v) == len(LANGUAGES) - 2, k
        out[f"{NS}.{k}"] = v[i - 2]
    return out


def write():
    """Copies each translation's texts to languages/<code>.json (keeps the rest, ordered as it was)."""
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages")
    for c in LANGUAGES[2:]:
        p = os.path.join(folder, f"{c}.json")
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        d.update(translation(c))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    write()
