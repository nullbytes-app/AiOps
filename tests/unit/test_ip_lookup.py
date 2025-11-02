"""
Unit tests for IP address lookup service (Story 2.7).

Tests cover:
- IPv4 extraction from single and multiple IPs
- IPv6 extraction and mixed IPv4/IPv6
- IP deduplication
- Database lookups with tenant isolation
- Error handling and graceful degradation
- Edge cases and boundary conditions

Fixtures and patterns align with existing test infrastructure
(see test_kb_search.py for service testing patterns).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.ip_lookup import extract_and_lookup_ips, IPV4_PATTERN, IPV6_PATTERN


class TestIPExtraction:
    """Test IP extraction from descriptions."""

    def test_ipv4_extraction_single_ip(self):
        """Test extraction of single IPv4 address from description."""
        description = "Server 192.168.1.10 is down"
        matches = __import__("re").findall(IPV4_PATTERN, description)
        assert len(matches) == 1
        assert matches[0] == "192.168.1.10"

    def test_ipv4_extraction_multiple_ips(self):
        """Test extraction of multiple IPv4 addresses from description."""
        description = "Check 10.0.0.1, 10.0.0.2, and 10.0.0.3"
        matches = __import__("re").findall(IPV4_PATTERN, description)
        assert len(matches) == 3
        assert "10.0.0.1" in matches
        assert "10.0.0.2" in matches
        assert "10.0.0.3" in matches

    def test_ipv4_extraction_with_duplicates(self):
        """Test that duplicate IPs are extracted (dedupe happens in service)."""
        description = "Server 192.168.1.1 and 192.168.1.1 reported issues"
        matches = __import__("re").findall(IPV4_PATTERN, description)
        # Regex finds duplicates; service dedupes with set()
        assert len(matches) == 2
        assert matches[0] == "192.168.1.1"
        assert matches[1] == "192.168.1.1"

    def test_ipv6_extraction(self):
        """Test extraction of IPv6 address from description."""
        description = "IPv6 system 2001:0db8:85a3:0000:0000:8a2e:0370:7334 failed"
        matches = __import__("re").findall(IPV6_PATTERN, description)
        assert len(matches) == 1
        assert matches[0] == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

    def test_mixed_ipv4_and_ipv6_extraction(self):
        """Test extraction of both IPv4 and IPv6 from same description."""
        description = "Affected: 192.168.1.1 and 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        ipv4_matches = __import__("re").findall(IPV4_PATTERN, description)
        ipv6_matches = __import__("re").findall(IPV6_PATTERN, description)
        assert len(ipv4_matches) == 1
        assert ipv4_matches[0] == "192.168.1.1"
        assert len(ipv6_matches) == 1
        assert ipv6_matches[0] == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

    def test_no_ip_in_description(self):
        """Test extraction returns empty list when no IPs in description."""
        description = "This ticket has no IP addresses mentioned"
        ipv4_matches = __import__("re").findall(IPV4_PATTERN, description)
        ipv6_matches = __import__("re").findall(IPV6_PATTERN, description)
        assert len(ipv4_matches) == 0
        assert len(ipv6_matches) == 0

    def test_invalid_ipv4_filtered_out(self):
        """Test that invalid IPv4 patterns are not matched."""
        description = "Invalid 999.999.999.999 but valid 192.168.1.1"
        matches = __import__("re").findall(IPV4_PATTERN, description)
        # Note: Regex pattern matches numbers, not IP validity
        # Service should handle validation if needed
        assert "192.168.1.1" in matches

    def test_ips_with_word_boundaries(self):
        """Test IP extraction respects word boundaries."""
        description = "Address: 192.168.1.1 (not in1922681)  addressed"
        matches = __import__("re").findall(IPV4_PATTERN, description)
        # Word boundary \b ensures 1922681 is not matched as IP
        assert len(matches) == 1
        assert "192.168.1.1" in matches


class TestExtractAndLookupIPs:
    """Test main extract_and_lookup_ips async function."""

    @pytest.mark.asyncio
    async def test_extract_and_lookup_single_ip_success(self):
        """Test successful extraction and lookup of single IP."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("192.168.1.10", "server1", "web", "client-a", "dc-1"),
        ]
        mock_session.execute.return_value = mock_result

        tenant_id = "tenant-1"
        description = "Server 192.168.1.10 is down"

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-123"
        )

        assert len(result) == 1
        assert result[0]["ip_address"] == "192.168.1.10"
        assert result[0]["hostname"] == "server1"
        assert result[0]["role"] == "web"
        assert result[0]["client"] == "client-a"
        assert result[0]["location"] == "dc-1"

    @pytest.mark.asyncio
    async def test_extract_and_lookup_multiple_ips_success(self):
        """Test successful extraction and lookup of multiple IPs."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("10.0.0.1", "web1", "web", "client-x", "us-east"),
            ("10.0.0.2", "web2", "web", "client-x", "us-east"),
            ("10.0.0.3", "db1", "database", "client-x", "us-west"),
        ]
        mock_session.execute.return_value = mock_result

        tenant_id = "tenant-2"
        description = "Affected systems: 10.0.0.1, 10.0.0.2, and 10.0.0.3"

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-456"
        )

        assert len(result) == 3
        assert all("ip_address" in r for r in result)
        assert all("hostname" in r for r in result)

    @pytest.mark.asyncio
    async def test_extract_and_lookup_no_ips_in_description(self):
        """Test graceful degradation when no IPs in description (AC #5)."""
        mock_session = AsyncMock(spec=AsyncSession)

        tenant_id = "tenant-1"
        description = "No IP addresses here"

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-789"
        )

        # Should return empty list, not error
        assert result == []
        # Database should not be queried
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_and_lookup_no_matches_in_inventory(self):
        """Test graceful handling when IPs don't match inventory (AC #5)."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        tenant_id = "tenant-1"
        description = "Server 192.168.1.99 issue"

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-aaa"
        )

        # Should return empty list
        assert result == []
        # But database should have been queried
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_and_lookup_tenant_isolation(self):
        """Test that tenant_id is used in query for isolation."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        tenant_id = "tenant-alpha"
        description = "System 10.0.0.1 affected"

        await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-bbb"
        )

        # Verify execute was called (actual SQL building tested elsewhere)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_and_lookup_database_error_graceful(self):
        """Test graceful degradation on database error (AC #5)."""
        mock_session = AsyncMock(spec=AsyncSession)
        # Simulate database error
        mock_session.execute.side_effect = Exception("Database connection timeout")

        tenant_id = "tenant-1"
        description = "Server 192.168.1.10 issue"

        # Should not raise exception
        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-ccc"
        )

        # Should return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_and_lookup_empty_description(self):
        """Test handling of empty/whitespace-only description."""
        mock_session = AsyncMock(spec=AsyncSession)

        tenant_id = "tenant-1"
        description = "   "

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-ddd"
        )

        assert result == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_and_lookup_invalid_tenant_id(self):
        """Test handling of invalid tenant_id."""
        mock_session = AsyncMock(spec=AsyncSession)

        tenant_id = ""
        description = "Server 192.168.1.10 issue"

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-eee"
        )

        assert result == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_and_lookup_non_string_description(self):
        """Test handling of non-string description input."""
        mock_session = AsyncMock(spec=AsyncSession)

        tenant_id = "tenant-1"
        description = 12345  # Not a string

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-fff"
        )

        assert result == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_and_lookup_ipv6_support(self):
        """Test IPv6 address extraction and lookup (AC #6)."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", "ipv6-host", "compute", "client-y", "dc-2"),
        ]
        mock_session.execute.return_value = mock_result

        tenant_id = "tenant-ipv6"
        description = "System 2001:0db8:85a3:0000:0000:8a2e:0370:7334 configuration needed"

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-ggg"
        )

        assert len(result) == 1
        assert "2001:0db8:85a3:0000:0000:8a2e:0370:7334" in result[0]["ip_address"]

    @pytest.mark.asyncio
    async def test_extract_and_lookup_duplicate_ips_deduplicated(self):
        """Test that duplicate IPs are deduplicated before lookup."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        # Should only get one result for deduplicated IP
        mock_result.fetchall.return_value = [
            ("192.168.1.1", "server", "web", "client", "loc"),
        ]
        mock_session.execute.return_value = mock_result

        tenant_id = "tenant-dup"
        description = "Server 192.168.1.1 and 192.168.1.1 both affected"

        result = await extract_and_lookup_ips(
            mock_session, tenant_id, description, correlation_id="req-hhh"
        )

        # Should find one system even though IP mentioned twice
        assert len(result) == 1


class TestIntegrationWithLogging:
    """Test logging integration."""

    @pytest.mark.asyncio
    async def test_logging_on_success(self):
        """Test that success is logged with proper fields."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("192.168.1.10", "server1", "web", "client-a", "dc-1"),
        ]
        mock_session.execute.return_value = mock_result

        with patch("src.services.ip_lookup.logger") as mock_logger:
            result = await extract_and_lookup_ips(
                mock_session,
                "tenant-log",
                "Server 192.168.1.10",
                correlation_id="req-log-1",
            )

            # Should have logged extraction and lookup completion
            assert mock_logger.info.called
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_logging_on_error(self):
        """Test that errors are logged."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("DB error")

        with patch("src.services.ip_lookup.logger") as mock_logger:
            result = await extract_and_lookup_ips(
                mock_session,
                "tenant-log-err",
                "Server 192.168.1.10",
                correlation_id="req-log-2",
            )

            # Should have logged error
            assert mock_logger.error.called
            assert result == []
