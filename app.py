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
CRMA = DATA / "eu_crma_materials.csv"


@st.cache_data(show_spinner=False)
def build_tables():
    # preparation unique des data pour la session
    m = load_matches(VOTES, CONV)
    g = merge_metrics(wr_eco(m, by_cat=False), bt(m, by_cat=False), by_cat=False)
    c = merge_metrics(wr_eco(m, by_cat=True), bt(m, by_cat=True), by_cat=True)
    return m, g, c


@st.cache_data(show_spinner=False)
def load_crma() -> pd.DataFrame:
    if not CRMA.exists():
        return pd.DataFrame()
    return pd.read_csv(CRMA)


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


def main() -> None:
    st.set_page_config(page_title="Comparaison modeles", layout="wide")
    st.title("Comparaison modeles: Winrate + BT + cout ecologique")

    if not VOTES.exists() or not CONV.exists():
        st.error("Fichiers manquants: Data/votes.parquet et Data/conversations.parquet")
        st.stop()

    base, global_df, cat_df = build_tables()
    crma = load_crma()
    if global_df.empty:
        st.warning("Pas de donnees exploitables")
        st.stop()

    with st.sidebar:
        metric = st.selectbox("Classement", ["win_rate", "bt_raw"], format_func=lambda x: {"win_rate": "Winrate", "bt_raw": "Bradley-Terry"}[x])
        top_n = st.slider("Top modeles affiches", 5, max(5, int(global_df["model_name"].nunique())), min(12, int(global_df["model_name"].nunique())), 1)

    p1, p2 = st.tabs(["Comparaison modeles", "Materiaux & hypotheses"])

    with p1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Duels", int(base.shape[0]))
        c2.metric("Modeles", int(global_df["model_name"].nunique()))
        c3.metric("Categories", int(cat_df["category"].nunique()) if not cat_df.empty else 0)

        t1, t2 = st.tabs(["Global", "Par categorie"])
        with t1:
            top = global_df.sort_values(metric, ascending=False).head(top_n)
            st.plotly_chart(bar(top, metric), use_container_width=True)
            st.plotly_chart(scatter(top, metric), use_container_width=True)
            st.dataframe(top[["model_name", "n_obs", "win_rate", "bt_raw", "bt_strength", "eco_kwh_mean", "eco_kwh_total"]], use_container_width=True)

        with t2:
            if cat_df.empty:
                st.info("Pas de categories exploitables")
            else:
                cat = st.selectbox("Categorie", sorted(cat_df["category"].unique().tolist()))
                one = cat_df[cat_df["category"] == cat].sort_values(metric, ascending=False).head(top_n)
                st.plotly_chart(bar(one, metric), use_container_width=True)
                st.plotly_chart(scatter(one, metric), use_container_width=True)
                st.dataframe(one[["model_name", "n_obs", "win_rate", "bt_raw", "bt_strength", "eco_kwh_mean", "eco_kwh_total"]], use_container_width=True)

    with p2:
        st.caption("Premier jet: 34/17 CRMA + calcul simple matiere/requete avec hypotheses explicites.")
        if crma.empty:
            st.info("Fichier manquant: Data/eu_crma_materials.csv")
            st.stop()

        x1, x2, x3 = st.columns(3)
        x1.metric("Matieres critiques UE", int(crma["is_critical_ue"].sum()))
        x2.metric("Matieres strategiques UE", int(crma["is_strategic_ue"].sum()))
        x3.metric("Total unique (union)", int(crma["material_name"].nunique()))

        st.dataframe(crma.sort_values(["is_strategic_ue", "is_critical_ue", "material_name"], ascending=[False, False, True]), use_container_width=True)

        st.subheader("Simulation rapide: matiere vierge par requete")
        s1, s2, s3 = st.columns(3)
        lifetime_years = s1.slider("Duree de vie infra (ans)", 1.0, 8.0, 5.0, 0.5)
        req_per_sec = s2.number_input("Requetes par seconde (infra)", min_value=0.0001, value=0.25, step=0.05)
        utilization = s3.slider("Taux d'utilisation", 0.05, 1.0, 0.5, 0.05)

        m1, m2, m3 = st.columns(3)
        critical_mass_g = m1.number_input("Masse totale matieres critiques (g)", min_value=0.0, value=250.0, step=10.0)
        strategic_share = m2.slider("Part strategique dans ces matieres", 0.0, 1.0, 0.6, 0.05)
        recycling_rate = m3.slider("Taux recyclage effectif", 0.0, 0.95, 0.2, 0.05)

        requests_lifetime = req_per_sec * utilization * 365.25 * 24 * 3600 * lifetime_years
        virgin_critical_mg_per_req = ((critical_mass_g * (1 - recycling_rate)) * 1000.0) / requests_lifetime if requests_lifetime > 0 else 0.0
        virgin_strategic_mg_per_req = virgin_critical_mg_per_req * strategic_share

        r1, r2, r3 = st.columns(3)
        r1.metric("Requetes vie entiere (estime)", f"{requests_lifetime:,.0f}")
        r2.metric("Critiques vierges / requete (mg)", f"{virgin_critical_mg_per_req:.6f}")
        r3.metric("Strategiques vierges / requete (mg)", f"{virgin_strategic_mg_per_req:.6f}")

        st.caption("Formule: matiere_vierge/requete = (masse * (1-recyclage)) / requetes_vie_entiere")


if __name__ == "__main__":
    main()
