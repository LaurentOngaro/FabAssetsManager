# Plan d'implementation - recommandations UAM vers FAM

Objectif: capitaliser sur les optimisations observees dans UnityAssetsManager pour ameliorer les performances, la robustesse API et la maintenabilite de FabAssetsManager.

## Portee

Ce plan couvre 7 axes:

1. Cache memoire backend avec TTL.
2. Pagination et filtrage server-side.
3. Validation JSON API plus robuste.
4. Normalisation de la configuration (types et parsing).
5. Endpoint de diagnostic de configuration/source.
6. Export headless pour automatisation locale.
7. Enrichissement du payload d'erreur (champ path).

## Details d'implementation

### REF4 - Cache memoire TTL backend

But:

- Eviter les relectures disque repetitives de assets/\*.json entre appels API proches.

Approche:

- Introduire un cache applicatif en memoire pour la liste plate des assets et/ou les assets bruts.
- Ajouter un TTL configurable dans config/config.json (ex: cache_ttl_seconds).
- Invalider explicitement le cache apres fetch, clear_cache, clear_previews (si necessaire), et operations qui modifient les assets.

DoD:

- Les endpoints frequents n'appellent plus load_all_assets a chaque requete quand le TTL est valide.
- Presence de tests unitaires pour expiration TTL et invalidation.

Risques:

- Donnees stale si invalidation oubliee.

Mitigation:

- Centraliser l'invalidation dans une seule fonction.

### REF5 - Pagination + filtrage server-side

But:

- Eviter de charger et filtrer toute la bibliotheque dans le navigateur.

Approche:

- Ajouter endpoint API pagine (draw/start/length/search/order/filtres).
- Deplacer logique de filtrage principal cote backend.
- Conserver un mode compatibilite temporaire pour la grille actuelle.

DoD:

- Le frontend peut fonctionner sans charger toute la bibliotheque d'un coup.
- Les volumes eleves restent fluides (temps de reponse stable, RAM navigateur reduite).

Risques:

- Refacto transverse frontend/backend.

Mitigation:

- Introduire par feature-flag (mode client actuel vs mode server-side).

### REF6 - Validation JSON API robuste

But:

- Reduire les 500 sur payload invalide ou header Content-Type absent.

Approche:

- Utiliser request.get_json(silent=True) partout ou pertinent.
- Ajouter validation centralisee des champs obligatoires.
- Retourner des erreurs standardisees avec code explicite.

DoD:

- Aucun endpoint POST/PUT/PATCH ne depend d'un get_json non protege.
- Tests API pour payload vide, JSON malforme, champs manquants.

### REF7 - Normalisation config (types + parsing)

But:

- Rendre la configuration plus resilientes aux types inattendus.

Approche:

- Introduire utilitaires de parsing (\_parse_bool, \_parse_int, etc.) cote FAM.
- Charger/sauver config via couche unifiee (eventuellement service config.py).
- Valider les bornes (ex: port > 0, log_max_bytes > 0).

DoD:

- Parametres critiques valides et sanitizes au chargement.
- Comportement previsible meme avec config partiellement invalide.

### GE4 - Endpoint diagnostic config/source

But:

- Diagnostiquer rapidement les preconditions backend sans lancer un fetch complet.

Approche:

- Ajouter endpoint de test (ex: cookies/user-agent presentes, chemins resolves, droits ecriture assets/previews, metadata lisible).
- Retourner statut detaille et hints actionnables.

DoD:

- Endpoint exploitable par UI maintenance et par scripts.
- Erreurs detaillees standardisees.

### FEAT9 - Export headless orient automation

But:

- Permettre des exports fichiers sans passer par telechargement navigateur.

Approche:

- Endpoint POST acceptant format, filtres, output_path ou output_dir/file_name.
- Reutiliser les mecanismes d'export existants.

DoD:

- Ecriture fichier reussie avec retour chemin + nombre d'elements exportes.
- Validation de chemin et erreurs claires.

### REF8 - Ajouter path dans les reponses d'erreur

But:

- Accelerer le diagnostic cote client et logs.

Approche:

- Etendre create_error_response/AppError pour inclure request.path dans error.path.
- Mettre a jour le contrat JSON Schema de reponse erreur.

DoD:

- Tous les payloads d'erreur exposent error.path.
- Contrat de schema synchronise.

## Strategie de tests

- Unit tests backend:
  - cache TTL et invalidation.
  - parsing config resilient.
  - serialization erreur avec path.
- API tests:
  - payload invalide sur endpoints JSON.
  - endpoint diagnostic.
  - export headless avec chemins valides/invalides.
- Non regression:
  - /api/assets, /api/details/<uid>, /api/export/csv, /api/export/json.

## Note

Le detail ci-dessus sert de reference par chantier. L'ordre d'implementation prioritaire est maintenu dans `TODO.md`.
