"""
Custom exceptions for AI Agents platform.

This module defines application-specific exceptions for better error handling
and clearer error messages throughout the platform.
"""


class BudgetExceededError(Exception):
    """
    Raised when a tenant's LLM budget limit has been exceeded.

    This exception is raised when a tenant attempts to make an LLM API call
    but their budget has reached the grace threshold (default: 110%). The
    exception message includes the current spend, max budget, and remediation
    steps for the tenant.

    Attributes:
        tenant_id: Tenant ID that exceeded budget
        current_spend: Current spend in USD
        max_budget: Maximum budget in USD
        grace_threshold: Blocking threshold percentage (e.g., 110)
        message: Formatted error message with remediation steps

    Example:
        >>> if spend >= (max_budget * grace_threshold / 100):
        >>>     raise BudgetExceededError(
        >>>         tenant_id="acme-corp",
        >>>         current_spend=550.00,
        >>>         max_budget=500.00,
        >>>         grace_threshold=110
        >>>     )
    """

    def __init__(
        self,
        tenant_id: str,
        current_spend: float,
        max_budget: float,
        grace_threshold: int = 110,
        message: str | None = None,
    ):
        """
        Initialize BudgetExceededError with tenant budget details.

        Args:
            tenant_id: Tenant ID that exceeded budget
            current_spend: Current spend in USD
            max_budget: Maximum budget in USD
            grace_threshold: Blocking threshold percentage (default: 110)
            message: Optional custom error message (auto-generated if None)
        """
        self.tenant_id = tenant_id
        self.current_spend = current_spend
        self.max_budget = max_budget
        self.grace_threshold = grace_threshold

        if message is None:
            blocking_amount = max_budget * (grace_threshold / 100)
            self.message = (
                f"Budget exceeded for tenant {tenant_id}. "
                f"Current spend: ${current_spend:.2f}, "
                f"Max budget: ${max_budget:.2f}, "
                f"Grace limit: ${blocking_amount:.2f} ({grace_threshold}%). "
                f"Remediation: Contact your administrator to increase budget or "
                f"wait for monthly reset. Agent execution is blocked until budget is increased."
            )
        else:
            self.message = message

        super().__init__(self.message)

    def __str__(self) -> str:
        """Return formatted error message."""
        return self.message

    def to_dict(self) -> dict:
        """
        Convert exception to dictionary for API error responses.

        Returns:
            dict: Error details including tenant_id, spend, budget, and message

        Example:
            >>> try:
            >>>     # Some LLM call
            >>> except BudgetExceededError as e:
            >>>     return JSONResponse(status_code=402, content=e.to_dict())
        """
        return {
            "error": "budget_exceeded",
            "tenant_id": self.tenant_id,
            "current_spend": self.current_spend,
            "max_budget": self.max_budget,
            "grace_threshold": self.grace_threshold,
            "message": self.message,
            "remediation": (
                "Contact your administrator to increase budget or wait for monthly reset. "
                "View budget usage in Admin UI."
            ),
        }
