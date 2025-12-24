# Sunny Tuktuk Hailing - Architecture Overview

## System Architecture

Your ride hailing system uses a **split architecture** with clear separation between customer-facing and operational systems:

```
┌──────────────────────────────────────────────────────────────┐
│                    CUSTOMER INTERFACE                        │
│          www.sunnytuktuk.com (Marketing Website)            │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         booking-standalone.html                     │    │
│  │                                                      │    │
│  │  • OpenStreetMap Display                           │    │
│  │  • Real-time Driver Locations                      │    │
│  │  • Fare Estimation                                 │    │
│  │  • Ride Request Form                               │    │
│  │  • Driver Tracking (En Route)                      │    │
│  └─────────────────┬────────────────────────────────────┘    │
└────────────────────┼─────────────────────────────────────────┘
                     │
                     │ HTTPS + CORS
                     │ JSON REST API
                     │
┌────────────────────▼─────────────────────────────────────────┐
│              BACKEND & OPERATIONS                            │
│          console.sunnytuktuk.com (ERPNext)                  │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Tuktuk Hailing App                         │    │
│  │                                                      │    │
│  │  API Layer:                                        │    │
│  │    • location.py - GPS tracking                    │    │
│  │    • rides.py - Ride management                    │    │
│  │                                                      │    │
│  │  DocTypes:                                         │    │
│  │    • Hailing Settings (configuration)              │    │
│  │    • Ride Request (customer requests)              │    │
│  │    • Ride Trip (completed rides)                   │    │
│  │    • Driver Location (GPS tracking)                │    │
│  │                                                      │    │
│  │  UI Extensions:                                     │    │
│  │    • Driver Dashboard (embedded in ERPNext)        │    │
│  │                                                      │    │
│  └──────────────┬─────────────────────────────────────┘    │
│                 │                                            │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │         Tuktuk Management App                       │   │
│  │                                                      │   │
│  │  • M-Pesa Payment Processing                       │   │
│  │  • Daily Target Tracking                           │   │
│  │  • Driver Performance                              │   │
│  │  • Fleet Management                                │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### Customer Requests Ride

```
1. Customer (www.sunnytuktuk.com)
   ↓ Opens booking page
   ↓ Allows location access
   ↓ Sees available drivers on map
   ↓
2. API Call: get_available_drivers()
   → https://console.sunnytuktuk.com/api/method/...
   ← Returns list of available drivers with locations
   ↓
3. Customer enters details:
   - Phone number (WhatsApp)
   - Pickup location (map click)
   - Destination (map click)
   ↓ Sees estimated fare
   ↓
4. API Call: create_ride_request_public()
   → Sends ride details to backend
   ← Returns request_id
   ↓
5. Polling: get_ride_status()
   → Check every 3 seconds
   ← Status: Pending | Accepted | Expired
   ↓
6. When Accepted:
   ← Returns driver info (name, phone, photo, vehicle)
   ↓ Display driver details
   ↓ Show WhatsApp button
   ↓ Track driver location in real-time
```

### Driver Accepts Ride

```
1. Driver (console.sunnytuktuk.com)
   ↓ Logs into ERPNext
   ↓ Opens TukTuk Driver record
   ↓
2. Clicks "Go Available"
   ↓ Browser requests location permission
   ↓ GPS starts tracking every 10s
   ↓
3. API Call: update_driver_location()
   → Sends lat/lng/heading/speed
   ← Success confirmation
   ↓
4. Sees pending requests:
   - Pickup address
   - Destination address
   - Estimated fare
   - Distance to pickup
   ↓
5. Clicks "Accept"
   ↓
6. API Call: accept_ride_request_by_driver()
   → Marks request as accepted
   ← Returns customer details
   ↓
7. Gets customer WhatsApp number
   ↓ Clicks to open WhatsApp
   ↓ Coordinates with customer
   ↓
8. GPS tracking increases to every 5s
   ↓ Customer sees driver approaching
   ↓
9. Completes ride
   ↓ Enters actual fare
   ↓
10. API Call: complete_ride_by_driver()
    → Creates Ride Trip record
    → Creates TukTuk Transaction
    → Triggers M-Pesa payment
    ← Success confirmation
