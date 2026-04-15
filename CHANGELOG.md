# Changelog

Version: 0.13.7

## [0.13.7] - 2026-04-15

### Changed

- Extraction de la configuration du logging dans un module dédié `logging_setup.py`.
- Standardisation des clés de configuration du logging dans `config/config.json` pour correspondre à la structure de UnityAssetsManager.
- Mise à jour de `config_manager.py` pour valider et normaliser les paramètres de log (passage à `"both"` en minuscules).
- Correction d'erreurs de type et d'imports manquants dans `app.py`.

## [0.13.6] - 2026-04-15

### Changed

- **[REF5]** Added server-side query endpoint (`/api/assets/query`) with filtering, sorting, pagination and facets; frontend now uses this mode by default with legacy fallback for local-only filters.
- API guide now describes `/api/cache-info` with its actual synchronization metadata fields.
- Added backend tests for `/api/assets/query` edge cases: non-object payload rejection, page clamping, and `include_all_items` behavior.

## [0.13.5] - 2026-04-15

### Added

- New dedicated backend routes module `routes.py` for all web/API endpoints.
- **[GE4]** New backend diagnostic endpoint `/api/diagnostic` to validate local preconditions (auth/config/storage/cache) without Fab.com fetch.
- **[FEAT9]** New headless export endpoint `/api/export/headless` to write JSON/CSV exports directly to disk.
- New centralized configuration service module `config_manager.py`.

### Changed

- Aligned `_helpers/bumpImportantVersion.py` with the UnityAssetsManager helper: repo-local JSON configuration, recursive version-tag scan, and synchronized version-tag updates.
- Refactored `app.py` to focus on startup/configuration concerns and route telemetry hooks.
- Registered Flask routes through a blueprint (`main_bp`) to align backend structure with UnityAssetsManager.
- Preserved route behavior and test monkeypatch compatibility by resolving runtime dependencies via the `app` module inside the new routes blueprint.
- **[REF6]** Hardened JSON route parsing with `request.get_json(silent=True)` on POST endpoints handling JSON payloads.
- **[REF7]** Centralized configuration loading/validation (defaults, int parsing, bounds checks) through `config_manager.py`.
- **[REF8]** Standardized API errors now include `error.path` (request endpoint path).
- **[REF4]** Added backend in-memory TTL cache for `load_all_assets()` to reduce repeated disk reads.

## [0.13.4] - 2026-04-15

### Added

- Normalized project headers across core source files and versioned documentation.

### Changed

- Expanded version tracking to include the frontend stylesheet and the version helper itself.
- Broadened `IMPORTANT_FILES` so the version bump helper watches the core backend, frontend, docs, and tests.

## [0.13.3] - 2026-04-14

### Added

- **[FEAT3]** Système de favoris local: étoile cliquable dans la grille et bouton dédié dans la modale de détail.
- **[FEAT5]** Commentaires locaux par asset: champ de note dans la modale avec sauvegarde locale par UID.

### Changed

- Ajout d'un indicateur visuel en liste lorsqu'un asset possède une note locale.
- Persistance des annotations utilisateur (favoris/commentaires) dans le localStorage, indépendante du cache backend (`assets/*.json`).
- Ajout d'un bouton `Clean note` dans la modale de détail pour effacer rapidement la note locale de l'asset courant.

## [0.13.2] - 2026-04-14

### Fixed

- Correction de la modale `Custom Export` qui ne s'affichait pas malgré le clic sur le bouton.
- Stabilisation du flux de chargement des profils d'export depuis `/api/export-templates`.

### Changed

- Détection automatique de l'extension de fichier d'export personnalisé selon le profil sélectionné (`.csv`, `.md`, `.txt`).
- Journalisation explicite côté backend lors des appels à `/api/export-templates` pour faciliter le diagnostic.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.1]

### ✨ Ajouté

- [FEAT6] Profils d'exportation de données customisables via \config/export_templates.json\ avec un nouveau point d'entrée d'API \/api/export-templates\ et une modale d'export personnalisée.

### ♻️ Refactoring

- [FEAT7] Externalisation du code CSS depuis \static/index.html\ vers \static/css/style.css\.
- [FEAT8] Externalisation du code JavaScript depuis \static/index.html\ vers \static/js/app.js\.

## [0.12.2] - 2026-04-14

### Added

- **[PAG1, PAG2]** Amélioration de la pagination : choix du nombre d'assets par page (20, 50, 100) et menu déroulant pour la sélection de page.
- **[GE3, GE1, GE2]** Ajout d'une zone d'actions de maintenance pour effacer les prévisualisations (`/api/clear_previews`) et vider le cache local (`/api/clear_cache`).

## [0.12.1] - 2026-04-14

### Added

- **[FIL2]** Ajout d'une zone de recherche pour le filtre des vendeurs (Sellers) afin de faciliter la navigation.

## [0.12.0] - 2026-04-14

### Added

