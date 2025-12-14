from __future__ import annotations

import os
import shutil
from typing import Iterable, List


def _is_dir_writable(path: str) -> bool:
    try:
        testfile = os.path.join(path, ".write_test")
        with open(testfile, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(testfile)
        return True
    except Exception:
        return False


def ensure_models_present(
    model_dir: str,
    required_paths: Iterable[str],
    source_dir: str = "/app/models",
) -> None:
    """
    Гарантирует, что файлы моделей доступны по путям required_paths.
    Если файла нет в model_dir, пробует скопировать его из source_dir в model_dir.

    Это нужно, потому что named volume /data/models при первом запуске пустой
    и перекрывает содержимое образа.
    """
    os.makedirs(model_dir, exist_ok=True)

    required_paths = list(required_paths)
    missing: List[str] = [p for p in required_paths if not os.path.exists(p)]

    if not missing:
        return

    # Если volume не writable, то копирование не получится.
    writable = _is_dir_writable(model_dir)

    copied_any = False
    for dst in missing:
        filename = os.path.basename(dst)
        src = os.path.join(source_dir, filename)

        # копируем только если исходник существует
        if os.path.exists(src) and writable:
            shutil.copy2(src, dst)
            copied_any = True

    # повторная проверка
    still_missing = [p for p in required_paths if not os.path.exists(p)]
    if still_missing:
        msg = (
            "Model files are missing in /data/models.\n"
            f"model_dir='{model_dir}' (writable={writable})\n"
            f"source_dir='{source_dir}'\n"
            "Missing:\n  - " + "\n  - ".join(still_missing) + "\n\n"
            "How to fix:\n"
            "1) Ensure the repository contains ./models/* (xgb_bin.json, xgb_multi.json, class_mapping.json, features_*.json)\n"
            "2) Rebuild and start containers: docker compose up --build\n"
            "3) If you use bind-mount for /data/models as read-only, make sure files already exist there.\n"
        )
        raise FileNotFoundError(msg)

    if copied_any:
        print(f"[models] Seeded models into '{model_dir}' from '{source_dir}'.")
