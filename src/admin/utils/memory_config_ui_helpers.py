"""
Streamlit UI helper functions for memory configuration management.

Provides reusable UI components for memory configuration forms, memory
state viewer, and memory clearing with confirmation dialogs.

Story 8.15: Memory Configuration UI - Streamlit UI Helpers (Task 5)
"""

from typing import Any, Dict, Optional
from uuid import UUID

import streamlit as st

from src.schemas.memory import (
    AgenticMemoryConfig,
    LongTermMemoryConfig,
    MemoryConfig,
    ShortTermMemoryConfig,
    VectorDBType,
)


def render_memory_config_form(
    current_config: Optional[MemoryConfig] = None,
) -> Dict[str, Any]:
    """
    Render memory configuration form with three sections.

    Creates interactive form with st.number_input(), st.checkbox(),
    st.selectbox() for configuring short-term, long-term, and agentic
    memory settings.

    Args:
        current_config: Current memory configuration or None for defaults

    Returns:
        Dict[str, Any]: Form data dictionary with memory configuration
    """
    # Initialize with defaults if no current config
    if current_config is None:
        current_config = MemoryConfig()

    form_data = {}

    # Short-Term Memory Section
    st.subheader("Short-Term Memory (Conversation History)")
    st.markdown(
        "Short-term memory maintains recent conversation context within a single session."
    )

    col1, col2 = st.columns(2)

    with col1:
        context_window = st.number_input(
            "Context Window Size (tokens)",
            min_value=512,
            max_value=128000,
            value=current_config.short_term.context_window_size,
            step=512,
            help="Maximum tokens in conversation context. Higher values allow longer conversations but increase costs.",
            key="memory_context_window",
        )

    with col2:
        history_length = st.number_input(
            "Conversation History Length (messages)",
            min_value=1,
            max_value=100,
            value=current_config.short_term.conversation_history_length,
            step=1,
            help="Maximum number of messages to retain in short-term memory.",
            key="memory_history_length",
        )

    form_data["short_term"] = ShortTermMemoryConfig(
        context_window_size=context_window,
        conversation_history_length=history_length,
    )

    st.divider()

    # Long-Term Memory Section
    st.subheader("Long-Term Memory (Semantic Memory)")
    st.markdown(
        "Long-term memory stores important information across sessions using vector similarity search."
    )

    col1, col2 = st.columns(2)

    with col1:
        long_term_enabled = st.checkbox(
            "Enable Long-Term Memory",
            value=current_config.long_term.enabled,
            help="Enable persistent semantic memory with vector search.",
            key="memory_long_term_enabled",
        )

        vector_db_options = [
            VectorDBType.POSTGRESQL_PGVECTOR.value,
            VectorDBType.EXTERNAL.value,
        ]
        vector_db = st.selectbox(
            "Vector Database",
            options=vector_db_options,
            index=vector_db_options.index(current_config.long_term.vector_db),
            disabled=not long_term_enabled,
            help="Vector database backend for similarity search. External option coming soon.",
            key="memory_vector_db",
        )

    with col2:
        long_term_retention = st.number_input(
            "Retention Period (days)",
            min_value=1,
            max_value=3650,
            value=current_config.long_term.retention_days,
            step=1,
            disabled=not long_term_enabled,
            help="Days to retain long-term memories before auto-deletion (1-3650).",
            key="memory_long_term_retention",
        )

    form_data["long_term"] = LongTermMemoryConfig(
        enabled=long_term_enabled,
        vector_db=vector_db,
        retention_days=long_term_retention,
    )

    st.divider()

    # Agentic Memory Section
    st.subheader("Agentic Memory (Structured Notes)")
    st.markdown(
        "Agentic memory allows agents to autonomously extract and store structured facts."
    )

    col1, col2 = st.columns(2)

    with col1:
        agentic_enabled = st.checkbox(
            "Enable Agentic Memory",
            value=current_config.agentic.enabled,
            help="Allow agent to extract and store structured notes automatically.",
            key="memory_agentic_enabled",
        )

    with col2:
        agentic_retention = st.number_input(
            "Retention Period (days)",
            min_value=1,
            max_value=3650,
            value=current_config.agentic.retention_days,
            step=1,
            disabled=not agentic_enabled,
            help="Days to retain agentic memories before auto-deletion (1-3650).",
            key="memory_agentic_retention",
        )

    form_data["agentic"] = AgenticMemoryConfig(
        enabled=agentic_enabled,
        retention_days=agentic_retention,
    )

    return form_data


