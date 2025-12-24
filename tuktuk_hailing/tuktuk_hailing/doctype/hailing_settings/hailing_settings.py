# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

class HailingSettings(Document):
    def validate(self):
        """Validate service area coordinates are valid GeoJSON"""
        if self.service_area_coordinates:
            try:
                coords = json.loads(self.service_area_coordinates)
                # Basic validation - should be a list of lists
                if not isinstance(coords, list):
                    frappe.throw("Service area coordinates must be a valid GeoJSON polygon array")
                
                # Check if it's a polygon (at least 3 points, first and last should be same)
                if len(coords) > 0 and len(coords[0]) > 0:
                    first_ring = coords[0]
                    if len(first_ring) < 4:
                        frappe.throw("Service area polygon must have at least 3 points (4 including closing point)")
                    if first_ring[0] != first_ring[-1]:
                        frappe.throw("Service area polygon must be closed (first and last coordinate must be the same)")
                        
            except json.JSONDecodeError:
                frappe.throw("Invalid JSON format for service area coordinates")
    
    def before_save(self):
        """Generate map preview HTML"""
        if self.service_area_coordinates:
            self.service_area_map = self.generate_map_preview()
    
    def generate_map_preview(self):
        """Generate HTML for map preview in the form"""
        if not self.service_area_coordinates:
            return ""
        
        try:
            coords = json.loads(self.service_area_coordinates)
            # Calculate center of polygon for map centering
            if len(coords) > 0 and len(coords[0]) > 0:
                lats = [point[1] for point in coords[0]]
                lngs = [point[0] for point in coords[0]]
                center_lat = sum(lats) / len(lats)
                center_lng = sum(lngs) / len(lngs)
                
                return f'''
                <div id="service-area-preview" style="height: 400px; width: 100%;"></div>
                <script>
                    frappe.ready(function() {{
                        if (typeof L !== 'undefined') {{
                            var map = L.map('service-area-preview').setView([{center_lat}, {center_lng}], 13);
                            L.tileLayer('{self.osm_tile_server}', {{
                                attribution: '© OpenStreetMap contributors'
                            }}).addTo(map);
                            
                            var polygon = L.polygon({coords[0]}, {{
                                color: '#f39c12',
                                fillColor: '#f39c12',
                                fillOpacity: 0.2
                            }}).addTo(map);
                            
                            map.fitBounds(polygon.getBounds());
                        }}
                    }});
                </script>
                '''
        except:
            return "<p>Invalid coordinates format. Cannot preview map.</p>"

@frappe.whitelist()
def get_hailing_settings():
    """Get hailing settings - used by client apps"""
    if not frappe.db.exists("Hailing Settings", "Hailing Settings"):
        return None
    
    settings = frappe.get_single("Hailing Settings")
    
    return {
        "base_fare": settings.base_fare,
        "per_km_rate": settings.per_km_rate,
        "minimum_fare": settings.minimum_fare,
        "surge_pricing_enabled": settings.surge_pricing_enabled,
        "service_area_coordinates": settings.service_area_coordinates,
        "location_update_interval_available": settings.location_update_interval_available,
        "location_update_interval_enroute": settings.location_update_interval_enroute,
        "request_timeout_seconds": settings.request_timeout_seconds,
        "cancellation_fee": settings.cancellation_fee,
        "cancellation_free_period_seconds": settings.cancellation_free_period_seconds,
        "osm_tile_server": settings.osm_tile_server,
        "routing_api_url": settings.routing_api_url,
        "show_driver_radius_meters": settings.show_driver_radius_meters
    }

@frappe.whitelist()
def is_location_in_service_area(latitude, longitude):
    """Check if a location is within the service area"""
    settings = frappe.get_single("Hailing Settings")
    
    if not settings.service_area_coordinates:
        # If no service area defined, allow all locations
        return True
    
    try:
        coords = json.loads(settings.service_area_coordinates)
        # Point-in-polygon algorithm
        return point_in_polygon(float(latitude), float(longitude), coords[0])
    except:
        return False

def point_in_polygon(lat, lng, polygon):
    """Ray casting algorithm for point-in-polygon test"""
    inside = False
    j = len(polygon) - 1
    
    for i in range(len(polygon)):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        
        j = i
    
    return inside
