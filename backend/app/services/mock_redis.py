"""Mock Redis for development without actual Redis server"""
import json
from typing import Optional, Dict
from datetime import datetime, timedelta

class MockRedis:
    def __init__(self):
        self.store: Dict[str, tuple] = {}  # key: (value, expiry)
    
    async def setex(self, key: str, ttl: int, value: str):
        """Set key with expiration"""
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self.store[key] = (value, expiry)
    
    async def get(self, key: str) -> Optional[str]:
        """Get key value"""
        if key not in self.store:
            return None
        
        value, expiry = self.store[key]
        if datetime.utcnow() > expiry:
            del self.store[key]
            return None
        
        return value
    
    async def delete(self, key: str):
        """Delete key"""
        if key in self.store:
            del self.store[key]
    
    async def ping(self):
        """Health check"""
        return True

mock_redis_client = MockRedis()
