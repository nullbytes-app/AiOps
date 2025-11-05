"""
Unit tests for plugin base interface.

Tests the TicketingToolPlugin abstract base class and TicketMetadata dataclass
structure, method signatures, type hints, and enforcement of abstract methods.

Validates AC1, AC2, AC3, AC4, AC6, AC7 from Story 7.1.
"""

import inspect
import pytest
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional, get_type_hints

from src.plugins.base import TicketingToolPlugin, TicketMetadata


class TestTicketingToolPluginABC:
    """Test suite for TicketingToolPlugin abstract base class structure."""

    def test_ticketing_tool_plugin_is_abstract(self):
        """
        Validate AC1: Cannot instantiate TicketingToolPlugin directly.

        Tests that TicketingToolPlugin is properly defined as an abstract class
        and raises TypeError when attempting direct instantiation.
        """
        with pytest.raises(TypeError, match="Can't instantiate abstract class TicketingToolPlugin"):
            TicketingToolPlugin()

    def test_ticketing_tool_plugin_inherits_from_abc(self):
        """
        Validate AC1: TicketingToolPlugin inherits from ABC.

        Tests that the class uses ABC pattern for proper abstract behavior.
        """
        assert issubclass(TicketingToolPlugin, ABC)

    def test_ticketing_tool_plugin_has_four_methods(self):
        """
        Validate AC2: TicketingToolPlugin defines exactly four abstract methods.

        Tests that the interface has the expected number of abstract methods:
        validate_webhook, get_ticket, update_ticket, extract_metadata.
        """
        abstract_methods = [
            name
            for name, method in inspect.getmembers(TicketingToolPlugin)
            if getattr(method, "__isabstractmethod__", False)
        ]

        assert (
            len(abstract_methods) == 4
        ), f"Expected 4 abstract methods, found {len(abstract_methods)}: {abstract_methods}"

        expected_methods = {
            "validate_webhook",
            "get_ticket",
            "update_ticket",
            "extract_metadata",
        }
        assert set(abstract_methods) == expected_methods

    def test_abstract_methods_properly_decorated(self):
        """
        Validate AC2: All four methods have @abstractmethod decorator.

        Tests that each method is properly marked as abstract using inspect.
        """
        for method_name in [
            "validate_webhook",
            "get_ticket",
            "update_ticket",
            "extract_metadata",
        ]:
            method = getattr(TicketingToolPlugin, method_name)
            assert getattr(
                method, "__isabstractmethod__", False
            ), f"Method {method_name} missing @abstractmethod decorator"

    def test_ticketing_tool_plugin_requires_all_methods(self):
        """
        Validate AC6: Incomplete subclass raises TypeError.

        Tests that attempting to instantiate a plugin with missing methods
        raises TypeError with appropriate message.
        """

        class IncompletePlugin(TicketingToolPlugin):
            """Incomplete plugin missing update_ticket method."""

            async def validate_webhook(self, payload, signature):
                return True

            async def get_ticket(self, tenant_id, ticket_id):
                return {}

            # Missing update_ticket intentionally

            def extract_metadata(self, payload):
                return TicketMetadata(
                    tenant_id="test",
                    ticket_id="123",
                    description="test",
                    priority="medium",
                    created_at=datetime.now(timezone.utc),
                )

        with pytest.raises(TypeError, match="Can't instantiate abstract class IncompletePlugin"):
            IncompletePlugin()


