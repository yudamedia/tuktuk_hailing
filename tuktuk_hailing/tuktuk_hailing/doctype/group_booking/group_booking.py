# Copyright (c) 2024, Sunny Tuktuk and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now

class GroupBooking(Document):
	def before_insert(self):
		"""Set timestamps before inserting"""
		if not self.requested_at:
			self.requested_at = now()
	
	def validate(self):
		"""Validate group booking"""
		# Calculate tuktuks required based on passengers
		import math
		if self.total_passengers and not self.tuktuks_required:
			self.tuktuks_required = math.ceil(self.total_passengers / 3)
	
	def update_status(self):
		"""Update group booking status based on ride request statuses"""
		if not self.ride_requests:
			return
		
		statuses = [row.status for row in self.ride_requests if row.status]
		
		if not statuses:
			return
		
		# Check if all are accepted
		if all(status in ["Accepted", "En Route", "Completed"] for status in statuses):
			if self.status == "Pending" or self.status == "Partially Accepted":
				self.status = "Fully Accepted"
				if not self.fully_accepted_at:
					self.fully_accepted_at = now()
		
		# Check if at least one is accepted
		elif any(status in ["Accepted", "En Route", "Completed"] for status in statuses):
			if self.status == "Pending":
				self.status = "Partially Accepted"
		
		# Check if all are completed
		if all(status == "Completed" for status in statuses):
			self.status = "Completed"
			if not self.completed_at:
				self.completed_at = now()
		
		# Check if any are cancelled
		if any(status == "Cancelled" for status in statuses):
			# If all are cancelled, mark group as cancelled
			if all(status == "Cancelled" for status in statuses):
				self.status = "Cancelled"
		
		self.save(ignore_permissions=True)

