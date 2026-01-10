from typing import Any, Dict, List, Tuple

from soficca_core.errors import make_error


def validate_input(input_data: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Validate input structure and basic types."""
    errors: List[Dict[str, Any]] = []
    cleaned: Dict[str, Any] = {}

    if not isinstance(input_data, dict):
        errors.append(make_error("INVALID_TYPE", "Input data must be a dict", path="$"))
        return errors, cleaned

    if "user" in input_data and isinstance(input_data["user"], dict):
        cleaned["user"] = input_data["user"]

    if "measurements" in input_data and isinstance(input_data["measurements"], list):
        cleaned["measurements"] = input_data["measurements"]

    if "context" in input_data and isinstance(input_data["context"], dict):
        cleaned["context"] = input_data["context"]

    return errors, cleaned

