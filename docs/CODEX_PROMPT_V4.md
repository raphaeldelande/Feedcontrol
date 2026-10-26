# MISSION CODEX — FeedControl V4

Tu es mon assistant de développement dans VS Code. Travaille DIRECTEMENT dans mon dépôt/projet **FeedControl V3**, actuellement ouvert. Je débute en programmation : privilégie une architecture claire, des noms explicites et une documentation compréhensible. Ne te contente pas d'un plan : **inspecte la V3, écris le code nécessaire, teste-le et documente ce qui fonctionne réellement**.

## Objectif du produit

Transformer mon extension Chrome **FeedControl** en un système de contrôle personnalisé de l'expérience YouTube. La V3 filtrait essentiellement en MASQUANT les recommandations non conformes. Problème : le flux peut être presque vide si YouTube ne recommande pas déjà les thèmes demandés (par exemple bricolage). **La V4 doit (1) analyser, (2) filtrer et hiérarchiser, et (3) proposer de NOUVELLES vidéos pertinentes dans un espace clairement identifié FeedControl Découvertes.** Ne prétends pas modifier l'algorithme interne de YouTube. Ne crée pas de fausses vidéos ou de recommandations prétendument réelles.

## Préparation impérative

- Examine TOUS les fichiers utiles de la V3 avant toute modification : arborescence, manifest.json, popup, content scripts, service worker, fichiers CSS/JS, serveur Python, environnement virtuel, API `/classify`, modèle, tests, éventuel README. Ne suppose aucun nom de fichier ni endpoint autre que ceux trouvés. Le projet avait un serveur local Python sur 127.0.0.1:8765 avec un endpoint `/classify` lors de versions précédentes : CONFIRME son existence et conserve la compatibilité si possible.
- Établis un diagnostic court : composants existants, fonctionnalités réellement opérationnelles, code réutilisable, fragilités. Ne remplace pas la V3 par un projet vierge.
- Avant modifications, crée une sauvegarde locale ou branche `feedcontrol-v4` si Git est disponible et le dépôt propre. Ne supprime aucune donnée et ne casse pas les configurations existantes.
- Le fichier **`ui_reference/feedcontrol-v2.html`** est la maquette graphique de référence. Lis-le entièrement et RÉUTILISE son style, ses icônes SVG, sa palette, ses noms/codes/couleurs de catégories, ses cartes déroulantes et son footer. Adapte son HTML/CSS/JS au vrai popup de l'extension en séparant proprement les fichiers si nécessaire. Ne te contente pas d'afficher le fichier à part : **la vraie extension Chrome doit utiliser le nouveau design**.

## Interface / design non négociable

- Extension Chrome Manifest V3, interface sombre, épurée, compacte, inspiration « réglages Apple », sans reprendre d'assets propriétaires. Typographie système ou Geist locale, pas de CSS/JS distant dépendant d'un CDN dans l'extension.
- En-tête FeedControl et icône étoile blanc/rose/violet inspirée de la maquette fournie.
- Trois sections dépliables : **Masquer** (rouge), **Favoriser** (rose/violet), **Suivi** (vert/turquoise). Chaque sous-catégorie possède sa propre icône SVG blanche dans un carré arrondi à dégradé coloré, et un libellé lisible. **Conserver l'icône Sport en coureur stylisé de la v2**, sauf amélioration évidente dans le même style.
- En bas, discret, gris, centré : « Développé par Raphaël Delande ». Aucun gros panneau « À propos ».
- Actions visibles : sélection multiple, option « Favoriser », mode « Uniquement mes thèmes », mode « Contenu qualitatif », désactivation de tous les Shorts, activation de la découverte, préférence pour les petits créateurs, réglage de la durée observée, affichage de l'état du serveur et de l'accès à l'API YouTube.
- Le popup doit rester rapide, lisible à ~390-410 px et utilisable au clavier. Indicateurs de sélection et état des interrupteurs persistants. Statistiques plus complètes possibles dans une page dédiée `stats.html` si le popup devient trop long ; le panneau « Suivi » doit afficher l'essentiel.
- Données démo clairement étiquetées DEMO ; jamais présentées comme du vrai suivi.

## Taxonomie commune : ne pas fusionner thème et qualité

**À masquer**, chacun avec un code stable :
- `brainrot` (contenu absurde répétitif et purement addictif), `clickbait` (titres/miniatures trompeurs), `suggestif` (contenu suggestif non demandé), `viral` (montages, compilations et memes viraux), `shorts` (option de blocage format court YouTube Shorts).

