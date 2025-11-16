"""
API endpoints for agent testing (Story 8.14).

Provides REST endpoints for:
- Executing agent tests in sandbox mode
- Retrieving test execution history
- Comparing test results
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_db, get_tenant_id
from src.database.session import get_async_session
from src.schemas.agent_test import (
    AgentTestRequest,
    AgentTestResponse,
    TestComparisonRequest,
    TestComparisonResult,
)
from src.services.agent_test_service import AgentTestService
from src.utils.logger import logger

router = APIRouter(prefix="/api/agents", tags=["agent-testing"])


def get_agent_test_service() -> AgentTestService:
    """Get agent test service instance."""
    return AgentTestService()


@router.post(
    "/{agent_id}/test",
    response_model=AgentTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Agent Test",
    description="Execute agent test in sandbox mode. Returns execution trace, token usage, and timing breakdown.",
)
async def execute_agent_test(
    agent_id: UUID,
    test_request: AgentTestRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: AsyncSession = Depends(get_tenant_db),
    service: AgentTestService = Depends(get_agent_test_service),
) -> AgentTestResponse:
    """
    Execute agent test in sandbox mode.

    Runs agent without side effects (mocked tools, read-only database).
    Returns detailed execution trace for verification before activation.

    Args:
        agent_id: Agent to test
        test_request: Test configuration (payload, trigger type)
        tenant_id: Tenant ID from request headers
        db: Tenant-aware database session
        service: Agent test service

    Returns:
        AgentTestResponse: Complete test results

    Raises:
        HTTPException: If agent not found or test execution fails
    """
    try:
        # Execute test
        result = await service.execute_agent_test(
            agent_id=agent_id,
            tenant_id=tenant_id,
            test_request=test_request,
            db=db,
        )

        # Commit test result to database
        await db.commit()

        return result

    except ValueError as e:
        logger.error(f"Invalid test request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Test execution failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test execution failed",
        )


@router.get(
    "/{agent_id}/test-history",
    summary="Get Test History",
    description="Retrieve paginated test execution history for an agent.",
)
async def get_test_history(
    agent_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_tenant_db),
    service: AgentTestService = Depends(get_agent_test_service),
) -> dict:
    """
    Get paginated test execution history.

    Args:
        agent_id: Agent to get history for
        tenant_id: Tenant ID from request headers
        limit: Maximum results (1-500, default 50)
        offset: Number of results to skip
        db: Tenant-aware database session
        service: Agent test service

    Returns:
        dict: {tests: [test objects], total: int, limit: int, offset: int}

    Raises:
        HTTPException: If agent not found
    """
    try:
        result = await service.get_test_history(
            agent_id=agent_id,
            tenant_id=tenant_id,
            db=db,
            limit=limit,
            offset=offset,
        )

        return result

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve test history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve test history",
        )


@router.get(
    "/{agent_id}/test/{test_id}",
    summary="Get Test Result",
    description="Retrieve a single test execution result.",
)
async def get_test_result(
    agent_id: UUID,
    test_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: AsyncSession = Depends(get_tenant_db),
    service: AgentTestService = Depends(get_agent_test_service),
) -> dict:
    """
    Get single test result.

    Args:
        agent_id: Agent being tested
        test_id: Test execution ID
        tenant_id: Tenant ID from request headers
        db: Tenant-aware database session
        service: Agent test service

    Returns:
        dict: Test execution result

    Raises:
        HTTPException: If test not found or isolation violated
    """
    try:
        test = await service.get_test_result(
            test_id=test_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            db=db,
        )

        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test not found",
            )

        return {
            "test_id": test.id,
            "agent_id": test.agent_id,
            "status": test.status,
            "payload": test.payload,
            "execution_trace": test.execution_trace,
            "token_usage": test.token_usage,
            "execution_time": test.execution_time,
            "errors": test.errors,
            "created_at": test.created_at,
        }

    except ValueError as e:
        logger.error(f"Isolation violation: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve test result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve test result",
        )


@router.post(
    "/{agent_id}/test/compare",
    response_model=TestComparisonResult,
    summary="Compare Tests",
    description="Compare two test execution results to identify differences.",
)
async def compare_tests(
    agent_id: UUID,
    request: TestComparisonRequest,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: AsyncSession = Depends(get_tenant_db),
    service: AgentTestService = Depends(get_agent_test_service),
) -> TestComparisonResult:
    """
    Compare two test results.

    Highlights differences in token usage, execution time, and trace details.

    Args:
        agent_id: Agent being tested
        request: Comparison request with test IDs
        tenant_id: Tenant ID from request headers
        db: Tenant-aware database session
        service: Agent test service

    Returns:
        TestComparisonResult: Comparison results

    Raises:
        HTTPException: If tests not found or comparison fails
    """
    try:
        comparison = await service.compare_tests(
            test_id_1=request.test_id_1,
            test_id_2=request.test_id_2,
            agent_id=agent_id,
            tenant_id=tenant_id,
            db=db,
        )

        return TestComparisonResult(**comparison)

    except ValueError as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Failed to compare tests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare tests",
        )
