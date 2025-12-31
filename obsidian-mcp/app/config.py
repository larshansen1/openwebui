"""
Configuration management using Pydantic Settings
Loads settings from environment variables with validation
"""
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Vault configuration
    obsidian_vault_path: str = Field(
        ...,
        description="Path to Obsidian vault"
    )

    # API configuration
    mcp_api_key: str = Field(
        default="",
        min_length=0,
        description="API key for MCP server authentication (not required in dev mode)"
    )

    # Dev mode configuration
    devmode: bool = Field(
        default=False,
        description="Enable development mode (disables authentication - DO NOT USE IN PRODUCTION)"
    )

    # Server configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8000,
        description="Server port"
    )

    # Performance settings
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size in MB"
    )
    cache_max_size: int = Field(
        default=1000,
        description="Maximum number of items in cache"
    )
    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache TTL in seconds (5 minutes default)"
    )

    # Path handling settings
    normalize_paths_lowercase: bool = Field(
        default=True,
        description="Normalize directory paths to lowercase (recommended for cross-platform syncing)"
    )


    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_levels)}")
        return v

    @field_validator("obsidian_vault_path")
    @classmethod
    def validate_vault_path(cls, v: str) -> str:
        """Validate vault path exists"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Vault path does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Vault path is not a directory: {v}")
        return str(path.resolve())

    @model_validator(mode='after')
    def validate_api_key_for_mode(self) -> 'Settings':
        """Validate API key is provided when not in dev mode"""
        if not self.devmode:
            if not self.mcp_api_key:
                raise ValueError("MCP_API_KEY is required when DEVMODE is not enabled")
            if len(self.mcp_api_key) < 16:
                raise ValueError("MCP_API_KEY must be at least 16 characters for security")
        return self

    @property
    def vault_path(self) -> Path:
        """Get vault path as Path object"""
        return Path(self.obsidian_vault_path)

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()
