import os


_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-prod")
    DATABASE = os.environ.get("DATABASE", os.path.join(_BASE_DIR, "db", "actionhub.db"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False
    # P1 — Asset versioning (bump on each deploy)
    ASSET_VERSION = "3.42"
    # P2 — Response compression
    COMPRESS_MIMETYPES = [
        "text/html",
        "text/css",
        "application/javascript",
        "application/json",
    ]
    COMPRESS_MIN_SIZE = 2000   # skip compressing small responses to save CPU
    COMPRESS_LEVEL = 1         # fastest gzip level — critical on 2-core VM
    # SEP-1 — JWT Auth (dual-mode with session)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-dev-key-change-in-prod")
    JWT_ACCESS_EXPIRY = 14400    # 4 hours in seconds
    JWT_REFRESH_EXPIRY = 604800  # 7 days in seconds


class ProductionConfig(Config):
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    DATABASE = os.environ.get("DATABASE", r"C:\ActionHub\data\actionhub.db")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE = ":memory:"


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
