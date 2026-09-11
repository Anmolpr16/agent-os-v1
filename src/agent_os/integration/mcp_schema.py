from __future__ import annotations

from typing import Any


class MCPSchemaValidationError(ValueError):
    """Raised when MCP tool arguments violate the advertised input schema."""


def _type_matches(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    check = checks.get(expected)
    if check is None:
        raise MCPSchemaValidationError(
            f"unsupported_schema_type:{expected}"
        )
    return check(value)


def validate_mcp_arguments(
    arguments: Any,
    schema: dict[str, Any] | None,
    *,
    path: str = "$",
) -> None:
    """Validate the useful JSON-Schema subset used by MCP tool inputs."""
    if schema is None:
        return

    if not isinstance(schema, dict):
        raise MCPSchemaValidationError("schema_must_be_object")

    if "type" in schema:
        expected = schema["type"]

        if not isinstance(expected, str):
            raise MCPSchemaValidationError(
                f"{path}.type_invalid"
            )

        if not _type_matches(arguments, expected):
            raise MCPSchemaValidationError(
                f"{path}.type_expected:{expected}"
            )

    if "enum" in schema:
        values = schema["enum"]

        if not isinstance(values, list):
            raise MCPSchemaValidationError(
                f"{path}.enum_invalid"
            )

        if arguments not in values:
            raise MCPSchemaValidationError(
                f"{path}.enum_value_invalid"
            )

    if isinstance(arguments, dict):
        required = schema.get("required", [])

        if not isinstance(required, list):
            raise MCPSchemaValidationError(
                f"{path}.required_invalid"
            )

        for name in required:
            if not isinstance(name, str):
                raise MCPSchemaValidationError(
                    f"{path}.required_name_invalid"
                )

            if name not in arguments:
                raise MCPSchemaValidationError(
                    f"{path}.{name}.required"
                )

        properties = schema.get("properties", {})

        if properties is None:
            properties = {}

        if not isinstance(properties, dict):
            raise MCPSchemaValidationError(
                f"{path}.properties_invalid"
            )

        additional = schema.get("additionalProperties", True)

        if not isinstance(additional, bool) and not isinstance(additional, dict):
            raise MCPSchemaValidationError(
                f"{path}.additionalProperties_invalid"
            )

        if additional is False:
            unknown = set(arguments) - set(properties)

            if unknown:
                name = sorted(unknown)[0]
                raise MCPSchemaValidationError(
                    f"{path}.{name}.additional_property"
                )

        for name, value in arguments.items():
            child_schema = properties.get(name)

            if child_schema is None:
                if isinstance(additional, dict):
                    child_schema = additional
                else:
                    continue

            if not isinstance(child_schema, dict):
                raise MCPSchemaValidationError(
                    f"{path}.{name}.schema_invalid"
                )

            validate_mcp_arguments(
                value,
                child_schema,
                path=f"{path}.{name}",
            )

    if isinstance(arguments, list):
        items = schema.get("items")

        if items is not None:
            if not isinstance(items, dict):
                raise MCPSchemaValidationError(
                    f"{path}.items_invalid"
                )

            for index, value in enumerate(arguments):
                validate_mcp_arguments(
                    value,
                    items,
                    path=f"{path}[{index}]",
                )