**À favoriser**, codes exacts de la maquette :
- `science`, `motivation`, `sport`, `bricolage`, `cuisine`, `musique`, `philosophie`, `cinema`, `histoire`, `geopolitique`, `economie`, `tech_ia`, `maths`, `sante`, `langues`, `documentaires`.

Chaque vidéo doit avoir plusieurs dimensions DIFFÉRENTES :
- `topics`: zéro, une ou plusieurs catégories thématiques ;
- `contentType`: `educatif`, `analyse`, `cours`, `documentaire`, `performance_authentique`, `divertissement`, `compilation_virale`, `clickbait`, `suggestif`, `inconnu`, etc. ;
- `qualityScore` (0-1) ET `qualityConfidence` (0-1), distincts des thèmes, plus des explications/indices disponibles ;
- `blockedReasons` et `recommendationReasons` lisibles, fondés sur des éléments réellement examinés ;
- `videoId`, `channelId`, titre, description SI DISPONIBLE, miniature SI réellement analysée, durée SI disponible, statistiques publiques SI disponibles, source (`youtube_dom` ou `youtube_api`).

Le détecteur sémantique doit idéalement réutiliser le moteur IA existant. Ne prétends pas qu'un classificateur heuristique à mots-clés est une IA capable de comprendre les miniatures. Si l'IA ou la vision ne fonctionne pas, exposer honnêtement les limites / `inconnu` plutôt que faire semblant. Traiter de façon raisonnable les titres français et anglais. Limiter les requêtes et mettre en cache les résultats par `videoId`.

**Sport, cas test crucial** :
- Acceptables avec mode qualitatif : analyses tactiques football, vrais matchs/compétitions, séquences sportives authentiques, entraînement, technique sportive, science de l'entraînement, analyses stratégiques.
- Rejetables avec mode qualitatif : « funny football moments », edits viraux, compilations de fails, memes de joueurs, Shorts d'humour sans analyse, montage répétitif avec effet de rétention sans contenu substantiel.
- Une vidéo de sport n'est PAS qualitative par le simple fait qu'elle appartient à `sport`. Inversement, une vraie compétition est acceptable même sans discours pédagogique. Prévoir cas ambigus, seuil de confiance et correction manuelle.

## Fonction essentielle : éviter un feed vide

A. **Filtrage du feed existant**
- Sur la page d'accueil YouTube, récupérer les cartes reconnues via content script et classer sans casser leur clic/miniature/titre. Observer les chargements dynamiques avec `MutationObserver` DÉBOUNCÉ, éviter classifications répétées et fuite mémoire. Garder la page réactive même si plusieurs dizaines de recommandations chargent.
- En mode « Favoriser », reclasser en priorité les vidéos pertinentes, mais ne pas forcément masquer toutes les autres. En mode « Uniquement », ne conserver parmi les propositions existantes que les catégories sélectionnées et compatibles avec les exclusions. Exclusions explicites > priorités thématiques ; la qualité est un filtre transversal.
- Bloquer les Shorts quand demandé, sans toucher au lecteur YouTube, aux pubs, aux contrôles de lecture ou aux données d'autres pages sans accord explicite.

B. **Découverte et réapprovisionnement V4 : indispensables**
- Créer un espace distinct et identifié **« Découvertes FeedControl »**, avec ses propres cartes cliquables ouvrant `https://www.youtube.com/watch?v=<videoId>`. Ce n'est PAS une recommandation native YouTube. Conserver titres/miniatures/métadonnées véridiques et leur attribution ; ne pas les modifier trompeusement.
- Si le nombre de recommandations compatibles est sous un seuil configurable (valeur initiale suggérée : 8), chercher des candidats SUPPLÉMENTAIRES selon les catégories favorisées, puis filtrer/reclasser par sujet, qualité et pertinence. Permettre un bouton « Explorer d'autres vidéos » ; prévoir un maximum de requêtes et un état « Aucun résultat correspondant trouvé ».
- Préférer une intégration serveur Python de **YouTube Data API v3** `search.list` pour la découverte, `videos.list`/`channels.list` pour les métadonnées si nécessaires, en RESPECTANT les quotas et les conditions applicables. Ajouter un cache TTL, une file de requêtes/batch, un plafond de résultats, la déduplication par `videoId`, gestion des erreurs API/réseau/quota, retry limité et annulation quand le contexte change. Ne fais PAS de scraping opaque d'API internes de YouTube, ni d'appel massif à une API à chaque mutation DOM.
- La clé API doit être conservée UNIQUEMENT côté serveur en variable d'environnement (`YOUTUBE_API_KEY`, `.env` dans `.gitignore`, `.env.example` sans secret). Si la clé est absente, la découverte doit rester désactivée proprement en affichant la configuration requise, sans inventer des résultats. Tests possibles avec fixtures en mode DEMO explicitement signalé.
- Afficher si possible au moins un mélange de catégories, plutôt que remplir tout le panneau d'un seul thème. Ne pas inventer de quota « garanti » de contenus satisfaisants : si l'API ne trouve rien, expliquer pourquoi et proposer de modifier les filtres, SANS réintroduire silencieusement les contenus explicitement bloqués.

