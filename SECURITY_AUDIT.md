# Audit de sécurité Slovo — 10 novembre 2026

## Résultat et périmètre

Audit et corrections effectués sur le code Flask/Jinja/JavaScript, les requêtes SQLite, les comptes, les fichiers privés, les dépendances Python et la configuration de déploiement fournie. Les essais utilisent des bases temporaires : la base personnelle existante n’a pas été remplacée et aucun mot de passe réel n’a été lu.

Résultats : **43 tests Python réussis**, dont les tests de sécurité ajoutés et un contrôle HTTP avec un vrai serveur Waitress sur une adresse locale. **Aucune vulnérabilité connue signalée par pip-audit** dans les 50 distributions inspectées de l’environnement local après correction, ni dans l’environnement des outils d’audit. Le fichier `requirements.lock` verrouille les 22 dépendances du graphe d’exécution. **Bandit ne signale aucune anomalie non justifiée** sur le code de l’application et les scripts d’exploitation. Ces résultats sont datés : les bases d’avis de vulnérabilité peuvent évoluer.

Les sept scripts JavaScript ont été analysés syntaxiquement. La revalidation de l’historique et du changement de compte a été testée avec un environnement JavaScript simulé, pas par une vérification visuelle dans un navigateur réel. La configuration Compose a été analysée comme YAML ; Docker n’étant pas installé ici, l’image et Caddy n’ont pas été exécutés.

Cela ne constitue ni une certification, ni une garantie d’absence de faille. Le système d’exploitation, les certificats TLS publics, le DNS, le pare-feu et l’hébergement réel restent à auditer après déploiement.

## Faiblesses corrigées

| Point | Risque avant correction | Correction et preuve |
|---|---|---|
| Durée des connexions | La réémission d’un cookie après une activité pouvait prolonger l’authentification au-delà des sept jours annoncés. | Date de début d’authentification signée, contrôlée à chaque requête privée. Test d’une activité au jour 6 puis d’un accès au jour 8. Les anciennes sessions sans cette date doivent se reconnecter. |
| Transport de production | Une mauvaise exposition du serveur pouvait permettre de présenter le formulaire de connexion en HTTP. | Refus du HTTP dans l’application de production, sauf sonde `/health` sans données privées. Cookies `__Host-slovo`, Secure, HttpOnly, SameSite=Lax, domaine absent, chemin `/`. Le mode debug est forcé à faux. Tests de configuration et de trafic Waitress. |
| Requêtes coûteuses | La génération audio et le hachage pouvaient occuper tous les threads ou consommer trop de mémoire. Les créations de sessions d’exercice et exports étaient peu limitées. | Deux travaux simultanés maximum pour chaque catégorie coûteuse, sans attente d’un thread supplémentaire ; limites persistantes par compte et limite globale des opérations de mot de passe. Réponses 429/503 explicites. Tests de saturation sans perte de données. Cela ne remplace pas une défense réseau contre un déni de service distribué. |
| Cache et changement de compte | Les réponses audio n’avaient pas la même politique de cache que les autres réponses authentifiées ; les pages privées pouvaient rester visibles dans un historique restauré. | `no-store` sur les réponses hors fichiers statiques, `Vary: Cookie`, revalidation de l’historique et des changements de compte entre onglets. Les ressources publiques et la sonde ne créent plus de cookie. Le contrôle d’accès reste effectué sur le serveur, indépendamment du JavaScript. |
| Politique des mots de passe | La politique de 12 caractères et les paramètres scrypt implicites ne suivaient pas les recommandations OWASP retenues pour un compte sans MFA. | Nouveaux mots de passe de 15 à 128 caractères, scrypt explicite `32768:8:3`, sel aléatoire de 16 caractères. Les anciennes empreintes restent vérifiables et sont renforcées après une connexion réussie. Aucun changement d’empreinte après un échec. |
| Fichiers de sauvegarde | Permissions dépendant du masque système et vérification d’existence non atomique avant création. | Création exclusive `O_EXCL`, mode 0600 sur Unix, répertoire de données 0700, masque 077 du serveur de production. Refus d’un chemin existant, y compris un lien symbolique. Les permissions Unix restent à valider sur le serveur Linux ; sous Windows, les ACL du dossier doivent être privées. |
| Dépendances et livraison | Outils d’installation locaux obsolètes ; installation non verrouillée ; image copiant tout le répertoire du projet. | Mise à jour de pip/setuptools. Outils d’audit isolés sous Python 3.11 avec une version corrigée de filelock. Contraintes des dépendances d’exécution, copie explicite des seuls fichiers nécessaires dans Docker. Fichiers locaux, clés, sauvegardes, environnement virtuel et données de développement exclus de l’image. |
| Confinement du déploiement | L’application pouvait écrire dans tout le système de fichiers de son conteneur et dans les sauvegardes montées. | Racine de l’application en lecture seule, utilisateur non privilégié, capacités supprimées, interdiction d’acquérir des privilèges, limites mémoire/CPU/processus. Les sauvegardes sont montées en lecture seule dans l’application et sont écrites par le service de sauvegarde séparé. Port de l’application non publié. |

## Contrôles sans faille exploitable observée dans les essais

