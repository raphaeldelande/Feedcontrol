# FeedControl V4 — état vérifié

## Opérationnel dans les tests exécutés

- Base V3 importée, sauvegardée dans `legacy_v3/` et prolongée, branche `feedcontrol-v4`. Aucun envoi GitHub effectué.
- Popup sombre 400 px, trois panneaux dépliables, 16 thèmes, SVG/couleurs cohérents, options persistantes, migration V3, exclusions prioritaires, Favoriser/Uniquement, trois seuils qualité, configuration découverte/petits créateurs/suivi.
- Règles texte FR/EN séparant thème, type, score qualité, confiance et raisons. 24 titres fictifs, dont analyses sportives, matchs, compilations et bricolage.
- Serveur Python standard `127.0.0.1:8765` ; `/`, `/classify`, `/discover`. Classification et messages d’erreur réellement testés en HTTP ; démarrage effectué sans modèle ni clé.
- Content script : filtres sur l’accueil, observation débouncée, borne de concurrence/cache, réception de préférences, nettoyage SPA, panneaux indépendants, retours et explications.
- Découverte officielle : recherches par thèmes, cache TTL, plafond horaire, déduplication, métadonnées vidéos/chaînes groupées, inconnues conservées comme inconnues, aucune vidéo inventée. Transport API testé avec fixtures, y compris absence de résultat, clé absente, refus/quota et cache.
- Score pertinent/petite chaîne, diversification, pénalité d’exposition, retours locaux sans réentraînement.
- Suivi avec accord explicite : delta de lecture, état de visibilité/pause/recherche, agrégats par jour et catégorie primaire, stockage borné, historique 7/30/90 jours, barres Vidéos/Durée, répartition favoris/autres, effacement. Consentement et totaux concurrents testés dans le vrai code du service worker avec API stockage simulée.
- Démo hors ligne clairement marquée DEMO et séparée des préférences/statistiques réelles.

## Résultats des commandes

- `npm test` : **32 tests réussis**, zéro échec, dont 24 titres avec scores/raisons.
- `python -m unittest discover -s tests -v` : **6 tests réussis**, zéro échec ; le test des fixtures couvre aussi les 24 titres.
- `python tests/browser_smoke.py` : **réussi dans Chromium**, vrai HTML/CSS/JS, API Chrome et pages YouTube simulées : persistance, propagation entre pages, filtres qualitatifs/exclusifs, DOM dynamique, zéro candidat natif et découverte DEMO, clé absente, feedback, nettoyage SPA, affichage/effacement des statistiques, largeur 400 px, aucune erreur JS de page détectée. Le chronométrage du lecteur est testé comme fonction pure, pas sur une vidéo YouTube réelle.
- `python tests/extension_smoke.py` : **bloqué** au chargement de l’extension par la politique système Chromium (`ExtensionInstallBlocklist: ["*"]`). Aucun succès de chargement MV3 revendiqué. Téléchargement du navigateur Playwright alternatif refusé par le proxy (`cdn.playwright.dev`, HTTP 403). Les restrictions n’ont pas été modifiées.

## Partiel / à valider sur votre machine

- Extension conçue pour le vrai YouTube mais **pas validée sur le site réel**. Liste manuelle dans README_V4.md : SPA/scroll, DOM actuel, performance, clavier, Shorts, annonces et lecteur.
- API YouTube réelle : clé absente dans cet environnement. Endpoint et intégration testés avec fixtures, pas de réponse Google authentifiée vérifiée. Ajouter la clé uniquement au Python local et tester.
- Classement natif par CSS order : fonctionne selon la disposition flex/grid de YouTube, sans altérer les liens ; la stabilité sur toutes variantes de l’accueil n’est pas garantie.
- Le modèle multilingue V3 est réutilisable avec `FEEDCONTROL_SEMANTIC=1`, mais dépendance/modèle non installés ni exécutés ici. Mode par défaut : heuristique texte explicitement annoncé, sans vision. Même avec le modèle, la qualité reste heuristique.
- Format Shorts des découvertes : API insuffisante pour l’identifier exactement ; l’option d’exclusion retire prudemment les durées ≤3 min et inconnues. Peut écarter de courtes vidéos classiques.
- Le bouton Explorer tourne dans le pool en cache durant 15 minutes ; ne promet pas de candidats supplémentaires si le pool est épuisé. Les réponses obsolètes sont ignorées côté extension ; une requête Google déjà partie n’est pas annulée côté serveur.
- Suivi estimé, perte possible des dernières secondes à la fermeture, détection publicitaire dépendante du DOM. Catégorie primaire par titre, pas historique officiel. Évolution disponible par sélection de période ; pas encore de courbe quotidienne comparative.
- Le nombre de vues est fourni et conservé, mais ne contribue pas encore à un score de découverte distinct ; il ne donne aucun bonus automatique de qualité.

## Non implémenté

- Reproduction exacte de `ui_reference/feedcontrol-v2.html` et de son icône Sport : fichier non joint. Nouveau design selon le texte, avec coureur SVG.
- Analyse des miniatures/vidéos, certification de qualité, modification de l’algorithme YouTube.
- Réentraînement à partir des retours, éditeur de corrections manuelles de thèmes, analyse de sous-titres.
- Graphique longitudinal comparant deux périodes, suivi synchronisé multiappareil, publication Chrome Web Store.
