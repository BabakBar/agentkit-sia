# -*- coding: utf-8 -*-
from typing import Any, List, Literal, Optional, Union

from box import Box
from langchain.schema import AIMessage, HumanMessage
from pydantic.v1 import BaseModel  # Using v1 since LangChain internally uses v1

LLMType = Literal[
    # OpenAI Models
    "gpt-4o",
    "gpt-4o-2024-08-06",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    # Anthropic Models
    "claude-3-5-sonnet-latest",
    # Google Models
    "gemini-2.0-flash-exp"
]


class PromptInput(BaseModel):
    """Schema for prompt input configuration."""
    class Config:
        arbitrary_types_allowed = True

    name: str
    content: str


class ToolConfig(BaseModel):
    """Schema for tool configuration."""
    class Config:
        arbitrary_types_allowed = True

    description: str
    prompt_message: str
    image_description_prompt: Optional[str]
    system_context: str
    prompt_selection: Optional[str]
    system_context_selection: Optional[str]
    prompt_validation: Optional[str]
    system_context_validation: Optional[str]
    prompt_refinement: Optional[str]
    system_context_refinement: Optional[str]
    prompt_inputs: list[PromptInput]
    additional: Optional[Box] = None


class SqlToolConfig(ToolConfig):
    """Schema for SQL tool specific configuration."""

    nb_example_rows: int
    validate_empty_results: bool
    validate_with_llm: bool
    always_limit_query: bool


class ToolsLibrary(BaseModel):
    """Schema for tool library configuration."""

    library: dict[
        str,
        ToolConfig,
    ]


class UserSettings(BaseModel):
    """Schema for user settings configuration."""

    data: dict[
        str,
        Any,
    ]
    version: Optional[int] = None


class ToolInputSchema(BaseModel):
    """Schema for tool input with support for LangChain message types."""
    class Config:
        arbitrary_types_allowed = True

    chat_history: List[Union[HumanMessage, AIMessage]]
    latest_human_message: str
    user_settings: Optional[UserSettings] = None
    intermediate_steps: dict[str, Any] = {}
