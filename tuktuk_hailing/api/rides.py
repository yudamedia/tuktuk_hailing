# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
import math

@frappe.whitelist(allow_guest=True)
def create_ride_request_public(customer_phone, pickup_address, pickup_lat, pickup_lng,
                               destination_address, dest_lat, dest_lng, customer_name=None, passenger_count=1):
    """
    Public endpoint for customers to create ride requests
    Called from the booking page
    Handles both single and group bookings (multiple tuktuks)
    """
    
    try:
        passenger_count = int(passenger_count) if passenger_count else 1
        
        # Check if multiple tuktuks needed (more than 3 passengers)
        if passenger_count > 3:
            # Create group booking with multiple linked ride requests
            group_booking_id = create_group_booking(
                customer_phone=customer_phone,
                customer_name=customer_name,
                passenger_count=passenger_count,
                pickup_address=pickup_address,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                destination_address=destination_address,
                dest_lat=dest_lat,
                dest_lng=dest_lng
            )
            
            return {
                "success": True,
                "request_id": group_booking_id,
                "is_group": True,
                "tuktuks_required": math.ceil(passenger_count / 3),
                "message": f"Group booking created for {passenger_count} passengers"
            }
        else:
            # Single tuktuk booking
            from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import create_ride_request
            
            request_id = create_ride_request(
                customer_phone=customer_phone,
                pickup_address=pickup_address,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                destination_address=destination_address,
                dest_lat=dest_lat,
                dest_lng=dest_lng,
                customer_name=customer_name,
                passenger_count=passenger_count
            )
            
            return {
                "success": True,
                "request_id": request_id,
                "is_group": False,
                "message": "Ride request created successfully"
            }
    
    except Exception as e:
        frappe.log_error(f"Ride request creation error: {str(e)}", "Ride Request Error")
        return {
            "success": False,
            "error": str(e)
        }

def create_group_booking(customer_phone, customer_name, passenger_count,
                        pickup_address, pickup_lat, pickup_lng,
                        destination_address, dest_lat, dest_lng):
    """
    Create a group booking with multiple linked ride requests
    One tuktuk can carry max 3 passengers
    """
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import calculate_fare
    
    # Calculate tuktuks needed
    tuktuks_needed = math.ceil(passenger_count / 3)
    
    # Calculate fare
    single_fare, distance = calculate_fare(pickup_lat, pickup_lng, dest_lat, dest_lng)
    total_fare = single_fare * tuktuks_needed
    
    # Create Group Booking record
    group_booking = frappe.get_doc({
        "doctype": "Group Booking",
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "total_passengers": passenger_count,
        "tuktuks_required": tuktuks_needed,
        "pickup_address": pickup_address,
        "pickup_latitude": pickup_lat,
        "pickup_longitude": pickup_lng,
        "destination_address": destination_address,
        "destination_latitude": dest_lat,
        "destination_longitude": dest_lng,
        "estimated_distance_km": distance,
        "total_estimated_fare": total_fare,
        "status": "Pending",
        "requested_at": now()
    })
    
    group_booking.insert(ignore_permissions=True)
    
    # Create individual Ride Requests
    remaining_passengers = passenger_count
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import create_ride_request
    
    for i in range(tuktuks_needed):
        pax_count = min(3, remaining_passengers)
        
        # Create ride request
        request_id = create_ride_request(
            customer_phone=customer_phone,
            pickup_address=pickup_address,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            destination_address=destination_address,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            customer_name=customer_name,
            passenger_count=pax_count,
            group_booking=group_booking.name,
            tuktuk_number=i + 1
        )
        
        # Add to group booking child table
        group_booking.append("ride_requests", {
            "ride_request": request_id,
            "tuktuk_number": i + 1,
            "passenger_count": pax_count,
            "status": "Pending"
        })
        
        remaining_passengers -= pax_count
    
    group_booking.save(ignore_permissions=True)
    frappe.db.commit()
    
    return group_booking.name

