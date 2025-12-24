# Tuktuk Hailing - Implementation Summary

## Project Overview

A complete ride-hailing system built for Sunny Tuktuk's electric tuktuk fleet in Diani Beach, Kenya. The system enables real-time GPS tracking, customer ride requests via web portal, driver acceptance through ERPNext dashboard, and WhatsApp-based customer-driver communication.

## Architecture

### Technology Stack

- **Backend Framework**: Frappe/ERPNext 15
- **Frontend**: Vanilla JavaScript + Leaflet.js for maps
- **Real-time Communication**: Frappe's built-in Socket.IO
- **Mapping**: OpenStreetMap tiles
- **Routing**: OSRM (Open Source Routing Machine)
- **Payments**: M-Pesa integration (via tuktuk_management)
- **Communication**: WhatsApp

### Key Components

```
tuktuk_hailing/
├── DocTypes
│   ├── Hailing Settings (Single)      # System configuration
│   ├── Ride Request                   # Customer ride requests
│   ├── Ride Trip                      # Completed rides with ratings
│   └── Driver Location                # Real-time GPS tracking
├── API Endpoints
│   ├── location.py                    # GPS tracking & driver queries
│   └── rides.py                       # Ride request lifecycle
├── Web Portal
│   └── www/book/                      # Customer booking interface
└── UI Extensions
    └── public/js/tuktuk_driver_hailing.js  # Driver dashboard
```

## Core Features Implemented

### 1. Service Area Geofencing

**DocType**: Hailing Settings

**Feature**: GeoJSON polygon definition with point-in-polygon validation

**Implementation**:
```python
# hailing_settings.py
def point_in_polygon(lat, lng, polygon):
    """Ray casting algorithm for point-in-polygon test"""
    # Uses ray casting to determine if point is inside polygon
```

**Usage**: 
- Prevents ride requests outside service area
- Validates customer location before accepting booking

### 2. Real-time Driver Location Tracking

**DocType**: Driver Location

**Update Frequency**:
- Available: Every 10 seconds (configurable)
- En Route: Every 5 seconds (configurable)

**Privacy Protection**:
- ~50m radius offset applied to displayed locations
- Customers see approximate location, not exact coordinates

**Implementation**:
```javascript
// tuktuk_driver_hailing.js
function updateLocation(frm) {
    navigator.geolocation.getCurrentPosition(
        async (position) => {
            await frappe.call({
                method: 'tuktuk_hailing.api.location.update_driver_location',
                args: {
                    driver_id: frm.doc.name,
                    latitude: lat,
                    longitude: lng,
                    // ... other data
                }
            });
        }
    );
}
```

**Cleanup**: 
- Stale locations marked after 60 seconds (configurable)
- Old records deleted after 24 hours (automated task)

### 3. Fare Estimation

**Algorithm**: 
```
Estimated Fare = Base Fare + (Distance in KM × Per KM Rate)
Minimum Fare = 100 KSH
```

**Distance Calculation**: Haversine formula for great-circle distance

**Implementation**:
```python
# ride_request.py
def calculate_fare(pickup_lat, pickup_lng, dest_lat, dest_lng):
    R = 6371  # Earth's radius in km
    # Haversine formula implementation
    distance = R * c
    fare = base_fare + (distance * per_km_rate)
    return max(fare, minimum_fare), distance
```

### 4. Ride Request Workflow

```
Customer Creates Request
    ↓
System Validates Service Area
    ↓
Calculate Estimated Fare
    ↓
Broadcast to Available Drivers
    ↓
First Driver Accepts
    ↓
Other Requests Marked Unavailable
    ↓
Customer Receives Driver Info
    ↓
Driver En Route (tracked in real-time)
    ↓
Ride Completed
    ↓
Payment Requested (M-Pesa STK Push)
    ↓
Rating Request Sent
```

**Status States**:
- Pending → Accepted → En Route → Completed
- Pending → Expired (after timeout)
- Any → Cancelled (by customer or driver)

### 5. Driver Dashboard Integration

**Location**: Extends existing TukTuk Driver form

**Features**:
- **Availability Toggle**: On/Off button for receiving requests
- **Real-time Map**: Shows driver's location and nearby drivers
- **Pending Requests List**: All available rides sorted by distance
- **Accept/Reject Interface**: One-click acceptance
- **Active Ride Display**: Current customer info with WhatsApp button
- **GPS Auto-tracking**: Automatic location updates when available

**UI Components**:
```javascript
frappe.ui.form.on('TukTuk Driver', {
    refresh: function(frm) {
        add_hailing_dashboard(frm);  // Injects hailing interface
    }
});
```

### 6. Customer Booking Portal

**URL**: `/book` (guest-accessible)

