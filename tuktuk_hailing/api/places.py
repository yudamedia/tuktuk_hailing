# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cstr
import re
import math
import json

@frappe.whitelist(allow_guest=True)
def search_places(query, limit=5, user_lat=None, user_lng=None, bounds=None):
    """
    Search for places in local database
    Returns matches based on place name, aliases, and category
    Falls back to Nominatim if no local results found
    
    Args:
        query: Search term
        limit: Maximum results to return
        user_lat: User's latitude (for distance sorting)
        user_lng: User's longitude (for distance sorting)
        bounds: Geographic bounds dict with min_lat, max_lat, min_lng, max_lng
    """
    
    # Rate limiting: max 30 requests per minute per IP
    try:
        from frappe.rate_limiter import rate_limit
        rate_limit(limit=30, seconds=60)
    except:
        pass  # Graceful degradation if rate limiter not available
    
    if not query or len(query.strip()) < 2:
        return {"source": "local", "results": []}
    
    query = query.strip()
    
    # Parse bounds if provided as string
    if bounds and isinstance(bounds, str):
        try:
            bounds = frappe.parse_json(bounds)
        except:
            bounds = None
    
    # Search in local database
    local_results = search_local_places(
        query, 
        limit, 
        user_lat=user_lat, 
        user_lng=user_lng,
        bounds=bounds
    )
    
    if local_results:
        return {
            "source": "local",
            "results": local_results
        }
    
    # No local results found
    return {
        "source": "none",
        "results": [],
        "message": "No local places found. Use Nominatim fallback."
    }

def search_local_places(query, limit=5, user_lat=None, user_lng=None, bounds=None):
    """
    Search local places database with fuzzy matching
    
    Args:
        query: Search term
        limit: Maximum results
        user_lat: User's latitude for distance sorting
        user_lng: User's longitude for distance sorting
        bounds: Geographic bounds for filtering
    """
    
    # Escape special characters for SQL LIKE
    query_escaped = query.replace('%', '\\%').replace('_', '\\_')
    
    # Build bounds filter
    bounds_filter = ""
    params = {'query': query_escaped, 'limit': int(limit)}
    
    if bounds and all(k in bounds for k in ['min_lat', 'max_lat', 'min_lng', 'max_lng']):
        bounds_filter = """
            AND latitude BETWEEN %(min_lat)s AND %(max_lat)s
            AND longitude BETWEEN %(min_lng)s AND %(max_lng)s
        """
        params.update({
            'min_lat': float(bounds['min_lat']),
            'max_lat': float(bounds['max_lat']),
            'min_lng': float(bounds['min_lng']),
            'max_lng': float(bounds['max_lng'])
        })
    
    # Build distance calculation if user coordinates provided
    distance_calc = ""
    if user_lat and user_lng:
        try:
            lat = float(user_lat)
            lng = float(user_lng)
            distance_calc = f"""
                , (6371 * acos(
                    cos(radians({lat})) 
                    * cos(radians(latitude)) 
                    * cos(radians(longitude) - radians({lng})) 
                    + sin(radians({lat})) 
                    * sin(radians(latitude))
                )) AS distance_km
            """
            order_by = "match_priority ASC, distance_km ASC"
        except (ValueError, TypeError):
            order_by = "match_priority ASC, place_name ASC"
    else:
        order_by = "match_priority ASC, place_name ASC"
    
    # Search strategy:
    # 1. Exact match on place_name
    # 2. Starts with match on place_name
    # 3. Contains match on place_name
    # 4. Match in aliases
    # 5. Match in category
    
    sql = f"""
        SELECT 
            place_name,
            category,
            latitude,
            longitude,
            aliases,
            description
            {distance_calc},
            CASE
                WHEN LOWER(place_name) = LOWER(%(query)s) THEN 1
                WHEN LOWER(place_name) LIKE LOWER(CONCAT(%(query)s, '%%')) THEN 2
                WHEN LOWER(place_name) LIKE LOWER(CONCAT('%%', %(query)s, '%%')) THEN 3
                WHEN LOWER(IFNULL(aliases, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%')) THEN 4
                WHEN LOWER(IFNULL(category, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%')) THEN 5
                ELSE 6
            END as match_priority
        FROM `tabHailing Place`
        WHERE 
            is_active = 1
            {bounds_filter}
            AND (
                LOWER(place_name) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
                OR LOWER(IFNULL(aliases, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
                OR LOWER(IFNULL(category, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
            )
        ORDER BY {order_by}
        LIMIT %(limit)s
    """
    
    results = frappe.db.sql(sql, params, as_dict=True)
    
    # Format results for frontend
    formatted_results = []
    for result in results:
        formatted_result = {
            'place_name': result.place_name,
            'display_name': format_display_name(result),
            'lat': result.latitude,
            'lon': result.longitude,
            'category': result.category,
            'source': 'local'
        }
        
        # Add distance if calculated
        if hasattr(result, 'distance_km') and result.distance_km is not None:
            formatted_result['distance_km'] = round(result.distance_km, 2)
        
        formatted_results.append(formatted_result)
    
    return formatted_results

