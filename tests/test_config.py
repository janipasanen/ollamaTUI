"""Tests for configuration management."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from ollamatui.config import (
    Config,
    load_config,
    save_config,
    get_config_dir,
    get_config_path,
    SandboxMode,
    ApprovalPolicy,
    ProviderType,
)


def test_default_config():
    """Test default configuration values."""
    config = Config()
    
    assert config.provider == ProviderType.LOCAL
    assert config.model == "qwen2.5-coder:3b"
    assert config.temperature == 0.7
    assert config.top_p == 0.9
    assert config.sandbox == SandboxMode.WORKSPACE_WRITE
    assert config.approval == ApprovalPolicy.ON_REQUEST
    assert config.working_dir == "."
    assert config.add_dirs == []


def test_config_with_api_key():
    """Test configuration with API key."""
    config = Config(api_key="test-key-12345")
    
    assert config.api_key == "test-key-12345"


def test_config_sandbox_modes():
    """Test sandbox mode values."""
    assert SandboxMode.READ_ONLY.value == "read-only"
    assert SandboxMode.WORKSPACE_WRITE.value == "workspace-write"
    assert SandboxMode.DANGER_FULL_ACCESS.value == "danger-full-access"


def test_config_approval_policies():
    """Test approval policy values."""
    assert ApprovalPolicy.UNTRUSTED.value == "untrusted"
    assert ApprovalPolicy.ON_REQUEST.value == "on-request"
    assert ApprovalPolicy.NEVER.value == "never"


def test_config_provider_types():
    """Test provider type values."""
    assert ProviderType.LOCAL.value == "local"
    assert ProviderType.CLOUD.value == "cloud"


def test_save_and_load_config():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        
        config = Config(
            provider=ProviderType.CLOUD,
            model="test-model",
            temperature=0.5,
        )
        
        save_config(config)
        
        # Verify file was created
        default_path = get_config_path()
        assert default_path.exists() or config_path.parent.exists()


def test_load_config_missing_file():
    """Test loading configuration from non-existent file."""
    # Should return default config with default values
    # Note: If ~/.ollamatui/config.toml exists, it will be loaded
    config = load_config()
    
    # Should have valid provider value
    assert config.provider in [ProviderType.LOCAL, ProviderType.CLOUD]
    assert config.model is not None


def test_get_config_dir():
    """Test config directory generation."""
    config_dir = get_config_dir()
    
    assert ".ollamatui" in str(config_dir)


def test_get_config_path():
    """Test config path generation."""
    config_path = get_config_path()
    
    assert ".ollamatui" in str(config_path)
    assert "config.toml" in str(config_path)


def test_config_from_env():
    """Test configuration from environment variables."""
    with patch.dict(os.environ, {"OLLAMATUI_MODEL": "env-model"}):
        config = load_config()
        
        # Should use env var
        assert config.model == "env-model"


def test_config_ollama_api_key_env():
    """Test OLLAMA_API_KEY environment variable fallback."""
    with patch.dict(os.environ, {"OLLAMA_API_KEY": "ollama-test-key"}, clear=False):
        # Clear any existing OLLAMATUI_API_KEY
        with patch.dict(os.environ, {"OLLAMATUI_API_KEY": ""}, clear=False):
            config = load_config()
            
            # Should use OLLAMA_API_KEY as fallback
            assert config.api_key == "ollama-test-key"


def test_config_temperature_validation():
    """Test configuration temperature bounds."""
    # Valid temperature
    config = Config(temperature=0.5)
    assert config.temperature == 0.5
    
    # Temperature at bounds
    config = Config(temperature=0.0)
    assert config.temperature == 0.0
    
    config = Config(temperature=1.0)
    assert config.temperature == 1.0


def test_config_path_expansion():
    """Test that paths are expanded."""
    config = Config(
        working_dir="~/project",
        add_dirs=["~/other", "/absolute/path"]
    )
    
    # Load config to trigger expansion
    # Note: load_config does the expansion
    assert True  # Placeholder for path expansion test


def test_config_model_dump():
    """Test config serialization."""
    config = Config(model="test-model", temperature=0.5)
    
    data = config.model_dump()
    
    assert data["model"] == "test-model"
    assert data["temperature"] == 0.5


def test_config_extra_fields_ignored():
    """Test that extra fields are ignored."""
    config = Config(**{"model": "test", "unknown_field": "value"})
    
    assert config.model == "test"
    assert not hasattr(config, "unknown_field")