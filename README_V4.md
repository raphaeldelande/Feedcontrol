# FeedControl 0.4.1 — installation et fonctionnement réel

Extension Chrome Manifest V3 : filtres explicables sur l’accueil YouTube, découvertes indépendantes, petits créateurs et suivi local avec consentement. FeedControl ne modifie pas l’algorithme YouTube.

## Mettre à jour depuis la V4

1. Télécharger le ZIP de la branche `feedcontrol-v4` et le décompresser dans un dossier distinct.
2. Arrêter l’ancien Python avec Ctrl+C. Démarrer le nouveau serveur depuis ce nouveau dossier (commandes ci-dessous). Si vous aviez une clé, conserver votre `.env` local en le copiant dans ce dossier ; ne le publiez jamais.
3. Dans `chrome://extensions`, retirer l’ancienne extension puis charger le nouveau dossier, ou remplacer les fichiers de l’ancien dossier et cliquer sur **Recharger** pour conserver l’identifiant et les préférences.
4. Recharger les onglets YouTube déjà ouverts. Ouvrir le popup puis **Actualiser le diagnostic**.

Le popup utilise maintenant une seule colonne. **Ouvrir les réglages en grand** donne une page complète sans les contraintes de taille du popup. Le diagnostic distingue ancien serveur, serveur arrêté, modèle texte inactif, clé absente, erreur API et modules visuels disponibles.

## Windows / PowerShell

Prérequis : Python 3.10+ et Chrome. Ouvrir PowerShell dans le dossier qui contient `manifest.json` et `ai_server.py` :

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe ai_server.py
```

L’activation du venv est facultative. Si vous souhaitez l’activer : `.\.venv\Scripts\Activate.ps1` puis `python ai_server.py`. Pas besoin de modifier la politique PowerShell pour utiliser directement le Python du venv.

Le script `lancer_feedcontrol.ps1` reproduit ces étapes, préserve un `.env` existant et crée une copie du modèle seulement si le fichier n’existe pas. Il n’a pas été exécuté sur Windows ici ; les commandes Python équivalentes ont été vérifiées sous Linux dans un venv neuf. L’installation de base ajoute Pillow et numpy pour les pixels ; aucun gros modèle n’est téléchargé automatiquement.

Dans `chrome://extensions`, activer Mode développeur → Charger l’extension non empaquetée → sélectionner le dossier contenant le manifest. Garder le terminal Python ouvert. **Chrome et Python doivent tourner sur le même ordinateur.** Un Python exécuté dans le cloud n’est pas le serveur local de votre Chrome personnel.

## Trouver de nouvelles vidéos, même absentes du feed

Le mode **Uniquement mes thèmes** et l’option **Petits créateurs** déclenchent maintenant la découverte automatiquement. Le mode Favoriser utilise le bouton Découvertes ou l’exploration manuelle. Les candidats apparaissent dans **Découvertes FeedControl**, séparément des recommandations natives.

La recherche automatique exige **YouTube Data API v3** :

1. Dans Google Cloud Console, créer/choisir un projet et activer YouTube Data API v3.
2. Dans API et services → Identifiants, créer une clé API, restreinte à cette API et à votre usage serveur.
3. Copier `.env.example` vers `.env` **seulement si `.env` n’existe pas**, puis compléter localement `YOUTUBE_API_KEY=` dans votre éditeur.
4. Arrêter puis relancer Python. Revenir dans le popup, Actualiser le diagnostic, puis Explorer dans le panneau YouTube.

Ne jamais donner la clé dans un chat, la mettre dans l’extension ou dans Git. Une clé configurée ne prouve pas son autorisation ; le diagnostic affiche la dernière recherche réellement effectuée. Sans clé, serveur ou quota, le panneau explique le blocage et propose des **liens normaux de recherche YouTube** par thème. Ces liens n’injectent pas de faux résultats et ne remplacent pas une API configurée.

Pour Cuisine : la recherche utilise « recette cuisine maison pas à pas », et non seulement le libellé « Cuisine ». Les filtres transversaux et les exclusions s’appliquent ensuite aux vrais résultats. Si tous sont exclus, le panneau montre combien et pourquoi, sans assouplir silencieusement les critères.

## Classification plus précise

- `taxonomy.json` / `taxonomy.js` : catégories et vocabulaire FR/EN, incluant vocabulaire de cuisine, sport, bricolage et punchlines de motivation.
- `genre_profiles.json` : pour **chacun des 16 genres**, exemples positifs, contre-exemples, codes visuels et requête de découverte. Le modèle texte utilise les positifs, contre-exemples et types de contenu ; le modèle visuel reçoit les codes visuels.
- `classification_rules.json` / `.js` : mêmes types et seuils qualitatifs des deux côtés (égalité testée).
- Le thème, le type, la qualité et sa confiance restent distincts. Un nom de personnalité, une image monochrome ou une petite chaîne ne certifient jamais la qualité.
- Shorts : **seulement analyse ou apprentissage** activé par défaut. Un edit sportif, un match court sans explication ou un Short sans titre ne passent pas uniquement parce qu’ils sont sportifs. Analyses/cours/contenu éducatif/documentaires restent admissibles. Cette option est désactivable séparément de « tous les Shorts ».
- L’option **Masquer les vidéos non classées** est explicite. Sans cette option, les inconnues peuvent rester visibles en mode Favoriser, particulièrement si le serveur est arrêté. Le mode Uniquement ne les présente pas comme validées.
- Qualité : Souple score/confiance ≥0,40/0,35 ; Équilibré ≥0,65/0,55 ; Strict ≥0,80/0,65. Ce sont des estimations, pas une certification après visionnage.