C. **Petits créateurs qualitatifs**
- Interrupteur « Découvrir les petits créateurs » et seuil configurable d'abonnés (valeur indicative initiale : 50 000, modifiable).
- Quand les stats publiques existent, tenir compte du nombre d'abonnés ET du nombre de vues, du thème, de la qualité sémantique et de la diversité. Un petit nombre de vues n'implique PAS qualité, et une miniature moins travaillée ne doit pas pénaliser automatiquement. Si abonnés masqués ou absents, signal `unknown`, pas un faux 0.
- Prévoir un score de découverte équilibré, documenté ; une pénalité pour les vidéos déjà montrées récemment ; expliquer « Nouvelle chaîne — 3 200 abonnés » UNIQUEMENT lorsque l'API fournit véritablement cette information.

## Mode qualitatif et personnalisation fine

- Ajouter un curseur simple « Exigence de qualité » avec 3 valeurs : Souple / Équilibré / Strict. Modifie les seuils, pas seulement la couleur d'un bouton. Distinction forte entre catégorie et qualité.
- Pour les catégories favorites, supporter « favoriser » versus « uniquement » ; préserver la possibilité de bloquer explicitement d'autres catégories.
- Option « Pourquoi cette vidéo ? » sur les cartes contrôlées par FeedControl, avec raisons intelligibles et incertitude. Actions utilisateur « Pertinente » / « Pas pertinente » / « Mauvaise classification » sauvegardées localement ; utiliser ces retours pour ajuster le classement de façon explicable (pas de promesse de réentraînement instantané).
- En cas d'indisponibilité du classificateur, signaler clairement le mode dégradé. Mode Favoriser : ne pas masquer massivement des vidéos inconnues. Mode Uniquement : ne jamais prétendre que les vidéos inconnues ont été validées ; expliquer la limitation et montrer le statut de filtrage.

## Suivi et analytics REELS (pas de données fictives en production)

- Enregistrer localement, avec consentement/activation explicite, le **temps réellement regardé** sur une page vidéo/Short : éviter de compter une vidéo seulement ouverte, un onglet en arrière-plan, une vidéo en pause ou des secondes déjà comptées deux fois. Exploiter prudemment les événements de lecture, la visibilité de l'onglet et le delta du temps de lecture ; éviter doubles comptages. Cette métrique est une ESTIMATION locale, pas le YouTube Watch History officiel.
- Stockage limité/agrégé, configurable et effaçable, sans envoyer l'historique personnel à un service tiers. Par catégorie : nombre de vidéos vues et minutes regardées (attribuer par catégorie primaire, et documenter pour les vidéos multi-thèmes pour ne pas doubler les totaux), jour/semaine ; autres indicateurs : Shorts, contenus masqués, répartition favorisés/autres, évolution par période.
- La section **Suivi** reprend le panneau graphique de `ui_reference/feedcontrol-v2.html` (barres par catégorie, choix « Vidéos / Durée », couleurs identiques) et l'alimente par les vraies données `chrome.storage.local`. Afficher explicitement « Aucune donnée pour le moment » si vide. Le bouton DEMO, s'il est conservé, reste étiqueté et séparé.

## Architecture, performance, intégration

