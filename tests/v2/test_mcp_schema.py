import pytest

from agent_os.integration.mcp_schema import (
    MCPSchemaValidationError,
    validate_mcp_arguments,
)


def test_valid_object_schema():
    validate_mcp_arguments(
        {"name": "Alice", "age": 16},
        {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    )


def test_missing_required_argument():
    with pytest.raises(
        MCPSchemaValidationError,
        match=r"\$\.name\.required",
    ):
        validate_mcp_arguments(
            {},
            {
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}},
            },
        )


def test_wrong_type_is_rejected():
    with pytest.raises(
        MCPSchemaValidationError,
        match=r"\$\.age\.type_expected:integer",
    ):
        validate_mcp_arguments(
            {"age": "16"},
            {
                "type": "object",
                "properties": {"age": {"type": "integer"}},
            },
        )


def test_additional_properties_can_be_rejected():
    with pytest.raises(
        MCPSchemaValidationError,
        match=r"\$\.secret\.additional_property",
    ):
        validate_mcp_arguments(
            {"name": "Alice", "secret": "x"},
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "additionalProperties": False,
            },
        )


def test_enum_is_enforced():
    with pytest.raises(
        MCPSchemaValidationError,
        match="enum_value_invalid",
    ):
        validate_mcp_arguments(
            {"mode": "unsafe"},
            {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["safe", "normal"],
                    }
                },
            },
        )


def test_nested_objects_and_arrays():
    validate_mcp_arguments(
        {
            "items": [
                {"name": "one", "enabled": True},
                {"name": "two", "enabled": False},
            ]
        },
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "enabled": {"type": "boolean"},
                        },
                    },
                }
            },
        },
    )


def test_invalid_schema_type_is_rejected():
    with pytest.raises(
        MCPSchemaValidationError,
        match="unsupported_schema_type",
    ):
        validate_mcp_arguments(
            "value",
            {"type": "made_up_type"},
        )


def test_none_schema_allows_arguments():
    validate_mcp_arguments(
        {"anything": "goes"},
        None,
    )


def test_additional_properties_schema_is_validated():
    validate_mcp_arguments(
        {
            "known": "ok",
            "extra": 42,
        },
        {
            "type": "object",
            "properties": {
                "known": {"type": "string"},
            },
            "additionalProperties": {"type": "integer"},
        },
    )

    with pytest.raises(
        MCPSchemaValidationError,
        match=r"\$\.extra\.type_expected:integer",
    ):
        validate_mcp_arguments(
            {
                "known": "ok",
                "extra": "bad",
            },
            {
                "type": "object",
                "properties": {
                    "known": {"type": "string"},
                },
                "additionalProperties": {"type": "integer"},
            },
        )


def test_root_level_scalar_schema_is_supported():
    validate_mcp_arguments(
        "hello",
        {"type": "string"},
    )

    with pytest.raises(
        MCPSchemaValidationError,
        match=r"\$\.type_expected:string",
    ):
        validate_mcp_arguments(
            123,
            {"type": "string"},
        )


def test_array_item_type_is_enforced():
    with pytest.raises(
        MCPSchemaValidationError,
        match=r"\$\[1\]\.type_expected:integer",
    ):
        validate_mcp_arguments(
            [1, "two", 3],
            {
                "type": "array",
                "items": {"type": "integer"},
            },
        )


def test_boolean_is_not_accepted_as_integer():
    with pytest.raises(
        MCPSchemaValidationError,
        match=r"\$\.type_expected:integer",
    ):
        validate_mcp_arguments(
            True,
            {"type": "integer"},
        )
