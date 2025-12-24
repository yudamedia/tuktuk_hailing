# Tuktuk Hailing Installation Guide

## Overview

Tuktuk Hailing is a ride-hailing system built for the Sunny Tuktuk fleet management platform. It enables real-time GPS tracking, customer ride requests, driver acceptance, and seamless WhatsApp integration.

## Prerequisites

- ERPNext 15 installed
- tuktuk_management app already installed and configured
- Internet connectivity for drivers and customers
- Modern web browsers with geolocation support
- WhatsApp on driver phones (for customer communication)

## Installation Steps

### 1. Get the App

```bash
cd ~/frappe-bench
bench get-app /path/to/tuktuk_hailing
```

Or if cloning from repository:
```bash
cd ~/frappe-bench
bench get-app https://github.com/your-org/tuktuk_hailing.git
```

### 2. Install on Site

```bash
bench --site sunnytuktuk.com install-app tuktuk_hailing
```

### 3. Run Migrations

```bash
bench --site sunnytuktuk.com migrate
```

### 4. Restart Bench

```bash
bench restart
```

## Post-Installation Configuration

### 1. Configure Hailing Settings

Navigate to: **Tuktuk Hailing > Hailing Settings**

Configure the following:

#### Service Area
- **Service Area Name**: Diani Beach Area (default)
- **Service Area Coordinates**: Define the GeoJSON polygon for your service area

Example coordinates for Diani Beach area:
```json
[[[39.550, -4.300], [39.580, -4.300], [39.580, -4.270], [39.550, -4.270], [39.550, -4.300]]]
```

#### Fare Settings
- **Base Fare**: 50 KSH (default)
- **Per KM Rate**: 40 KSH (default)
- **Minimum Fare**: 100 KSH (default)
- **Surge Pricing**: Enable if desired

#### Location Tracking
- **Update Interval - Available**: 10 seconds (default)
- **Update Interval - En Route**: 5 seconds (default)
- **Stale Location Threshold**: 60 seconds (default)
- **Driver Location Display Radius**: 50 meters (for privacy)

#### Ride Request Settings
- **Request Timeout**: 30 seconds (default)
- **Max Active Requests Per Customer**: 1 (default)
- **Free Cancellation Period**: 60 seconds (default)
- **Cancellation Fee**: 50 KSH (default)

#### Customer Rating Settings
- **Enable Customer Ratings**: Yes
- **Minimum Rating Threshold**: 3.5 (default)
- **Low Rating Warning Count**: 3 (default)

#### WhatsApp Integration (Optional)
- **Enable WhatsApp Business API**: If you have Business API
- **WhatsApp API Token**: Your API token
- **WhatsApp Business Number**: Your business number

#### Map Settings
- **OSM Tile Server URL**: https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png (default)
- **Routing API URL**: https://router.project-osrm.org/route/v1/driving/ (default)
- **Routing API Provider**: OSRM (default)

### 2. Update TukTuk Driver DocType

The tuktuk_hailing app automatically extends the TukTuk Driver doctype with:
- `hailing_status` field (Available/Offline/En Route/Busy)
- `total_hailing_trips` field
- `average_hailing_rating` field

Run this after installation:
```bash
bench --site sunnytuktuk.com execute frappe.reload_doc --args "['tuktuk_management', 'doctype', 'tuktuk_driver']"
```

Or manually add these fields to TukTuk Driver via Customize Form:

1. **Hailing Status** (Select field)
   - Options: Offline, Available, En Route, Busy
   - Default: Offline

2. **Total Hailing Trips** (Int field)
   - Default: 0
   - Read Only

3. **Average Hailing Rating** (Float field)
   - Precision: 2
   - Read Only

### 3. Set Up Scheduled Tasks

The app includes scheduled tasks that run automatically:

- **cleanup_stale_locations**: Runs every 5 minutes
  - Marks old driver locations as stale
  - Deletes location records older than 24 hours

- **expire_old_requests**: Should be added to hooks.py
  - Expires pending ride requests that have timed out

Verify scheduler is running:
```bash
bench --site sunnytuktuk.com doctor
```

Enable scheduler if needed:
```bash
bench --site sunnytuktuk.com enable-scheduler
```

### 4. Configure Web Portal Access

The customer booking page is accessible at:
```
https://sunnytuktuk.com/book
```

This page is guest-accessible (no login required).

To customize the booking page, edit:
`tuktuk_hailing/www/book/index.html`

## Driver Setup

### Enabling Hailing for Drivers

1. Open a TukTuk Driver record
2. Scroll to the "Ride Hailing" dashboard section
3. Click "Go Available" to enable hailing
4. The driver's phone will start sending GPS updates

### Driver Dashboard Features

- **Real-time map** showing driver's location and nearby drivers
- **Availability toggle** (Available/Offline)
- **Pending ride requests** list with distance and fare info
- **Accept/Reject** ride requests
- **Active ride** display with customer contact
- **WhatsApp integration** for customer communication

### Driver Permissions

Ensure drivers have proper permissions:

1. Go to: **User Permission Manager**
2. Add permission for Driver role:
   - **Driver Location**: Create, Read, Write
   - **Ride Request**: Read
   - **Ride Trip**: Read