class TestAbstractMethodSignatures:
    """Test suite for abstract method signatures and type hints."""

    def test_validate_webhook_signature(self):
        """
        Validate AC2, AC3: validate_webhook has correct signature and type hints.

        Expected: async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool
        """
        method = getattr(TicketingToolPlugin, "validate_webhook")

        # Check method is async
        assert inspect.iscoroutinefunction(method), "validate_webhook should be async"

        # Check signature
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert params == [
            "self",
            "payload",
            "signature",
        ], f"Expected parameters [self, payload, signature], got {params}"

        # Check type hints
        hints = get_type_hints(method)
        assert hints["payload"] == Dict[str, Any]
        assert hints["signature"] == str
        assert hints["return"] == bool

    def test_get_ticket_signature(self):
        """
        Validate AC2, AC3: get_ticket has correct signature and type hints.

        Expected: async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]
        """
        method = getattr(TicketingToolPlugin, "get_ticket")

        # Check method is async
        assert inspect.iscoroutinefunction(method), "get_ticket should be async"

        # Check signature
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert params == [
            "self",
            "tenant_id",
            "ticket_id",
        ], f"Expected parameters [self, tenant_id, ticket_id], got {params}"

        # Check type hints
        hints = get_type_hints(method)
        assert hints["tenant_id"] == str
        assert hints["ticket_id"] == str
        assert hints["return"] == Optional[Dict[str, Any]]

    def test_update_ticket_signature(self):
        """
        Validate AC2, AC3: update_ticket has correct signature and type hints.

        Expected: async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool
        """
        method = getattr(TicketingToolPlugin, "update_ticket")

        # Check method is async
        assert inspect.iscoroutinefunction(method), "update_ticket should be async"

        # Check signature
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert params == [
            "self",
            "tenant_id",
            "ticket_id",
            "content",
        ], f"Expected parameters [self, tenant_id, ticket_id, content], got {params}"

        # Check type hints
        hints = get_type_hints(method)
        assert hints["tenant_id"] == str
        assert hints["ticket_id"] == str
        assert hints["content"] == str
        assert hints["return"] == bool

    def test_extract_metadata_signature(self):
        """
        Validate AC2, AC3: extract_metadata has correct signature and type hints.

        Expected: def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata
        Note: This method is SYNCHRONOUS (not async).
        """
        method = getattr(TicketingToolPlugin, "extract_metadata")

        # Check method is NOT async (synchronous)
        assert not inspect.iscoroutinefunction(
            method
        ), "extract_metadata should be synchronous (not async)"

        # Check signature
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert params == ["self", "payload"], f"Expected parameters [self, payload], got {params}"

        # Check type hints
        hints = get_type_hints(method)
        assert hints["payload"] == Dict[str, Any]
        assert hints["return"] == TicketMetadata


class TestMethodDocstrings:
    """Test suite for Google-style docstrings on all methods."""

    def test_all_methods_have_docstrings(self):
        """
        Validate AC3: All abstract methods have docstrings.

        Tests that each method has a non-empty __doc__ attribute.
        """
        for method_name in [
            "validate_webhook",
            "get_ticket",
            "update_ticket",
            "extract_metadata",
        ]:
            method = getattr(TicketingToolPlugin, method_name)
            assert method.__doc__ is not None, f"Method {method_name} missing docstring"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty docstring"

    def test_class_has_docstring(self):
        """
        Validate AC3: TicketingToolPlugin class has comprehensive docstring.

        Tests that the class-level docstring exists and is comprehensive.
        """
        assert TicketingToolPlugin.__doc__ is not None
        assert (
            len(TicketingToolPlugin.__doc__.strip()) > 100
        ), "Class docstring should be comprehensive (>100 chars)"

    def test_docstrings_contain_required_sections(self):
        """
        Validate AC3: Docstrings follow Google-style format.

        Tests that docstrings contain expected sections: Args, Returns, Raises.
        """
        for method_name in ["validate_webhook", "get_ticket", "update_ticket"]:
            method = getattr(TicketingToolPlugin, method_name)
            docstring = method.__doc__ or ""

            assert "Args:" in docstring, f"Method {method_name} docstring missing 'Args:' section"
            assert (
                "Returns:" in docstring
            ), f"Method {method_name} docstring missing 'Returns:' section"
            assert (
                "Raises:" in docstring
            ), f"Method {method_name} docstring missing 'Raises:' section"


