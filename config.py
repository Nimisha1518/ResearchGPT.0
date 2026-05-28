import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_research_gpt_123!")
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # Path settings
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "uploads"))
    CHROMA_DB_DIR = os.path.join(BASE_DIR, os.getenv("CHROMA_DB_DIR", "data/chromadb"))
    
    # Flask settings
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = ENV == "development"

# Ensure directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.CHROMA_DB_DIR, exist_ok=True)
