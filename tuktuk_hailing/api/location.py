# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, get_datetime, add_to_date
from datetime import datetime, timedelta

@frappe.whitelist()
def update_driver_location(latitude, longitude, driver_id=None, accuracy=None, heading=None, speed=None, hailing_status="Available"):
    """
    Update driver's current location
    Called every N seconds by driver's phone

    driver_id: Optional - if not provided, uses current authenticated user
    """

    # If driver_id not provided, get from the authenticated user (mobile app context)
    if not driver_id:
        driver_id = frappe.db.get_value("TukTuk Driver", {"user_account": frappe.session.user}, "name")

        if not driver_id:
            frappe.throw("No driver found for current user")

    # Convert numeric parameters to proper types (they come as strings from API)
    latitude = float(latitude)
    longitude = float(longitude)
    
    # Handle optional parameters that might be None or empty strings
    if accuracy is not None and accuracy != '':
        accuracy = float(accuracy)
    else:
        accuracy = None
        
    if heading is not None and heading != '':
        heading = float(heading)
    else:
        heading = None
        
    if speed is not None and speed != '':
        speed = float(speed)
    else:
        speed = None
    
    # Get or create latest location record for driver
    existing = frappe.db.get_value("Driver Location",
        filters={"driver": driver_id},
        fieldname="name",
        order_by="timestamp desc"
    )
    
    if existing:
        # Update existing record
        loc = frappe.get_doc("Driver Location", existing)
        loc.latitude = latitude
        loc.longitude = longitude
        loc.accuracy_meters = accuracy
        loc.heading = heading
        loc.speed_kmh = speed
        loc.hailing_status = hailing_status
        loc.timestamp = now()
        loc.is_stale = 0
        loc.save(ignore_permissions=True)
    else:
        # Create new location record
        driver = frappe.get_doc("TukTuk Driver", driver_id)
        
        loc = frappe.get_doc({
            "doctype": "Driver Location",
            "driver": driver_id,
            "vehicle": driver.assigned_tuktuk,
            "latitude": latitude,
            "longitude": longitude,
            "accuracy_meters": accuracy,
            "heading": heading,
            "speed_kmh": speed,
            "hailing_status": hailing_status,
            "timestamp": now(),
            "is_stale": 0
        })
        loc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    
    # Broadcast location update to clients watching this driver
    frappe.publish_realtime(
        event="driver_location_update",
        message={
            "driver": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "status": hailing_status,
            "timestamp": now()
        },
        doctype="Driver Location"
    )
    
    return {"success": True, "timestamp": loc.timestamp}

@frappe.whitelist(allow_guest=True)
def get_available_drivers(customer_lat=None, customer_lng=None, max_distance_km=None):
    """
    Get list of available drivers and their locations
    Optionally filter by distance from customer location
    """
    
    settings = frappe.get_single("Hailing Settings")
    stale_threshold = settings.stale_location_threshold or 60
    
    # Get cutoff time for stale locations
    cutoff_time = add_to_date(now(), seconds=-stale_threshold)
    
    # Query available drivers with recent location updates
    drivers = frappe.db.sql("""
        SELECT
            dl.driver,
            dl.vehicle,
            dl.latitude,
            dl.longitude,
            dl.heading,
            dl.speed_kmh,
            dl.timestamp,
            d.driver_name,
            d.mpesa_number,
            d.driver_photo
        FROM `tabDriver Location` dl
        INNER JOIN `tabTukTuk Driver` d ON dl.driver = d.name
        WHERE
            dl.hailing_status = 'Available'
            AND dl.timestamp >= %s
            AND dl.is_stale = 0
        ORDER BY dl.timestamp DESC
    """, (cutoff_time,), as_dict=True)
    
    # If customer location provided, calculate distances and filter
    if customer_lat and customer_lng and max_distance_km:
        import math
        
        # Convert parameters to correct types (they come as strings from API)
        customer_lat = float(customer_lat)
        customer_lng = float(customer_lng)
        max_distance_km = float(max_distance_km)
        
        filtered_drivers = []
        for driver in drivers:
            distance = calculate_distance(
                customer_lat, customer_lng,
                driver.latitude, driver.longitude
            )
            
            if distance <= max_distance_km:
                driver['distance_km'] = round(distance, 2)
                # Add privacy radius offset
                driver['display_latitude'] = driver.latitude + (0.0005 * (1 if distance % 2 == 0 else -1))
                driver['display_longitude'] = driver.longitude + (0.0005 * (1 if int(distance * 10) % 2 == 0 else -1))
                filtered_drivers.append(driver)
        
        # Sort by distance
        filtered_drivers.sort(key=lambda x: x['distance_km'])
        return filtered_drivers
    
    # Apply privacy radius to all drivers
    for driver in drivers:
        driver['display_latitude'] = driver.latitude + 0.0005
        driver['display_longitude'] = driver.longitude + 0.0005
    
    return drivers

