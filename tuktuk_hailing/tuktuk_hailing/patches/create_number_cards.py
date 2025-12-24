# ~/frappe-bench/apps/tuktuk_hailing/tuktuk_hailing/tuktuk_hailing/patches/create_number_cards.py

import frappe
from frappe import _

def execute():
    """Create Number Cards for Tuktuk Hailing workspace"""

    cards = [
        {
            "name": "Total Ride Requests",
            "label": "Total Ride Requests",
            "document_type": "Ride Request",
            "function": "Count",
            "filters_json": "[]",
            "color": "Blue",
            "show_percentage_stats": 1,
            "stats_time_interval": "Daily",
            "is_public": 1,
            "is_standard": 1,
            "module": "Tuktuk Hailing"
        },
        {
            "name": "Pending Requests",
            "label": "Pending Requests",
            "document_type": "Ride Request",
            "function": "Count",
            "filters_json": "[[\"Ride Request\", \"status\", \"=\", \"Pending\", false]]",
            "color": "Orange",
            "show_percentage_stats": 1,
            "stats_time_interval": "Daily",
            "is_public": 1,
            "is_standard": 1,
            "module": "Tuktuk Hailing"
        },
        {
            "name": "Active Rides",
            "label": "Active Rides",
            "document_type": "Ride Request",
            "function": "Count",
            "filters_json": "[[\"Ride Request\", \"status\", \"in\", [\"Accepted\", \"En Route\"], false]]",
            "color": "Green",
            "show_percentage_stats": 1,
            "stats_time_interval": "Daily",
            "is_public": 1,
            "is_standard": 1,
            "module": "Tuktuk Hailing"
        },
        {
            "name": "Completed Trips",
            "label": "Completed Trips",
            "document_type": "Ride Trip",
            "function": "Count",
            "filters_json": "[]",
            "color": "Purple",
            "show_percentage_stats": 1,
            "stats_time_interval": "Daily",
            "is_public": 1,
            "is_standard": 1,
            "module": "Tuktuk Hailing"
        }
    ]

    for card_data in cards:
        try:
            # Try to get existing card or create new one
            try:
                card = frappe.get_doc("Number Card", card_data["name"])
            except frappe.DoesNotExistError:
                card = frappe.new_doc("Number Card")
                card.name = card_data["name"]

            # Update card properties
            card.update(card_data)

            # Save the card
            card.save(ignore_permissions=True)
            frappe.db.commit()

            print(f"Created/Updated Number Card: {card_data['name']}")

        except Exception as e:
            print(f"Error creating Number Card {card_data['name']}: {str(e)}")
            frappe.log_error(f"Number Card creation error: {str(e)}", f"Create {card_data['name']}")
