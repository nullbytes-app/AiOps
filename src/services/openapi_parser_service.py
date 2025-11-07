"""
OpenAPI Parser Service - Parse and validate OpenAPI/Swagger specifications.

Story 8.8: OpenAPI Tool Upload and Auto-Generation (Task 2 & 3)
Provides:
- OpenAPI spec parsing using openapi-pydantic
- Spec version detection (Swagger 2.0, OpenAPI 3.0, 3.1)
- Validation with user-friendly error messages
- Tool metadata extraction (name, description, base URL, auth schemes, operations)

Architecture:
- openapi-pydantic for spec parsing (supports Pydantic v1.8+ and v2.x)
- Version-specific parsers (v3_0, v3_1 for OpenAPI 3.x; v2 for Swagger 2.0)
- Comprehensive error handling with line number extraction

Constraints:
- File size ≤ 500 lines
- All functions include type hints and Google-style docstrings
- Graceful error handling with specific validation messages
"""

from typing import Any, Optional

from pydantic import ValidationError


def detect_spec_version(spec_dict: dict[str, Any]) -> str:
    """
    Detect OpenAPI spec version from spec dictionary.

    Args:
        spec_dict: Parsed OpenAPI specification dictionary

    Returns:
        Spec version string: "2.0", "3.0", or "3.1"

    Raises:
        ValueError: If spec version cannot be determined
    """
    # Check for OpenAPI 3.x
    if "openapi" in spec_dict:
        openapi_version = spec_dict["openapi"]
        if openapi_version.startswith("3.0"):
            return "3.0"
        elif openapi_version.startswith("3.1"):
            return "3.1"
        else:
            raise ValueError(f"Unsupported OpenAPI version: {openapi_version}")

    # Check for Swagger 2.0
    elif "swagger" in spec_dict:
        swagger_version = spec_dict["swagger"]
        if swagger_version == "2.0":
            return "2.0"
        else:
            raise ValueError(f"Unsupported Swagger version: {swagger_version}")

    else:
        raise ValueError(
            "Cannot determine spec version. Missing 'openapi' or 'swagger' field."
        )


def parse_openapi_spec(spec_dict: dict[str, Any]) -> Any:
    """
    Parse and validate OpenAPI specification using openapi-pydantic.

    Args:
        spec_dict: Parsed OpenAPI specification dictionary

    Returns:
        Validated openapi-pydantic OpenAPI object

    Raises:
        ValueError: If spec version is unsupported or spec is invalid
        ValidationError: If Pydantic validation fails
    """
    # Detect version
    spec_version = detect_spec_version(spec_dict)

    # Import appropriate parser based on version
    try:
        if spec_version == "3.0":
            from openapi_pydantic.v3.v3_0 import OpenAPI

            return OpenAPI.model_validate(spec_dict)

        elif spec_version == "3.1":
            from openapi_pydantic.v3.v3_1 import OpenAPI

            return OpenAPI.model_validate(spec_dict)

        elif spec_version == "2.0":
            # Swagger 2.0 support (if available in openapi-pydantic)
            # Note: Check library docs for Swagger 2.0 parser availability
            raise ValueError(
                "Swagger 2.0 parsing not yet implemented. "
                "Please use OpenAPI 3.0+ or convert your spec."
            )

        else:
            raise ValueError(f"Unsupported spec version: {spec_version}")

    except ValidationError as e:
        # Re-raise with original validation error for detailed error handling
        raise
    except ImportError as e:
        raise ValueError(f"Failed to import OpenAPI parser for version {spec_version}: {e}")


