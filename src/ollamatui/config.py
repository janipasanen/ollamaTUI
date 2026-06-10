"""Configuration management for OllamaTUI."""

import os
from pathlib import Path
from typing import Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxMode(str, Enum):
    """Sandbox mode options."""
    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    DANGER_FULL_ACCESS = "danger-full-access"


class ApprovalPolicy(str, Enum):
    """Approval policy options."""
    UNTRUSTED = "untrusted"
    ON_REQUEST = "on-request"
    NEVER = "never"


class ProviderType(str, Enum):
    """Provider type options."""
    LOCAL = "local"
    CLOUD = "cloud"


class Config(BaseModel):
    """Main configuration model."""
    
    # Model settings
    model: str = "qwen2.5-coder:3b"
    provider: ProviderType = ProviderType.LOCAL
    
    # Sandbox settings
    sandbox: SandboxMode = SandboxMode.WORKSPACE_WRITE
    approval: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    
    # Ollama settings
    local_host: str = "http://localhost:11434"
    cloud_host: str = "https://ollama.com"
    api_key: Optional[str] = None
    
    # Working directory
    working_dir: str = "."
    add_dirs: list[str] = Field(default_factory=list)
    
    # Session settings
    session_db: str = "~/.ollamatui/sessions.db"
    
    # UI settings
    theme: str = "dark"
    show_timestamps: bool = True
    show_token_count: bool = False
    
    # Advanced
    max_context_tokens: int = 32768
    temperature: float = 0.7
    top_p: float = 0.9
    
    model_config = {
        "extra": "ignore",
        "use_enum_values": True,
    }


class Settings(BaseSettings):
    """Settings loaded from environment and config file."""
    
    model_config = SettingsConfigDict(
        env_prefix="OLLAMATUI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Override config file path
    config_file: Optional[str] = None
    
    # Environment variable overrides
    model: Optional[str] = None
    provider: Optional[ProviderType] = None
    sandbox: Optional[SandboxMode] = None
    approval: Optional[ApprovalPolicy] = None
    api_key: Optional[str] = None
    working_dir: Optional[str] = None


def get_config_dir() -> Path:
    """Get the configuration directory."""
    return Path.home() / ".ollamatui"


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.toml"


def load_config(profile: Optional[str] = None, cli_overrides: Optional[dict] = None) -> Config:
    """Load configuration from file, environment, and CLI overrides."""
    try:
        import tomllib as tomli
    except ImportError:
        import tomli
    import tomli_w
    
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = get_config_path()
    
    # Load base config from file
    file_config = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            file_config = tomli.load(f)
    
    # Load profile config if specified
    profile_config = {}
    if profile:
        profile_path = config_dir / f"{profile}.config.toml"
        if profile_path.exists():
            with open(profile_path, "rb") as f:
                profile_config = tomli.load(f)
    
    # Load environment settings
    env_settings = Settings()
    
    # Merge configs (file -> profile -> env -> cli)
    merged = {**file_config, **profile_config}
    
    # Apply environment overrides
    for field in ["model", "provider", "sandbox", "approval", "api_key", "working_dir"]:
        value = getattr(env_settings, field, None)
        if value is not None:
            merged[field] = value
    
    # Apply CLI overrides
    if cli_overrides:
        merged.update({k: v for k, v in cli_overrides.items() if v is not None})
    
    # Create config object
    config = Config(**merged)
    
    # Expand paths
    config.working_dir = os.path.expanduser(config.working_dir)
    config.session_db = os.path.expanduser(config.session_db)
    config.add_dirs = [os.path.expanduser(d) for d in config.add_dirs]
    
    return config


def save_config(config: Config, profile: Optional[str] = None) -> None:
    """Save configuration to file."""
    import tomli_w
    
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    if profile:
        config_path = config_dir / f"{profile}.config.toml"
    else:
        config_path = get_config_path()
    
    # Convert to dict, excluding defaults
    data = config.model_dump(exclude_defaults=True)
    
    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)