@frappe.whitelist()
def set_driver_availability(driver_id=None, available=True):
    """
    Toggle driver's availability for hailing
    available=True: Set to "Available"
    available=False: Set to "Offline"

    driver_id: Optional - if not provided, uses current authenticated user
    """

    # If driver_id not provided, get from the authenticated user (mobile app context)
    if not driver_id:
        driver_id = frappe.db.get_value("TukTuk Driver", {"user_account": frappe.session.user}, "name")

        if not driver_id:
            frappe.throw("No driver found for current user")

    # Convert available to boolean (it comes as string/int from API)
    if isinstance(available, str):
        available = available.lower() in ['true', '1', 'yes']
    else:
        available = bool(int(available)) if available not in [True, False] else available
    
    # Update driver's hailing status in TukTuk Driver doctype
    driver = frappe.get_doc("TukTuk Driver", driver_id)
    
    if available:
        if not driver.assigned_tuktuk:
            frappe.throw("Cannot go available without an assigned tuktuk")
        driver.db_set("hailing_status", "Available", update_modified=False)
    else:
        driver.db_set("hailing_status", "Offline", update_modified=False)
    
    # Update location record
    existing = frappe.db.get_value("Driver Location",
        filters={"driver": driver_id},
        fieldname="name",
        order_by="timestamp desc"
    )
    
    if existing:
        loc = frappe.get_doc("Driver Location", existing)
        loc.hailing_status = "Available" if available else "Offline"
        loc.save(ignore_permissions=True)
        frappe.db.commit()
    
    return {
        "success": True,
        "status": "Available" if available else "Offline"
    }

@frappe.whitelist()
def get_all_driver_locations():
    """
    Get all driver locations with their current status (not filtered by availability)
    Used by Fleet Location Map to show all drivers regardless of status

    Returns:
    - drivers_with_locations: Drivers with recent GPS updates (shown on map)
    - all_driver_counts: Status counts for ALL drivers with assigned tuktuks
    """

    settings = frappe.get_single("Hailing Settings")
    stale_threshold = settings.stale_location_threshold or 60

    # Get cutoff time for stale locations
    cutoff_time = add_to_date(now(), seconds=-stale_threshold)

    # Query drivers with recent location updates (these will be shown on the map)
    drivers_with_locations = frappe.db.sql("""
        SELECT
            dl.driver,
            dl.vehicle,
            dl.latitude,
            dl.longitude,
            dl.heading,
            dl.speed_kmh,
            dl.hailing_status,
            dl.timestamp,
            d.driver_name,
            d.mpesa_number,
            d.driver_photo
        FROM `tabDriver Location` dl
        INNER JOIN `tabTukTuk Driver` d ON dl.driver = d.name
        WHERE
            dl.timestamp >= %s
            AND dl.is_stale = 0
        ORDER BY dl.timestamp DESC
    """, (cutoff_time,), as_dict=True)

    # Apply privacy radius to drivers with locations
    for driver in drivers_with_locations:
        driver['display_latitude'] = driver.latitude + 0.0005
        driver['display_longitude'] = driver.longitude + 0.0005

    # Get ALL drivers with assigned tuktuks and their status for accurate counts
    all_drivers = frappe.db.sql("""
        SELECT
            d.name as driver,
            d.hailing_status,
            dl.timestamp
        FROM `tabTukTuk Driver` d
        LEFT JOIN `tabDriver Location` dl ON dl.driver = d.name
        WHERE
            d.assigned_tuktuk IS NOT NULL
            AND d.assigned_tuktuk != ''
        ORDER BY dl.timestamp DESC
    """, as_dict=True)

    # Count drivers by status
    # For drivers without recent location updates, use their hailing_status from TukTuk Driver doctype
    # For drivers with recent updates, use the status from Driver Location (already in drivers_with_locations)
    status_counts = {
        'Available': 0,
        'En Route': 0,
        'Busy': 0,
        'Offline': 0
    }

    # Create a set of drivers with active locations
    active_driver_ids = {d['driver'] for d in drivers_with_locations}

    for driver in all_drivers:
        # If driver has recent location update, they're already counted in drivers_with_locations
        if driver['driver'] in active_driver_ids:
            # Get status from the location data
            for d in drivers_with_locations:
                if d['driver'] == driver['driver']:
                    status = d['hailing_status'] or 'Offline'
                    status_counts[status] = status_counts.get(status, 0) + 1
                    break
        else:
            # Driver doesn't have recent location, use their doctype status or mark as Offline
            status = driver['hailing_status'] or 'Offline'
            # If they claim to be Available/En Route/Busy but have no recent location, consider them Offline
            if status != 'Offline' and (not driver['timestamp'] or driver['timestamp'] < get_datetime(cutoff_time)):
                status = 'Offline'
            status_counts[status] = status_counts.get(status, 0) + 1

    return {
        'drivers': drivers_with_locations,
        'counts': status_counts
    }

