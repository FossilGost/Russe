"""Curated transcription of the supplied studied worksheets, never the textbook.

Run python data/build_vocabulary.py after editing this file to rebuild vocabulary.json.
Runtime needs only vocabulary.json, not the original documents or pypdf.
"""
import json
from pathlib import Path

SOURCES = {
    "prepositions": "Complément pédagogique : prépositions russes courantes et exemples contextualisés (ajout à la demande)",
    "consonnes": "fiche_pedagogique_consonnes.pdf",
    "accent": "fiche_pedagogique_accent_tonique.pdf",
    "lecon2": "fiche_pedagogique_lecon_2.pdf",
    "devoirs": "Домашнее задание_ Домашнее задание - Русский язык (A1).pdf",
    "musique": "2 Домашнее задание.pdf",
    "soir": "Мой вечер , текст и словарь 30 окт.pdf",
    "sons": "russe_consonnes_voyelles.pdf",
    "devoirs3": "Devoirs_maison_3_Russe_Etre_Avoir.pdf (contenu vérifié)",
    "etre_avoir": "Russian_Verbs_Быть_и_Иметь_corrige.pdf (vérifié avec le cours original)",
    "possessifs_genre": "Притяжательные местоимения и род.pdf (règles précisées)",
    "lecon2_revision": "fiche_pedagogique_lecon_2 1.pdf (version complémentaire)",
}
# Russian | French | category | source. Stress marks are for learning, not required input.
ROWS = """
дом|la maison|Au quotidien|consonnes
мост|le pont|Au quotidien|consonnes
сад|le jardin|Au quotidien|consonnes
суп|la soupe|À table|consonnes
сон|le sommeil, le rêve|Au quotidien|consonnes
зонт|le parapluie|Au quotidien|consonnes
банк|la banque|Au quotidien|consonnes
сок|le jus|À table|consonnes
кот|le chat|Au quotidien|consonnes
звук|le son|Premiers mots|consonnes
год|l’année|Au quotidien|consonnes
газ|le gaz|Au quotidien|consonnes
вода́|l’eau|À table|accent
окно́|la fenêtre|Au quotidien|accent
ма́ма|la maman|Les personnes|accent
па́па|le papa|Les personnes|accent
фонта́н|la fontaine|Au quotidien|accent
стака́н|le verre|À table|accent
мо́да|la mode|Au quotidien|accent
на́до|il faut|Petits mots|accent
мно́го|beaucoup|Petits mots|accent
ва́за|le vase|Au quotidien|accent
су́мка|le sac|Au quotidien|accent
она́|elle|Les pronoms|accent
оно́|il / ça (neutre)|Les pronoms|accent
туда́|là-bas (direction)|Petits mots|accent
давно́|depuis longtemps|Petits mots|accent
куда́|où (direction)|Questions|accent
когда́|quand|Questions|accent
тогда́|alors, dans ce cas|Petits mots|soir
ваго́н|le wagon|Au quotidien|accent
бана́н|la banane|À table|accent
пото́м|ensuite|Petits mots|accent
заво́д|l’usine|Au quotidien|accent
восто́к|l’est|Au quotidien|accent
доска́|le tableau|Au quotidien|accent
бу́ква|la lettre|Premiers mots|accent
за́пад|l’ouest|Au quotidien|accent
а́том|l’atome|Premiers mots|accent
ко́смос|l’espace|Premiers mots|accent
ва́нна|la baignoire|Au quotidien|accent
то́нна|la tonne|Premiers mots|accent
ка́сса|la caisse|Au quotidien|accent
ма́сса|la masse|Premiers mots|accent
су́мма|la somme|Premiers mots|accent
ко́фта|le gilet|Au quotidien|accent
па́пка|le dossier|Au quotidien|accent
фо́то|la photo|Au quotidien|lecon2
Москва́|Moscou|Les personnes|lecon2
поэ́т|le poète|Les personnes|lecon2
рабо́та|le travail|Au quotidien|lecon2
э́то|c’est / ceci|Petits mots|lecon2
тут|ici|Petits mots|consonnes
там|là-bas|Petits mots|soir
вот|voici / voilà|Petits mots|consonnes
рука́|la main|Au quotidien|lecon2
ро́за|la rose|Au quotidien|lecon2
брат|le frère|Les personnes|lecon2
тра́сса|la route principale|Au quotidien|lecon2
дра́ма|le drame|Loisirs|lecon2
март|mars|Au quotidien|lecon2
тра́ктор|le tracteur|Au quotidien|lecon2
друг|un ami|Les personnes|soir
спорт|le sport|Loisirs|lecon2
тра́нспорт|le transport|Au quotidien|lecon2
тру́дно|difficile|Petits mots|lecon2
ка́рта|la carte|Au quotidien|lecon2
трава́|l’herbe|Au quotidien|lecon2
страна́|le pays|Les personnes|lecon2
гора́|la montagne|Au quotidien|lecon2
за́втра|demain|Petits mots|lecon2
у́тром|le matin|Petits mots|lecon2
вопро́с|la question|Questions|lecon2
карма́н|la poche|Au quotidien|lecon2
уро́к|la leçon|Premiers mots|lecon2
па́спорт|le passeport|Au quotidien|lecon2
фра́за|la phrase|Premiers mots|lecon2
расска́з|le récit|Premiers mots|lecon2
сторона́|le côté|Au quotidien|lecon2
ко́мната|la pièce|Au quotidien|lecon2
разгово́р|la conversation|Premiers mots|lecon2
гастроно́м|le magasin d’alimentation|Au quotidien|lecon2
пого́да|le temps (météo)|Météo et soirée|lecon2
доро́га|la route|Au quotidien|lecon2
до́рого|cher (prix)|Petits mots|lecon2
ко́ротко|brièvement|Petits mots|lecon2
я|je|Les pronoms|devoirs
ты|tu|Les pronoms|devoirs
он|il|Les pronoms|devoirs
мы|nous|Les pronoms|devoirs
вы|vous|Les pronoms|devoirs
они́|ils / elles|Les pronoms|devoirs
мой|mon (masculin)|Les possessifs|devoirs
моя́|ma (féminin)|Les possessifs|devoirs
моё|mon / ma (neutre)|Les possessifs|devoirs
твой|ton (masculin)|Les possessifs|devoirs
твоя́|ta (féminin)|Les possessifs|musique
твоё|ton / ta (neutre)|Les possessifs|musique
его́|son / sa (à lui)|Les possessifs|devoirs
её|son / sa (à elle)|Les possessifs|devoirs
наш|notre (masculin)|Les possessifs|devoirs
на́ша|notre (féminin)|Les possessifs|devoirs
на́ше|notre (neutre)|Les possessifs|musique
ваш|votre (masculin)|Les possessifs|devoirs
ва́ша|votre (féminin)|Les possessifs|devoirs
их|leur|Les possessifs|devoirs
маши́на|la voiture|Au quotidien|devoirs
где|où (lieu)|Questions|devoirs
плейли́ст|la playlist|Loisirs|musique
биле́т|le billet|Loisirs|musique
конце́рт|le concert|Loisirs|musique
пе́сня|la chanson|Loisirs|musique
друзья́|les amis|Les personnes|musique
кофе́йня|un salon de café (spécialisé dans le café)|Loisirs|musique
ко́фе|le café à boire (boisson)|À table|soir
но́вый|nouveau|Petits mots|musique
уже́|déjà|Petits mots|musique
дождь|la pluie|Météo et soirée|soir
ве́тер|le vent|Météo et soirée|soir
у́лица|la rue|Météo et soirée|soir
пя́тница|vendredi|Météo et soirée|soir
ве́чер|le soir, la soirée|Météo et soirée|soir
чай|le thé|À table|soir
му́зыка|la musique|Loisirs|soir
телефо́н|le téléphone|Au quotidien|soir
Фра́нция|la France|Les personnes|soir
язы́к|la langue|Premiers mots|soir
кино́|le cinéma|Loisirs|soir
футбо́л|le football|Loisirs|soir
кафе́|un café / petit restaurant (lieu)|Loisirs|soir
жить|habiter, vivre|Les verbes|soir
рабо́тать|travailler|Les verbes|soir
учи́ть|apprendre, étudier|Les verbes|soir
слу́шать|écouter|Les verbes|soir
смотре́ть|regarder|Les verbes|soir
люби́ть|aimer|Les verbes|soir
хоте́ть|vouloir|Les verbes|soir
гуля́ть|se promener|Les verbes|soir
звони́ть|téléphoner, appeler|Les verbes|soir
де́лать|faire|Les verbes|soir
пить|boire|Les verbes|soir
идти́|aller (à pied)|Les verbes|soir
сего́дня|aujourd’hui|Petits mots|soir
до́ма|à la maison|Petits mots|soir
то́же|aussi|Petits mots|soir
почему́|pourquoi|Questions|soir
отли́чно|excellent, super|Petits mots|soir
хорошо́|bien|Petits mots|soir
свобо́ден|libre, disponible (masculin)|Petits mots|soir
Приве́т!|Salut !|Expressions|soir
Как дела́?|Comment ça va ?|Expressions|soir
Всё хорошо́.|Tout va bien.|Expressions|soir
Что ты де́лаешь?|Qu’est-ce que tu fais ?|Expressions|soir
До встре́чи!|À bientôt !|Expressions|soir
Я хочу́ гуля́ть.|Je veux me promener.|Expressions|soir
Я люблю́ ко́фе.|J’aime le café.|Expressions|soir
У меня́ есть зонт.|J’ai un parapluie.|Expressions|soir
На у́лице дождь.|Il pleut dehors.|Expressions|soir
мать|la mère|Les personnes|sons
кит|la baleine|Au quotidien|sons
о́чень|très|Petits mots|sons
сестра́|la sœur|Les personnes|sons
мужчи́на|l’homme|Les personnes|sons
да|oui|Petits mots|lecon2
быть|être|Les verbes|etre_avoir
име́ть|avoir (verbe ; possession courante : у … есть)|Les verbes|etre_avoir
стул|la chaise|Au quotidien|possessifs_genre
кни́ги|les livres|Au quotidien|possessifs_genre
мои́|mes (pluriel)|Les possessifs|possessifs_genre
твои́|tes (pluriel)|Les possessifs|possessifs_genre
на́ши|nos (pluriel)|Les possessifs|possessifs_genre
ва́ше|votre (neutre)|Les possessifs|possessifs_genre
ва́ши|vos (pluriel)|Les possessifs|possessifs_genre
мой стул|ma chaise|Les possessifs|possessifs_genre
моя́ су́мка|mon sac|Les possessifs|possessifs_genre
моё окно́|ma fenêtre|Les possessifs|possessifs_genre
мои́ кни́ги|mes livres|Les possessifs|possessifs_genre
твой стул|ta chaise|Les possessifs|possessifs_genre
твоя́ су́мка|ton sac|Les possessifs|possessifs_genre
твоё окно́|ta fenêtre|Les possessifs|possessifs_genre
твои́ кни́ги|tes livres|Les possessifs|possessifs_genre
наш стул|notre chaise|Les possessifs|possessifs_genre
на́ша су́мка|notre sac|Les possessifs|possessifs_genre
на́ше окно́|notre fenêtre|Les possessifs|possessifs_genre
на́ши кни́ги|nos livres|Les possessifs|possessifs_genre
ваш стул|votre chaise|Les possessifs|possessifs_genre
ва́ша су́мка|votre sac|Les possessifs|possessifs_genre
ва́ше окно́|votre fenêtre|Les possessifs|possessifs_genre
ва́ши кни́ги|vos livres|Les possessifs|possessifs_genre
его́ стул|sa chaise (à lui)|Les possessifs|possessifs_genre
его́ су́мка|son sac (à lui)|Les possessifs|possessifs_genre
его́ окно́|sa fenêtre (à lui)|Les possessifs|possessifs_genre
его́ кни́ги|ses livres (à lui)|Les possessifs|possessifs_genre
её стул|sa chaise (à elle)|Les possessifs|possessifs_genre
её су́мка|son sac (à elle)|Les possessifs|possessifs_genre
её окно́|sa fenêtre (à elle)|Les possessifs|possessifs_genre
её кни́ги|ses livres (à elle)|Les possessifs|possessifs_genre
их стул|leur chaise|Les possessifs|possessifs_genre
их су́мка|leur sac|Les possessifs|possessifs_genre
их окно́|leur fenêtre|Les possessifs|possessifs_genre
их кни́ги|leurs livres|Les possessifs|possessifs_genre
Э́то мой дом.|C’est ma maison.|Être au présent|devoirs3
Э́то фо́то.|C’est une photo.|Être au présent|devoirs3
Он до́ма.|Il est à la maison.|Être au présent|devoirs3
Она́ в Москве́.|Elle est à Moscou.|Être au présent|devoirs3
Она́ до́ма.|Elle est à la maison.|Être au présent|devoirs3
Э́то но́вая ко́фта.|C’est un nouveau gilet.|Être au présent|devoirs3
Э́то Москва́.|C’est Moscou.|Être au présent|devoirs3
Ма́ма до́ма.|Maman est à la maison.|Être au présent|devoirs3
Тут окно́.|Ici, il y a une fenêtre.|Être au présent|devoirs3
Банк там.|La banque est là-bas.|Être au présent|devoirs3
Э́то моя́ ко́мната.|C’est ma chambre.|Être au présent|devoirs3
Там фонта́н.|Là-bas, il y a une fontaine.|Être au présent|devoirs3
Моя́ ма́ма до́ма.|Ma maman est à la maison.|Être au présent|devoirs3
Там сад.|Là-bas, il y a un jardin.|Être au présent|devoirs3
Я — преподава́тель.|Je suis professeur.|Être au présent|etre_avoir
Мы до́ма.|Nous sommes à la maison.|Être au présent|etre_avoir
Я до́ма.|Je suis à la maison.|Être au présent|etre_avoir
Ты гото́в?|Tu es prêt ? (à un homme)|Être au présent|etre_avoir
Он экспе́рт.|Il est expert.|Être au présent|etre_avoir
Мы в о́фисе.|Nous sommes au bureau.|Être au présent|etre_avoir
Вы здесь?|Vous êtes ici ?|Être au présent|etre_avoir
Они́ друзья́.|Ils sont amis.|Être au présent|etre_avoir
Я — студе́нт.|Je suis étudiant. (homme)|Être au présent|etre_avoir
У меня́ есть брат.|J’ai un frère.|Avoir au présent|devoirs3
У тебя́ есть зонт.|Tu as un parapluie.|Avoir au présent|devoirs3
У него́ есть па́спорт.|Il a un passeport.|Avoir au présent|devoirs3
У неё есть фо́то.|Elle a une photo.|Avoir au présent|devoirs3
У нас есть зонт.|Nous avons un parapluie.|Avoir au présent|devoirs3
У нас есть два до́ма.|Nous avons deux maisons.|Avoir au présent|devoirs3
У меня́ есть фо́то.|J’ai une photo.|Avoir au présent|devoirs3
У меня́ есть прое́кт.|J’ai un projet.|Avoir au présent|etre_avoir
У тебя́ есть вре́мя?|Tu as du temps ?|Avoir au présent|etre_avoir
У него́ есть маши́на.|Il a une voiture.|Avoir au présent|etre_avoir
У неё есть иде́я.|Elle a une idée.|Avoir au présent|etre_avoir
У нас есть реше́ние.|Nous avons une solution.|Avoir au présent|etre_avoir
У вас есть вопро́с?|Vous avez une question ?|Avoir au présent|etre_avoir
У них есть о́пыт.|Ils ont de l’expérience.|Avoir au présent|etre_avoir
У меня́ есть кни́га.|J’ai un livre.|Avoir au présent|etre_avoir
Э́то вода́.|C’est de l’eau.|Phrases et intonation|lecon2_revision
Э́то ва́за.|C’est un vase.|Phrases et intonation|lecon2_revision
Она́ там.|Elle est là-bas.|Phrases et intonation|lecon2_revision
Она́ одна́.|Elle est seule.|Phrases et intonation|lecon2_revision
Э́то су́мка.|C’est un sac.|Phrases et intonation|lecon2_revision
Э́то зонт.|C’est un parapluie.|Phrases et intonation|lecon2_revision
Вот фо́то.|Voici une photo.|Phrases et intonation|lecon2_revision
Э́та поэ́ма|ce poème|Phrases et intonation|lecon2_revision
Э́тот поэ́т|ce poète|Phrases et intonation|lecon2_revision
два дру́га|deux amis|Phrases et intonation|lecon2_revision
два бра́та|deux frères|Phrases et intonation|lecon2_revision
два уро́ка|deux leçons|Phrases et intonation|lecon2_revision
два ра́за|deux fois|Phrases et intonation|lecon2_revision
два до́ма|deux maisons|Phrases et intonation|lecon2_revision
два го́да|deux ans|Phrases et intonation|lecon2_revision
поэ́ма|le poème|Premiers mots|lecon2_revision
поэ́тому|c’est pourquoi|Petits mots|lecon2_revision
эта́п|l’étape|Premiers mots|lecon2_revision
экза́мен|l’examen|Premiers mots|lecon2_revision
в|dans / à (intérieur)|Les prépositions|prepositions
на|sur / à (surface, activité)|Les prépositions|prepositions
у|près de / chez|Les prépositions|prepositions
к|vers / chez (destination)|Les prépositions|prepositions
из|de (provenance de l’intérieur)|Les prépositions|prepositions
от|de / depuis (point de départ)|Les prépositions|prepositions
до|jusqu’à|Les prépositions|prepositions
без|sans|Les prépositions|prepositions
для|pour (destinataire)|Les prépositions|prepositions
с|avec / de (selon le cas)|Les prépositions|prepositions
под|sous|Les prépositions|prepositions
над|au-dessus de|Les prépositions|prepositions
пе́ред|devant / avant|Les prépositions|prepositions
за|derrière / pour (selon le contexte)|Les prépositions|prepositions
о|au sujet de / à propos de|Les prépositions|prepositions
по|le long de / selon (selon le contexte)|Les prépositions|prepositions
в до́ме|dans la maison (position)|Les prépositions|prepositions
в дом|dans la maison (destination)|Les prépositions|prepositions
на столе́|sur la table (position)|Les prépositions|prepositions
на стол|sur la table (destination)|Les prépositions|prepositions
у до́ма|près de la maison|Les prépositions|prepositions
у меня́|chez moi|Les prépositions|prepositions
к до́му|vers la maison|Les prépositions|prepositions
из до́ма|de la maison (depuis l’intérieur)|Les prépositions|prepositions
от до́ма|depuis la maison (point de départ)|Les prépositions|prepositions
до до́ма|jusqu’à la maison|Les prépositions|prepositions
без са́хара|sans sucre|Les prépositions|prepositions
для дру́га|pour un ami|Les prépositions|prepositions
с дру́гом|avec un ami|Les prépositions|prepositions
со стола́|de la table (provenance)|Les prépositions|prepositions
под столо́м|sous la table (position)|Les prépositions|prepositions
под стол|sous la table (destination)|Les prépositions|prepositions
над столо́м|au-dessus de la table|Les prépositions|prepositions
пе́ред до́мом|devant la maison|Les prépositions|prepositions
за до́мом|derrière la maison (position)|Les prépositions|prepositions
за дом|derrière la maison (destination)|Les prépositions|prepositions
о дру́ге|au sujet d’un ami|Les prépositions|prepositions
по у́лице|le long de la rue|Les prépositions|prepositions
"""

if __name__ == "__main__":
    words = []
    for line in ROWS.strip().splitlines():
        parts = line.split("|")
        ru, fr, category, source = parts
        words.append(dict(id=len(words)+1, ru=ru, fr=fr, category=category, source=source))
    Path(__file__).with_name("vocabulary.json").write_text(
        json.dumps(dict(sources=SOURCES, words=words), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(words)} entrées enregistrées.")
