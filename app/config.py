# ==========================================
# PDF Consultor - Configuration
# ==========================================

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List
import os


class Settings(BaseSettings):
    """Configurações da aplicação usando Pydantic Settings"""

    # --- LLM Configuration ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- Alternative LLMs ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Embeddings ---
    huggingface_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    huggingface_device: str = "cpu"

    # --- RAG Configuration ---
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k_results: int = 5
    max_context_tokens: int = 16000

    # --- RAPTOR Configuration ---
    raptor_max_depth: int = 3
    raptor_min_chunks: int = 4
    raptor_top_k: int = 3

    # --- Search Configuration ---
    rrf_k: int = 60
    hybrid_weight_vector: float = 0.7
    hybrid_weight_keyword: float = 0.3

    # --- Server Configuration ---
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 1

    # --- Paths ---
    pdfs_dir: str = "trabalho"
    indexes_dir: str = "indexes"
    notes_dir: str = "notes"
    upload_max_size_mb: int = 50

    # --- Security ---
    secret_key: str = "change-this-secret-key"
    allowed_origins: str = "http://localhost:8000"

    # --- Logging ---
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # --- Performance ---
    max_concurrent_requests: int = 10
    cache_ttl: int = 3600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def pdfs_path(self) -> Path:
        """Caminho absoluto para o diretório de PDFs"""
        return Path(self.pdfs_dir).absolute()

    @property
    def indexes_path(self) -> Path:
        """Caminho absoluto para o diretório de índices"""
        return Path(self.indexes_dir).absolute()

    @property
    def notes_path(self) -> Path:
        """Caminho absoluto para o diretório de notas"""
        return Path(self.notes_dir).absolute()

    @property
    def log_path(self) -> Path:
        """Caminho absoluto para o arquivo de log"""
        return Path(self.log_file).absolute()

    @property
    def allowed_origins_list(self) -> List[str]:
        """Lista de origens permitidas para CORS"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    def ensure_directories(self) -> None:
        """Criar diretórios necessários se não existirem"""
        for path in [self.pdfs_path, self.indexes_path, self.notes_path, Path("logs")]:
            path.mkdir(parents=True, exist_ok=True)


# Instância global de configurações
settings = Settings()
settings.ensure_directories()
