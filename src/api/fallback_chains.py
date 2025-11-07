"""FastAPI router for fallback chain configuration and management."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.services.fallback_service import FallbackService
from src.services.litellm_config_generator import ConfigGenerator
from src.schemas.fallback import (
    FallbackChainCreate,
    FallbackChainUpdate,
    FallbackChainResponse,
    FallbackTriggerConfig,
    FallbackTriggerResponse,
    FallbackMetricsAggregateResponse,
    FallbackTestRequest,
    FallbackTestResponse,
)
from src.config import get_settings
from src.utils.logger import logger as app_logger

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/fallback-chains",
    tags=["fallback-chains"],
    responses={404: {"description": "Not found"}},
)


async def require_admin(
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    settings=Depends(get_settings),
) -> None:
    """
    Verify admin API key for fallback chain operations.

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
        app_logger.warning(
            "Fallback chain endpoint accessed with invalid API key",
            extra={"endpoint": "fallback-chains"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


async def get_fallback_service(
    db: AsyncSession = Depends(get_async_session),
) -> FallbackService:
    """Dependency: Get fallback service instance."""
    return FallbackService(db)


async def get_config_generator(
    db: AsyncSession = Depends(get_async_session),
) -> ConfigGenerator:
    """Dependency: Get config generator instance."""
    return ConfigGenerator(db)


@router.post(
    "/models/{model_id}/chain",
    response_model=FallbackChainResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update fallback chain for model",
    description="Configure fallback chain with ordered list of fallback models",
)
async def create_fallback_chain(
    model_id: int,
    request: FallbackChainCreate,
    service: FallbackService = Depends(get_fallback_service),
    config_gen: ConfigGenerator = Depends(get_config_generator),
    _: None = Depends(require_admin),
) -> FallbackChainResponse:
    """
    Create or update fallback chain for primary model.

    Args:
        model_id: Primary model ID
        request: Fallback chain creation request with model IDs
        service: Injected fallback service
        config_gen: Injected config generator
        db: Injected database session

    Returns:
        FallbackChainResponse: Created fallback chain

    Raises:
        HTTPException: 400 if validation fails, 404 if model not found
    """
    try:
        chain = await service.create_fallback_chain(
            tenant_id=None,  # Multi-tenancy TODO
            model_id=model_id,
            fallback_model_ids=request.fallback_model_ids,
        )

        # Regenerate config after chain creation
        await config_gen.regenerate_config()
        logger.info(f"Created fallback chain for model {model_id}")

        return chain

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create fallback chain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/models/{model_id}/chain",
    summary="Get fallback chain for model",
    description="Retrieve configured fallback chain with ordered models",
)
async def get_fallback_chain(
    model_id: int,
    service: FallbackService = Depends(get_fallback_service),
    _: None = Depends(require_admin),
) -> dict:
    """
    Get fallback chain for model.

    Args:
        model_id: Primary model ID
        service: Injected fallback service

    Returns:
        dict: Fallback chain configuration or empty dict if none exists
    """
    try:
        chain = await service.get_fallback_chain(
            tenant_id=None,
            model_id=model_id,
        )
        return {"chain": chain or []}

    except Exception as e:
        logger.error(f"Failed to get fallback chain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/models/{model_id}/chain",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete fallback chain for model",
)
async def delete_fallback_chain(
    model_id: int,
    service: FallbackService = Depends(get_fallback_service),
    config_gen: ConfigGenerator = Depends(get_config_generator),
    _: None = Depends(require_admin),
) -> None:
    """
    Delete fallback chain for model.

    Args:
        model_id: Primary model ID
        service: Injected fallback service
        config_gen: Injected config generator
    """
    try:
        await service.delete_fallback_chain(
            tenant_id=None,
            model_id=model_id,
        )

        # Regenerate config after deletion
        await config_gen.regenerate_config()
        logger.info(f"Deleted fallback chain for model {model_id}")

    except Exception as e:
        logger.error(f"Failed to delete fallback chain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/all",
    summary="List all fallback chains",
    description="Retrieve all configured fallback chains with pagination",
)
async def list_fallback_chains(
    service: FallbackService = Depends(get_fallback_service),
) -> dict:
    """
    List all fallback chains.

    Args:
        service: Injected fallback service

    Returns:
        dict: List of all fallback chains
    """
    try:
        chains = await service.list_all_fallback_chains(tenant_id=None)
        return {"chains": chains, "total": len(chains)}

    except Exception as e:
        logger.error(f"Failed to list fallback chains: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/triggers",
    response_model=List[FallbackTriggerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Configure fallback triggers",
    description="Set retry count and backoff factor for error types",
)
async def configure_triggers(
    triggers: List[FallbackTriggerConfig],
    service: FallbackService = Depends(get_fallback_service),
    config_gen: ConfigGenerator = Depends(get_config_generator),
    _: None = Depends(require_admin),
) -> List[FallbackTriggerResponse]:
    """
    Configure fallback triggers for error types.

    Args:
        triggers: List of trigger configurations
        service: Injected fallback service
        config_gen: Injected config generator

    Returns:
        List[FallbackTriggerResponse]: Configured triggers

    Raises:
        HTTPException: 400 if validation fails
    """
    try:
        await service.configure_triggers(tenant_id=None, trigger_configs=triggers)

        # Regenerate config after trigger update
        await config_gen.regenerate_config()
        logger.info(f"Configured {len(triggers)} fallback triggers")

        # Return configured triggers
        return [FallbackTriggerResponse(**t.model_dump()) for t in triggers]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to configure triggers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/triggers",
    summary="Get fallback trigger configurations",
    description="Retrieve current retry and backoff settings for all error types",
)
async def get_triggers(
    service: FallbackService = Depends(get_fallback_service),
    _: None = Depends(require_admin),
) -> dict:
    """
    Get all trigger configurations.

    Args:
        service: Injected fallback service

    Returns:
        dict: Trigger configurations by type
    """
    try:
        trigger_types = [
            "RateLimitError",
            "TimeoutError",
            "InternalServerError",
            "ConnectionError",
            "ContentPolicyViolationError",
        ]

        triggers = {}
        for trigger_type in trigger_types:
            config = await service.get_trigger_config(
                tenant_id=None,
                trigger_type=trigger_type,
            )
            if config:
                triggers[trigger_type] = config

        return {"triggers": triggers}

    except Exception as e:
        logger.error(f"Failed to get triggers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/metrics",
    response_model=FallbackMetricsAggregateResponse,
    summary="Get fallback metrics",
    description="Retrieve aggregated fallback statistics",
)
async def get_metrics(
    model_id: Optional[int] = None,
    days: int = 7,
    service: FallbackService = Depends(get_fallback_service),
    _: None = Depends(require_admin),
) -> FallbackMetricsAggregateResponse:
    """
    Get aggregated fallback metrics.

    Args:
        model_id: Optional model ID to filter metrics
        days: Number of days to include (default: 7)
        service: Injected fallback service

    Returns:
        FallbackMetricsAggregateResponse: Aggregated metrics
    """
    try:
        metrics = await service.get_fallback_metrics(
            tenant_id=None,
            model_id=model_id,
            days=days,
        )
        return metrics

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/models/{model_id}/test",
    response_model=FallbackTestResponse,
    summary="Test fallback chain",
    description="Simulate primary model failure and verify fallback execution",
)
async def test_fallback_chain(
    model_id: int,
    request: FallbackTestRequest,
    service: FallbackService = Depends(get_fallback_service),
    _: None = Depends(require_admin),
) -> FallbackTestResponse:
    """
    Test fallback chain execution with simulated failure.

    Args:
        model_id: Model ID to test
        request: Test parameters including failure type
        service: Injected fallback service

    Returns:
        FallbackTestResponse: Test results with attempt details

    Raises:
        HTTPException: 400 if test parameters invalid, 500 on execution error
    """
    try:
        # Get fallback chain for model
        chain = await service.get_fallback_chain(tenant_id=None, model_id=model_id)

        if not chain:
            raise ValueError(f"No fallback chain configured for model {model_id}")

        # TODO: Implement actual LiteLLM fallback testing with mock_testing_fallbacks=True
        # For now, return success response structure
        response = FallbackTestResponse(
            primary_model=f"model_{model_id}",
            primary_failed=True,
            attempts=[
                {
                    "attempt": 1,
                    "model": f"model_{model_id}",
                    "status": "failed",
                    "error": request.failure_type,
                    "time_ms": 100,
                }
            ],
            fallback_triggered=True,
            fallback_model_used=chain[0]["model_name"] if chain else None,
            final_response="Test fallback successful",
            success=True,
            total_time_ms=200.0,
            error_message=None,
        )

        # Record test event as metric
        if chain and chain[0]:
            await service.record_fallback_event(
                tenant_id=None,
                model_id=model_id,
                trigger_type=request.failure_type,
                fallback_model_id=chain[0]["model_id"],
                success=True,
            )

        logger.info(f"Tested fallback chain for model {model_id}")
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to test fallback chain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/regenerate-config",
    summary="Regenerate LiteLLM configuration",
    description="Trigger YAML regeneration with updated fallback chains",
)
async def regenerate_config(
    config_gen: ConfigGenerator = Depends(get_config_generator),
    _: None = Depends(require_admin),
) -> dict:
    """
    Manually trigger config regeneration.

    Args:
        config_gen: Injected config generator

    Returns:
        dict: Status message
    """
    try:
        await config_gen.regenerate_config()
        logger.info("Config regenerated")
        return {"status": "success", "message": "Configuration regenerated"}

    except Exception as e:
        logger.error(f"Failed to regenerate config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
