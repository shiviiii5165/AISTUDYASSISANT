from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Resolve the .env path relative to the root directory
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_root_dir = os.path.dirname(_backend_dir)
_env_file = os.path.join(_root_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "LearnByGenie API"
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
    ANTHROPIC_API_KEY: str = ""
    
    # Centralized Production Model Identifiers
    GROQ_PRIMARY_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODELS: str = "qwen/qwen3.8-27b,openai/gpt-oss-20b,qwen/qwen3.6-27b"
    GEMINI_PRIMARY_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-2.5-flash"
    OPENROUTER_PRIMARY_MODEL: str = "openai/gpt-4o"
    
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
    ALLOWED_ORIGINS: str = "http://localhost:5173,https://prepmind.vercel.app,https://teachgenie.online,https://www.teachgenie.online,https://learnbygenie.com,https://www.learnbygenie.com,https://learnbygenie.online,https://www.learnbygenie.online,https://aistudyassisant.onrender.com"

    # Lesson Planner Feature Flags & Integrations
    LESSON_PLANNER_YOUTUBE_ENABLED: bool = True
    LESSON_PLANNER_MATERIALS_ENABLED: bool = True
    YOUTUBE_API_KEY: str = ""
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    CROSSREF_MAILTO: str = "contact@learnbygenie.com"
    TAVILY_API_KEY: str = ""

    # Legacy & Dual-read Environment Variables
    LEARNBYGENIE_MODE: str | None = None
    TEACHGENIE_MODE: str = "PRODUCTION"
    LEARNBYGENIE_ALLOW_DEV_AUTH: str | None = None
    TEACHGENIE_ALLOW_DEV_AUTH: str = ""

    # Lesson Planner VNext Production-Safe Feature Flags (Default False)
    LESSON_VNEXT_ENABLED: bool = False
    LESSON_RESOURCE_INTELLIGENCE_ENABLED: bool = False
    LESSON_YOUTUBE_SEGMENTS_ENABLED: bool = False
    LESSON_ACADEMIC_ENGINE_ENABLED: bool = False
    LESSON_CODING_RESOURCES_ENABLED: bool = False
    LESSON_ADAPTIVE_ENGINE_ENABLED: bool = False
    LESSON_AUTO_STUDENT_ADAPTATION_ENABLED: bool = False
    LESSON_CLASS_ADAPTATION_ENABLED: bool = False
    LESSON_CROSS_FEATURE_CONTEXT_ENABLED: bool = False
    LESSON_OUTCOME_RANKING_ENABLED: bool = False

    ENVIRONMENT: str = "development"

    # Presentation Composition Renderer Feature Flag (Phase 3.2E - Default False)
    PRESENTATION_COMPOSITION_RENDERER_ENABLED: bool = False

    # Presentation Native Chart & Diagram Intelligence Flag (Phase 3.3 - Default False, strictly opt-in)
    PRESENTATION_CHART_DIAGRAM_INTELLIGENCE_ENABLED: bool = False

    # Presentation Image Intelligence Flag (Phase 3.4 - Default False, strictly opt-in)
    # Requires PRESENTATION_COMPOSITION_RENDERER_ENABLED=True to be active.
    PRESENTATION_IMAGE_INTELLIGENCE_ENABLED: bool = False

    # Presentation Rendered Visual QA & Targeted Repair Flag (Phase 3.5 - Default False, strictly opt-in)
    # Requires PRESENTATION_COMPOSITION_RENDERER_ENABLED=True to be active.
    PRESENTATION_RENDERED_VISUAL_QA_ENABLED: bool = False

    # Source Reading MVP Feature Flags (Default False — strictly opt-in)
    LIBRARIAN_SOURCE_EXTRACTION_ENABLED: bool = False
    LIBRARIAN_SOURCE_EXTRACTION_CANARY_USERS: str = ""  # Comma-separated user IDs or test accounts
    LIBRARIAN_SOURCE_EXTRACTION_CANARY_ENVIRONMENTS: str = "staging,internal,canary"

    # Live Quiz VNext Scale & Free-Tier Optimization Flag (§18)
    LIVE_QUIZ_FREE_TIER_MODE: bool = True


    def is_source_extraction_canary_active(self, user_id: str | None = None) -> bool:
        """
        Determines whether source extraction is active for this request.
        Stays False by default. Enables only if:
        1. Globally enabled (LIBRARIAN_SOURCE_EXTRACTION_ENABLED = True), OR
        2. user_id is explicitly listed in LIBRARIAN_SOURCE_EXTRACTION_CANARY_USERS, OR
        3. ENVIRONMENT is in LIBRARIAN_SOURCE_EXTRACTION_CANARY_ENVIRONMENTS.
        """
        if self.LIBRARIAN_SOURCE_EXTRACTION_ENABLED:
            return True
        if user_id and self.LIBRARIAN_SOURCE_EXTRACTION_CANARY_USERS:
            allowed_users = {u.strip().lower() for u in self.LIBRARIAN_SOURCE_EXTRACTION_CANARY_USERS.split(",") if u.strip()}
            if str(user_id).strip().lower() in allowed_users:
                return True
        if self.ENVIRONMENT and self.LIBRARIAN_SOURCE_EXTRACTION_CANARY_ENVIRONMENTS:
            allowed_envs = {e.strip().lower() for e in self.LIBRARIAN_SOURCE_EXTRACTION_CANARY_ENVIRONMENTS.split(",") if e.strip()}
            if self.ENVIRONMENT.strip().lower() in allowed_envs and user_id is not None:
                return True
        return False

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

