# FeedControl V4

Extension Chrome Manifest V3 pour choisir ses thèmes YouTube, filtrer l’accueil, découvrir des vidéos et mesurer localement sa lecture **avec consentement**. FeedControl ne modifie pas l’algorithme de YouTube.

## Ce qui a été repris

Les 13 fichiers V3 fournis ont été examinés et conservés dans `legacy_v3/` (archive, pas une deuxième extension à charger). Le serveur local `127.0.0.1:8765` et `/classify`, le content script, le service worker, le classificateur, la démo et l’audit ont été prolongés. La V3 fournie référençait un `popup.js` et un `ui.css` absents. Aucun environnement virtuel, test ni modèle téléchargé n’était joint. Le dépôt initial ne contenait qu’un README. La branche de travail est `feedcontrol-v4` ; les fichiers originaux sont aussi sauvegardés hors dépôt dans `/workspace/feedcontrol-v3-backup` sur la machine de développement.

**Maquette absente :** `ui_reference/feedcontrol-v2.html` n’a pas été fourni. Le popup sombre de 400 px, les trois sections, les dégradés, les SVG dont le coureur Sport, et le footer ont été créés à partir des spécifications textuelles. Ce n’est pas une reproduction vérifiée de la V2.

## Installation Windows / PowerShell

Prérequis : Python 3.10+ et Chrome. Le fonctionnement de base utilise uniquement la bibliothèque standard Python : aucune dépendance à télécharger.

```powershell
cd C:\chemin\Feedcontrol
py -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python ai_server.py
```

Ne recopiez pas `.env.example` par-dessus un `.env` existant. Si PowerShell bloque l’activation, utilisez directement `.\.venv\Scripts\python.exe ai_server.py` sans changer la politique globale de la machine.

Ouvrez `.env` localement dans votre éditeur et renseignez `YOUTUBE_API_KEY` avec une clé d’un projet ayant **YouTube Data API v3** activée. Ne collez jamais cette clé dans l’extension, dans Git ou dans un chat. Les restrictions de clé doivent autoriser l’API et la machine qui exécute Python (pas une restriction de référent navigateur). Redémarrez Python après modification. Sans clé : classification disponible, découverte désactivée avec message de configuration.

Dans Chrome, ouvrez `chrome://extensions`, activez le mode développeur, choisissez **Charger l’extension non empaquetée**, sélectionnez le dossier contenant `manifest.json`. Épinglez FeedControl. Rechargez les onglets YouTube déjà ouverts. Le serveur doit tourner **sur le même ordinateur que Chrome** : le serveur de cet environnement cloud n’est pas accessible au Chrome de votre ordinateur par `127.0.0.1`.

### Modèle multilingue V3, optionnel

```powershell
python -m pip install -r requirements-semantic.txt
# Dans .env : FEEDCONTROL_SEMANTIC=1, puis relancer Python.
python ai_server.py
```

Premier démarrage : téléchargement du modèle officiel `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` depuis Hugging Face (réseau et espace disque nécessaires). Le modèle enrichit les **thèmes** ; les scores de qualité restent des indices heuristiques du texte. En cas d’échec : serveur utilisable, statut heuristique explicite. Ce chemin optionnel n’a pas été exécuté dans l’environnement de développement. Aucun classificateur ici ne regarde les miniatures ou la vidéo.

### Linux / cloud

```sh
cd /workspace/Feedcontrol
python ai_server.py
# Dans un autre terminal :
npm test
python -m unittest discover -s tests -v
```

Pas de `npm install` nécessaire. Pour le test navigateur optionnel, installer Playwright dans un environnement de test, disposer de Chromium puis lancer `python tests/browser_smoke.py` avec le serveur lancé sans clé API. Les API Chrome, pages et réponses sont simulées et explicitement DEMO ; aucune requête à YouTube réel. Ce test peut nécessiter d’adapter le chemin Chromium à votre OS.

## Utilisation

