# Sources retenues pour estimer "materiaux par requete"

## Objectif
Construire une estimation defendable de `materiaux vierges / requete IA` meme sans BOM publique complete des GPU IA.

Formule cible:
`materiaux_vierges_par_requete = (masse_materiaux * (1 - taux_recyclage)) / requetes_totales_vie`

## Pourquoi ces sources

### 1) Capacite de service (requetes/s ou tokens/s)
- Source: MLCommons / MLPerf Inference (datacenter)
- Lien:
  - https://mlcommons.org/benchmarks/inference-datacenter/
  - https://github.com/mlcommons/inference_results_v5.1
- Pourquoi:
  - benchmark public, reproductible, standard de facto.
  - donne un proxy robuste de throughput par hardware/workload.

### 2) Duree de vie infra (proxy puces)
- Sources:
  - Microsoft AR: https://www.microsoft.com/investor/reports/ar22/
  - Alphabet filing: https://www.sec.gov/Archives/edgar/data/1652044/000165204423000070/goog-20230630.htm
  - Amazon filing: https://www.sec.gov/Archives/edgar/data/1018724/000101872425000036/amzn-20250331.htm
  - Meta filing: https://www.sec.gov/Archives/edgar/data/1326801/000132680125000054/meta-20250331.htm
- Pourquoi:
  - chiffres officiels d'acteurs qui operent l'infra IA a grande echelle.
  - pas "duree de vie puce" pure, mais meilleur proxy public pour allocation par requete.

### 3) Recyclage (global/sectoriel, pas par puce)
- Sources:
  - Global E-waste Monitor 2024: https://api.globalewaste.org/publications/file/297/Global-E-waste-Monitor-2024.pdf
  - ITU PR (rare earths ~1%): https://www.itu.int/en/mediacentre/Pages/PR-2024-03-20-e-waste-recycling.aspx
  - UE COM(2023)306: https://www.europarl.europa.eu/RegData/docs_autres_institutions/commission_europeenne/com/2023/0306/COM_COM%282023%290306_EN.pdf
- Pourquoi:
  - pas de base ouverte robuste "recyclage par puce IA".
  - ces sources permettent des scenarios bas/central/haut transparents.

### 4) Liste des materiaux cibles (34/17 UE)
- Source legale: Regulation (EU) 2024/1252 (CRMA)
- Lien: https://eur-lex.europa.eu/eli/reg/2024/1252/oj/eng
- Pourquoi:
  - definit le perimetre materiaux critique/strategique pour l'etude.

## Limites explicites
- Pas de BOM publique complete des GPU IA recents (masse metal precise par puce).
- Les hypotheses masse materiaux doivent etre traitees en scenarios.
- Les resultats doivent etre presentes en fourchettes, pas comme une valeur unique "vraie".

## Date
- 2026-03-18
