import json
from pathlib import Path

from flask import request


def _load_catalog(lang: str) -> dict:
    lang_code = "zh" if lang == "zh" else "en"
    base_dir = Path(__file__).resolve().parent
    file_path = base_dir / f"{lang_code}.json"
    with open(file_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_language() -> str:
    user = getattr(request, "_current_user", None)
    if isinstance(user, dict) and user.get("lang") == "zh":
        return "zh"
    lang_hint = request.args.get("lang") or request.headers.get("X-Language") or request.headers.get("Accept-Language", "")
    return "zh" if str(lang_hint).lower().startswith("zh") else "en"


def set_language(lang: str) -> str:
    normalized = "zh" if str(lang).lower().startswith("zh") else "en"
    user = getattr(request, "_current_user", None)
    if isinstance(user, dict):
        user["lang"] = normalized
        # Persist to DB so preference survives session expiry
        try:
            from actionhub.middleware.db import get_db
            db = get_db()
            db.execute(
                "UPDATE t_user SET usr_lang = ? WHERE usr_id = ?",
                (normalized, user["id"]),
            )
            db.commit()
        except Exception:
            pass  # never break the UI over a lang-save failure
    return normalized


def t(key: str) -> str:
    catalog = _load_catalog(get_language())
    return str(catalog.get(key, key))


def init_i18n(app) -> None:
    @app.context_processor
    def i18n_helpers():
        return {
            "t": t,
            "_": t,
            "current_lang": get_language(),
        }
