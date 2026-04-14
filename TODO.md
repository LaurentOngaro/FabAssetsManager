# TODOs

## Bugs (last: BUG3)

## Corrections immédiates (last:CI14)

## Améliorations du projet

Pour plus de détails sur l'implémentation de ces modifications, consulter le fichier `_helpers\PLAN_ACTIONS.md` qui détaille les étapes à suivre pour chaque tâche.

### Priorités d'implémentation

classement des demandes par priorité de la plus urgente à la moins urgente:

- FEAT3
- FEAT5
- FEAT4
- IDEA1

### documentation (last: DOC1)

### filtrage (last: FIL2)

### pagination (last: PAG2)

### gestion (last: GE3)

### refactoring (last: REF3)

### affichage (last: AFF5)

### features (last: FEAT8)

- [ ] FEAT4: ajouter un système de tags personnalisés pour classer les assets (ex: "à tester", "inspirant", "à acheter", etc.)

### idées à creuser (last: IDEA1)

- [ ] IDEA1: rechercher/filtrer des assets (et afficher) parmis la totalité de la bibliothèque FAB (et pas seulement ceux qui sont posssédés) . Attention au volume de données à gérer et à afficher !!!

## Terminés

- [x] FEAT5: ajouter un system de commentaires locaux pour chaque asset (ex: "ne fonctionne pas avec UE5.3", "super pour les jeux 2D", etc.)
- [x] FEAT3: ajouter un système de favoris pour marquer les assets préférés
- [x] FEAT6: utiliser des profils d'exportation de données
- [x] FEAT7: externaliser le css dans static/css/style.css
- [x] FEAT8: externaliser le js dans static/js/app.js

- [x] GE3: ajouter une zone avec des action de maintenance en bas de la colonne de gauche
  - [x] GE1: ajouter un bouton pour effacer les preview téléchargé localement
  - [x] GE2: ajouter un bouton pour effacer le cache (avec avertissement pour éviter les suppressions accidentelles)
