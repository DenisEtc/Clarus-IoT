from __future__ import annotations

from typing import Iterable, Optional, Tuple

import pandas as pd


def _guess_sep_from_header(header: str) -> Optional[str]:
    if ";" in header and header.count(";") >= 2:
        return ";"
    if "\t" in header and header.count("\t") >= 2:
        return "\t"
    return None


def read_csv_robust(
    path: str,
    expected_columns: Optional[Iterable[str]] = None,
) -> Tuple[pd.DataFrame, str]:
    """
    Robust CSV reader with separator auto-detection.

    Returns: (df, used_separator)

    It tries:
      1) default pandas read_csv (comma)
      2) if looks like "one column header contains ; or \\t" -> reread with that sep
      3) if expected_columns provided: choose sep that maximizes intersection with expected columns
         among [",", ";", "\\t"].

    This fixes the common case when CSV is actually ';' separated.
    """

    # --- Try default first ---
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    used_sep = ","

    # Case A: parsed into one column, but header suggests delimiter
    if df.shape[1] == 1 and len(df.columns) == 1:
        header = str(df.columns[0])
        sep = _guess_sep_from_header(header)
        if sep:
            df = pd.read_csv(path, sep=sep)
            df.columns = [c.strip() for c in df.columns]
            return df, sep

    # Case B: expected columns are known -> maximize overlap
    if expected_columns is not None:
        expected = set(str(c).strip() for c in expected_columns)

        def overlap(d: pd.DataFrame) -> int:
            cols = set(str(c).strip() for c in d.columns)
            return len(cols & expected)

        best_df = df
        best_sep = used_sep
        best_score = overlap(df)

        for sep in [";", "\t"]:
            try:
                d = pd.read_csv(path, sep=sep)
                d.columns = [c.strip() for c in d.columns]
                sc = overlap(d)
                if sc > best_score:
                    best_score = sc
                    best_df = d
                    best_sep = sep
            except Exception:
                continue

        return best_df, best_sep

    return df, used_sep
