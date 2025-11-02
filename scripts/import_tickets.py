"""
Bulk import script for historical tickets from ServiceDesk Plus API.

This script enables platform operators to seed tenant deployments with historical
ticket context data during onboarding. It fetches closed/resolved tickets from
ServiceDesk Plus API v3, transforms the data, and stores them in the ticket_history
table with provenance tracking.

Usage:
    python scripts/import_tickets.py --tenant-id=acme-corp --days=90
    python scripts/import_tickets.py --tenant-id=acme-corp --start-date=2024-01-01 --end-date=2024-03-31
    python scripts/import_tickets.py --tenant-id=acme-corp --days=180 --log-level=DEBUG

Exit Codes:
    0 = Success
    1 = Invalid arguments (missing --tenant-id, invalid dates)
    2 = Tenant not found in tenant_configs table
    3 = API error (401, 403, 500+, all retries exhausted)
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple

import httpx
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DatabaseError

from src.database.models import TicketHistory
from src.database.session import async_session_maker
from src.utils.logger import configure_logging


# Configure structured logging with tenant context
def setup_logger(log_level: str = "INFO") -> None:
    """
    Configure loguru logger with structured output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    configure_logging(log_level.upper())


async def fetch_tenant_config(tenant_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch tenant configuration from database.

    Loads ServiceDesk Plus API credentials (base_url, api_key) for the given tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Tuple of (base_url, api_key) or (None, None) if tenant not found

    Raises:
        DatabaseError: If database connection fails
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                text(
                    "SELECT base_url, api_key FROM tenant_configs WHERE tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_id},
            )
            row = result.fetchone()
            if row:
                return row[0], row[1]
            return None, None
    except DatabaseError as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        raise


async def fetch_tickets_page(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    start_index: int,
    row_count: int,
    start_date: datetime,
    end_date: datetime,
    retry_count: int = 0,
) -> Tuple[list, bool]:
    """
    Fetch a single page of tickets from ServiceDesk Plus API.

    Implements pagination and exponential backoff for rate limits and transient errors.

    Args:
        client: httpx.AsyncClient for API calls
        base_url: ServiceDesk Plus API base URL
        api_key: Zoho API token for authentication
        start_index: Starting row index (1-based)
        row_count: Number of rows to fetch per page (max 100)
        start_date: Start of date range (milliseconds since epoch)
        end_date: End of date range (milliseconds since epoch)
        retry_count: Current retry attempt (internal)

    Returns:
        Tuple of (tickets_list, has_more_rows)

    Raises:
        httpx.HTTPStatusError: If API returns non-retryable error (401, 403)
        Exception: If all retries exhausted or unexpected error
    """
    max_retries = 3
    start_date_ms = int(start_date.timestamp() * 1000)
    end_date_ms = int(end_date.timestamp() * 1000)

    payload = {
        "list_info": {"start_index": start_index, "row_count": row_count},
        "input_data": {
            "status": {"name": ["Closed", "Resolved"]},
            "resolved_time": {"from": start_date_ms, "to": end_date_ms},
        },
    }

    headers = {
        "Authorization": f"Zoho-oauthtoken {api_key}",
        "Accept": "application/vnd.manageengine.sdp.v3+json",
        "Content-Type": "application/json",
    }

    try:
        logger.debug(
            f"Fetching page: start_index={start_index}, row_count={row_count}"
        )
        response = await client.post(
            f"{base_url}/api/v3/requests",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        response_status = data.get("response_status", [{}])[0]

        if response_status.get("status_code") != 2000:
            logger.error(f"API error: {response_status.get('status')}")
            raise Exception(f"API returned error: {response_status}")

        requests_list = data.get("requests", [])
        list_info = data.get("list_info", {})
        has_more_rows = list_info.get("has_more_rows", False)

        logger.debug(
            f"Fetched {len(requests_list)} tickets, has_more_rows={has_more_rows}"
        )
        return requests_list, has_more_rows

    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            logger.error(
                f"Authentication error: {e.response.status_code}. Exiting."
            )
            raise
        elif e.response.status_code == 429:
            if retry_count < max_retries:
                wait_time = 60
                logger.warning(
                    f"Rate limit hit (429). Waiting {wait_time}s before retry ({retry_count + 1}/{max_retries})"
                )
                await asyncio.sleep(wait_time)
                return await fetch_tickets_page(
                    client,
                    base_url,
                    api_key,
                    start_index,
                    row_count,
                    start_date,
                    end_date,
                    retry_count + 1,
                )
            else:
                logger.error("Rate limit retries exhausted. Exiting.")
                raise
        elif e.response.status_code in (500, 502, 503):
            if retry_count < max_retries:
                wait_time = 2 ** (retry_count + 1)  # Exponential backoff
                logger.warning(
                    f"Server error {e.response.status_code}. Waiting {wait_time}s before retry ({retry_count + 1}/{max_retries})"
                )
                await asyncio.sleep(wait_time)
                return await fetch_tickets_page(
                    client,
                    base_url,
                    api_key,
                    start_index,
                    row_count,
                    start_date,
                    end_date,
                    retry_count + 1,
                )
            else:
                logger.error("Server error retries exhausted. Exiting.")
                raise
        else:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise

    except httpx.TimeoutException as e:
        if retry_count < max_retries:
            wait_time = 2 ** (retry_count + 1)
            logger.warning(
                f"Timeout. Waiting {wait_time}s before retry ({retry_count + 1}/{max_retries})"
            )
            await asyncio.sleep(wait_time)
            return await fetch_tickets_page(
                client,
                base_url,
                api_key,
                start_index,
                row_count,
                start_date,
                end_date,
                retry_count + 1,
            )
        else:
            logger.error("Timeout retries exhausted. Exiting.")
            raise


def extract_ticket_data(ticket_json: dict, tenant_id: str) -> Optional[TicketHistory]:
    """
    Extract and transform ticket data from API response to TicketHistory model.

    Args:
        ticket_json: Raw ticket JSON from API response
        tenant_id: Tenant identifier for data isolation

    Returns:
        TicketHistory object or None if extraction fails

    Raises:
        None - logs errors and returns None on failure
    """
    try:
        ticket_id = str(ticket_json.get("id", ""))
        subject = ticket_json.get("subject", "")
        description_text = ticket_json.get("description", "")

        # Combine subject and description for richer context
        description = f"{subject}\n\n{description_text}".strip()

        resolution_obj = ticket_json.get("resolution", {})
        if isinstance(resolution_obj, dict):
            resolution = resolution_obj.get("content", "")
        else:
            resolution = str(resolution_obj) if resolution_obj else ""

        resolved_time = ticket_json.get("resolved_time", {})
        resolved_time_ms = resolved_time.get("value") if isinstance(resolved_time, dict) else None

        if not resolved_time_ms:
            logger.warning(f"Ticket {ticket_id}: Missing resolved_time, skipping")
            return None

        # Convert milliseconds to datetime
        resolved_date = datetime.fromtimestamp(resolved_time_ms / 1000)

        tags = ticket_json.get("tags", [])
        tags_str = (
            ", ".join([t.get("name", "") for t in tags if isinstance(t, dict)])
            if tags
            else ""
        )

        # Validate required fields
        if not ticket_id:
            logger.warning("Ticket missing ID field, skipping")
            return None
        if not description:
            logger.warning(f"Ticket {ticket_id}: Missing description, skipping")
            return None

        # Create TicketHistory object with provenance
        ticket_obj = TicketHistory(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            description=description,
            resolution=resolution,
            resolved_date=resolved_date,
            source="bulk_import",
            # ingested_at will be set by database server_default
        )

        return ticket_obj

    except Exception as e:
        logger.error(
            f"Error extracting ticket data: {e}",
            exc_info=True,
        )
        return None


async def insert_ticket(session, ticket_obj: TicketHistory) -> bool:
    """
    Insert ticket into database with duplicate handling.

    Attempts to insert ticket. If UNIQUE constraint violation occurs (duplicate),
    logs the duplicate and returns False. Other database errors are raised.

    Args:
        session: SQLAlchemy AsyncSession
        ticket_obj: TicketHistory object to insert

    Returns:
        True if inserted successfully, False if duplicate
    """
    try:
        session.add(ticket_obj)
        await session.commit()
        return True
    except IntegrityError as e:
        await session.rollback()
        logger.debug(
            f"Duplicate ticket (tenant_id={ticket_obj.tenant_id}, ticket_id={ticket_obj.ticket_id}), skipping"
        )
        return False
    except DatabaseError as e:
        await session.rollback()
        logger.error(
            f"Database error inserting ticket {ticket_obj.ticket_id}: {e}",
            exc_info=True,
        )
        return False


async def import_tickets(
    tenant_id: str,
    base_url: str,
    api_key: str,
    start_date: datetime,
    end_date: datetime,
) -> int:
    """
    Main import loop with pagination and progress tracking.

    Fetches all tickets from ServiceDesk Plus API within the date range,
    transforms them, and inserts into database. Includes progress logging
    and rate-limit handling.

    Args:
        tenant_id: Tenant identifier
        base_url: ServiceDesk Plus API base URL
        api_key: Zoho API token
        start_date: Start of date range for import
        end_date: End of date range for import

    Returns:
        0 on success, 3 on fatal API error
    """
    start_index = 1
    row_count = 100
    total_imported = 0
    total_skipped = 0
    total_processed = 0
    start_time = datetime.now()

    try:
        async with httpx.AsyncClient() as client:
            async with async_session_maker() as session:
                while True:
                    try:
                        # Fetch page from API
                        tickets, has_more = await fetch_tickets_page(
                            client,
                            base_url,
                            api_key,
                            start_index,
                            row_count,
                            start_date,
                            end_date,
                        )

                        if not tickets:
                            logger.info("No more tickets to fetch")
                            break

                        # Process each ticket
                        for ticket_json in tickets:
                            total_processed += 1

                            ticket_obj = extract_ticket_data(ticket_json, tenant_id)
                            if not ticket_obj:
                                total_skipped += 1
                                continue

                            success = await insert_ticket(session, ticket_obj)
                            if success:
                                total_imported += 1
                            else:
                                total_skipped += 1

                            # Progress logging every 100 tickets
                            if total_processed % 100 == 0:
                                logger.info(
                                    f"Imported {total_imported}/{total_processed} tickets ({100 * total_imported // total_processed}%)"
                                )

                        # Rate limiting: 0.6s delay between requests (100 req/min)
                        await asyncio.sleep(0.6)

                        if not has_more:
                            logger.info("All pages fetched")
                            break

                        start_index += row_count

                    except (httpx.HTTPStatusError, Exception) as e:
                        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (401, 403):
                            logger.error("Authentication error. Cannot continue.")
                            return 3
                        logger.error(f"Error during import: {e}", exc_info=True)
                        return 3

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 3

    # Final summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"Import complete: {total_imported} imported, {total_skipped} skipped, {total_processed} processed in {elapsed:.1f}s"
    )

    return 0


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Bulk import historical tickets from ServiceDesk Plus API"
    )

    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant ID to import tickets for (required)",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days of history to import (default: 90)",
    )

    parser.add_argument(
        "--start-date",
        help="Import from this date (ISO format: YYYY-MM-DD, overrides --days)",
    )

    parser.add_argument(
        "--end-date",
        help="Import until this date (ISO format: YYYY-MM-DD, default: today)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set log level (default: INFO)",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Tuple[bool, str]:
    """
    Validate command-line arguments.

    Args:
        args: Parsed arguments

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not args.tenant_id or not args.tenant_id.strip():
        return False, "tenant_id cannot be empty"

    if args.days and args.days <= 0:
        return False, "days must be positive integer"

    if args.start_date:
        try:
            datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            return False, "start_date must be ISO format (YYYY-MM-DD)"

    if args.end_date:
        try:
            datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            return False, "end_date must be ISO format (YYYY-MM-DD)"

    # Validate date range
    if args.start_date and args.end_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
        end = datetime.strptime(args.end_date, "%Y-%m-%d")
        if start > end:
            return False, "start_date must be before end_date"

    return True, ""


def calculate_date_range(args: argparse.Namespace) -> Tuple[datetime, datetime]:
    """
    Calculate start and end dates for import based on arguments.

    Args:
        args: Parsed arguments

    Returns:
        Tuple of (start_date, end_date)
    """
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    else:
        end_date = datetime.now()

    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    else:
        start_date = end_date - timedelta(days=args.days)

    return start_date, end_date


async def main() -> int:
    """
    Main entry point for import script.

    Returns:
        Exit code (0=success, 1=invalid args, 2=tenant not found, 3=API error)
    """
    # Parse and validate arguments
    args = parse_args()

    # Setup logging
    setup_logger(args.log_level)

    is_valid, error_msg = validate_args(args)
    if not is_valid:
        logger.error(f"Invalid arguments: {error_msg}")
        return 1

    # Fetch tenant configuration
    try:
        base_url, api_key = await fetch_tenant_config(args.tenant_id)
    except DatabaseError:
        return 3

    if not base_url or not api_key:
        logger.error(f"Tenant '{args.tenant_id}' not found in tenant_configs")
        return 2

    logger.info(
        f"Starting import for tenant '{args.tenant_id}' "
        f"from ServiceDesk Plus API"
    )

    # Calculate date range
    start_date, end_date = calculate_date_range(args)
    logger.info(
        f"Import date range: {start_date.date()} to {end_date.date()}"
    )

    # Run import
    return await import_tickets(args.tenant_id, base_url, api_key, start_date, end_date)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
