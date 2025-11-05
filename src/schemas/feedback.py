"""
Pydantic schemas for enhancement feedback API (Story 5.5 - AC5).

Defines request/response models for submitting and retrieving enhancement feedback
from technicians. Supports thumbs up/down and 1-5 rating scales for continuous
quality monitoring and roadmap prioritization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FeedbackType(str, Enum):
    """
    Types of feedback that can be submitted.

    - thumbs_up: Positive binary feedback (enhancement was helpful)
    - thumbs_down: Negative binary feedback (enhancement was not helpful)
    - rating: Numeric 1-5 scale rating with optional comment
    """

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"


class FeedbackSubmitRequest(BaseModel):
    """
    Request model for submitting enhancement feedback.

    Used by POST /api/v1/feedback endpoint to capture technician satisfaction
    with ticket enhancements. Supports both quick thumbs up/down feedback
    and detailed 1-5 ratings with optional comments.

    Attributes:
        tenant_id: Tenant identifier (validated against RLS context)
        ticket_id: ServiceDesk ticket ID that was enhanced
        enhancement_id: Optional reference to enhancement_history record
        technician_email: Optional email for feedback attribution (anonymous allowed)
        feedback_type: Type of feedback (thumbs_up, thumbs_down, rating)
        rating_value: Numeric rating 1-5 (required if feedback_type=rating, null otherwise)
        feedback_comment: Optional qualitative feedback text
    """

    tenant_id: str = Field(..., min_length=1, max_length=100, description="Tenant identifier")
    ticket_id: str = Field(..., min_length=1, max_length=255, description="ServiceDesk ticket ID")
    enhancement_id: Optional[UUID] = Field(None, description="Reference to enhancement_history.id")
    technician_email: Optional[str] = Field(None, max_length=255, description="Technician email (optional)")
    feedback_type: FeedbackType = Field(..., description="Type of feedback: thumbs_up, thumbs_down, or rating")
    rating_value: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5 (required if feedback_type=rating)")
    feedback_comment: Optional[str] = Field(None, max_length=5000, description="Optional feedback comment")

    @field_validator("rating_value")
    @classmethod
    def validate_rating_value(cls, v, info):
        """
        Validate rating_value is provided when feedback_type=rating.

        Raises:
            ValueError: If feedback_type=rating but rating_value is null
            ValueError: If feedback_type is thumbs_up/thumbs_down but rating_value is provided
        """
        feedback_type = info.data.get("feedback_type")

        if feedback_type == FeedbackType.RATING:
            if v is None:
                raise ValueError("rating_value is required when feedback_type='rating'")
        else:
            # For thumbs_up/thumbs_down, rating_value should be null
            if v is not None:
                raise ValueError(
                    f"rating_value must be null when feedback_type='{feedback_type.value}'"
                )

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tenant_id": "tenant-abc-123",
                    "ticket_id": "TKT-001",
                    "enhancement_id": "550e8400-e29b-41d4-a716-446655440000",
                    "technician_email": "tech@example.com",
                    "feedback_type": "rating",
                    "rating_value": 5,
                    "feedback_comment": "Very helpful context, resolved ticket 10 min faster!",
                },
                {
                    "tenant_id": "tenant-abc-123",
                    "ticket_id": "TKT-002",
                    "feedback_type": "thumbs_up",
                },
            ]
        }
    }


class FeedbackResponse(BaseModel):
    """
    Response model for feedback submission.

    Returned by POST /api/v1/feedback after successful feedback storage.

    Attributes:
        id: UUID of created feedback record
        status: Operation status (always "created" for successful submissions)
        message: Human-readable confirmation message
    """

    id: UUID = Field(..., description="UUID of created feedback record")
    status: str = Field("created", description="Operation status")
    message: str = Field("Feedback submitted successfully", description="Confirmation message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    "status": "created",
                    "message": "Feedback submitted successfully",
                }
            ]
        }
    }


class FeedbackRecord(BaseModel):
    """
    Model representing a single feedback record for GET responses.

    Used in FeedbackListResponse to return feedback history.

    Attributes:
        id: Feedback record UUID
        tenant_id: Tenant identifier
        ticket_id: ServiceDesk ticket ID
        enhancement_id: Reference to enhancement_history (if available)
        technician_email: Technician email (if provided)
        feedback_type: Type of feedback (thumbs_up, thumbs_down, rating)
        rating_value: Numeric rating 1-5 (null for thumbs up/down)
        feedback_comment: Optional comment text
        created_at: Timestamp when feedback was submitted
    """

    id: UUID
    tenant_id: str
    ticket_id: str
    enhancement_id: Optional[UUID]
    technician_email: Optional[str]
    feedback_type: FeedbackType
    rating_value: Optional[int]
    feedback_comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackListResponse(BaseModel):
    """
    Response model for feedback list retrieval (GET /api/v1/feedback).

    Attributes:
        feedback: List of feedback records matching query filters
        count: Total number of records returned
    """

    feedback: list[FeedbackRecord] = Field(default_factory=list, description="List of feedback records")
    count: int = Field(..., description="Total number of feedback records returned")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "feedback": [
                        {
                            "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                            "tenant_id": "tenant-abc-123",
                            "ticket_id": "TKT-001",
                            "enhancement_id": "550e8400-e29b-41d4-a716-446655440000",
                            "technician_email": "tech@example.com",
                            "feedback_type": "rating",
                            "rating_value": 5,
                            "feedback_comment": "Very helpful!",
                            "created_at": "2025-11-04T10:30:00Z",
                        }
                    ],
                    "count": 1,
                }
            ]
        }
    }
