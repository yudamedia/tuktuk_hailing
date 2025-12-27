#!/usr/bin/env python3
"""
Import places from Diani_Galu.csv into ERPNext

Usage:
1. Upload CSV to server
2. Run: bench execute tuktuk_hailing.import_diani_places.import_from_csv --kwargs "{'filepath': '/path/to/Diani_Galu.csv'}"
"""

import frappe
import csv
import os

def import_from_csv(filepath, dry_run=False):
    """
    Import places from Diani_Galu.csv
    
    CSV Format:
    Name,Category,Address,Latitude,Longitude
    
    Args:
        filepath: Path to CSV file
        dry_run: If True, preview changes without saving to database
    """
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be saved to database")
        print("=" * 60)
    
    # Check for duplicates in CSV first
    if not check_duplicates(filepath):
        response = input("\n⚠️  Duplicates found. Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Import cancelled.")
            return
    
    # First, create all unique categories
    create_categories(filepath, dry_run)
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\n📥 Starting import from: {filepath}")
    print("=" * 60)
    
    with open(filepath, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for index, row in enumerate(reader, start=1):
            try:
                name = row['Name'].strip()
                category = row['Category'].strip() if row['Category'].strip() else None
                latitude = row['Latitude'].strip()
                longitude = row['Longitude'].strip()
                address = row.get('Address', '').strip()
                
                # Skip if no coordinates
                if not latitude or not longitude:
                    print(f"⚠️  Skipping {name}: Missing coordinates")
                    skipped_count += 1
                    continue
                
                # Convert coordinates
                try:
                    lat = float(latitude)
                    lng = float(longitude)
                except ValueError:
                    print(f"⚠️  Skipping {name}: Invalid coordinates")
                    skipped_count += 1
                    continue
                
                # Clean up the name (remove quotes and extra spaces)
                name = name.replace('"', '').strip()
                
                # Generate aliases from name variations
                aliases = generate_aliases(name, category)
                
                # Check if place already exists
                existing = frappe.db.exists("Hailing Place", name)
                
                if existing:
                    # Update existing place
                    if dry_run:
                        print(f"🔄 Would update: {name} ({category}) - {lat}, {lng}")
                        updated_count += 1
                    else:
                        place = frappe.get_doc("Hailing Place", name)
                        place.category = category
                        place.latitude = lat
                        place.longitude = lng
                        if address:
                            place.description = address
                        if aliases:
                            place.aliases = aliases
                        place.save(ignore_permissions=True)
                        updated_count += 1
                        
                        if updated_count % 50 == 0:
                            print(f"🔄 Updated {updated_count} places...")
                else:
                    # Create new place
                    if dry_run:
                        print(f"✅ Would create: {name} ({category}) - {lat}, {lng}")
                        created_count += 1
                    else:
                        place = frappe.get_doc({
                            "doctype": "Hailing Place",
                            "place_name": name,
                            "category": category,
                            "latitude": lat,
                            "longitude": lng,
                            "aliases": aliases,
                            "description": address if address else None,
                            "is_active": 1
                        })
                        
                        place.insert(ignore_permissions=True)
                        created_count += 1
                        
                        if created_count % 50 == 0:
                            print(f"✅ Created {created_count} places...")
                
                # Commit every 100 records
                if not dry_run and (created_count + updated_count) % 100 == 0:
                    frappe.db.commit()
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error importing row {index} ({row.get('Name', 'unknown')}): {str(e)}")
                continue
    
    # Final commit
    if not dry_run:
        frappe.db.commit()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 IMPORT SUMMARY")
    print("=" * 60)
    print(f"✅ Created:  {created_count}")
    print(f"🔄 Updated:  {updated_count}")
    print(f"⚠️  Skipped:  {skipped_count}")
    print(f"❌ Errors:   {error_count}")
    print(f"📍 Total:    {created_count + updated_count}")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY RUN - No changes were saved to database")
        print("Run without dry_run=True to actually import the data\n")
    else:
        print("✨ Import complete!\n")

def create_categories(filepath, dry_run=False):
    """
    Extract unique categories from CSV and create Category records
    
    Args:
        filepath: Path to CSV file
        dry_run: If True, preview without saving
    """
    
    categories = set()
    
    with open(filepath, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            category = row['Category'].strip()
            if category and category not in ['Kenya', 'Diani']:  # Skip non-category values
                categories.add(category)
    
    created_categories = 0
    
    for category in sorted(categories):
        if not frappe.db.exists("Hailing Place Category", category):
            if dry_run:
                print(f"📁 Would create category: {category}")
                created_categories += 1
            else:
                try:
                    cat_doc = frappe.get_doc({
                        "doctype": "Hailing Place Category",
                        "category_name": category,
                        "icon": get_category_icon(category)
                    })
                    cat_doc.insert(ignore_permissions=True)
                    created_categories += 1
                except Exception as e:
                    print(f"Warning: Could not create category '{category}': {str(e)}")
    
    if created_categories > 0:
        if not dry_run:
            frappe.db.commit()
        print(f"📁 {'Would create' if dry_run else 'Created'} {created_categories} categories")

def check_duplicates(filepath):
    """
    Check for duplicate entries in CSV before import
    
    Args:
        filepath: Path to CSV file
    
    Returns:
        bool: True if no duplicates, False if duplicates found
    """
    
    names = []
    duplicates = []
    
    with open(filepath, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row['Name'].strip().replace('"', '').strip()
            if name in names:
                duplicates.append(name)
            names.append(name)
    
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} duplicate entries in CSV:")
        for dup in set(duplicates):
            count = duplicates.count(dup)
            print(f"  • {dup} (appears {count + 1} times)")
        return False
    
    print("✅ No duplicates found in CSV")
    return True

def generate_aliases(name, category):
    """
    Generate search aliases for a place
    """
    aliases = []
    
    # Add category as alias
    if category:
        aliases.append(category)
    
    # Extract keywords from name
    # Remove common words
    common_words = ['hotel', 'resort', 'beach', 'villa', 'house', 'restaurant', 
                    'cafe', 'bar', 'grill', 'the', 'and', 'at', 'in']
    
    words = name.lower().split()
    keywords = [w for w in words if w not in common_words and len(w) > 2]
    
    # Add significant words as aliases
    for keyword in keywords[:3]:  # Max 3 keywords
        if keyword not in aliases:
            aliases.append(keyword.capitalize())
    
    return ", ".join(aliases) if aliases else None

def get_category_icon(category):
    """
    Map category to FontAwesome icon
    """
    
    icon_map = {
        # Hotels & Accommodation
        '5-star hotel': 'fa-hotel',
        '4-star hotel': 'fa-hotel',
        '3-star hotel': 'fa-hotel',
        '2-star hotel': 'fa-hotel',
        'Hotel': 'fa-bed',
        'Resort hotel': 'fa-umbrella-beach',
        'Bed & breakfast': 'fa-bed',
        'Guest house': 'fa-home',
        'Villa': 'fa-home',
        'Cottage': 'fa-home',
        'Holiday home': 'fa-home',
        'Lodge': 'fa-home',
        
        # Food & Dining
        'Restaurant': 'fa-utensils',
        'Seafood': 'fa-fish',
        'Grill': 'fa-fire',
        'Barbecue': 'fa-fire',
        'Italian': 'fa-pizza-slice',
        'African': 'fa-utensils',
        'Western': 'fa-utensils',
        
        # Beach & Nature
        'Beach': 'fa-umbrella-beach',
        
        # Services
        'Vacation home rental agency': 'fa-key',
        'Holiday apartment rental': 'fa-key',
        'Travel agency': 'fa-plane',
    }
    
    return icon_map.get(category, 'fa-map-marker-alt')

def test_search():
    """
    Test the search functionality after import
    """
    
    test_queries = [
        'Diani Beach',
        'Hotel',
        'Restaurant',
        'Baobab',
        'Villa'
    ]
    
    print("\n🔍 TESTING SEARCH FUNCTIONALITY")
    print("=" * 60)
    
    for query in test_queries:
        results = frappe.db.sql("""
            SELECT place_name, category, latitude, longitude
            FROM `tabHailing Place`
            WHERE 
                is_active = 1
                AND (
                    LOWER(place_name) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
                    OR LOWER(IFNULL(aliases, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
                    OR LOWER(IFNULL(category, '')) LIKE LOWER(CONCAT('%%', %(query)s, '%%'))
                )
            LIMIT 5
        """, {'query': query}, as_dict=True)
        
        print(f"\nQuery: '{query}' - Found {len(results)} results")
        for r in results:
            print(f"  • {r.place_name} ({r.category})")
    
    print("\n" + "=" * 60)

def get_statistics():
    """
    Get statistics about imported places
    """
    
    total = frappe.db.count("Hailing Place")
    
    category_stats = frappe.db.sql("""
        SELECT category, COUNT(*) as count
        FROM `tabHailing Place`
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)
    
    print("\n📊 DATABASE STATISTICS")
    print("=" * 60)
    print(f"Total Places: {total}")
    print("\nTop 10 Categories:")
    for stat in category_stats:
        print(f"  • {stat.category}: {stat.count}")
    print("=" * 60)