def extract_base_url(openapi: Any, spec_version: str) -> str:
    """
    Extract base URL from OpenAPI spec.

    Args:
        openapi: Parsed OpenAPI object
        spec_version: Spec version ("2.0", "3.0", "3.1")

    Returns:
        Base URL string

    Raises:
        ValueError: If base URL cannot be extracted
    """
    if spec_version in ["3.0", "3.1"]:
        # OpenAPI 3.x uses servers array
        if hasattr(openapi, "servers") and openapi.servers:
            return openapi.servers[0].url
        else:
            raise ValueError("No servers found in OpenAPI 3.x spec")

    elif spec_version == "2.0":
        # Swagger 2.0 uses host + basePath + schemes
        host = getattr(openapi, "host", None)
        base_path = getattr(openapi, "basePath", "")
        schemes = getattr(openapi, "schemes", ["https"])

        if not host:
            raise ValueError("No host found in Swagger 2.0 spec")

        scheme = schemes[0] if schemes else "https"
        return f"{scheme}://{host}{base_path}"

    else:
        raise ValueError(f"Unsupported spec version: {spec_version}")


def extract_auth_schemes(openapi: Any, spec_version: str) -> dict[str, Any]:
    """
    Extract authentication schemes from OpenAPI spec.

    Args:
        openapi: Parsed OpenAPI object
        spec_version: Spec version ("2.0", "3.0", "3.1")

    Returns:
        Dictionary of security schemes {scheme_name: scheme_details}
    """
    auth_schemes: dict[str, Any] = {}

    if spec_version in ["3.0", "3.1"]:
        # OpenAPI 3.x uses components.securitySchemes
        if hasattr(openapi, "components") and openapi.components:
            if hasattr(openapi.components, "securitySchemes"):
                security_schemes = openapi.components.securitySchemes
                if security_schemes:
                    # Convert Pydantic models to dicts
                    for name, scheme in security_schemes.items():
                        auth_schemes[name] = scheme.model_dump(by_alias=True, exclude_none=True)

    elif spec_version == "2.0":
        # Swagger 2.0 uses securityDefinitions
        if hasattr(openapi, "securityDefinitions"):
            security_defs = openapi.securityDefinitions
            if security_defs:
                for name, scheme in security_defs.items():
                    auth_schemes[name] = scheme.model_dump(by_alias=True, exclude_none=True)

    return auth_schemes


def extract_operations(openapi: Any) -> list[dict[str, Any]]:
    """
    Extract all API operations from OpenAPI spec.

    Args:
        openapi: Parsed OpenAPI object

    Returns:
        List of operation dictionaries [{method, path, operationId, summary, description, parameters}]
    """
    operations: list[dict[str, Any]] = []

    if not hasattr(openapi, "paths") or not openapi.paths:
        return operations

    # Iterate through all paths
    for path, path_item in openapi.paths.items():
        # Get all HTTP methods for this path
        http_methods = ["get", "post", "put", "delete", "patch", "options", "head", "trace"]

        for method in http_methods:
            if hasattr(path_item, method):
                operation = getattr(path_item, method)
                if operation:
                    operations.append(
                        {
                            "method": method.upper(),
                            "path": path,
                            "operationId": getattr(operation, "operationId", None),
                            "summary": getattr(operation, "summary", None),
                            "description": getattr(operation, "description", None),
                            "parameters": (
                                [p.model_dump(by_alias=True, exclude_none=True) for p in operation.parameters]
                                if hasattr(operation, "parameters") and operation.parameters
                                else []
                            ),
                        }
                    )

    return operations


def count_endpoints_by_method(operations: list[dict[str, Any]]) -> dict[str, int]:
    """
    Count endpoints by HTTP method.

    Args:
        operations: List of operation dictionaries

    Returns:
        Dictionary with method counts {GET: 10, POST: 5, ...}
    """
    method_counts: dict[str, int] = {}

    for operation in operations:
        method = operation["method"]
        method_counts[method] = method_counts.get(method, 0) + 1

    return method_counts


