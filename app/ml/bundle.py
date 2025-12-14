from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

DROP_COMMON = [
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
    "category",
    "subcategory",
]

LABEL_COLS = ["attack", "category", "subcategory"]


def _to_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _fill_median(df: pd.DataFrame) -> pd.DataFrame:
    return df.fillna(df.median(numeric_only=True))


def _drop_zero_var(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    zero_var_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    if zero_var_cols:
        df = df.drop(columns=zero_var_cols)
    return df


def _align_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    df = df.copy()
    for f in features:
        if f not in df.columns:
            df[f] = 0.0
    df = df[[f for f in features]]
    return df


@dataclass(frozen=True)
class XGBBundle:
    bin_model: XGBClassifier
    multi_model: XGBClassifier

    features_bin: List[str]
    features_multi: List[str]

    class_mapping: Dict[int, str]

    @staticmethod
    def load(
        xgb_bin_path: str,
        xgb_multi_path: str,
        class_mapping_path: str,
        features_bin_path: str,
        features_multi_path: str,
    ) -> "XGBBundle":
        bin_model = XGBClassifier()
        bin_model.load_model(xgb_bin_path)

        multi_model = XGBClassifier()
        multi_model.load_model(xgb_multi_path)

        with open(features_bin_path, "r", encoding="utf-8") as f:
            features_bin = json.load(f)

        with open(features_multi_path, "r", encoding="utf-8") as f:
            features_multi = json.load(f)

        with open(class_mapping_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            class_mapping: Dict[int, str] = {int(k): str(v) for k, v in raw.items()}

        return XGBBundle(
            bin_model=bin_model,
            multi_model=multi_model,
            features_bin=list(features_bin),
            features_multi=list(features_multi),
            class_mapping=class_mapping,
        )

    def _preprocess(self, df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.strip() for c in df.columns]

        # leakage: target-колонки нельзя использовать как фичи
        for col in LABEL_COLS:
            if col in df.columns:
                df = df.drop(columns=[col])

        to_drop = [c for c in DROP_COMMON if c in df.columns]
        if to_drop:
            df = df.drop(columns=to_drop)

        df = _to_numeric_df(df)
        df = _fill_median(df)
        df = _drop_zero_var(df)

        df = _align_features(df, features)
        return df

    def preprocess_binary(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._preprocess(df, self.features_bin)

    def preprocess_multi(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._preprocess(df, self.features_multi)

    def score_df(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Возвращает df_raw + столбцы:
          - pred_attack (0/1)
          - pred_attack_proba (float или NaN)
          - pred_class (str)
          - pred_class_proba (float или NaN)
        """
        if df_raw.shape[0] == 0:
            out = df_raw.copy()
            out["pred_attack"] = []
            out["pred_attack_proba"] = []
            out["pred_class"] = []
            out["pred_class_proba"] = []
            return out

        out = df_raw.copy()
        Xb = self.preprocess_binary(df_raw)

        pred_bin = self.bin_model.predict(Xb)
        pred_bin = np.asarray(pred_bin).astype(int)

        proba_bin = None
        try:
            pb = self.bin_model.predict_proba(Xb)
            if pb is not None and pb.shape[1] >= 2:
                proba_bin = pb[:, 1].astype(float)
        except Exception:
            proba_bin = None

        out["pred_attack"] = pred_bin
        out["pred_attack_proba"] = proba_bin if proba_bin is not None else np.nan

        out["pred_class"] = "benign"
        out["pred_class_proba"] = np.nan

        idx_attack = np.where(pred_bin == 1)[0]
        if idx_attack.size == 0:
            return out

        df_att = df_raw.iloc[idx_attack].copy()
        Xm = self.preprocess_multi(df_att)

        pred_multi = self.multi_model.predict(Xm)
        pred_multi = np.asarray(pred_multi).astype(int)

        proba_multi = None
        try:
            pm = self.multi_model.predict_proba(Xm)
            if pm is not None and pm.ndim == 2 and pm.shape[1] >= 1:
                proba_multi = pm.max(axis=1).astype(float)
        except Exception:
            proba_multi = None

        class_names = [self.class_mapping.get(int(c), str(int(c))) for c in pred_multi]

        out.loc[out.index[idx_attack], "pred_class"] = class_names
        if proba_multi is not None:
            out.loc[out.index[idx_attack], "pred_class_proba"] = proba_multi

        return out

    def predict_rows(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Продуктовый row-level output:
          - is_attack (0/1)
          - attack_type (benign / тип атаки)

        Важно: если во входном CSV случайно есть target-колонки,
        мы НЕ возвращаем их в scored CSV.
        """
        scored_internal = self.score_df(df_raw)

        out = df_raw.copy()
        for col in LABEL_COLS:
            if col in out.columns:
                out = out.drop(columns=[col])

        out["is_attack"] = scored_internal["pred_attack"].astype(int)
        out["attack_type"] = scored_internal["pred_class"].astype(str)
        return out

    def summary_from_scored(self, scored_df: pd.DataFrame) -> Tuple[int, int, float, str | None, float | None]:
        """
        total_rows, attack_rows, attack_ratio, top_class, top_class_share
        Поддерживает оба формата:
          - internal: pred_attack / pred_class
          - product:  is_attack / attack_type
        """
        total = int(scored_df.shape[0])
        if total == 0:
            return 0, 0, 0.0, None, None

        if "pred_attack" in scored_df.columns:
            attack_col = "pred_attack"
        elif "is_attack" in scored_df.columns:
            attack_col = "is_attack"
        else:
            raise ValueError("scored_df must contain pred_attack or is_attack")

        if "pred_class" in scored_df.columns:
            class_col = "pred_class"
        elif "attack_type" in scored_df.columns:
            class_col = "attack_type"
        else:
            raise ValueError("scored_df must contain pred_class or attack_type")

        pred_attack = scored_df[attack_col].astype(int).to_numpy()
        attack_rows = int(pred_attack.sum())
        attack_ratio = float(attack_rows / total) if total else 0.0

        if attack_rows == 0:
            return total, 0, 0.0, "benign", 1.0

        only_att = scored_df.loc[scored_df[attack_col].astype(int) == 1, class_col].astype(str)
        vc = only_att.value_counts()
        top_class = str(vc.index[0]) if len(vc) else None
        top_share = float(vc.iloc[0] / attack_rows) if top_class else None

        return total, attack_rows, attack_ratio, top_class, top_share
