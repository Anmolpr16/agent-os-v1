

def test_mock_provider_accepts_identity_configuration():
    from agent_os.providers import MockProvider, ProviderRequest

    provider = MockProvider(
        response="configured",
        provider="custom-provider",
        model="custom-model",
    )

    result = provider.generate(ProviderRequest(prompt="hello"))

    assert result.text == "configured"
    assert result.provider == "custom-provider"
    assert result.model == "custom-model"