**Flow**:
1. Request location permission
2. Display map with available drivers
3. Enter phone (WhatsApp), name
4. Select pickup and destination on map
5. View estimated fare
6. Request ride
7. Wait for acceptance (polling every 3 seconds)
8. Show driver info when accepted
9. Track driver location in real-time
10. Open WhatsApp for communication

**Implementation**: Pure HTML/CSS/JS with Leaflet.js for mapping

### 7. Cancellation Management

**Free Cancellation Period**: 60 seconds after acceptance (configurable)

**Cancellation Fee**: 50 KSH (configurable)

**Logic**:
```python
# ride_request.py
def calculate_cancellation_fee(self):
    time_difference = (cancelled_time - accepted_time).total_seconds()
    if time_difference > free_period:
        self.cancellation_fee_charged = settings.cancellation_fee
```

**Notifications**:
- Customer notified if driver cancels
- Driver notified if customer cancels
- Fee charged automatically via M-Pesa

### 8. Customer Rating System

**DocType**: Ride Trip (includes rating fields)

**Features**:
- 5-star rating system
- Optional comment
- Rating link sent via WhatsApp/SMS after ride
- Driver average rating tracked
- Low rating warnings (below 3.5 threshold)

**Driver Performance Tracking**:
```python
# ride_trip.py
def update_driver_stats(self):
    current_avg = driver.average_hailing_rating
    current_count = driver.total_hailing_trips
    new_avg = ((current_avg * (current_count - 1)) + self.customer_rating) / current_count
    driver.average_hailing_rating = round(new_avg, 2)
```

### 9. Payment Integration

**Integration Point**: tuktuk_management app's M-Pesa system

**Workflow**:
```
Ride Completed
    ↓
Create Ride Trip Record
    ↓
Create TukTuk Transaction (links to tuktuk_management)
    ↓
Payment Split Logic Applied
    ↓
M-Pesa B2C Payment to Driver
    ↓
Contribute to Daily Target
```

**Payment Split**:
- Before target met: 50% driver, 50% to target
- After target met: 100% to driver
- Same logic as existing tuktuk_management system

### 10. WhatsApp Integration

**Use Cases**:
- Customer-Driver communication
- Rating requests
- Trip confirmations
- Notifications

**Implementation**:
```javascript
function openWhatsApp(phone, message) {
    const url = `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
    window.open(url, '_blank');
}
```

**Optional**: WhatsApp Business API for automated messages

## API Endpoints

### Location Management

```python
# location.py

@frappe.whitelist()
def update_driver_location(driver_id, latitude, longitude, ...)
    # Updates driver's GPS position

@frappe.whitelist()
def get_available_drivers(customer_lat, customer_lng, max_distance_km)
    # Returns list of available drivers within distance

@frappe.whitelist()
def set_driver_availability(driver_id, available)
    # Toggles driver's availability status

@frappe.whitelist()
def get_driver_location(driver_id)
    # Gets specific driver's current location
```

### Ride Management

```python
# rides.py

@frappe.whitelist(allow_guest=True)
def create_ride_request_public(customer_phone, pickup_address, ...)
    # Creates new ride request from customer

@frappe.whitelist()
def get_pending_requests_for_driver(driver_id)
    # Gets all pending requests for a driver

@frappe.whitelist()
def accept_ride_request_by_driver(request_id, driver_id)
    # Driver accepts a ride

@frappe.whitelist()
def complete_ride_by_driver(request_id, actual_fare)
    # Marks ride as complete and processes payment

@frappe.whitelist(allow_guest=True)
def cancel_ride_by_customer(request_id, customer_phone, reason)
    # Customer cancels their request

@frappe.whitelist(allow_guest=True)
def get_ride_status(request_id, customer_phone)
    # Customer checks their ride status
```

## Real-time Features

### Socket.IO Events

**Published Events**:
```python
# New ride request broadcast
frappe.publish_realtime(
    event="new_ride_request",
    message={"request_id": request_id},
    user="all_drivers"
)

# Driver location update
frappe.publish_realtime(
    event="driver_location_update",
    message={...},
    doctype="Driver Location"
)