class TestAsyncMethodMarking:
    """Test suite for async method validation."""

    def test_async_methods_properly_marked(self):
        """
        Validate AC6: validate_webhook, get_ticket, update_ticket are async.

        Tests that the three I/O methods are properly marked as coroutine functions.
        """
        async_methods = ["validate_webhook", "get_ticket", "update_ticket"]

        for method_name in async_methods:
            method = getattr(TicketingToolPlugin, method_name)
            assert inspect.iscoroutinefunction(
                method
            ), f"Method {method_name} should be async (coroutine function)"

    def test_extract_metadata_is_sync(self):
        """
        Validate AC6: extract_metadata is synchronous (not async).

        Tests that extract_metadata is a regular function, not a coroutine.
        This method is sync because it only transforms data without I/O.
        """
        method = getattr(TicketingToolPlugin, "extract_metadata")
        assert not inspect.iscoroutinefunction(
            method
        ), "extract_metadata should be synchronous (not async coroutine)"


class TestTicketMetadataDataclass:
    """Test suite for TicketMetadata dataclass structure and behavior."""

    def test_ticket_metadata_dataclass_creation(self):
        """
        Validate AC4: TicketMetadata can be instantiated with required fields.

        Tests that all five required fields can be provided and accessed.
        """
        created_time = datetime(2025, 11, 4, 10, 0, 0, tzinfo=timezone.utc)

        metadata = TicketMetadata(
            tenant_id="tenant-001",
            ticket_id="INC-123",
            description="User cannot access email",
            priority="high",
            created_at=created_time,
        )

        assert metadata.tenant_id == "tenant-001"
        assert metadata.ticket_id == "INC-123"
        assert metadata.description == "User cannot access email"
        assert metadata.priority == "high"
        assert metadata.created_at == created_time

    def test_ticket_metadata_field_types(self):
        """
        Validate AC4: TicketMetadata fields have correct type hints.

        Tests that get_type_hints returns the expected types for all fields.
        """
        hints = get_type_hints(TicketMetadata)

        assert hints["tenant_id"] == str
        assert hints["ticket_id"] == str
        assert hints["description"] == str
        assert hints["priority"] == str
        assert hints["created_at"] == datetime

    def test_ticket_metadata_equality(self):
        """
        Validate AC4: TicketMetadata supports equality comparison.

        Tests dataclass equality behavior - two instances with same data are equal.
        """
        created_time = datetime(2025, 11, 4, 10, 0, 0, tzinfo=timezone.utc)

        metadata1 = TicketMetadata(
            tenant_id="tenant-001",
            ticket_id="INC-123",
            description="Test",
            priority="high",
            created_at=created_time,
        )

        metadata2 = TicketMetadata(
            tenant_id="tenant-001",
            ticket_id="INC-123",
            description="Test",
            priority="high",
            created_at=created_time,
        )

        assert metadata1 == metadata2

        # Different data should not be equal
        metadata3 = TicketMetadata(
            tenant_id="tenant-002",  # Different tenant
            ticket_id="INC-123",
            description="Test",
            priority="high",
            created_at=created_time,
        )

        assert metadata1 != metadata3

    def test_ticket_metadata_repr(self):
        """
        Validate AC4: TicketMetadata has useful repr for debugging.

        Tests that dataclass automatically generates a repr containing field values.
        """
        created_time = datetime(2025, 11, 4, 10, 0, 0, tzinfo=timezone.utc)

        metadata = TicketMetadata(
            tenant_id="tenant-001",
            ticket_id="INC-123",
            description="Test",
            priority="high",
            created_at=created_time,
        )

        repr_str = repr(metadata)

        # Repr should contain class name and field values
        assert "TicketMetadata" in repr_str
        assert "tenant_id='tenant-001'" in repr_str
        assert "ticket_id='INC-123'" in repr_str
        assert "priority='high'" in repr_str

    def test_ticket_metadata_with_timezone_aware_datetime(self):
        """
        Validate AC4: TicketMetadata handles timezone-aware datetime (UTC).

        Edge case: Tests that created_at field properly stores UTC datetime objects.
        """
        utc_time = datetime.now(timezone.utc)

        metadata = TicketMetadata(
            tenant_id="tenant-001",
            ticket_id="INC-123",
            description="Test",
            priority="medium",
            created_at=utc_time,
        )

        assert metadata.created_at.tzinfo == timezone.utc

    def test_ticket_metadata_missing_required_field(self):
        """
        Validate AC4: TicketMetadata raises TypeError when field missing.

        Failure case: Tests that omitting a required field raises TypeError.
        """
        with pytest.raises(TypeError, match="missing 1 required positional argument"):
            # Missing created_at field
            TicketMetadata(
                tenant_id="tenant-001",
                ticket_id="INC-123",
                description="Test",
                priority="high",
            )


