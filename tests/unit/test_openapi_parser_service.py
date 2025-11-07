"""Unit tests for OpenAPI parser service.

Tests cover:
- Spec version detection
- OpenAPI parsing and validation
- Metadata extraction
- Error formatting
"""

import pytest
from pydantic import ValidationError

from services.openapi_parser_service import (
    detect_spec_version,
    parse_openapi_spec,
    extract_tool_metadata,
    format_validation_errors,
    detect_common_issues,
)


class TestSpecVersionDetection:
    """Test OpenAPI spec version detection."""

    def test_detect_openapi_3_0(self) -> None:
        """Test detection of OpenAPI 3.0."""
        spec = {"openapi": "3.0.0", "info": {"title": "Test"}}
        assert detect_spec_version(spec) == "3.0"

    def test_detect_openapi_3_1(self) -> None:
        """Test detection of OpenAPI 3.1."""
        spec = {"openapi": "3.1.0", "info": {"title": "Test"}}
        assert detect_spec_version(spec) == "3.1"

    def test_detect_swagger_2_0(self) -> None:
        """Test detection of Swagger 2.0."""
        spec = {"swagger": "2.0", "info": {"title": "Test"}}
        assert detect_spec_version(spec) == "2.0"

    def test_missing_version_field_raises_error(self) -> None:
        """Test error when no version field present."""
        spec = {"info": {"title": "Test"}}
        with pytest.raises(ValueError, match="Cannot determine spec version"):
            detect_spec_version(spec)


class TestCommonIssuesDetection:
    """Test detection of common OpenAPI spec issues."""

    def test_detect_swagger_with_openapi_3_features(self) -> None:
        """Test detection of version mismatch."""
        spec = {"swagger": "2.0", "servers": [{"url": "https://api.example.com"}]}
        issues = detect_common_issues(spec)
        assert len(issues) > 0
        assert "Version Mismatch" in issues[0]

    def test_detect_missing_servers_in_openapi_3(self) -> None:
        """Test detection of missing servers array."""
        spec = {"openapi": "3.0.0", "info": {"title": "Test"}, "paths": {}}
        issues = detect_common_issues(spec)
        assert any("Missing Base URL" in issue for issue in issues)

    def test_detect_missing_info_section(self) -> None:
        """Test detection of missing required info section."""
        spec = {"openapi": "3.0.0", "paths": {}}
        issues = detect_common_issues(spec)
        assert any("Missing Required Field" in issue and "info" in issue for issue in issues)

    def test_no_issues_for_valid_spec(self) -> None:
        """Test no issues detected for valid spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {"/users": {"get": {}}},
        }
        issues = detect_common_issues(spec)
        # Should have minimal or no issues for valid spec
        assert len(issues) == 0 or all("Missing" not in issue for issue in issues)


class TestErrorFormatting:
    """Test user-friendly error formatting."""

    def test_format_validation_errors(self) -> None:
        """Test formatting of Pydantic validation errors."""
        errors = [
            {"loc": ("info", "title"), "msg": "Field required", "type": "value_error.missing"},
            {"loc": ("paths",), "msg": "Field required", "type": "value_error.missing"},
        ]
        formatted = format_validation_errors(errors)

        assert "info → title" in formatted
        assert "paths" in formatted
        assert "Field required" in formatted


class TestOpenAPISpecParsing:
    """Test OpenAPI spec parsing with openapi-pydantic."""

    def test_parse_valid_openapi_3_0_spec(self) -> None:
        """Test parsing valid OpenAPI 3.0 spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "GitHub API", "version": "1.0.0"},
            "servers": [{"url": "https://api.github.com"}],
            "paths": {
                "/users": {"get": {"summary": "List users", "responses": {"200": {"description": "OK"}}}}
            },
        }
        parsed = parse_openapi_spec(spec)
        assert parsed is not None
        # Check openapi-pydantic parsed the spec correctly
        assert hasattr(parsed, "info")
        assert hasattr(parsed, "paths")

    def test_parse_valid_openapi_3_1_spec(self) -> None:
        """Test parsing valid OpenAPI 3.1 spec."""
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        parsed = parse_openapi_spec(spec)
        assert parsed is not None

    def test_parse_spec_missing_info_field_raises_error(self) -> None:
        """Test parsing spec without required 'info' field raises error."""
        spec = {
            "openapi": "3.0.0",
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        with pytest.raises((ValidationError, KeyError, ValueError)):
            parse_openapi_spec(spec)

    def test_parse_spec_missing_paths_field_raises_error(self) -> None:
        """Test parsing spec without 'paths' field raises error."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
        }
        with pytest.raises((ValidationError, KeyError, ValueError)):
            parse_openapi_spec(spec)

    def test_parse_spec_invalid_path_operations(self) -> None:
        """Test parsing spec with invalid path operations raises error."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        # Missing required 'responses' field
                        "summary": "List users"
                    }
                }
            },
        }
        with pytest.raises((ValidationError, KeyError, ValueError)):
            parse_openapi_spec(spec)


class TestMetadataExtraction:
    """Test metadata extraction from parsed OpenAPI specs."""

    def test_extract_tool_name_from_info_title(self) -> None:
        """Test extracting tool name from info.title."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "GitHub API", "description": "GitHub REST API", "version": "1.0.0"},
            "servers": [{"url": "https://api.github.com"}],
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        parsed = parse_openapi_spec(spec)
        metadata = extract_tool_metadata(parsed, "3.0")

        assert metadata["tool_name"] == "GitHub API"
        assert metadata["description"] == "GitHub REST API"

    def test_extract_base_url_from_servers_openapi_3x(self) -> None:
        """Test extracting base URL from servers array (OpenAPI 3.x)."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        parsed = parse_openapi_spec(spec)
        metadata = extract_tool_metadata(parsed, "3.0")

        assert metadata["base_url"] == "https://api.example.com/v1"

    def test_extract_operations_list_correctly(self) -> None:
        """Test extracting operations list with method and path details."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/users": {
                    "get": {"operationId": "listUsers", "summary": "List users", "responses": {"200": {"description": "OK"}}},
                    "post": {"operationId": "createUser", "summary": "Create user", "responses": {"201": {"description": "Created"}}},
                },
                "/users/{id}": {
                    "get": {"operationId": "getUser", "summary": "Get user", "responses": {"200": {"description": "OK"}}},
                },
            },
        }
        parsed = parse_openapi_spec(spec)
        metadata = extract_tool_metadata(parsed, "3.0")

        operations = metadata.get("operations", [])
        assert len(operations) == 3  # 3 total operations (GET /users, POST /users, GET /users/{id})

        # Verify operation details
        operation_ids = [op.get("operationId") for op in operations]
        assert "listUsers" in operation_ids
        assert "createUser" in operation_ids
        assert "getUser" in operation_ids
