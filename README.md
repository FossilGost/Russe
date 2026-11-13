# Slovo — apprendre le russe

Application en **Python, Flask, Jinja, HTML, CSS et JavaScript**, interface en français. Utilisable en local ou sur un serveur Internet, avec connexion par compte et progression personnelle.

Les optimisations et mesures locales sont décrites dans [PERFORMANCE.md](PERFORMANCE.md) : carnet paginé, ressources publiques mises en cache, cache audio limité et transitions d’exercice allégées. Le lanceur évite pip lorsque les dépendances sont déjà à jour et utilise Waitress sur le port 5000.

La préparation au déploiement, les sauvegardes et le rattachement de l’ancien profil local sont expliqués dans [DEPLOYMENT.md](DEPLOYMENT.md). Au premier lancement, créer un compte ou utiliser la commande `claim-local` pour retrouver ses données historiques.

## Démarrer sur Windows

Depuis ce dossier, dans PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -c requirements.lock
.\.venv\Scripts\python app.py
```

Ouvrir **http://127.0.0.1:5000**. Si l’environnement est déjà installé, seule la dernière commande est nécessaire. On peut aussi lancer `demarrer.bat` par double-clic : il crée `.venv` si nécessaire avec Python 3.10 ou plus récent, l’active, vérifie et installe les dépendances, puis lance l’application. Garder la fenêtre ouverte pendant l’utilisation. Une connexion Internet est nécessaire pour installer les dépendances manquantes. En cas d’erreur, la fenêtre reste ouverte avec les instructions.

## Fonctionnalités

- Apprentissage progressif en six paliers, calculé à partir des XP cumulés du compte (les XP existants comptent). Départ : quiz de traduction et copie, sur les premiers mots, le quotidien et les aliments. À 60 XP : personnes, pronoms, questions et QCM sonore ; à 150 XP : loisirs, météo, verbes et écriture ; à 300 XP : expressions, possessifs, petits mots et parcours mixte ; à 500 XP : phrases, être/avoir et dictée ; à 750 XP : prépositions. Les cartes indiquent les XP manquants, le serveur vérifie les accès et les cours restent consultables. Les erreurs ne retirent pas de déblocages. Seuils regroupés dans `data/learning.py`.
- Cinq palettes avec accents violet, turquoise, corail, doré et bleu sur les cartes, les panneaux et les indicateurs ; luminosité adaptée à chaque thème.
- QCM : un mot russe, quatre traductions, une seule réponse exacte.
- Dictée sonore : écouter le russe sans mot ni traduction à l’écran, puis le saisir. Réécoute normale ou lente, validation automatique, correction illustrée et XP.
- Écoute et choisis : écouter puis reconnaître l’écriture russe parmi quatre propositions (touches 1 à 4 puis Entrée).
- 296 repères visuels locaux dans le carnet, les exemples des cours, l’alphabet et les corrections : scènes composées et schémas des prépositions. Les mots abstraits utilisent des associations visuelles. Aucun téléchargement d’image pendant l’utilisation. Crédits et licence dans `static/illustrations/CREDITS.md` ; reconstruction explicite avec `python scripts/build_illustrations.py` (Internet requis).
- Saisie français → russe, copie russe → russe et parcours mixte.
- Clavier cyrillique avec insertion à la position du curseur, espace et effacement.
- Corrections immédiates, accents toniques et ponctuation facultatifs, distinction е/ё configurable.
- 10 XP par QCM réussi, 15 XP en saisie/copie ; bonus de 2 XP par réussite consécutive, plafonné à 10 XP. Un niveau tous les 250 XP.
- Révisions espacées après 1, 3, 7, 14 puis 30 jours de réussite ; erreur à revoir immédiatement. Trois réussites consécutives marquent un mot comme maîtrisé.
- Objectif quotidien, série de jours, badges, activité sur sept jours, historique des sessions terminées.
- Carnet avec recherche russe/français, filtres, favoris et provenance de chaque entrée.
- Alphabet de 33 lettres avec écoute du nom, mots d’exemple surlignés et lecture lente.
- 18 cours simples par thème, exemples à écouter et suivi des cours terminés.
- Profil, longueur des sessions et préférences sauvegardés ; export JSON des progrès.
- Paramètres appliqués dès la modification et enregistrés automatiquement sans bouton de confirmation. L’indicateur affiche la sauvegarde ou un problème de connexion ; les changements en attente sont conservés localement pour être réessayés. Chaque modification ne touche que le réglage concerné.
- Bouton « Se déconnecter » dans la barre du haut, accessible aussi sur mobile ; menu latéral défilable sur les petites hauteurs.
- Apparition douce des pages et des cartes, transitions entre questions et réactions des boutons, avec respect de la réduction des animations du système.
- Mise en page adaptée au mobile, navigation clavier et réduction des animations.
- Cinq thèmes sauvegardés : clair, semi-clair, normal, semi-sombre et sombre intégral, avec aperçu immédiat dans les préférences. Couleurs inspirées du drapeau russe : blanc, bleu et rouge.
- Voix russes naturelles Svetlana et Dmitry, trois vitesses et bouton de préécoute dans les préférences.

L’écoute utilise par défaut **Svetlana**, une voix russe naturelle, via le service en ligne de Microsoft et la bibliothèque [edge-tts](https://github.com/rany2/edge-tts). **Dmitry** et la voix du navigateur sont également proposés. Lors de la première lecture, le texte du cours est envoyé au service vocal ; le MP3 est ensuite conservé dans `instance/audio/` pour cette voix et cette vitesse. Les sons déjà générés restent utilisables sans connexion. La disponibilité du service externe n’est pas garantie ; en cas d’échec, un message propose de choisir explicitement la voix du navigateur, dont la qualité et le fonctionnement hors ligne dépendent de l’appareil. La liste des voix installées se charge même si le navigateur la fournit tardivement. La lecture du corrigé se lance automatiquement après validation ; les autres écoutes se lancent avec le bouton « Écouter ».

Les préférences permettent de choisir la voix du navigateur et de tester les réglages, appliqués et enregistrés automatiquement. Après chaque validation, la voix lit automatiquement le mot russe corrigé dans tous les modes, y compris le quiz, que la réponse soit juste ou fausse. Le bouton « Écouter » permet de le réécouter ou de lancer la lecture si le navigateur bloque l’automatisme. Chaque bonne réponse déclenche des confettis, un gain d’XP animé et une mélodie courte, enrichie à 3 puis 5 réussites consécutives. Une erreur produit une légère secousse et deux notes descendantes ; une série interrompue est signalée sans retirer d’XP. Les effets sonores sont synthétisés localement, désactivables dans les préférences et joués dès la correction lorsque le navigateur les autorise après une interaction. Ils ne se rejouent pas au rechargement de la même correction. Les animations respectent le réglage système de réduction des mouvements. Les nouvelles préférences sont ajoutées automatiquement à une base existante, sans effacer la progression. Après une mise à jour, relancer `demarrer.bat` pour installer les dépendances et redémarrer Flask, puis recharger la page (Ctrl+F5 si nécessaire).

## Sources et vocabulaire

Pendant une session, validation, correction, mot suivant et résultats s'affichent dans le même document, sans rechargement complet. Le curseur revient automatiquement dans le champ russe et le clavier conserve son état ouvert ou fermé. Les sons déjà préparés restent disponibles entre les mots. Les transitions utilisent une seule requête serveur sans redirection ; en cas de connexion interrompue, l'application tente de relire l'état courant sans renvoyer la réponse ni recharger la page. Sans JavaScript, les formulaires classiques restent utilisables.

En saisie et en copie, une réponse correcte est détectée automatiquement après une courte pause de frappe (180 ms), sans appuyer sur Entrée. La vérification se fait sur le serveur sans dévoiler le corrigé ni attribuer de points à un brouillon. La réponse est alors validée, le mot russe est lu, puis le mot suivant s’affiche à la fin de l’audio avec le curseur dans le champ. Les vérifications anciennes sont annulées quand la saisie change, et la composition clavier est respectée.

Entrée et le bouton Valider restent disponibles, même avec une saisie vide : ils montrent et lisent la bonne réponse, puis passent à la suite. Un mot inconnu ou incorrect ne rapporte pas de points et rejoint les révisions. La correction est chargée sans navigation complète pour conserver l’interaction clavier et faciliter la lecture audio automatique. Une correction déjà lue n’est pas répétée lors d’un simple rechargement. Si la lecture est indisponible ou bloquée par le navigateur, la correction reste affichée ; Écouter permet de réessayer, et Entrée sur Continuer permet de poursuivre.

`Sources.txt` pointe vers `C:\Users\fossi\Documents\Russe`. Le catalogue comprend **296 entr?es s?lectionn?es**, dont 38 entrées sur les prépositions et 94 ajouts du 6 novembre 2026 provenant des devoirs n? 3, du cours ?tre/avoir corrig?, de la fiche sur les possessifs et du compl?ment ? la le?on 2. Le carnet propose des rappels sur ces notions. Les corrections et exclusions sont d?taill?es dans [le compte rendu de v?rification](data/verification_documents.md).

Le manuel Tome 1, les images non transcrites et les exercices personnels du dossier `??????????` sont exclus. `Texte_russe.docx` et sa version PDF ne servent pas de r?f?rences. Le catalogue n'est pas une transcription exhaustive du dossier ; les corrections concernent le contenu int?gr?, sans modifier les PDF originaux.

Le contenu est transcrit et contrôlé dans `data/build_vocabulary.py`, avec un identifiant stable et une référence à la fiche pour chaque entrée. Les traductions ont été précisées lorsque nécessaire (genre des possessifs, café boisson/lieu, lieu/direction). Le brouillon Word comportant des erreurs n’est pas utilisé comme corrigé.

Pour ajouter du vocabulaire : ajouter une ligne `russe|français|thème|clé_source` **en fin** de `ROWS` et, si nécessaire, la source dans `SOURCES`, puis :

```powershell
.\.venv\Scripts\python data/build_vocabulary.py
```

Redémarrer le serveur ensuite. Conserver l’ordre des entrées existantes : leurs identifiants sont associés aux progrès. Le serveur lit seulement `data/vocabulary.json` ; les documents originaux et `pypdf` ne sont pas nécessaires pour le lancement. Changer `Sources.txt` ne déclenche pas d’import automatique.

## Données et périmètre

La lecture normale conserve la vitesse de prononciation habituelle. Les boutons normal et lent partagent le même enregistrement : la lecture lente réduit sa vitesse à 72 %, en conservant la hauteur de la voix. Les sons visibles ou proches de l’écran sont préchargés avec deux préparations simultanées au maximum, puis conservés dans la page pour les réécoutes. Un clic sur un son déjà préparé réutilise directement son lecteur, sans nouvelle requête. La première génération, un réseau lent ou l’initialisation audio du navigateur peuvent encore entraîner une attente. Le corrigé caché des exercices de traduction reste caché et n’est chargé qu’après validation. Le mode lent est accessible dans les préférences, les exercices et le carnet.

Pour conserver la même voix, Slovo ne bascule plus automatiquement vers une autre voix en cas de lenteur ou d’erreur du service naturel. Un message permet de réessayer ou de sélectionner explicitement la voix du navigateur dans les préférences. En mode navigateur, la voix retenue reste la même entre les lectures normale et lente.

- Comptes distincts : préférences, réponses, favoris, progression, cours et sessions isolés par utilisateur.
- Base SQLite : `instance/slovo.sqlite3`. La date du système détermine les jours d’activité et de révision.
- Clé de session créée dans `instance/secret.key` ; une variable `SECRET_KEY` peut la remplacer.
- Sauvegarde cohérente : `python scripts/backup.py backups`. En production, le service Compose `backup` en crée une toutes les 24 heures. L’export JSON reste consultable ; la restauration complète utilise une sauvegarde SQLite, voir `DEPLOYMENT.md`.
- Les formulaires sont protégés contre les requêtes intersites ; les réponses et scores sont vérifiés côté serveur. Les doubles soumissions et formulaires périmés ne rapportent pas de points supplémentaires.
- Lancement local lié à `127.0.0.1`, debug désactivé. Pour Internet : Waitress, Caddy avec HTTPS, disque persistant et sauvegardes quotidiennes via Docker Compose ; voir [le guide de déploiement](DEPLOYMENT.md).

## Vérifier

Voir également le [rapport de sécurité et les limites du contrôle](SECURITY_AUDIT.md), avec les commandes d’audit reproductibles.

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Les tests utilisent des bases temporaires et couvrent les quatre modes, les points et doubles soumissions, la fin de session, les révisions, la recherche, les favoris, les préférences, la normalisation russe, la protection des formulaires et l’exclusion du manuel.