def render_memory_viewer(memory_state: Dict[str, Any]) -> None:
    """
    Render memory state viewer with expandable sections.

    Displays current memory state with st.expander() sections for each
    memory type (short-term, long-term, agentic) showing content and
    statistics.

    Args:
        memory_state: Memory state dictionary from API
    """
    st.subheader("Current Memory State")

    # Handle case where memory_state might not be a dictionary (e.g., agent_id string)
    if not isinstance(memory_state, dict):
        st.info("No memories stored yet. Memories will appear here after agent execution.")
        return

    # Display statistics
    stats = memory_state.get("stats", {})
    total_count = stats.get("total_count", 0)

    if total_count == 0:
        st.info("No memories stored yet. Memories will appear here after agent execution.")
        return

    # Display summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Memories",
            total_count,
            help="Total number of memories across all types",
        )

    with col2:
        by_type = stats.get("by_type", {})
        long_term_count = by_type.get("long_term", {}).get("count", 0)
        st.metric(
            "Long-Term Memories",
            long_term_count,
            help="Semantic memories with embeddings",
        )

    with col3:
        short_term_count = by_type.get("short_term", {}).get("count", 0)
        st.metric(
            "Short-Term Memories",
            short_term_count,
            help="Recent conversation messages",
        )

    st.divider()

    # Short-Term Memories Expander
    short_term_memories = memory_state.get("short_term_memories", [])
    with st.expander(
        f"Short-Term Memories ({len(short_term_memories)})",
        expanded=len(short_term_memories) > 0,
    ):
        if short_term_memories:
            for i, memory in enumerate(short_term_memories, 1):
                with st.container():
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        content = memory.get("content", {})
                        # Reason: Display conversation messages in chat-like format
                        role = content.get("role", "unknown")
                        text = content.get("text", content.get("content", str(content)))

                        if role == "user":
                            st.markdown(f"**User:** {text}")
                        elif role == "assistant":
                            st.markdown(f"**Assistant:** {text}")
                        else:
                            st.markdown(f"**{role.title()}:** {text}")

                    with col2:
                        created_at = memory.get("created_at", "")
                        if created_at:
                            st.caption(f"🕒 {created_at[:19]}")

                    if i < len(short_term_memories):
                        st.divider()
        else:
            st.info("No short-term memories stored.")

    # Long-Term Memories Expander
    long_term_memories = memory_state.get("long_term_memories", [])
    with st.expander(
        f"Long-Term Memories ({len(long_term_memories)})",
        expanded=len(long_term_memories) > 0,
    ):
        if long_term_memories:
            for i, memory in enumerate(long_term_memories, 1):
                with st.container():
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        content = memory.get("content", {})
                        text = content.get("text", str(content))
                        source = content.get("source", "unknown")

                        st.markdown(f"**{text}**")
                        st.caption(f"Source: {source}")

                    with col2:
                        created_at = memory.get("created_at", "")
                        if created_at:
                            st.caption(f"🕒 {created_at[:19]}")

                        # Display similarity score if available
                        similarity_score = memory.get("similarity_score")
                        if similarity_score:
                            st.caption(f"📊 Score: {similarity_score:.2f}")

                    if i < len(long_term_memories):
                        st.divider()
        else:
            st.info("No long-term memories stored.")

    # Agentic Memories Expander
    agentic_memories = memory_state.get("agentic_memories", [])
    with st.expander(
        f"Agentic Memories ({len(agentic_memories)})",
        expanded=len(agentic_memories) > 0,
    ):
        if agentic_memories:
            for i, memory in enumerate(agentic_memories, 1):
                with st.container():
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        content = memory.get("content", {})
                        text = content.get("text", str(content))
                        fact_type = content.get("type", "note")

                        st.markdown(f"**{text}**")
                        st.caption(f"Type: {fact_type}")

                    with col2:
                        created_at = memory.get("created_at", "")
                        if created_at:
                            st.caption(f"🕒 {created_at[:19]}")

                    if i < len(agentic_memories):
                        st.divider()
        else:
            st.info("No agentic memories stored.")


