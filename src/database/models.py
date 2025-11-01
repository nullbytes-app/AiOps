"""
SQLAlchemy database models.

This module will contain all database models (tables) for the application.
Models will be implemented in Story 1.3 when the database schema is defined.
"""

from sqlalchemy.ext.declarative import declarative_base

# Base class for all database models
Base = declarative_base()

# Future models will be added here in Story 1.3:
# - Tenant
# - Ticket
# - EnhancementJob
# - etc.
