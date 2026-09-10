from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Resolve the .env path relative to the root directory
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_root_dir = os.path.dirname(_backend_dir)
_env_file = os.path.join(_root_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "TeachGenie API"
    VERSION: str = "1.0.0"
    
    # Supabase config
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # LLM Config
    GEMINI_API_KEY: str
    GEMINI_IMAGE_API_KEY: str = ""
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    CLOUDFLARE_API_TOKEN: str = ""
    CLOUDFLARE_ACCOUNT_ID: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Stock Photo API Keys (single-key legacy fields)
    PEXELS_API_KEY: str = ""
    PIXABAY_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""
    UNSPLASH_SECRET_KEY: str = ""

    # Stock Photo Multi-Key Pools (comma-separated, for health-based routing)
    PEXELS_API_KEYS: str = ""
    PIXABAY_API_KEYS: str = ""
    UNSPLASH_ACCESS_KEYS: str = ""
    
    # Optional Multi-Key Pools (comma-separated or specific indexed keys)
    GEMINI_API_KEYS: str = ""
    GROQ_API_KEYS: str = ""
    OPENROUTER_API_KEYS: str = ""
    CEREBRAS_API_KEYS: str = ""
    
    # AWS Bedrock (for Claude Vision OCR - Optional now)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-west-2"
    
    
    # Cashfree Config
    CASHFREE_APP_ID: str
    CASHFREE_SECRET_KEY: str
    

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,https://prepmind.vercel.app,https://teachgenie.online,https://www.teachgenie.online,https://aistudyassisant.onrender.com"

    # Lesson Planner Feature Flags & Integrations
    LESSON_PLANNER_YOUTUBE_ENABLED: bool = True
    LESSON_PLANNER_MATERIALS_ENABLED: bool = True
    YOUTUBE_API_KEY: str = ""

    @property
    def lesson_planner_youtube_enabled(self) -> bool:
        return self.LESSON_PLANNER_YOUTUBE_ENABLED

    @property
    def lesson_planner_materials_enabled(self) -> bool:
        return self.LESSON_PLANNER_MATERIALS_ENABLED

    model_config = SettingsConfigDict(
        env_file=_env_file if os.path.exists(_env_file) else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

