"""Leakage-safe validation, experiment tracking, and model fitting for SHM."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.shm.feature_extraction import feature_columns_for_groups


RANDOM_STATE = 42
N_SPLITS = 5
N_REPEATS = 10
MODEL_NAMES = ("dummy_median", "ridge", "extra_trees")


@dataclass(frozen=True)
class EvaluationResult:
    experiment_id: str
    feature_groups: str
    feature_count: int
    model: str
    target_transform: str
    hyperparameters: str
    CV_MAPE_mean: float
    CV_MAPE_std: float
    CV_official_score: float
    OOF_MAPE: float
    OOF_official_score: float
    median_APE: float
    P90_APE: float
    max_APE: float
    MAE: float
    RMSE: float
    R2: float
    mean_signed_percentage_error: float
    training_MAPE: float
    notes: str


def make_model(name: str):
    """Create one conservative baseline estimator."""
    if name == "dummy_median":
        return DummyRegressor(strategy="median")
    if name == "ridge":
        return Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=10.0))])
    if name == "extra_trees":
        return ExtraTreesRegressor(
            n_estimators=400,
            max_features=0.7,
            min_samples_leaf=2,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
    raise ValueError(f"Unknown SHM model: {name}")


def official_score(mape: float) -> float:
    """PS3 score from fractional MAPE (0.10 means 10%, not 10)."""
    if not np.isfinite(mape) or mape < 0:
        raise ValueError("MAPE must be a finite nonnegative fraction.")
    return max(0.0, 1.0 - float(mape))


def percentage_errors(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    if not np.isfinite(y_true).all() or not np.isfinite(y_pred).all():
        raise ValueError("SHM metric inputs must be finite.")
    if np.any(y_true <= 0):
        raise ValueError("MAPE requires strictly positive SHM targets.")
    return np.abs(y_true - y_pred) / np.abs(y_true)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    ape = percentage_errors(y_true, y_pred)
    return {
        "MAPE": float(np.mean(ape)),
        "official_score": official_score(float(np.mean(ape))),
        "median_APE": float(np.median(ape)),
        "P90_APE": float(np.percentile(ape, 90)),
        "max_APE": float(np.max(ape)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "mean_signed_percentage_error": float(np.mean((y_pred - y_true) / np.abs(y_true))),
    }


def evaluate_candidate(
    table: pd.DataFrame,
    feature_groups: Sequence[str],
    model_name: str,
    experiment_id: str,
) -> tuple[EvaluationResult, pd.DataFrame]:
    """Evaluate one candidate on fixed repeated folds and average OOF repeats."""
    feature_names = feature_columns_for_groups(table, feature_groups)
    if not feature_names:
        raise ValueError(f"No columns found for feature groups {feature_groups}")
    X = table[feature_names].to_numpy(dtype=float)
    y = table["target"].to_numpy(dtype=float)
    splitter = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    prediction_sums = np.zeros_like(y)
    prediction_counts = np.zeros_like(y, dtype=int)
    fold_mapes: list[float] = []

    for train_indices, validation_indices in splitter.split(X):
        estimator = clone(make_model(model_name))
        estimator.fit(X[train_indices], y[train_indices])
        predictions = np.maximum(estimator.predict(X[validation_indices]), 0.0)
        fold_mapes.append(float(np.mean(percentage_errors(y[validation_indices], predictions))))
        prediction_sums[validation_indices] += predictions
        prediction_counts[validation_indices] += 1

    if not np.all(prediction_counts == N_REPEATS):
        raise RuntimeError("Repeated CV did not produce the expected OOF prediction count.")
    oof_predictions = prediction_sums / prediction_counts
    oof_metrics = _metrics(y, oof_predictions)

    fitted = make_model(model_name).fit(X, y)
    train_predictions = np.maximum(fitted.predict(X), 0.0)
    result = EvaluationResult(
        experiment_id=experiment_id,
        feature_groups="+".join(feature_groups),
        feature_count=len(feature_names),
        model=model_name,
        target_transform="raw",
        hyperparameters=json.dumps(make_model(model_name).get_params(deep=False), default=str, sort_keys=True),
        CV_MAPE_mean=float(np.mean(fold_mapes)),
        CV_MAPE_std=float(np.std(fold_mapes, ddof=1)),
        CV_official_score=official_score(float(np.mean(fold_mapes))),
        OOF_MAPE=oof_metrics["MAPE"],
        OOF_official_score=oof_metrics["official_score"],
        median_APE=oof_metrics["median_APE"],
        P90_APE=oof_metrics["P90_APE"],
        max_APE=oof_metrics["max_APE"],
        MAE=oof_metrics["MAE"],
        RMSE=oof_metrics["RMSE"],
        R2=oof_metrics["R2"],
        mean_signed_percentage_error=oof_metrics["mean_signed_percentage_error"],
        training_MAPE=float(np.mean(percentage_errors(y, train_predictions))),
        notes="RepeatedKFold(5 splits, 10 repeats, random_state=42); averaged OOF predictions",
    )
    oof = pd.DataFrame(
        {
            "file_id": table["file_id"],
            "actual": y,
            "OOF_prediction": oof_predictions,
            "absolute_error": np.abs(y - oof_predictions),
            "percentage_error": percentage_errors(y, oof_predictions),
        }
    ).sort_values("percentage_error", ascending=False)
    return result, oof


def run_baseline_experiments(table: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Run the required progressive Phase 1 ablation on identical CV splits."""
    available_groups = []
    if any(column.startswith("stats__") for column in table):
        available_groups.append(("statistics",))
    if any(column.startswith("dist__") for column in table):
        available_groups.append(("statistics", "distribution"))
    if not available_groups:
        raise ValueError("Feature table has no supported Phase 1 features.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results: list[EvaluationResult] = []
    oof_tables: dict[str, pd.DataFrame] = {}
    for group_index, groups in enumerate(available_groups, start=1):
        for model_index, model_name in enumerate(MODEL_NAMES, start=1):
            experiment_id = f"{timestamp}_p1_{group_index}_{model_index}"
            result, oof = evaluate_candidate(table, groups, model_name, experiment_id)
            results.append(result)
            oof_tables[experiment_id] = oof
    return pd.DataFrame([asdict(result) for result in results]), oof_tables


def append_experiment_results(results: pd.DataFrame, path: str | Path) -> None:
    """Append experiments without overwriting prior runs."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        previous = pd.read_csv(destination)
        results = pd.concat([previous, results], ignore_index=True)
    results.to_csv(destination, index=False)


def fit_and_save_best(
    table: pd.DataFrame,
    results: pd.DataFrame,
    artifact_dir: str | Path,
) -> dict[str, object]:
    """Refit the lowest-mean-CV-MAPE candidate on all labelled files."""
    best = results.sort_values(["CV_MAPE_mean", "CV_MAPE_std"]).iloc[0]
    groups = tuple(str(best["feature_groups"]).split("+"))
    feature_names = feature_columns_for_groups(table, groups)
    estimator = make_model(str(best["model"]))
    estimator.fit(table[feature_names].to_numpy(dtype=float), table["target"].to_numpy(dtype=float))
    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)
    bundle = {
        "artifact_version": 1,
        "model": estimator,
        "model_name": str(best["model"]),
        "feature_groups": groups,
        "feature_names": feature_names,
        "target_transform": "raw",
        "random_state": RANDOM_STATE,
    }
    joblib.dump(bundle, artifact_path / "model.joblib")
    metadata = {
        key: (value.item() if isinstance(value, np.generic) else value)
        for key, value in best.to_dict().items()
    }
    metadata.update(
        {
            "artifact_version": 1,
            "feature_names": feature_names,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    (artifact_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return metadata
