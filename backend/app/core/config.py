from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Resolve the .env path relative to the backend directory, not the cwd
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_env_file = os.path.join(_backend_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "TeachGenie API"
    VERSION: str = "1.0.0"
    
    # Supabase config
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # LLM Config
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    ANTHROPIC_API_KEY: str = ""
    
    # AWS Bedrock (for Claude Vision OCR - Optional now)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-west-2"
    
    
    # Cashfree Config
    CASHFREE_APP_ID: str
    CASHFREE_SECRET_KEY: str
    

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,https://prepmind.vercel.app,https://teachgenie.online,https://www.teachgenie.online"

    model_config = SettingsConfigDict(
        env_file=_env_file if os.path.exists(_env_file) else None,
        env_file_encoding="utf-8",
    )

settings = Settings()

