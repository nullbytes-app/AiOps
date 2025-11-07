"""
Pytest fixtures for provider integration tests.

Provides database sessions, Redis mocks, and test data fixtures for
integration testing of LLM provider configuration workflows.

Story: 8.11 - Provider Configuration UI
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import LLMProvider, LLMModel
from src.schemas.provider import LLMProviderCreate, LLMModelCreate


@pytest.fixture
async def redis_client():
    """
    Provide mocked Redis client for integration tests.

    Returns:
        MagicMock: Async Redis client mock with standard methods

    Methods mocked:
        - get: Returns None (cache miss)
        - set: Returns True
        - delete: Returns 1 (success)
        - exists: Returns False
    """
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=False)
    return mock_redis


@pytest.fixture
def openai_provider_create() -> LLMProviderCreate:
    """
    Provide OpenAI provider creation schema for testing with unique name.

    Returns:
        LLMProviderCreate: Valid OpenAI provider configuration with unique name per test run
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return LLMProviderCreate(
        name=f"Test OpenAI Provider {unique_id}",
        provider_type="openai",
        api_base_url="https://api.openai.com/v1",
        api_key="sk-test-openai-api-key-for-integration-testing-1234567890",
    )


@pytest.fixture
def anthropic_provider_create() -> LLMProviderCreate:
    """
    Provide Anthropic provider creation schema for testing with unique name.

    Returns:
        LLMProviderCreate: Valid Anthropic provider configuration with unique name per test run
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return LLMProviderCreate(
        name=f"Test Anthropic Provider {unique_id}",
        provider_type="anthropic",
        api_base_url="https://api.anthropic.com",
        api_key="sk-ant-test-anthropic-api-key-for-integration-testing-1234567890",
    )


@pytest.fixture
def azure_provider_create() -> LLMProviderCreate:
    """
    Provide Azure OpenAI provider creation schema for testing with unique name.

    Returns:
        LLMProviderCreate: Valid Azure OpenAI provider configuration with unique name per test run
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return LLMProviderCreate(
        name=f"Test Azure OpenAI Provider {unique_id}",
        provider_type="azure_openai",
        api_base_url="https://test-resource.openai.azure.com",
        api_key="test-azure-openai-api-key-for-integration-testing",
    )


@pytest.fixture
async def test_openai_provider(db_session: AsyncSession, openai_provider_create: LLMProviderCreate):
    """
    Create persisted OpenAI provider in test database with proper cleanup.

    Args:
        db_session: Async database session
        openai_provider_create: Provider creation schema

    Yields:
        LLMProvider: Persisted provider database record

    Note:
        - Provider is committed to database (visible to other sessions)
        - Cleanup handled by explicit deletion in teardown
        - API key is NOT encrypted (using plain test key for integration tests)
    """
    from src.services.provider_service import ProviderService
    from src.database.models import LLMProvider
    from sqlalchemy import select

    # Create mock Redis client
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)

    # Create provider via service
    provider_service = ProviderService(db_session, mock_redis)
    provider = await provider_service.create_provider(openai_provider_create)

    await db_session.commit()
    await db_session.refresh(provider)

    yield provider

    # Cleanup: Delete provider and all associated models
    try:
        # Refresh to ensure we have the latest state
        await db_session.refresh(provider)
        await db_session.delete(provider)
        await db_session.commit()
    except Exception:
        # If provider already deleted or session closed, rollback and continue
        await db_session.rollback()


@pytest.fixture
async def test_anthropic_provider(db_session: AsyncSession, anthropic_provider_create: LLMProviderCreate):
    """
    Create persisted Anthropic provider in test database with proper cleanup.

    Args:
        db_session: Async database session
        anthropic_provider_create: Provider creation schema

    Yields:
        LLMProvider: Persisted provider database record
    """
    from src.services.provider_service import ProviderService

    # Create mock Redis client
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)

    # Create provider via service
    provider_service = ProviderService(db_session, mock_redis)
    provider = await provider_service.create_provider(anthropic_provider_create)

    await db_session.commit()
    await db_session.refresh(provider)

    yield provider

    # Cleanup: Delete provider and all associated models
    try:
        await db_session.refresh(provider)
        await db_session.delete(provider)
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest.fixture
def gpt4_model_create(test_openai_provider: LLMProvider) -> LLMModelCreate:
    """
    Provide GPT-4 model creation schema for testing.

    Args:
        test_openai_provider: Parent OpenAI provider

    Returns:
        LLMModelCreate: Valid GPT-4 model configuration
    """
    return LLMModelCreate(
        provider_id=test_openai_provider.id,
        model_name="gpt-4-turbo-preview",
        display_name="GPT-4 Turbo",
        enabled=True,
        cost_per_input_token=0.00001,
        cost_per_output_token=0.00003,
        context_window=128000,
        capabilities={"vision": True, "function_calling": True},
    )


@pytest.fixture
def claude_model_create(test_anthropic_provider: LLMProvider) -> LLMModelCreate:
    """
    Provide Claude model creation schema for testing.

    Args:
        test_anthropic_provider: Parent Anthropic provider

    Returns:
        LLMModelCreate: Valid Claude model configuration
    """
    return LLMModelCreate(
        provider_id=test_anthropic_provider.id,
        model_name="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        enabled=True,
        cost_per_input_token=0.000003,
        cost_per_output_token=0.000015,
        context_window=200000,
        capabilities={"vision": True, "function_calling": False},
    )


@pytest.fixture
async def test_gpt4_model(db_session: AsyncSession, test_openai_provider: LLMProvider, gpt4_model_create: LLMModelCreate) -> LLMModel:
    """
    Create persisted GPT-4 model in test database.

    Args:
        db_session: Async database session
        test_openai_provider: Parent provider (ensures provider exists)
        gpt4_model_create: Model creation schema

    Returns:
        LLMModel: Persisted model database record
    """
    from src.services.model_service import ModelService

    model_service = ModelService(db_session)
    model = await model_service.create_model(gpt4_model_create)

    await db_session.commit()
    await db_session.refresh(model)

    return model


@pytest.fixture
async def test_claude_model(db_session: AsyncSession, test_anthropic_provider: LLMProvider, claude_model_create: LLMModelCreate) -> LLMModel:
    """
    Create persisted Claude model in test database.

    Args:
        db_session: Async database session
        test_anthropic_provider: Parent provider (ensures provider exists)
        claude_model_create: Model creation schema

    Returns:
        LLMModel: Persisted model database record
    """
    from src.services.model_service import ModelService

    model_service = ModelService(db_session)
    model = await model_service.create_model(claude_model_create)

    await db_session.commit()
    await db_session.refresh(model)

    return model


@pytest.fixture
def mock_openai_models_response():
    """
    Provide mock OpenAI /v1/models API response.

    Returns:
        dict: Mock API response with model list
    """
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4-turbo-preview",
                "object": "model",
                "created": 1706037777,
                "owned_by": "system",
            },
            {
                "id": "gpt-4",
                "object": "model",
                "created": 1687882411,
                "owned_by": "openai",
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai",
            },
        ],
    }


@pytest.fixture
def mock_anthropic_models_response():
    """
    Provide mock Anthropic models list.

    Note: Anthropic doesn't have a public models endpoint,
    so this returns a hardcoded list.

    Returns:
        list[str]: Mock Anthropic model names
    """
    return [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]
