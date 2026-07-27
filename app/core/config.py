import os
import secrets
import warnings


class Settings:
    """
    Application configuration, read from environment variables.

    Previously LLM_PROVIDER/LLM_MODEL/OLLAMA_BASE_URL were read via
    inline os.environ.get() calls inside main.py's provider factory -
    fine for 3 variables, but it doesn't scale, and it's not obvious
    what's configurable without reading through endpoint code. This
    class is the one place that knows about env vars; everything else
    (main.py, answer_service.py) depends on a Settings instance instead.

    Instantiate fresh (Settings()) rather than relying only on the
    module-level singleton below when a test needs specific env values -
    each instance re-reads os.environ at construction time.
    """

    def __init__(self):
        # Provider selection
        self.llm_provider = os.environ.get("LLM_PROVIDER", "fake").lower()
        self.llm_model = os.environ.get("LLM_MODEL", "qwen3:1.7b")
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

        # Resilience: timeout and retry behavior for provider calls
        self.llm_timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
        self.llm_max_retries = int(os.environ.get("LLM_MAX_RETRIES", "1"))
        
        # Chunking: max chars per chunk, and overlap carried into the next
        # chunk (see chunking_service.py for how these are applied).
        self.chunk_size = int(os.environ.get("CHUNK_SIZE", "800"))
        self.chunk_overlap = int(os.environ.get("CHUNK_OVERLAP", "100"))

        if self.chunk_size <= 0:
            raise ValueError(f"CHUNK_SIZE must be > 0, got {self.chunk_size}")
        if self.chunk_overlap < 0:
            raise ValueError(f"CHUNK_OVERLAP must be >= 0, got {self.chunk_overlap}")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.chunk_overlap}) must be < CHUNK_SIZE ({self.chunk_size})"
            )

        # Auth: single hardcoded user via env vars, not a full user system.
        # See README for how to generate APP_PASSWORD_HASH.
        self.app_username = os.environ.get("APP_USERNAME", "")
        self.app_password_hash = os.environ.get("APP_PASSWORD_HASH", "")
        self.jwt_algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes = int(os.environ.get("JWT_EXPIRE_MINUTES", "30"))

        # No persistent default: an unset secret gets a random one per
        # process (see warning below), not a shared hardcoded value.
        self._jwt_secret_was_set = "JWT_SECRET" in os.environ
        self.jwt_secret = os.environ.get("JWT_SECRET") or secrets.token_hex(32)

        # Rate limits: requests per 60s window, keyed by IP (/auth/token)
        # or authenticated user (everything else - see rate_limit.py).
        self.rate_limit_auth_token = int(os.environ.get("RATE_LIMIT_AUTH_TOKEN", "5"))
        self.rate_limit_answer = int(os.environ.get("RATE_LIMIT_ANSWER", "10"))
        self.rate_limit_documents_post = int(os.environ.get("RATE_LIMIT_DOCUMENTS_POST", "5"))
        self.rate_limit_default = int(os.environ.get("RATE_LIMIT_DEFAULT", "60"))

        # Input limits, enforced by validators in app/models.py.
        self.max_document_name_length = int(os.environ.get("MAX_DOCUMENT_NAME_LENGTH", "255"))
        self.max_document_characters = int(os.environ.get("MAX_DOCUMENT_CHARACTERS", "100000"))
        self.max_question_characters = int(os.environ.get("MAX_QUESTION_CHARACTERS", "1000"))
        self.max_top_k = int(os.environ.get("MAX_TOP_K", "20"))

        # CORS: comma-separated origins. Empty means none allowed (fail
        # closed, not wildcard) - see main.py for CORSMiddleware wiring.
        self.cors_allowed_origins = [
            origin.strip()
            for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        ]

        if self.jwt_expire_minutes <= 0:
            raise ValueError(f"JWT_EXPIRE_MINUTES must be > 0, got {self.jwt_expire_minutes}")
        if self.max_top_k <= 0:
            raise ValueError(f"MAX_TOP_K must be > 0, got {self.max_top_k}")
        if not self._jwt_secret_was_set:
            warnings.warn(
                "JWT_SECRET not set - using a random per-process secret. "
                "Tokens won't survive a restart. Set JWT_SECRET for real use.",
                stacklevel=2,
            )


# Module-level singleton, built once at import time from the process's
# actual environment - what the running app uses.
settings = Settings()