- Conserver l'architecture réelle du projet V3 autant que possible. Si approprié : `popup.html/css/js` pour UI ; `content.js` pour détecter/filtrer/insérer la zone Découvertes ; `background.js` ou service worker pour messages et stockage ; `ai_server.py` pour classification et API discovery ; modules partagés pour taxonomie, config, scoring, stats. Ajuste les noms à l'existant au lieu de recréer des doublons.
- Utiliser `chrome.storage.local` pour préférences et statistiques, migration propre depuis paramètres existants si présents ; ne pas utiliser `localStorage` de la maquette comme stockage de production. Respecter les autorisations Manifest V3 au minimum nécessaire, et les CSP/limitations d'extensions Chrome.
- Ne pas modifier le lecteur YouTube, ne pas bloquer les publicités et ne pas injecter de code distant. Respecter les règles d'API YouTube, notamment attribution et présentation correcte des miniatures/titres ; si une opération prévue est incompatible avec les règles, substitue une page/panneau FeedControl clairement identifié et explique l'écart.
- Cohérence catégories/id/couleurs/icons entre popup, IA, filtres, découverte et statistiques. Charger en lots et mettre les opérations coûteuses en cache ; pas de requête modèle à chaque scroll.
- Prévoir un mode dégradé propre si Python/clé API/connexion indisponibles : ne pas casser YouTube, signaler l'état des fonctions et fournir une action de correction.

## Tests d'acceptation obligatoires

Écris ou adapte des tests exécutables (Python unittest/pytest, tests JS/fixtures selon l'environnement), et teste réellement ce qui est testable hors navigateur ; documente la vérification manuelle Chrome. Au minimum :
- 20 vidéos YouTube fictives dont plusieurs `sport` (analyse tactique versus « funny moments »), `bricolage` et hors-sujet ; le classificateur ne doit pas confondre thème et qualité ; trace de scores/raisons.
- Zéro recommandation compatible dans le feed natif : l'espace FeedControl Découvertes cherche et affiche des candidats si l'API répond ; jamais d'affirmation de succès sans résultats ; interface informative en cas d'échec.
- Mode « Favoriser » et « Uniquement » donnent des comportements distincts ; exclusions toujours prioritaires ; Shorts désactivables.
- Petit créateur pertinent versus vidéo populaire hors sujet : le petit créateur doit être valorisé sans conclure qu'il est « bon » sur le seul nombre d'abonnés.
- Le changement de préférences dans le popup impacte vraiment le filtrage sur YouTube (pas une sélection graphique factice), persiste après fermeture, et synchronise la zone Découvertes.
- Navigation YouTube SPA, scroll infini, vidéos répétées, backend arrêté, clé API absente/quota épuisé, absence de métadonnées, stockage vide.
- Suivi : temps à l'arrêt = 0, onglet invisible = 0, lecture active = augmentation ; répartition et totaux cohérents ; bouton « Effacer mes statistiques » testé.
- Vérifier manifest/extension chargée, absence d'erreurs bloquantes console, styles popup, accessibilité minimale et fluidité. Si test automatique navigateur indisponible, fournir des étapes exactes dans `README_V4.md` et ne PAS inventer de succès.

## Ordre d'exécution et livrables

Procède par tranches testables, sans perdre le fil :
- Audit V3 / sauvegarde, puis intégration visuelle V2 dans le popup et stockage persistant.
- Classificateur étendu, logique bloquer/favoriser/uniquement, score qualité et cas sportifs.
- Découverte depuis YouTube Data API avec panneau autonome, classement/diversité/petits créateurs/cache.
- Tracking réel et panneau suivi par catégories ; explications/feedback ; tests de bout en bout.

À la fin, fournir : **code V4 modifié dans le projet existant**, `README_V4.md` en français (installation Windows/PowerShell, activation `.venv`, variables `.env`, lancement du serveur, chargement sur `chrome://extensions`, scénario de démo en 5 minutes), `.env.example`, tests et un fichier `CHANGELOG_V4.md` distinguant « opérationnel / partiel / non implémenté ». Ne marque jamais comme opérationnelle une fonction non connectée.

**Règle centrale : la V4 doit être une extension utilisable sur le vrai YouTube, pas uniquement une jolie maquette.** Commence maintenant par inspecter les fichiers présents puis implémente la V4, en réutilisant vraiment le design fourni.

## Documentation technique officielle (à consulter si nécessaire)

- https://developer.chrome.com/docs/extensions/develop/concepts/messaging
- https://developer.chrome.com/docs/extensions/reference/api/storage
- https://developers.google.com/youtube/data/reference/rest/v3/search/list
- https://developers.google.com/youtube/data/reference/rest/v3/channels/list
- https://developers.google.com/youtube/terms/developer-policies-guide