def extract_tool_metadata(openapi: Any, spec_version: str) -> dict[str, Any]:
    """
    Extract comprehensive tool metadata from parsed OpenAPI spec.

    Args:
        openapi: Parsed OpenAPI object
        spec_version: Spec version ("2.0", "3.0", "3.1")

    Returns:
        Metadata dictionary with:
        - tool_name: From info.title
        - description: From info.description
        - version: From info.version
        - spec_version: OpenAPI spec version
        - base_url: Extracted base URL
        - auth_schemes: Security schemes dictionary
        - operations: List of all operations
        - endpoint_count: Total endpoint count
        - method_counts: Breakdown by HTTP method
    """
    # Extract basic info
    tool_name = openapi.info.title if hasattr(openapi.info, "title") else "Untitled API"
    description = (
        openapi.info.description if hasattr(openapi.info, "description") else ""
    )
    version = openapi.info.version if hasattr(openapi.info, "version") else "1.0.0"

    # Extract base URL
    try:
        base_url = extract_base_url(openapi, spec_version)
    except ValueError as e:
        base_url = f"ERROR: {str(e)}"

    # Extract auth schemes
    auth_schemes = extract_auth_schemes(openapi, spec_version)

    # Extract operations
    operations = extract_operations(openapi)
    method_counts = count_endpoints_by_method(operations)

    return {
        "tool_name": tool_name,
        "description": description,
        "version": version,
        "spec_version": spec_version,
        "base_url": base_url,
        "auth_schemes": auth_schemes,
        "operations": operations,
        "endpoint_count": len(operations),
        "method_counts": method_counts,
    }


def format_validation_errors(errors: list[dict[str, Any]]) -> str:
    """
    Format Pydantic ValidationError into user-friendly message.

    Args:
        errors: List of error dictionaries from ValidationError.errors()

    Returns:
        Formatted error message string
    """
    formatted_lines = ["⚠️ OpenAPI Specification Validation Errors:\n"]

    for idx, error in enumerate(errors, 1):
        # Extract location path
        loc = error.get("loc", ())
        loc_path = " → ".join(str(part) for part in loc)

        # Get error message and type
        msg = error.get("msg", "Unknown error")
        error_type = error.get("type", "")

        formatted_lines.append(
            f"{idx}. **Location:** {loc_path}\n"
            f"   **Error:** {msg}\n"
            f"   **Type:** {error_type}\n"
        )

    return "\n".join(formatted_lines)


def detect_common_issues(spec_dict: dict[str, Any]) -> list[str]:
    """
    Detect common OpenAPI spec issues and provide suggestions.

    Args:
        spec_dict: Parsed OpenAPI specification dictionary

    Returns:
        List of issue descriptions with suggested fixes
    """
    issues: list[str] = []

    # Check for version mismatch (Swagger 2.0 with OpenAPI 3.x features)
    if "swagger" in spec_dict and "servers" in spec_dict:
        issues.append(
            "❌ **Version Mismatch:** Detected Swagger 2.0 spec but found 'servers' field (OpenAPI 3.x feature). "
            "Either upgrade spec to OpenAPI 3.0+ or remove 'servers' and use 'host' + 'schemes' instead."
        )

    # Check for missing base URL
    if "openapi" in spec_dict:
        if "servers" not in spec_dict or not spec_dict.get("servers"):
            issues.append(
                "⚠️ **Missing Base URL:** No 'servers' array found. "
                "Add a servers array: `servers: [{url: 'https://api.example.com'}]`"
            )
    elif "swagger" in spec_dict:
        if "host" not in spec_dict:
            issues.append(
                "⚠️ **Missing Host:** No 'host' field found in Swagger 2.0 spec. "
                "Add a host field: `host: 'api.example.com'`"
            )

    # Check for missing required fields
    if "info" not in spec_dict:
        issues.append("❌ **Missing Required Field:** 'info' section is required in OpenAPI specs.")

    if "paths" not in spec_dict:
        issues.append("❌ **Missing Required Field:** 'paths' section is required in OpenAPI specs.")

    return issues
