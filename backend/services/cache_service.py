import redis
import json
import os
from typing import Optional, Dict, Any
import hashlib
from datetime import date, datetime
from decimal import Decimal
import time

# Memory-based cache (alternative to Redis)
memory_cache = {}
MEMORY_CACHE_MAX_SIZE = 100  # Maximum number of cache items

# Redis connection settings
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None
redis_available = False

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Connection test
    redis_client.ping()
    redis_available = True
    print("Redis connection successful")
except Exception as e:
    print(f"Redis not available, using memory cache instead: {e}")
    redis_available = False
    redis_client = None

# Cache TTL (1 hour)
CACHE_TTL = 3600

class DateTimeEncoder(json.JSONEncoder):
    """Encoder to serialize Date, DateTime, Decimal objects to JSON"""
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def generate_search_key(params: dict) -> str:
    """Generate a unique key based on search parameters"""
    # Generate consistent keys with sorted parameters
    sorted_params = json.dumps(params, sort_keys=True, cls=DateTimeEncoder)
    return f"search:{hashlib.md5(sorted_params.encode()).hexdigest()}"

def _clean_memory_cache():
    """Clean up expired items in the memory cache"""
    current_time = time.time()
    expired_keys = []
    
    for key, value in memory_cache.items():
        # Only process entries that are tuples (search cache)
        if isinstance(value, tuple) and len(value) == 2:
            data, timestamp = value
            # Ensure timestamp is a float
            try:
                timestamp = float(timestamp)
            except (TypeError, ValueError):
                continue  # skip if timestamp is not a valid float
                
            if current_time - timestamp > CACHE_TTL:
                expired_keys.append(key)
    
    for key in expired_keys:
        del memory_cache[key]
    
    # Check size limit
    if len(memory_cache) > MEMORY_CACHE_MAX_SIZE:
        # Delete the oldest items
        sorted_items = sorted(memory_cache.items(), key=lambda x: x[1][1])
        items_to_remove = len(memory_cache) - MEMORY_CACHE_MAX_SIZE
        for i in range(items_to_remove):
            key_to_remove = sorted_items[i][0]
            del memory_cache[key_to_remove]

def cache_search_results(key: str, results: Dict[str, Any]) -> None:
    """Cache search results"""
    if redis_available and redis_client:
        # Save to Redis if available
        try:
            redis_client.setex(key, CACHE_TTL, json.dumps(results, cls=DateTimeEncoder))
            print(f"Cached to Redis: {key}")
            return
        except Exception as e:
            print(f"Redis cache error, falling back to memory: {e}")
    
    # Use memory cache if Redis is not available
    try:
        _clean_memory_cache()  # Clean up expired items
        memory_cache[key] = (results, time.time())
        print(f"Cached to memory: {key} (Total: {len(memory_cache)} items)")
    except Exception as e:
        print(f"Memory cache error: {e}")

