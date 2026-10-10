import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    # Azure OpenAI credentials
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_MODEL_NAME: str = os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-oss-120b")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "Neo-Hackathon")

    # Hugging Face Embeddings Configuration
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", os.getenv("HF_TOKEN", ""))
    HUGGINGFACE_EMBEDDING_MODEL: str = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")

    # Database Path
    DB_PATH_ENV = os.getenv("DATABASE_PATH", "Neostats Hackathon AI Usecase/ridewise.db")
    DATABASE_PATH: Path = (BASE_DIR / DB_PATH_ENV).resolve() if not Path(DB_PATH_ENV).is_absolute() else Path(DB_PATH_ENV)

    # Policy documents directory
    POLICIES_DIR_ENV = os.getenv("POLICIES_DIR", "Neostats Hackathon AI Usecase")
    POLICIES_DIR: Path = (BASE_DIR / POLICIES_DIR_ENV).resolve() if not Path(POLICIES_DIR_ENV).is_absolute() else Path(POLICIES_DIR_ENV)

    # Server Settings
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8501"))

settings = Settings()
