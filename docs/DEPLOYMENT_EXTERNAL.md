# External Website Deployment Guide

## Your Setup

- **ERPNext Domain**: `console.sunnytuktuk.com` (backend/admin)
- **Customer Website**: `www.sunnytuktuk.com` (frontend)
- **Customer Booking**: Hosted on www.sunnytuktuk.com, calls APIs on console.sunnytuktuk.com

## Quick Deployment (15 minutes)

### Part 1: Install Backend on ERPNext (5 minutes)

```bash
# SSH into your ERPNext server
cd ~/frappe-bench

# Extract app
tar -xzf tuktuk_hailing.tar.gz -C apps/

# Install on site
bench --site console.sunnytuktuk.com install-app tuktuk_hailing

# Restart
bench restart
```

### Part 2: Configure CORS (3 minutes)

Enable cross-origin requests from your customer website:

```bash
# Edit site config
cd ~/frappe-bench
nano sites/console.sunnytuktuk.com/site_config.json
```

**Add these lines:**

```json
{
  "allow_cors": "https://www.sunnytuktuk.com",
  "cors_allowed_origins": ["https://www.sunnytuktuk.com", "https://sunnytuktuk.com"],
  "ignore_csrf": 1
}
```

**Save and restart:**

```bash
bench restart
```

### Part 3: Configure Hailing Settings (2 minutes)

1. Login to `https://console.sunnytuktuk.com`
2. Go to: **Tuktuk Hailing > Hailing Settings**
3. Set minimum required:
   - Base Fare: 50 KSH
   - Per KM Rate: 40 KSH
   - Minimum Fare: 100 KSH
4. **Save**

### Part 4: Add Fields to TukTuk Driver (2 minutes)

Via **Customize Form**:

1. Open: **TukTuk Driver** doctype
2. Add field: **hailing_status** (Select)
   - Options: `Offline\nAvailable\nEn Route\nBusy`
   - Default: Offline
3. Add field: **total_hailing_trips** (Int, Read Only)
4. Add field: **average_hailing_rating** (Float, Precision: 2, Read Only)
5. **Update**

### Part 5: Deploy Customer Booking Page (3 minutes)

#### On Your Website Server:

1. **Upload** `booking-standalone.html` to www.sunnytuktuk.com
2. **Rename** to `book-ride.html` (or any name you prefer)
3. **Update Line 225** in the HTML file:
   ```javascript
   const API_BASE_URL = 'https://console.sunnytuktuk.com';
   ```
4. **Ensure HTTPS** is enabled on www.sunnytuktuk.com

#### Link from Main Website:

Add navigation link:
```html
<a href="/book-ride.html" class="btn">Book a Ride</a>
```

Or create a button on homepage:
```html
<a href="/book-ride.html" class="cta-button">
    🚖 Book Your Sunny Tuktuk Now
</a>
```

## Testing the Integration

### Test 1: Check CORS

From www.sunnytuktuk.com, open browser console:

```javascript
fetch('https://console.sunnytuktuk.com/api/method/tuktuk_hailing.api.location.get_available_drivers', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({})
})
.then(r => r.json())
.then(d => console.log('CORS Working:', d))
.catch(e => console.error('CORS Failed:', e));
```

**Expected**: See driver data, not CORS error.

### Test 2: Test Driver Dashboard

1. Login to `console.sunnytuktuk.com`
2. Open a TukTuk Driver record
3. Click "Go Available"
4. Allow location access
5. See map with your location

### Test 3: Test Complete Flow

**Customer Side:**
1. Visit `www.sunnytuktuk.com/book-ride.html`
2. Allow location
3. Click map to set pickup/destination
4. See estimated fare
5. Enter phone and click "Request"

**Driver Side:**
1. Should see request appear in dashboard
2. Click "Accept"
3. Get customer WhatsApp number

## Architecture Overview

```
┌─────────────────────────────────┐
│   www.sunnytuktuk.com           │
│   (Customer Website)            │
│                                 │
│   ┌─────────────────────────┐  │
│   │  book-ride.html         │  │
│   │  (Booking Interface)    │  │
│   │                         │  │
│   │  - Map Display          │  │
│   │  - Fare Calculator      │  │
│   │  - Request Form         │  │
│   └────────┬────────────────┘  │
│            │                    │
│            │ HTTPS/CORS         │
└────────────┼────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   console.sunnytuktuk.com       │
│   (ERPNext Backend)             │
│                                 │
│   ┌─────────────────────────┐  │
│   │  Tuktuk Hailing API     │  │
│   │                         │  │
│   │  - Location Tracking    │  │
│   │  - Ride Management      │  │
│   │  - Payment Processing   │  │
│   │  - Driver Dashboard     │  │
│   └─────────────────────────┘  │
└─────────────────────────────────┘
```

## API Endpoints Used by Customer Website

All endpoints at: `https://console.sunnytuktuk.com/api/method/`

**Guest-Accessible (No Login Required):**

