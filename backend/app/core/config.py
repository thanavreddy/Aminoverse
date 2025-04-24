import os
from pydantic import BaseSettings
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

class Settings(BaseSettings):
    """Configuration settings for the application."""
    
    # API Config
    API_PREFIX: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    PROJECT_NAME: str = "AminoVerse API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "API for the AminoVerse protein research assistant"
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Neo4j Database Configuration
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_USERNAME: str = os.getenv("REDIS_USERNAME", "")
    
    # LLM Configuration - Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_URL: str = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent")
    
    # OpenAI Configuration (legacy)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # External API endpoints
    UNIPROT_API_URL: str = os.getenv("UNIPROT_API_URL", "https://rest.uniprot.org/uniprotkb")
    PDB_API_URL: str = os.getenv("PDB_API_URL", "https://data.rcsb.org/rest/v1")
    STRING_DB_API_URL: str = os.getenv("STRING_DB_API_URL", "https://string-db.org/api")
    DISGENET_API_URL: str = os.getenv("DISGENET_API_URL", "https://www.disgenet.org/api")
    CHEMBL_API_URL: str = os.getenv("CHEMBL_API_URL", "https://www.ebi.ac.uk/chembl/api/data")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get the settings instance."""
    return Settings()

# Settings instance that can be imported
settings = get_settings()