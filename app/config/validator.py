import json


def validate_json_list(value, field_name: str = "field") -> list:
    if isinstance(value, str):
        if not value or value.isspace():
            raise ValueError(f"{field_name} cannot be empty")
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError(f"{field_name} must be a JSON array")
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for {field_name}: {e}")
    elif isinstance(value, list):
        return value
    raise ValueError(f"{field_name} must be a list or JSON string, got {type(value)}")


def validate_json_dict(value, field_name: str = "field") -> dict:
    if isinstance(value, str):
        if not value or value.isspace():
            raise ValueError(f"{field_name} cannot be empty")
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError(f"{field_name} must be a JSON object")
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for {field_name}: {e}")
    elif isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} must be a dict or JSON string, got {type(value)}")
