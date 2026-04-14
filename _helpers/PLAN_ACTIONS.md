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

### DONE [FEAT7] Externaliser le CSS

- CSS déplacé dans static/css/style.css

### DONE [FEAT8] Externaliser le JS

- JS déplacé dans static/js/app.js

## Groupe Filtrage

### DONE [FIL2] Recherche pour le filtre des vendeurs (Sellers)

- **Objectif :** Faciliter la navigation quand la liste de vendeurs est longue.
- **Actions :**
  - Ajouter un champ `<input type="text">` au-dessus de la liste des sellers dans la colonne de gauche.
  - Ajouter un event listener JS pour filtrer/masquer dynamiquement les éléments de la liste qui ne correspondent pas au texte saisi.

## Groupe Fonctionnalités (Export)

### DONE [FEAT6] Profils d'exportation des données

- **Objectif :** Permettre un export modulable.
- **Actions :**
  - Analyser l'implémentation d'export dans l'application UnityAssetsManager.
  - consulter le fichier `H:\Sync\PKM_PROJECTS\TerraBloom\_Helpers\04_Assets\UnityAssetsManager\data\export_templates.jsonc` pour s'inspirer de la structure de données utilisée pour les profils d'exportation.
  - Adapter le endpoint ou la fonction d'export frontend pour supporter ces profils.

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
