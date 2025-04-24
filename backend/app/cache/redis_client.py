import json
import logging
from typing import Any, Dict, List, Optional, Union
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Client for Redis cache operations."""
    
    def __init__(self):
        """Initialize Redis connection."""
        # Construct Redis URL with authentication if provided
        redis_url = f"redis://"
        if settings.REDIS_USERNAME and settings.REDIS_PASSWORD:
            redis_url += f"{settings.REDIS_USERNAME}:{settings.REDIS_PASSWORD}@"
        redis_url += f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        
        try:
            self.redis = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Redis client initialized with host {settings.REDIS_HOST}")
        except Exception as e:
            logger.error(f"Error initializing Redis client: {str(e)}")
            self.redis = None
    
    async def get(self, key: str) -> Optional[str]:
        """Get a raw value from Redis"""
        try:
            if not self.redis:
                logger.error("Redis client not initialized")
                return None
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Error getting value from Redis for key {key}: {str(e)}")
            return None

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set a raw value in Redis"""
        try:
            if not self.redis:
                logger.error("Redis client not initialized")
                return False
            result = await self.redis.set(key, value, ex=expire)
            return result is True or result == "OK"
        except Exception as e:
            logger.error(f"Error setting value in Redis for key {key}: {str(e)}")
            return False

    async def get_value(self, key: str) -> Optional[Any]:
        """Get a value from Redis with JSON deserialization."""
        try:
            value = await self.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error(f"Error getting value from Redis for key {key}: {str(e)}")
            return None
    
    async def set_value(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Set a value in Redis with JSON serialization."""
        try:
            serialized = json.dumps(value)
            return await self.set(key, serialized, expire=expire)
        except Exception as e:
            logger.error(f"Error setting value in Redis for key {key}: {str(e)}")
            return False
    
    async def delete_value(self, key: str) -> bool:
        """Delete a value from Redis."""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting value from Redis for key {key}: {str(e)}")
            return False
    
    async def get_cached_protein_data(self, protein_id: str) -> Optional[Dict[str, Any]]:
        """Get cached protein data."""
        return await self.get_value(f"protein:{protein_id}")
    
    async def cache_protein_data(
        self,
        protein_id: str,
        data: Dict[str, Any],
        expire: int = 86400  # 24 hours
    ) -> bool:
        """Cache protein data."""
        return await self.set_value(f"protein:{protein_id}", data, expire=expire)
    
    async def get_cached_structure_data(self, protein_id: str) -> Optional[Dict[str, Any]]:
        """Get cached protein structure data."""
        return await self.get_value(f"structure:{protein_id}")
    
    async def cache_structure_data(
        self,
        protein_id: str,
        data: Dict[str, Any],
        expire: int = 604800  # 1 week
    ) -> bool:
        """Cache protein structure data."""
        return await self.set_value(f"structure:{protein_id}", data, expire=expire)
    
    async def store_chat_message(
        self,
        session_id: str,
        message: Dict[str, Any],
        max_history: int = 50
    ) -> bool:
        """Store a chat message in the history."""
        try:
            key = f"chat:history:{session_id}"
            
            # Add message to list with timestamp
            message_json = json.dumps(message)
            await self.redis.lpush(key, message_json)
            
            # Trim list to max_history items
            await self.redis.ltrim(key, 0, max_history - 1)
            
            # Set expiry on the chat history (1 week)
            await self.redis.expire(key, 604800)
            
            return True
        except Exception as e:
            logger.error(f"Error storing chat message for session {session_id}: {str(e)}")
            return False
    
    async def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat message history."""
        try:
            key = f"chat:history:{session_id}"
            messages_json = await self.redis.lrange(key, 0, -1)
            
            # Parse messages from JSON
            messages = []
            for msg_json in messages_json:
                try:
                    messages.append(json.loads(msg_json))
                except:
                    logger.error(f"Error parsing chat message: {msg_json}")
            
            # Return in chronological order
            return list(reversed(messages))
        except Exception as e:
            logger.error(f"Error getting chat history for session {session_id}: {str(e)}")
            return []

    async def test_connection(self) -> bool:
        """Test Redis connection
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            return await self.redis.ping()
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            return False