from pathlib import Path
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
            return
        cat = st.selectbox("Categorie", sorted(cat_df["category"].unique().tolist()))
        one = cat_df[cat_df["category"] == cat].sort_values(metric, ascending=False).head(top_n)
        st.plotly_chart(bar(one, metric), use_container_width=True)
        st.plotly_chart(scatter(one, metric), use_container_width=True)
        st.dataframe(one[["model_name", "n_obs", "win_rate", "bt_raw", "bt_strength", "eco_kwh_mean", "eco_kwh_total"]], use_container_width=True)


if __name__ == "__main__":
    main()