- **Masquer** : brainrot, clickbait, suggestif, viral, tous les Shorts. On peut aussi exclure explicitement les thèmes dans Favoriser → Exclure aussi des thèmes.
- **Favoriser** : sélection multiple persistée dans `chrome.storage.local`. Priorité visuelle avec `order` lorsque le conteneur YouTube est flex/grid. Les autres thèmes restent visibles. Le reclassement dépend donc de la mise en page YouTube.
- **Uniquement mes thèmes** : exclut les thèmes non sélectionnés et les inconnus ; sans thème sélectionné, ne restreint pas les thèmes. Les exclusions explicites passent toujours avant les favoris.
- **Contenu qualitatif** : seuils score/confiance Souple 0,40/0,35 ; Équilibré 0,65/0,55 ; Strict 0,80/0,65. Ce sont des estimations textuelles, pas une certification. Un titre sportif n’est pas une preuve de qualité. Un match intégral ou entraînement peut être acceptable ; une compilation drôle est pénalisée. Les vidéos ambiguës sont signalées inconnues. En mode Favoriser, si le serveur est arrêté, les inconnues sont conservées sans être présentées comme validées ; les exclusions explicites restent actives.
- **Découvertes FeedControl** : panneau indépendant sur l’accueil, jamais une carte native YouTube. Sous le seuil (8 par défaut), recherche de candidats ; exploration manuelle possible même au-dessus du seuil. Liens et métadonnées proviennent de l’API officielle, sans vidéo inventée. Sans résultat : message explicite, aucun assouplissement silencieux des exclusions.
- **Petits créateurs** : bonus uniquement pour une vidéo thématiquement pertinente avec nombre public d’abonnés inférieur au seuil (50 000 par défaut). Abonnés cachés = inconnus. Les vues publiques sont conservées comme métadonnée et ne prouvent pas la qualité.
- **Pourquoi cette vidéo ?** : raisons, limites et retours persistants Pertinente/Pas pertinente/Mauvaise classification. Ces retours ajustent le classement ; ils ne réentraînent aucun modèle. La correction d’un thème précis n’est pas encore proposée.
- **Suivi** : désactivé initialement. Lorsque vous l’activez, enregistre des estimations de lecture active visible, hors pause, hors publicité détectable et sans compter les sauts dans la vidéo. Ne modifie jamais le lecteur. Compte des secondes de temps réel, y compris à vitesse accélérée (pas de double durée). Échantillonnage 1 s, écriture groupée ~4 s ; une fermeture brutale peut perdre les dernières secondes.

## Découverte, quotas, confidentialité

Clé uniquement côté Python. `search.list` : au plus quatre thèmes distincts par requête, huit candidats par thème, 32 candidats maximum. Métadonnées groupées avec `videos.list` et `channels.list`. Cache mémoire TTL 15 minutes, 50 recherches différentes maximum en cache ; au plus 12 appels **search** par heure par processus (jusqu’à 1 200 unités selon le tarif API actuel de 100 par recherche, plus les métadonnées). Ce plafond ne garantit aucun quota Google et se réinitialise au redémarrage. Une seule recherche exécutée simultanément. Un retry seulement sur panne réseau/5xx ; pas de retry sur refus/quota. Aucun appel à une API YouTube interne.

Le bouton Explorer réutilise les candidats en cache durant 15 minutes ; la pénalité d’exposition favorise les candidats non montrés. Il ne promet pas de nouvelles vidéos si le pool est épuisé. Le classement combine correspondance thème +2, score qualité × confiance, bonus petit créateur +0,3, retour pertinent +0,25 / non pertinent −1 / mauvaise classification −0,2, exposition récente −0,4. Une première passe diversifie par catégorie primaire, puis complète jusqu’à 12 cartes. L’exclusion intervient **avant** le classement. Les vues publiques ne donnent aucun bonus de qualité ; leur intégration au score reste à améliorer. Les recherches suivent l’ordre des quatre premiers thèmes choisis si plus de quatre sont sélectionnés.

Une réponse devenue obsolète après changement de préférences/navigation est ignorée côté extension ; une requête serveur déjà partie peut néanmoins consommer le quota. Timeout réseau et file de classification limitée à trois appels. Cache par ID + titre limité à 500 entrées. Les métadonnées et le cache API restent en mémoire, disparaissent au redémarrage.