# Ride accepted notification
frappe.publish_realtime(
    event="ride_accepted",
    message={...},
    user=ride_request.customer_phone
)
```

### Polling Fallback

For clients without Socket.IO support:
- Customer polls ride status every 3 seconds
- Driver polls pending requests every 5 seconds

## Database Schema

### Hailing Settings (Single DocType)
```
- service_area_coordinates (JSON)
- base_fare (Currency)
- per_km_rate (Currency)
- minimum_fare (Currency)
- location_update_interval_available (Int)
- location_update_interval_enroute (Int)
- request_timeout_seconds (Int)
- cancellation_fee (Currency)
- enable_customer_ratings (Check)
- osm_tile_server (Data)
- routing_api_url (Data)
```

### Ride Request
```
- customer_phone (Data) *indexed*
- pickup_latitude/longitude (Float)
- destination_latitude/longitude (Float)
- estimated_fare (Currency)
- status (Select) *indexed*
- accepted_by_driver (Link to TukTuk Driver)
- accepted_by_vehicle (Link to TukTuk Vehicle)
- requested_at (Datetime)
- expires_at (Datetime)
```

### Ride Trip
```
- ride_request (Link) *indexed*
- driver (Link) *indexed*
- vehicle (Link)
- customer_phone (Data)
- fare_charged (Currency)
- payment_status (Select)
- customer_rating (Rating)
- started_at (Datetime)
- completed_at (Datetime)
```

### Driver Location
```
- driver (Link) *indexed*
- latitude/longitude (Float)
- hailing_status (Select) *indexed*
- timestamp (Datetime) *indexed*
- is_stale (Check)
```

## Performance Considerations

### Optimizations Implemented

1. **Database Indexes**: On frequently queried fields (status, timestamp, driver)
2. **Stale Data Cleanup**: Automated task every 5 minutes
3. **Location Privacy**: ~50m offset reduces precision requirements
4. **Request Expiration**: Automatic cleanup of old requests
5. **Efficient Distance Calc**: Haversine formula, not full routing

### Recommended Enhancements

1. **Redis Caching**: Cache available driver locations
2. **Database Partitioning**: Partition Driver Location by date
3. **CDN for Tiles**: Use CDN for OpenStreetMap tiles
4. **Web Workers**: Offload distance calculations to web workers
5. **Progressive Loading**: Load drivers incrementally on map

## Security Measures

1. **Guest Endpoints**: Only ride creation and status checking
2. **Phone Verification**: Customer phone must match for cancellation
3. **Driver Authentication**: Location updates require login
4. **Service Area Validation**: All requests checked against geofence
5. **Rate Limiting**: Should be added to prevent abuse
6. **Location Privacy**: Approximate display, not exact coordinates

## Testing Checklist

- [ ] Driver can go available/offline
- [ ] Location updates sent correctly
- [ ] Customer can create ride request
- [ ] Driver receives pending requests
- [ ] Driver can accept request
- [ ] Customer sees driver info when accepted
- [ ] WhatsApp links work
- [ ] Ride can be completed
- [ ] Payment transaction created
- [ ] Daily target updated
- [ ] Customer can rate driver
- [ ] Cancellation fees calculated correctly
- [ ] Expired requests cleaned up
- [ ] Stale locations marked
- [ ] Service area validation works

## Future Enhancements

### Phase 2 Features
- Push notifications (web push API)
- Route optimization for multi-stop rides
- Surge pricing implementation
- Driver heat maps (demand visualization)
- Customer ride history
- Loyalty/rewards program

### Phase 3 Features
- Mobile apps (React Native)
- Advanced analytics dashboard
- Machine learning for demand prediction
- Dynamic pricing based on demand
- Driver scheduling optimization
- Corporate accounts

## Integration Points

### With tuktuk_management App

1. **Payment Processing**: M-Pesa integration reused
2. **Daily Targets**: Hailing revenue contributes to targets
3. **Driver Management**: Extends TukTuk Driver doctype
4. **Vehicle Assignment**: Uses assigned tuktuk from driver
5. **Performance Tracking**: Integrates with existing metrics

### Extension Fields Required

Add to TukTuk Driver doctype:
```json
{
    "fieldname": "hailing_status",
    "fieldtype": "Select",
    "options": "Offline\nAvailable\nEn Route\nBusy",
    "default": "Offline"
},
{
    "fieldname": "total_hailing_trips",
    "fieldtype": "Int",
    "default": "0",
    "read_only": 1
},
{
    "fieldname": "average_hailing_rating",
    "fieldtype": "Float",
    "precision": "2",
    "read_only": 1
}
```

## Deployment Notes

1. **Ensure scheduler is running**: `bench enable-scheduler`
2. **Configure firewall**: Allow port 443 for HTTPS
3. **SSL Certificate**: Required for geolocation API
4. **Test on mobile**: Primary use case is mobile browsers
5. **Monitor error logs**: Watch for location/payment errors
6. **Backup strategy**: Regular backups of Ride Trip records

## Support & Maintenance

**Weekly Tasks**:
- Review error logs
- Check stale location cleanup
- Monitor driver ratings
- Verify payment processing

**Monthly Tasks**:
- Analyze ride patterns
- Review customer feedback
- Optimize service area boundaries
- Update fare rates if needed

## License

MIT License - Free to use and modify

## Contributors

Built for Sunny Tuktuk by [Your Team]

## Version History

- **v0.0.1** (2024-12-18): Initial implementation
  - Core ride hailing features
  - Real-time GPS tracking
  - Customer booking portal
  - Driver dashboard integration
  - Payment integration
  - Rating system