@frappe.whitelist()
def get_driver_location(driver_id):
    """Get latest location for a specific driver"""

    location = frappe.db.get_value("Driver Location",
        filters={"driver": driver_id},
        fieldname=["latitude", "longitude", "hailing_status", "timestamp", "heading", "speed_kmh"],
        order_by="timestamp desc",
        as_dict=True
    )

    if not location:
        return None

    # Check if stale
    settings = frappe.get_single("Hailing Settings")
    stale_threshold = settings.stale_location_threshold or 60
    cutoff_time = add_to_date(now(), seconds=-stale_threshold)

    if get_datetime(location.timestamp) < get_datetime(cutoff_time):
        location['is_stale'] = True
    else:
        location['is_stale'] = False

    return location

def cleanup_stale_locations():
    """
    Scheduled task to mark old locations as stale
    Runs every 5 minutes via scheduler
    """
    
    settings = frappe.get_single("Hailing Settings")
    stale_threshold = settings.stale_location_threshold or 60
    cutoff_time = add_to_date(now(), seconds=-stale_threshold)
    
    # Mark stale locations
    frappe.db.sql("""
        UPDATE `tabDriver Location`
        SET is_stale = 1
        WHERE timestamp < %s AND is_stale = 0
    """, (cutoff_time,))
    
    frappe.db.commit()
    
    # Optionally delete very old location records (older than 24 hours)
    delete_cutoff = add_to_date(now(), hours=-24)
    frappe.db.sql("""
        DELETE FROM `tabDriver Location`
        WHERE timestamp < %s
    """, (delete_cutoff,))
    
    frappe.db.commit()

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points using Haversine formula"""
    import math
    
    R = 6371  # Earth's radius in km
    
    lat1, lon1 = math.radians(lat1), math.radians(lng1)
    lat2, lon2 = math.radians(lat2), math.radians(lng2)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return distance

@frappe.whitelist()
def get_driver_route_to_customer(driver_id, customer_lat, customer_lng):
    """
    Get routing information from driver's current location to customer
    Uses configured routing API (OSRM, MapBox, etc.)
    """
    
    # Convert coordinates to float (they come as strings from API)
    customer_lat = float(customer_lat)
    customer_lng = float(customer_lng)
    
    # Get driver's current location
    driver_location = get_driver_location(driver_id)
    
    if not driver_location or driver_location.get('is_stale'):
        return {"error": "Driver location not available"}
    
    # Get routing from routing API
    settings = frappe.get_single("Hailing Settings")
    
    if settings.routing_api_provider == "OSRM":
        return get_osrm_route(
            driver_location.latitude, driver_location.longitude,
            customer_lat, customer_lng,
            settings.routing_api_url
        )
    
    return {"error": "Routing provider not configured"}

def get_osrm_route(start_lat, start_lng, end_lat, end_lng, api_url):
    """Get route from OSRM routing API"""
    import requests
    
    url = f"{api_url}{start_lng},{start_lat};{end_lng},{end_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "distance_km": round(route["distance"] / 1000, 2),
                "duration_minutes": round(route["duration"] / 60, 1),
                "geometry": route["geometry"],
                "success": True
            }
        else:
            return {"error": "Route not found", "success": False}
    
    except Exception as e:
        frappe.log_error(f"OSRM routing error: {str(e)}", "Routing API Error")
        return {"error": "Routing service unavailable", "success": False}
