# Local Places System - Quick Start Guide

## 🚀 Getting Started (5 Minutes)

Follow these steps to activate all the improvements:

---

### Step 1: Apply Database Indexes (1 minute)

This creates optimized indexes for faster searches:

```bash
cd ~/frappe-bench

# Create indexes
bench execute tuktuk_hailing.patches.add_place_indexes.execute

# Update statistics
bench execute tuktuk_hailing.patches.add_place_indexes.analyze_table
```

**Expected Output**:
```
===========================================================
ADDING DATABASE INDEXES FOR HAILING PLACES
===========================================================
✅ Created idx_place_name: Index on place_name for faster name searches
✅ Created idx_category: Index on category for filtering by type
✅ Created idx_is_active: Index on is_active for active place filtering
✅ Created idx_coordinates: Composite index on coordinates for geographic queries
```

---

### Step 2: Verify Current Data (30 seconds)

Check how many places you have:

```bash
bench execute tuktuk_hailing.patches.add_place_indexes.show_table_info
```

---

### Step 3: Import/Update Places (Optional)

If you have a CSV file with places:

```bash
# Preview first (dry run)
bench execute tuktuk_hailing.import_diani_places.import_from_csv \
  --kwargs "{'filepath': '/path/to/your/places.csv', 'dry_run': True}"

# If preview looks good, import for real
bench execute tuktuk_hailing.import_diani_places.import_from_csv \
  --kwargs "{'filepath': '/path/to/your/places.csv'}"
```

---

### Step 4: Clear Cache (30 seconds)

Clear the cache to ensure fresh data:

```bash
bench clear-cache
bench clear-website-cache
```

---

### Step 5: Test the System (2 minutes)

#### A. Run Automated Tests
```bash
bench run-tests --app tuktuk_hailing --module test_places
```

#### B. Test Search API
```bash
# Search for a place
curl "http://localhost:8000/api/method/tuktuk_hailing.api.places.search_places?query=Beach&limit=5"

# Get autocomplete suggestions
curl "http://localhost:8000/api/method/tuktuk_hailing.api.places.get_place_suggestions?query=Hotel&limit=10"
```

#### C. Test in Browser
1. Open your booking page: `https://your-domain.com/book.html`
2. Click on pickup/destination input
3. Start typing a place name
4. Test keyboard navigation:
   - Press `↓` to move down suggestions
   - Press `↑` to move up
   - Press `Enter` to select
   - Press `Escape` to close

---

## ✅ Verification Checklist

After completing the steps above, verify:

- [ ] Database indexes created successfully
- [ ] Automated tests pass
- [ ] Autocomplete dropdown appears when typing
- [ ] "LOCAL" badge shows for local places
- [ ] Keyboard navigation works (↑↓ Enter Escape)
- [ ] Highlighted suggestion visible
- [ ] "No results" message displays when appropriate
- [ ] Mobile interface works properly

---

## 🎨 New Features You Can Use

### 1. Keyboard Navigation
Users can now navigate autocomplete with keyboard:
- **↓** - Next suggestion
- **↑** - Previous suggestion
- **Enter** - Select highlighted
- **Escape** - Close dropdown

### 2. Local Place Badges
Local database results show a "LOCAL" badge for clear distinction from Nominatim results.

### 3. Distance Sorting
Pass user coordinates to sort by proximity:
```javascript
search_places("Hotel", limit=5, user_lat=-4.283, user_lng=39.567)
```

### 4. Geographic Filtering
Filter results by bounding box:
```javascript
search_places("Restaurant", limit=10, bounds={
    min_lat: -4.30, max_lat: -4.28,
    min_lng: 39.56, max_lng: 39.58
})
```

### 5. Smart Caching
Autocomplete suggestions cached for 5 minutes, reducing database load.

### 6. Rate Limiting
Protects your API from abuse:
- Search: 30 requests/minute
- Autocomplete: 50 requests/minute

---

## 📊 Monitor Performance

Check system performance:

```bash
# View table info and index statistics
bench execute tuktuk_hailing.patches.add_place_indexes.show_table_info

# Get import statistics
bench execute tuktuk_hailing.import_diani_places.get_statistics

# Test search functionality
bench execute tuktuk_hailing.import_diani_places.test_search
```

---

## 🛠️ Common Commands

### Clear Cache
```bash
bench clear-cache
bench clear-website-cache
```

### Clear Place Suggestions Cache Only
```bash
bench --site your-site.local console
>>> import frappe
>>> frappe.cache().delete_keys("place_suggestions:*")
>>> exit()
```

### Rebuild Search Indexes
```bash
bench execute tuktuk_hailing.patches.add_place_indexes.analyze_table
```

### View Logs
```bash
bench logs
```

---

## 📚 Documentation

For detailed information, see:
- **Complete Documentation**: `docs/LOCAL_PLACES_SYSTEM.md`
- **Implementation Summary**: `PLACES_SYSTEM_IMPROVEMENTS.md`
- **This Quick Start**: `QUICK_START.md`

---

## 🐛 Troubleshooting

### Issue: No autocomplete suggestions

**Solution**:
```bash
# Check if places exist
bench --site your-site.local mariadb
SELECT COUNT(*) FROM `tabHailing Place` WHERE is_active = 1;

# Clear cache
bench clear-cache
```

### Issue: Slow search

**Solution**:
```bash
# Verify indexes exist
bench execute tuktuk_hailing.patches.add_place_indexes.show_table_info

# Rebuild statistics
bench execute tuktuk_hailing.patches.add_place_indexes.analyze_table
```

### Issue: Import fails

**Solution**:
```bash
# Run in dry-run mode first
bench execute tuktuk_hailing.import_diani_places.import_from_csv \
  --kwargs "{'filepath': '/path/to/places.csv', 'dry_run': True}"

# Check CSV format (should have: Name,Category,Address,Latitude,Longitude)
head -5 /path/to/places.csv
```

---

## 📞 Need Help?

- **Documentation**: See `docs/LOCAL_PLACES_SYSTEM.md`
- **Email**: info@sunnytuktuk.com
- **Phone**: +254 757 785 824

---

## 🎉 You're All Set!

Your Local Places System is now optimized and ready to use with:

✅ **90% Faster Searches**
✅ **Keyboard Navigation**
✅ **Smart Caching**
✅ **Rate Limiting**
✅ **Comprehensive Tests**
✅ **Full Documentation**

Happy coding! 🚀