1. `tuktuk_hailing.api.location.get_available_drivers`
   - Get all available drivers and locations
   - Used to show tuktuks on map

2. `tuktuk_hailing.api.rides.create_ride_request_public`
   - Create new ride request
   - Called when customer clicks "Request"

3. `tuktuk_hailing.api.rides.get_ride_status`
   - Check status of ride request
   - Used for polling while waiting

4. `tuktuk_hailing.api.rides.cancel_ride_by_customer`
   - Cancel a ride request
   - Requires customer phone verification

**Driver-Only (Login Required):**

5. `tuktuk_hailing.api.location.update_driver_location`
6. `tuktuk_hailing.api.rides.accept_ride_request_by_driver`
7. `tuktuk_hailing.api.rides.complete_ride_by_driver`

## Security Notes

### What's Protected:

✅ **CORS**: Only www.sunnytuktuk.com can make requests  
✅ **Guest Endpoints**: Limited to customer actions only  
✅ **Driver Endpoints**: Require ERPNext authentication  
✅ **Phone Verification**: Customers can only modify their own requests  
✅ **HTTPS**: Geolocation requires secure connection  

### What to Monitor:

- Request rate from customer website
- Failed API attempts
- Invalid phone numbers
- Service area violations

## Customization Options

### Custom Styling

Edit `booking-standalone.html`:

**Change colors:**
```css
/* Line 21 - Main gradient */
background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);

/* Line 71 - Button gradient */
background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
```

**Change logo/header:**
```html
<!-- Line 179 -->
<h1>🌞 Your Company Name</h1>
<p>Your Tagline Here</p>
```

### Custom Map Center

Change default map location (Line 228):

```javascript
// Current: Diani Beach
map = L.map('map').setView([-4.2833, 39.5667], 13);

// Change to your location:
map = L.map('map').setView([YOUR_LAT, YOUR_LNG], ZOOM_LEVEL);
```

### Custom Fare Calculation

If you need different fare logic, update server-side in:
`tuktuk_hailing/doctype/ride_request/ride_request.py`

The client-side estimate (in HTML) is just for UX.

## WordPress Integration (Optional)

If your website is WordPress:

### Method 1: Custom Page Template

1. Create file: `wp-content/themes/your-theme/template-booking.php`
2. Copy contents of `booking-standalone.html`
3. Wrap in WordPress template tags
4. Create page and assign template

### Method 2: Shortcode

Add to `functions.php`:

```php
function sunny_booking_shortcode() {
    return file_get_contents('path/to/booking-standalone.html');
}
add_shortcode('sunny_booking', 'sunny_booking_shortcode');
```

Use in any page: `[sunny_booking]`

### Method 3: Custom Plugin

Create a plugin that:
- Enqueues Leaflet CSS/JS
- Registers custom page
- Handles routing

## Troubleshooting

### CORS Error

**Symptom**: Browser console shows "Access-Control-Allow-Origin" error

**Fix:**
```bash
# Check site config
cat sites/console.sunnytuktuk.com/site_config.json

# Should see:
# "allow_cors": "https://www.sunnytuktuk.com"

# If missing, add it and restart
bench restart
```

### Geolocation Not Working

**Symptom**: Browser doesn't ask for location permission

**Fix:**
- Ensure www.sunnytuktuk.com uses **HTTPS** (required!)
- Check browser settings allow location
- Try in different browser

### Map Not Loading

**Symptom**: Gray box instead of map

**Fix:**
- Check internet connection
- Verify Leaflet JS loaded (check console)
- Try different tile server in booking HTML

### No Drivers Showing

**Symptom**: Map loads but no driver markers

**Fix:**
- Ensure at least one driver is "Available"
- Check driver has location update (recent)
- Verify API call succeeds in console

### Ride Request Fails

**Symptom**: Error when clicking "Request Sunny Tuktuk"

**Fix:**
- Check phone number format (+254...)
- Verify pickup/destination are set
- Check console for API errors
- Ensure service area configured (if using)

## Next Steps

Once basic deployment works:

1. **Test with Real Drivers**: Have 2-3 drivers go available
2. **Test Complete Flow**: Create real ride request end-to-end
3. **Configure Service Area**: Define your operational boundaries
4. **Set Up Payment**: Ensure M-Pesa integration works
5. **Train Staff**: Show drivers how to use dashboard
6. **Soft Launch**: Start with limited hours/area
7. **Monitor**: Watch error logs and performance

## Support Resources

- **Installation Guide**: `INSTALLATION.md`
- **CORS Setup**: `CORS_SETUP.md`
- **Technical Details**: `IMPLEMENTATION_SUMMARY.md`
- **ERPNext Logs**: `bench logs` or `/var/log/nginx/error.log`

## That's It! 🎉

Your cross-domain ride hailing system is ready to deploy!

**Key Points:**
- ✅ Customer website (www) hosts booking interface
- ✅ ERPNext (console) handles all backend logic
- ✅ CORS enables secure communication
- ✅ Drivers use ERPNext dashboard
- ✅ Customers use your branded website
