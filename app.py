from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from engine import load_matches, wr_eco, bt, merge_metrics

# ------------------------
# arbre d'appels (app)
# main -> build_tables
# build_tables -> load_matches
# build_tables -> wr_eco(global + categorie)
# build_tables -> bt(global + categorie)
# build_tables -> merge_metrics
#
# roles rapides:
# build_tables : prepare les 2 tables finales (global / categorie)
# bar/scatter  : juste affichage

DATA = Path("Data")
VOTES = DATA / "votes.parquet"
CONV = DATA / "conversations.parquet"


@st.cache_data(show_spinner=False)
def build_tables():
    # preparation unique des data pour la session
    m = load_matches(VOTES, CONV)
    g = merge_metrics(wr_eco(m, by_cat=False), bt(m, by_cat=False), by_cat=False)
    c = merge_metrics(wr_eco(m, by_cat=True), bt(m, by_cat=True), by_cat=True)
    return m, g, c


def bar(df, metric: str):
    # classement simple
    labels = {"win_rate": "Winrate (%)", "bt_raw": "BT raw"}
    fig = px.bar(df, x="model_name", y=metric, color=metric, color_continuous_scale="Tealgrn", labels={"model_name": "Modele", metric: labels[metric]})
    fig.update_layout(xaxis_tickangle=-30, coloraxis_showscale=False)
    return fig


def scatter(df, metric: str):
    # X=score, Y=pollution
    labels = {"win_rate": "Winrate (%)", "bt_raw": "BT raw"}
    fig = px.scatter(
        df,
        x=metric,
        y="eco_kwh_mean",
        text="model_name",
        size="n_obs",
        hover_name="model_name",
        labels={metric: labels[metric], "eco_kwh_mean": "Conso moyenne (kWh)"},
    )
    fig.update_traces(textposition="top center")
    return fig


def corr_caption(df: pd.DataFrame, metric: str, scope: str) -> str:
    val = df[metric].corr(df["eco_kwh_mean"], method="pearson")
    if pd.isna(val):
        return f"Correlation {scope}: non calculable (pas assez de variance)."
    return f"Correlation {scope} ({metric} vs cout energetique): {val:.2f}."


def corr_memo() -> None:
    st.caption(
        "Memo correlation (Pearson, |r|) : <0.2 tres faible | 0.2-0.4 faible | 0.4-0.6 moderee | "
        "0.6-0.8 forte | >=0.8 tres forte. "
        "Si negatif: + le modele est performant, moins il est efficace. "
        "Si positif: + le modele est performant, + il est efficace."
    )


def main() -> None:
    st.set_page_config(page_title="Comparaison modeles", layout="wide")
    st.title("Comparaison modeles: Winrate + BT + cout ecologique")

    if not VOTES.exists() or not CONV.exists():
        st.error("Fichiers manquants: Data/votes.parquet et Data/conversations.parquet")
        st.stop()

    base, global_df, cat_df = build_tables()
    if global_df.empty:
        st.warning("Pas de donnees exploitables")
        st.stop()

    with st.sidebar:
        metric = st.selectbox("Classement", ["win_rate", "bt_raw"], format_func=lambda x: {"win_rate": "Winrate", "bt_raw": "Bradley-Terry"}[x])
        top_n = st.slider("Top modeles affiches", 5, max(5, int(global_df["model_name"].nunique())), min(12, int(global_df["model_name"].nunique())), 1)

    p1, p2 = st.tabs(["Comparaison modeles", "Materiaux & hypotheses"])

    with p1:
        t1, t2 = st.tabs(["Global", "Par categorie"])
        with t1:
            g_duels = int(round(global_df["n_obs"].sum() / 2))
            g_models = int(global_df["model_name"].nunique())
            g_categories = int(cat_df["category"].nunique()) if not cat_df.empty else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Duels (global)", g_duels)
            c2.metric("Modeles (global)", g_models)
            c3.metric("Categories dispo", g_categories)

            st.caption(corr_caption(global_df, metric, "global"))
            top = global_df.sort_values(metric, ascending=False).head(top_n)
            st.plotly_chart(bar(top, metric), use_container_width=True)
            st.plotly_chart(scatter(top, metric), use_container_width=True)
            st.dataframe(top[["model_name", "n_obs", "win_rate", "bt_raw", "bt_strength", "eco_kwh_mean", "eco_kwh_total"]], use_container_width=True)
            corr_memo()

        with t2:
            if cat_df.empty:
                st.info("Pas de categories exploitables")
            else:
                cat = st.selectbox("Categorie", sorted(cat_df["category"].unique().tolist()))
                cat_slice = cat_df[cat_df["category"] == cat]
                c_duels = int(round(cat_slice["n_obs"].sum() / 2))
                c_models = int(cat_slice["model_name"].nunique())
                c1, c2, c3 = st.columns(3)
                c1.metric("Duels (categorie)", c_duels)
                c2.metric("Modeles (categorie)", c_models)
                c3.metric("Categorie", cat)

                st.caption(corr_caption(cat_slice, metric, f"categorie '{cat}'"))
                one = cat_slice.sort_values(metric, ascending=False).head(top_n)
                st.plotly_chart(bar(one, metric), use_container_width=True)
                st.plotly_chart(scatter(one, metric), use_container_width=True)
                st.dataframe(one[["model_name", "n_obs", "win_rate", "bt_raw", "bt_strength", "eco_kwh_mean", "eco_kwh_total"]], use_container_width=True)
                corr_memo()

    with p2:
        st.markdown(
            """
### Question
Vas t'on etre a cours de materiaux dans les prochaines annees a cause de l'IA ?
En partant du principe qu'on utilisera une technologie similaire dans les années à venir. 

### Data 
1. Combien de materiaux contient une puce IA : NVDIA H100 souvent utilisée comme référence
2. Comment ces materiaux evoluent avec le recyclage
3. Comment le recyclage de ces matériaux évolue t'il dans le temps ? 
3. Quel est le stock de ces materiaux a l'echelle mondiale ? 
4. Quelle est la duree de vie d'une puce et sa \"duree utile\" de puissance de calcul.
5. Combien les modeles consomment en moyenne. 
6. Comment évolue la demande pour l'IA ?


### Data ?
2. **Stock mondial par matiere:** via USGS (reserves par commodite, pas un total unique). a priori ? 
3. **Conso moyenne des modeles dans notre app:** deja calculee via `eco_kwh_mean` depuis `conversations.parquet`.

### Sources principales
- UE (34 critiques / 17 strategiques): https://eur-lex.europa.eu/eli/reg/2024/1252/oj/eng  
- USGS (reserves mondiales par matiere): https://www.usgs.gov/publications/mineral-commodity-summaries-2025  

### Conclusion dans le délai de réalisation du projet 
    - Impossible d'estimer correctement la demande future en materiaux pour l'IA (evolution de la puissance de calcul, du recyclage, des modeles, etc.)
            """
        )


if __name__ == "__main__":
    main()