- **[AFF5]** Ajout de la possibilité de trier les assets par format, type et vendeur.
- **[AFF4]** Dans la fenêtre de preview, ajout de boutons << et >> pour naviguer entre les médias d'un asset (utilise `listing.medias` extrait via les détails de l'asset).
- **[AFF3]** Possibilité de personnaliser l'ordre d'affichage des colonnes de la liste par simple glisser-déposer (Drag & Drop) depuis le panneau de filtrage.

## [0.11.0] - 2026-04-13

### Added

- **[REF3]** Système d'erreurs standardisées pour toutes les routes API et fonctions internes via le nouveau fichier `errors.py`.
- Énumération `ErrorCode` et classe `AppError` pour créer des réponses d'erreur cohérentes avec structure unifiée: `code`, `message`, `http_status`, `timestamp`, `details`.
- Fonction helper `create_error_response()` pour retourner un tuple `(response_dict, http_status)` compatible Flask.
- Contrat d'API formel pour les réponses d'erreur en JSON Schema draft 2020-12 (`_helpers/error_response_contract.json`).
- Guide complet d'exploitation des erreurs: [HOW_TO_ERRORS.md](HOW_TO_ERRORS.md) avec exemples de codes, scénarios d'erreur et intégration client.
- 14 codes d'erreur standardisés couvrant les cas courants: authentification, ressource non trouvée, problèmes de connexion, erreurs de cache, timeouts, etc.

### Changed

- Tous les endpoints API (`/api/lookup`, `/api/details/<uid>`, `/api/config`, `/api/fetch`, `/api/export/*`, `/api/image/<uid>`) retournent désormais des erreurs standardisées via `create_error_response()`.
- Les messages d'erreur incluent maintenant des `details` avec contexte spécifique: UIDs recherchés, paramètres attendus, hints de résolution, etc.
- Réponses d'erreur contiennent un champ `timestamp` ISO 8601 UTC pour l'audit et le débogage.

## [0.10.0] - 2026-04-13

### Added

- **[REF1]** Ajout d'une classe `Asset` (dataclass) dans `models.py` pour centraliser le mapping des données brutes Fab (liste + détails) vers le format plat utilisé par l'UI et les exports.
- Ajout de méthodes dédiées dans `Asset` pour normaliser et fusionner les payloads de détail (`extract_detail_listing`, `merge_detail_payload`).
- Endpoint local `/api/lookup` permettant de retrouver un asset du cache par `uid`, `name` ou `url` Fab.
- Nouveau guide d’exploitation [HOW_TO.md](HOW_TO.md) avec exemples de requêtes et usage Terrabloom.

### Changed

- Le backend utilise désormais `Asset(...).to_dict()` au lieu de `flatten_asset()` dans les endpoints principaux (`/api/assets`, `/api/details/<uid>`, exports CSV/JSON, image preview) et dans le script CLI d'export CSV.
- Suppression de la fonction legacy `flatten_asset` de `fetch_fab_library.py` au profit du modèle centralisé.
- Documentation: ajout du contrat JSON Schema complet de sortie des assets aplatis dans `_helpers/asset_output_schema_full.json`.

## [0.8.0] - 2026-04-13

### Added

- **[CI12]** Les exports CSV incluent désormais toujours la colonne `uid` en première position pour faciliter le mapping avec les fichiers `assets/<uid>.json`.
- **[FEAT1]** La date de dernière synchronisation du cache est affichée dans l’interface via un badge dédié, alimenté par `/api/cache-info`.

### Changed

- `/api/cache-info` expose maintenant `last_sync_at` et `last_sync_label` en plus des métriques de cache existantes.
- L’interface recharge automatiquement l’horodatage du cache après un chargement ou un rafraîchissement.

## [0.7.3] - 2026-04-13

### Fixed

- **[BUG2]** Les appels aux routes Flask sont désormais journalisés en DEBUG dans `app.log` avec méthode, endpoint, chemin, arguments et statut de réponse.

### Changed

- Ajout de hooks Flask `before_request` / `after_request` pour tracer systématiquement les routes de l'application.

## [0.7.2] - 2026-04-13

### Fixed

- **[BUG2]** Les options de log sont désormais sauvegardées dans `config/config.json` et restaurées au lancement: `log level`, `log output` et `debug mode`.
- **[BUG2]** Le backend reconfigure le logger immédiatement lorsque l'utilisateur modifie les options, pour que le changement soit effectif sans redémarrage.

### Changed

- `/api/config` expose maintenant les paramètres de logging persistés pour permettre la restauration côté UI.

## [0.7.1] - 2026-04-13

### Fixed

- **[CI7 hotfix]** Correction du merge backend dans `/api/details/<uid>` : la réponse de détail Fab est désormais correctement fusionnée même quand le payload est un objet `listing` direct (et non `{listing: {...}}`).
- **[CI7 hotfix]** Réparation des faux positifs `details_fetched=true` : les assets marqués "détaillés" mais incomplets sont à nouveau considérés comme manquants par `/api/missing_details` et peuvent être enrichis correctement.
- **[CI7 hotfix]** La modale force un refetch des détails quand le cache local est incomplet (même si `details_fetched=true`) pour garantir l'affichage des informations enrichies.

### Security