## Customer Workflow

1. Customer visits: `https://sunnytuktuk.com/book`
2. Browser requests location permission
3. Customer sees available Sunny Tuktuks on map
4. Customer enters:
   - Phone number (must be on WhatsApp)
   - Name (optional)
   - Pickup location
   - Destination
5. System shows estimated fare
6. Customer clicks "Request Sunny Tuktuk"
7. Request sent to all available drivers
8. First driver to accept gets the ride
9. Customer sees driver info and WhatsApp button
10. Customer can track driver's location in real-time
11. After ride, customer receives payment request via M-Pesa
12. Customer receives rating link via WhatsApp/SMS

## Integration with Tuktuk Management

### Payment Integration

When a ride is completed:

1. Driver enters actual fare
2. System creates **Ride Trip** record
3. System creates **TukTuk Transaction** (via tuktuk_management)
4. Payment split logic applies:
   - Before target: 50% to driver, 50% to target
   - After target: 100% to driver
5. M-Pesa B2C payment sent to driver

### Revenue Tracking

Hailing rides contribute to:
- Driver's daily target
- Driver's performance metrics
- Overall fleet revenue

Tag all hailing transactions with `ride_request` link for reporting.

## Testing

### Test Driver Setup

1. Create a test driver
2. Assign a tuktuk
3. Open driver record and go available
4. Verify location updates in Driver Location doctype

### Test Customer Booking

1. Open: `https://sunnytuktuk.com/book`
2. Allow location access
3. Create a test ride request
4. Check if it appears in driver's pending requests
5. Accept from driver dashboard
6. Verify customer sees driver info

### Test Payment Flow

1. Complete a test ride
2. Enter actual fare
3. Verify TukTuk Transaction created
4. Check driver's daily target updated
5. Verify payment split calculation

## Troubleshooting

### Location Not Updating

**Problem**: Driver location not showing on map

**Solutions**:
- Check browser permissions for location access
- Verify driver is "Available" status
- Check console for JavaScript errors
- Verify scheduler is running: `bench doctor`

### Ride Requests Not Appearing

**Problem**: Drivers not seeing ride requests

**Solutions**:
- Check service area configuration
- Verify customer location is within service area
- Check request expiration settings
- Verify real-time event publishing is working

### Map Not Loading

**Problem**: OpenStreetMap tiles not loading

**Solutions**:
- Check internet connectivity
- Verify tile server URL in Hailing Settings
- Try alternative tile server:
  ```
  https://tile.openstreetmap.org/{z}/{x}/{y}.png
  ```
- Check browser console for CORS errors

### WhatsApp Integration Issues

**Problem**: WhatsApp links not working

**Solutions**:
- Verify phone numbers are in international format (+254...)
- Check if WhatsApp is installed on driver/customer phones
- Test WhatsApp link format: `https://wa.me/254712345678`

### Payment Integration Not Working

**Problem**: M-Pesa payments not processing

**Solutions**:
- Verify tuktuk_management M-Pesa configuration
- Check M-Pesa credentials in TukTuk Settings
- Review error logs: `bench logs`
- Test M-Pesa connection separately

## Performance Optimization

### Database Indexing

Add indexes for better query performance:

```sql
-- Index on driver location timestamp
CREATE INDEX idx_driver_location_timestamp 
ON `tabDriver Location` (timestamp DESC);

-- Index on ride request status
CREATE INDEX idx_ride_request_status 
ON `tabRide Request` (status, requested_at DESC);

-- Index on driver location status
CREATE INDEX idx_driver_location_status 
ON `tabDriver Location` (hailing_status, is_stale);
```

### Caching

Enable Redis caching for better performance:

```python
# In site_config.json
{
    "redis_cache": "redis://localhost:6379",
    "redis_queue": "redis://localhost:6379",
    "redis_socketio": "redis://localhost:6379"
}
```

### Location Update Optimization

To reduce server load:
- Increase location update intervals
- Use geofencing to only update when in service area
- Batch location updates when possible

## Security Considerations

1. **API Rate Limiting**: Implement rate limits on public endpoints
2. **Phone Number Verification**: Consider SMS OTP for customer verification
3. **Driver Authentication**: Ensure only authenticated drivers can update locations
4. **Data Privacy**: Driver locations are shown with ~50m radius offset
5. **HTTPS**: Always use HTTPS for location and payment data

## Monitoring

### Key Metrics to Track

1. **Active Drivers**: Count of available drivers
2. **Request Success Rate**: Accepted vs. expired requests
3. **Average Response Time**: Time from request to acceptance
4. **Customer Satisfaction**: Average ratings
5. **Driver Performance**: Acceptance rates, ratings
6. **Revenue**: Total hailing revenue vs. street pickups

### Logging

Check logs for issues:

```bash
# Application logs
bench --site sunnytuktuk.com console
>>> frappe.db.get_value("Error Log", filters={}, order_by="creation desc")

# Bench logs
tail -f ~/frappe-bench/logs/web.error.log
tail -f ~/frappe-bench/logs/worker.error.log
```

## Support

For issues or questions:
- Email: support@sunnytuktuk.com
- GitHub Issues: [repository URL]
- ERPNext Community Forum

## License

MIT License - See license.txt for details
