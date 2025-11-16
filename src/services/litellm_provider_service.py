"""
LiteLLM Provider Service

Manages LLM provider models via the LiteLLM proxy API.
Acts as the client for LiteLLM's /model/new, /v1/model/info, and /model/delete endpoints.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class LiteLLMProviderService:
    """
    Service for managing LLM providers and models via LiteLLM proxy API.

    Handles:
    - Adding new models via /model/new endpoint
    - Listing all configured models via /v1/model/info endpoint
    - Deleting models via /model/delete endpoint
    """

    def __init__(self, base_url: Optional[str] = None, master_key: Optional[str] = None):
        """
        Initialize the LiteLLM Provider Service.

        Args:
            base_url: LiteLLM proxy base URL (default: http://litellm:4000)
            master_key: LiteLLM master key for authentication (default: LITELLM_MASTER_KEY env var)
        """
        self.base_url = base_url or os.getenv("LITELLM_URL", "http://litellm:4000")
        self.master_key = master_key or os.getenv("LITELLM_MASTER_KEY", "")

        if not self.master_key:
            logger.warning("LITELLM_MASTER_KEY not configured")

        # Configure httpx client with granular timeouts (2025 best practice)
        self.timeout = httpx.Timeout(
            timeout=30.0,
            connect=5.0,
            read=30.0,
            write=5.0,
            pool=5.0,
        )

    async def add_model_to_litellm(
        self,
        model_name: str,
        litellm_params: Dict[str, Any],
        model_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add a new model to LiteLLM proxy via /model/new endpoint.

        Args:
            model_name: Name to register model as (e.g., "gpt-4-production")
            litellm_params: LiteLLM parameters including:
                - model: underlying model identifier (e.g., "openai/gpt-4")
                - api_key: provider API key
                - api_base: optional provider base URL
                - rpm: optional rate limit (requests per minute)
            model_info: optional metadata dict with display_name, description, tags, etc.

        Returns:
            Response dict with 'status' and 'message' keys

        Raises:
            httpx.HTTPError: if request fails
        """
        url = f"{self.base_url}/model/new"
        headers = self._get_auth_headers()

        payload = {
            "model_name": model_name,
            "litellm_params": litellm_params,
        }

        if model_info:
            payload["model_info"] = model_info

        logger.info(f"Adding model to LiteLLM: {model_name}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Successfully added model {model_name}: {result}")
                return result
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to add model {model_name}: {e.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise
        except httpx.RequestError as e:
            error_msg = f"Request failed when adding model {model_name}: {str(e)}"
            logger.error(error_msg)
            raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List all configured models from LiteLLM proxy via /v1/model/info endpoint.

        Returns:
            List of model dicts with structure:
            [
                {
                    "model_name": "gpt-4",
                    "litellm_params": {"model": "gpt-4"},
                    "model_info": {"max_tokens": 8192, ...}
                }
            ]

        Raises:
            httpx.HTTPError: if request fails
        """
        url = f"{self.base_url}/v1/model/info"
        headers = self._get_auth_headers()

        logger.info("Fetching models from LiteLLM")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Response format: {"data": [...]} or direct dict with model names as keys
                if isinstance(data, dict) and "data" in data:
                    models = data["data"]
                else:
                    # Old format: direct dict, convert to list
                    models = [
                        {
                            "model_name": name,
                            "litellm_params": model_data.get("litellm_params", {}),
                            "model_info": model_data.get("model_info", {}),
                        }
                        for name, model_data in data.items()
                        if isinstance(model_data, dict)
                    ]

                logger.info(f"Retrieved {len(models)} models from LiteLLM")
                return models
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to list models: {e.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise
        except httpx.RequestError as e:
            error_msg = f"Request failed when listing models: {str(e)}"
            logger.error(error_msg)
            raise

    async def delete_model(self, model_id: str) -> Dict[str, Any]:
        """
        Delete a model from LiteLLM proxy via /model/delete endpoint.

        Args:
            model_id: Name of the model to delete

        Returns:
            Response dict with 'status' and 'message' keys

        Raises:
            httpx.HTTPError: if request fails
        """
        url = f"{self.base_url}/model/delete"
        headers = self._get_auth_headers()

        payload = {"model_id": model_id}

        logger.info(f"Deleting model from LiteLLM: {model_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Successfully deleted model {model_id}")
                return result
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to delete model {model_id}: {e.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise
        except httpx.RequestError as e:
            error_msg = f"Request failed when deleting model {model_id}: {str(e)}"
            logger.error(error_msg)
            raise

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for LiteLLM API requests.

        Returns:
            Dict with Authorization header
        """
        return {"Authorization": f"Bearer {self.master_key}"}