- Sanitation HTML côté frontend pour le rendu de `description` et `technical_specs` dans la modale afin de réduire les risques d'injection de contenu non sûr.

### Changed

- Correction de la galerie modale : l'asset courant est désormais résolu par `uid` (au lieu du titre), évitant les collisions quand plusieurs assets partagent le même nom.

## [0.7.0] - 2026-04-13

### Fixed

- **[BUG1]** Le bouton "Get New Assets" affiche désormais un message informatif "No new assets — your library is up to date!" au lieu d'une erreur 403 quand il n'y a pas de nouveaux assets en ligne.

### Changed

- **[CI7]** Enrichissement significatif de la modale de détails d'asset :
  - Chargement automatique (lazy loading) des détails depuis l'API lors de l'ouverture de la modale si les détails n'ont pas encore été récupérés.
  - Affichage du seller avec avatar, du prix, de la date de mise à jour, du nombre de reviews.
  - Nouvelle section "Technical Specs" affichant les spécifications techniques HTML détaillées.
  - Nouvelle section "Gallery" avec vignettes cliquables des médias de l'asset.
  - Indicateur de chargement pendant la récupération des détails.
  - Correction du merge des données détaillées dans le cache (extraction correcte de `listing` depuis la réponse de l'API de détail).
- **[CI11]** Amélioration du bouton "Get Details" :
  - Si des assets sont cochés, seuls ceux-ci sont enrichis (au lieu du batch complet).
  - Ajout d'un bouton "Stop Scraping" pour interrompre le processus en cours.
  - Utilisation d'`AbortController` pour annuler les requêtes AJAX proprement.
  - Le bouton "Get Details" est masqué pendant le scraping et remplacé par "Stop Scraping".

### Added

- Nouveaux champs extraits dans `flatten_asset` : `seller_avatar_url`, `technical_specs`, `media_urls`, `review_count`.
- Support du paramètre `uids` dans l'endpoint `/api/missing_details` pour vérifier uniquement des UIDs spécifiques.

## [0.6.0] - 2026-04-13

### Added

- **[AFF1/CI2/CI3]** Ajout d'une modale d'information détaillée de l'asset (Asset Details Modal). Elle s'ouvre en cliquant sur le titre de l'asset ou via le bouton "See details".
- **[CI9]** Ajout d'un système de logging configurable depuis l'interface (niveau et sortie console/fichier) pour tracer les requêtes REST et faciliter le debug.
- **[CI4]** Ajout de filtres rapides supplémentaires dans le panneau latéral : par Vendeur (Seller), par Format (Format), par Type (Listing Type) et option de filtrage pour les articles "Discounted".
- **[CI5]** Mémorisation (LocalStorage) des filtres sélectionnés pour les conserver au rechargement de la page.
- **[CI6]** Navigation rapide contextuelle : il est maintenant possible de cliquer sur les tags (Vendeur, Format, Type) directement dans la liste ou dans la modale de détails pour activer le filtre correspondant.

### Changed

- **[CI0]** Modification de l'ordre d'affichage par défaut des colonnes (Title, Type, Seller, Formats en premier).
- **[CI8]** Déplacement du bouton "See details" de la colonne du tableau vers la barre d'outils supérieure pour une meilleure ergonomie (activé lorsqu'un seul élément est sélectionné).
- **[CI10]** Résolution des imports de constantes de configuration entre `cache_manager.py` et `app.py` sans dépendance circulaire.
- **[CI1]** Les colonnes "Title" et "Seller" sont devenues obligatoires et ne peuvent plus être décochées pour éviter un tableau cassé.

## [0.5.2] - 2026-04-13

### Added

- Ajout de la suite de tests unitaires (pytest) :
  - `tests/test_cache.py` : Validation du cache local et des métadonnées (fichiers JSON par asset).
  - `tests/test_api.py` : Validation des endpoints du serveur Flask (`/api/test`, `/api/status`, `/api/assets`).
  - `tests/test_parser.py` : Validation de l'aplatissement des données de l'API (`flatten_asset`).

## [0.5.1] - 2026-04-13

### Changed

- Déplacement des fichiers de configuration `cookies.txt` et `user_agent.txt` dans le sous-dossier `config/`.
- Renommage de `VERSION` en `VERSION.txt` pour éviter des conflits avec l'extension C++ dans VS Code.
- Déplacement des fichiers de configuration vers un répertoire dédié

## [0.5.0] - 2026-04-13

### Added

- Mise en place de l'architecture du projet FabAssetsManager.
- Serveur Flask local avec interface Vanilla JS.
- Mémorisation des cookies et de l'User-Agent pour le contournement Cloudflare.
- Synchronisation complète et partielle avec l'API fab.com.
- Base de données locale par fichier JSON (`assets/<uid>.json`).
- Tri, recherche et filtrage des assets (par version UE, par licence, etc.).
- Fonctionnalité de sélection et d'export en CSV et JSON.
- **[FEAT2]** Téléchargement par batch et enrichissement des détails depuis l'API de détails (`/i/listings/<uid>`).

### Changed

- Refactorisation de l'affichage avec des filtres repliables **[FIL1]**.