class TestTicketingToolPluginWithExtraMethods:
    """Test edge cases for plugin implementations."""

    def test_ticketing_tool_plugin_with_extra_methods(self):
        """
        Edge case: Verify subclass can add methods beyond the four required.

        Tests that plugins can extend the base interface with additional methods
        without breaking the ABC contract.
        """

        class ExtendedPlugin(TicketingToolPlugin):
            """Plugin with additional helper methods."""

            async def validate_webhook(self, payload, signature):
                return True

            async def get_ticket(self, tenant_id, ticket_id):
                return {"id": ticket_id}

            async def update_ticket(self, tenant_id, ticket_id, content):
                return True

            def extract_metadata(self, payload):
                return TicketMetadata(
                    tenant_id="test",
                    ticket_id="123",
                    description="test",
                    priority="medium",
                    created_at=datetime.now(timezone.utc),
                )

            # Additional custom method
            async def get_ticket_comments(self, tenant_id, ticket_id):
                """Custom method not in base interface."""
                return []

        # Should instantiate successfully
        plugin = ExtendedPlugin()
        assert plugin is not None
        assert hasattr(plugin, "get_ticket_comments")


class MockTicketingToolPlugin(TicketingToolPlugin):
    """
    Mock plugin implementation for testing.

    Provides simple implementations of all abstract methods with configurable
    return values. Used in integration tests (Story 7.6) to test enhancement
    workflow without requiring actual API calls.

    Attributes:
        validate_webhook_response (bool): Return value for validate_webhook
        get_ticket_response (Optional[Dict]): Return value for get_ticket
        update_ticket_response (bool): Return value for update_ticket
        extract_metadata_response (TicketMetadata): Return value for extract_metadata

    Example:
        # Create mock plugin that fails webhook validation
        mock_plugin = MockTicketingToolPlugin(validate_webhook_response=False)

        # Create mock plugin that returns None for get_ticket (ticket not found)
        mock_plugin = MockTicketingToolPlugin(get_ticket_response=None)
    """

    def __init__(
        self,
        validate_webhook_response: bool = True,
        get_ticket_response: Optional[Dict[str, Any]] = "default",
        update_ticket_response: bool = True,
        extract_metadata_response: Optional[TicketMetadata] = None,
    ):
        self.validate_webhook_response = validate_webhook_response
        if get_ticket_response == "default":
            self.get_ticket_response = {
                "id": "MOCK-123",
                "description": "Mock ticket description",
                "priority": "Medium",
                "status": "Open",
            }
        else:
            self.get_ticket_response = get_ticket_response
        self.update_ticket_response = update_ticket_response
        if extract_metadata_response is None:
            self.extract_metadata_response = TicketMetadata(
                tenant_id="mock-tenant",
                ticket_id="MOCK-123",
                description="Mock ticket description",
                priority="medium",
                created_at=datetime.now(timezone.utc),
            )
        else:
            self.extract_metadata_response = extract_metadata_response

        # Track method calls for test assertions
        self.validate_webhook_calls = []
        self.get_ticket_calls = []
        self.update_ticket_calls = []
        self.extract_metadata_calls = []

    async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """Mock validate_webhook implementation."""
        self.validate_webhook_calls.append({"payload": payload, "signature": signature})
        return self.validate_webhook_response

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Mock get_ticket implementation."""
        self.get_ticket_calls.append({"tenant_id": tenant_id, "ticket_id": ticket_id})
        return self.get_ticket_response

    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """Mock update_ticket implementation."""
        self.update_ticket_calls.append(
            {"tenant_id": tenant_id, "ticket_id": ticket_id, "content": content}
        )
        return self.update_ticket_response

    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """Mock extract_metadata implementation."""
        self.extract_metadata_calls.append({"payload": payload})
        return self.extract_metadata_response


class TestMockTicketingToolPlugin:
    """Test suite for MockTicketingToolPlugin fixture."""

    @pytest.mark.asyncio
    async def test_mock_plugin_instantiation(self):
        """Test MockTicketingToolPlugin can be instantiated successfully."""
        mock_plugin = MockTicketingToolPlugin()
        assert mock_plugin is not None
        assert isinstance(mock_plugin, TicketingToolPlugin)

    @pytest.mark.asyncio
    async def test_mock_plugin_validate_webhook(self):
        """Test MockTicketingToolPlugin validate_webhook method."""
        mock_plugin = MockTicketingToolPlugin(validate_webhook_response=True)

        result = await mock_plugin.validate_webhook(payload={"test": "data"}, signature="test-sig")

        assert result is True
        assert len(mock_plugin.validate_webhook_calls) == 1
        assert mock_plugin.validate_webhook_calls[0]["payload"] == {"test": "data"}
        assert mock_plugin.validate_webhook_calls[0]["signature"] == "test-sig"

    @pytest.mark.asyncio
    async def test_mock_plugin_get_ticket(self):
        """Test MockTicketingToolPlugin get_ticket method."""
        mock_plugin = MockTicketingToolPlugin()

        result = await mock_plugin.get_ticket(tenant_id="tenant-001", ticket_id="MOCK-123")

        assert result is not None
        assert result["id"] == "MOCK-123"
        assert len(mock_plugin.get_ticket_calls) == 1

    @pytest.mark.asyncio
    async def test_mock_plugin_get_ticket_not_found(self):
        """Test MockTicketingToolPlugin get_ticket returns None when configured."""
        mock_plugin = MockTicketingToolPlugin(get_ticket_response=None)

        result = await mock_plugin.get_ticket(tenant_id="tenant-001", ticket_id="NOT-FOUND")

        assert result is None

    @pytest.mark.asyncio
    async def test_mock_plugin_update_ticket(self):
        """Test MockTicketingToolPlugin update_ticket method."""
        mock_plugin = MockTicketingToolPlugin(update_ticket_response=True)

        result = await mock_plugin.update_ticket(
            tenant_id="tenant-001", ticket_id="MOCK-123", content="Enhancement content"
        )

        assert result is True
        assert len(mock_plugin.update_ticket_calls) == 1
        assert mock_plugin.update_ticket_calls[0]["content"] == "Enhancement content"

    def test_mock_plugin_extract_metadata(self):
        """Test MockTicketingToolPlugin extract_metadata method."""
        mock_plugin = MockTicketingToolPlugin()

        result = mock_plugin.extract_metadata(payload={"test": "data"})

        assert isinstance(result, TicketMetadata)
        assert result.tenant_id == "mock-tenant"
        assert result.ticket_id == "MOCK-123"
        assert len(mock_plugin.extract_metadata_calls) == 1


@pytest.fixture
def mock_plugin():
    """Pytest fixture providing MockTicketingToolPlugin with default responses."""
    return MockTicketingToolPlugin()


@pytest.fixture
def mock_plugin_validation_failure():
    """Pytest fixture providing mock plugin that fails webhook validation."""
    return MockTicketingToolPlugin(validate_webhook_response=False)


@pytest.fixture
def mock_plugin_ticket_not_found():
    """Pytest fixture providing mock plugin that returns None for get_ticket."""
    return MockTicketingToolPlugin(get_ticket_response=None)


@pytest.fixture
def mock_plugin_update_failure():
    """Pytest fixture providing mock plugin that fails ticket updates."""
    return MockTicketingToolPlugin(update_ticket_response=False)
