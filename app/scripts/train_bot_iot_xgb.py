from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier


DROP_COLS_COMMON = [
    "pkSeqID",
    "stime",
    "ltime",
    "saddr",
    "daddr",
    "smac",
    "dmac",
    "soui",
    "doui",
    "sco",
    "dco",
    "seq",
    "subcategory",
]

TARGET_BIN = "attack"
TARGET_MULTI = "category"


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _fillna_median(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    med = df.median(numeric_only=True)
    return df.fillna(med)


def _drop_zero_var(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    zero_var = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    return df.drop(columns=zero_var, errors="ignore"), zero_var


def train_and_export(input_csv: Path, out_dir: Path, test_size: float = 0.2, seed: int = 42) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv)
    df.columns = [c.strip() for c in df.columns]

    # ---------- Binary model: attack vs normal ----------
    if TARGET_BIN not in df.columns:
        raise RuntimeError(f"Column '{TARGET_BIN}' not found in dataset")

    # бинарная цель: 0/1
    y_bin = df[TARGET_BIN].astype(int)

    drop_bin = list(DROP_COLS_COMMON) + ["category"]  # category не используем как признак
    X_bin = df.drop(columns=drop_bin + [TARGET_BIN], errors="ignore")

    X_bin = _coerce_numeric(X_bin)
    X_bin = _fillna_median(X_bin)
    X_bin, zero_var_bin = _drop_zero_var(X_bin)

    X_train, X_test, y_train, y_test = train_test_split(
        X_bin, y_bin, test_size=test_size, random_state=seed, stratify=y_bin
    )

    bin_model = XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        tree_method="hist",
        eval_metric="logloss",
        random_state=seed,
    )
    bin_model.fit(X_train, y_train)

    # ---------- Multiclass model: type of attack (only for attack rows) ----------
    if TARGET_MULTI not in df.columns:
        raise RuntimeError(f"Column '{TARGET_MULTI}' not found in dataset")

    df_attack = df[df[TARGET_BIN].astype(int) == 1].copy()
    if len(df_attack) == 0:
        raise RuntimeError("No attack rows found (attack == 1). Cannot train multiclass model.")

    le = LabelEncoder()
    y_multi = le.fit_transform(df_attack[TARGET_MULTI].astype(str))

    drop_multi = list(DROP_COLS_COMMON) + [TARGET_BIN, TARGET_MULTI, "category"]  # category — таргет, убираем
    # ВНИМАНИЕ: если в датасете есть отдельная колонка 'category' и мы её используем как таргет,
    # то выше drop_multi уже убирает её. Если таргет у тебя именно 'category', то всё ок.

    X_multi = df_attack.drop(columns=drop_multi, errors="ignore")

    X_multi = _coerce_numeric(X_multi)
    X_multi = _fillna_median(X_multi)
    X_multi, zero_var_multi = _drop_zero_var(X_multi)

    X_train_m, X_test_m, y_train_m, y_test_m = train_test_split(
        X_multi, y_multi, test_size=test_size, random_state=seed, stratify=y_multi
    )

    multi_model = XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        tree_method="hist",
        eval_metric="mlogloss",
        random_state=seed,
    )
    multi_model.fit(X_train_m, y_train_m)

    # ---------- Export artifacts ----------
    # модели
    (out_dir / "xgb_bin.json").write_bytes(b"")  # ensure file exists even if save_model fails early
    bin_model.save_model(str(out_dir / "xgb_bin.json"))
    multi_model.save_model(str(out_dir / "xgb_multi.json"))

    # маппинг классов multiclass: index -> label
    class_mapping = {int(i): cls for i, cls in enumerate(le.classes_)}
    (out_dir / "class_mapping.json").write_text(json.dumps(class_mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    # список фичей (важно для инференса, чтобы выровнять колонки)
    (out_dir / "features_bin.json").write_text(
        json.dumps(list(X_bin.columns), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "features_multi.json").write_text(
        json.dumps(list(X_multi.columns), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # мета-инфо (для отладки)
    meta = {
        "input_csv": str(input_csv),
        "rows_total": int(len(df)),
        "rows_attack": int(len(df_attack)),
        "features_bin": int(len(X_bin.columns)),
        "features_multi": int(len(X_multi.columns)),
        "zero_var_dropped_bin": zero_var_bin,
        "zero_var_dropped_multi": zero_var_multi,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Saved artifacts to:", out_dir)
    print(" - xgb_bin.json")
    print(" - xgb_multi.json")
    print(" - class_mapping.json")
    print(" - features_bin.json")
    print(" - features_multi.json")
    print(" - meta.json")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to BoT-IoT CSV (e.g. bot_iot_small.csv)")
    p.add_argument("--out", default="/data/models", help="Output dir for model artifacts")
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    train_and_export(Path(args.input), Path(args.out), test_size=args.test_size, seed=args.seed)


if __name__ == "__main__":
    main()
