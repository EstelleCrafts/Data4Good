from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


# ------------------------
# base de duels

def load_matches(votes_path: Path, conversations_path: Path) -> pd.DataFrame:
    votes = pq.read_table(
        votes_path,
        columns=["conversation_pair_id", "model_a_name", "model_b_name", "chosen_model_name", "both_equal"],
    ).to_pandas()

    conv = pq.read_table(
        conversations_path,
        columns=["conversation_pair_id", "categories", "total_conv_a_kwh", "total_conv_b_kwh"],
    ).to_pandas()

    data = votes.merge(conv, on="conversation_pair_id", how="left")

    score_a = np.where(
        data["chosen_model_name"] == data["model_a_name"],
        1.0,
        np.where(data["both_equal"] == True, 0.5, 0.0),
    )

    return pd.DataFrame(
        {
            "model_a": data["model_a_name"],
            "model_b": data["model_b_name"],
            "score_a": score_a,
            "categories": data["categories"],
            "eco_a_kwh": pd.to_numeric(data["total_conv_a_kwh"], errors="coerce"),
            "eco_b_kwh": pd.to_numeric(data["total_conv_b_kwh"], errors="coerce"),
        }
    ).dropna(subset=["model_a", "model_b"])


# ------------------------
# helpers

def _explode_categories(matches: pd.DataFrame) -> pd.DataFrame:
    df = matches.explode("categories").dropna(subset=["categories"]).copy()
    df["category"] = df["categories"].astype(str).str.strip()
    return df[df["category"] != ""]


def _to_side_rows(matches: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    a = matches[group_cols + ["model_a", "score_a", "eco_a_kwh"]].rename(
        columns={"model_a": "model_name", "score_a": "win_point", "eco_a_kwh": "eco_kwh"}
    )
    b = matches[group_cols + ["model_b", "score_a", "eco_b_kwh"]].rename(
        columns={"model_b": "model_name", "eco_b_kwh": "eco_kwh"}
    )
    b["win_point"] = 1.0 - b["score_a"]
    b = b.drop(columns=["score_a"])
    return pd.concat([a, b], ignore_index=True)


# ------------------------
# winrate + eco

def _aggregate_wr_eco(side: pd.DataFrame, group_cols: list[str], min_obs: int) -> pd.DataFrame:
    out = (
        side.groupby(group_cols + ["model_name"], dropna=False)
        .agg(
            n_obs=("win_point", "size"),
            win_rate=("win_point", "mean"),
            eco_kwh_mean=("eco_kwh", "mean"),
            eco_kwh_total=("eco_kwh", "sum"),
        )
        .reset_index()
    )
    out = out[out["n_obs"] >= min_obs].copy()
    out["win_rate"] = (out["win_rate"] * 100).round(2)
    out["eco_kwh_mean"] = out["eco_kwh_mean"].round(10)
    out["eco_kwh_total"] = out["eco_kwh_total"].round(10)
    return out


def compute_global_wr_eco(matches: pd.DataFrame, min_obs: int) -> pd.DataFrame:
    side = _to_side_rows(matches, group_cols=[])
    out = _aggregate_wr_eco(side, group_cols=[], min_obs=min_obs)
    return out.sort_values("win_rate", ascending=False)


def compute_category_wr_eco(matches: pd.DataFrame, min_obs: int) -> pd.DataFrame:
    by_cat = _explode_categories(matches)
    side = _to_side_rows(by_cat, group_cols=["category"])
    out = _aggregate_wr_eco(side, group_cols=["category"], min_obs=min_obs)
    return out.sort_values(["category", "win_rate"], ascending=[True, False])


# ------------------------
# bradley-terry

def _bt_single(matches: pd.DataFrame, min_obs: int, max_iter: int = 200, tol: float = 1e-6) -> pd.DataFrame:
    side = _to_side_rows(matches, group_cols=[])
    counts = side.groupby("model_name").size().rename("n_obs")
    keep = counts[counts >= min_obs].index

    m = matches[matches["model_a"].isin(keep) & matches["model_b"].isin(keep)].copy()
    if m.empty:
        return pd.DataFrame(columns=["model_name", "bt_raw", "bt_strength"])

    model_counts = pd.concat([m["model_a"], m["model_b"]]).value_counts()
    models = model_counts.index.tolist()
    idx = {name: i for i, name in enumerate(models)}
    n = len(models)

    wins = np.zeros((n, n), dtype=float)
    comps = np.zeros((n, n), dtype=float)

    for row in m.itertuples(index=False):
        i = idx[row.model_a]
        j = idx[row.model_b]
        s = float(row.score_a)
        wins[i, j] += s
        wins[j, i] += 1.0 - s
        comps[i, j] += 1.0
        comps[j, i] += 1.0

    w = wins.sum(axis=1)
    p = np.ones(n, dtype=float)

    for _ in range(max_iter):
        denom = np.zeros(n, dtype=float)
        for i in range(n):
            den = comps[i] / (p[i] + p)
            den[i] = 0.0
            denom[i] = den.sum()

        p_new = np.where(denom > 0, w / denom, p)
        p_new = np.clip(p_new, 1e-12, None)
        p_new /= p_new.mean()

        if np.max(np.abs(np.log(p_new) - np.log(p))) < tol:
            p = p_new
            break
        p = p_new

    return pd.DataFrame(
        {
            "model_name": models,
            "bt_raw": np.round(p, 6),
            "bt_strength": np.round(np.log(p), 4),
        }
    ).sort_values("bt_strength", ascending=False)


def compute_global_bt(matches: pd.DataFrame, min_obs: int) -> pd.DataFrame:
    return _bt_single(matches, min_obs=min_obs)


def compute_category_bt(matches: pd.DataFrame, min_obs: int) -> pd.DataFrame:
    by_cat = _explode_categories(matches)
    rows = []
    for cat, g in by_cat.groupby("category"):
        bt = _bt_single(g[["model_a", "model_b", "score_a", "eco_a_kwh", "eco_b_kwh"]], min_obs=min_obs)
        if bt.empty:
            continue
        bt.insert(0, "category", cat)
        rows.append(bt)

    if not rows:
        return pd.DataFrame(columns=["category", "model_name", "bt_raw", "bt_strength"])
    return pd.concat(rows, ignore_index=True)


# ------------------------
# fusion finale

def combine_metrics(wr_eco: pd.DataFrame, bt: pd.DataFrame, by_category: bool) -> pd.DataFrame:
    keys = ["category", "model_name"] if by_category else ["model_name"]
    out = wr_eco.merge(bt, on=keys, how="left")
    out["bt_raw"] = out["bt_raw"].fillna(0)
    out["bt_strength"] = out["bt_strength"].fillna(-999)
    return out
