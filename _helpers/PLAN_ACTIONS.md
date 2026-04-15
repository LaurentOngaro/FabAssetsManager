# Plan d'Action - FabAssetsManager

Ce document ordonne et détaille les étapes d'implémentation selon les définies dans le fichier `TODO.md`.

**REGLE D'OR : Toujours proposer d'effectuer les corrections de bugs et les corrections immédiates en premier. Elles sont listées dans les section "Corrections immédiates" et "Bugs" du fichier `TODO.md`.**

Chaque fois qu'une modification est teminée:

- dans ce document:
  - ajouter "DONE " en début du titre de la section correspondante (ex: `### 1. [FIL1] Sections de filtres collapsables` devient `### 1. DONE [FIL1] Sections de filtres collapsables`)
  - les sections terminées sont régulièrement effacées de ce document pour ne conserver que les tâches en cours ou à venir
- dans `TODO.md`:
  - cocher la case associée
  - supprimer la tache de la liste des Groupes
  - déplacer la tache au début de la section "Terminés" à la fin du fichier (ex: `### Terminés`)

## TOP Priorités (pour les corrections immédiates)

- Note: l'ordre d'implementation detaille est desormais porte par `TODO.md`; ce document regroupe les chantiers par theme et par nature de travail.

## Refactoring

### DONE [REF6] Durcissement des endpoints JSON

- Objectif: eviter les erreurs 500 sur payload JSON invalide.
- Actions:
  - remplacer les usages restants de `request.get_json()` non protege par `request.get_json(silent=True)`.
  - ajouter une validation explicite des champs obligatoires pour chaque endpoint concerne.
  - conserver les retours via `create_error_response` avec code metier adapte.
- Validation:
  - tests API sur payload vide, JSON malforme, champs manquants.

### DONE [REF8] Ajouter `error.path` aux reponses d'erreur

- Objectif: faciliter le diagnostic cote client et journalisation.
- Actions:
  - enrichir `AppError.to_dict()` avec le chemin de requete.
  - verifier la retro-compatibilite des clients existants.
  - mettre a jour `_helpers/error_response_contract.json`.
- Validation:
  - tests unitaires et API verifiant la presence de `error.path`.

### DONE [REF4] Cache memoire TTL backend

- Objectif: limiter les relectures disque repetitives des assets.
- Actions:
  - introduire un cache en memoire avec TTL configurable.
  - ajouter une invalidation explicite apres fetch/clear_cache et operations de mutation.
  - centraliser la lecture du cache via un service/fonction unique.
- Validation:
  - tests unitaires sur expiration TTL et invalidation.
  - verification de baisse du nombre d'appels disque sur endpoints frequents.

### DONE [REF7] Service de configuration unifie

- Objectif: fiabiliser le chargement des parametres de config.
- Actions:
  - ajouter des parseurs de types (bool/int) et des valeurs par defaut robustes.
  - valider les bornes minimales (port, tailles de logs, etc.).
  - centraliser lecture/ecriture config pour eviter la duplication.
- Validation:
  - tests sur configurations partielles ou invalides.

### [REF5] Pagination et filtrage server-side

- Objectif: eviter le chargement complet de toute la bibliotheque cote UI.
- Actions:
  - creer un endpoint pagine/filtre/sort (draw/start/length/search/order/filtres).
  - migrer progressivement le frontend vers ce mode.
  - conserver temporairement un mode de compatibilite.
- Validation:
  - non regression UX sur filtres, tri, pagination.
  - mesure de reduction de memoire cote navigateur.

## Filtrage

## Fonctionnalités (Export)

### DONE [FEAT9] Export headless pour scripts locaux

- Objectif: permettre l'export vers un fichier local sans telechargement navigateur.
- Actions:
  - creer endpoint POST avec `output_path` ou `output_dir` + `file_name`.
  - reutiliser la logique d'export existante (json/csv).
  - gerer la validation et securisation de chemin.
- Validation:
  - tests sur succes d'ecriture, dossiers manquants, chemins invalides.

## Maintenance, Tableaux et Caches

### DONE [GE4] Endpoint de diagnostic backend

- Objectif: verifier rapidement l'etat de configuration et de stockage.
- Actions:
  - ajouter endpoint de test backend (cookies/user-agent, acces assets/previews, metadata cache).
  - retourner un statut detaille avec hints de remediation.
  - exposer ce diagnostic dans la zone de maintenance UI (optionnel en phase 2).
- Validation:
  - endpoint retourne un rapport exploitable sans effectuer de fetch vers Fab.

## Améliorations de l'UX (Pagination)

## Fonctionnalités de marquage utilisateur (Local Data)

## Etudes (Hors-Périmètre/Long-Terme)

### [IDEA2] mis de côté

- **Décision :** repoussé volontairement, car moins utile à court terme que FEAT3 et FEAT5.
- **Remarque :** à réévaluer seulement après mise en place d'une base commune pour les données utilisateur.

### [IDEA1] Recherche globale (Bibliothèque Fab complète)

- **Verdict :** Priorité la plus basse (très gourmand, API complexe hors-catalogue personnel).
