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
- `lib/app_settings.py` centralise les constantes applicatives.
- `lib/fetch_fab_library.py` (et `lib/cache_manager.py`) s'occupent de contacter l'API (avec `curl_cffi` pour by-passer Cloudflare) et de traiter les JSON.
- Les données sont **mises en cache localement** :
  - L'ensemble des assets sous forme de fichiers unitaires dans le dossier `assets/`
  - Les miniatures des images sous forme de `.jpg` dans le dossier `previews/`
  - La date de dernière mise à jour dans `last_update.txt` (ou équivalent).

2. **Frontend (Vanilla)** :

- L'interface est répartie entre `static/index.html`, `static/js/app.js` et `static/css/style.css`.
- **Interdiction formelle** d'utiliser un framework JavaScript (React, Vue, etc.) ou CSS (Tailwind, Bootstrap). Toute l'UI doit rester en Vanilla JS et CSS pur.
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


**Règles de suivi :**

1. Documentez systématiquement la modification dans le fichier `CHANGELOG.md` (idéalement au format [Keep a Changelog](https://keepachangelog.com/)) sous la version en cours ou la balise `[Unreleased]`.
2. Utilisez les catégories standard : `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, ou `Security`.
3. **Actualisation de la documentation** : après une modification significative, assurez-vous que la documentation impactée reste cohérente.

- `README.md` et `API_GUIDE.md` : mettez-les à jour si le comportement visible, les workflows ou les usages changent.
- `_helpers/specs.md` : gardez-le aligné avec l'architecture réelle, les routes, les formats de cache et les hypothèses techniques courantes.
- `openapi.yaml` : mettez-le à jour dès qu'un endpoint, un payload ou un contrat de réponse change.
- `CHANGELOG.md` et `VERSION.txt` : mettez-les à jour pour les changements significatifs, en suivant le versionnement sémantique (MAJOR.MINOR.PATCH).
  - **IMPORTANT** : Tout bump de version doit passer par le helper `python _helpers/bumpImportantVersion.py` (via Terminal). N'éditez plus les versions manuellement : ce script synchronise automatiquement le fichier `VERSION.txt`, `CHANGELOG.md` et les balises de version (`Version: X.Y.Z`, `**Version:** X.Y.Z`) situées en haut des différents fichiers du projet (`app.py`, `static/index.html`, `README.md`, `openapi.yaml`, etc.).
