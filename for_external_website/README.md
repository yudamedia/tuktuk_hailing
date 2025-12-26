# External Website Booking Template - Integration Guide

## Overview

This template (`template.html`) is designed to be hosted on your external website (https://www.sunnytuktuk.com) and integrates with your ERPNext backend at https://console.sunnytuktuk.com.

## How It Integrates with Hailing Settings

### 1. **Settings Loaded on Page Load**

When the page loads, the template automatically fetches configuration from the **Hailing Settings** doctype:

```javascript
loadHailingSettings() → GET /api/method/tuktuk_hailing.tuktuk_hailing.doctype.hailing_settings.hailing_settings.get_hailing_settings
```

**Settings Retrieved:**
- `base_fare` - Base fare for all rides (default: 50 KSH)
- `per_km_rate` - Rate per kilometer (default: 40 KSH)
- `minimum_fare` - Minimum charge regardless of distance (default: 100 KSH)
- `osm_tile_server` - OpenStreetMap tile server URL for map display
- `service_area_coordinates` - GeoJSON polygon defining service boundary
- `location_update_interval_available` - GPS update frequency for available drivers
- `show_driver_radius_meters` - Privacy radius for driver location display

### 2. **Dynamic Fare Calculation**

The `calculateFare()` function uses settings from the backend:

```javascript
const baseFare = hailingSettings.base_fare || 50;
const perKm = hailingSettings.per_km_rate || 40;
const minimumFare = hailingSettings.minimum_fare || 100;
const estimatedFare = Math.max(minimumFare, baseFare + (distance * perKm));
```

**Formula:** `Fare = max(minimum_fare, base_fare + (distance × per_km_rate))`

### 3. **Service Area Geofencing**

When a customer clicks on the map to set pickup or destination:

1. Template checks if coordinates are within `service_area_coordinates` polygon
2. Uses **point-in-polygon ray-casting algorithm**
3. Rejects locations outside service area with error message
4. Service area boundary is displayed on map as dashed orange polygon

**Functions:**
- `isInServiceArea(lat, lng)` - Validates coordinates
- `drawServiceArea()` - Renders polygon on map

### 4. **Map Tile Server**

The map uses the tile server specified in Hailing Settings:

```javascript
L.tileLayer(hailingSettings.osm_tile_server, {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);
```

**Default:** `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`

Can be changed in Hailing Settings to use custom tile server.

### 5. **Available Drivers Display**

Loads and displays available drivers on the map:

```javascript
GET /api/method/tuktuk_hailing.api.location.get_available_drivers
```

Shows yellow markers for each available Sunny Tuktuk with approximate location (privacy radius applied by backend).

---

## API Endpoints Used

### 1. **Get Hailing Settings**
```
POST /api/method/tuktuk_hailing.tuktuk_hailing.doctype.hailing_settings.hailing_settings.get_hailing_settings
```
**Guest Access:** Yes  
**Purpose:** Load system configuration  
**Response:**
```json
{
  "message": {
    "base_fare": 50,
    "per_km_rate": 40,
    "minimum_fare": 100,
    "service_area_coordinates": "[[[39.5,4.2],[39.6,-4.3],...]]",
    "osm_tile_server": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    ...
  }
}
```

### 2. **Get Available Drivers**
```
POST /api/method/tuktuk_hailing.api.location.get_available_drivers
```
**Guest Access:** Yes  
**Purpose:** Show available tuktuks on map  
**Response:**
```json
{
  "message": [
    {
      "driver": "DRV-001",
      "driver_name": "John Doe",
      "display_latitude": -4.2833,
      "display_longitude": 39.5667,
      "vehicle": "TT-001"
    }
  ]
}
```

### 3. **Create Ride Request**
```
POST /api/method/tuktuk_hailing.api.rides.create_ride_request_public
```
**Guest Access:** Yes  
**Purpose:** Customer creates a ride request  
**Payload:**
```json
{
  "customer_phone": "+254712345678",
  "customer_name": "Jane Customer",
  "pickup_address": "-4.2833, 39.5667",
  "pickup_lat": -4.2833,
  "pickup_lng": 39.5667,
  "destination_address": "-4.2900, 39.5700",
  "dest_lat": -4.2900,
  "dest_lng": 39.5700
}
```
**Response:**
```json
{
  "message": {
    "success": true,
    "request_id": "RR-00001"
  }
}
```

### 4. **Get Ride Status (Polling)**
```
POST /api/method/tuktuk_hailing.api.rides.get_ride_status
```
**Guest Access:** Yes  
**Purpose:** Check if driver accepted (polls every 3 seconds)  
**Payload:**
```json
{
  "request_id": "RR-00001",
  "customer_phone": "+254712345678"
}
```
**Response:**
```json
{
  "message": {
    "success": true,
    "status": "Accepted",
    "driver_name": "John Doe",
    "driver_phone": "+254712345679",
    "vehicle_id": "TT-001",
    "driver_photo": "/files/driver-photo.jpg"
  }
}
```

---

## Configuration Requirements

### 1. **CORS Setup (site_config.json)**

Your ERPNext site must allow requests from your website:

```json
{
  "allow_cors": "https://www.sunnytuktuk.com",
  "cors_allowed_origins": ["https://www.sunnytuktuk.com"],
  "ignore_csrf": 1
}
```

**Important:** After changing `site_config.json`, restart your site:
```bash
bench --site sunnytuktuk.com restart
```

### 2. **API Base URL**

Update line 193 in `template.html`:

```javascript
const API_BASE_URL = 'https://console.sunnytuktuk.com';
```

Change this to your actual ERPNext domain.

### 3. **Hailing Settings Configuration**

In ERPNext, navigate to:  
**Tuktuk Hailing > Hailing Settings**

Configure:
- ✅ **Service Area Coordinates** - Define GeoJSON polygon boundary
- ✅ **Base Fare** - Starting fare (KSH)
- ✅ **Per KM Rate** - Rate per kilometer (KSH)
- ✅ **Minimum Fare** - Lowest possible charge (KSH)
- ✅ **OSM Tile Server** - Map tile server URL
- ✅ **Request Timeout** - How long requests stay active
- ✅ **Location Update Intervals** - GPS update frequency

---

## Service Area Configuration

### How to Define Service Area

1. Go to **Hailing Settings** in ERPNext
2. Find a GeoJSON tool like http://geojson.io
3. Draw a polygon around your service area (Diani Beach)
4. Copy the coordinates array
5. Paste into **Service Area Coordinates** field

**Format:**
```json
[
  [
    [39.5500, -4.2500],
    [39.6000, -4.2500],
    [39.6000, -4.3000],
    [39.5500, -4.3000],
    [39.5500, -4.2500]
  ]
]
```

**Notes:**
- Coordinates are `[longitude, latitude]` format
- First and last coordinate must be identical (closed polygon)
- Minimum 4 points (3 unique + 1 closing)

---

## Workflow Integration

### Customer Booking Flow

1. **Customer visits** → `https://www.sunnytuktuk.com/book.html`
2. **Page loads settings** → Fetches Hailing Settings from API
3. **Service area displayed** → Orange dashed polygon shown on map
4. **Available drivers loaded** → Yellow markers on map
5. **Customer sets location** → Clicks map for pickup/destination
6. **Validation** → Template checks if within service area
7. **Fare calculated** → Uses settings (base_fare + distance × per_km_rate)
8. **Request submitted** → Creates Ride Request via API
9. **Polling starts** → Checks status every 3 seconds
10. **Driver accepts** → Shows driver info and WhatsApp button

### Backend Processing

1. **Ride Request created** → `create_ride_request_public()` in rides.py
2. **Service area validated** → Backend double-checks using `is_location_in_service_area()`
3. **Fare calculated** → Backend calculates using Haversine + settings
4. **Broadcast to drivers** → All available drivers notified
5. **Driver accepts** → First to accept gets the ride
6. **Status updated** → Customer sees driver details
7. **Real-time tracking** → Driver location updated every 5 seconds
8. **Completion** → Payment and rating flows triggered

---

## Testing Checklist

### Before Going Live

- [ ] Update `API_BASE_URL` to your ERPNext domain
- [ ] Configure CORS in `site_config.json`
- [ ] Restart ERPNext site after CORS changes
- [ ] Set **Hailing Settings** with correct fares
- [ ] Define **Service Area** polygon coordinates
- [ ] Test from external domain (not localhost)
- [ ] Verify fare calculation matches settings
- [ ] Test service area boundary (inside/outside)
- [ ] Confirm driver markers appear on map
- [ ] Test ride request creation
- [ ] Test status polling (wait for driver)
- [ ] Verify WhatsApp link works with driver phone

### Test Scenarios

**Scenario 1: Normal Booking**
1. Open booking page
2. Allow location access
3. Set pickup and destination within service area
4. Verify fare calculation
5. Submit ride request
6. Wait for driver acceptance
7. Verify driver info displayed
8. Test WhatsApp link

**Scenario 2: Outside Service Area**
1. Try to set pickup outside defined polygon
2. Should show error: "Sorry, this location is outside our service area"
3. Same for destination

**Scenario 3: Fare Adjustment**
1. Change fares in Hailing Settings
2. Reload booking page
3. Set pickup/destination
4. Verify new fare is calculated correctly

**Scenario 4: No Available Drivers**
1. Ensure all drivers are offline
2. Submit ride request
3. Should timeout and show "Expired" message

---

## Troubleshooting

### Issue: Settings not loading

**Symptoms:** Map shows default fares, service area not displayed

**Solutions:**
1. Check browser console for API errors
2. Verify CORS configuration in `site_config.json`
3. Ensure `get_hailing_settings()` method has `@frappe.whitelist()` decorator
4. Check if Hailing Settings record exists in ERPNext
5. Verify API_BASE_URL is correct

### Issue: Service area validation not working

**Symptoms:** Can select locations outside boundary

**Solutions:**
1. Check if `service_area_coordinates` is valid GeoJSON
2. Verify coordinates are in `[longitude, latitude]` format
3. Ensure polygon is closed (first = last coordinate)
4. Check browser console for JavaScript errors

### Issue: CORS errors

**Symptoms:** `Access to fetch blocked by CORS policy` in console

**Solutions:**
1. Add your domain to `site_config.json`
2. Restart site: `bench --site sunnytuktuk.com restart`
3. Clear browser cache
4. Verify domain matches exactly (https vs http)

### Issue: Fare calculation wrong

**Symptoms:** Displayed fare doesn't match expected amount

**Solutions:**
1. Check Hailing Settings values in ERPNext
2. Verify settings loaded in browser console: `console.log(hailingSettings)`
3. Test distance calculation with known coordinates
4. Ensure minimum fare is not overriding calculation

---

## Customization Options

### 1. **Change Map Style**

Edit the tile server URL in Hailing Settings:

**Carto Light:**
```
https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png
```

**Carto Dark:**
```
https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png
```

### 2. **Adjust Service Area Color**

In template.html, find `drawServiceArea()` function:

```javascript
serviceAreaPolygon = L.polygon(leafletCoords, {
    color: '#f39c12',        // Border color
    fillColor: '#f39c12',    // Fill color
    fillOpacity: 0.1,        // Transparency
    weight: 2,               // Border width
    dashArray: '5, 10'       // Dash pattern
});
```

### 3. **Change Driver Marker Colors**

In `loadAvailableDrivers()` function:

```javascript
iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-yellow.png'
```

Available colors: red, blue, green, yellow, violet, grey, black, orange

---

## Security Considerations

1. **Phone Number Verification** - Customer phone must match for status checks
2. **Service Area Enforcement** - Both frontend and backend validate boundaries
3. **Guest API Rate Limiting** - Consider adding rate limits to prevent abuse
4. **CORS Restrictions** - Only allow your specific domain, not wildcard
5. **No Sensitive Data** - Driver exact locations are offset for privacy

---

## Performance Tips

1. **CDN for Assets** - Host CSS/JS on CDN for faster loading
2. **Image Optimization** - Compress logo and driver photos
3. **Lazy Load Maps** - Map loads after page render
4. **API Caching** - Settings cached for session duration
5. **Minimize Polling** - Status checked every 3 seconds (not more frequent)

---

## Support

For issues or questions:
- **Email:** info@sunnytuktuk.com
- **Phone:** +254 757 785 824
- **ERPNext Logs:** Check Error Log in ERPNext for backend issues

---

## Version History

- **v1.0** (2024-12-26) - Initial external website template with Hailing Settings integration
  - Dynamic fare calculation from settings
  - Service area geofencing
  - Real-time driver availability
  - WhatsApp integration

