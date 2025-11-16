"""
Embedding service for generating OpenAI text embeddings with Redis caching.

Provides text-to-vector conversion using OpenAI's text-embedding-3-small model
(1536 dimensions) with Redis caching to reduce API costs and improve performance.

Story 8.15: Memory Configuration UI - Embedding Service (Task 7)
"""

import hashlib
import json
from typing import List, Optional

import openai
import redis.asyncio as redis
from openai import AsyncOpenAI

from src.config import settings
from src.utils.logger import logger


class EmbeddingService:
    """
    Service for generating text embeddings with caching.

    Uses OpenAI text-embedding-3-small model (1536 dimensions) with Redis
    cache to minimize API costs. Handles rate limiting and API failures gracefully.
    """

    # OpenAI embedding model configuration
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    CACHE_TTL = 86400 * 7  # 7 days in seconds
    CACHE_PREFIX = "embedding:"

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        redis_url: Optional[str] = None,
    ):
        """
        Initialize embedding service.

        Args:
            openai_api_key: OpenAI API key (defaults to settings.openai_api_key)
            redis_url: Redis connection URL (defaults to settings.redis_url)

        Raises:
            ValueError: If OpenAI API key not configured
        """
        self.api_key = openai_api_key or getattr(settings, "openai_api_key", None)

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not configured. Set AI_AGENTS_OPENAI_API_KEY environment variable."
            )

        # Initialize OpenAI async client
        self.client = AsyncOpenAI(api_key=self.api_key)

        # Initialize Redis cache (optional)
        self.redis_url = redis_url or getattr(settings, "redis_url", None)
        self.redis_client: Optional[redis.Redis] = None

        if self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
                logger.info("EmbeddingService: Redis cache initialized")
            except Exception as e:
                logger.warning(
                    f"EmbeddingService: Failed to initialize Redis cache: {e}. Proceeding without cache."
                )
                self.redis_client = None
        else:
            logger.warning(
                "EmbeddingService: Redis URL not configured. Proceeding without cache."
            )

    def _cache_key(self, text: str) -> str:
        """
        Generate cache key from text using SHA-256 hash.

        Args:
            text: Input text to hash

        Returns:
            str: Cache key with prefix
        """
        # Reason: Use SHA-256 hash to handle long texts and ensure consistent key length
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.CACHE_PREFIX}{text_hash}"

    async def _get_cached_embedding(self, text: str) -> Optional[str]:
        """
        Retrieve cached embedding from Redis.

        Args:
            text: Input text to lookup

        Returns:
            Optional[str]: Cached embedding as JSON string or None if not found
        """
        if not self.redis_client:
            return None

        try:
            cache_key = self._cache_key(text)
            cached = await self.redis_client.get(cache_key)

            if cached:
                logger.debug(f"EmbeddingService: Cache hit for text hash {cache_key}")
                return cached

        except Exception as e:
            logger.warning(f"EmbeddingService: Redis cache read error: {e}")

        return None

    async def _cache_embedding(self, text: str, embedding: str) -> None:
        """
        Store embedding in Redis cache with TTL.

        Args:
            text: Input text (used for cache key generation)
            embedding: Embedding vector as JSON string
        """
        if not self.redis_client:
            return

        try:
            cache_key = self._cache_key(text)
            await self.redis_client.setex(cache_key, self.CACHE_TTL, embedding)
            logger.debug(
                f"EmbeddingService: Cached embedding for text hash {cache_key}"
            )

        except Exception as e:
            logger.warning(f"EmbeddingService: Redis cache write error: {e}")

    async def generate_embedding(self, text: str) -> Optional[str]:
        """
        Generate embedding for text with caching.

        Uses OpenAI text-embedding-3-small model (1536 dimensions).
        Checks Redis cache first, generates embedding if cache miss,
        then caches result for future requests.

        Args:
            text: Input text to embed (max 8192 tokens for text-embedding-3-small)

        Returns:
            Optional[str]: Embedding vector as JSON string (list of 1536 floats) or None if error

        Raises:
            ValueError: If text is empty or exceeds token limit
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Reason: Truncate very long texts to avoid token limit errors (8192 tokens ~ 32768 chars)
        if len(text) > 32768:
            logger.warning(
                f"EmbeddingService: Text truncated from {len(text)} to 32768 chars"
            )
            text = text[:32768]

        # Check cache first
        cached_embedding = await self._get_cached_embedding(text)
        if cached_embedding:
            return cached_embedding

        # Generate embedding via OpenAI API
        try:
            response = await self.client.embeddings.create(
                model=self.EMBEDDING_MODEL, input=text, dimensions=self.EMBEDDING_DIMENSIONS
            )

            # Extract embedding vector (list of floats)
            embedding_vector = response.data[0].embedding

            # Reason: Serialize to JSON string for PostgreSQL TEXT storage
            embedding_json = json.dumps(embedding_vector)

            # Cache for future requests
            await self._cache_embedding(text, embedding_json)

            logger.info(
                f"EmbeddingService: Generated embedding ({self.EMBEDDING_DIMENSIONS} dims) for text (length: {len(text)})"
            )

            return embedding_json

        except openai.RateLimitError as e:
            logger.error(
                f"EmbeddingService: OpenAI rate limit exceeded: {e}. Consider implementing retry with exponential backoff."
            )
            return None

        except openai.APIError as e:
            logger.error(f"EmbeddingService: OpenAI API error: {e}")
            return None

        except Exception as e:
            logger.error(
                f"EmbeddingService: Unexpected error generating embedding: {e}"
            )
            return None

    async def batch_embeddings(self, texts: List[str]) -> List[Optional[str]]:
        """
        Generate embeddings for multiple texts in batch.

        Processes texts individually to maintain cache effectiveness
        (OpenAI batch API doesn't reduce costs significantly for embeddings).

        Args:
            texts: List of input texts

        Returns:
            List[Optional[str]]: List of embedding JSON strings (None for errors)

        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        logger.info(f"EmbeddingService: Batch generating embeddings for {len(texts)} texts")

        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)

        success_count = sum(1 for e in embeddings if e is not None)
        logger.info(
            f"EmbeddingService: Batch complete - {success_count}/{len(texts)} successful"
        )

        return embeddings

    async def close(self) -> None:
        """
        Close Redis connection gracefully.

        Should be called on application shutdown.
        """
        if self.redis_client:
            await self.redis_client.close()
            logger.info("EmbeddingService: Redis connection closed")
