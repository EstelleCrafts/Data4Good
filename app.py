from pathlib import Path

import plotly.express as px
import streamlit as st

from engine import (
    compute_category_bt,
    compute_category_winrate,
    compute_global_bt,
    compute_global_winrate,
    load_matches_with_categories,
)

DATA_DIR = Path("Data")
VOTES_PATH = DATA_DIR / "votes.parquet"
CONVERSATIONS_PATH = DATA_DIR / "conversations.parquet"


@st.cache_data(show_spinner=False)
def load_base():
    return load_matches_with_categories(VOTES_PATH, CONVERSATIONS_PATH)


def _bar(df, x, y, label):
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=y,
        color_continuous_scale="Tealgrn",
        labels={x: "Modele", y: label},
    )
    fig.update_layout(xaxis_tickangle=-30, coloraxis_showscale=False)
    return fig


def main() -> None:
    st.set_page_config(page_title="Compar:IA Ranking", layout="wide")
    st.title("Compar:IA - Winrate + Bradley-Terry")

    with st.sidebar:
        min_obs = st.slider("Minimum observations", 30, 5000, 200, 10)
        top_n = st.slider("Top modeles affiches", 5, 30, 12, 1)

    if not VOTES_PATH.exists() or not CONVERSATIONS_PATH.exists():
        st.error("Fichiers manquants: Data/votes.parquet et Data/conversations.parquet")
        st.stop()

    base = load_base()
    global_wr = compute_global_winrate(base, min_obs=min_obs)
    category_wr = compute_category_winrate(base, min_obs=min_obs)
    global_bt = compute_global_bt(base, min_obs=min_obs)
    category_bt = compute_category_bt(base, min_obs=min_obs)

    if global_wr.empty:
        st.warning("Aucun modele ne passe le seuil minimum.")
        st.stop()

    c1, c2, c3 = st.columns(3)
    c1.metric("Duels", int(base.shape[0]))
    c2.metric("Modeles (winrate)", int(global_wr["model_name"].nunique()))
    c3.metric("Modeles (BT)", int(global_bt["model_name"].nunique()) if not global_bt.empty else 0)

    t1, t2 = st.tabs(["Winrate", "Bradley-Terry"])

    with t1:
        st.subheader("1) Winrate global")
        top_global = global_wr.head(top_n)
        st.plotly_chart(_bar(top_global, "model_name", "win_rate", "Winrate (%)"), use_container_width=True)
        st.dataframe(top_global, use_container_width=True)

        st.subheader("2) Winrate par categorie")
        if category_wr.empty:
            st.info("Aucune categorie ne passe le seuil minimum.")
        else:
            cats = sorted(category_wr["category"].unique().tolist())
            selected = st.selectbox("Choisis une categorie", cats, index=0, key="wr_cat")
            one = category_wr[category_wr["category"] == selected].sort_values("win_rate", ascending=False).head(top_n)
            st.plotly_chart(_bar(one, "model_name", "win_rate", "Winrate (%)"), use_container_width=True)
            st.dataframe(one, use_container_width=True)

    with t2:
        st.subheader("1) Bradley-Terry global")
        if global_bt.empty:
            st.info("BT global indisponible avec ce seuil.")
        else:
            top_bt = global_bt.head(top_n)
            st.plotly_chart(_bar(top_bt, "model_name", "bt_raw", "BT raw (non normalise)"), use_container_width=True)
            st.dataframe(top_bt, use_container_width=True)

        st.subheader("2) Bradley-Terry par categorie")
        if category_bt.empty:
            st.info("BT par categorie indisponible avec ce seuil.")
        else:
            cats_bt = sorted(category_bt["category"].unique().tolist())
            selected_bt = st.selectbox("Choisis une categorie BT", cats_bt, index=0, key="bt_cat")
            one_bt = category_bt[category_bt["category"] == selected_bt].sort_values("bt_strength", ascending=False).head(top_n)
            st.plotly_chart(_bar(one_bt, "model_name", "bt_raw", "BT raw (non normalise)"), use_container_width=True)
            st.dataframe(one_bt, use_container_width=True)


if __name__ == "__main__":
    main()
