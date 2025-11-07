"""
Admin API endpoints for LLM provider configuration management.

Provides CRUD operations for managing LLM providers (OpenAI, Anthropic, Azure OpenAI, etc.)
including API key encryption, connection testing, and litellm-config.yaml generation.
All endpoints require admin API key authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.schemas.provider import (
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProviderResponse,
    ConnectionTestResponse,
    ConfigRegenerationResponse,
    LLMModelResponse,
)
from src.services.provider_service import ProviderService
from src.services.model_service import ModelService
from src.services.litellm_config_generator import ConfigGenerator
from src.database.session import get_async_session
from src.cache.redis_client import get_redis_client
from src.config import get_settings
from src.utils.logger import logger
from src.utils.exceptions import ProviderNotFoundException
from src.api.utils.error_handlers import handle_provider_errors, handle_model_errors

router = APIRouter(prefix="/api/llm-providers", tags=["llm-providers"])


async def require_admin(
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    settings=Depends(get_settings),
) -> None:
    """
    Verify admin API key for LLM provider management.

    Args:
        x_admin_key: Admin API key from X-Admin-Key header
        settings: Application settings with admin key

    Raises:
        HTTPException(401): If API key is missing or invalid
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Admin-Key header",
        )

    if x_admin_key != settings.admin_api_key:
        logger.warning(
            "Admin endpoint accessed with invalid API key",
            extra={"endpoint": "api/llm-providers"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


@router.post(
    "",
    response_model=LLMProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new LLM provider",
    description="Creates a new LLM provider configuration (OpenAI, Anthropic, Azure OpenAI, etc.). "
    "API keys are encrypted before storage using Fernet encryption. "
    "Requires admin authentication via X-Admin-Key header.",
)
@handle_provider_errors("create provider")
async def create_provider(
    provider: LLMProviderCreate,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> LLMProviderResponse:
    """
    Create a new LLM provider configuration.

    Args:
        provider: Provider configuration data with API key
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        LLMProviderResponse: Created provider with masked API key
    """
    provider_service = ProviderService(db, redis_client)

    created_provider = await provider_service.create_provider(provider)

    logger.info(
        "Provider created",
        extra={
            "provider_id": created_provider.id,
            "provider_name": created_provider.name,
            "provider_type": created_provider.provider_type,
        },
    )

    return LLMProviderResponse.model_validate(created_provider)


@router.get(
    "",
    response_model=List[LLMProviderResponse],
    summary="List all LLM providers",
    description="Returns a list of all configured LLM providers with connection status. "
    "Supports pagination and filtering by enabled status. "
    "Results are cached in Redis for 60 seconds.",
)
@handle_provider_errors("list providers")
async def list_providers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    include_disabled: bool = Query(False, description="Include disabled providers"),
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> List[LLMProviderResponse]:
    """
    List all LLM provider configurations.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        include_disabled: Whether to include disabled providers
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        List[LLMProviderResponse]: List of providers with masked API keys
    """
    provider_service = ProviderService(db, redis_client)

    providers = await provider_service.list_providers(
        include_disabled=include_disabled,
        skip=skip,
        limit=limit,
    )

    return [LLMProviderResponse.model_validate(p) for p in providers]


@router.get(
    "/{provider_id}",
    response_model=LLMProviderResponse,
    summary="Get LLM provider details",
    description="Returns full details for a specific LLM provider including masked API key. "
    "Connection status is determined by last test timestamp and result.",
)
@handle_provider_errors("get provider")
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> LLMProviderResponse:
    """
    Get details for a specific LLM provider.

    Args:
        provider_id: Provider database ID
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        LLMProviderResponse: Provider details with masked API key
    """
    provider_service = ProviderService(db, redis_client)

    provider = await provider_service.get_provider(provider_id)

    if not provider:
        raise ProviderNotFoundException(f"Provider {provider_id} not found")

    return LLMProviderResponse.model_validate(provider)


@router.put(
    "/{provider_id}",
    response_model=LLMProviderResponse,
    summary="Update LLM provider configuration",
    description="Updates an existing LLM provider. If API key is provided, it will be re-encrypted. "
    "Invalidates provider list cache on success.",
)
@handle_provider_errors("update provider")
async def update_provider(
    provider_id: int,
    provider_update: LLMProviderUpdate,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> LLMProviderResponse:
    """
    Update an existing LLM provider configuration.

    Args:
        provider_id: Provider database ID
        provider_update: Fields to update (partial update)
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        LLMProviderResponse: Updated provider with masked API key
    """
    provider_service = ProviderService(db, redis_client)

    updated_provider = await provider_service.update_provider(
        provider_id, provider_update
    )

    logger.info(
        "Provider updated",
        extra={
            "provider_id": provider_id,
            "updated_fields": provider_update.model_dump(exclude_unset=True).keys(),
        },
    )

    return LLMProviderResponse.model_validate(updated_provider)


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete LLM provider (soft delete)",
    description="Soft deletes an LLM provider by setting enabled=false. "
    "Cascades to all associated models. Does not physically remove from database.",
)
@handle_provider_errors("delete provider")
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> None:
    """
    Soft delete an LLM provider (sets enabled=false).

    Args:
        provider_id: Provider database ID
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)
    """
    provider_service = ProviderService(db, redis_client)

    await provider_service.delete_provider(provider_id)

    logger.info(
        "Provider deleted (soft delete)",
        extra={"provider_id": provider_id},
    )


@router.post(
    "/{provider_id}/test-connection",
    response_model=ConnectionTestResponse,
    summary="Test LLM provider connection",
    description="Validates API key and tests connection to provider endpoint. "
    "Fetches available models from provider API. Updates last_test_at and last_test_success. "
    "Timeout: 10 seconds per provider.",
)
@handle_provider_errors("test provider connection")
async def test_provider_connection(
    provider_id: int,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> ConnectionTestResponse:
    """
    Test connection to LLM provider and fetch available models.

    Args:
        provider_id: Provider database ID
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        ConnectionTestResponse: Test results with success status, available models, response time
    """
    provider_service = ProviderService(db, redis_client)

    result = await provider_service.test_provider_connection(provider_id)

    logger.info(
        "Provider connection tested",
        extra={
            "provider_id": provider_id,
            "success": result.success,
            "model_count": len(result.models),
        },
    )

    return result


@router.get(
    "/{provider_id}/models",
    response_model=List[LLMModelResponse],
    summary="Get models for LLM provider",
    description="Returns all models configured for this provider. "
    "Includes both enabled and disabled models with pricing and configuration.",
)
@handle_model_errors("get provider models")
async def get_provider_models(
    provider_id: int,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> List[LLMModelResponse]:
    """
    Get all models for a specific provider.

    Args:
        provider_id: Provider database ID
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        List[LLMModelResponse]: List of models for this provider
    """
    model_service = ModelService(db)

    models = await model_service.list_models_by_provider(
        provider_id=provider_id,
        enabled_only=False,
    )

    return [LLMModelResponse.model_validate(m) for m in models]


@router.post(
    "/{provider_id}/sync-models",
    response_model=dict,
    summary="Sync models from provider API",
    description="Fetches latest available models from provider API and creates/updates database entries. "
    "Useful after adding a new provider or when provider adds new models.",
)
@handle_model_errors("sync models")
async def sync_provider_models(
    provider_id: int,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> dict:
    """
    Sync models from provider API to database.

    Args:
        provider_id: Provider database ID
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        dict: Sync results with counts of created/updated/skipped models
    """
    provider_service = ProviderService(db, redis_client)
    model_service = ModelService(db)

    # Test connection to fetch available models
    test_result = await provider_service.test_provider_connection(provider_id)

    if not test_result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot sync models: {test_result.error or 'Connection test failed'}",
        )

    # Sync models to database
    sync_result = await model_service.sync_models_from_provider(
        provider_id=provider_id,
        available_models=test_result.models,
    )

    logger.info(
        "Models synced from provider",
        extra={
            "provider_id": provider_id,
            **sync_result,
        },
    )

    return {
        "success": True,
        "provider_id": provider_id,
        "total_available": len(test_result.models),
        **sync_result,
    }


@router.post(
    "/regenerate-config",
    response_model=ConfigRegenerationResponse,
    summary="Regenerate litellm-config.yaml",
    description="Reads enabled providers and models from database, generates new litellm-config.yaml. "
    "Creates timestamped backup before overwriting. Validates YAML syntax. "
    "⚠️  LiteLLM proxy restart required for changes to take effect.",
)
@handle_provider_errors("regenerate config")
async def regenerate_config(
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> ConfigRegenerationResponse:
    """
    Regenerate litellm-config.yaml from database state.

    Args:
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        ConfigRegenerationResponse: Regeneration results with backup path and restart command
    """
    config_generator = ConfigGenerator(db)

    result = await config_generator.regenerate_config()

    logger.info(
        "LiteLLM config regenerated",
        extra={
            "backup_path": result["backup_path"],
            "config_path": result["config_path"],
        },
    )

    return ConfigRegenerationResponse(**result)
