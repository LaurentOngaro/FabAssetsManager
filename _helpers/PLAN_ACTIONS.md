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

### [FEAT3] Système de Favoris

- **Actions :** Étoile cliquable dans la grille ; sauvegarde d'un Array d'UID.

### [FEAT4] Tags personnalisés

- **Actions :** Modale ou input texte au sein de l'[AFF1] permettant la persistance de mots-clés.

### [FEAT5] Commentaires locaux

- **Actions :** Champ `textarea` libre sauvegardé par UID.

## Groupe 9 : Etudes (Hors-Périmètre/Long-Terme)

### [IDEA1] Recherche globale (Bibliothèque Fab complète)

- **Verdict :** Priorité la plus basse (très gourmand, API complexe hors-catalogue personnel).