@frappe.whitelist()
def get_pending_requests_for_driver(driver_id):
    """
    Get all pending ride requests visible to this driver
    Called by driver dashboard to show available requests
    """
    
    # Get driver's current location
    from tuktuk_hailing.api.location import get_driver_location
    driver_location = get_driver_location(driver_id)
    
    if not driver_location:
        return []
    
    # Get pending requests
    requests = frappe.get_all("Ride Request",
        filters={
            "status": "Pending",
            "expires_at": [">", now()]
        },
        fields=[
            "name",
            "customer_phone",
            "customer_name",
            "pickup_address",
            "pickup_latitude",
            "pickup_longitude",
            "destination_address",
            "destination_latitude",
            "destination_longitude",
            "estimated_fare",
            "estimated_distance_km",
            "requested_at",
            "expires_at"
        ],
        order_by="requested_at asc"
    )
    
    # Calculate distance from driver to each pickup location
    from tuktuk_hailing.api.location import calculate_distance
    
    for request in requests:
        request['distance_to_pickup_km'] = round(calculate_distance(
            driver_location.latitude,
            driver_location.longitude,
            request.pickup_latitude,
            request.pickup_longitude
        ), 2)
    
    # Sort by distance to pickup
    requests.sort(key=lambda x: x['distance_to_pickup_km'])
    
    return requests

@frappe.whitelist()
def accept_ride_request_by_driver(request_id, driver_id):
    """
    Driver accepts a ride request
    """
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import accept_ride_request
    
    try:
        result = accept_ride_request(request_id, driver_id)
        
        # Notify customer that driver accepted
        notify_customer_driver_accepted(request_id)
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_my_active_ride(driver_id):
    """
    Get driver's currently active ride (if any)
    Returns the Accepted or En Route ride request
    """
    
    active_ride = frappe.db.get_value("Ride Request",
        filters={
            "accepted_by_driver": driver_id,
            "status": ["in", ["Accepted", "En Route"]]
        },
        fieldname=["name", "customer_phone", "customer_name", "pickup_address", 
                   "destination_address", "estimated_fare", "status", "accepted_at"],
        as_dict=True
    )
    
    return active_ride

@frappe.whitelist()
def mark_ride_en_route(request_id):
    """
    Driver marks that they are en route to pickup customer
    """
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import mark_en_route
    
    try:
        result = mark_en_route(request_id)
        
        # Notify customer
        notify_customer_driver_enroute(request_id)
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def complete_ride_by_driver(request_id, actual_fare):
    """
    Driver marks ride as complete and enters actual fare
    """
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import complete_ride
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_trip.ride_trip import create_ride_trip_from_request
    
    try:
        # Complete the ride request
        result = complete_ride(request_id, actual_fare)
        
        # Create ride trip record
        trip_id = create_ride_trip_from_request(request_id)
        
        # Send payment request to customer
        send_payment_request(trip_id, actual_fare)
        
        # Send rating request link
        send_rating_request(trip_id)
        
        return {
            "success": True,
            "trip_id": trip_id,
            "message": "Ride completed. Payment request sent to customer."
        }
    
    except Exception as e:
        frappe.log_error(f"Complete ride error: {str(e)}", "Complete Ride Error")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def cancel_ride_by_driver(request_id, reason=None):
    """
    Driver cancels an accepted ride
    """
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import cancel_ride_request
    
    try:
        result = cancel_ride_request(request_id, "Driver", reason)
        
        # Notify customer
        notify_customer_ride_cancelled(request_id, "driver")
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def cancel_ride_by_customer(request_id, customer_phone, reason=None):
    """
    Customer cancels their ride request
    Verify customer phone matches
    """
    
    # Verify customer
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    if ride_request.customer_phone != customer_phone:
        return {
            "success": False,
            "error": "Unauthorized"
        }
    
    from tuktuk_hailing.tuktuk_hailing.doctype.ride_request.ride_request import cancel_ride_request
    
    try:
        result = cancel_ride_request(request_id, "Customer", reason)
        
        # Notify driver if already accepted
        if ride_request.accepted_by_driver:
            notify_driver_customer_cancelled(request_id)
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_group_booking_status(group_booking_id, customer_phone):
    """
    Get status of a group booking with multiple tuktuks
    """
    
    group_booking = frappe.get_doc("Group Booking", group_booking_id)
    
    # Verify customer
    if group_booking.customer_phone != customer_phone:
        return {
            "success": False,
            "error": "Unauthorized"
        }
    
    response = {
        "success": True,
        "group_booking_id": group_booking_id,
        "is_group": True,
        "status": group_booking.status,
        "total_passengers": group_booking.total_passengers,
        "tuktuks_required": group_booking.tuktuks_required,
        "pickup_address": group_booking.pickup_address,
        "destination_address": group_booking.destination_address,
        "total_estimated_fare": group_booking.total_estimated_fare,
        "ride_requests": []
    }
    
    # Get status of each ride request
    for row in group_booking.ride_requests:
        if row.ride_request:
            ride_request = frappe.get_doc("Ride Request", row.ride_request)
            
            ride_info = {
                "tuktuk_number": row.tuktuk_number,
                "passenger_count": row.passenger_count,
                "status": ride_request.status
            }
            
            # Add driver info if accepted
            if ride_request.status in ["Accepted", "En Route", "Completed"] and ride_request.accepted_by_driver:
                try:
                    driver = frappe.get_doc("TukTuk Driver", ride_request.accepted_by_driver)
                    vehicle = frappe.get_doc("TukTuk Vehicle", ride_request.accepted_by_vehicle)
                    
                    ride_info.update({
                        "driver_name": driver.driver_name,
                        "driver_phone": driver.phone_number,
                        "driver_photo": driver.photo,
                        "vehicle_id": vehicle.tuktuk_id
                    })
                except:
                    pass
            
            response["ride_requests"].append(ride_info)
    
    return response

@frappe.whitelist(allow_guest=True)
def get_ride_status(request_id, customer_phone):
    """
    Get current status of a ride request
    Customer can check their ride status
    """
    
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    # Verify customer
    if ride_request.customer_phone != customer_phone:
        return {
            "success": False,
            "error": "Unauthorized"
        }
    
    response = {
        "success": True,
        "request_id": request_id,
        "status": ride_request.status,
        "pickup_address": ride_request.pickup_address,
        "destination_address": ride_request.destination_address,
        "estimated_fare": ride_request.estimated_fare
    }
    
    # Add driver info if accepted
    if ride_request.status in ["Accepted", "En Route", "Completed"] and ride_request.accepted_by_driver:
        driver = frappe.get_doc("TukTuk Driver", ride_request.accepted_by_driver)
        vehicle = frappe.get_doc("TukTuk Vehicle", ride_request.accepted_by_vehicle)
        
        response.update({
            "driver_name": driver.driver_name,
            "driver_phone": driver.phone_number,
            "driver_photo": driver.photo,
            "vehicle_id": vehicle.tuktuk_id,
            "accepted_at": ride_request.accepted_at
        })
        
        # Add driver's current location if en route
        if ride_request.status == "En Route":
            from tuktuk_hailing.api.location import get_driver_location
            driver_location = get_driver_location(ride_request.accepted_by_driver)
            if driver_location and not driver_location.get('is_stale'):
                response['driver_location'] = {
                    "latitude": driver_location.latitude,
                    "longitude": driver_location.longitude,
                    "heading": driver_location.heading
                }
    
    return response

# Notification helper functions

def notify_customer_driver_accepted(request_id):
    """Send notification to customer that driver accepted"""
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    frappe.publish_realtime(
        event="ride_accepted",
        message={
            "request_id": request_id,
            "driver": ride_request.accepted_by_driver,
            "vehicle": ride_request.accepted_by_vehicle
        },
        user=ride_request.customer_phone
    )

def notify_customer_driver_enroute(request_id):
    """Send notification to customer that driver is en route"""
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    frappe.publish_realtime(
        event="driver_enroute",
        message={"request_id": request_id},
        user=ride_request.customer_phone
    )

def notify_customer_ride_cancelled(request_id, cancelled_by):
    """Notify customer that ride was cancelled"""
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    frappe.publish_realtime(
        event="ride_cancelled",
        message={
            "request_id": request_id,
            "cancelled_by": cancelled_by
        },
        user=ride_request.customer_phone
    )

def notify_driver_customer_cancelled(request_id):
    """Notify driver that customer cancelled"""
    ride_request = frappe.get_doc("Ride Request", request_id)
    
    if ride_request.accepted_by_driver:
        driver = frappe.get_doc("TukTuk Driver", ride_request.accepted_by_driver)
        
        frappe.publish_realtime(
            event="customer_cancelled",
            message={"request_id": request_id},
            user=driver.user
        )

def send_payment_request(trip_id, amount):
    """
    Send M-Pesa STK push to customer for payment
    This integrates with tuktuk_management M-Pesa functionality
    """
    # This will be implemented to integrate with existing M-Pesa system
    # For now, just log it
    frappe.log_error(f"Payment request for trip {trip_id}: KSH {amount}", "Payment Request")
    pass

def send_rating_request(trip_id):
    """
    Send rating request to customer via WhatsApp or SMS
    """
    # Generate rating link
    rating_url = f"{frappe.utils.get_url()}/rate-ride?trip={trip_id}"
    
    # TODO: Implement WhatsApp/SMS sending
    frappe.log_error(f"Rating request for trip {trip_id}: {rating_url}", "Rating Request")
    pass
