# Vérification des ajouts du 6 novembre 2026

94 nouvelles entrées ajoutées après les 164 entrées existantes : total 258.
Les anciennes entrées et leurs identifiants sont inchangés. Aucune modification
de la base de progression n'est nécessaire.

## Documents retenus

- `Devoirs_maison_3_Russe_Etre_Avoir.pdf` : exemples complets et corrigés non
  ambigus des exercices sur être, avoir et les possessifs. Les productions libres
  ne sont pas importées comme réponses uniques.
- `Russian_Verbs_Быть_и_Иметь_corrige.pdf` : six pages examinées visuellement et
  comparées au cours original `Russian Verbs - Быть и Иметь.pdf`. La version
  corrigée est la référence retenue ; aucun double import du cours original.
- `Притяжательные местоимения и род.pdf` : tableau au nominatif, formes
  manquantes et groupes nominaux. Les genres des noms russes sont respectés,
  même quand ils diffèrent du français.
- `fiche_pedagogique_lecon_2 1.pdf` : complément au vocabulaire déjà importé de
  la leçon 2 ; ajout de phrases et groupes de mots sans répéter les entrées
  existantes. L'opposition question/affirmation est expliquée dans le rappel,
  sans créer deux réponses ne différant que par la ponctuation ignorée par
  le correcteur.

## Corrections et précisions appliquées dans l'application

- Dans le cours original être/avoir, page 3, `Ты готовит?` est incorrect pour
  « Tu es prêt ? ». La version corrigée donne bien `Ты готов?` : c'est cette
  forme qui est retenue, avec indication du destinataire masculin. Le rappel
  mentionne aussi `Ты готова?` pour une femme.
- L'absence du verbe être est présentée comme le cas général dans les phrases
  simples au présent, et non une interdiction universelle de l'employer.
- `У меня есть…` est une construction de possession, non la conjugaison
  d'`иметь`. Les formes après `у` sont au génitif ; l'emploi d'`есть` dépend du
  contexte. On n'en déduit pas une traduction automatique de tout « avoir ».
- Les tableaux des possessifs sont explicitement limités au nominatif.
  `его`, `её`, `их` restent invariables en emploi possessif ; les traductions
  des groupes précisent le possesseur pour éviter l'ambiguïté de son/sa/ses.
- Le mémo du PDF sur le genre est trop général : les terminaisons sont des
  indices avec exceptions. `папа` est masculin ; le pluriel n'est pas limité
  à `-и`, comme le montre `дома` (« maisons »).
- Les accents toniques des entrées ont été ajoutés pour la lecture.
  `два до́ма` (« deux maisons ») se distingue de `до́ма` (« à la maison »)
  par son contexte, malgré une forme identique.
- L'intonation est décrite sur la syllabe accentuée du mot mis en relief.
  La voix synthétique n'est pas présentée comme une reproduction garantie
  des courbes pédagogiques.

## Exclusions

Le dossier personnel `Упражниние` n'est pas une source. Son document
`Texte_russe.docx`, ainsi que `Texte_russe.pdf` présent à la racine et contenant
le même dialogue personnel, ne sont pas intégrés. Le manuel Tome 1 et les
images non transcrites restent exclus du catalogue.

Les corrections portent sur le contenu intégré dans l'application ; les PDF
originaux du dossier Documents ne sont pas réécrits.

## Accès dans l'application

- Carnet « Mes mots » : section dépliable « Repères de cours ».
- Nouveaux thèmes : « Être au présent », « Avoir au présent »,
  « Phrases et intonation » ; enrichissement du thème « Les possessifs ».
- Toutes les nouvelles entrées utilisent les exercices, la lecture normale
  et lente, les favoris et les révisions existants.

Après régénération du catalogue, redémarrer le serveur Flask pour charger
les nouvelles entrées (arrêter puis relancer `demarrer.bat`).