Titres transmis uniquement au Python local pour classement. La découverte transmet les noms des thèmes sélectionnés à l’API Google, pas l’historique de lecture. Aucune clé dans Chrome. Les données de suivi sont dans `chrome.storage.local`, agrégées par journée UTC, 7/30/90 jours au choix. Un ID est conservé localement pour dédupliquer les vidéos (2 000/jour max), sans titre ni URL. Un multi-thème est attribué à la première catégorie reconnue selon l’ordre de `taxonomy.json` pour éviter les totaux doublés. Les répartitions favoris/autres sont attribuées selon les favoris lors de la lecture. Les IDs récemment découverts sont limités à 300 pendant 7 jours et les retours à 500 entrées ; indépendants du consentement de suivi, ils servent au classement demandé. Effacer les statistiques supprime les agrégats V4 et l’ancien audit V3, pas les préférences ni les retours. Les chiffres V3 n’ont pas été migrés en faux historique V4.

## Démo en cinq minutes

1. Charger l’extension, lancer Python, ouvrir le popup : statut serveur et statut **clé configurée**, qui n’est pas une preuve d’accès API. Cliquer Ouvrir YouTube.
2. Sélectionner Sport et Bricolage. Comparer Favoriser et Uniquement, puis activer Contenu qualitatif et changer les seuils. Vérifier la notice et les vidéos masquées.
3. Activer Découvertes, fixer le seuil à 30. Sans clé : message de configuration. Avec clé valide : cartes YouTube réelles ou erreur/absence de résultat explicite. Cliquer Pourquoi cette vidéo et enregistrer un retour.
4. Activer le suivi ; regarder une vidéo 15 s, mettre en pause 10 s et passer sur un autre onglet. Vérifier que seule la lecture active contribue ; ouvrir Statistiques puis effacer.
5. Ouvrir `demo.html` depuis le dossier pour comparer les règles sur des titres inventés clairement marqués **DEMO**, sans toucher aux préférences Chrome.

## Vérifications et limites

Tests automatisés : `npm test` (32 cas, dont 24 titres avec trace de scores), `python -m unittest discover -s tests -v` (6 tests : classificateur, API HTTP, cache/déduplication/métadonnées, clé absente, erreurs/quota). Le test `browser_smoke.py` vérifie le vrai DOM Chromium avec des API Chrome simulées ; `extension_smoke.py` tente le chargement MV3 complet (bloqué ici par la politique Chromium). son résultat réel est consigné dans `CHANGELOG_V4.md`.

À vérifier manuellement sur **YouTube réel** : accueil connecté et déconnecté, scroll infini, bouton Retour, navigation SPA vers vidéo puis accueil, éléments Shorts, clic/miniature préservés, publicité/lecteur intacts, filtres après fermeture popup, clavier Tab/Espace/Entrée, console et erreurs dans `chrome://extensions`. Arrêter Python pour vérifier le mode dégradé ; ne jamais prétendre que les inconnus sont validés. Tester une clé réelle, un quota refusé et des abonnés masqués. Aucun de ces résultats en production ne peut être déduit des fixtures.

Limites connues : DOM YouTube évolutif ; classement flex/grid dépendant du site ; suivi heuristique des titres ; détection d’annonces dépendant de `ad-showing` ; pas de vision ; le format Shorts d’un résultat `search.list` n’est pas établi par cette API : avec Shorts désactivés, la découverte écarte prudemment toutes les vidéos de 3 minutes ou moins et celles sans durée, y compris certains formats longs courts ; pas de garanti de qualité sémantique réelle ; pas de reproduction V2 sans son fichier ; aucune validation de clé Google réelle ni test du modèle optionnel.

## Organisation

`taxonomy.json` et sa copie navigateur `taxonomy.js` (égalité testée), `classifier.js` (règles/scoring/temps), `background.js` (réseau et écritures sérialisées), `content.js/css` (accueil, découverte, lecture), `popup.html/css/js` (contrôles et graphiques), `stats.html`, `ai_server.py`, `tests/`, `legacy_v3/`. Les scripts de production n’utilisent aucun CDN ni JS distant. CSP Manifest V3 par défaut. Permissions : stockage et serveur local ; injection seulement sur `www.youtube.com`.
