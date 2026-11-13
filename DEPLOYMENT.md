# Mettre Slovo sur Internet

Slovo dispose de comptes avec identifiant et mot de passe, de données séparées par utilisateur et d’une configuration pour **un serveur unique avec disque persistant**. Aucune publication n’est effectuée automatiquement. Le domaine, le serveur et leurs accès restent à fournir.

## Ce qui est enregistré

- Préférences : pseudo, thème, voix, vitesse, objectif, durée, son, orthographe, volume et clavier.
- Apprentissage : réponses, XP, niveaux, séries, favoris, maîtrise, révisions, historique et session en cours.
- Cours : bouton « Marquer ce cours comme terminé », conservé par compte.

Les bonnes réponses et les préférences du formulaire sont sauvegardées à leur validation. Volume et clavier sont synchronisés après une courte pause ; une alerte apparaît si la connexion échoue. Les changements ne sont pas synchronisés instantanément entre deux onglets déjà ouverts : recharger la page pour retrouver les derniers réglages du compte.

Les mots de passe sont hachés avec scrypt. L’accès nécessite une connexion, les formulaires utilisent un jeton CSRF et les essais de connexion sont limités dans SQLite, y compris après un redémarrage. Une session dure au maximum sept jours. Changer le mot de passe ou se déconnecter invalide les autres sessions du compte également.

## Garder ton ancien profil local

Au premier démarrage de cette version, la base historique est copiée dans `instance/slovo.pre-accounts-<date>.sqlite3`, puis migrée dans une transaction. Les identifiants des mots, les réponses et les XP restent conservés. L’ancien profil n’est jamais attribué à la première personne qui s’inscrit sur le site.

Avant de publier, depuis PowerShell dans ce dossier :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c requirements.lock
.\.venv\Scripts\python.exe -m flask --app wsgi:app claim-local monidentifiant
```

La commande demande un nouveau mot de passe (15 caractères minimum), puis sa confirmation. Aucun mot de passe par défaut n’existe. Connecte-toi ensuite avec cet identifiant pour retrouver ton ancien profil. La commande refuse de réattribuer un profil déjà rattaché. Les comptes créés par inscription démarrent avec une progression vide.

Pour utiliser le site localement : `demarrer.bat`, puis connexion ou inscription. Pour tester le serveur WSGI local : `python serve.py`, adresse `http://127.0.0.1:8080`.

## Déployer sur un serveur Linux avec Docker Compose

Prérequis : Docker et Compose installés, un domaine pointant vers le serveur (A et éventuellement AAAA corrects), ports 80 et 443 accessibles. Garder le port 8080 privé : seul Caddy doit joindre l’application. Cette configuration ne nécessite pas de rendre la base accessible sur le réseau.

1. Copier le code sur le serveur, sans `.venv`, `.git`, `.env`, `instance` ni sauvegardes personnelles.
2. Copier `.env.example` vers `.env`. Renseigner `SLOVO_DOMAIN` avec le domaine seul, puis une `SECRET_KEY` aléatoire privée et stable. Pour générer la clé : `python -c 'import secrets; print(secrets.token_hex(32))'`. La saisir dans `.env`, sans la publier.
3. Préparer le répertoire des sauvegardes pour l’utilisateur du conteneur :

```sh
mkdir -p backups
sudo chown 10001:10001 backups
chmod 700 backups
docker compose build
```

4. Si tu souhaites transférer le profil local : arrêter Slovo localement, copier sa base par un canal privé sur le serveur, puis, **avant le premier démarrage de l’application**, l’importer dans le volume :

```sh
docker compose run --rm --no-deps --user root --cap-add CHOWN -v /chemin/prive/slovo.sqlite3:/import/slovo.sqlite3:ro app python -c 'import os,shutil; from pathlib import Path; p=Path("/data/slovo.sqlite3"); assert not p.exists(), "Une base existe deja : import refuse"; shutil.copyfile("/import/slovo.sqlite3",p); os.chown(p,10001,10001)'
```

Utiliser un chemin absolu et privé à la place de `/chemin/prive/slovo.sqlite3`. Cette commande refuse de remplacer une base existante. Si la base importée est encore au format historique, rattacher ensuite le profil avec `docker compose run --rm --no-deps app python -m flask --app wsgi:app claim-local monidentifiant`.

5. Démarrer :

```sh
docker compose up -d
docker compose ps
docker compose logs --tail 100 app backup caddy
```

