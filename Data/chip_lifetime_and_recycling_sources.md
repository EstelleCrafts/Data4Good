# Recyclage des materiaux & duree de vie des puces/serveurs (sources)

## TL;DR
- Donnee **directe** "taux de recyclage par puce" : **non disponible publiquement** de facon robuste.
- Donnees **utilisables** :
  - taux globaux e-waste / metaux critiques (proxy),
  - duree de vie comptable des serveurs chez hyperscalers (proxy infra IA).

## 1) Recyclage: ce qu'on a

### 1.1 Niveau global e-waste
- Source: Global E-waste Monitor 2024 (ITU/UNITAR)
- Chiffre cle: 22.3% de l'e-waste 2022 documente comme collecte/recycle formellement.
- Lien: https://www.itu.int/en/ITU-D/Environment/Pages/Publications/The-Global-E-waste-Monitor-2024.aspx
- Lien PDF direct: https://api.globalewaste.org/publications/file/297/Global-E-waste-Monitor-2024.pdf

### 1.2 Metaux critiques / terres rares
- Source: ITU press release GEM 2024
- Chiffre cle: ~1% de la demande en terres rares couverte par recyclage e-waste.
- Lien: https://www.itu.int/en/mediacentre/Pages/PR-2024-03-20-e-waste-recycling.aspx

### 1.3 UE - ordres de grandeur CRMA (proposition 2023)
- Source: COM(2023)306 (texte de la Commission)
- Chiffres cites:
  - nickel: ~16% end-of-life recycling rate
  - cobalt: ~22%
  - beaucoup de metaux de specialite / terres rares: ~1%
- Lien: https://www.europarl.europa.eu/RegData/docs_autres_institutions/commission_europeenne/com/2023/0306/COM_COM%282023%290306_EN.pdf

## 2) Duree de vie: ce qu'on a (proxy serveurs IA)

### 2.1 Microsoft
- Changement estime de vie serveurs/network: 4 -> 6 ans (FY2023)
- Source: Microsoft 2022 Annual Report
- Lien: https://www.microsoft.com/investor/reports/ar22/

### 2.2 Alphabet (Google)
- Changement estime de vie serveurs: 4 -> 6 ans (FY2023)
- Source: SEC filing (Alphabet)
- Lien: https://www.sec.gov/Archives/edgar/data/1652044/000165204423000070/goog-20230630.htm

### 2.3 Amazon
- 2024: certains serveurs 5 -> 6 ans
- 2025: subset serveurs/network 6 -> 5 ans (IA/ML pace)
- Source: SEC filing (Amazon)
- Lien: https://www.sec.gov/Archives/edgar/data/1018724/000101872425000036/amzn-20250331.htm
- Lien (10-K 2025): https://www.sec.gov/Archives/edgar/data/0001018724/000101872426000004/amzn-20251231.htm

### 2.4 Meta
- Changement estime de vie de la plupart des serveurs/network: 5.5 ans (effet 2025)
- Source: SEC filing (Meta)
- Lien: https://www.sec.gov/Archives/edgar/data/1326801/000132680125000054/meta-20250331.htm
- Lien (10-K 2025): https://www.sec.gov/Archives/edgar/data/1326801/000162828026003942/meta-20251231.htm

## 3) Ce qui manque pour une metrique "metal par requete"
- Masse de chaque metal par type de puce/serveur (BOM detaillee, rarement publique).
- Taux de recyclage specifique "puces IA" (pas trouve en open data robuste).
- Debit de service comparable (requetes/s ou tokens/s) par type d'infra + taux d'utilisation reel.

## 4) Recommandation methode
- Utiliser les taux globaux/sectoriels comme **scenarios** (bas/central/haut), pas comme verite absolue.
- Documenter explicitement les hypotheses (durée de vie, usage, recyclage effectif).
- Presenter les resultats en **fourchettes**.

## Date
- 2026-03-18
