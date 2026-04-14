# Plan d'Action - FabAssetsManager

Ce document ordonne et détaille les étapes d'implémentation selon les Groupes définies dans le fichier `TODO.md`.

**REGLE D'OR : Toujours proposer d'effectuer les corrections de bugs et les corrections immédiates en premier. Elles sont listées dans les section "Corrections immédiates" et "Bugs" du fichier `TODO.md`.**

Chaque fois qu'une modification est teminée:

- dans ce document: ajouter "DONE " en début du titre de la section correspondante (ex: `### 1. [FIL1] Sections de filtres collapsables` devient `### 1. DONE [FIL1] Sections de filtres collapsables`)
- dans `TODO.md`:
  - cocher la case associée
  - supprimer la tache de la liste des Groupes
  - déplacer la tache au début de la section "Terminés" à la fin du fichier (ex: `### Terminés`)

## TOP Priorités (pour les corrections immédiates)

## Groupe Refactoring

## Groupe Filtrage

## Groupe Fonctionnalités (Export)

## Groupe 6 : Maintenance, Tableaux et Caches

## Groupe 7 : Améliorations de l'UX (Pagination)

## Groupe 8 : Fonctionnalités de marquage utilisateur (Local Data)

_Note : Ces données devront être stockées localement en parallèle du cache de base de l'API (ex: via un fichier JSON séparé `userdata.json` ou localStorage), afin qu'elles survivent à un `Clear Cache` (CA2) ou à une mise à jour d'asset (FEAT2)._

### DONE [FEAT3] Système de Favoris

- **Objectif :** Permettre de repérer rapidement les assets à garder sous la main.
- **Actions :**
  - Ajouter une icône étoile cliquable dans la grille et/ou dans la modale de détail.
  - Stocker l'état favori localement par UID dans un fichier userdata ou localStorage.
  - Réafficher l'état au rechargement et lors des changements de filtre / pagination.
  - Prévoir une logique de compatibilité avec les exports et les mises à jour de cache.

### FEAT4 mis de côté

- **Décision :** repoussé volontairement, car moins utile à court terme que FEAT3 et FEAT5.
- **Remarque :** à réévaluer seulement après mise en place d'une base commune pour les données utilisateur.

### DONE [FEAT5] Commentaires locaux

- **Objectif :** Permettre de conserver des notes personnelles par asset.
- **Actions :**
  - Ajouter un champ `textarea` dans la modale de détail ou dans une zone dédiée.
  - Sauvegarder le commentaire localement par UID.
  - Afficher un indicateur visuel quand un asset possède déjà une note.
  - Prévoir une lecture/écriture robuste avec le même stockage que FEAT3.

## Groupe 9 : Etudes (Hors-Périmètre/Long-Terme)

### [IDEA1] Recherche globale (Bibliothèque Fab complète)

- **Verdict :** Priorité la plus basse (très gourmand, API complexe hors-catalogue personnel).
