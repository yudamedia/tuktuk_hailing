# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime, time_diff_in_seconds

class RideTrip(Document):
    def validate(self):
        """Calculate duration if not set"""
        if self.started_at and self.completed_at and not self.duration_minutes:
            duration_seconds = time_diff_in_seconds(self.completed_at, self.started_at)
            self.duration_minutes = int(duration_seconds / 60)
    
    def on_submit(self):
        """Update driver statistics when trip is submitted"""
        self.update_driver_stats()
    
    def update_driver_stats(self):
        """Update driver's hailing statistics"""
        driver = frappe.get_doc("TukTuk Driver", self.driver)
        
        # Update total hailing trips count (if field exists)
        if hasattr(driver, 'total_hailing_trips'):
            driver.total_hailing_trips = (driver.total_hailing_trips or 0) + 1
        
        # Update average rating (if rating provided and field exists)
        if self.customer_rating and hasattr(driver, 'average_hailing_rating'):
            current_avg = driver.average_hailing_rating or 0
            current_count = driver.total_hailing_trips or 1
            
            new_avg = ((current_avg * (current_count - 1)) + self.customer_rating) / current_count
            driver.average_hailing_rating = round(new_avg, 2)
        
        driver.save(ignore_permissions=True)

@frappe.whitelist()
def create_ride_trip_from_request(request_id):
    """Create a Ride Trip record from a completed Ride Request"""
    
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    if ride_request.status != "Completed":
        frappe.throw("Ride request must be completed")
    
    # Check if trip already exists
    existing = frappe.db.exists("Ride Trip", {"ride_request": request_id})
    if existing:
        return existing
    
    # Create trip record
    ride_trip = frappe.get_doc({
        "doctype": "Ride Trip",
        "ride_request": request_id,
        "driver": ride_request.accepted_by_driver,
        "vehicle": ride_request.accepted_by_vehicle,
        "customer_phone": ride_request.customer_phone,
        "customer_name": ride_request.customer_name,
        "pickup_address": ride_request.pickup_address,
        "destination_address": ride_request.destination_address,
        "started_at": ride_request.accepted_at,
        "completed_at": now(),
        "distance_traveled_km": ride_request.estimated_distance_km,
        "fare_charged": ride_request.actual_fare,
        "payment_status": "Pending"
    })
    
    ride_trip.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return ride_trip.name

@frappe.whitelist()
def submit_customer_rating(trip_id, rating, comment=None):
    """Submit customer rating for a trip"""
    
    settings = frappe.get_single("Hailing Settings")
    
    if not settings.enable_customer_ratings:
        frappe.throw("Customer ratings are not enabled")
    
    ride_trip = frappe.get_doc("Ride Trip", trip_id)
    
    if ride_trip.customer_rating:
        frappe.throw("This trip has already been rated")
    
    ride_trip.customer_rating = rating
    ride_trip.customer_rating_comment = comment
    ride_trip.rated_at = now()
    ride_trip.save(ignore_permissions=True)
    frappe.db.commit()
    
    # Check if driver's rating has dropped below threshold
    check_driver_rating_threshold(ride_trip.driver)
    
    return {"success": True, "message": "Thank you for your rating!"}

def check_driver_rating_threshold(driver_id):
    """Check if driver's average rating is below threshold"""
    settings = frappe.get_single("Hailing Settings")
    
    if not settings.enable_customer_ratings:
        return
    
    driver = frappe.get_doc("TukTuk Driver", driver_id)
    
    if not hasattr(driver, 'average_hailing_rating'):
        return
    
    if driver.average_hailing_rating and driver.average_hailing_rating < settings.minimum_rating_threshold:
        # Send warning to driver and management
        frappe.publish_realtime(
            event="low_rating_warning",
            message={
                "driver": driver_id,
                "rating": driver.average_hailing_rating,
                "threshold": settings.minimum_rating_threshold
            },
            user=driver.user
        )
        
        # Log to system
        frappe.log_error(
            f"Driver {driver_id} has low rating: {driver.average_hailing_rating}",
            "Low Driver Rating Alert"
        )

@frappe.whitelist()
def update_payment_status(trip_id, status, transaction_id=None):
    """Update payment status for a trip"""
    
    ride_trip = frappe.get_doc("Ride Trip", trip_id)
    ride_trip.payment_status = status
    
    if transaction_id:
        ride_trip.mpesa_transaction_id = transaction_id
    
    ride_trip.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"success": True}
