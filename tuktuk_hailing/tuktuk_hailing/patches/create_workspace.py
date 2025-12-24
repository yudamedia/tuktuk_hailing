# ~/frappe-bench/apps/tuktuk_hailing/tuktuk_hailing/tuktuk_hailing/patches/create_workspace.py

import frappe
from frappe import _

def execute():
    """Create Tuktuk Hailing workspace"""

    workspace_name = "Tuktuk Hailing"

    # Try to get existing workspace or create new one
    try:
        workspace = frappe.get_doc("Workspace", workspace_name)
    except frappe.DoesNotExistError:
        workspace = frappe.new_doc("Workspace")
        workspace.name = workspace_name

    # Update workspace properties
    workspace.update({
        "label": workspace_name,
        "category": "Modules",
        "extends": "",
        "module": "Tuktuk Hailing",
        "icon": "ride",
        "is_standard": 1,
        "public": 1,
        "title": workspace_name,
        "sequence_id": "2.0",
        "charts": [
            {
                "chart_name": "Total Ride Requests",
                "label": "Total Ride Requests"
            },
            {
                "chart_name": "Pending Requests",
                "label": "Pending Requests"
            },
            {
                "chart_name": "Active Rides",
                "label": "Active Rides"
            },
            {
                "chart_name": "Completed Trips",
                "label": "Completed Trips"
            }
        ],
        "shortcuts": [
            {
                "type": "DocType",
                "link_to": "Ride Request",
                "label": "Total Ride Requests",
                "color": "blue",
                "stats_filter": "{}"
            },
            {
                "type": "DocType",
                "link_to": "Ride Request",
                "label": "Pending Requests",
                "color": "orange",
                "stats_filter": "{\"status\": \"Pending\"}"
            },
            {
                "type": "DocType",
                "link_to": "Ride Request",
                "label": "Active Rides",
                "color": "green",
                "stats_filter": "{\"status\": [\"in\", [\"Accepted\", \"En Route\"]]}"
            },
            {
                "type": "DocType",
                "link_to": "Ride Trip",
                "label": "Completed Trips",
                "color": "purple",
                "stats_filter": "{}"
            }
        ],
        "links": [
            {
                "label": "Operations",
                "type": "Card Break",
                "hidden": 0,
                "items": [
                    {
                        "type": "doctype",
                        "name": "Ride Request",
                        "label": "Ride Request"
                    },
                    {
                        "type": "doctype",
                        "name": "Ride Trip",
                        "label": "Ride Trip"
                    },
                    {
                        "type": "doctype",
                        "name": "Driver Location",
                        "label": "Driver Location"
                    }
                ]
            },
            {
                "label": "Settings",
                "type": "Card Break",
                "hidden": 0,
                "items": [
                    {
                        "type": "doctype",
                        "name": "Hailing Settings",
                        "label": "Hailing Settings"
                    }
                ]
            }
        ]
    })

    # Save the workspace
    workspace.save(ignore_permissions=True)
    frappe.db.commit()
