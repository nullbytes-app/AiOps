"""
Plugin Configuration Form Component (Story 7.8 - AC#5).

Reusable Streamlit component for rendering dynamic plugin configuration forms
based on JSON Schema. Generates form fields with appropriate types and validation.
"""

import re
from typing import Any, Dict, List, Optional

import streamlit as st
from loguru import logger


def render_plugin_config_form(
    plugin_id: str,
    schema_fields: List[Dict[str, Any]],
    existing_config: Optional[Dict[str, Any]] = None,
    form_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Render a dynamic configuration form based on plugin schema.

    Generates Streamlit form fields (text_input, number_input, checkbox, selectbox)
    based on schema field types. Applies validation rules (required, min/max length,
    regex patterns). Returns submitted configuration or None if not submitted.

    Args:
        plugin_id: Plugin identifier for logging and form key
        schema_fields: List of field schema dicts from plugin config schema
        existing_config: Optional existing configuration to pre-populate fields
        form_key: Optional unique form key (defaults to f"config_form_{plugin_id}")

    Returns:
        dict: Submitted configuration {field_name: value} if form submitted
        None: If form not yet submitted or validation failed

    Example:
        schema_fields = [
            {
                "field_name": "jira_url",
                "field_type": "string",
                "required": True,
                "description": "Jira instance URL",
                "pattern": r"^https?://.*\\.atlassian\\.net.*"
            },
            {
                "field_name": "jira_api_token",
                "field_type": "string",
                "required": True,
                "description": "Jira API token",
                "min_length": 20
            }
        ]

        config = render_plugin_config_form("jira", schema_fields)
        if config:
            st.success(f"Configuration saved: {config}")
    """
    if not form_key:
        form_key = f"config_form_{plugin_id}"

    if not existing_config:
        existing_config = {}

    # Create form
    with st.form(key=form_key):
        st.subheader(f"Configure {plugin_id.replace('_', ' ').title()}")

        config_values = {}
        validation_errors = []

        # Generate form fields
        for field in schema_fields:
            field_name = field.get("field_name", "")
            field_type = field.get("field_type", "string")
            required = field.get("required", False)
            description = field.get("description", "")
            default_value = field.get("default")
            min_length = field.get("min_length")
            max_length = field.get("max_length")
            pattern = field.get("pattern")
            enum_values = field.get("enum_values")

            # Get existing value or default
            current_value = existing_config.get(field_name, default_value)

            # Build label
            label = field_name.replace("_", " ").title()
            if required:
                label += " *"

            # Build help text
            help_text = description
            if min_length or max_length:
                help_text += f" (Length: "
                if min_length:
                    help_text += f"min {min_length}"
                if max_length:
                    if min_length:
                        help_text += f", max {max_length}"
                    else:
                        help_text += f"max {max_length}"
                help_text += ")"
            if pattern:
                help_text += f" (Pattern: {pattern})"

            # Render field based on type
            try:
                if field_type == "boolean":
                    value = st.checkbox(
                        label,
                        value=bool(current_value) if current_value is not None else False,
                        help=help_text,
                    )
                    config_values[field_name] = value

                elif field_type in ["integer", "number"]:
                    value = st.number_input(
                        label,
                        value=int(current_value) if current_value is not None else 0,
                        help=help_text,
                    )
                    config_values[field_name] = value

                elif field_type == "enum" and enum_values:
                    # Enum field (selectbox)
                    current_index = 0
                    if current_value and current_value in enum_values:
                        current_index = enum_values.index(current_value)

                    value = st.selectbox(
                        label,
                        options=enum_values,
                        index=current_index,
                        help=help_text,
                    )
                    config_values[field_name] = value

                else:
                    # String field (default)
                    # Use password input for fields with "token", "key", "password", "secret" in name
                    is_sensitive = any(
                        keyword in field_name.lower()
                        for keyword in ["token", "key", "password", "secret", "api_key"]
                    )

                    if is_sensitive:
                        value = st.text_input(
                            label,
                            value=str(current_value) if current_value else "",
                            type="password",
                            help=help_text,
                            placeholder="Enter secure value...",
                        )
                    else:
                        value = st.text_input(
                            label,
                            value=str(current_value) if current_value else "",
                            help=help_text,
                            placeholder=f"Enter {field_name}...",
                        )

                    config_values[field_name] = value

            except Exception as e:
                logger.error(f"Error rendering field {field_name}: {str(e)}")
                st.error(f"Error rendering field '{field_name}': {str(e)}")

        st.markdown("---")

        # Form actions
        col1, col2 = st.columns([1, 4])

        with col1:
            submit_button = st.form_submit_button("💾 Save Configuration", type="primary")

        with col2:
            test_button = st.form_submit_button("🧪 Test Connection")

        # Process form submission
        if submit_button or test_button:
            # Validate configuration
            for field in schema_fields:
                field_name = field.get("field_name", "")
                required = field.get("required", False)
                min_length = field.get("min_length")
                max_length = field.get("max_length")
                pattern = field.get("pattern")

                value = config_values.get(field_name, "")

                # Required field validation
                if required and not value:
                    validation_errors.append(f"❌ {field_name}: Required field is empty")
                    continue

                # Skip validation if field is empty and not required
                if not value:
                    continue

                # String length validation
                if isinstance(value, str):
                    if min_length and len(value) < min_length:
                        validation_errors.append(
                            f"❌ {field_name}: Must be at least {min_length} characters"
                        )
                    if max_length and len(value) > max_length:
                        validation_errors.append(
                            f"❌ {field_name}: Must be at most {max_length} characters"
                        )

                # Regex pattern validation
                if pattern and isinstance(value, str):
                    try:
                        if not re.match(pattern, value):
                            validation_errors.append(
                                f"❌ {field_name}: Does not match required pattern"
                            )
                    except re.error as e:
                        logger.error(f"Invalid regex pattern for {field_name}: {str(e)}")
                        validation_errors.append(
                            f"❌ {field_name}: Invalid validation pattern (config error)"
                        )

            # Display validation errors
            if validation_errors:
                st.error("**Validation Errors:**")
                for error in validation_errors:
                    st.error(error)
                logger.warning(
                    f"Form validation failed for {plugin_id}: {len(validation_errors)} errors"
                )
                return None

            # Store which button was clicked in session state
            if submit_button:
                st.session_state[f"{form_key}_action"] = "save"
            elif test_button:
                st.session_state[f"{form_key}_action"] = "test"

            logger.info(
                f"Configuration form submitted for {plugin_id}: "
                f"{len(config_values)} fields validated"
            )

            return config_values

    return None


def get_form_action(plugin_id: str, form_key: Optional[str] = None) -> Optional[str]:
    """
    Get the action that triggered form submission.

    Args:
        plugin_id: Plugin identifier
        form_key: Optional form key (defaults to f"config_form_{plugin_id}")

    Returns:
        str: "save" or "test" if form submitted, None otherwise
    """
    if not form_key:
        form_key = f"config_form_{plugin_id}"

    action_key = f"{form_key}_action"
    action = st.session_state.get(action_key)

    # Clear action from session state after reading
    if action:
        del st.session_state[action_key]

    return action


def display_validation_summary(validation_errors: List[str]) -> None:
    """
    Display validation errors in a formatted error box.

    Args:
        validation_errors: List of validation error messages
    """
    if not validation_errors:
        return

    st.error("**❌ Configuration Validation Failed**")
    st.markdown(f"Found {len(validation_errors)} error(s):")

    for i, error in enumerate(validation_errors, 1):
        st.markdown(f"{i}. {error}")

    st.info(
        "💡 **Tip:** Review the field descriptions and validation rules above. "
        "Required fields are marked with an asterisk (*)."
    )


def display_test_result(success: bool, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Display connection test results with appropriate styling.

    Args:
        success: True if connection test succeeded
        message: Test result message
        details: Optional additional details (response time, error codes, etc.)
    """
    if success:
        st.success(f"✅ **Connection Test Successful**\n\n{message}")
        if details:
            with st.expander("📊 Test Details"):
                st.json(details)
    else:
        st.error(f"❌ **Connection Test Failed**\n\n{message}")
        if details:
            with st.expander("🔍 Error Details"):
                st.json(details)

        st.info(
            "💡 **Troubleshooting:**\n"
            "- Verify URL format (must include https://)\n"
            "- Check API token/key validity\n"
            "- Ensure network connectivity to the ticketing tool\n"
            "- Review error details above for specific failure reason"
        )
