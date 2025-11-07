"""BYOK (Bring Your Own Key) API Endpoints - Story 8.13.

FastAPI router providing BYOK management endpoints for tenants to enable/disable
BYOK mode, test provider keys, rotate keys, and revert to platform keys.

Endpoints:
- POST /api/tenants/{tenant_id}/byok/enable - Enable BYOK with validation
- POST /api/tenants/{tenant_id}/byok/test-keys - Test provider keys before enabling
- PUT /api/tenants/{tenant_id}/byok/rotate-keys - Rotate BYOK tenant's API keys
- POST /api/tenants/{tenant_id}/byok/disable - Disable BYOK and revert to platform keys
- GET /api/tenants/{tenant_id}/byok/status - Get BYOK status

All endpoints require admin authorization via X-Admin-Key header.
"""

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from loguru import logger

from src.config import settings
from src.database.session import get_async_session
from src.database.models import TenantConfig
from src.schemas.byok import (
    BYOKEnableRequest,
    BYOKEnableResponse,
    BYOKTestKeysRequest,
    BYOKTestKeysResponse,
    BYOKRotateKeysRequest,
    BYOKRotateKeysResponse,
    BYOKDisableResponse,
    BYOKStatusResponse,
    ProviderValidationResult,
)
from src.services.llm_service import LLMService, VirtualKeyCreationError, VirtualKeyRotationError
from src.services.tenant_service import TenantService
from src.utils.encryption import encrypt, decrypt


# Create router
router = APIRouter(
    prefix="/api/tenants",
    tags=["BYOK"],
)


