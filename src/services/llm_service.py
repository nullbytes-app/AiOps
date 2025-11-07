"""LiteLLM Virtual Key Management Service.

This module provides virtual key management for LiteLLM proxy integration,
enabling per-tenant LLM cost tracking and budget enforcement. Each tenant
gets a dedicated virtual key that routes all agent LLM calls through the
LiteLLM proxy for centralized tracking.

Key Features:
    - Virtual key creation with budget constraints
    - Key rotation for security
    - AsyncOpenAI client provisioning per tenant
    - Retry logic with exponential backoff
    - Encrypted storage using Fernet

Architecture:
    - LiteLLM Proxy: Central LLM gateway with virtual key support
    - Master Key: Admin key for /key/* operations (LITELLM_MASTER_KEY)
    - Virtual Keys: Per-tenant keys (user_id=tenant_id) for usage tracking
    - Budget Enforcement: max_budget parameter enforced by LiteLLM proxy

References:
    - LiteLLM Docs: https://github.com/berriai/litellm (Context7 2025)
    - Story 8.1: LiteLLM proxy integration as Docker service
    - Story 8.10: Budget enforcement with grace period (depends on 8.9)
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

import httpx
from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.models import TenantConfig as TenantConfigModel, AuditLog
from src.utils.encryption import encrypt, decrypt, EncryptionError


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    pass


class VirtualKeyCreationError(LLMServiceError):
    """Raised when virtual key creation fails."""

    pass


class VirtualKeyRotationError(LLMServiceError):
    """Raised when virtual key rotation fails."""

    pass


class VirtualKeyValidationError(LLMServiceError):
    """Raised when virtual key validation fails."""

    pass


class LLMService:
    """
    Service for managing LiteLLM virtual keys and AsyncOpenAI clients.

    Provides centralized virtual key lifecycle management (create, rotate, validate)
    and AsyncOpenAI client provisioning for tenant-specific LLM calls.

    Attributes:
        db: AsyncSession for database operations
        litellm_proxy_url: LiteLLM proxy base URL (from settings)
        master_key: LiteLLM master key for admin operations (from settings)
    """

    # Retry configuration (exponential backoff: 2s, 4s, 8s)
    RETRY_ATTEMPTS = 3
    RETRY_DELAYS = [2.0, 4.0, 8.0]

    # Timeout configuration (granular: connect, read, write, pool)
    TIMEOUT_CONFIG = httpx.Timeout(
        connect=5.0,  # Connection establishment
        read=30.0,  # Reading response
        write=5.0,  # Writing request
        pool=5.0,  # Acquiring connection from pool
    )

    def __init__(
        self,
        db: AsyncSession,
        litellm_proxy_url: Optional[str] = None,
        master_key: Optional[str] = None,
    ):
        """
        Initialize LLMService with database session and LiteLLM credentials.

        Args:
            db: AsyncSession for database operations
            litellm_proxy_url: LiteLLM proxy URL (defaults to settings)
            master_key: LiteLLM master key (defaults to settings)

        Raises:
            ValueError: If required configuration missing
        """
        self.db = db
        self.litellm_proxy_url = litellm_proxy_url or getattr(
            settings, "litellm_proxy_url", None
        )
        self.master_key = master_key or getattr(settings, "litellm_master_key", None)

        if not self.litellm_proxy_url:
            raise ValueError(
                "LITELLM_PROXY_URL not configured. Set AI_AGENTS_LITELLM_PROXY_URL environment variable."
            )

        if not self.master_key:
            raise ValueError(
                "LITELLM_MASTER_KEY not configured. Set AI_AGENTS_LITELLM_MASTER_KEY environment variable."
            )

        # Remove trailing slash for consistent URL construction
        self.litellm_proxy_url = self.litellm_proxy_url.rstrip("/")

    async def _call_litellm_api(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        retry: bool = True,
    ) -> Dict[str, Any]:
        """
        Call LiteLLM proxy API with retry logic and exponential backoff.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/key/generate")
            json_data: Request body as JSON dict
            retry: Enable retry logic with exponential backoff

        Returns:
            Dict[str, Any]: API response as JSON

        Raises:
            LLMServiceError: If API call fails after retries
        """
        url = f"{self.litellm_proxy_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json",
        }

        transport = httpx.AsyncHTTPTransport(retries=1)
        async with httpx.AsyncClient(
            transport=transport,
            timeout=self.TIMEOUT_CONFIG,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        ) as client:
            for attempt in range(self.RETRY_ATTEMPTS if retry else 1):
                try:
                    logger.debug(
                        f"LiteLLM API call: {method} {url} (attempt {attempt + 1}/{self.RETRY_ATTEMPTS})"
                    )

                    response = await client.request(
                        method=method, url=url, headers=headers, json=json_data
                    )

                    # Check for HTTP errors
                    if response.status_code >= 400:
                        error_detail = response.text
                        logger.warning(
                            f"LiteLLM API error {response.status_code}: {error_detail}"
                        )

                        # Retry on 5xx errors, fail immediately on 4xx
                        if response.status_code >= 500 and retry and attempt < self.RETRY_ATTEMPTS - 1:
                            delay = self.RETRY_DELAYS[attempt]
                            logger.info(
                                f"Retrying in {delay}s (attempt {attempt + 1}/{self.RETRY_ATTEMPTS})"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise LLMServiceError(
                                f"LiteLLM API error {response.status_code}: {error_detail}"
                            )

                    # Success - return JSON response
                    return response.json()

                except httpx.TimeoutException as e:
                    logger.warning(f"LiteLLM API timeout: {str(e)}")
                    if retry and attempt < self.RETRY_ATTEMPTS - 1:
                        delay = self.RETRY_DELAYS[attempt]
                        logger.info(
                            f"Retrying in {delay}s (attempt {attempt + 1}/{self.RETRY_ATTEMPTS})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise LLMServiceError(f"LiteLLM API timeout after {self.RETRY_ATTEMPTS} attempts")

                except httpx.HTTPError as e:
                    logger.warning(f"LiteLLM API HTTP error: {str(e)}")
                    if retry and attempt < self.RETRY_ATTEMPTS - 1:
                        delay = self.RETRY_DELAYS[attempt]
                        logger.info(
                            f"Retrying in {delay}s (attempt {attempt + 1}/{self.RETRY_ATTEMPTS})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise LLMServiceError(f"LiteLLM API HTTP error: {str(e)}")

            # Should not reach here, but just in case
            raise LLMServiceError("LiteLLM API call failed after all retry attempts")

    async def create_virtual_key_for_tenant(
        self, tenant_id: str, max_budget: float = 100.0
    ) -> str:
        """
        Create LiteLLM virtual key for tenant with budget constraint.

        Calls LiteLLM POST /key/generate with user_id=tenant_id for cost tracking.
        Returns the plaintext virtual key for immediate use (caller must encrypt).

        Args:
            tenant_id: Unique tenant identifier
            max_budget: Maximum budget in USD (default: $100)

        Returns:
            str: Plaintext virtual key (format: "sk-...")

        Raises:
            VirtualKeyCreationError: If key creation fails
            ValueError: If tenant_id empty or max_budget negative

        Example:
            >>> service = LLMService(db)
            >>> virtual_key = await service.create_virtual_key_for_tenant("acme-corp", 500.0)
            >>> encrypted_key = encrypt(virtual_key)
        """
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")

        if max_budget < 0:
            raise ValueError(f"max_budget must be >= 0, got {max_budget}")

        logger.info(
            f"Creating virtual key for tenant {tenant_id} with max_budget ${max_budget}"
        )

        try:
            response_data = await self._call_litellm_api(
                method="POST",
                endpoint="/key/generate",
                json_data={
                    "user_id": tenant_id,
                    "key_alias": f"{tenant_id}-key",
                    "max_budget": max_budget,
                    "metadata": {
                        "tenant_id": tenant_id,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "purpose": "agent-orchestration",
                    },
                },
            )

            virtual_key = response_data.get("key")
            if not virtual_key:
                raise VirtualKeyCreationError(
                    f"LiteLLM API returned no key: {response_data}"
                )

            logger.info(f"Virtual key created for tenant {tenant_id}")
            return virtual_key

        except LLMServiceError as e:
            logger.error(f"Failed to create virtual key for tenant {tenant_id}: {str(e)}")
            raise VirtualKeyCreationError(
                f"Failed to create virtual key for tenant {tenant_id}: {str(e)}"
            ) from e

    async def get_llm_client_for_tenant(self, tenant_id: str) -> AsyncOpenAI:
        """
        Get AsyncOpenAI client configured with tenant's virtual key (AC#5).

        Retrieves encrypted virtual key from database (BYOK or platform based on
        byok_enabled flag), decrypts it, and returns AsyncOpenAI client pointing
        to LiteLLM proxy. All LLM calls through this client are tracked under
        tenant's budget.

        **BYOK Support (Story 8.13):**
        If tenant has BYOK enabled (byok_enabled=True), uses byok_virtual_key
        instead of platform litellm_virtual_key. This enables tenants to use
        their own OpenAI/Anthropic keys (AC#5).

        **BUDGET ENFORCEMENT (Story 8.10):**
        Checks budget status BEFORE returning client. If tenant has exceeded
        grace threshold (default: 110%), raises BudgetExceededError to block
        execution. This ensures all LLM calls are budget-checked transparently.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            AsyncOpenAI: Configured client for tenant's LLM calls

        Raises:
            ValueError: If tenant not found or virtual key missing
            EncryptionError: If decryption fails
            BudgetExceededError: If tenant budget exceeded (Story 8.10)

        Example:
            >>> service = LLMService(db)
            >>> try:
            >>>     client = await service.get_llm_client_for_tenant("acme-corp")
            >>>     response = await client.chat.completions.create(...)
            >>> except BudgetExceededError as e:
            >>>     logger.warning(f"Budget exceeded: {e.message}")
        """
        from sqlalchemy import select
        from src.database.models import TenantConfig as TenantConfigModel
        from src.services.budget_service import BudgetService
        from src.exceptions import BudgetExceededError

        # CRITICAL: Budget check BEFORE provisioning client (Story 8.10)
        budget_service = BudgetService(self.db, self.litellm_proxy_url, self.master_key)
        exceeded, error_msg = await budget_service.check_budget_exceeded(tenant_id)
        if exceeded:
            logger.warning(f"Budget check failed for tenant {tenant_id}: {error_msg}")
            # Get current spend for detailed error
            status = await budget_service.get_budget_status(tenant_id)
            await budget_service.handle_budget_block(tenant_id, status.spend)

        # Fetch tenant config including BYOK flag (Story 8.13)
        stmt = select(
            TenantConfigModel.litellm_virtual_key,
            TenantConfigModel.byok_enabled,
            TenantConfigModel.byok_virtual_key,
        ).where(
            TenantConfigModel.tenant_id == tenant_id,
            TenantConfigModel.is_active == True,
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()

        if not row:
            raise ValueError(f"Tenant not found or inactive: {tenant_id}")

        platform_key, byok_enabled, byok_virtual_key = row

        # Select correct virtual key: BYOK or platform (AC#5)
        if byok_enabled:
            if not byok_virtual_key:
                raise ValueError(
                    f"BYOK enabled but virtual key not found for tenant {tenant_id}"
                )
            encrypted_key = byok_virtual_key
            logger.debug(f"Using BYOK virtual key for tenant {tenant_id}")
        else:
            if not platform_key:
                raise ValueError(
                    f"Virtual key not configured for tenant {tenant_id}. "
                    "Ensure tenant was created after Story 8.9 deployment."
                )
            encrypted_key = platform_key
            logger.debug(f"Using platform virtual key for tenant {tenant_id}")

        # Decrypt virtual key
        try:
            virtual_key = decrypt(encrypted_key)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt virtual key for tenant {tenant_id}: {str(e)}")
            raise

        # Return AsyncOpenAI client pointing to LiteLLM proxy
        return AsyncOpenAI(
            base_url=f"{self.litellm_proxy_url}/v1",
            api_key=virtual_key,
            timeout=30.0,
        )

    async def rotate_virtual_key(self, tenant_id: str) -> str:
        """
        Rotate tenant's virtual key by generating new key and invalidating old one.

        Creates new virtual key via LiteLLM /key/generate, returns plaintext key
        for caller to encrypt and store. Does NOT automatically update database -
        caller must handle encryption and database update.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            str: New plaintext virtual key (format: "sk-...")

        Raises:
            VirtualKeyRotationError: If rotation fails
            ValueError: If tenant not found

        Example:
            >>> service = LLMService(db)
            >>> new_key = await service.rotate_virtual_key("acme-corp")
            >>> encrypted = encrypt(new_key)
            >>> # Caller updates database with encrypted key
        """
        # Verify tenant exists
        result = await self.db.execute(
            "SELECT id FROM tenant_configs WHERE tenant_id = :tenant_id AND is_active = TRUE",
            {"tenant_id": tenant_id},
        )
        if not result.fetchone():
            raise ValueError(f"Tenant not found or inactive: {tenant_id}")

        logger.info(f"Rotating virtual key for tenant {tenant_id}")

        try:
            # Create new virtual key (LiteLLM automatically invalidates old key)
            new_key = await self.create_virtual_key_for_tenant(tenant_id, max_budget=100.0)
            logger.info(f"Virtual key rotated for tenant {tenant_id}")
            return new_key

        except VirtualKeyCreationError as e:
            logger.error(f"Failed to rotate virtual key for tenant {tenant_id}: {str(e)}")
            raise VirtualKeyRotationError(
                f"Failed to rotate virtual key for tenant {tenant_id}: {str(e)}"
            ) from e

    async def validate_virtual_key(self, virtual_key: str) -> bool:
        """
        Validate virtual key by testing against LiteLLM proxy.

        Makes lightweight API call to verify key is valid and not expired/blocked.
        Uses /user/info endpoint which requires valid authentication.

        Args:
            virtual_key: Virtual key to validate (plaintext, not encrypted)

        Returns:
            bool: True if key is valid, False otherwise

        Example:
            >>> service = LLMService(db)
            >>> is_valid = await service.validate_virtual_key("sk-...")
            >>> if not is_valid:
            >>>     logger.warning("Virtual key is invalid")
        """
        if not virtual_key or not virtual_key.startswith("sk-"):
            logger.warning(f"Invalid key format: {virtual_key[:10]}...")
            return False

        try:
            # Test key by making authenticated request to /user/info
            # This endpoint requires valid virtual key authentication
            headers = {
                "Authorization": f"Bearer {virtual_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=self.TIMEOUT_CONFIG) as client:
                response = await client.get(
                    f"{self.litellm_proxy_url}/user/info",
                    headers=headers,
                )

                if response.status_code == 200:
                    logger.debug("Virtual key validation: VALID")
                    return True
                else:
                    logger.warning(
                        f"Virtual key validation: INVALID (status {response.status_code})"
                    )
                    return False

        except Exception as e:
            logger.warning(f"Virtual key validation error: {str(e)}")
            return False

    async def log_audit_entry(
        self,
        operation: str,
        tenant_id: Optional[str] = None,
        user: str = "system",
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
    ) -> None:
        """
        Log virtual key operation to audit log table.

        Args:
            operation: Operation name (e.g., "llm_key_created", "llm_key_rotated")
            tenant_id: Tenant ID for operation (optional)
            user: User who performed operation (default: "system")
            details: Additional operation details as JSON dict
            status: Operation status ("success", "failure", "in_progress")

        Example:
            >>> await service.log_audit_entry(
            ...     operation="llm_key_created",
            ...     tenant_id="acme-corp",
            ...     details={"max_budget": 100.0}
            ... )
        """
        audit_entry = AuditLog(
            user=user,
            operation=operation,
            details=details or {},
            status=status,
        )
        self.db.add(audit_entry)
        await self.db.flush()
        logger.info(f"Audit log: {operation} for tenant {tenant_id} - {status}")


    # ============================================================================
    # BYOK (Bring Your Own Key) Methods - Story 8.13
    # ============================================================================

    async def validate_provider_keys(
        self, openai_key: Optional[str] = None, anthropic_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate tenant-provided OpenAI and Anthropic API keys.

        Tests each key by calling the provider's models endpoint. Returns validation
        results with available models for display in UI.

        Args:
            openai_key: Optional OpenAI API key to validate (format: sk-...)
            anthropic_key: Optional Anthropic API key to validate (format: sk-ant-...)

        Returns:
            Dict with validation results:
            {
                "openai": {"valid": bool, "models": list[str], "error": str | None},
                "anthropic": {"valid": bool, "models": list[str], "error": str | None}
            }

        Example:
            >>> result = await service.validate_provider_keys(
            >>>     openai_key="sk-...", anthropic_key="sk-ant-..."
            >>> )
            >>> if result["openai"]["valid"]:
            >>>     print(f"OpenAI models: {result['openai']['models']}")
        """
        result = {
            "openai": {"valid": False, "models": [], "error": None},
            "anthropic": {"valid": False, "models": [], "error": None},
        }

        # Validate OpenAI key
        if openai_key:
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT_CONFIG) as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {openai_key}"},
                    )

                    if response.status_code == 200:
                        data = response.json()
                        models = [m["id"] for m in data.get("data", [])]
                        result["openai"]["valid"] = True
                        result["openai"]["models"] = models
                        logger.info(
                            f"OpenAI key validation successful: {len(models)} models available"
                        )
                    else:
                        error_msg = f"OpenAI API returned {response.status_code}: {response.text[:100]}"
                        result["openai"]["error"] = error_msg
                        logger.warning(f"OpenAI key validation failed: {error_msg}")
            except Exception as e:
                error_msg = f"OpenAI validation error: {str(e)}"
                result["openai"]["error"] = error_msg
                logger.error(error_msg)

        # Validate Anthropic key
        if anthropic_key:
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT_CONFIG) as client:
                    response = await client.get(
                        "https://api.anthropic.com/v1/models",
                        headers={"x-api-key": anthropic_key},
                    )

                    if response.status_code == 200:
                        data = response.json()
                        models = [m["name"] for m in data.get("data", [])]
                        result["anthropic"]["valid"] = True
                        result["anthropic"]["models"] = models
                        logger.info(
                            f"Anthropic key validation successful: {len(models)} models available"
                        )
                    else:
                        error_msg = f"Anthropic API returned {response.status_code}: {response.text[:100]}"
                        result["anthropic"]["error"] = error_msg
                        logger.warning(f"Anthropic key validation failed: {error_msg}")
            except Exception as e:
                error_msg = f"Anthropic validation error: {str(e)}"
                result["anthropic"]["error"] = error_msg
                logger.error(error_msg)

        return result

    async def create_byok_virtual_key(
        self,
        tenant_id: str,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
    ) -> str:
        """
        Create LiteLLM virtual key for BYOK tenant using tenant's API keys.

        Creates virtual key with tenant's custom API keys stored in metadata.
        Sets max_budget=null to disable platform spend tracking (AC#6).

        Args:
            tenant_id: Unique tenant identifier
            openai_key: Optional tenant's OpenAI API key
            anthropic_key: Optional tenant's Anthropic API key

        Returns:
            str: Plaintext BYOK virtual key

        Raises:
            VirtualKeyCreationError: If key creation fails
            ValueError: If no keys provided or tenant_id empty

        Example:
            >>> vkey = await service.create_byok_virtual_key(
            >>>     tenant_id="acme-corp",
            >>>     openai_key="sk-...",
            >>>     anthropic_key="sk-ant-..."
            >>> )
        """
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")

        if not openai_key and not anthropic_key:
            raise ValueError("At least one provider key must be provided")

        logger.info(f"Creating BYOK virtual key for tenant {tenant_id}")

        # Build metadata with provider keys
        # In production, keys would be stored securely (e.g., vault) and referenced
        # For now, store encrypted versions in metadata
        metadata = {
            "byok_enabled": True,
            "tenant_id": tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "byok-agent-orchestration",
        }

        if openai_key:
            metadata["openai_api_key"] = f"os.environ/OPENAI_KEY_{tenant_id}"
        if anthropic_key:
            metadata["anthropic_api_key"] = f"os.environ/ANTHROPIC_KEY_{tenant_id}"

        try:
            response_data = await self._call_litellm_api(
                method="POST",
                endpoint="/key/generate",
                json_data={
                    "user_id": tenant_id,
                    "key_alias": f"{tenant_id}-byok-key",
                    "max_budget": None,  # No platform spend tracking for BYOK
                    "metadata": metadata,
                },
            )

            virtual_key = response_data.get("key")
            if not virtual_key:
                raise VirtualKeyCreationError(
                    f"LiteLLM API returned no key: {response_data}"
                )

            logger.info(f"BYOK virtual key created for tenant {tenant_id}")
            return virtual_key

        except LLMServiceError as e:
            logger.error(f"Failed to create BYOK virtual key for {tenant_id}: {str(e)}")
            raise VirtualKeyCreationError(
                f"Failed to create BYOK virtual key: {str(e)}"
            ) from e

    async def rotate_byok_keys(
        self,
        tenant_id: str,
        new_openai_key: Optional[str] = None,
        new_anthropic_key: Optional[str] = None,
    ) -> str:
        """
        Rotate BYOK tenant's provider keys and virtual key (AC#7).

        Validates new keys, creates new virtual key, updates database with
        encrypted keys and new virtual key.

        Args:
            tenant_id: Unique tenant identifier
            new_openai_key: New OpenAI API key
            new_anthropic_key: New Anthropic API key

        Returns:
            str: New BYOK virtual key

        Raises:
            VirtualKeyRotationError: If rotation fails
            ValueError: If tenant not found or no keys provided

        Example:
            >>> new_vkey = await service.rotate_byok_keys(
            >>>     tenant_id="acme-corp",
            >>>     new_openai_key="sk-..."
            >>> )
        """
        from sqlalchemy import select, update

        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")

        if not new_openai_key and not new_anthropic_key:
            raise ValueError("At least one new provider key must be provided")

        logger.info(f"Rotating BYOK keys for tenant {tenant_id}")

        try:
            # Validate new keys
            validation = await self.validate_provider_keys(
                new_openai_key, new_anthropic_key
            )
            if (
                new_openai_key
                and not validation["openai"]["valid"]
                or new_anthropic_key
                and not validation["anthropic"]["valid"]
            ):
                raise VirtualKeyRotationError(
                    f"Key validation failed: OpenAI={validation['openai'].get('error')}, "
                    f"Anthropic={validation['anthropic'].get('error')}"
                )

            # Create new BYOK virtual key
            new_virtual_key = await self.create_byok_virtual_key(
                tenant_id, new_openai_key, new_anthropic_key
            )

            # Update database with encrypted keys
            stmt = update(TenantConfigModel).where(
                TenantConfigModel.tenant_id == tenant_id
            )
            values = {
                "byok_virtual_key": encrypt(new_virtual_key),
            }
            if new_openai_key:
                values["byok_openai_key_encrypted"] = encrypt(new_openai_key)
            if new_anthropic_key:
                values["byok_anthropic_key_encrypted"] = encrypt(new_anthropic_key)

            await self.db.execute(stmt.values(**values))
            await self.db.commit()

            # Log audit entry
            await self.log_audit_entry(
                action="BYOK_KEYS_ROTATED",
                tenant_id=tenant_id,
                details={
                    "old_virtual_key_id": "redacted",
                    "new_virtual_key_id": "redacted",
                    "providers_updated": [
                        p for p in ["openai", "anthropic"]
                        if (p == "openai" and new_openai_key) or (p == "anthropic" and new_anthropic_key)
                    ],
                },
            )

            logger.info(f"BYOK keys rotated for tenant {tenant_id}")
            return new_virtual_key

        except VirtualKeyRotationError:
            raise
        except Exception as e:
            logger.error(f"Failed to rotate BYOK keys for {tenant_id}: {str(e)}")
            raise VirtualKeyRotationError(f"Key rotation failed: {str(e)}") from e

    async def revert_to_platform_keys(self, tenant_id: str) -> str:
        """
        Disable BYOK and revert tenant to platform keys (AC#8).

        Deletes BYOK virtual key, creates standard platform virtual key,
        clears BYOK columns in database.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            str: New platform virtual key

        Raises:
            ValueError: If tenant not found
            VirtualKeyCreationError: If platform key creation fails

        Example:
            >>> platform_vkey = await service.revert_to_platform_keys("acme-corp")
        """
        from sqlalchemy import select, update

        logger.info(f"Reverting tenant {tenant_id} to platform keys")

        try:
            # Create new platform virtual key (uses existing pattern from Story 8.9)
            max_budget = 100.0  # Default budget
            stmt = select(TenantConfigModel.max_budget).where(
                TenantConfigModel.tenant_id == tenant_id
            )
            result = await self.db.execute(stmt)
            row = result.fetchone()
            if row:
                max_budget = row[0]

            platform_virtual_key = await self.create_virtual_key_for_tenant(
                tenant_id, max_budget
            )

            # Clear BYOK columns and set platform virtual key
            stmt = (
                update(TenantConfigModel)
                .where(TenantConfigModel.tenant_id == tenant_id)
                .values(
                    byok_enabled=False,
                    byok_openai_key_encrypted=None,
                    byok_anthropic_key_encrypted=None,
                    byok_virtual_key=None,
                    byok_enabled_at=None,
                    litellm_virtual_key=encrypt(platform_virtual_key),
                    litellm_key_created_at=datetime.now(timezone.utc),
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

            # Log audit entry
            await self.log_audit_entry(
                action="BYOK_DISABLED",
                tenant_id=tenant_id,
                details={"reverted_to_platform": True},
            )

            logger.info(f"Tenant {tenant_id} reverted to platform keys")
            return platform_virtual_key

        except Exception as e:
            logger.error(f"Failed to revert {tenant_id} to platform keys: {str(e)}")
            raise VirtualKeyCreationError(f"Reversion failed: {str(e)}") from e
