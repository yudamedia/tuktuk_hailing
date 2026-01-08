# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, add_to_date, get_datetime
from datetime import datetime, timedelta

class RideRequest(Document):
    def before_insert(self):
        """Set timestamps and expiration before inserting"""
        if not self.requested_at:
            self.requested_at = now()
        
        # Set expiration based on settings
        settings = frappe.get_single("Hailing Settings")
        timeout_seconds = settings.request_timeout_seconds or 30
        
        self.expires_at = add_to_date(self.requested_at, seconds=timeout_seconds)
    
    def validate(self):
        """Validate ride request"""
        # Check if customer already has active requests
        if self.status == "Pending":
            self.check_customer_active_requests()
        
        # Validate that pickup and destination are different
        if (self.pickup_latitude == self.destination_latitude and 
            self.pickup_longitude == self.destination_longitude):
            frappe.throw("Pickup and destination cannot be the same location")
    
    def check_customer_active_requests(self):
        """Check if customer has too many active requests"""
        settings = frappe.get_single("Hailing Settings")
        max_requests = settings.max_active_requests_per_customer or 1
        
        active_count = frappe.db.count("Ride Request", {
            "customer_phone": self.customer_phone,
            "status": ["in", ["Pending", "Accepted", "En Route"]],
            "name": ["!=", self.name]
        })
        
        if active_count >= max_requests:
            frappe.throw(f"You already have {active_count} active ride request(s). Please wait for completion or cancel existing requests.")
    
    def on_update(self):
        """Handle status changes"""
        if self.has_value_changed("status"):
            if self.status == "Accepted":
                self.on_accept()
            elif self.status == "Cancelled":
                self.on_cancel()
            elif self.status == "Completed":
                self.on_complete()
    
    def on_accept(self):
        """Called when request is accepted by a driver"""
        if not self.accepted_at:
            self.accepted_at = now()
        
        # Update driver status to busy
        if self.accepted_by_driver:
            driver = frappe.get_doc("TukTuk Driver", self.accepted_by_driver)
            driver.db_set("hailing_status", "En Route", update_modified=False)
    
    def on_cancel(self):
        """Called when request is cancelled"""
        if not self.cancelled_at:
            self.cancelled_at = now()
        
        # Calculate and charge cancellation fee if applicable
        if self.cancelled_by == "Customer" and self.accepted_at:
            self.calculate_cancellation_fee()
        
        # Free up driver if they were assigned
        if self.accepted_by_driver:
            driver = frappe.get_doc("TukTuk Driver", self.accepted_by_driver)
            driver.db_set("hailing_status", "Available", update_modified=False)
    
    def on_complete(self):
        """Called when ride is completed"""
        # Free up driver
        if self.accepted_by_driver:
            driver = frappe.get_doc("TukTuk Driver", self.accepted_by_driver)
            driver.db_set("hailing_status", "Available", update_modified=False)
    
    def calculate_cancellation_fee(self):
        """Calculate if cancellation fee should be charged"""
        if not self.accepted_at:
            return
        
        settings = frappe.get_single("Hailing Settings")
        free_period = settings.cancellation_free_period_seconds or 60
        
        accepted_time = get_datetime(self.accepted_at)
        cancelled_time = get_datetime(self.cancelled_at or now())
        
        time_difference = (cancelled_time - accepted_time).total_seconds()
        
        if time_difference > free_period:
            self.cancellation_fee_charged = settings.cancellation_fee or 0

