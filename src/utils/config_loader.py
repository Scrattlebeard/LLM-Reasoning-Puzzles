import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, config_path: Optional[str] = None):
        self.config_path = config_path
        super().__init__(f"Configuration error in '{config_path}': {message}" if config_path else f"Configuration error: {message}")


def load_config(config_path: str) -> Dict[str, Any]:

    path = Path(config_path)

    if not path.exists():
        raise ConfigError("Configuration file not found", config_path)

    if not path.is_file():
        raise ConfigError("Configuration path is not a file", config_path)

    try:
        # Create a unique module name to avoid conflicts
        module_name = f"config_{abs(hash(str(path)))}"

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ConfigError("Cannot load configuration file", config_path)

        config_module = importlib.util.module_from_spec(spec)

        # Execute the module
        spec.loader.exec_module(config_module)

        # Extract all non-private variables as config
        config = {}
        for key in dir(config_module):
            if not key.startswith("_") and not callable(getattr(config_module, key)):
                config[key] = getattr(config_module, key)

        logger.info(f"Loaded configuration from {config_path} with {len(config)} settings")
        return config

    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Failed to load configuration: {e}", config_path) from e


def validate_config(config: Dict[str, Any]) -> List[str]:
    errors = []

    errors.extend(_validate_required_fields(config))
    errors.extend(_validate_field_types(config))
    errors.extend(_validate_value_ranges(config))
    errors.extend(_validate_specific_constraints(config))

    logger.debug(f"Configuration validation found {len(errors)} errors")
    return errors


def _validate_required_fields(config: Dict[str, Any]) -> List[str]:
    """Validate that all required fields are present."""
    required_fields = {
        "model",
        "temperature",
        "puzzle",
        "puzzle_sizes",
        "turn_limit_multiplier",
        "move_limit_multiplier",
        "repeated_invalid_limit",
        "state_revisit_limit",
        "window_size"
    }

    missing_fields = required_fields - set(config.keys())
    return [f"Missing required fields: {', '.join(sorted(missing_fields))}"] if missing_fields else []


def _validate_field_types(config: Dict[str, Any]) -> List[str]:
    """Validate field types."""
    errors = []

    type_checks = {
        "model": str,
        "temperature": (int, float),
        "max_tokens": (int, type(None)),
        "puzzle": str,
        "puzzle_sizes": list,
        "turn_limit_multiplier": (int, float),
        "move_limit_multiplier": (int, float),
        "repeated_invalid_limit": int,
        "state_revisit_limit": int,
        "window_size": int,
        "seed": (int, type(None)),
        "prompt_template_dir": (str, type(None)),
        "output_dir": (str, type(None))
    }

    for field, expected_type in type_checks.items():
        if field in config:
            value = config[field]
            if not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = " or ".join(t.__name__ for t in expected_type)
                else:
                    type_names = expected_type.__name__
                errors.append(f"Field '{field}' must be {type_names}, got {type(value).__name__}")

    return errors


def _validate_value_ranges(config: Dict[str, Any]) -> List[str]:
    """Validate value ranges for numeric fields."""
    errors = []

    if "temperature" in config:
        temp = config["temperature"]
        if isinstance(temp, (int, float)) and not (0.0 <= temp <= 2.0):
            errors.append("Field 'temperature' must be between 0.0 and 2.0")

    positive_fields = [
        "max_tokens", "turn_limit_multiplier", "move_limit_multiplier",
        "repeated_invalid_limit", "state_revisit_limit", "window_size"
    ]

    for field in positive_fields:
        if field in config and config[field] is not None:
            value = config[field]
            if isinstance(value, (int, float)) and value <= 0:
                errors.append(f"Field '{field}' must be positive")

    return errors


def _validate_specific_constraints(config: Dict[str, Any]) -> List[str]:
    """Validate specific field constraints."""
    errors = []

    errors.extend(_validate_puzzle_sizes(config))
    errors.extend(_validate_paths(config))

    return errors


def _validate_puzzle_sizes(config: Dict[str, Any]) -> List[str]:
    """Validate puzzle_sizes field."""
    errors = []
    if "puzzle_sizes" in config:
        sizes = config["puzzle_sizes"]
        if isinstance(sizes, list):
            if not sizes:
                errors.append("Field 'puzzle_sizes' cannot be empty")
            else:
                for i, size in enumerate(sizes):
                    if not isinstance(size, int) or size <= 0:
                        errors.append(f"puzzle_sizes[{i}] must be a positive integer")
    return errors


def _validate_paths(config: Dict[str, Any]) -> List[str]:
    """Validate path fields."""
    errors = []
    if "prompt_template_dir" in config and config["prompt_template_dir"] is not None:
        template_dir = config["prompt_template_dir"]
        if isinstance(template_dir, str):
            path = Path(template_dir)
            if not path.exists():
                errors.append(f"prompt_template_dir '{template_dir}' does not exist")
            elif not path.is_dir():
                errors.append(f"prompt_template_dir '{template_dir}' is not a directory")
    return errors
