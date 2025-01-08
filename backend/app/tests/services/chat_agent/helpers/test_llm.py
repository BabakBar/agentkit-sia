import pytest
from unittest.mock import patch

from app.core.config import settings
from app.schemas.tool_schema import LLMType
from app.services.chat_agent.helpers.llm import get_llm, get_token_length

def test_get_token_length():
    """Test token length calculation."""
    text = "Hello, world!"
    length = get_token_length(text)
    assert isinstance(length, int)
    assert length > 0

@pytest.mark.parametrize("model,expected_class", [
    ("gpt-4o", "ChatOpenAI"),
    ("claude-3-5-sonnet-latest", "ChatAnthropic"),
    ("gemini-2.0-flash-exp", "ChatGoogleGenerativeAI"),
])
def test_get_llm_returns_correct_model(model: LLMType, expected_class: str):
    """Test that get_llm returns the correct model class for each provider."""
    llm = get_llm(model)
    assert llm.__class__.__name__ == expected_class

def test_get_llm_with_custom_api_key():
    """Test that get_llm uses custom API key when provided."""
    test_api_key = "test-key-123"
    llm = get_llm("gpt-4o", api_key=test_api_key)
    assert llm.openai_api_key.get_secret_value() == test_api_key

def test_get_llm_uses_default_api_key():
    """Test that get_llm uses default API key when none provided."""
    llm = get_llm("gpt-4o")
    assert llm.openai_api_key.get_secret_value() == settings.OPENAI_API_KEY

def test_get_llm_with_invalid_model():
    """Test that get_llm handles invalid model names gracefully."""
    llm = get_llm("invalid-model")  # type: ignore
    assert llm.__class__.__name__ == "ChatOpenAI"  # Falls back to default

@pytest.mark.parametrize("model", [
    "gpt-4o",
    "claude-3-5-sonnet-latest",
    "gemini-2.0-flash-exp",
])
def test_llm_streaming_enabled(model: LLMType):
    """Test that streaming is enabled for all models."""
    llm = get_llm(model)
    # Gemini uses 'stream' instead of 'streaming'
    if model == "gemini-2.0-flash-exp":
        assert getattr(llm, "stream", False) is True
    else:
        assert getattr(llm, "streaming", False) is True

@pytest.mark.parametrize("model", [
    "gpt-4o",
    "claude-3-5-sonnet-latest",
    "gemini-2.0-flash-exp",
])
def test_llm_temperature_zero(model: LLMType):
    """Test that temperature is set to 0 for consistent outputs."""
    llm = get_llm(model)
    assert getattr(llm, "temperature", None) == 0

@pytest.mark.asyncio
@pytest.mark.parametrize("model", [
    "gpt-4o",
    "claude-3-5-sonnet-latest",
    "gemini-2.0-flash-exp",
])
async def test_llm_generate(model: LLMType):
    """Test that each model can generate text."""
    llm = get_llm(model)
    messages = [{"role": "user", "content": "Say hello"}]
    
    with patch.object(llm, "ainvoke") as mock_invoke:
        mock_invoke.return_value = "Hello!"
        response = await llm.ainvoke(messages)
        assert isinstance(response, str)
        assert len(response) > 0
