from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
from ecologits import EcoLogits
from openai import OpenAI


# ------------------------
# utilitaires simples

DEFAULT_PROMPT = (
    "Reponds en 6 points tres concrets pour aider une personne a prioriser "
    "des actions climate/energie a impact."
)


def _get_attr_or_key(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _extract_energy(impacts: Any) -> tuple[float | None, float | None, float | None]:
    energy = _get_attr_or_key(impacts, "energy")
    if energy is None:
        return None, None, None

    value = _get_attr_or_key(energy, "value")
    minimum = _get_attr_or_key(energy, "min")
    maximum = _get_attr_or_key(energy, "max")

    return (
        float(value) if value is not None else None,
        float(minimum) if minimum is not None else None,
        float(maximum) if maximum is not None else None,
    )


def _to_jsonable(obj: Any) -> str:
    if obj is None:
        return ""
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), ensure_ascii=True)
    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=True)
    return str(obj)


def _load_models(votes_path: Path) -> list[str]:
    votes = pq.read_table(votes_path, columns=["model_a_name", "model_b_name"]).to_pandas()
    models = pd.concat([votes["model_a_name"], votes["model_b_name"]], ignore_index=True)
    models = models.dropna().astype(str).str.strip()
    models = models[models != ""].drop_duplicates().sort_values()
    return models.tolist()


# ------------------------
# pipeline principal

def main() -> None:
    parser = argparse.ArgumentParser(description="Mesure energie modele par modele via API + EcoLogits.")
    parser.add_argument("--votes-path", default="Data/votes.parquet")
    parser.add_argument("--output-path", default="Data/model_energy_api.csv")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--runs-per-model", type=int, default=1)
    parser.add_argument("--max-models", type=int, default=0, help="0 = tous les modeles")
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--provider", default="openai", help="Provider EcoLogits (ex: openai, anthropic, mistralai)")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--base-url", default="", help="URL API compatible OpenAI (optionnel)")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--resume", action="store_true", help="Ignore les lignes deja en succes")
    args = parser.parse_args()

    votes_path = Path(args.votes_path)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not votes_path.exists():
        raise FileNotFoundError(f"votes parquet introuvable: {votes_path}")

    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(f"Cle API manquante: export {args.api_key_env}=...")

    # ------------------------
    # EcoLogits s'accroche au SDK fournisseur
    EcoLogits.init(providers=[args.provider])

    client_kwargs = {"api_key": api_key}
    if args.base_url:
        client_kwargs["base_url"] = args.base_url
    client = OpenAI(**client_kwargs)

    models = _load_models(votes_path)
    if args.max_models > 0:
        models = models[: args.max_models]

    done = set()
    if args.resume and output_path.exists():
        old = pd.read_csv(output_path)
        ok = old[old["status"] == "ok"][["model_name", "run_id"]].dropna()
        done = set(zip(ok["model_name"].astype(str), ok["run_id"].astype(int)))

    rows: list[dict[str, Any]] = []

    print(f"Modeles a tester: {len(models)}")
    print(f"Sortie: {output_path}")

    for i, model in enumerate(models, start=1):
        print(f"[{i}/{len(models)}] {model}")
        for run_id in range(1, args.runs_per_model + 1):
            if (model, run_id) in done:
                continue

            row: dict[str, Any] = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "model_name": model,
                "run_id": run_id,
                "prompt": args.prompt,
                "status": "error",
                "error": "",
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "energy_kwh": None,
                "energy_min_kwh": None,
                "energy_max_kwh": None,
                "raw_impacts": "",
            }

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": args.prompt}],
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                )

                usage = _get_attr_or_key(response, "usage")
                row["prompt_tokens"] = _get_attr_or_key(usage, "prompt_tokens")
                row["completion_tokens"] = _get_attr_or_key(usage, "completion_tokens")
                row["total_tokens"] = _get_attr_or_key(usage, "total_tokens")

                impacts = _get_attr_or_key(response, "impacts")
                kwh, kwh_min, kwh_max = _extract_energy(impacts)
                row["energy_kwh"] = kwh
                row["energy_min_kwh"] = kwh_min
                row["energy_max_kwh"] = kwh_max
                row["raw_impacts"] = _to_jsonable(impacts)
                row["status"] = "ok"

            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)

            rows.append(row)
            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

    out_df = pd.DataFrame(rows)

    if output_path.exists():
        previous = pd.read_csv(output_path)
        out_df = pd.concat([previous, out_df], ignore_index=True)

    out_df.to_csv(output_path, index=False)
    print("Termine.")
    print(f"Lignes enregistrees: {len(out_df)}")
    print(f"Succes: {int((out_df['status'] == 'ok').sum())}")
    print(f"Erreurs: {int((out_df['status'] == 'error').sum())}")


if __name__ == "__main__":
    main()