async def require_admin(x_admin_key: str = Header(...)) -> None:
    """
    Validate admin authorization via X-Admin-Key header.

    All BYOK endpoints require this authorization. Reuses pattern from Story 8.12.

    Args:
        x_admin_key: Admin key from request header

    Raises:
        HTTPException: 403 Forbidden if key doesn't match

    Example:
        >>> @router.post("/test")
        >>> async def test_endpoint(_: None = Depends(require_admin)):
        >>>     return {"status": "authorized"}
    """
    if x_admin_key != settings.admin_api_key:
        logger.warning(f"Unauthorized BYOK access attempt with key: {x_admin_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.post(
    "/{tenant_id}/byok/test-keys",
    response_model=BYOKTestKeysResponse,
    summary="Test Provider API Keys",
    description="Validate OpenAI and Anthropic API keys before enabling BYOK (AC#3)",
)
async def test_keys(
    tenant_id: str,
    request: BYOKTestKeysRequest,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> BYOKTestKeysResponse:
    """
    Test provider API keys without enabling BYOK mode (AC#3).

    Validates both OpenAI and Anthropic keys by calling their models endpoints.
    Returns validation results with available models for each provider.

    Args:
        tenant_id: Unique tenant identifier
        request: BYOKTestKeysRequest with keys to test
        db: Database session
        _: Admin authorization (required)

    Returns:
        BYOKTestKeysResponse with validation results per provider

    Raises:
        HTTPException: 403 Forbidden if not admin, 500 if validation fails
    """
    logger.info(f"Testing provider keys for tenant {tenant_id}")

    try:
        llm_service = LLMService(db)
        validation_result = await llm_service.validate_provider_keys(
            request.openai_key, request.anthropic_key
        )

        return BYOKTestKeysResponse(
            openai=ProviderValidationResult(
                valid=validation_result["openai"]["valid"],
                models=validation_result["openai"]["models"],
                error=validation_result["openai"]["error"],
            ),
            anthropic=ProviderValidationResult(
                valid=validation_result["anthropic"]["valid"],
                models=validation_result["anthropic"]["models"],
                error=validation_result["anthropic"]["error"],
            ),
        )

    except Exception as e:
        logger.error(f"Key validation failed for tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key validation failed: {str(e)}",
        )


@router.post(
    "/{tenant_id}/byok/enable",
    response_model=BYOKEnableResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enable BYOK Mode",
    description="Enable BYOK with validation, encryption, and virtual key creation (AC#1-4)",
)
async def enable_byok(
    tenant_id: str,
    request: BYOKEnableRequest,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> BYOKEnableResponse:
    """
    Enable BYOK mode for tenant with validation and encryption (AC#1-4).

    Validates tenant-provided API keys, encrypts them, creates BYOK virtual key,
    and updates tenant configuration.

    Args:
        tenant_id: Unique tenant identifier
        request: BYOKEnableRequest with OpenAI/Anthropic keys
        db: Database session
        _: Admin authorization (required)

    Returns:
        BYOKEnableResponse confirming BYOK enablement

    Raises:
        HTTPException: 403 Forbidden if not admin, 400 if validation fails
    """
    logger.info(f"Enabling BYOK for tenant {tenant_id}")

    try:
        # Validate keys
        llm_service = LLMService(db)
        validation = await llm_service.validate_provider_keys(
            request.openai_key, request.anthropic_key
        )

        # Check validation results
        if request.openai_key and not validation["openai"]["valid"]:
            raise ValueError(f"OpenAI key validation failed: {validation['openai']['error']}")
        if request.anthropic_key and not validation["anthropic"]["valid"]:
            raise ValueError(f"Anthropic key validation failed: {validation['anthropic']['error']}")

        # Create BYOK virtual key
        virtual_key = await llm_service.create_byok_virtual_key(
            tenant_id, request.openai_key, request.anthropic_key
        )

        # Encrypt and store keys
        stmt = (
            update(TenantConfig)
            .where(TenantConfig.tenant_id == tenant_id)
            .values(
                byok_enabled=True,
                byok_virtual_key=virtual_key,
            )
        )

        if request.openai_key:
            stmt = stmt.values(byok_openai_key_encrypted=encrypt(request.openai_key))
        if request.anthropic_key:
            stmt = stmt.values(byok_anthropic_key_encrypted=encrypt(request.anthropic_key))

        await db.execute(stmt)
        await db.commit()

        # Log audit entry
        providers = []
        if request.openai_key:
            providers.append("openai")
        if request.anthropic_key:
            providers.append("anthropic")

        await llm_service.log_audit_entry(
            action="BYOK_ENABLED",
            tenant_id=tenant_id,
            details={"providers_configured": providers},
        )

        logger.info(f"BYOK enabled for tenant {tenant_id} with providers: {providers}")

        return BYOKEnableResponse(
            success=True,
            virtual_key_created=True,
            message=f"BYOK enabled for tenant {tenant_id}",
            providers_configured=providers,
        )

    except VirtualKeyCreationError as e:
        logger.error(f"Virtual key creation failed for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Virtual key creation failed: {str(e)}",
        )
    except ValueError as e:
        logger.warning(f"BYOK enablement validation failed for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error enabling BYOK for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable BYOK: {str(e)}",
        )


@router.put(
    "/{tenant_id}/byok/rotate-keys",
    response_model=BYOKRotateKeysResponse,
    summary="Rotate BYOK Keys",
    description="Rotate BYOK tenant's provider API keys and virtual key (AC#7)",
)
async def rotate_keys(
    tenant_id: str,
    request: BYOKRotateKeysRequest,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> BYOKRotateKeysResponse:
    """
    Rotate BYOK tenant's provider keys and virtual key (AC#7).

    Validates new keys, creates new BYOK virtual key, updates database,
    and logs rotation in audit trail.

    Args:
        tenant_id: Unique tenant identifier
        request: BYOKRotateKeysRequest with new provider keys
        db: Database session
        _: Admin authorization (required)

    Returns:
        BYOKRotateKeysResponse confirming key rotation

    Raises:
        HTTPException: 403 Forbidden if not admin, 400/500 if rotation fails
    """
    logger.info(f"Rotating BYOK keys for tenant {tenant_id}")

    try:
        llm_service = LLMService(db)

        # Rotate keys (validation happens inside)
        new_virtual_key = await llm_service.rotate_byok_keys(
            tenant_id, request.new_openai_key, request.new_anthropic_key
        )

        providers_updated = []
        if request.new_openai_key:
            providers_updated.append("openai")
        if request.new_anthropic_key:
            providers_updated.append("anthropic")

        logger.info(f"BYOK keys rotated for tenant {tenant_id}: {providers_updated}")

        return BYOKRotateKeysResponse(
            success=True,
            new_virtual_key_created=True,
            message=f"Keys rotated for tenant {tenant_id}",
            providers_updated=providers_updated,
        )

    except VirtualKeyRotationError as e:
        logger.error(f"Key rotation failed for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key rotation failed: {str(e)}",
        )
    except ValueError as e:
        logger.warning(f"Key rotation validation failed for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error rotating keys for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key rotation failed: {str(e)}",
        )


@router.post(
    "/{tenant_id}/byok/disable",
    response_model=BYOKDisableResponse,
    summary="Disable BYOK and Revert to Platform Keys",
    description="Disable BYOK mode and revert tenant to platform keys (AC#8)",
)
async def disable_byok(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> BYOKDisableResponse:
    """
    Disable BYOK and revert tenant to platform keys (AC#8).

    Deletes BYOK virtual key, creates platform virtual key, clears BYOK columns.

    Args:
        tenant_id: Unique tenant identifier
        db: Database session
        _: Admin authorization (required)

    Returns:
        BYOKDisableResponse confirming reversion to platform keys

    Raises:
        HTTPException: 403 Forbidden if not admin, 400/500 if reversion fails
    """
    logger.info(f"Disabling BYOK for tenant {tenant_id}")

    try:
        llm_service = LLMService(db)

        # Revert to platform keys
        platform_virtual_key = await llm_service.revert_to_platform_keys(tenant_id)

        logger.info(f"BYOK disabled for tenant {tenant_id}, reverted to platform keys")

        return BYOKDisableResponse(
            success=True,
            reverted_to_platform=True,
            message=f"BYOK disabled for tenant {tenant_id}. Reverted to platform keys.",
        )

    except VirtualKeyCreationError as e:
        logger.error(f"Reversion to platform keys failed for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reversion failed: {str(e)}",
        )
    except ValueError as e:
        logger.warning(f"Reversion validation failed for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error disabling BYOK for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable BYOK: {str(e)}",
        )


@router.get(
    "/{tenant_id}/byok/status",
    response_model=BYOKStatusResponse,
    summary="Get BYOK Status",
    description="Get BYOK status and configuration for tenant (AC#6)",
)
async def get_byok_status(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_admin),
) -> BYOKStatusResponse:
    """
    Get BYOK status and configuration for tenant (AC#6).

    Returns whether BYOK is enabled, which providers are configured, and
    when BYOK was enabled. Used for dashboard status display.

    Args:
        tenant_id: Unique tenant identifier
        db: Database session
        _: Admin authorization (required)

    Returns:
        BYOKStatusResponse with current BYOK status

    Raises:
        HTTPException: 403 Forbidden if not admin, 404 if tenant not found
    """
    logger.info(f"Getting BYOK status for tenant {tenant_id}")

    try:
        tenant_service = TenantService(db)
        byok_status = await tenant_service.get_byok_status(tenant_id)

        return BYOKStatusResponse(
            byok_enabled=byok_status["byok_enabled"],
            providers_configured=byok_status["providers_configured"],
            enabled_at=byok_status["enabled_at"],
            cost_tracking_mode=byok_status["cost_tracking_mode"],
        )

    except ValueError as e:
        logger.warning(f"Tenant not found: {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting BYOK status for {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get BYOK status: {str(e)}",
        )
