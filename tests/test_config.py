from agent_os.config import RuntimeConfig


def test_runtime_config_defaults():
    config = RuntimeConfig()

    assert config.memory_path == ":memory:"
    assert config.provider_response == "task completed"
    assert config.provider_name == "mock"
    assert config.provider_model == "mock-v1"


def test_runtime_config_is_explicitly_overridable():
    config = RuntimeConfig(
        memory_path="agent.db",
        provider_response="configured response",
        provider_name="custom-provider",
        provider_model="custom-v1",
    )

    assert config.memory_path == "agent.db"
    assert config.provider_response == "configured response"
    assert config.provider_name == "custom-provider"
    assert config.provider_model == "custom-v1"


def test_runtime_config_rejects_empty_provider_name():
    import pytest
    from agent_os.config import RuntimeConfig

    with pytest.raises(ValueError, match="provider_name"):
        RuntimeConfig(provider_name="")


def test_runtime_config_rejects_empty_provider_model():
    import pytest
    from agent_os.config import RuntimeConfig

    with pytest.raises(ValueError, match="provider_model"):
        RuntimeConfig(provider_model="")


def test_runtime_config_rejects_empty_provider_response():
    import pytest
    from agent_os.config import RuntimeConfig

    with pytest.raises(ValueError, match="provider_response"):
        RuntimeConfig(provider_response="")
