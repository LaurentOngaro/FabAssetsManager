---
description: "Instructions générales pour le développement du projet FabAssetsManager"
applyTo: "**/*.{py,js,html,css,md}"
---

# Projet FabAssetsManager

## Objectif du projet

Application locale (Python/Flask + Vanilla JS/HTML) permettant de lister, filtrer, et prévisualiser sa bibliothèque d'assets 3D achetés/récupérés sur le store Fab.com d'Epic Games.

## Architecture & Conventions

1. **Backend (Python)** :

- `app.py` sert simplement l'application Flask courante.
- `fetch_fab_library.py` (et `cache_manager.py`) s'occupent de contacter l'API (avec `curl_cffi` pour by-passer Cloudflare) et de traiter les JSON.
- Les données sont **mises en cache localement** :
  - L'ensemble des assets sous forme de fichiers unitaires dans le dossier `assets/`
  - Les miniatures des images sous forme de `.jpg` dans le dossier `previews/`
  - La date de dernière mise à jour dans `last_update.txt` (ou équivalent).

2. **Frontend (Vanilla)** :

- Tout est dans `static/index.html`.
- **Interdiction formelle** d'utiliser un framework JavaScript (React, Vue, etc.) ou CSS (Tailwind, Bootstrap). Tout doit être fait en Vanilla JS et CSS pur.
- Respectez les classes utilitaires CSS déjà existantes (`.btn`, `.modal`, `.filter-group`, etc.).

3. **Organisation du travail** :

- Lisez et appliquez les priorités définies dans `TODO.md` situé à la racine.
- Lisez systématiquement `_helpers/PLAN_ACTIONS.md` pour voir l'implémentation prévue d'une tâche.
- Ne modifiez pas ces fichiers sans avoir achevé la tâche correspondante. Une fois terminé, préfixez le titre dans `_helpers/PLAN_ACTIONS.md` par `DONE ` et cochez la case dans `TODO.md`.

## Règles de Codage

- Ciblez avec précision le code à modifier pour ne pas casser le reste (utilisez les outils d'édition ciblée).
- Pour Python, suivez PEP8, utilisez les types hints lorsque c'est pertinent.
- Soyez concis dans les explications textuelles et orienté solution.

## Gestion des versions et Changelog

À chaque modification significative du projet (nouvelle fonctionnalité, correction de bug, refonte), vous devez mettre à jour les fichiers `CHANGELOG.md` et `VERSION.txt` selon les principes du **Semantic Versioning (SemVer)** (format `MAJOR.MINOR.PATCH`) :

- **MAJOR** : Changements incompatibles ou refonte majeure (ex: changement radical de l'architecture, nouvelle techno, cassure de compatibilité).
- **MINOR** : Ajout de nouvelles fonctionnalités de manière rétrocompatible (ex: ajout d'un nouveau filtre, nouvel export, actions par lot).
- **PATCH** : Corrections de bugs et petites améliorations rétrocompatibles (ex: ajustement UI, fix d'un parsing JSON).

**Règles de suivi :**

1. Documentez systématiquement la modification dans le fichier `CHANGELOG.md` (idéalement au format [Keep a Changelog](https://keepachangelog.com/)) sous la version en cours ou la balise `[Unreleased]`.
2. Utilisez les catégories standard : `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, ou `Security`.
3. Tout bump de version doit passer par le helper `python _helpers/bumpImportantVersion.py` (`patch` par défaut, ou via `--scope minor` / `--scope major`).
4. **IMPORTANT** : N'éditez plus les versions manuellement. Ce script synchronise automatiquement `VERSION.txt`, `CHANGELOG.md`, ainsi que l'ensemble des balises de version (`Version: X.Y.Z`, `**Version:** X.Y.Z`, ou `version: X.Y.Z`) présentes dans les en-têtes des fichiers du projet (ex: `app.py`, `static/index.html`, `fetch_fab_library.py`, `README.md`, `openapi.yaml`, etc.).