- **SQL** : paramètres séparés du SQL ; mise à jour des préférences d’interface réécrite sans construction de requête. Les noms de tables de migration viennent d’une liste fixe et les colonnes sont intersectées avec le schéma fixe du logiciel. Les charges SQL dans la connexion, le nom et les préférences ne s’exécutent pas.
- **Séparation des comptes** : préférences, cours, historique, réponses, favoris et exports filtrés par l’identité authentifiée. Les mutations des sessions d’exercice ont aussi un filtre SQL explicite sur leur propriétaire. Un identifiant utilisateur fourni dans l’URL ou le formulaire ne choisit jamais le compte cible.
- **Sessions** : signature non falsifiable sans la clé secrète, rotation après connexion, invalidation après déconnexion/changement/réinitialisation de mot de passe. Une modification du mot de passe vérifie aussi que la version de session n’a pas changé pendant l’opération. Une session falsifiée ne donne pas accès aux données.
- **CSRF et XSS** : jetons requis sur les formulaires de mutation, anciens jetons rejetés après connexion ; échappement Jinja des champs et réponses, absence d’insertion de saisie brute par `innerHTML`, politique CSP sans scripts inline ni `eval`. Les charges XSS testées restent du texte.
- **Chemins et secrets** : routes ne servant ni base SQLite, ni clé de session, ni `.env`, ni dépôt Git, ni sauvegardes ; tentatives de traversée avec `/` et `\` rejetées. Aucun secret de production trouvé en dur dans les modules de l’application. Les scripts d’administration ne sont pas des routes HTTP.
- **Entrées et ressources** : formulaires limités à 16 Kio, champs numériques bornés, champs d’interface autorisés explicitement, aucun import de fichier offert aux visiteurs et aucune commande système construite à partir de leurs saisies.
- **Audio et appels sortants** : seuls les mots fixes du catalogue, les exemples fixes de l’alphabet et l’exemple vocal fixe sont envoyés au service vocal. Aucun paramètre ne permet de choisir une URL distante ou un chemin arbitraire. Les préférences et réponses personnelles ne sont pas le texte à synthétiser.
- **Sauvegardes et progression** : sauvegarde cohérente via SQLite, contrôle d’intégrité, refus d’écrasement et conservation des données précédentes lors d’une restauration. Migration de l’ancien schéma transactionnelle et testée avec l’historique complet. Soumissions répétées d’une réponse ne multiplient pas les points.

Les six avertissements statiques conservés sous des annotations ciblées sont documentés dans le code : deux constructions de migration à noms autorisés, un tirage aléatoire pédagogique, une constante publique de paramètres scrypt et l’import/appel de subprocess avec arguments fixes, sans shell, pour les sauvegardes. Les annotations ne s’appliquent pas aux autres lignes et ne désactivent pas globalement ces règles.

## Vérifications encore nécessaires sur le serveur

1. Tester l’image construite, Caddy, les certificats publics et la redirection HTTP vers HTTPS. Vérifier qu’aucun port d’application ni fichier privé n’est publié. N’activer `SLOVO_PROXY=1` que derrière un unique proxy de confiance ; Caddy doit écraser les en-têtes de transfert reçus du public.
2. Définir une `SECRET_KEY` privée, aléatoire et stable ; garder `.env` et les sauvegardes hors des répertoires publics. Restreindre les comptes système, les ACL Windows ou les permissions Linux, le compte d’administration et les accès au serveur. Les tests locaux Windows n’attestent pas les ACL du futur hébergeur.
3. Configurer des copies de sauvegarde privées hors du serveur, leur chiffrement dans le stockage choisi, la rétention, les alertes d’échec et un essai de restauration. Les sauvegardes SQLite contiennent les données de tous les comptes et des empreintes de mots de passe ; elles ne sont pas chiffrées par l’application.
4. Surveiller l’espace disque et le trafic ; prévoir une protection réseau contre les attaques distribuées. Les limites applicatives ne rendent pas un service invulnérable à une saturation.
5. Réexécuter l’audit à chaque mise à jour et régulièrement. Maintenir également le système d’exploitation, l’image Python et Caddy. Leurs paquets système et leurs images ne sont pas couverts par pip-audit.

Limites fonctionnelles explicites : pas de MFA, pas de détection exhaustive de mots de passe divulgués, pas de récupération par e-mail et pas de poivre de mot de passe. Les mots de passe sont hachés et salés. Un poivre n’a pas été ajouté sans un dispositif adapté de conservation et de rotation des secrets. Une personne administrant le serveur peut accéder à ses fichiers et à la base : l’application ne protège pas contre un administrateur compromis.

## Reproduire les contrôles

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m pip check
py -3.11 -m venv .venv-audit
.\.venv-audit\Scripts\python.exe -m pip install --upgrade pip setuptools -r requirements-security.txt
.\.venv-audit\Scripts\python.exe -m bandit -r app.py accounts.py storage.py security.py speech.py serve.py wsgi.py scripts
.\.venv-audit\Scripts\python.exe -m pip_audit --path .venv/Lib/site-packages --cache-dir tmp/pip-audit-cache
```

Ne pas installer les outils d’audit dans l’image de production. Les versions corrigées de filelock requièrent Python 3.11 ou plus ; l’application locale peut conserver Python 3.10. Pour actualiser une version du logiciel, mettre à jour les contraintes `requirements.lock`, vérifier la compatibilité et relancer l’audit avant livraison.

Rapports des outils : [dépendances locales](security_reports/dependencies.json), [outils d’audit](security_reports/audit-tools.json), [analyse statique](security_reports/bandit.json).

Références utilisées : [sécurité Flask](https://flask.palletsprojects.com/en/stable/web-security/), [authentification OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [stockage des mots de passe OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [sessions OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [paramètres Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).
