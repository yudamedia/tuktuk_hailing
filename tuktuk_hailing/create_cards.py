#!/usr/bin/env python3
"""
Utility script to create/update individual number cards for Tuktuk Hailing workspace
Run from frappe-bench directory:
  bench execute tuktuk_hailing.create_cards.create_all_cards
  bench execute tuktuk_hailing.create_cards.create_total_ride_requests_card
  bench execute tuktuk_hailing.create_cards.create_pending_requests_card
  bench execute tuktuk_hailing.create_cards.create_active_rides_card
  bench execute tuktuk_hailing.create_cards.create_completed_trips_card
"""

import frappe
from frappe import _

def create_card(card_data):
    """Helper function to create or update a number card"""
    try:
        # Try to get existing card or create new one
        try:
            card = frappe.get_doc("Number Card", card_data["name"])
            print(f"Updating existing Number Card: {card_data['name']}")
        except frappe.DoesNotExistError:
            card = frappe.new_doc("Number Card")
            card.name = card_data["name"]
            print(f"Creating new Number Card: {card_data['name']}")

        # Update card properties
        card.update(card_data)

        # Save the card
        card.save(ignore_permissions=True)
        frappe.db.commit()

        print(f"Successfully created/updated: {card_data['name']}")
        return True

    except Exception as e:
        print(f"Error creating Number Card {card_data['name']}: {str(e)}")
        frappe.log_error(f"Number Card creation error: {str(e)}", f"Create {card_data['name']}")
        return False


def create_total_ride_requests_card():
    """Create Total Ride Requests number card"""
    card_data = {
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
    }
    return create_card(card_data)


def create_pending_requests_card():
    """Create Pending Requests number card"""
    card_data = {
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
    }
    return create_card(card_data)


def create_active_rides_card():
    """Create Active Rides number card"""
    card_data = {
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
    }
    return create_card(card_data)


def create_completed_trips_card():
    """Create Completed Trips number card"""
    card_data = {
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
    return create_card(card_data)


def create_all_cards():
    """Create all number cards for Tuktuk Hailing"""
    print("Creating all Tuktuk Hailing Number Cards...")
    print("=" * 50)

    cards = [
        create_total_ride_requests_card,
        create_pending_requests_card,
        create_active_rides_card,
        create_completed_trips_card
    ]

    success_count = 0
    for create_func in cards:
        if create_func():
            success_count += 1
        print("-" * 50)

    print(f"\nCompleted: {success_count}/{len(cards)} cards created/updated successfully")


if __name__ == "__main__":
    create_all_cards()
