"""
LLM Model Discovery Service with dynamic LiteLLM integration.

This module provides dynamic model discovery from LiteLLM proxy,
enabling real-time model availability updates without code changes.
Implements intelligent caching with TTL expiry and graceful fallback
when LiteLLM is unavailable.

Key Features:
    - Dynamic model fetching from LiteLLM /v1/model/info endpoint
    - 5-minute TTL in-memory cache with datetime-based expiry
    - Graceful fallback to default models on LiteLLM unavailability
    - Comprehensive error handling with logging
    - Single model lookup with get_model_details()

Architecture:
    - ModelDiscoveryService: Core service with cache management
    - Uses httpx for async HTTP calls to LiteLLM proxy
    - Returns Pydantic ModelInfo schemas for type safety
    - Cache invalidation: automatic TTL or manual force_refresh

References:
    - LiteLLM Docs: https://docs.litellm.ai/docs/proxy/model_management
    - Story 9.1: Dynamic Model Discovery from LiteLLM
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from src.config import settings
from src.schemas.llm_models import ModelInfo


class ModelDiscoveryService:
    """
    Service for discovering and caching available LLM models from LiteLLM.

    Manages dynamic model discovery with intelligent caching. Queries LiteLLM
    /v1/model/info endpoint and caches results with 5-minute TTL. Falls back
    to sensible defaults if LiteLLM is unavailable.

    Attributes:
        _cache: Cached list of ModelInfo objects (None if not cached)
        _cache_expiry: Datetime when cache expires (None if not cached)
        _cache_ttl: Time-to-live duration (5 minutes)
        litellm_proxy_url: LiteLLM proxy base URL
        litellm_master_key: Master key for LiteLLM API access
    """

    # Default fallback models when LiteLLM is unreachable
    DEFAULT_FALLBACK_MODELS = [
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "provider": "openai",
            "max_tokens": 8192,
            "supports_function_calling": True,
        },
        {
            "id": "claude-3-opus-20240229",
            "name": "Claude 3 Opus",
            "provider": "anthropic",
            "max_tokens": 200000,
            "supports_function_calling": True,
        },
    ]

    # Timeout configuration (granular: connect, read, write, pool)
    TIMEOUT_CONFIG = httpx.Timeout(
        connect=5.0,  # Connection establishment
        read=10.0,  # Reading response (model list should be quick)
        write=5.0,  # Writing request
        pool=5.0,  # Acquiring connection from pool
    )

    def __init__(
        self,
        litellm_proxy_url: Optional[str] = None,
        litellm_master_key: Optional[str] = None,
    ):
        """
        Initialize ModelDiscoveryService with LiteLLM credentials.

        Args:
            litellm_proxy_url: LiteLLM proxy base URL (defaults to settings.litellm_proxy_url)
            litellm_master_key: Master key for LiteLLM API (defaults to settings.litellm_master_key)
        """
        self._cache: Optional[List[Dict[str, Any]]] = None
        self._cache_expiry: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)

        self.litellm_proxy_url = litellm_proxy_url or settings.litellm_proxy_url
        self.litellm_master_key = litellm_master_key or settings.litellm_master_key

    def _is_cache_valid(self) -> bool:
        """
        Check if cached data is still valid.

        Returns:
            bool: True if cache exists and hasn't expired, False otherwise
        """
        if self._cache is None or self._cache_expiry is None:
            return False
        return datetime.now(timezone.utc) < self._cache_expiry

    def _log_cache_hit(self) -> None:
        """Log cache hit for observability."""
        logger.debug("Model cache hit - using cached models")

    def _log_cache_miss(self) -> None:
        """Log cache miss - will fetch from LiteLLM."""
        logger.debug("Model cache miss - fetching from LiteLLM")

    def _update_cache(self, models: List[Dict[str, Any]]) -> None:
        """
        Update cache with new models and set expiry time.

        Args:
            models: List of model dictionaries to cache
        """
        self._cache = models
        self._cache_expiry = datetime.now(timezone.utc) + self._cache_ttl
        logger.debug(f"Updated model cache with {len(models)} models, TTL: 5 minutes")

    async def get_available_models(
        self, force_refresh: bool = False
    ) -> List[ModelInfo]:
        """
        Fetch available models from LiteLLM with caching.

        Queries LiteLLM /v1/model/info endpoint. Caches results for 5 minutes.
        Returns cached data if fresh. Falls back to defaults if LiteLLM unavailable.

        Args:
            force_refresh: Skip cache and fetch fresh from LiteLLM

        Returns:
            List[ModelInfo]: List of available models with metadata

        Raises:
            None - Always returns a list (cached, fresh, or fallback)
        """
        # Return cached data if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid():
            self._log_cache_hit()
            return [ModelInfo(**model) for model in self._cache]

        self._log_cache_miss()

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_CONFIG) as client:
                headers = {"Authorization": f"Bearer {self.litellm_master_key}"}
                url = f"{self.litellm_proxy_url}/v1/model/info"

                logger.debug(f"Fetching models from {url}")
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                models = data.get("data", [])

                # Transform LiteLLM response to ModelInfo format
                # FIX: Parse actual LiteLLM response format (model_name, litellm_params, model_info)
                transformed_models = []
                for model in models:
                    try:
                        # Extract fields from actual LiteLLM response format
                        model_name = model.get("model_name")  # e.g., "xai/*", "xai/grok-code-fast-1-0825"
                        litellm_params = model.get("litellm_params", {})
                        model_info_obj = model.get("model_info", {})

                        # Get provider from litellm_params
                        provider = litellm_params.get("custom_llm_provider") or "litellm"
                        
                        # Get model ID from model_info or use model_name
                        model_id = model_info_obj.get("id") or model_name
                        
                        # Skip if no model_name
                        if not model_name:
                            logger.warning(f"Skipping model with missing model_name: {model}")
                            continue

                        # Create display name (remove provider prefix if present)
                        display_name = model_name
                        if "/" in model_name and not model_name.endswith("/*"):
                            # e.g., "xai/grok-code-fast-1-0825" -> "Grok Code Fast 1 0825"
                            display_name = model_name.split("/", 1)[1].replace("-", " ").title()
                        elif model_name.endswith("/*"):
                            # e.g., "xai/*" -> "XAI (All Models)"
                            display_name = f"{provider.upper()} (All Models)"
                        
                        transformed = {
                            "id": model_name,  # Use model_name as ID for consistency
                            "name": display_name,
                            "provider": provider,
                            "max_tokens": litellm_params.get("max_tokens", 4096),
                            "supports_function_calling": litellm_params.get(
                                "supports_function_calling", True
                            ),
                            "input_cost_per_token": litellm_params.get("input_cost_per_token"),
                            "output_cost_per_token": litellm_params.get("output_cost_per_token"),
                        }
                        transformed_models.append(transformed)
                    except (KeyError, AttributeError) as e:
                        logger.warning(f"Failed to parse model {model}: {e}")
                        continue

                if transformed_models:
                    self._update_cache(transformed_models)
                    logger.info(f"Successfully fetched {len(transformed_models)} models from LiteLLM")
                    return [ModelInfo(**model) for model in transformed_models]
                else:
                    logger.warning("LiteLLM returned empty model list, using fallback")
                    self._update_cache(self.DEFAULT_FALLBACK_MODELS)
                    return [ModelInfo(**model) for model in self.DEFAULT_FALLBACK_MODELS]

        except httpx.TimeoutException as e:
            logger.warning(f"Timeout fetching models from LiteLLM: {e}")
            if self._cache:
                logger.info("Returning stale cached models due to timeout")
                return [ModelInfo(**model) for model in self._cache]
            return [ModelInfo(**model) for model in self.DEFAULT_FALLBACK_MODELS]

        except httpx.ConnectError as e:
            logger.warning(f"Failed to connect to LiteLLM: {e}")
            if self._cache:
                logger.info("Returning stale cached models due to connection error")
                return [ModelInfo(**model) for model in self._cache]
            return [ModelInfo(**model) for model in self.DEFAULT_FALLBACK_MODELS]

        except httpx.HTTPStatusError as e:
            logger.error(f"LiteLLM returned error {e.response.status_code}: {e.response.text}")
            if self._cache:
                logger.info("Returning stale cached models due to HTTP error")
                return [ModelInfo(**model) for model in self._cache]
            return [ModelInfo(**model) for model in self.DEFAULT_FALLBACK_MODELS]

        except Exception as e:
            logger.error(f"Unexpected error fetching models: {e}")
            if self._cache:
                logger.info("Returning stale cached models due to unexpected error")
                return [ModelInfo(**model) for model in self._cache]
            return [ModelInfo(**model) for model in self.DEFAULT_FALLBACK_MODELS]

    async def get_model_details(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get details for a specific model.

        Args:
            model_id: Model identifier to lookup

        Returns:
            ModelInfo: Model details if found, None otherwise
        """
        models = await self.get_available_models()
        for model in models:
            if model.id == model_id:
                return model
        logger.warning(f"Model {model_id} not found in available models")
        return None
