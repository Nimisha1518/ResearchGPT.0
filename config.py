import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BaseConfig:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_research_gpt_123!")
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # Path settings
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "uploads"))
    CHROMA_DB_DIR = os.path.join(BASE_DIR, os.getenv("CHROMA_DB_DIR", "data/chromadb"))

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'data', 'researchgpt.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload safety
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 25 * 1024 * 1024))

    # Provider selection
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
    VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "chroma").lower()
    QUEUE_BACKEND = os.getenv("QUEUE_BACKEND", "sync").lower()

    # S3-compatible object storage
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION = os.getenv("AWS_REGION", "")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

    # Pinecone vector database
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "")

    # Redis/RQ queue
    REDIS_URL = os.getenv("REDIS_URL", "")


class DevelopmentConfig(BaseConfig):
    ENV = "development"
    DEBUG = True


class ProductionConfig(BaseConfig):
    ENV = "production"
    DEBUG = False
    # Secret key validation happens in get_config() below, not at class-body time,
    # so importing this module in dev/test doesn't explode.


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        if not os.getenv("FLASK_SECRET_KEY"):
            raise RuntimeError(
                "FLASK_SECRET_KEY must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return ProductionConfig
    if env == "testing":
        return TestingConfig
    return DevelopmentConfig


Config = get_config()

# Ensure directories exist — only create what the chosen backend needs
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(Config.BASE_DIR, "data"), exist_ok=True)

if Config.VECTOR_BACKEND == "chroma":
    os.makedirs(Config.CHROMA_DB_DIR, exist_ok=True)