### Modèle texte multilingue

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-semantic.txt
# Dans .env : FEEDCONTROL_SEMANTIC=1
.\.venv\Scripts\python.exe ai_server.py
```

Réutilise le moteur V3 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` avec profils enrichis. Les thèmes et types sont comparés séparément ; une ressemblance thématique n’implique pas une qualité élevée. Les similarités ne sont pas des probabilités. Installation/téléchargement requis, modèle non exécuté ici : Hugging Face est refusé par le proxy cloud (HTTP 403). Sans modèle, le diagnostic annonce des règles texte.

### Miniatures réellement examinées

L’option **Analyser les miniatures localement** envoie l’ID au Python local, qui récupère la miniature publique officielle sur `i.ytimg.com` ; aucune URL arbitraire ni redirection n’est acceptée. Image ≤1,5 Mo et 4 millions de pixels, analyse réduite à 320×180, cache 500 images / TTL 1 h, échec caché 60 s et concurrence visuelle limitée à deux.

1. **Pixels (Pillow/numpy)** : composantes rouges, géométrie de formes ressemblant à des cercles ou flèches, proportion monochrome. Un objet rouge uni n’est pas considéré automatiquement comme une annotation. Ces détecteurs sont heuristiques et peuvent manquer certaines formes ou produire de faux positifs.
2. **OCR local** : si Tesseract est installé et accessible dans le PATH, lit le texte incrusté avec limite de temps et seuil de confiance. « FOCUS IN LIFE » peut ainsi contribuer au thème motivation, même avec un titre vague. Une image noir et blanc seule ne le peut pas. L’OCR anglais peut mal lire certains textes français.
3. **Modèle multimodal optionnel** : installer Ollama sur cet ordinateur puis `ollama pull qwen2.5vl:3b`. Ajouter `FEEDCONTROL_VISION_MODEL=qwen2.5vl:3b` dans `.env`, redémarrer Python. Le serveur contacte uniquement `127.0.0.1:11434`, avec un timeout. Le modèle reçoit les profils visuels et propose scène, thèmes, type de présentation et incertitude. Il ne reconnaît pas l’identité des visages. S’il est absent/lent/inaccessible, aucune sortie de modèle n’est inventée ; pixels et OCR restent utilisables. Ce moteur optionnel n’a pas été exécuté ici.

Des annotations rouges ne prouvent pas une tromperie. En présence d’un type pédagogique explicite, le diagramme reste admissible. Sans contenu de fond identifié, elles abaissent le score et peuvent activer l’exclusion Clickbait : raison « présentation potentiellement racoleuse ». Un montage de memes suggéré avec faible incertitude par le modèle visuel alimente le type viral, sans prétendre avoir vu la vidéo. Les raisons et limites sont consultables dans le panneau ; la notice indique combien de miniatures ont réellement été examinées.

## Petits créateurs : comportement visible

L’option active une recherche **pertinence + date** pour élargir le pool au-delà des vidéos populaires, puis demande les métadonnées des chaînes par lots. Le panneau affiche le nombre public d’abonnés et le nombre de candidats compatibles sous le seuil (50 000 par défaut). Abonnés cachés/absents restent inconnus, jamais zéro.

Score : correspondance thème +2 ; qualité×confiance ; bonus petit créateur **+1,25 uniquement si pertinent et score/confiance ≥0,65/0,55** ; retour pertinent +0,25, non pertinent −1, mauvaise classification −0,2 ; exposition récente −0,4. Diversification par thème puis remplissage jusqu’à 12 cartes. Les vues publiques sont conservées sans donner de bonus automatique de qualité. Les cartes natives n’exposent généralement pas le nombre d’abonnés : cette préférence concerne **Découvertes**, pas une reconnaissance supposée de la taille de chaque chaîne native.

## Quotas et dégradation

Au plus quatre thèmes par recherche, 16 résultats par thème/ordre, 64 IDs dédupliqués, vidéos/chaînes groupées par 50. Plafond local : 12 appels `search.list` par heure et par processus, jusqu’à 1 200 unités au tarif de 100 unités/recherche, plus les métadonnées ; ne garantit pas le quota Google. Petits créateurs utilise deux appels search par thème. Cache 15 min ; Explorer peut paginer après 45 s avec le `nextPageToken` réel. Avant ce délai, rotation locale dans les candidats disponibles. Cache/limite réinitialisés au redémarrage. Un retry réseau/5xx ; pas de retry refus/quota. Pas d’API YouTube interne ni scraping opaque.