def clear_memory_confirmation(
    agent_id: UUID,
    on_clear_callback=None,
) -> None:
    """
    Render memory clearing interface with confirmation.

    Displays memory type selector and clear button with st.warning()
    confirmation dialog to prevent accidental deletion.

    Args:
        agent_id: Agent UUID for clearing memory
        on_clear_callback: Optional callback function(agent_id, memory_type) to execute on clear
    """
    st.subheader("Clear Agent Memory")
    st.warning(
        "⚠️ **Warning:** Clearing memory is permanent and cannot be undone. "
        "The agent will lose all stored context and will start fresh."
    )

    # Memory type selector
    memory_type_options = {
        "All Types": None,
        "Short-Term Only": "short_term",
        "Long-Term Only": "long_term",
        "Agentic Only": "agentic",
    }

    selected_option = st.selectbox(
        "Select Memory Type to Clear",
        options=list(memory_type_options.keys()),
        index=0,
        help="Choose which memory types to clear. 'All Types' will delete everything.",
        key="memory_clear_type",
    )

    memory_type = memory_type_options[selected_option]

    # Confirmation checkbox
    confirm_clear = st.checkbox(
        f"I understand that clearing {selected_option.lower()} memory is permanent",
        value=False,
        key="memory_clear_confirm",
    )

    # Clear button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        clear_button = st.button(
            f"🗑️ Clear {selected_option}",
            type="primary",
            disabled=not confirm_clear,
            use_container_width=True,
            key="memory_clear_button",
        )

    if clear_button and confirm_clear:
        if on_clear_callback is None:
            st.warning("Memory clearing functionality is not available in this context.")
            return

        try:
            # Execute clear callback
            result = on_clear_callback(agent_id, memory_type)

            if result.get("success"):
                cleared_count = result.get("cleared_count", 0)
                st.success(
                    f"✅ Successfully cleared {cleared_count} memories ({selected_option})"
                )

                # Reset confirmation checkbox
                st.session_state.memory_clear_confirm = False

                # Trigger rerun to refresh memory state
                st.rerun()
            else:
                error_msg = result.get("error", "Unknown error occurred")
                st.error(f"❌ Failed to clear memory: {error_msg}")

        except Exception as e:
            st.error(f"❌ Error clearing memory: {str(e)}")


def render_memory_stats_summary(stats: Dict[str, Any]) -> None:
    """
    Render memory statistics summary panel.

    Displays aggregated memory statistics including counts, oldest/newest
    timestamps, and retention policy information.

    Args:
        stats: Statistics dictionary from memory state
    """
    st.subheader("Memory Statistics")

    total_count = stats.get("total_count", 0)
    by_type = stats.get("by_type", {})

    if total_count == 0:
        st.info("No memory statistics available. Agent hasn't stored any memories yet.")
        return

    # Display statistics table
    table_data = []

    for memory_type, type_stats in by_type.items():
        count = type_stats.get("count", 0)
        oldest = type_stats.get("oldest", "N/A")
        newest = type_stats.get("newest", "N/A")

        # Format timestamps
        if oldest != "N/A":
            oldest = oldest[:19].replace("T", " ")
        if newest != "N/A":
            newest = newest[:19].replace("T", " ")

        table_data.append(
            {
                "Memory Type": memory_type.replace("_", " ").title(),
                "Count": count,
                "Oldest": oldest,
                "Newest": newest,
            }
        )

    if table_data:
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
        )


def get_memory_config_defaults() -> MemoryConfig:
    """
    Get default memory configuration values.

    Returns:
        MemoryConfig: Default memory configuration object
    """
    return MemoryConfig(
        short_term=ShortTermMemoryConfig(
            context_window_size=4096,
            conversation_history_length=10,
        ),
        long_term=LongTermMemoryConfig(
            enabled=True,
            vector_db="postgresql_pgvector",
            retention_days=90,
        ),
        agentic=AgenticMemoryConfig(
            enabled=False,
            retention_days=90,
        ),
    )
