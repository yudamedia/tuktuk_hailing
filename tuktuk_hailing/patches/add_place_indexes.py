#!/usr/bin/env python3
"""
Database Index Migration for Hailing Place

This script adds performance indexes to the Hailing Place table
for faster search queries.

Usage:
    bench execute tuktuk_hailing.patches.add_place_indexes.execute
"""

import frappe

def execute():
    """
    Add indexes to Hailing Place table for better query performance
    """
    
    print("\n" + "=" * 60)
    print("ADDING DATABASE INDEXES FOR HAILING PLACES")
    print("=" * 60)
    
    indexes = [
        {
            'name': 'idx_place_name',
            'sql': 'ALTER TABLE `tabHailing Place` ADD INDEX idx_place_name (place_name(50))',
            'check': "SELECT COUNT(*) as cnt FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'tabHailing Place' AND index_name = 'idx_place_name'",
            'description': 'Index on place_name for faster name searches'
        },
        {
            'name': 'idx_category',
            'sql': 'ALTER TABLE `tabHailing Place` ADD INDEX idx_category (category)',
            'check': "SELECT COUNT(*) as cnt FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'tabHailing Place' AND index_name = 'idx_category'",
            'description': 'Index on category for filtering by type'
        },
        {
            'name': 'idx_is_active',
            'sql': 'ALTER TABLE `tabHailing Place` ADD INDEX idx_is_active (is_active)',
            'check': "SELECT COUNT(*) as cnt FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'tabHailing Place' AND index_name = 'idx_is_active'",
            'description': 'Index on is_active for active place filtering'
        },
        {
            'name': 'idx_coordinates',
            'sql': 'ALTER TABLE `tabHailing Place` ADD INDEX idx_coordinates (latitude, longitude)',
            'check': "SELECT COUNT(*) as cnt FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'tabHailing Place' AND index_name = 'idx_coordinates'",
            'description': 'Composite index on coordinates for geographic queries'
        }
    ]
    
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    for index in indexes:
        try:
            # Check if index already exists
            result = frappe.db.sql(index['check'], as_dict=True)
            
            if result and result[0]['cnt'] > 0:
                print(f"⏭️  Skipping {index['name']}: Already exists")
                skipped_count += 1
                continue
            
            # Create the index
            frappe.db.sql(index['sql'])
            print(f"✅ Created {index['name']}: {index['description']}")
            added_count += 1
            
        except Exception as e:
            print(f"❌ Error creating {index['name']}: {str(e)}")
            error_count += 1
    
    # Commit changes
    frappe.db.commit()
    
    # Print summary
    print("\n" + "=" * 60)
    print("INDEX MIGRATION SUMMARY")
    print("=" * 60)
    print(f"✅ Added:   {added_count}")
    print(f"⏭️  Skipped: {skipped_count}")
    print(f"❌ Errors:  {error_count}")
    print("=" * 60)
    
    if added_count > 0:
        print("✨ Indexes created successfully!")
        print("💡 Run ANALYZE TABLE to update statistics:")
        print("   bench execute tuktuk_hailing.patches.add_place_indexes.analyze_table")
    else:
        print("ℹ️  All indexes already exist")
    
    print()

def analyze_table():
    """
    Analyze the Hailing Place table to update query optimizer statistics
    """
    
    print("\n" + "=" * 60)
    print("ANALYZING HAILING PLACE TABLE")
    print("=" * 60)
    
    try:
        frappe.db.sql("ANALYZE TABLE `tabHailing Place`")
        print("✅ Table analysis complete")
        print("💡 Query optimizer statistics have been updated")
        
        # Show index statistics
        stats = frappe.db.sql("""
            SELECT 
                INDEX_NAME,
                COLUMN_NAME,
                SEQ_IN_INDEX,
                CARDINALITY
            FROM information_schema.STATISTICS
            WHERE table_schema = DATABASE()
            AND table_name = 'tabHailing Place'
            AND INDEX_NAME != 'PRIMARY'
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """, as_dict=True)
        
        if stats:
            print("\n📊 Index Statistics:")
            print("-" * 60)
            current_index = None
            for stat in stats:
                if stat.INDEX_NAME != current_index:
                    if current_index:
                        print()
                    print(f"Index: {stat.INDEX_NAME}")
                    current_index = stat.INDEX_NAME
                print(f"  • {stat.COLUMN_NAME} (Cardinality: {stat.CARDINALITY or 'N/A'})")
        
    except Exception as e:
        print(f"❌ Error analyzing table: {str(e)}")
    
    print("=" * 60 + "\n")

def drop_indexes():
    """
    Remove all custom indexes (for rollback if needed)
    
    ⚠️  WARNING: Only use this if you need to rollback the migration
    """
    
    print("\n⚠️  WARNING: This will remove all custom indexes!")
    print("=" * 60)
    
    indexes_to_drop = ['idx_place_name', 'idx_category', 'idx_is_active', 'idx_coordinates']
    
    dropped_count = 0
    
    for index_name in indexes_to_drop:
        try:
            # Check if index exists
            check = frappe.db.sql(f"""
                SELECT COUNT(*) as cnt 
                FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = 'tabHailing Place' 
                AND index_name = '{index_name}'
            """, as_dict=True)
            
            if check and check[0]['cnt'] > 0:
                frappe.db.sql(f"ALTER TABLE `tabHailing Place` DROP INDEX {index_name}")
                print(f"🗑️  Dropped index: {index_name}")
                dropped_count += 1
            
        except Exception as e:
            print(f"❌ Error dropping {index_name}: {str(e)}")
    
    frappe.db.commit()
    
    print("=" * 60)
    print(f"Dropped {dropped_count} indexes")
    print("=" * 60 + "\n")

def show_table_info():
    """
    Display information about the Hailing Place table
    """
    
    print("\n" + "=" * 60)
    print("HAILING PLACE TABLE INFORMATION")
    print("=" * 60)
    
    # Get row count
    count = frappe.db.sql("SELECT COUNT(*) as cnt FROM `tabHailing Place`", as_dict=True)
    print(f"\n📊 Total Places: {count[0]['cnt'] if count else 0}")
    
    # Get active count
    active = frappe.db.sql("SELECT COUNT(*) as cnt FROM `tabHailing Place` WHERE is_active = 1", as_dict=True)
    print(f"✅ Active Places: {active[0]['cnt'] if active else 0}")
    
    # Get category breakdown
    categories = frappe.db.sql("""
        SELECT category, COUNT(*) as cnt
        FROM `tabHailing Place`
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT 10
    """, as_dict=True)
    
    if categories:
        print("\n📁 Top 10 Categories:")
        for cat in categories:
            print(f"  • {cat.category}: {cat.cnt}")
    
    # Show indexes
    indexes = frappe.db.sql("""
        SELECT DISTINCT INDEX_NAME
        FROM information_schema.STATISTICS
        WHERE table_schema = DATABASE()
        AND table_name = 'tabHailing Place'
        ORDER BY INDEX_NAME
    """, as_dict=True)
    
    if indexes:
        print("\n🔍 Current Indexes:")
        for idx in indexes:
            print(f"  • {idx.INDEX_NAME}")
    
    # Show table size
    size = frappe.db.sql("""
        SELECT 
            ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
        FROM information_schema.TABLES
        WHERE table_schema = DATABASE()
        AND table_name = 'tabHailing Place'
    """, as_dict=True)
    
    if size:
        print(f"\n💾 Table Size: {size[0]['size_mb']} MB")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    # For direct execution
    execute()

