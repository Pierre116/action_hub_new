import json
from pathlib import Path

from flask import Blueprint, jsonify, abort

i18n_bp = Blueprint("i18n", __name__, url_prefix="/api/i18n")

# i18n files are in actionhub/i18n/ directory
I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"


@i18n_bp.get("/<lang>")
def get_translations(lang: str):
    """Return i18n JSON file for the specified language.
    
    Args:
        lang: Language code (e.g., 'en', 'zh')
    
    Returns:
        JSON content of the translation file
    """
    allowed_langs = ["en", "zh"]
    if lang not in allowed_langs:
        return jsonify({"error": {"code": "INVALID_LANGUAGE", "message": f"Language {lang} not supported"}}), 400
    
    file_path = I18N_DIR / f"{lang}.json"
    
    if not file_path.exists():
        return jsonify({"error": {"code": "NOT_FOUND", "message": f"Translation file for {lang} not found"}}), 404
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
        return jsonify(translations)
    except json.JSONDecodeError:
        return jsonify({"error": {"code": "PARSE_ERROR", "message": "Invalid JSON in translation file"}}), 500