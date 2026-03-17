from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# ------------------------
# arbre d'appels (depuis app.py)
# main -> build_tables
# build_tables -> load_matches
# build_tables -> wr_eco(by_cat=False/True)
# build_tables -> bt(by_cat=False/True)
# build_tables -> merge_metrics
#
# roles rapides:
# load_matches : fabrique la base de duels A/B + categorie + kwh
# wr_eco       : winrate + cout eco (global ou categorie)
# bt           : force Bradley-Terry (global ou categorie)
# merge_metrics: colle winrate/eco et bt dans une table finale


def load_matches(votes_path: Path, conv_path: Path) -> pd.DataFrame:
    # lit juste les colonnes utiles
    v = pq.read_table(votes_path, columns=["conversation_pair_id", "model_a_name", "model_b_name", "chosen_model_name", "both_equal"]).to_pandas()
    c = pq.read_table(conv_path, columns=["conversation_pair_id", "categories", "total_conv_a_kwh", "total_conv_b_kwh"]).to_pandas()
    d = v.merge(c, on="conversation_pair_id", how="left")

    # score du duel: A gagne=1, nul=0.5, A perd=0
    score_a = np.where(d["chosen_model_name"] == d["model_a_name"], 1.0, np.where(d["both_equal"] == True, 0.5, 0.0))

    return pd.DataFrame({
        "model_a": d["model_a_name"],
        "model_b": d["model_b_name"],
        "score_a": score_a,
        "categories": d["categories"],
        "eco_a_kwh": pd.to_numeric(d["total_conv_a_kwh"], errors="coerce"),
        "eco_b_kwh": pd.to_numeric(d["total_conv_b_kwh"], errors="coerce"),
    }).dropna(subset=["model_a", "model_b"])


def _explode_cat(df: pd.DataFrame) -> pd.DataFrame:
    # passe de liste de categories -> 1 ligne par categorie
    x = df.explode("categories").dropna(subset=["categories"]).copy()
    x["category"] = x["categories"].astype(str).str.strip()
    return x[x["category"] != ""]


def _side(df: pd.DataFrame, gcols: list[str]) -> pd.DataFrame:
    # transforme un duel en 2 lignes (vue modele)
    a = df[gcols + ["model_a", "score_a", "eco_a_kwh"]].rename(columns={"model_a": "model_name", "score_a": "win_point", "eco_a_kwh": "eco_kwh"})
    b = df[gcols + ["model_b", "score_a", "eco_b_kwh"]].rename(columns={"model_b": "model_name", "eco_b_kwh": "eco_kwh"})
    b["win_point"] = 1.0 - b["score_a"]
    return pd.concat([a, b.drop(columns=["score_a"])], ignore_index=True)


def wr_eco(matches: pd.DataFrame, by_cat: bool) -> pd.DataFrame:
    # calcule winrate + conso moyenne/totale
    src = _explode_cat(matches) if by_cat else matches
    gcols = ["category"] if by_cat else []
    s = _side(src, gcols)
    out = s.groupby(gcols + ["model_name"], dropna=False).agg(
        n_obs=("win_point", "size"),
        win_rate=("win_point", "mean"),
        eco_kwh_mean=("eco_kwh", "mean"),
        eco_kwh_total=("eco_kwh", "sum"),
    ).reset_index()
    out["win_rate"] = (out["win_rate"] * 100).round(2)
    out[["eco_kwh_mean", "eco_kwh_total"]] = out[["eco_kwh_mean", "eco_kwh_total"]].round(10)
    return out


def _bt_single(df: pd.DataFrame) -> pd.DataFrame:
    # BT en mode itératif: on part tous egaux puis on ajuste jusqu'a stabilisation
    models = pd.Index(pd.concat([df["model_a"], df["model_b"]]).dropna().unique())
    if models.empty:
        return pd.DataFrame(columns=["model_name", "bt_raw", "bt_strength"])

    idx = {m: i for i, m in enumerate(models)}
    n = len(models)
    wins, comps = np.zeros((n, n)), np.zeros((n, n))

    # matrice de confrontations
    for r in df[["model_a", "model_b", "score_a"]].itertuples(index=False):
        i, j, s = idx[r.model_a], idx[r.model_b], float(r.score_a)
        wins[i, j] += s
        wins[j, i] += 1.0 - s
        comps[i, j] += 1.0
        comps[j, i] += 1.0

    p = np.ones(n)  # init egale
    w = wins.sum(axis=1)
    for _ in range(200):
        denom = np.zeros(n)
        for i in range(n):
            den = comps[i] / (p[i] + p)
            den[i] = 0.0
            denom[i] = den.sum()
        p_new = np.divide(w, denom, out=p.copy(), where=denom > 0)
        p_new = np.clip(p_new, 1e-12, None)
        p_new /= p_new.mean()  # juste pour stabilité numerique
        if np.max(np.abs(np.log(p_new) - np.log(p))) < 1e-6:
            p = p_new
            break
        p = p_new

    out = pd.DataFrame({"model_name": models, "bt_raw": np.round(p, 6), "bt_strength": np.round(np.log(p), 4)})
    return out.sort_values("bt_strength", ascending=False)


def bt(matches: pd.DataFrame, by_cat: bool) -> pd.DataFrame:
    # BT global ou BT par categorie
    if not by_cat:
        return _bt_single(matches)
    rows = []
    for cat, g in _explode_cat(matches).groupby("category"):
        x = _bt_single(g)
        if not x.empty:
            x.insert(0, "category", cat)
            rows.append(x)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["category", "model_name", "bt_raw", "bt_strength"])


def merge_metrics(wr_df: pd.DataFrame, bt_df: pd.DataFrame, by_cat: bool) -> pd.DataFrame:
    # merge final pour l'app
    keys = ["category", "model_name"] if by_cat else ["model_name"]
    out = wr_df.merge(bt_df, on=keys, how="left")
    out["bt_raw"] = out["bt_raw"].fillna(0)
    out["bt_strength"] = out["bt_strength"].fillna(-999)
    return out
