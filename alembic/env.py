import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from src.database.models import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get database URL from environment variable
    url = os.getenv("AI_AGENTS_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "AI_AGENTS_DATABASE_URL environment variable is not set. "
            "Please set it before running migrations."
        )

    # For local development, replace 'postgres' service name with 'localhost'
    # But only if NOT running inside a Docker container
    import socket
    hostname = socket.gethostname()
    is_in_docker = os.path.exists('/.dockerenv') or hostname.startswith('ai-agents-')

    if "postgres:" in url and not is_in_docker:
        url = url.replace("postgres:5432", "localhost:5433")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using async SQLAlchemy.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get database URL from environment variable
    url = os.getenv("AI_AGENTS_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "AI_AGENTS_DATABASE_URL environment variable is not set. "
            "Please set it before running migrations."
        )

    # For local development, replace 'postgres' service name with 'localhost'
    # But only if NOT running inside a Docker container
    # Check if we're in Docker by looking for the container hostname/environment
    import socket
    hostname = socket.gethostname()
    is_in_docker = os.path.exists('/.dockerenv') or hostname.startswith('ai-agents-')

    if "postgres:" in url and not is_in_docker:
        url = url.replace("postgres:5432", "localhost:5433")

    # Create async engine with pooling disabled for migrations
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        echo=False,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(
            lambda conn: context.configure(
                connection=conn, target_metadata=target_metadata
            )
        )

        await connection.run_sync(lambda conn: context.run_migrations())

    await connectable.dispose()


def invoke_migrations_offline() -> None:
    """Run migrations in offline mode."""
    run_migrations_offline()


def invoke_migrations_online() -> None:
    """Run async migrations in online mode."""
    asyncio.run(run_migrations_online())


if context.is_offline_mode():
    invoke_migrations_offline()
else:
    invoke_migrations_online()
