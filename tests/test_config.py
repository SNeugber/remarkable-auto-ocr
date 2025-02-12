# tests/test_config.py
from pathlib import Path
from unittest.mock import patch

import pytest
import tomllib

from src.rao.config import ConfigLoadError, _Config


# Mock the tomllib.load function
@patch("tomllib.load")
def test_config_load_success(mock_tomllib_load):
    # Create a mock config file path
    mock_config_path = Path("./test_config.toml")

    # Create mock config data
    mock_config_data = {
        "remarkable-auto-ocr-app": {
            "google_api_key": "test_key",
            "remarkable_ip_address": "test_ip",
            "ssh_key_path": "test_path",
        }
    }

    # Set the return value of the mocked tomllib.load function
    mock_tomllib_load.return_value = mock_config_data

    # Call the load method with the mock path
    config = _Config.load(path_override=mock_config_path)

    # Assert that the config values are loaded correctly
    assert config.google_api_key == "test_key"
    assert config.remarkable_ip_address == "test_ip"
    assert config.ssh_key_path == "test_path"
    assert config.check_interval == 120  # test default values
    assert config.model == "gemini-1.5-pro"


@patch("tomllib.load")
def test_config_load_failure(mock_tomllib_load):
    mock_tomllib_load.side_effect = FileNotFoundError
    with pytest.raises(ConfigLoadError):
        _Config.load()


@patch("tomllib.load")
def test_config_load_toml_decode_error(mock_tomllib_load):
    mock_tomllib_load.side_effect = tomllib.TOMLDecodeError("Invalid TOML")
    with pytest.raises(ConfigLoadError):
        _Config.load()


@patch("tomllib.load")
def test_config_reload_success(mock_tomllib_load):
    # setup a config object first, so we can validate it's updated
    _Config.default_prompt = "test_prompt"
    config = _Config(
        google_api_key="test_key",
        remarkable_ip_address="test_ip",
        ssh_key_path="test_path",
    )
    config.default_prompt = "test_prompt"

    # Create a mock config file path
    mock_config_path = Path("./test_config.toml")

    # Create mock config data
    mock_config_data = {
        "remarkable-auto-ocr-app": {
            "google_api_key": "test_key",
            "remarkable_ip_address": "test_ip",
            "ssh_key_path": "test_path",
            "default_prompt": "new_prompt",  # updated prompt
        }
    }

    # Set the return value of the mocked tomllib.load function
    mock_tomllib_load.return_value = mock_config_data

    # Call the reload method with the mock path
    config.reload(path_override=mock_config_path)

    # Assert that the config values are loaded correctly
    assert config.google_api_key == "test_key"
    assert config.default_prompt == "new_prompt"