```

## API Endpoints

### Public Endpoints (Guest Access)

These are called from **www.sunnytuktuk.com** without authentication:

| Endpoint | Method | Purpose | Used By |
|----------|--------|---------|---------|
| `get_available_drivers` | POST | Get list of available drivers | Customer booking |
| `create_ride_request_public` | POST | Create new ride request | Customer booking |
| `get_ride_status` | POST | Check request status | Customer polling |
| `cancel_ride_by_customer` | POST | Cancel a request | Customer |

### Protected Endpoints (Driver Only)

These require ERPNext login from **console.sunnytuktuk.com**:

| Endpoint | Method | Purpose | Used By |
|----------|--------|---------|---------|
| `update_driver_location` | POST | Update GPS position | Driver dashboard |
| `set_driver_availability` | POST | Toggle available/offline | Driver dashboard |
| `get_pending_requests_for_driver` | POST | Get ride requests | Driver dashboard |
| `accept_ride_request_by_driver` | POST | Accept a request | Driver dashboard |
| `mark_ride_en_route` | POST | Mark en route | Driver dashboard |
| `complete_ride_by_driver` | POST | Complete ride | Driver dashboard |
| `cancel_ride_by_driver` | POST | Cancel ride | Driver dashboard |

## Security Model

### CORS (Cross-Origin Resource Sharing)

**Problem**: Browser blocks API calls from www.sunnytuktuk.com to console.sunnytuktuk.com

**Solution**: Configure CORS headers

```json
// site_config.json
{
  "allow_cors": "https://www.sunnytuktuk.com",
  "cors_allowed_origins": [
    "https://www.sunnytuktuk.com",
    "https://sunnytuktuk.com"
  ],
  "ignore_csrf": 1
}
```

### Authentication Layers

1. **Guest Endpoints**: 
   - Allow customer actions without login
   - Validate phone number for customer-specific actions
   - Rate-limited to prevent abuse

2. **Driver Endpoints**:
   - Require ERPNext authentication
   - Driver must be logged in to console
   - Session-based security

3. **Data Validation**:
   - Service area geofencing
   - Phone number format validation
   - Request expiration (30s timeout)
   - Stale location cleanup

### Privacy Protection

- Driver locations shown with ~50m radius offset
- Customer can only access their own requests
- Phone numbers validated before cancellation
- No sensitive data in API responses

## Technology Stack

### Frontend (www.sunnytuktuk.com)

```
HTML5/CSS3/JavaScript
├── Leaflet.js (maps)
├── OpenStreetMap tiles
├── Fetch API (HTTP requests)
└── Geolocation API (GPS)
```

**No frameworks required** - Pure vanilla JS for minimal dependencies.

### Backend (console.sunnytuktuk.com)

```
Frappe/ERPNext
├── Python 3.10+
├── MariaDB/MySQL
├── Redis (caching)
├── Socket.IO (real-time)
└── Gunicorn (WSGI)
```

**Integration**: M-Pesa via existing tuktuk_management app.

## Database Schema

### Core Tables

```
tabRide Request
├── customer_phone (indexed)
├── pickup_lat, pickup_lng
├── destination_lat, destination_lng
├── status (indexed)
├── estimated_fare
├── accepted_by_driver (FK)
└── expires_at

tabDriver Location
├── driver (indexed)
├── latitude, longitude
├── hailing_status (indexed)
├── timestamp (indexed)
└── is_stale

tabRide Trip
├── ride_request (FK)
├── driver (FK)
├── vehicle (FK)
├── fare_charged
├── customer_rating
├── payment_status
└── mpesa_transaction_id
```

## Real-time Updates

### GPS Tracking

**Driver Side:**
```javascript
// Every 10s when Available
navigator.geolocation.getCurrentPosition()
  → Send to update_driver_location()
  
// Every 5s when En Route  
navigator.geolocation.getCurrentPosition()
  → Send to update_driver_location()