def get_cached_results(key: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached search results"""
    if redis_available and redis_client:
        # Attempt from Redis first
        try:
            data = redis_client.get(key)
            if data:
                print(f"Retrieved from Redis: {key}")
                return json.loads(data)
        except Exception as e:
            print(f"Redis retrieve error, trying memory cache: {e}")
    
    # Attempt from memory cache
    try:
        if key in memory_cache:
            data, timestamp = memory_cache[key]
            current_time = time.time()
            
            # Check TTL
            if current_time - timestamp <= CACHE_TTL:
                print(f"Retrieved from memory: {key}")
                return data
            else:
                # Delete expired data
                del memory_cache[key]
                print(f"Expired data removed from memory: {key}")
        
        print(f"No cached data found: {key}")
        return None
    except Exception as e:
        print(f"Memory cache retrieve error: {e}")
        return None

def test_redis_connection() -> bool:
    """Test Redis connection status"""
    if not redis_client:
        print("Redis client not initialized")
        return False
    
    try:
        redis_client.ping()
        print("Redis connection successful")
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False

def clear_cache_pattern(pattern: str) -> int:
    """Delete cache keys matching the pattern"""
    deleted_count = 0
    
    # Attempt to delete from Redis
    if redis_available and redis_client:
        try:
            keys = redis_client.keys(pattern)
            if keys:
                deleted_count += redis_client.delete(*keys)
                print(f"Deleted {deleted_count} keys from Redis")
        except Exception as e:
            print(f"Redis cache clear error: {e}")
    
    # Delete from memory cache
    try:
        # Simple implementation for pattern matching (*)
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            keys_to_delete = [key for key in memory_cache.keys() if key.startswith(prefix)]
        else:
            keys_to_delete = [key for key in memory_cache.keys() if key == pattern]
        
        for key in keys_to_delete:
            del memory_cache[key]
            deleted_count += 1
        
        print(f"Deleted {len(keys_to_delete)} keys from memory cache")
    except Exception as e:
        print(f"Memory cache clear error: {e}")
    
    return deleted_count

def get_cache_info() -> Dict[str, Any]:
    """Return cache status information"""
    info = {
        "redis_available": redis_available,
        "memory_cache_size": len(memory_cache),
        "memory_cache_max_size": MEMORY_CACHE_MAX_SIZE,
        "cache_ttl": CACHE_TTL
    }
    
    if redis_available and redis_client:
        try:
            redis_info = redis_client.info()
            info["redis_used_memory"] = redis_info.get("used_memory_human", "Unknown")
            info["redis_connected_clients"] = redis_info.get("connected_clients", 0)
        except Exception as e:
            info["redis_error"] = str(e)
    
    return info

def parse_date_strings(data: Dict[str, Any], date_fields: list = None) -> Dict[str, Any]:
    """Convert date strings in cached data back to date objects"""
    if not date_fields:
        date_fields = ['publication_date', 'created_at', 'updated_at', 'start_date', 'end_date']
    
    def convert_dates(obj):
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key in date_fields and isinstance(value, str):
                    try:
                        # Convert ISO date strings to date/datetime objects
                        if 'T' in value:  # datetime
                            result[key] = datetime.fromisoformat(value)
                        else:  # date
                            result[key] = datetime.fromisoformat(value).date()
                    except ValueError:
                        result[key] = value  # Keep original if conversion fails
                else:
                    result[key] = convert_dates(value) if isinstance(value, (dict, list)) else value
            return result
        elif isinstance(obj, list):
            return [convert_dates(item) for item in obj]
        else:
            return obj
    
    return convert_dates(data)

class CacheService:
    """Cache service class"""
    
    def cache_insights(self, insights_key: str, insights_data: Dict[str, Any], ttl: int = CACHE_TTL) -> bool:
        """Cache insights data"""
        try:
            serialized_data = json.dumps(insights_data, cls=DateTimeEncoder)
            
            if redis_available:
                redis_client.setex(f"insights:{insights_key}", ttl, serialized_data)
            else:
                _clean_memory_cache()
                memory_cache[f"insights:{insights_key}"] = {
                    'data': serialized_data,
                    'expiry': time.time() + ttl
                }
            
            return True
        except Exception as e:
            print(f"Failed to cache insights: {e}")
            return False
    
    def get_insights(self, insights_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached insights"""
        try:
            cache_key = f"insights:{insights_key}"
            
            if redis_available:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            else:
                if cache_key in memory_cache:
                    cache_entry = memory_cache[cache_key]
                    if time.time() < cache_entry['expiry']:
                        return json.loads(cache_entry['data'])
                    else:
                        del memory_cache[cache_key]
            
            return None
        except Exception as e:
            print(f"Failed to get insights from cache: {e}")
            return None
    
    def invalidate_insights(self, search_key: str) -> bool:
        """Invalidate all insights for a search key"""
        try:
            if redis_available:
                # Find and delete all insights keys for this search
                pattern = f"insights:insights_{search_key}_*"
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
            else:
                # Remove from memory cache
                keys_to_remove = [key for key in memory_cache.keys() 
                                if key.startswith(f"insights:insights_{search_key}_")]
                for key in keys_to_remove:
                    del memory_cache[key]
            
            return True
        except Exception as e:
            print(f"Failed to invalidate insights: {e}")
            return False
    
    def get_search_results(self, search_key: str, page: int = 1) -> Optional[Dict[str, Any]]:
        """Get cached search results for a specific page"""
        try:
            # Try different cache key formats
            cache_keys = [
                f"{search_key}_page_{page}",  # Original format
                f"{search_key}",              # Direct search key format
                search_key                    # Just the key itself
            ]
            
            for cache_key in cache_keys:
                if redis_available:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        data = json.loads(cached_data)
                        # If this is the main search data, extract results for the page
                        if 'all_results' in data:
                            # Calculate page start and end indices
                            page_size = data.get('search_params', {}).get('pageSize', 10)
                            start_idx = (page - 1) * page_size
                            end_idx = start_idx + page_size
                            
                            all_results = data['all_results']
                            page_results = all_results[start_idx:end_idx]
                            
                            return {
                                'results': page_results,
                                'total': len(all_results),
                                'page': page,
                                'search_params': data.get('search_params', {}),
                                'filter_stats': data.get('filter_stats', {})
                            }
                        else:
                            return data
                else:
                    if cache_key in memory_cache:
                        cache_entry = memory_cache[cache_key]
                        if isinstance(cache_entry, tuple) and len(cache_entry) >= 2:
                            # Old format: (data, timestamp)
                            data, timestamp = cache_entry
                            if time.time() - timestamp < CACHE_TTL:
                                # Process the same way as Redis
                                if isinstance(data, dict) and 'all_results' in data:
                                    page_size = data.get('search_params', {}).get('pageSize', 10)
                                    start_idx = (page - 1) * page_size
                                    end_idx = start_idx + page_size
                                    
                                    all_results = data['all_results']
                                    page_results = all_results[start_idx:end_idx]
                                    
                                    return {
                                        'results': page_results,
                                        'total': len(all_results),
                                        'page': page,
                                        'search_params': data.get('search_params', {}),
                                        'filter_stats': data.get('filter_stats', {})
                                    }
                                else:
                                    return data
                        elif isinstance(cache_entry, dict) and 'expiry' in cache_entry:
                            # New format: {'data': ..., 'expiry': ...}
                            if time.time() < cache_entry['expiry']:
                                data = json.loads(cache_entry['data']) if isinstance(cache_entry['data'], str) else cache_entry['data']
                                # Process the same way
                                if isinstance(data, dict) and 'all_results' in data:
                                    page_size = data.get('search_params', {}).get('pageSize', 10)
                                    start_idx = (page - 1) * page_size
                                    end_idx = start_idx + page_size
                                    
                                    all_results = data['all_results']
                                    page_results = all_results[start_idx:end_idx]
                                    
                                    return {
                                        'results': page_results,
                                        'total': len(all_results),
                                        'page': page,
                                        'search_params': data.get('search_params', {}),
                                        'filter_stats': data.get('filter_stats', {})
                                    }
                                else:
                                    return data
                            else:
                                del memory_cache[cache_key]
            
            return None
        except Exception as e:
            print(f"Failed to get search results from cache: {e}")
            return None