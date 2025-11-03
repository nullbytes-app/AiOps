"""
Input validation constants for webhook and API request validation.

Defines maximum length constraints for various fields to prevent oversized inputs
and enforce consistent validation across the application per Epic 3 security requirements.
"""

# Ticket field length constraints (AC3)
MAX_TICKET_DESCRIPTION_LENGTH = 10000  # 10K chars for ticket descriptions
MAX_TICKET_ID_LENGTH = 100  # Standard ServiceDesk Plus ticket ID length
MAX_TENANT_ID_LENGTH = 100  # Tenant identifier length
MAX_RESOLUTION_LENGTH = 20000  # 20K chars for detailed resolutions (2x description)
MAX_URL_LENGTH = 500  # Maximum URL length for external links
MAX_SUBJECT_LENGTH = 500  # Ticket subject/title length

# Field format patterns (AC1)
TICKET_ID_PATTERN = r"^[A-Z0-9-]+$"  # Alphanumeric + dashes (e.g., "TKT-12345")
TENANT_ID_PATTERN = r"^[a-z0-9-]+$"  # Lowercase alphanumeric + dashes (e.g., "tenant-abc")

# Sanitization patterns (AC2, AC5)
DANGEROUS_CONTROL_CHARS_PATTERN = r"[\x00-\x08\x0B\x0C\x0E-\x1F]"  # Exclude \n (0x0A) and \t (0x09)
NULL_BYTE = "\x00"