def format_display_name(result):
    """
    Format a display name similar to Nominatim's display_name
    """
    parts = [result.place_name]
    
    if result.category:
        parts.append(result.category)
    
    parts.append("Diani Beach, Kenya")
    
    return ", ".join(parts)

@frappe.whitelist(allow_guest=True)
def get_place_suggestions(query, limit=10):
    """
    Get autocomplete suggestions for place names with caching
    Used for dropdown suggestions as user types
    
    Args:
        query: Search term
        limit: Maximum suggestions to return
    """
    
    # Rate limiting
    try:
        from frappe.rate_limiter import rate_limit
        rate_limit(limit=50, seconds=60)  # Higher limit for autocomplete
    except:
        pass
    
    if not query or len(query.strip()) < 2:
        return []
    
    query = query.strip()
    query_lower = query.lower()
    
    # Use frappe cache for popular queries (5 minute cache)
    cache_key = f"place_suggestions:{query_lower}:{limit}"
    cached = frappe.cache().get(cache_key)
    
    if cached:
        # Deserialize from JSON string
        try:
            return json.loads(cached)
        except:
            pass  # If cache is corrupted, continue to fetch fresh data
    
    query_escaped = query.replace('%', '\\%').replace('_', '\\_')
    
    sql = """
        SELECT 
            place_name,
            category,
            latitude,
            longitude,
            CASE
                WHEN LOWER(place_name) LIKE LOWER(CONCAT(%(query)s, '%%')) THEN 1
                WHEN LOWER(place_name) LIKE LOWER(CONCAT('%%', %(query)s, '%%')) THEN 2
                WHEN LOWER(IFNULL(aliases, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%')) THEN 3
                ELSE 4
            END as match_priority
        FROM `tabHailing Place`
        WHERE 
            is_active = 1
            AND (
                LOWER(place_name) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
                OR LOWER(IFNULL(aliases, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
            )
        ORDER BY match_priority ASC, place_name ASC
        LIMIT %(limit)s
    """
    
    results = frappe.db.sql(sql, {
        'query': query_escaped,
        'limit': int(limit)
    }, as_dict=True)
    
    suggestions = []
    for result in results:
        suggestions.append({
            'label': format_display_name(result),
            'value': result.place_name,
            'lat': result.latitude,
            'lon': result.longitude,
            'category': result.category
        })
    
    # Cache the results for 5 minutes (300 seconds)
    # Serialize to JSON string before caching
    try:
        frappe.cache().setex(cache_key, 300, json.dumps(suggestions))
    except Exception as e:
        # If caching fails, log it but continue
        frappe.log_error(f"Cache error: {str(e)}", "Place Suggestions Cache")
    
    return suggestions