@frappe.whitelist()
def create_ride_request(customer_phone, pickup_address, pickup_lat, pickup_lng, 
                       destination_address, dest_lat, dest_lng, customer_name=None,
                       passenger_count=1, group_booking=None, tuktuk_number=None):
    """Create a new ride request"""
    
    # Check if location is in service area
    from tuktuk_hailing.tuktuk_hailing.doctype.hailing_settings.hailing_settings import is_location_in_service_area
    
    if not is_location_in_service_area(pickup_lat, pickup_lng):
        frappe.throw("Pickup location is outside service area")
    
    # Calculate estimated fare
    estimated_fare, distance = calculate_fare(pickup_lat, pickup_lng, dest_lat, dest_lng)
    
    # Create ride request
    ride_request = frappe.get_doc({
        "doctype": "Ride Request",
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "customer_latitude": pickup_lat,
        "customer_longitude": pickup_lng,
        "pickup_address": pickup_address,
        "pickup_latitude": pickup_lat,
        "pickup_longitude": pickup_lng,
        "destination_address": destination_address,
        "destination_latitude": dest_lat,
        "destination_longitude": dest_lng,
        "estimated_distance_km": distance,
        "estimated_fare": estimated_fare,
        "passenger_count": passenger_count,
        "group_booking": group_booking,
        "tuktuk_number": tuktuk_number,
        "status": "Pending",
        "requested_at": now()
    })
    
    ride_request.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # Notify available drivers
    notify_drivers(ride_request.name)
    
    return ride_request.name

@frappe.whitelist()
def accept_ride_request(request_id, driver_id):
    """Driver accepts a ride request"""

    try:
        # Get the ride request
        ride_request = frappe.get_doc("Ride Request", request_id)

        # Check if request is still pending
        if ride_request.status != "Pending":
            return {
                "success": False,
                "error": "This ride request is no longer available"
            }

        # Check if request has expired
        if get_datetime(ride_request.expires_at) < get_datetime(now()):
            ride_request.status = "Expired"
            ride_request.save(ignore_permissions=True)
            frappe.db.commit()
            return {
                "success": False,
                "error": "This ride request has expired"
            }

        # Get driver and vehicle
        driver = frappe.get_doc("TukTuk Driver", driver_id)

        if not driver.assigned_tuktuk:
            return {
                "success": False,
                "error": "You do not have an assigned tuktuk. Please contact support."
            }

        # Accept the request
        ride_request.status = "Accepted"
        ride_request.accepted_by_driver = driver_id
        ride_request.accepted_by_vehicle = driver.assigned_tuktuk
        ride_request.accepted_at = now()
        ride_request.save(ignore_permissions=True)

        # Update group booking status if this is part of a group
        if ride_request.group_booking:
            update_group_booking_status(ride_request.group_booking, request_id)

        frappe.db.commit()

        return {
            "success": True,
            "name": ride_request.name,
            "customer_phone": ride_request.customer_phone,
            "customer_name": ride_request.customer_name,
            "pickup_address": ride_request.pickup_address,
            "pickup_latitude": ride_request.pickup_latitude,
            "pickup_longitude": ride_request.pickup_longitude,
            "destination_address": ride_request.destination_address,
            "destination_latitude": ride_request.destination_latitude,
            "destination_longitude": ride_request.destination_longitude,
            "estimated_fare": ride_request.estimated_fare,
            "estimated_distance_km": ride_request.estimated_distance_km,
            "accepted_at": str(ride_request.accepted_at),
            "status": ride_request.status
        }

    except Exception as e:
        frappe.log_error(f"Error accepting ride request: {str(e)}", "Accept Ride Error")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def mark_en_route(request_id):
    """Mark that driver is en route to pickup"""
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    if ride_request.status != "Accepted":
        frappe.throw("Can only mark accepted requests as en route")
    
    ride_request.status = "En Route"
    ride_request.save(ignore_permissions=True)
    
    # Update group booking status if this is part of a group
    if ride_request.group_booking:
        update_group_booking_status(ride_request.group_booking, request_id)
    
    frappe.db.commit()
    
    return {"success": True}

@frappe.whitelist()
def complete_ride(request_id, actual_fare):
    """Complete a ride and process payment"""
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    if ride_request.status not in ["Accepted", "En Route"]:
        frappe.throw("Cannot complete this ride")
    
    ride_request.status = "Completed"
    ride_request.actual_fare = actual_fare
    ride_request.save(ignore_permissions=True)
    
    # Update group booking status if this is part of a group
    if ride_request.group_booking:
        update_group_booking_status(ride_request.group_booking, request_id)
    
    frappe.db.commit()
    
    # Trigger M-Pesa STK push for payment
    # This will be handled by tuktuk_management app
    
    return {
        "success": True,
        "message": "Ride completed. Payment request sent to customer."
    }

