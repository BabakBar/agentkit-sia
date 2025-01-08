# -*- coding: utf-8 -*-
# mypy: disable-error-code="call-arg"
# TODO: Change langchain param names to match the new langchain version

import logging
from typing import Optional

import tiktoken
from langchain.base_language import BaseLanguageModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.schemas.tool_schema import LLMType

logger = logging.getLogger(__name__)


def get_token_length(
    string: str,
    model: str = "gpt-4",
) -> int:
    """Get the token length of a string."""
    enc = tiktoken.encoding_for_model(model)
    encoded = enc.encode(string)
    return len(encoded)


def get_llm(
    llm: LLMType,
    api_key: Optional[str] = None,
) -> BaseLanguageModel:
    """Get the LLM instance for the given LLM type."""
    # OpenAI Models
    if llm in ["gpt-4o", "gpt-4o-2024-08-06", "gpt-4o-mini", "gpt-4o-mini-2024-07-18"]:
        return ChatOpenAI(
            temperature=0,
            model_name=llm,
            openai_organization=settings.OPENAI_ORGANIZATION,
            openai_api_key=api_key if api_key is not None else settings.OPENAI_API_KEY,
            streaming=True,
        )
    
    # Anthropic Models
    elif llm == "claude-3-5-sonnet-latest":
        return ChatAnthropic(
            model_name=llm,
            temperature=0,
            anthropic_api_key=api_key if api_key is not None else settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
            streaming=True,
        )
    
    # Google Models
    elif llm == "gemini-2.0-flash-exp":
        return ChatGoogleGenerativeAI(
            model=f"models/{llm}",  # Gemini requires full model path
            temperature=0,
            google_api_key=api_key if api_key is not None else settings.GOOGLE_API_KEY,
            convert_system_message_to_human=True,  # Required for proper message handling
            stream=True,  # Gemini uses 'stream' instead of 'streaming'
        )
    
    # Azure OpenAI (if needed)
    elif llm == "azure-3.5":
        if settings.OPENAI_API_BASE is None:
            raise ValueError("OPENAI_API_BASE must be set to use Azure LLM")
        return AzureChatOpenAI(
            openai_api_base=settings.OPENAI_API_BASE,
            openai_api_version="2023-03-15-preview",
            deployment_name="rnd-gpt-35-turbo",
            openai_api_key=api_key if api_key is not None else settings.OPENAI_API_KEY,
            openai_api_type="azure",
            streaming=True,
        )
    
    # Default/Fallback
    else:
        logger.warning(f"LLM {llm} not found, using default LLM")
        return ChatOpenAI(
            temperature=0,
            model_name="gpt-4o",
            openai_organization=settings.OPENAI_ORGANIZATION,
            openai_api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )
