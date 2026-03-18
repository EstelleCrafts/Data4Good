# Sources - Matieres critiques / strategiques UE

## Fichier de donnees
- `Data/eu_crma_materials.csv`
- Colonnes principales:
  - `material_name`
  - `is_critical_ue`
  - `is_strategic_ue`
  - `critical_annex`
  - `strategic_annex`

## Source officielle principale
- Regulation (EU) 2024/1252 (Critical Raw Materials Act)
- EUR-Lex: https://eur-lex.europa.eu/eli/reg/2024/1252/oj/eng

## Sections utilisees
- Liste des matieres strategiques: **Annex I, Section 1**
- Liste des matieres critiques: **Annex II, Section 1**

## Regles de construction du CSV
- Le CSV est un **union** des 2 listes (strategiques + critiques).
- Resultat: 40 lignes uniques au total.
- Comptes verifies:
  - 34 matieres critiques (`is_critical_ue = true`)
  - 17 matieres strategiques (`is_strategic_ue = true`)
  - 11 matieres presentes dans les 2 listes.

## Notes de normalisation
- Les libelles restent proches des annexes, avec une forme pratique pour l'analyse (`lowercase`, variantes explicites comme `battery grade`, `metal`, etc.).
- Certaines entrees ont des variantes entre annexes (ex: `boron` vs `boron - metallurgy grade`, `lithium` vs `lithium - battery grade`, `graphite` vs `graphite - battery grade`).

## Date
- Extraction/structuration: 2026-03-18