@frappe.whitelist()
def cancel_ride_request(request_id, cancelled_by, reason=None):
    """Cancel a ride request"""
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    if ride_request.status in ["Completed", "Cancelled"]:
        frappe.throw("Cannot cancel this ride request")
    
    ride_request.status = "Cancelled"
    ride_request.cancelled_by = cancelled_by
    ride_request.cancellation_reason = reason
    ride_request.cancelled_at = now()
    ride_request.save(ignore_permissions=True)
    
    # Update group booking status if this is part of a group
    if ride_request.group_booking:
        update_group_booking_status(ride_request.group_booking, request_id)
    
    frappe.db.commit()
    
    return {"success": True, "cancellation_fee": ride_request.cancellation_fee_charged}

def calculate_fare(pickup_lat, pickup_lng, dest_lat, dest_lng):
    """Calculate estimated fare based on distance"""
    import math
    
    settings = frappe.get_single("Hailing Settings")
    
    # Haversine formula to calculate distance
    R = 6371  # Earth's radius in km
    
    lat1, lon1 = math.radians(float(pickup_lat)), math.radians(float(pickup_lng))
    lat2, lon2 = math.radians(float(dest_lat)), math.radians(float(dest_lng))
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    
    # Calculate fare
    fare = float(settings.base_fare) + (distance * float(settings.per_km_rate))
    
    # Apply minimum fare
    if fare < float(settings.minimum_fare):
        fare = float(settings.minimum_fare)
    
    return round(fare, 2), round(distance, 2)

def update_group_booking_status(group_booking_id, ride_request_id):
    """Update group booking status and child table when a ride request status changes"""
    try:
        group_booking = frappe.get_doc("Group Booking", group_booking_id)
        ride_request = frappe.get_doc("Ride Request", ride_request_id)
        
        # Update the child table row
        for row in group_booking.ride_requests:
            if row.ride_request == ride_request_id:
                row.status = ride_request.status
                break
        
        # Update group booking status
        group_booking.update_status()
        
    except Exception as e:
        frappe.log_error(f"Error updating group booking status: {str(e)}", "Group Booking Status Update")

def notify_drivers(request_id):
    """Notify available drivers about new ride request"""
    # Get all available drivers (online and available for rides)
    available_drivers = frappe.get_all("TukTuk Driver",
        filters={
            "hailing_status": "Available"
        },
        fields=["name", "user_account", "driver_name"]
    )

    frappe.logger().info(f"🔔 notify_drivers called for request {request_id}")
    frappe.logger().info(f"   Found {len(available_drivers)} available drivers")

    # Get ride request details for the notification
    ride_request = frappe.get_doc("Ride Request", request_id)

    notification_data = {
        "request_id": request_id,
        "pickup_address": ride_request.pickup_address,
        "destination_address": ride_request.destination_address,
        "pickup_latitude": ride_request.pickup_latitude,
        "pickup_longitude": ride_request.pickup_longitude,
        "destination_latitude": ride_request.destination_latitude,
        "destination_longitude": ride_request.destination_longitude,
        "estimated_fare": ride_request.estimated_fare,
        "estimated_distance_km": ride_request.estimated_distance_km,
        "passenger_count": ride_request.passenger_count,
        "requested_at": str(ride_request.requested_at),
        "expires_at": str(ride_request.expires_at)
    }

    # Send real-time notification to each available driver
    for driver in available_drivers:
        if driver.user_account:
            frappe.logger().info(f"   📤 Sending event to driver {driver.driver_name} (user: {driver.user_account})")
            frappe.publish_realtime(
                event="new_ride_request",
                message=notification_data,
                user=driver.user_account
            )
        else:
            frappe.logger().info(f"   ⚠️ Driver {driver.driver_name} has no user_account, skipping")

    frappe.logger().info(f"✅ Notified {len(available_drivers)} drivers about ride request {request_id}")

def expire_old_requests():
    """Scheduled task to expire old pending requests"""
    expired_requests = frappe.get_all("Ride Request", 
        filters={
            "status": "Pending",
            "expires_at": ["<", now()]
        }
    )
    
    for req in expired_requests:
        doc = frappe.get_doc("Ride Request", req.name)
        doc.status = "Expired"
        doc.save(ignore_permissions=True)
    
    frappe.db.commit()
