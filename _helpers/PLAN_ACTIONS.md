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
