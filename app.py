from pathlib import Path

import plotly.express as px
import streamlit as st

from engine import (
    combine_metrics,
    compute_category_bt,
    compute_category_wr_eco,
    compute_global_bt,
    compute_global_wr_eco,
    load_matches,
)

DATA_DIR = Path("Data")
VOTES_PATH = DATA_DIR / "votes.parquet"
CONVERSATIONS_PATH = DATA_DIR / "conversations.parquet"


@st.cache_data(show_spinner=False)
def load_base() -> object:
    return load_matches(VOTES_PATH, CONVERSATIONS_PATH)


@st.cache_data(show_spinner=False)
def build_tables():
    base = load_base()
    global_wr = compute_global_wr_eco(base, min_obs=1)
    global_bt = compute_global_bt(base, min_obs=1)
    global_df = combine_metrics(global_wr, global_bt, by_category=False)

    cat_wr = compute_category_wr_eco(base, min_obs=1)
    cat_bt = compute_category_bt(base, min_obs=1)
    cat_df = combine_metrics(cat_wr, cat_bt, by_category=True)
    return base, global_df, cat_df


def make_bar(df, metric: str):
    label = {
        "win_rate": "Winrate (%)",
        "bt_raw": "BT raw",
        "eco_kwh_mean": "Conso moyenne (kWh)",
    }[metric]
    fig = px.bar(
        df,
        x="model_name",
        y=metric,
        color=metric,
        color_continuous_scale="Tealgrn",
        labels={"model_name": "Modele", metric: label},
    )
    fig.update_layout(xaxis_tickangle=-30, coloraxis_showscale=False)
    return fig


def make_score_vs_eco_scatter(df, score_metric: str):
    label = {
        "win_rate": "Winrate (%)",
        "bt_raw": "BT raw",
    }[score_metric]
    fig = px.scatter(
        df,
        x=score_metric,
        y="eco_kwh_mean",
        text="model_name",
        size="n_obs",
        hover_name="model_name",
        labels={score_metric: label, "eco_kwh_mean": "Conso moyenne (kWh)"},
    )
    fig.update_traces(textposition="top center")
    return fig


def main() -> None:
    st.set_page_config(page_title="Comparaison modeles", layout="wide")
    st.title("Comparaison modeles: Winrate + BT + cout ecologique")

    with st.sidebar:
        metric = st.selectbox(
            "Classement",
            ["win_rate", "bt_raw"],
            format_func=lambda x: {
                "win_rate": "Winrate",
                "bt_raw": "Bradley-Terry",
            }[x],
        )

    if not VOTES_PATH.exists() or not CONVERSATIONS_PATH.exists():
        st.error("Fichiers manquants: Data/votes.parquet et Data/conversations.parquet")
        st.stop()

    base, global_df, cat_df = build_tables()
    if global_df.empty:
        st.warning("Aucun modele ne passe le seuil minimum.")
        st.stop()

    max_models = int(global_df["model_name"].nunique())
    with st.sidebar:
        top_n = st.slider("Top modeles affiches", 5, max(5, max_models), min(12, max_models), 1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Duels", int(base.shape[0]))
    c2.metric("Modeles", int(global_df["model_name"].nunique()))
    c3.metric("Categories", int(cat_df["category"].nunique()) if not cat_df.empty else 0)

    t1, t2 = st.tabs(["Global", "Par categorie"])

    with t1:
        top = global_df.sort_values(metric, ascending=False).head(top_n)
        st.plotly_chart(make_bar(top, metric), use_container_width=True)
        st.plotly_chart(make_score_vs_eco_scatter(top, metric), use_container_width=True)
        st.dataframe(
            top[["model_name", "n_obs", "win_rate", "bt_raw", "bt_strength", "eco_kwh_mean", "eco_kwh_total"]],
            use_container_width=True,
        )

    with t2:
        if cat_df.empty:
            st.info("Pas de categories exploitables avec ce seuil.")
            return

        categories = sorted(cat_df["category"].unique().tolist())
        selected = st.selectbox("Categorie", categories)
        one = cat_df[cat_df["category"] == selected].copy()
        one = one.sort_values(metric, ascending=False).head(top_n)

        st.plotly_chart(make_bar(one, metric), use_container_width=True)
        st.plotly_chart(make_score_vs_eco_scatter(one, metric), use_container_width=True)
        st.dataframe(
            one[["model_name", "n_obs", "win_rate", "bt_raw", "bt_strength", "eco_kwh_mean", "eco_kwh_total"]],
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
