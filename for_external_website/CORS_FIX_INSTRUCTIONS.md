# URGENT: Fix CORS Errors on Your Live Website

## The Problem

Your booking page at `https://www.sunnytuktuk.com/book.html` cannot communicate with your ERPNext backend at `https://console.sunnytuktuk.com` because CORS (Cross-Origin Resource Sharing) is not configured.

**Browser Error:**
```
Access to fetch at 'https://console.sunnytuktuk.com/api/method/...' from origin 
'https://sunnytuktuk.com' has been blocked by CORS policy
```

## The Solution

You need to configure your ERPNext server to accept requests from your website. Note that the browser is reporting the origin as `https://sunnytuktuk.com` (without www), so we'll configure both domains.

---

## Step 1: Configure CORS on ERPNext Server

**SSH into your ERPNext server** (where console.sunnytuktuk.com is hosted) and follow these steps:

### 1.1 Edit the Site Configuration File

```bash
cd ~/frappe-bench
nano sites/console.sunnytuktuk.com/site_config.json
```

### 1.2 Add CORS Configuration

Add these lines to your `site_config.json` file. If the file already has other configuration, just add these entries:

```json
{
  "allow_cors": "*",
  "cors_allowed_origins": [
    "https://www.sunnytuktuk.com",
    "https://sunnytuktuk.com"
  ],
  "ignore_csrf": 1
}
```

**Important Notes:**
- Include BOTH `https://www.sunnytuktuk.com` AND `https://sunnytuktuk.com` (with and without www)
- Do NOT include trailing slashes
- Do NOT remove any existing configuration - just add these lines
- Set `ignore_csrf: 1` to allow public API access

### 1.3 Save the File

Press `Ctrl + O` to save, then `Ctrl + X` to exit

### 1.4 Restart Your Site

```bash
bench restart
```

This should take 10-20 seconds. Wait for the restart to complete.

---

## Step 2: Verify CORS is Working

### 2.1 Open Your Booking Page

Go to: `https://www.sunnytuktuk.com/book.html`

### 2.2 Open Browser Console

- **Chrome/Edge**: Press `F12` or `Ctrl+Shift+I`
- **Firefox**: Press `F12` or `Ctrl+Shift+K`
- **Safari**: Enable Developer Menu, then press `Cmd+Option+I`

### 2.3 Run This Test

Copy and paste this code into the console:

```javascript
fetch('https://console.sunnytuktuk.com/api/method/tuktuk_hailing.tuktuk_hailing.doctype.hailing_settings.hailing_settings.get_hailing_settings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({})
})
.then(r => r.json())
.then(d => console.log('✅ SUCCESS! Settings loaded:', d))
.catch(e => console.error('❌ STILL BLOCKED:', e));
```

**Expected Result:** You should see `✅ SUCCESS!` with your hailing settings data.

**If you still see CORS errors**, continue to Step 3.

---

## Step 3: Alternative Fix (If Step 1 Doesn't Work)

If the site config approach doesn't work, you may need to configure CORS at the Nginx level.

### 3.1 Find Your Nginx Configuration

```bash
# List Nginx config files
ls -la /etc/nginx/sites-enabled/
```

Look for a file like `console.sunnytuktuk.com` or `frappe-bench-frappe`.

### 3.2 Edit the Nginx Configuration

```bash
sudo nano /etc/nginx/sites-enabled/console.sunnytuktuk.com
```

### 3.3 Add CORS Headers

Find the `server` block for `console.sunnytuktuk.com` and add this location block:

```nginx
server {
    # ... existing configuration ...

    # Add this location block for API endpoints
    location /api/method/tuktuk_hailing {
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '$http_origin' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
            add_header 'Access-Control-Max-Age' 1728000 always;
            add_header 'Content-Type' 'text/plain; charset=utf-8' always;
            add_header 'Content-Length' 0 always;
            return 204;
        }

        # Add CORS headers to all responses
        add_header 'Access-Control-Allow-Origin' '$http_origin' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;

        # Proxy to Frappe
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ... rest of existing configuration ...
}
```

### 3.4 Test and Reload Nginx

```bash
# Test configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx
```

### 3.5 Restart Frappe

```bash
cd ~/frappe-bench
bench restart
```

---

## Step 4: Fix the Missing CSS File

You also have a missing `booking.css` file. 

### Option A: Upload the CSS File

I've created a `booking.css` file in the `for_external_website` folder. Upload this file to your website at:

```
https://www.sunnytuktuk.com/css/booking.css
```

Make sure the folder structure on your website matches:
```
www.sunnytuktuk.com/
├── book.html
└── css/
    └── booking.css
```

### Option B: Use a CDN or Inline Styles

If you don't want to manage a separate CSS file, you can inline the styles in the HTML file. Let me know if you need help with this.

---

## Step 5: Configure www vs non-www Redirect

The browser is showing the origin as `sunnytuktuk.com` (without www), but you're accessing `www.sunnytuktuk.com`. This suggests your website might be redirecting between them.

### Recommended: Set Up a Permanent Redirect

Choose ONE primary domain and redirect the other to it. Most people choose `www` as primary.

**If using cPanel:**
1. Go to Domains → Redirects
2. Redirect `sunnytuktuk.com` → `https://www.sunnytuktuk.com`
3. Select "Permanent (301)"

**If using Nginx:**
```nginx
server {
    server_name sunnytuktuk.com;
    return 301 https://www.sunnytuktuk.com$request_uri;
}
```

---

## Quick Checklist

After completing the steps above, verify:

- [ ] `site_config.json` has CORS configuration
- [ ] ERPNext site restarted (`bench restart`)
- [ ] Browser console test shows `✅ SUCCESS!`
- [ ] `booking.css` file is accessible at `https://www.sunnytuktuk.com/css/booking.css`
- [ ] Map loads on the booking page
- [ ] No CORS errors in browser console
- [ ] Can click map to set pickup/destination
- [ ] Fare estimate calculates correctly

---

## Still Having Issues?

If you're still experiencing problems after following these steps:

1. **Check if both domains use HTTPS** - Mixed content (HTTP/HTTPS) will be blocked
2. **Clear your browser cache** - Old CORS errors can be cached
3. **Check firewall rules** - Ensure traffic between domains is allowed
4. **Verify DNS** - Make sure both domains resolve correctly

Run this from your ERPNext server:

```bash
# Test if API is reachable
curl -X POST https://console.sunnytuktuk.com/api/method/tuktuk_hailing.api.location.get_available_drivers \
  -H "Content-Type: application/json" \
  -d '{}'

# Should return JSON, not an HTML error page
```

---

## Summary

**The main issue is:** CORS is not configured on your ERPNext backend.

**The solution is:** Add CORS configuration to `site_config.json` and restart your site.

**Expected time:** 5-10 minutes to complete all steps.

After fixing CORS, your booking page will work perfectly! 🚀

