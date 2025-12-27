# Local Places System Documentation

## Overview

The Local Places System is a comprehensive geocoding solution for Tuktuk Hailing that stores frequently searched locations locally, reducing dependency on external services like Nominatim while providing faster, more accurate results for your service area.

## Table of Contents

1. [Architecture](#architecture)
2. [Features](#features)
3. [Database Structure](#database-structure)
4. [API Endpoints](#api-endpoints)
5. [Frontend Integration](#frontend-integration)
6. [Import System](#import-system)
7. [Performance Optimization](#performance-optimization)
8. [Testing](#testing)
9. [Maintenance](#maintenance)
10. [Troubleshooting](#troubleshooting)

---

## Architecture

### High-Level Design

```
┌─────────────────┐
│  User Interface │
│  (HTML/JS/CSS)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   API Layer     │◄─────┤  Cache Layer │
│  (places.py)    │      │   (Redis)    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Database Layer │◄─────┤   Indexes    │
│ (Hailing Place) │      │  (Optimized) │
└─────────────────┘      └──────────────┘
         │
         ▼
   ┌──────────┐
   │ Nominatim│  (Fallback)
   │  Service │
   └──────────┘
```

### Data Flow

1. **User Input** → Autocomplete suggestions
2. **Local Database Search** → Fast results with caching
3. **Nominatim Fallback** → If no local results found
4. **Result Display** → Shows source (LOCAL badge)

---

## Features

### ✅ Core Features

- **Fast Local Search**: Prioritizes local database over external APIs
- **Smart Matching**: Multiple search strategies (exact, partial, alias, category)
- **Autocomplete**: Real-time suggestions as user types
- **Keyboard Navigation**: Arrow keys, Enter, Escape support
- **Caching**: Redis-based caching for popular queries (5-minute TTL)
- **Distance Sorting**: Results sorted by proximity when user location provided
- **Geographic Bounds**: Filter results by bounding box
- **Rate Limiting**: Protects API from abuse (30 req/min for search, 50 req/min for autocomplete)
- **Fallback System**: Automatically uses Nominatim if no local results

### 🎨 UI Features

- **Visual Indicators**: "LOCAL" badge for local database results
- **Keyboard Shortcuts**:
  - `↓` / `↑` - Navigate suggestions
  - `Enter` - Select highlighted suggestion
  - `Escape` - Close suggestions
- **No Results Message**: Clear feedback when no local places found
- **Mobile Responsive**: Works on all device sizes

---

## Database Structure

### Hailing Place Category

Categorizes places for better organization and filtering.

| Field         | Type        | Description                    |
|---------------|-------------|--------------------------------|
| category_name | Data        | Unique category name (Primary) |
| icon          | Data        | FontAwesome icon class         |
| description   | Small Text  | Category description           |

**Example Categories**:
- 5-star hotel
- Restaurant
- Beach
- Shopping Mall
- Hospital

### Hailing Place

Stores individual place information with coordinates.

| Field       | Type       | Description                          |
|-------------|------------|--------------------------------------|
| place_name  | Data       | Unique place name (Primary)          |
| category    | Link       | Links to Hailing Place Category      |
| latitude    | Float(8)   | Latitude coordinate                  |
| longitude   | Float(8)   | Longitude coordinate                 |
| aliases     | Small Text | Comma-separated alternative names    |
| description | Small Text | Additional place information         |
| is_active   | Check      | Whether place is active (searchable) |

**Indexes** (for performance):
- `idx_place_name`: Place name (prefix 50 chars)
- `idx_category`: Category field
- `idx_is_active`: Active status
- `idx_coordinates`: Composite (lat, lng)

---

## API Endpoints

### 1. Search Places

**Endpoint**: `/api/method/tuktuk_hailing.api.places.search_places`

**Method**: GET

**Parameters**:
| Parameter | Type   | Required | Description                        |
|-----------|--------|----------|------------------------------------|
| query     | string | Yes      | Search term (min 2 characters)     |
| limit     | int    | No       | Max results (default: 5)           |
| user_lat  | float  | No       | User latitude for distance sorting |
| user_lng  | float  | No       | User longitude                     |
| bounds    | object | No       | Geographic bounds filter           |

**Bounds Object**:
```json
{
  "min_lat": -4.35,
  "max_lat": -4.20,
  "min_lng": 39.50,
  "max_lng": 39.65
}
```

**Response**:
```json
{
  "message": {
    "source": "local",
    "results": [
      {
        "place_name": "Diani Beach",
        "display_name": "Diani Beach, Beach, Diani Beach, Kenya",
        "lat": -4.2833,
        "lon": 39.5667,
        "category": "Beach",
        "source": "local",
        "distance_km": 0.45
      }
    ]
  }
}
```

**Rate Limit**: 30 requests per minute per IP

**Example Usage**:
```javascript
const response = await fetch(
  `${API_BASE_URL}/api/method/tuktuk_hailing.api.places.search_places?` +
  `query=Beach&limit=5&user_lat=-4.283&user_lng=39.567`
);
const data = await response.json();
```

### 2. Get Place Suggestions (Autocomplete)

**Endpoint**: `/api/method/tuktuk_hailing.api.places.get_place_suggestions`

**Method**: GET

**Parameters**:
| Parameter | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| query     | string | Yes      | Search term (min 2 characters) |
| limit     | int    | No       | Max suggestions (default: 10)  |

**Response**:
```json
{
  "message": [
    {
      "label": "Diani Beach, Beach, Diani Beach, Kenya",
      "value": "Diani Beach",
      "lat": -4.2833,
      "lon": 39.5667,
      "category": "Beach"
    }
  ]
}
```

**Caching**: Results cached for 5 minutes

**Rate Limit**: 50 requests per minute per IP

**Example Usage**:
```javascript
const response = await fetch(
  `${API_BASE_URL}/api/method/tuktuk_hailing.api.places.get_place_suggestions?` +
  `query=Hotel&limit=10`
);
const data = await response.json();
```

---

## Frontend Integration

### JavaScript Implementation

The booking form automatically integrates local places:

```javascript
// Autocomplete with keyboard navigation
setupAutocomplete();

// Handles user typing
async function handleAutocompleteInput(e, fieldType) {
    const query = e.target.value.trim();
    if (query.length >= 2) {
        await fetchAutocompleteSuggestions(query, fieldType);
    }
}

// Keyboard navigation
function handleAutocompleteKeydown(e, fieldType) {
    if (e.key === 'ArrowDown') {
        navigateAutocomplete(fieldType, 'down');
    } else if (e.key === 'ArrowUp') {
        navigateAutocomplete(fieldType, 'up');
    } else if (e.key === 'Enter') {
        selectHighlightedSuggestion(fieldType);
    }
}
```

### Search Priority

1. **Local Database** (with caching)
2. **Nominatim API** (fallback)

### Visual Feedback

- ✅ "LOCAL" badge for database results
- 🔍 "No results" message with instructions
- ⌨️ Highlighted suggestions during keyboard navigation

---

## Import System

### CSV Import

Import places from CSV file with the following format:

**CSV Format**:
```csv
Name,Category,Address,Latitude,Longitude
Diani Beach Hotel,5-star hotel,Diani Beach Road,-4.2833,39.5667
```

### Import Script

**Location**: `tuktuk_hailing/import_diani_places.py`

**Basic Import**:
```bash
bench execute tuktuk_hailing.import_diani_places.import_from_csv \
  --kwargs "{'filepath': '/path/to/places.csv'}"
```

**Dry Run** (preview without saving):
```bash
bench execute tuktuk_hailing.import_diani_places.import_from_csv \
  --kwargs "{'filepath': '/path/to/places.csv', 'dry_run': True}"
```

### Import Features

- ✅ **Duplicate Detection**: Checks for duplicates before import
- ✅ **Category Creation**: Automatically creates categories
- ✅ **Alias Generation**: Smart alias generation from place names
- ✅ **Update Support**: Updates existing places instead of failing
- ✅ **Progress Reporting**: Shows real-time progress
- ✅ **Error Handling**: Continues on errors, reports at end
- ✅ **Batch Commits**: Commits every 100 records for performance

### Import Statistics

After import, view statistics:
```bash
bench execute tuktuk_hailing.import_diani_places.get_statistics
```

### Test Search

Test the imported data:
```bash
bench execute tuktuk_hailing.import_diani_places.test_search
```

---

## Performance Optimization

### Database Indexes

**Create Indexes**:
```bash
bench execute tuktuk_hailing.patches.add_place_indexes.execute
```

**Analyze Table** (update optimizer statistics):
```bash
bench execute tuktuk_hailing.patches.add_place_indexes.analyze_table
```

**View Table Info**:
```bash
bench execute tuktuk_hailing.patches.add_place_indexes.show_table_info
```

**Remove Indexes** (rollback if needed):
```bash
bench execute tuktuk_hailing.patches.add_place_indexes.drop_indexes
```

### Caching Strategy

**Cache Keys**:
- Autocomplete: `place_suggestions:{query}:{limit}`
- TTL: 300 seconds (5 minutes)
- Backend: Redis

**Clear Cache**:
```python
import frappe
frappe.cache().delete_keys("place_suggestions:*")
```

### Query Optimization

**Search Priority Order**:
1. Exact match (Priority 1)
2. Starts with (Priority 2)
3. Contains (Priority 3)
4. Alias match (Priority 4)
5. Category match (Priority 5)

**Additional Optimizations**:
- Limit query with WHERE clause before sorting
- Use indexes for all WHERE conditions
- Parameterized queries prevent SQL injection
- Rate limiting prevents abuse

---

## Testing

### Run All Tests

```bash
bench run-tests --app tuktuk_hailing --module test_places
```

### Run Specific Test

```bash
bench run-tests --app tuktuk_hailing --module test_places \
  --test test_search_exact_match
```

### Test Coverage

The test suite covers:

- ✅ Exact match search
- ✅ Partial match search
- ✅ Alias-based search
- ✅ Category-based search
- ✅ Case-insensitive search
- ✅ Minimum character validation
- ✅ Inactive place filtering
- ✅ Distance-based sorting
- ✅ Geographic bounds filtering
- ✅ Autocomplete suggestions
- ✅ Special character handling
- ✅ Result limit enforcement
- ✅ Priority ordering
- ✅ Cache functionality
- ✅ DocType validations

### Manual Testing

Test the API directly:
```bash
curl "http://localhost:8000/api/method/tuktuk_hailing.api.places.search_places?query=Beach&limit=5"
```

---

## Maintenance

### Regular Tasks

#### 1. Update Places
```bash
# Import new places or update existing
bench execute tuktuk_hailing.import_diani_places.import_from_csv \
  --kwargs "{'filepath': '/path/to/updated_places.csv'}"
```

#### 2. Clear Cache
```python
import frappe
# Clear all place suggestion cache
frappe.cache().delete_keys("place_suggestions:*")
```

#### 3. Analyze Performance
```bash
# View table statistics
bench execute tuktuk_hailing.patches.add_place_indexes.show_table_info

# Update optimizer statistics
bench execute tuktuk_hailing.patches.add_place_indexes.analyze_table
```

#### 4. Check Data Quality
```bash
# Find places without coordinates
bench --site your-site.local mariadb
SELECT place_name FROM `tabHailing Place` 
WHERE latitude IS NULL OR longitude IS NULL;

# Find inactive places
SELECT COUNT(*) FROM `tabHailing Place` WHERE is_active = 0;

# Find places without categories
SELECT COUNT(*) FROM `tabHailing Place` WHERE category IS NULL;
```

### Backup Strategy

**Backup Places**:
```bash
bench --site your-site.local backup --only "Hailing Place,Hailing Place Category"
```

**Export to CSV**:
```sql
SELECT place_name, category, latitude, longitude, aliases, description
FROM `tabHailing Place`
INTO OUTFILE '/tmp/places_backup.csv'
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n';
```

---

## Troubleshooting

### Common Issues

#### 1. No Search Results

**Symptoms**: Search returns empty results for known places

**Solutions**:
```bash
# Check if places exist
bench --site your-site.local mariadb
SELECT COUNT(*) FROM `tabHailing Place` WHERE is_active = 1;

# Check if specific place exists
SELECT * FROM `tabHailing Place` WHERE place_name LIKE '%Beach%';

# Clear cache
bench --site your-site.local console
>>> import frappe
>>> frappe.cache().delete_keys("place_suggestions:*")
```

#### 2. Slow Search Performance

**Symptoms**: Search takes > 1 second

**Solutions**:
```bash
# Check if indexes exist
bench execute tuktuk_hailing.patches.add_place_indexes.show_table_info

# Create missing indexes
bench execute tuktuk_hailing.patches.add_place_indexes.execute

# Update optimizer statistics
bench execute tuktuk_hailing.patches.add_place_indexes.analyze_table

# Check slow query log
bench --site your-site.local mariadb
SHOW VARIABLES LIKE 'slow_query_log%';
```

#### 3. Import Errors

**Symptoms**: CSV import fails with errors

**Solutions**:
```bash
# Validate CSV format
head -5 /path/to/places.csv

# Check for duplicates
bench execute tuktuk_hailing.import_diani_places.check_duplicates \
  --kwargs "{'filepath': '/path/to/places.csv'}"

# Run in dry-run mode first
bench execute tuktuk_hailing.import_diani_places.import_from_csv \
  --kwargs "{'filepath': '/path/to/places.csv', 'dry_run': True}"

# Check permissions
ls -la /path/to/places.csv
```

#### 4. Autocomplete Not Working

**Symptoms**: No dropdown appears when typing

**Solutions**:
```javascript
// Check browser console for errors
console.log('Testing autocomplete...');

// Check API endpoint
fetch('${API_BASE_URL}/api/method/tuktuk_hailing.api.places.get_place_suggestions?query=test&limit=5')
  .then(r => r.json())
  .then(console.log);

// Verify autocomplete container exists
console.log(document.getElementById('autocomplete-pickup'));
```

#### 5. Rate Limiting Issues

**Symptoms**: "Too Many Requests" errors

**Solutions**:
```python
# Adjust rate limits in places.py
# Change from 30 to higher value:
rate_limit(limit=60, seconds=60)  # 60 requests per minute

# Or disable rate limiting temporarily:
# Comment out the rate_limit() call
```

### Debug Mode

Enable detailed logging:
```python
# In places.py, add at top:
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add debug statements:
logger.debug(f"Search query: {query}")
logger.debug(f"Results found: {len(results)}")
```

### Performance Monitoring

```bash
# Monitor MySQL queries
bench --site your-site.local mariadb
SET GLOBAL general_log = 'ON';
SHOW VARIABLES LIKE 'general_log_file';

# Watch the log
tail -f /path/to/general_log_file

# Disable when done
SET GLOBAL general_log = 'OFF';
```

---

## Best Practices

### 1. Data Management
- ✅ Keep places up-to-date
- ✅ Use meaningful aliases
- ✅ Assign appropriate categories
- ✅ Deactivate instead of deleting
- ✅ Regular data quality checks

### 2. Performance
- ✅ Keep indexes up-to-date
- ✅ Use caching for popular queries
- ✅ Limit result sets appropriately
- ✅ Monitor query performance
- ✅ Regular ANALYZE TABLE

### 3. User Experience
- ✅ Provide clear error messages
- ✅ Show loading states
- ✅ Enable keyboard navigation
- ✅ Display source badges
- ✅ Fallback to Nominatim gracefully

### 4. Security
- ✅ Rate limiting enabled
- ✅ SQL injection prevention
- ✅ Input validation
- ✅ Guest access whitelisting
- ✅ Regular security audits

---

## Future Enhancements

### Planned Features
- 📝 Full-text search with MATCH...AGAINST
- 🗺️ Geofencing support
- 📊 Search analytics and popular places
- 🌐 Multi-language support
- 📱 Mobile app API
- 🔄 Real-time place updates
- 📈 Search relevance scoring
- 🎯 Personalized results

### Contributing

To contribute improvements:
1. Create feature branch
2. Add tests for new features
3. Update documentation
4. Submit pull request

---

## Support

For issues or questions:
- 📧 Email: info@sunnytuktuk.com
- 📱 Phone: +254 757 785 824
- 🐛 GitHub Issues: [Your repo URL]

---

## License

Copyright (c) 2024, Sunny Tuktuk Ltd.
All rights reserved.

---

**Last Updated**: December 27, 2024
**Version**: 1.0.0
**Maintained by**: Sunny Tuktuk Development Team

