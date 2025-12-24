# CORS Configuration for External Website Integration

## Overview

Since your customer booking interface will be hosted on **www.sunnytuktuk.com** (external website) and needs to make API calls to **console.sunnytuktuk.com** (ERPNext), you need to configure CORS (Cross-Origin Resource Sharing) to allow these requests.

## Step 1: Enable CORS in ERPNext

### Option A: Site Config (Recommended)

Edit your site's `site_config.json`:

```bash
cd ~/frappe-bench
nano sites/console.sunnytuktuk.com/site_config.json
```

Add these lines:

```json
{
  "allow_cors": "https://www.sunnytuktuk.com",
  "cors_allowed_origins": ["https://www.sunnytuktuk.com"],
  "ignore_csrf": 1
}
```

If you need multiple domains:

```json
{
  "allow_cors": "*",
  "cors_allowed_origins": [
    "https://www.sunnytuktuk.com",
    "https://sunnytuktuk.com",
    "http://localhost:8000"
  ],
  "ignore_csrf": 1
}
```

**Then restart:**

```bash
bench restart
```

### Option B: Nginx Configuration

If Option A doesn't work, configure CORS at the Nginx level:

Edit your Nginx config:

```bash
sudo nano /etc/nginx/conf.d/console.sunnytuktuk.com.conf
```

Add these lines inside the `server` block:

```nginx
location /api/method/tuktuk_hailing {
    # CORS headers
    add_header 'Access-Control-Allow-Origin' 'https://www.sunnytuktuk.com' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
    add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range' always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;

    # Handle preflight requests
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' 'https://www.sunnytuktuk.com';
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
        add_header 'Access-Control-Max-Age' 1728000;
        add_header 'Content-Type' 'text/plain; charset=utf-8';
        add_header 'Content-Length' 0;
        return 204;
    }

    # Proxy pass to Frappe
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Then reload Nginx:**

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Step 2: Update API Endpoints to Allow Guest Access

The following endpoints need to be accessible without authentication (already done in the app):

- `tuktuk_hailing.api.rides.create_ride_request_public` ✓
- `tuktuk_hailing.api.rides.get_ride_status` ✓
- `tuktuk_hailing.api.rides.cancel_ride_by_customer` ✓
- `tuktuk_hailing.api.location.get_available_drivers` (needs update)

### Update Required in location.py

Edit: `tuktuk_hailing/api/location.py`

Change this line:
```python
@frappe.whitelist()
def get_available_drivers(customer_lat=None, customer_lng=None, max_distance_km=None):
```

To:
```python
@frappe.whitelist(allow_guest=True)
def get_available_drivers(customer_lat=None, customer_lng=None, max_distance_km=None):
```

## Step 3: Deploy Booking Interface on Your Website

You have two deployment options:

### Option A: Standalone Page (Recommended)

Host the provided `booking-standalone.html` on your website:

1. **Upload file** to your website hosting
2. **Update API_BASE_URL** in the HTML file (line 225):
   ```javascript
   const API_BASE_URL = 'https://console.sunnytuktuk.com';
   ```
3. **Link** from your main site navigation

Example URL: `https://www.sunnytuktuk.com/book-ride.html`

### Option B: Embedded Widget (iframe)

If you want to embed it in an existing page:

```html
<iframe 
    src="https://www.sunnytuktuk.com/book-ride.html"
    width="100%"
    height="800px"
    frameborder="0"
    style="border-radius: 10px;"
    allow="geolocation">
</iframe>
```

### Option C: Integrated in WordPress/CMS

If using WordPress or another CMS:

1. Create a new page template
2. Copy the HTML content into the template
3. Enqueue Leaflet CSS/JS in your theme
4. Update the API_BASE_URL constant

## Step 4: Testing CORS

### Test from Browser Console

On **www.sunnytuktuk.com**, open browser console and run:

```javascript
fetch('https://console.sunnytuktuk.com/api/method/tuktuk_hailing.api.location.get_available_drivers', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({})
})
.then(r => r.json())
.then(d => console.log('Success:', d))
.catch(e => console.error('CORS Error:', e));
```

**Expected Result**: You should see driver data, not a CORS error.

**If you see CORS error**, check:
- Site config is correct
- Nginx config is applied
- You restarted services

### Test Individual Endpoints

```javascript
// Test ride creation
fetch('https://console.sunnytuktuk.com/api/method/tuktuk_hailing.api.rides.create_ride_request_public', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        customer_phone: '+254712345678',
        pickup_address: 'Test Location',
        pickup_lat: -4.2833,
        pickup_lng: 39.5667,
        destination_address: 'Test Destination',
        dest_lat: -4.2900,
        dest_lng: 39.5700
    })
})
.then(r => r.json())
.then(d => console.log(d));
```

## Step 5: Security Considerations

### Rate Limiting

Add rate limiting to prevent abuse:

```nginx
# In Nginx config
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/method/tuktuk_hailing {
    limit_req zone=api_limit burst=20;
    # ... rest of config
}
```

### API Key Authentication (Optional)

For production, consider adding API key validation:

1. Generate API keys in ERPNext
2. Pass key in request headers
3. Validate on server side

### HTTPS Only

Ensure both domains use HTTPS:
- www.sunnytuktuk.com → HTTPS
- console.sunnytuktuk.com → HTTPS

Geolocation API requires HTTPS!

## Step 6: Update All Documentation

Replace all references in documentation:

**Old:** `sunnytuktuk.com`  
**New:** `console.sunnytuktuk.com`

Files to update:
- INSTALLATION.md
- QUICKSTART.md
- IMPLEMENTATION_SUMMARY.md
- README.md

## Troubleshooting

### CORS Error: "No 'Access-Control-Allow-Origin' header"

**Solution:**
- Check site_config.json has correct origin
- Verify Nginx config if using Option B
- Restart all services: `bench restart && sudo systemctl reload nginx`

### API Returns 403 Forbidden

**Solution:**
- Ensure `allow_guest=True` on API methods
- Check `ignore_csrf: 1` in site_config.json
- Verify method is whitelisted

### Requests Timing Out

**Solution:**
- Check firewall allows traffic between domains
- Verify DNS is resolving correctly
- Test with curl from server:
  ```bash
  curl -X POST https://console.sunnytuktuk.com/api/method/ping
  ```

### Geolocation Not Working

**Solution:**
- Must use HTTPS (browser requirement)
- User must grant permission
- Check browser console for errors

## Alternative: API Gateway

For complex deployments, consider using an API gateway:

**Cloudflare Workers** (Free tier available):
```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const apiUrl = 'https://console.sunnytuktuk.com' + url.pathname
  
  const response = await fetch(apiUrl, {
    method: request.method,
    headers: request.headers,
    body: request.body
  })
  
  const newResponse = new Response(response.body, response)
  newResponse.headers.set('Access-Control-Allow-Origin', 'https://www.sunnytuktuk.com')
  
  return newResponse
}
```

## Summary

**Required Steps:**
1. ✅ Enable CORS in site_config.json
2. ✅ Update API endpoint to allow guest access
3. ✅ Deploy booking HTML on www.sunnytuktuk.com
4. ✅ Update API_BASE_URL in booking HTML
5. ✅ Test CORS with browser console
6. ✅ Ensure HTTPS on both domains

**Your Setup:**
- **Customer Website**: https://www.sunnytuktuk.com (booking interface)
- **ERPNext/API**: https://console.sunnytuktuk.com (backend)
- **Communication**: HTTPS + CORS
- **Authentication**: Guest access for customer endpoints, JWT for driver endpoints

This architecture is secure, scalable, and separates concerns properly!