- [x] PAG1: choisir le nombre d'assets affichés par page (20, 50, 100)
- [x] PAG2: remplacer la liste des pages par une combobox (plus lisible)
- [x] FIL2: ajouter une zone de recherche pour le filtre sellers pour faciliter la navigation dans la liste des sellers (et éviter d'avoir à faire défiler toute la liste quand elle est longue)
- [x] REF2: déplacer les constantes de configuration présentes dans `app.py` dans le fichier de configuration dédié (cf CONFIG_FILE)
- [x] CI14: renommer `config/settings.json` en `config/config.json`
- [x] CI13: renommer le projet en "FabAssetsManager" pour mieux refléter sa fonction et normaliser son nom.
- [x] CI12: quand aucun asset n'est sélectionné, le bouton "Get details" doit faire un fetch pour récupérer les détails des assets affichés/filtrés (et non de la totalité des assets)
- [x] AFF3: customiser l'ordre d'affichage des colonnes
- [x] AFF4: dans la fenetre de preview, ajouter des boutons << et >> pour naviguer entre les MEDIAS de l'asset (nécessite FEAT2 pour que `listing.medias` soit disponible)
  - l'affichage de cette fenetre doit été précédée d'une demande des détails de l'asset (FEAT2) pour que `listing.medias` soit disponible et puisse être utilisé pour afficher les différentes images de la galerie (et pas seulement le thumbnail principal)
  - actuellement un seul média est affiché (thumbnail), il faut extraire les médias supplémentaires
- [x] AFF5: permettre de trier les assets par format, type et seller
- [x] DOC1: standardisation de la documentation API (OpenAPI 3.1 + API_GUIDE.md) et nettoyage des fichiers obsolètes (HOW_TO.md, HOW_TO_ERRORS.md)
- [x] REF3: Système d'erreurs standardisées pour toutes les routes API et fonctions internes via le nouveau fichier `errors.py`.
- [x] REF1: créer une classe Asset pour centraliser le mapping des données des assets (liste + détails), et faire basculer le backend pour l'utiliser au maximum.
- [x] FEAT1: mémoriser la date de mise à jour du cache (si ce n'est pas déjà fait)
- [x] CI12: ajouter le UID (ex "001d83fe-9594-42c5-a93e-3b277f74863d") dans l'export CSV pour faciliter le mapping avec les fichiers de cache individuels (`assets/<uid>.json`) et éviter les confusions en cas de titres d'assets similaires ou identiques.
- [x] BUG3:j'ai activé le niveau "debug" dans le log, mais app.log ne contient aucun "DEBUG". est ce un bug ? dans ce niveau de débug, je voudrai logguer TOUS les appels aux fonctions "app.route\*"
- [x] BUG2: sauvegarde et restauration des options de logs via `config/config.json` (log level, log output, debug mode)
- [x] CI7 (redo): correction du merge backend `/api/details`, revalidation des assets incomplets (`details_fetched`), et enrichissement effectif de la modale avec fallback de refetch
- [x] BUG1: un clic sur "Get new assets" affiche désormais un message "No new assets available" au lieu d'une erreur quand il n'y a pas de nouveaux assets
- [x] CI11: amélioration du bouton "Get Details" avec sélection d'assets, bouton "Stop Scraping", et requêtes AJAX
- [x] CI10: modifier le fichier cache_manager.py pour utiliser les constantes ASSETS_DIR et LAST_UPDATE_FILE du fichiers app.py
- [x] CI9: ajouter un système de logging pour suivre les actions de l'utilisateur et les erreurs (ex: lors de la récupération d'un asset, lors de l'affichage des détails, etc.) pour faciliter le debug et le suivi de l'utilisation de l'application
- [x] CI8: placer le bouton "See details" à gauche du bouton "Get details" (en haut) et non dans la colonne "fab url"
- [x] CI0: modifier l'ordre des colonne par défaut et mettre les colonne suivantes en premier: title, type, seller, format
- [x] CI1: rendre les colonnes title et seller obligatoire (cad non décochable dans la liste des colonnes à afficher) pour éviter les affichages vides (ex: si on décoche title, on n'a plus que des miniatures sans titre et c'est très confus)
- [x] CI2: utiliser le clic sur le titre pour ouvrir la modale de détail (AFF1)
- [x] CI3: ajouter un bouton "See details" (a gauche de "Get details") pour ouvrir la modale de détail (AFF1)
- [x] CI4: ajouter les filtres suivants pour faciliter la navigation dans la bibliothèque d'assets (priorité haute) :
  - seller
  - format
  - type (3D model, texture, audio, etc.)
  - discounted
- [x] CI5: mémoriser les filtres appliqués et les appliquer au rechargement de l'application ou de la page (actuellement la sélection est perdue à chaque rafraichissement)
- [x] CI6: utiliser le clic sur les éléments des filtres pour les activer (ex: cliquer sur un seller dans la liste des sellers pour activer le filtre avec ce seller sélectionné) pour faciliter la navigation
  - utiliser le clic sur le seller pour activer le filtre avec le seller sélectionné
  - utiliser le clic sur le format pour activer le filtre avec le format sélectionné
  - utiliser le clic sur le type pour activer le filtre avec le type sélectionné
- [x] FIL1: rendre les sections de la colonne de gauche (cad les filtres) colapsable pour reduire la hauteur de la zone
- [x] AFF1: proposer une fenetre modale d'info détaillée pour chaque asset
- [x] AFF2: proposer de customiser les colonne affichées
- [x] FEAT2: télécharger le détail de chaque asset par batch
  - [x] utilise le fichier json créé pour chaque asset dans la vue liste pour enregistrer les infos
    - [x] completer avec les informations manquantes disponible dans le détail pour éviter de faire une requete à chaque fois
  - [x] MEMORISER LA DATE DE DERNIERE MISE A JOUR (du cache et du détails des assets) pour ne faire une requete que si le cache est obsolète ou incomplet (détails pas encore ajoutés)
  - [x] vérifier si les infos ne sont pas déjà présentes dans le cache avant de faire la requete (et vérifier la date de mise à jour du cache pour éviter de faire des requetes inutiles)
  - [x] le faire automatiquement pour chaque asset consulté dans la liste
  - [x] ajouter une option pour le faire automatiquement pour tous les nouveaux assets disponibles (cf FEAT6)
  - [x] proposer de le faire par batch en tache de fond (définir une taille de batch et la périodicité du lancement à configurer dans les options)
