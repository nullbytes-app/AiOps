"""
Pydantic schemas for LLM model management and dynamic discovery.

This module defines data validation schemas for querying available models
from LiteLLM proxy, including metadata and capabilities. Following 2025
Pydantic v2 best practices with proper field validation and examples.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelInfo(BaseModel):
    """
    LLM Model metadata and capabilities.

    Represents a single model available from LiteLLM proxy, including
    ID, display name, provider, token limits, and feature support.

    Attributes:
        id: Unique model identifier (e.g., 'gpt-4', 'claude-3-opus-20240229')
        name: Human-readable display name (e.g., 'GPT-4', 'Claude 3 Opus')
        provider: LLM provider name (e.g., 'openai', 'anthropic')
        max_tokens: Maximum context window in tokens
        supports_function_calling: Whether model supports function calling capability
        input_cost_per_token: Cost per input token (optional, from LiteLLM)
        output_cost_per_token: Cost per output token (optional, from LiteLLM)
    """

    id: str = Field(
        ...,
        description="Unique model identifier",
        examples=["gpt-4", "claude-3-opus-20240229"],
    )
    name: str = Field(
        ...,
        description="Human-readable model display name",
        examples=["GPT-4", "Claude 3 Opus"],
    )
    provider: str = Field(
        ...,
        description="LLM provider name",
        examples=["openai", "anthropic"],
    )
    max_tokens: int = Field(
        ...,
        ge=1,
        description="Maximum context window in tokens",
        examples=[8192, 200000],
    )
    supports_function_calling: bool = Field(
        ...,
        description="Whether model supports function calling",
        examples=[True, False],
    )
    input_cost_per_token: Optional[float] = Field(
        None,
        ge=0,
        description="Input token cost (optional, from LiteLLM)",
        examples=[0.00003],
    )
    output_cost_per_token: Optional[float] = Field(
        None,
        ge=0,
        description="Output token cost (optional, from LiteLLM)",
        examples=[0.00006],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "openai",
                "max_tokens": 8192,
                "supports_function_calling": True,
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006,
            }
        }
    )
