"""
Admin API endpoints for LLM model configuration management.

Provides CRUD operations for managing LLM models including pricing configuration,
enable/disable toggles, and bulk operations. All endpoints require admin authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.schemas.provider import (
    LLMModelCreate,
    LLMModelUpdate,
    LLMModelResponse,
    BulkModelOperation,
    BulkModelOperationResponse,
)
from src.services.model_service import ModelService
from src.database.session import get_async_session
from src.config import get_settings
from src.utils.logger import logger
from src.utils.exceptions import ModelNotFoundException

router = APIRouter(prefix="/api/llm-models", tags=["llm-models"])


async def require_admin(
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    settings=Depends(get_settings),
) -> None:
    """
    Verify admin API key for LLM model management.

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
            extra={"endpoint": "api/llm-models"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


@router.post(
    "",
    response_model=LLMModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new LLM model",
    description="Creates a new LLM model entry for a provider with pricing and configuration. "
    "Validates positive pricing and context window. Requires admin authentication.",
)
async def create_model(
    model: LLMModelCreate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> LLMModelResponse:
    """
    Create a new LLM model configuration.

    Args:
        model: Model configuration data with pricing
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        LLMModelResponse: Created model with full configuration

    Raises:
        HTTPException(400): If validation fails (negative pricing, invalid context window)
        HTTPException(409): If model name already exists for this provider
        HTTPException(500): If database operation fails
    """
    # Validation (AC5.8)
    if model.cost_per_input_token is not None and model.cost_per_input_token < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cost_per_input_token must be positive",
        )

    if model.cost_per_output_token is not None and model.cost_per_output_token < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cost_per_output_token must be positive",
        )

    if model.context_window is not None and model.context_window <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="context_window must be greater than 0",
        )

    model_service = ModelService(db)

    try:
        created_model = await model_service.create_model(
            provider_id=model.provider_id,
            model_name=model.model_name,
            display_name=model.display_name,
            enabled=model.enabled,
            cost_per_input_token=model.cost_per_input_token,
            cost_per_output_token=model.cost_per_output_token,
            context_window=model.context_window,
            capabilities=model.capabilities,
        )

        logger.info(
            "Model created",
            extra={
                "model_id": created_model.id,
                "model_name": created_model.model_name,
                "provider_id": model.provider_id,
            },
        )

        return LLMModelResponse.model_validate(created_model)

    except ValueError as e:
        logger.error(f"Model creation validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Model creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create model: {str(e)}",
        )


@router.get(
    "/{model_id}",
    response_model=LLMModelResponse,
    summary="Get LLM model details",
    description="Returns full details for a specific LLM model including pricing configuration.",
)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> LLMModelResponse:
    """
    Get details for a specific LLM model.

    Args:
        model_id: Model database ID
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        LLMModelResponse: Model details with full configuration

    Raises:
        HTTPException(404): If model not found
        HTTPException(500): If database operation fails
    """
    model_service = ModelService(db)

    try:
        model = await model_service.get_model(model_id)

        if not model:
            raise ModelNotFoundException(f"Model {model_id} not found")

        return LLMModelResponse.model_validate(model)

    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model: {str(e)}",
        )


