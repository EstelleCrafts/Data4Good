# Data & Sources

## 1) Jeux de donnees bruts (fournis)

### `Data/conversations.parquet`
- Lignes: 481109
- Colonnes: 42
- Source (dataset): https://huggingface.co/datasets/ministere-culture/comparia-conversations
- Fichiers (onglet Files): https://huggingface.co/datasets/ministere-culture/comparia-conversations/tree/main
- Usage dans le projet:
  - categories de conversation (classements par categorie)
  - conso estimee `total_conv_a_kwh` / `total_conv_b_kwh`

### `Data/votes.parquet`
- Lignes: 152842
- Colonnes: 46
- Source (dataset): https://huggingface.co/datasets/ministere-culture/comparia-votes
- Fichiers (onglet Files): https://huggingface.co/datasets/ministere-culture/comparia-votes/tree/main
- Usage dans le projet:
  - duels modele A vs modele B
  - resultat du duel (`chosen_model_name`, `both_equal`)

### `Data/reactions.parquet`
- Lignes: 91833
- Colonnes: 45
- Source (dataset): https://huggingface.co/datasets/ministere-culture/comparia-reactions
- Fichiers (onglet Files): https://huggingface.co/datasets/ministere-culture/comparia-reactions/tree/main
- Usage actuel:
  - non utilise dans la version app simplifiee actuelle
  - conserve pour analyses futures (qualite fine, message-level)

### `Data/structuredatasetcomparia.csv`
- Dictionnaire de colonnes/descriptions du jeu Compar:IA.
- Source: fourni localement avec le projet (pas de lien externe trouve dans ce repo).

## 2) Donnees derivees (creees dans ce repo)

### `Data/model_energy_summary.csv`
- Lignes: 103
- Colonnes: 6
- Colonnes:
  - `model_name`, `n_obs`, `energy_kwh_total`, `energy_kwh_mean`, `energy_kwh_median`, `energy_kwh_p90`
- Generation:
  - script: `build_model_energy_summary.py`
  - source par defaut: `Data/conversations.parquet`
  - fallback possible: `Data/model_energy_api.csv` (si collecte API faite)

### `Data/eu_crma_materials.csv`
- Lignes: 40 (union des listes)
- Colonnes: 6
- Colonnes:
  - `material_name`, `is_critical_ue`, `is_strategic_ue`, `source_regulation`, `critical_annex`, `strategic_annex`
- Comptes verifies:
  - 34 critiques
  - 17 strategiques
  - 11 en overlap

### `Data/eu_crma_materials_sources.md`
- Note de sourcing specifique au fichier CRMA.

### `Data/chip_lifetime_and_recycling_sources.md`
- Note de sourcing sur:
  - recyclage (global + metaux critiques),
  - duree de vie des serveurs (proxy infra IA),
  - limites pour une metrique \"metal par requete\".

## 3) Fichiers code qui produisent/consomment la data

### `engine.py`
- Charge `votes.parquet` + `conversations.parquet`
- Calcule:
  - `win_rate`
  - `bt_raw` / `bt_strength` (Bradley-Terry)
  - `eco_kwh_mean` / `eco_kwh_total`
- Sort des tables globales et par categorie.

### `app.py`
- UI Streamlit principale.
- Affiche:
  - classements (winrate ou BT)
  - scatter `score (X)` vs `pollution (Y)`
  - tables globales et par categorie.

### `build_model_energy_summary.py`
- Construit `Data/model_energy_summary.csv`.
- Nettoie les noms de modeles.
- Agrege les stats d'energie par modele.

### `collect_energy_api.py`
- Script optionnel de collecte API (OpenAI + EcoLogits).
- Sortie cible: `Data/model_energy_api.csv`.
- Etat actuel du repo: ce fichier n'est pas present (collecte non executee ici).

## 4) Sources externes referencees

### A) Source de donnees principale (Compar:IA)
- Portail ranking:
  - https://comparia.beta.gouv.fr/ranking
- Article metodologique:
  - https://huggingface.co/blog/comparIA/publication-du-premier-classement
- Organisation Hugging Face (datasets publics):
  - https://huggingface.co/ministere-culture

### B) Cadre materiaux critiques UE (CRMA)
- Texte officiel (EUR-Lex):
  - https://eur-lex.europa.eu/eli/reg/2024/1252/oj/eng
- Annexes utilisees:
  - Annex I Section 1 (strategiques)
  - Annex II Section 1 (critiques)

### C) Ressources de contexte materiaux/energie (veille)
- RMIS (JRC UE):
  - https://rmis.jrc.ec.europa.eu/eu-critical-raw-materials
- IEA (critical minerals):
  - https://www.iea.org/reports/the-role-of-critical-minerals-in-clean-energy-transitions
- USGS critical minerals:
  - https://www.usgs.gov/index.php/programs/mineral-resources-program/science/about-2025-draft-list-critical-minerals

### D) Outils API energie (optionnel)
- EcoLogits docs:
  - https://ecologits.ai/latest/
- OpenAI Python SDK docs:
  - https://platform.openai.com/docs

## 4bis) Notes d'acces
- Les datasets Compar:IA sur Hugging Face sont annonces comme publics mais souvent **gated**:
  - il faut accepter les conditions pour telecharger les fichiers complets.
- Les liens `tree/main` permettent de voir la structure et les noms de fichiers.

## 5) Hypotheses et limites (version actuelle)
- La conso ecologique dans l'app vient des kWh deja presents dans `conversations.parquet`.
- `collect_energy_api.py` n'alimente pas encore l'app tant que `Data/model_energy_api.csv` n'existe pas.
- Les indicateurs affiches sont des comparatifs relatifs entre modeles, pas une ACV complete materiaux+infrastructure+fin de vie.

## 6) Date de mise a jour
- 2026-03-18
