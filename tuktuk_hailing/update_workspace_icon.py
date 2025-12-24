#!/usr/bin/env python3
"""
Script to update the Tuktuk Hailing workspace icon
Run this from the frappe-bench directory: bench execute tuktuk_hailing.update_workspace_icon.update_icon
"""

import frappe

def update_icon():
    """Update the Tuktuk Hailing workspace icon"""
    try:
        # Get the workspace
        workspace = frappe.get_doc("Workspace", "Tuktuk Hailing")

        # Update the icon (you can change this to any icon/emoji you prefer)
        workspace.icon = "ride"

        # Save the changes
        workspace.save()

        print("Successfully updated Tuktuk Hailing workspace icon")

        # Commit the changes
        frappe.db.commit()

    except frappe.DoesNotExistError:
        print("Tuktuk Hailing workspace not found")
    except Exception as e:
        print(f"Error updating workspace icon: {str(e)}")
        frappe.log_error(f"Workspace icon update error: {str(e)}")

if __name__ == "__main__":
    update_icon()
