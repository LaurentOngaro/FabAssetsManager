# PLAN D'ACTIONS

Ce document détaille (et décrits les étapes d'implémentation) de certaines des taches présentes dans le fichier `TODO.md`.
Un regroupement par Sprints peut être envisagé dans ce document, selon le nombre de tâches à implémenter.
La priorisation des tâches est définie dans `TODO.md` et doit être respectée pour éviter de se disperser sur des points moins urgents.

## Contexte et Lignes Directrices (Héritées du plan de migration)

- **Séparation des rôles** : Garder une séparation claire entre l'outil applicatif (`FABAssetsManager`) et le pipeline de curation (`_Helpers/04_Assets/AssetsCuration/`).

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

## Refactoring

## Filtrage

## Fonctionnalités (Export)

## Maintenance, Tableaux et Caches

## Améliorations de l'UX (Pagination)

## Fonctionnalités de marquage utilisateur (Local Data)

## Etudes (Hors-Périmètre/Long-Terme)

### [IDEA2] mis de côté

- **Décision :** repoussé volontairement, car moins utile à court terme que FEAT3 et FEAT5.
- **Remarque :** à réévaluer seulement après mise en place d'une base commune pour les données utilisateur.

### [IDEA1] Recherche globale (Bibliothèque Fab complète)

- **Verdict :** Priorité la plus basse (très gourmand, API complexe hors-catalogue personnel).

### [IDEA3] Utilisation de Bootstrap pour les pages statiques

Utiliser bootstrap plutot que du vanilla pour les pages statiques

- Pour:
  - Uniformisation avec UnityAssetsManager (Flask + Bootstrap + DataTables)
  - Mutualisation du code entre les 2 applis (ex: même template de base, même style de boutons, etc.)
  - Évolutivité : Si vous prévoyez d'ajouter à FAM des fonctionnalités complexes (tableaux de données denses, popups de confirmation, menus déroulants complexes), Bootstrap vous fera gagner un temps précieux.
  - Indispensable si ajout de datatables (pandas) dans le futur (filtrage avancé, pagination, etc.)
- Contre:
  - Le coût du refactoring : Remplacer du Vanilla par du Bootstrap demande de réécrire une grande partie du HTML (pour ajouter les classes spécifiques comme container, row, col, btn, etc.) et de nettoyer le CSS Vanilla existant pour éviter les conflits
