import os


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


# Module-level singleton, built once at import time from the process's
# actual environment - what the running app uses.
settings = Settings()