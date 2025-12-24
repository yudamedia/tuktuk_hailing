# Tuktuk Hailing Workspace Setup Guide

This guide explains the workspace and number cards created for the Tuktuk Hailing app.

## Overview

The Tuktuk Hailing workspace includes:
- 4 Number Cards displaying key metrics
- Organized links to all doctypes
- Shortcuts for quick access to filtered views

## Files Created

### 1. Number Cards Patch
**File:** `tuktuk_hailing/tuktuk_hailing/patches/create_number_cards.py`

Creates 4 number cards:
- **Total Ride Requests** (Blue) - Count of all ride requests
- **Pending Requests** (Orange) - Count of requests with status "Pending"
- **Active Rides** (Green) - Count of requests with status "Accepted" or "En Route"
- **Completed Trips** (Purple) - Count of all completed trips

### 2. Workspace Patch
**File:** `tuktuk_hailing/tuktuk_hailing/patches/create_workspace.py`

Creates the Tuktuk Hailing workspace with:
- Reference to the 4 number cards in the charts section
- Shortcuts for quick filtering
- Organized links in sections (Operations, Settings)

### 3. Utility Scripts
**Files:**
- `tuktuk_hailing/create_cards.py` - Standalone utility to create/update individual cards
- `tuktuk_hailing/update_workspace_icon.py` - Update workspace icon

### 4. Patches Registry
**File:** `tuktuk_hailing/patches.txt`

Registers the patches to run during migration.

## Installation

### Option 1: Run Migration (Recommended)

This will run all patches including number cards and workspace creation:

```bash
bench migrate
```

### Option 2: Run Individual Patches

Create number cards only:
```bash
bench execute tuktuk_hailing.tuktuk_hailing.patches.create_number_cards.execute
```

Create workspace only:
```bash
bench execute tuktuk_hailing.tuktuk_hailing.patches.create_workspace.execute
```

### Option 3: Use Utility Script

Create all cards at once:
```bash
bench execute tuktuk_hailing.create_cards.create_all_cards
```

Or create individual cards:
```bash
bench execute tuktuk_hailing.create_cards.create_total_ride_requests_card
bench execute tuktuk_hailing.create_cards.create_pending_requests_card
bench execute tuktuk_hailing.create_cards.create_active_rides_card
bench execute tuktuk_hailing.create_cards.create_completed_trips_card
```

## Number Cards Details

### 1. Total Ride Requests
- **Color:** Blue
- **DocType:** Ride Request
- **Filter:** None (shows all)
- **Shows:** Total count of all ride requests with daily percentage change

### 2. Pending Requests
- **Color:** Orange
- **DocType:** Ride Request
- **Filter:** Status = "Pending"
- **Shows:** Count of requests waiting to be accepted with daily percentage change

### 3. Active Rides
- **Color:** Green
- **DocType:** Ride Request
- **Filter:** Status in ["Accepted", "En Route"]
- **Shows:** Count of currently active rides with daily percentage change

### 4. Completed Trips
- **Color:** Purple
- **DocType:** Ride Trip
- **Filter:** None (shows all)
- **Shows:** Total count of completed trips with daily percentage change

## Customization

### Changing Card Colors

Edit the card creation functions in `create_cards.py` or `create_number_cards.py`:

Available colors: Blue, Green, Red, Orange, Purple, Yellow, Pink, Cyan, Grey

```python
"color": "Blue"  # Change to your preferred color
```

### Changing Filters

Edit the `filters_json` field:

```python
# Example: Show only completed rides with payment status "Paid"
"filters_json": "[[\"Ride Trip\", \"payment_status\", \"=\", \"Paid\", false]]"
```

### Changing Time Interval

Edit the `stats_time_interval` field:

Available options: Daily, Weekly, Monthly, Yearly

```python
"stats_time_interval": "Daily"  # Change to Weekly, Monthly, or Yearly
```

## Accessing the Workspace

1. After running the patches, refresh your browser
2. Click on the "Tuktuk Hailing" module in the sidebar
3. You should see the workspace with all 4 number cards at the top
4. Below the cards, you'll find organized links to:
   - **Operations:** Ride Request, Ride Trip, Driver Location
   - **Settings:** Hailing Settings

## Troubleshooting

### Cards not showing up

1. Make sure you've run the migration or patches
2. Clear cache: `bench clear-cache`
3. Reload the page in your browser

### Permission errors

Make sure you're running the commands with appropriate permissions. The patches use `ignore_permissions=True` to ensure they run successfully.

### Cards showing zero

This is normal if you don't have any data yet. Create some Ride Requests and Ride Trips to see the counts.

## Next Steps

1. Run `bench migrate` to create the workspace and cards
2. Navigate to the Tuktuk Hailing workspace
3. Create some test Ride Requests to see the cards update
4. Customize colors and filters as needed
5. Consider adding more number cards for other metrics (e.g., "Cancelled Requests", "Paid Trips", etc.)
