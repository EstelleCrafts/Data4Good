from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ALLOWED_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9._:@/+\\-]{1,120}$")


def normalize_model_name(s: str) -> str:
    return str(s).strip().lower()


def is_clean_model_name(s: str) -> bool:
    if not s or s == "nan":
        return False
    return bool(ALLOWED_MODEL_RE.fullmatch(s))


def load_energy_rows_from_conversations(path: Path) -> pd.DataFrame:
    cols = ["model_a_name", "model_b_name", "total_conv_a_kwh", "total_conv_b_kwh"]
    df = pq.read_table(path, columns=cols).to_pandas()
    a = df[["model_a_name", "total_conv_a_kwh"]].rename(
        columns={"model_a_name": "model_name", "total_conv_a_kwh": "energy_kwh"}
    )
    b = df[["model_b_name", "total_conv_b_kwh"]].rename(
        columns={"model_b_name": "model_name", "total_conv_b_kwh": "energy_kwh"}
    )
    return pd.concat([a, b], ignore_index=True)


def load_energy_rows_from_api_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = ["model_name", "energy_kwh", "status"]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans {path}: {missing}")
    return df[df["status"] == "ok"][["model_name", "energy_kwh"]].copy()


def build_summary(rows: pd.DataFrame, min_obs: int) -> pd.DataFrame:
    out = rows.copy()
    out["model_name"] = out["model_name"].map(normalize_model_name)
    out = out[out["model_name"].map(is_clean_model_name)]
    out["energy_kwh"] = pd.to_numeric(out["energy_kwh"], errors="coerce")
    out = out.dropna(subset=["energy_kwh"])

    summary = (
        out.groupby("model_name", as_index=False)
        .agg(
            n_obs=("energy_kwh", "size"),
            energy_kwh_total=("energy_kwh", "sum"),
            energy_kwh_mean=("energy_kwh", "mean"),
            energy_kwh_median=("energy_kwh", "median"),
            energy_kwh_p90=("energy_kwh", lambda s: s.quantile(0.90)),
        )
        .sort_values("energy_kwh_mean", ascending=True)
    )

    if min_obs > 1:
        summary = summary[summary["n_obs"] >= min_obs].copy()

    num_cols = ["energy_kwh_total", "energy_kwh_mean", "energy_kwh_median", "energy_kwh_p90"]
    summary[num_cols] = summary[num_cols].round(12)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Construit Data/model_energy_summary.csv avec noms propres.")
    parser.add_argument("--api-csv", default="Data/model_energy_api.csv")
    parser.add_argument("--conversations", default="Data/conversations.parquet")
    parser.add_argument("--out", default="Data/model_energy_summary.csv")
    parser.add_argument("--min-obs", type=int, default=1)
    args = parser.parse_args()

    api_csv = Path(args.api_csv)
    conversations = Path(args.conversations)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if api_csv.exists():
        rows = load_energy_rows_from_api_csv(api_csv)
        source = str(api_csv)
    elif conversations.exists():
        rows = load_energy_rows_from_conversations(conversations)
        source = str(conversations)
    else:
        raise FileNotFoundError("Aucune source trouvée (ni API CSV ni conversations parquet).")

    summary = build_summary(rows, min_obs=args.min_obs)
    summary.to_csv(out, index=False)

    print(f"source: {source}")
    print(f"saved: {out}")
    print(f"rows: {len(summary)}")
    if not summary.empty:
        print(summary.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
