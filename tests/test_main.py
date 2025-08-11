import os
import pytest
from unittest.mock import patch, mock_open
from main import Config


def test_config_defaults() -> None:
    """Test that Config has the correct default values."""
    config = Config()

    # All fields should be None by default
    assert config.ip is None
    assert config.token is None
    assert config.source_json is None
    assert config.paintings_json is None
    assert config.painters_json is None
    assert config.populated_json is None
    assert config.images_dir is None
    assert config.base_url is None


@patch.dict(
    os.environ,
    {
        "THEFRAME_IP": "192.168.1.100",
        "THEFRAME_TOKEN": "test_token",
        "SOURCE_JSON": "http://example.com/images.json",
    },
)
def test_config_from_env() -> None:
    """Test that Config correctly loads from environment variables."""
    config = Config()

    assert config.ip == "192.168.1.100"
    assert config.token == "test_token"
    assert config.source_json == "http://example.com/images.json"


def test_config_field_validation() -> None:
    """Test that Config fields are properly typed."""
    config = Config(
        ip="192.168.1.100",
        token="test_token",
        source_json="http://example.com/images.json",
    )

    assert isinstance(config.ip, str)
    assert isinstance(config.token, str)
    assert isinstance(config.source_json, str)