Le serveur Waitress exécute Flask. Caddy obtient et renouvelle les certificats HTTPS et redirige HTTP vers HTTPS. SQLite et les fichiers audio sont dans le volume `slovo_data`, les certificats dans `caddy_data`. Ces volumes persistent lors des mises à jour. Ne pas utiliser `docker compose down -v`, qui supprimerait les volumes.

La configuration de production refuse de démarrer sans clé privée d’au moins 32 caractères et sans domaine autorisé. Les cookies de session exigent HTTPS. `SLOVO_PROXY=1` ne doit être activé que derrière **un** proxy de confiance, sans exposition directe du port de l’application. `.env` est lu par Compose ; le lancement Python direct utilise les variables d’environnement du système.

Contrôle après déploiement : ouvrir `https://ton-domaine/health`, créer deux comptes de test, vérifier leur séparation, enregistrer des préférences, faire un exercice, se reconnecter et tester l’audio. Cette vérification sur le serveur réel reste nécessaire : Docker et le certificat public ne sont pas exécutés par les tests Python.

## Sauvegardes et récupération

Le service `backup` crée une sauvegarde vérifiée au démarrage puis toutes les 24 heures, dans `backups/`. Il réessaie après cinq minutes en cas d’échec et journalise l’erreur. Vérifier les journaux, l’espace disque et copier régulièrement ces fichiers **hors du serveur**, dans un stockage privé. Les sauvegardes contiennent les données de tous les comptes et leurs mots de passe hachés : elles ne doivent pas être publiques. Aucun nettoyage automatique n’est effectué.

Sauvegarde supplémentaire à la demande :

```sh
docker compose exec backup python scripts/backup.py /backups
```

Ou en local :

```powershell
.\.venv\Scripts\python.exe scripts/backup.py backups
```

L’API de sauvegarde SQLite assure une copie cohérente même pendant l’utilisation. Un contrôle d’intégrité est exécuté. Une commande refuse d’écraser un fichier de sauvegarde déjà présent. L’export JSON des préférences est personnel et lisible ; la récupération complète du serveur utilise la sauvegarde SQLite.

Pour restaurer : arrêter `app` et `backup`, conserver une copie de la base actuelle, puis restaurer le fichier choisi dans `/data/slovo.sqlite3` avec le propriétaire `10001:10001`. Utiliser le script ci-dessous dans un conteneur arrêté pour la circulation des utilisateurs :

```sh
docker compose stop app backup
docker compose run --rm --no-deps --user root --cap-add CHOWN -v /chemin/prive/sauvegarde.sqlite3:/restore.sqlite3:ro app python scripts/restore.py /restore.sqlite3
docker compose up -d app backup
```

Le script vérifie l’intégrité et conserve une copie de la base remplacée. Faire un essai de restauration sur une instance séparée avant une migration importante.

Mot de passe oublié : pas d’envoi d’e-mail configuré. Le responsable vérifie l’identité de la personne, puis exécute :

```sh
docker compose exec app python -m flask --app wsgi:app reset-password monidentifiant
```

Le nouveau mot de passe est demandé dans le terminal et les anciennes sessions sont révoquées. Pour fermer les nouvelles inscriptions, mettre `ALLOW_REGISTRATION=0` dans `.env`, puis `docker compose up -d`.

## Limites de cette préparation

L’audit du code, ses corrections, ses résultats et les points restant à vérifier sur le serveur sont consignés dans [SECURITY_AUDIT.md](SECURITY_AUDIT.md). Depuis ce renforcement, une reconnexion est nécessaire ; les données d’apprentissage restent conservées. Les nouveaux mots de passe exigent 15 caractères et les anciennes empreintes sont renforcées après une connexion réussie. Les versions d’exécution sont verrouillées par `requirements.lock`.

Cette configuration vise une petite instance sur un serveur unique. Ne pas multiplier les répliques ni mettre SQLite sur un partage réseau. Pour une forte fréquentation, migrer vers PostgreSQL et prévoir un stockage partagé et une limitation du débit des demandes audio. La génération vocale dépend d’un service externe ; le navigateur reste une alternative à choisir dans les préférences. Le nom de domaine, le serveur, les sauvegardes hors site, la supervision et l’éventuel service de récupération par e-mail restent à configurer par l’exploitant.

Références : [déploiement Flask](https://flask.palletsprojects.com/en/stable/deploying/), [sécurité Flask](https://flask.palletsprojects.com/en/stable/web-security/), [Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html), [HTTPS Caddy](https://caddyserver.com/docs/automatic-https), [volumes Docker](https://docs.docker.com/reference/compose-file/volumes/).