Les classifications sont mises en cache par ID/titre/métadonnées/option visuelle. Les réponses obsolètes après navigation ou préférences sont ignorées ; une requête serveur déjà partie peut consommer le quota. Enrichissement de 12 candidats maximum, deux requêtes à la fois côté panneau, sans attendre toutes les images avant de présenter les résultats texte. Les métadonnées d’abonnés et vues sont préservées lors de cet enrichissement.

## Suivi et confidentialité

Suivi désactivé initialement, uniquement après consentement. Échantillonnage 1 s : lecture active, visible, hors pause/recherche/publicité détectable. Secondes de temps réel, écritures ~4 s ; fermeture brutale peut perdre les dernières secondes. Agrégats locaux par journée UTC et catégorie primaire, conservation 7/30/90 jours, effacement complet des statistiques V4 et anciennes V3. Les multi-thèmes ne doublent pas les totaux. IDs pour déduplication bornés à 2 000/jour ; retours bornés à 500 ; exposition découverte 300 IDs/7 jours, indépendante du suivi et utilisée pour le classement demandé. Aucun historique personnel transmis à Google ou à Ollama : seuls les thèmes de recherche partent à Google ; les miniatures publiques sont récupérées par ID ; l’OCR et les modèles tournent localement.

## Vérifications exécutées

```sh
npm test
.venv/bin/python -m unittest discover -s tests -v
python tests/browser_smoke.py
```

Node requis uniquement pour les tests. `npm install` inutile. Playwright et Chromium requis pour le test navigateur optionnel ; le navigateur système est utilisé, les API Chrome et pages YouTube sont **simulées**.

- 36 tests JavaScript : 24 titres fictifs avec scores/raisons, règles de priorité et migration, lecture, worker concurrent/consentement, Shorts, inconnues, motivation/OCR, annotations et petits créateurs.
- 15 tests Python : classificateur, HTTP, recherche cuisine/abonnés/pagination, cache/quota/clé absente, géométrie d’images synthétiques, **OCR Tesseract réellement exécuté** et extraction du thème à partir de ce texte, erreurs visuelles.
- Chromium DOM : persistance et propagation, automatique Cuisine sans recommandation native, préférence petits créateurs et métrique visible, Shorts modernes sans titre, feedback, SPA, statistiques/effacement et contrôle des catégories dans des fenêtres de **280, 320 et 400 px**.

La suite n’établit ni la précision sur toutes les miniatures YouTube, ni le bon fonctionnement d’une clé Google réelle, ni l’inférence d’un modèle optionnel. L’essai de téléchargement d’une miniature publique sur i.ytimg.com a aussi été refusé par le proxy cloud (HTTP 403) : récupération réseau des miniatures à valider sur votre ordinateur. Le chargement MV3 complet est bloqué ici par la politique système de Chromium. `tests/extension_smoke.py` reste un scénario distinct à adapter sur une machine autorisée.

## Validation manuelle en cinq minutes

1. Charger la 0.4.1, redémarrer Python, recharger YouTube, vérifier diagnostic et réglages en grand. Tester clavier Tab/Espace, zoom et défilement du popup.
2. Choisir **Cuisine → Uniquement**, sans recette native : vérifier le panneau Découvertes, ses candidats réels si API configurée, sinon l’explication et le lien de recherche.
3. Activer **Petits créateurs** : vérifier le nombre public d’abonnés, les inconnus explicitement signalés et le nombre de candidats compatibles. Aucun petit créateur trouvé n’est un résultat possible, pas un succès simulé.
4. Favoriser Sport, activer le qualitatif et les Shorts pédagogiques : comparer analyse tactique, vrai match long, edit drôle et Short sans titre. Examiner les limites affichées. Les flèches/cercles ne constituent pas une preuve suffisante à eux seuls.
5. Activer le suivi, regarder 15 s, mettre en pause et changer d’onglet ; vérifier puis effacer les données. Arrêter Python pour tester le mode dégradé et le message de correction.

## Limites conservées

DOM YouTube évolutif et reclassement CSS dépendant de flex/grid ; pas de modification du lecteur ou des publicités ; les résultats API ne déterminent pas exactement le format Shorts (si tous les Shorts sont exclus, les durées ≤3 min ou inconnues sont retirées prudemment). Pas de visionnage complet, pas de certification de qualité, pas de réentraînement instantané, pas de reconnaissance de personnes. Retours de classement, pas encore d’éditeur de thèmes corrigés. Pas de courbe comparative entre deux périodes. La maquette `ui_reference/feedcontrol-v2.html` n’a pas été fournie ; le design suit le texte, pas une reproduction vérifiée de ce fichier.

La V3 d’origine est archivée dans `legacy_v3/`. Le prompt fourni reste dans `docs/`. Les scripts de production ne chargent aucun CDN. La branche de livraison est `feedcontrol-v4` ; `main` n’est pas modifiée.
