# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

from frappe import _

def get_data():
    return [
        {
            "label": _("Ride Hailing"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Hailing Settings",
                    "label": _("Hailing Settings"),
                    "description": _("Configure ride hailing system settings")
                },
                {
                    "type": "doctype",
                    "name": "Ride Request",
                    "label": _("Ride Requests"),
                    "description": _("View and manage ride requests")
                },
                {
                    "type": "doctype",
                    "name": "Ride Trip",
                    "label": _("Ride Trips"),
                    "description": _("Completed rides and ratings")
                },
                {
                    "type": "doctype",
                    "name": "Driver Location",
                    "label": _("Driver Locations"),
                    "description": _("Real-time driver GPS tracking")
                }
            ]
        },
        {
            "label": _("Customer Portal"),
            "items": [
                {
                    "type": "page",
                    "name": "book",
                    "label": _("Book a Ride"),
                    "description": _("Customer ride booking interface")
                }
            ]
        }
    ]
