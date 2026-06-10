"""Tests for configuration."""

import tempfile
import os
from pathlib import Path

from ollamatui.config import Config, load_config, save_config, get_config_dir, ProviderType, SandboxMode, ApprovalPolicy


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.model == "qwen2.5-coder:3b"
    assert config.provider == ProviderType.LOCAL
    assert config.sandbox == SandboxMode.WORKSPACE_WRITE
    assert config.approval == ApprovalPolicy.ON_REQUEST


def test_config_enum_values():
    """Test enum value handling."""
    config = Config(
        provider="cloud",
        sandbox="read-only",
        approval="never",
    )
    assert config.provider == ProviderType.CLOUD
    assert config.sandbox == SandboxMode.READ_ONLY
    assert config.approval == ApprovalPolicy.NEVER


def test_load_config_creates_dir():
    """Test that load_config creates config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".ollamatui"
        os.environ["HOME"] = tmpdir
        
        config = load_config()
        assert config_dir.exists()


def test_save_and_load_config():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".ollamatui"
        os.environ["HOME"] = tmpdir
        
        # Create and save config
        config = Config(
            model="test-model",
            provider=ProviderType.CLOUD,
        )
        save_config(config)
        
        # Load it back
        loaded = load_config()
        assert loaded.model == "test-model"
        assert loaded.provider == ProviderType.CLOUD


def test_config_with_profile():
    """Test profile-based configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".ollamatui"
        os.environ["HOME"] = tmpdir
        
        # Save profile
        config = Config(model="profile-model")
        save_config(config, profile="test")
        
        # Load with profile
        loaded = load_config(profile="test")
        assert loaded.model == "profile-model"