```

**Customer Side:**
```javascript
// Poll every 3s while waiting
setInterval(() => {
  fetch(get_ride_status)
    → If accepted: Show driver info
    → If en route: Show driver location
}, 3000)
```

### Alternative: WebSockets (Future)

For lower latency, can implement Socket.IO:
- Driver location broadcasts
- Ride request notifications
- Real-time status updates

## Performance Considerations

### Optimizations Implemented

1. **Location Privacy Offset**: Reduces GPS precision requirements
2. **Stale Data Cleanup**: Auto-delete old records every 5 minutes
3. **Request Expiration**: 30-second timeout on pending requests
4. **Database Indexes**: On frequently queried fields
5. **Haversine Formula**: Fast distance calculations

### Scaling Recommendations

- **CDN**: Serve map tiles via CDN
- **Redis Cache**: Cache available driver lists
- **Load Balancer**: Multiple ERPNext instances
- **Database Partitioning**: Partition Driver Location by date
- **Rate Limiting**: Prevent API abuse

## Deployment Requirements

### www.sunnytuktuk.com

- ✅ **HTTPS Required** (for geolocation API)
- ✅ **Static File Hosting** (HTML/CSS/JS)
- ✅ **No Database Required**
- ✅ **No Server-Side Code**

Can use: GitHub Pages, Netlify, Cloudflare Pages, or your existing web host.

### console.sunnytuktuk.com

- ✅ **ERPNext 15** installed
- ✅ **HTTPS Required**
- ✅ **Scheduler Enabled**
- ✅ **CORS Configured**
- ✅ **Internet Connectivity**

Typical: VPS or cloud server (DigitalOcean, AWS, etc.)

## Integration Points

### With tuktuk_management App

1. **Payment Processing**: Reuses M-Pesa integration
2. **Daily Targets**: Hailing revenue counts toward target
3. **Driver Records**: Extends TukTuk Driver doctype
4. **Performance Tracking**: Integrates with existing metrics
5. **Transaction Linking**: Each ride creates TukTuk Transaction

### Data Sharing

```python
# When ride completes
create_ride_trip()
  → Creates Ride Trip record (tuktuk_hailing)
  
  → Creates TukTuk Transaction (tuktuk_management)
      • Links to ride_request
      • Applies payment split logic
      • Updates daily target
      
  → Triggers M-Pesa B2C (tuktuk_management)
      • Sends payment to driver
      • Records transaction ID
```

## Monitoring & Maintenance

### Key Metrics

1. **Active Drivers**: Real-time count
2. **Request Conversion**: % of requests accepted
3. **Average Response Time**: Request → Acceptance
4. **Customer Ratings**: Average per driver
5. **Revenue**: Hailing vs. street pickups

### Health Checks

```bash
# Check scheduler
bench --site console.sunnytuktuk.com doctor

# Check location cleanup
SELECT COUNT(*) FROM `tabDriver Location` WHERE is_stale = 1;

# Check pending requests
SELECT COUNT(*) FROM `tabRide Request` WHERE status = 'Pending';

# Check API response
curl -X POST https://console.sunnytuktuk.com/api/method/ping
```

### Log Files

```
~/frappe-bench/logs/
├── web.error.log      # Nginx errors
├── worker.error.log   # Background job errors
├── web.log            # HTTP requests
└── console.log        # Application logs
```

## Future Enhancements

### Phase 2
- Push notifications (web push)
- Mobile apps (React Native)
- Multi-stop rides
- Scheduled pickups
- Corporate accounts

### Phase 3
- Machine learning for demand prediction
- Dynamic pricing (surge)
- Route optimization
- Driver heat maps
- Advanced analytics

## Summary

**Architecture Benefits:**

✅ **Separation of Concerns**: Marketing site separate from operations  
✅ **Security**: Guest endpoints for customers, auth for drivers  
✅ **Scalability**: Static frontend can use CDN, backend scales independently  
✅ **Maintainability**: Clear boundaries between systems  
✅ **Cost-Effective**: Minimal infrastructure requirements  
✅ **User Experience**: Branded customer interface, powerful admin tools  

**This design gives you:**
- Professional customer-facing booking experience on your main website
- Powerful operational tools for drivers and management in ERPNext
- Secure API communication between systems
- Ability to scale each component independently
- Easy maintenance and updates to either side without affecting the other
