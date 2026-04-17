"""Configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Paths
    data_dir: Path = Path.home() / ".repomemory"
    db_path: Path | None = None  # default: data_dir / "repomemory.db"
    faiss_index_dir: Path | None = None  # default: data_dir / "faiss"
    clone_dir: Path | None = None  # default: data_dir / "repos"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    embedding_batch_size: int = 64
    embedding_provider: str = "local"  # "local" or "huggingface"
    hf_api_key: str | None = None

    # LLM (Groq)
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    llm_enabled: bool = False  # auto-set if groq_api_key present

    # Git cloning
    clone_timeout: int = 120  # seconds
    max_clone_size_mb: int = 500

    # Indexing
    max_file_size_kb: int = 500
    supported_extensions: list[str] = [
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".md",
        ".rst",
        ".txt",
        ".html",
        ".css",
        ".scss",
        ".sh",
        ".bash",
        ".sql",
        ".env",
        ".env.example",
        ".gitignore",
        ".dockerignore",
        "Dockerfile",
        "Makefile",
    ]
    ignore_patterns: list[str] = [
        "node_modules",
        ".git",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "*.min.js",
        "*.min.css",
        "*.map",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dylib",
        "*.dll",
        "*.egg-info",
        ".eggs",
        ".tox",
        ".venv",
        "venv",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    ]

    # Chunking
    max_chunk_tokens: int = 512
    sliding_window_lines: int = 200
    sliding_window_overlap: int = 50

    # Retrieval
    default_top_k: int = 20
    token_budget: int = 8000

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = {"env_prefix": "REPOMEMORY_"}

    def model_post_init(self, __context) -> None:
        # Auto-enable LLM if Groq API key is set
        if self.groq_api_key and not self.llm_enabled:
            self.llm_enabled = True

    def get_db_path(self) -> Path:
        if self.db_path:
            return self.db_path
        return self.data_dir / "repomemory.db"

    def get_faiss_index_dir(self) -> Path:
        if self.faiss_index_dir:
            return self.faiss_index_dir
        return self.data_dir / "faiss"

    def get_clone_dir(self) -> Path:
        if self.clone_dir:
            return self.clone_dir
        return self.data_dir / "repos"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.get_faiss_index_dir().mkdir(parents=True, exist_ok=True)
        self.get_clone_dir().mkdir(parents=True, exist_ok=True)


settings = Settings()
