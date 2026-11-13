# Optimisations de Slovo — 13 novembre 2026

Le carnet charge 36 cartes par page et conserve la recherche, les filtres et les favoris. Les 296 mots restent accessibles. Les images sont décodées de manière asynchrone ; les cartes hors écran peuvent différer leur rendu dans les navigateurs compatibles.

Les fichiers publics CSS, JavaScript et images ont une version dans leur URL et un cache navigateur d’un an. Les pages privées, les réponses d’exercice et les sons protégés gardent `Cache-Control: no-store`. Après une mise à jour, redémarrer l’application renouvelle les versions des ressources.

Les transitions d’exercice transmettent seulement le contenu utile et les compteurs. Elles conservent les contrôles de session, la correction, la prononciation et la récupération après erreur réseau. Les scripts audio et d’exercice sont chargés seulement sur les pages qui les utilisent.

Le cache audio du navigateur est limité à 12 enregistrements, avec deux préparations simultanées et six préparations en attente au maximum. Les anciens lecteurs et URL temporaires sont libérés. Le préchargement reste proche des éléments visibles ; la voix et la vitesse naturelle restent identiques. Le moteur des effets sonores se met en veille après une période d’inactivité. Les animations restent courtes, sans boucle permanente.

Les préférences et totaux sont réutilisés au sein d’une même requête, puis invalidés après une réponse notée. Aucune donnée de compte n’est mise en cache globalement. Les recherches normalisées du catalogue sont préparées une fois au démarrage. L’activité hebdomadaire utilise une seule requête groupée.

Le lanceur vérifie localement les versions installées avant d’invoquer pip et n’utilise le réseau que lorsqu’une installation est nécessaire. Il démarre le serveur Waitress sur `127.0.0.1:5000`, avec quatre threads par défaut. `SLOVO_THREADS` permet d’ajuster ce nombre (1 à 32).

## Mesures reproductibles

Client de test Flask local, base temporaire avec 10 000 réponses fictives, 12 requêtes par route après compilation initiale des modèles. Ce test mesure le traitement serveur et le HTML transmis ; il ne mesure ni le temps réseau, ni les images par seconde, ni la mémoire totale du navigateur. Les questions tirées au hasard peuvent faire légèrement varier leur taille.

| Route | Médiane avant | Médiane après | Requêtes SQL avant → après | HTML avant → après |
|---|---:|---:|---:|---:|
| Accueil | 7,57 ms | 6,50 ms | 12 → 9 | 21 118 → 21 352 octets |
| Carnet | 27,62 ms | 9,36 ms | 11 → 8 | 459 172 → 68 053 octets |
| Exercice, page complète | 6,61 ms | 5,80 ms | 11 → 8 | 9 220 → 9 750 octets |
| Exercice, transition | 7,74 ms | 5,37 ms | 11 → 8 | 9 220 → 5 270 octets |

Le carnet produit environ 85 % de HTML en moins par page et se génère environ trois fois plus vite sur ce test. Ces résultats ne constituent pas une mesure des performances sur tous les appareils.

Commande : `.\.venv\Scripts\python -X utf8 scripts/benchmark_app.py --output tmp/performance.json`. Ce script utilise uniquement des données fictives et ne modifie pas la progression réelle.

Vérifications : suite Python, tests JavaScript de saisie et de sauvegarde automatique, plus une simulation audio de 40 mots vérifiant la limite de 12 enregistrements et la libération des anciennes ressources. Pas de contrôle visuel ou de mesure de mémoire du navigateur effectué pendant cette optimisation.