@router.put(
    "/{model_id}",
    response_model=LLMModelResponse,
    summary="Update LLM model configuration",
    description="Updates an existing LLM model including pricing, display name, and context window. "
    "Validates positive pricing and context window.",
)
async def update_model(
    model_id: int,
    model_update: LLMModelUpdate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> LLMModelResponse:
    """
    Update an existing LLM model configuration.

    Args:
        model_id: Model database ID
        model_update: Fields to update (partial update)
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        LLMModelResponse: Updated model with full configuration

    Raises:
        HTTPException(400): If validation fails (negative pricing, invalid context window)
        HTTPException(404): If model not found
        HTTPException(500): If update operation fails
    """
    # Validation (AC5.8)
    update_data = model_update.model_dump(exclude_unset=True)

    if "cost_per_input_token" in update_data and update_data["cost_per_input_token"] is not None:
        if update_data["cost_per_input_token"] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cost_per_input_token must be positive",
            )

    if "cost_per_output_token" in update_data and update_data["cost_per_output_token"] is not None:
        if update_data["cost_per_output_token"] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cost_per_output_token must be positive",
            )

    if "context_window" in update_data and update_data["context_window"] is not None:
        if update_data["context_window"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="context_window must be greater than 0",
            )

    model_service = ModelService(db)

    try:
        updated_model = await model_service.update_model(
            model_id=model_id,
            **update_data,
        )

        logger.info(
            "Model updated",
            extra={
                "model_id": model_id,
                "updated_fields": update_data.keys(),
            },
        )

        return LLMModelResponse.model_validate(updated_model)

    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model: {str(e)}",
        )


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete LLM model (soft delete)",
    description="Soft deletes an LLM model by setting enabled=false. "
    "Does not physically remove from database.",
)
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> None:
    """
    Soft delete an LLM model (sets enabled=false).

    Args:
        model_id: Model database ID
        db: Database session
        _: Admin authentication (dependency)

    Raises:
        HTTPException(404): If model not found
        HTTPException(500): If delete operation fails
    """
    model_service = ModelService(db)

    try:
        await model_service.delete_model(model_id)

        logger.info(
            "Model deleted (soft delete)",
            extra={"model_id": model_id},
        )

    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to delete model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {str(e)}",
        )


@router.post(
    "/{model_id}/toggle",
    response_model=LLMModelResponse,
    summary="Toggle LLM model enabled status",
    description="Toggles the enabled status of an LLM model (enabled <-> disabled). "
    "Useful for quick enable/disable operations from UI.",
)
async def toggle_model(
    model_id: int,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> LLMModelResponse:
    """
    Toggle LLM model enabled status.

    Args:
        model_id: Model database ID
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        LLMModelResponse: Model with toggled enabled status

    Raises:
        HTTPException(404): If model not found
        HTTPException(500): If toggle operation fails
    """
    model_service = ModelService(db)

    try:
        toggled_model = await model_service.toggle_model(model_id)

        logger.info(
            "Model toggled",
            extra={
                "model_id": model_id,
                "new_enabled_status": toggled_model.enabled,
            },
        )

        return LLMModelResponse.model_validate(toggled_model)

    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to toggle model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle model: {str(e)}",
        )


@router.post(
    "/bulk-enable",
    response_model=BulkModelOperationResponse,
    summary="Bulk enable LLM models",
    description="Enables multiple LLM models at once. Returns count of successful operations.",
)
async def bulk_enable_models(
    operation: BulkModelOperation,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> BulkModelOperationResponse:
    """
    Bulk enable multiple LLM models.

    Args:
        operation: Model IDs to enable
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        BulkModelOperationResponse: Success count and any error messages

    Raises:
        HTTPException(500): If bulk operation fails
    """
    model_service = ModelService(db)

    try:
        result = await model_service.bulk_enable_models(operation.model_ids)

        logger.info(
            "Bulk enable models",
            extra={
                "model_ids": operation.model_ids,
                "success_count": result["success_count"],
            },
        )

        return BulkModelOperationResponse(**result)

    except Exception as e:
        logger.error(f"Failed to bulk enable models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk enable models: {str(e)}",
        )


@router.post(
    "/bulk-disable",
    response_model=BulkModelOperationResponse,
    summary="Bulk disable LLM models",
    description="Disables multiple LLM models at once. Returns count of successful operations.",
)
async def bulk_disable_models(
    operation: BulkModelOperation,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> BulkModelOperationResponse:
    """
    Bulk disable multiple LLM models.

    Args:
        operation: Model IDs to disable
        db: Database session
        _: Admin authentication (dependency)

    Returns:
        BulkModelOperationResponse: Success count and any error messages

    Raises:
        HTTPException(500): If bulk operation fails
    """
    model_service = ModelService(db)

    try:
        result = await model_service.bulk_disable_models(operation.model_ids)

        logger.info(
            "Bulk disable models",
            extra={
                "model_ids": operation.model_ids,
                "success_count": result["success_count"],
            },
        )

        return BulkModelOperationResponse(**result)

    except Exception as e:
        logger.error(f"Failed to bulk disable models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk disable models: {str(e)}",
        )
