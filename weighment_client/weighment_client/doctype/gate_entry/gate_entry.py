# Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
# For license information, please see license.txt

from datetime import datetime
import json
import os
import subprocess
import frappe
import cv2
from frappe.client import insert
from frappe.utils.file_manager import get_files_path
from frappe import _
from frappe.core.api.file import create_new_folder
from frappe.model.document import Document
from frappe.frappeclient import FrappeClient, FrappeException
from frappe.utils import get_path
from frappe.utils.data import get_link_to_form

from weighment_client.api import check_item_weight_adjustment_on_weighment, get_api_data_for_entry_data, get_child_table_data, get_combined_document_names, get_extra_delivery_stock_settings, get_item_uom, get_purchase_order_items_data, get_weighment_mandatory_info, insert_document_with_child, delete_document, update_document,submit_document,cancel_document,get_value,get_document_names, update_document_with_child

from weighment_client.weighment_client_utils import fetch_ip_address, generate_photo, play_audio, read_smartcard

class OverAllowanceError(frappe.ValidationError):
	pass

class GateEntry(Document):

	@frappe.whitelist()
	def get_gate_entry_data(self):
		return get_api_data_for_entry_data(self)
	
	@frappe.whitelist()
	def get_branches(self):
		branches = []
		data = frappe.get_all("Branch Table",["branch"])
		for d in data:
			branches.append(d.branch)
		
		return branches
	
	@frappe.whitelist()
	def get_company(self):
		return frappe.db.get_value("Branch Table",{"branch":self.branch},["company"])

	@frappe.whitelist()
	def get_branch_abbr(self):
		return frappe.db.get_value("Branch Table",{"branch":self.branch},["abbr"])

	
	def after_insert(self):
		if not self.url:
			ip = fetch_ip_address()
			self.url = ip
		insert_document_with_child(self)


	def on_trash(self):
		delete_document(self)


	def on_update(self):
		if not self.url:
			ip = fetch_ip_address()
			self.url = ip
		update_document_with_child(self)
		


	def on_cancel(self):
		cancel_document(self)
		if self.card_number:
			card = frappe.get_cached_doc("Card Details",{"card_number":self.card_number})
			card.is_assigned = 0
			card.save()
		

	def on_submit(self):
		if self.card_number:
			card = frappe.get_cached_doc("Card Details",{"card_number":self.card_number})
			card.is_assigned = 1
			card.save()
			
	
	# @frappe.whitelist()
	# def get_branch_data(self):
	# 	branch = get_document_names(
	# 		doctype="Branch",
	# 	)
	# 	return branch
	
	# @frappe.whitelist()
	# def get_branch_abbr(self):
	# 	if not frappe.get_cached_doc("Weighment Profile").get_value("abbr"):
	# 		frappe.throw("Please reselect branch on {}".format(get_link_to_form("Weighment Profile","Weighment Profile")))
	# 	self.abbr = frappe.get_cached_doc("Weighment Profile").get_value("abbr")
	# 	return True


	# @frappe.whitelist()
	# def get_company_name(self,selected_branch):
	# 	value = get_value(
	# 		docname=selected_branch,
	# 		fieldname="company",
	# 		doctype="Branch",
	# 		filters=({"name":selected_branch})
	# 	)
	# 	return value


	# @frappe.whitelist()
	# def get_driver_name(self,selected_driver):
	# 	value = get_value(
	# 		docname=selected_driver,
	# 		fieldname="full_name",
	# 		doctype="Driver",
	# 		filters=({"name":selected_driver})
	# 	)
	# 	return value
	
	# @frappe.whitelist()
	# def get_item_groups(self):

	# 	ig = get_document_names(
	# 		doctype="Item Group",
	# 		filters={"is_group":0},
	# 	)

	# 	return ig

	# @frappe.whitelist()
	# def get_item_groups(self):

	# 	ig = get_combined_document_names(
	# 		doctype="Item Group",
	# 		filters={"is_group":0},
	# 		fields=["name","custom_super_parent_group"],
	# 		field_1="name",
	# 		field_2="custom_super_parent_group"
	# 	)

	# 	return ig
	
	# @frappe.whitelist()
	# def get_transporter(self):
	# 	t = get_combined_document_names(
	# 		doctype="Supplier",
	# 		filters={"is_transporter":1},
	# 		fields=["name","supplier_name"],
	# 		field_1="name",
	# 		field_2="supplier_name"
	# 	)
	# 	return t


	@frappe.whitelist()
	def check_weighment_required_details(self,selected_item_group):
		if selected_item_group and "~" in selected_item_group:
			selected_item_group = selected_item_group.split("~")[0]
		value = get_value(
			docname=selected_item_group,
			fieldname="custom_is_weighment_required",
			doctype="Item Group",
			filters=({"name":selected_item_group})
		)
		return value


	@frappe.whitelist()
	def get_allowed_tolerance(self,selected_item_group):
		if self.entry_type == "Ourword":

			if selected_item_group and "~" in selected_item_group:
				
				selected_item_group = selected_item_group.split("~")[0]
			print("0000000000000000",selected_item_group)
			data = get_child_table_data(
				
				docname=selected_item_group,
				doctype="Item Group",
				child_table_fieldname="custom_plant_wise_tolerance"
			)

			if data:
				for d in data:
					print(d)
					if d.get("branch") == self.branch:
						self.allowed_tolerance = d.get("allowed_tolerance")
						# return d.get("allowed_tolerance")


	# @frappe.whitelist()
	# def get_vehicle_types(self):
	# 	v = get_document_names(
	# 		doctype="Vehicle Type"
	# 	)
	# 	return v


	# @frappe.whitelist()
	# def get_vehicle(self):
	# 	v = get_document_names(
	# 		doctype="Vehicle"
	# 	)
	# 	return v


	# @frappe.whitelist()
	# def get_supplier(self,selected_po):
	# 	value = get_value(
	# 		docname=selected_po,
	# 		fieldname="supplier",
	# 		doctype="Purchase Order",
	# 		filters=({"name":selected_po})
	# 	)
	# 	return value


	# @frappe.whitelist()
	# def get_supplier_name(self,selected_supplier):
	# 	value = get_value(
	# 		docname=selected_supplier,
	# 		fieldname="supplier_name",
	# 		doctype="Supplier",
	# 		filters=({"name":selected_supplier})
	# 	)
	# 	return value

	
	# @frappe.whitelist()
	# def get_transporter(self):
	# 	t = get_combined_document_names(
	# 		doctype="Supplier",
	# 		filters={"is_transporter":1},
	# 		fields=["name","supplier_name"],
	# 		field_1="name",
	# 		field_2="supplier_name"
	# 	)
	# 	return t
	
	# @frappe.whitelist()
	# def get_supplier(self):
	# 	suppliers = get_combined_document_names(
	# 		doctype="Supplier",
	# 		# filters={"is_transporter":0},
	# 		fields=["name","supplier_name"],
	# 		field_1="name",
	# 		field_2="supplier_name"
	# 	)
	# 	# print("suppliers:--->",suppliers)
	# 	return suppliers


	# @frappe.whitelist()
	# def get_transporter_name(self,selected_transporter):
	# 	value = get_value(
	# 		docname=selected_transporter,
	# 		fieldname="supplier_name",
	# 		doctype="Supplier",
	# 		filters=({"name":selected_transporter})
	# 	)
	# 	return value
	

	@frappe.whitelist()
	def get_purchase_orders(self,selected_supplier):
		print("seleced dcsupplier:---->",selected_supplier)
		po = get_document_names(
			doctype="Purchase Order",
			filters={"docstatus":1,"branch":self.branch,"supplier":selected_supplier},
		)
		return po


	# @frappe.whitelist()
	# def get_vehical_drivers(self):
	# 	value = get_combined_document_names(
	# 		doctype="Driver",
	# 		fields=["name","full_name"],
	# 		field_1="name",
	# 		field_2="full_name"
	# 	)
	# 	return value
		
	
	# @frappe.whitelist()
	# def get_po_items(self,selected_po):
	# 	child_data = get_child_table_data(
	# 		docname=selected_po,
	# 		child_table_fieldname="items",
	# 		doctype="Purchase Order",
	# 	)
		
	# 	return child_data


	def before_save(self):
		self.validate_purchase_entry()
		self.validate_extra_delivery_details()
		generate_photo(self)
		self.get_allowed_tolerance(selected_item_group=self.item_group)
		if self.entry_type == "Inward" and self.items:
			item = self.items[0].get("item_code")
			enable_weight_adjustment = check_item_weight_adjustment_on_weighment(item_code=item)["message"]
			if enable_weight_adjustment:
				self.enable_weight_adjustment = 1
		self.update_card_details()
	
	def update_card_details(self):
		if not self.validate_vehicle():
			if not self.card_number and self.is_weighment_required == "Yes":
				if not self.read_card():
					frappe.throw("No Data Found From This Card")
				if not self.validate_card():
					self.card_number = self.read_card()


	def validate_purchase_entry(self):
		item_groups = {}
		weighable_entry = {}
			
		if self.entry_type == "Inward" and not self.items:
			frappe.throw("Fetch Items Data First")
		
		if self.entry_type == "Inward" and self.items:
			a_data = get_weighment_mandatory_info(self)["message"]
			weighment_mandatory_status = None
			ig = None
			for l in a_data:
				for k in self.items:
					if l.get("item_code") == k.get("item_code"):
						print("rrrrrrrrrrrrrrrr",l)
						current_weighment_status = l.get("custom_is_weighment_mandatory")
						item_group = l.get("ig")
					
						if weighment_mandatory_status is None:
							weighment_mandatory_status = current_weighment_status
						elif weighment_mandatory_status != current_weighment_status:
							frappe.throw(
								title="Multiple Found", 
								msg=f"Item {k.get('item_code')} you are trying to add has different weighment statuses."
							)
						if weighable_entry.get(l.get("custom_is_weighment_mandatory")):
							if weighable_entry[l.get("item_code")] and weighable_entry[l.get("item_code")][l.get("custom_is_weighment_mandatory")] != l.get("custom_is_weighment_mandatory"):
								frappe.throw(
									title="Multiple Found", 
									msg=f"Item {k.get('item_code')} you are trying to add has different items where some of items are not weighable"
								)
						if ig is None:
							ig = item_group
						elif ig != item_group:
							frappe.throw(
								title="Multiple Found", 
								msg=f"Item {k.get('item_code')} you are trying to add has different Item group apart from others items."
							)
						if k.item_code and l.get("custom_is_weighment_mandatory") == "Yes":
							k.is_weighable_item = 1
							self.is_weighment_required = "Yes"
						else:
							k.is_weighable_item = 0
							self.is_weighment_required = "No"

	@frappe.whitelist()
	def read_card(self):
		data = read_smartcard()
		get_card_number = frappe.db.get_value("Card Details", {"hex_code": data}, ["card_number"])
		if get_card_number:
			return get_card_number
		else:
			frappe.throw("No data found on the card.")


	def validate_card(self):
		if self.read_card():
			card_number = self.read_card()
			is_assigned = frappe.db.get_value("Card Details",{"card_number":card_number},"is_assigned")
			if is_assigned == 1:
				frappe.throw("This card is already assigned to other")


	def validate_vehicle(self):
		if self.vehicle_owner == "Third Party" and self.vehicle_number:
			data = frappe.db.sql("""select name, vehicle_number 
						from `tabGate Entry` 
						where branch = %s 
						and company = %s 
						and vehicle_number = %s 
						and name != %s
						and docstatus != 2
						and ((is_in_progress = 1 and is_completed = 0) or (is_in_progress = 0 and is_completed = 0)) 
					""",
					(self.branch,self.company,self.vehicle_number,self.name),as_dict=1)
			if data:
				frappe.throw(f"Entered Vehicle Number {self.vehicle_number} is already exist in Gate Entry {get_link_to_form('Gate Entry',data[0].get('name'))} which is not completed yet")
		
		if self.vehicle_owner == "Company Owned" and self.vehicle:
			data = frappe.db.sql("""select name, vehicle
						from `tabGate Entry` 
						where branch = %s 
						and company = %s 
						and vehicle = %s 
						and name != %s
						and docstatus != 2
						and ((is_in_progress = 1 and is_completed = 0) or (is_in_progress = 0 and is_completed = 0)) 
					""",
					(self.branch,self.company,self.vehicle,self.name),as_dict=1)
			if data:
				frappe.throw(f"Selected vehicle {self.vehicle} is already exist in Gate Entry {get_link_to_form('Gate Entry',data[0].get('name'))} which is not completed yet")
	

	def before_update_after_submit(self):
		if self.card_number:
			card = frappe.get_cached_doc("Card Details",self.card_number)
			if self.is_in_progress and not card.is_assigned:
				card.is_assigned = 1
				card.save()
				
			if self.is_completed and card.is_assigned:
				card.is_assigned = 0
				card.save()


	
	@frappe.whitelist()
	def fetch_po_item_details(self):
		items = []
		if self.purchase_orders:
			for d in self.purchase_orders:
				data = get_purchase_order_items_data(branch=self.branch,supplier=self.supplier.split("~")[0],purchase_order=d.purchase_orders)
				items.extend(data["message"])
		self.items = []
		for d in items:
			self.append("items",{
				"item_code":d.get("item_code"),
				"item_name":d.get("item_name"),
				"qty":d.get("qty"),
				"description":d.get("description"),
				"gst_hsn_code":d.get("gst_hsn_code"),
				"item_code":d.get("item_code"),
				"brand":d.get("brand"),
				"is_ineligible_for_itc":d.get("is_ineligible_for_itc"),
				"stock_uom":d.get("stock_uom"),
				"uom":d.get("uom"),
				"conversion_factor":d.get("conversion_factor"),
				"stock_qty":d.get("stock_qty"),
				"actual_received_qty":d.get("received_qty"),
				"rate":d.get("rate"),
				"amount":d.get("amount"),
				"item_tax_template":d.get("item_tax_template"),
				"gst_treatment":d.get("gst_treatment"),
				"rate_company_currency":d.get("base_rate"),
				"amount_company_currency":d.get("base_amount"),
				"weight_per_unit":d.get("weight_per_unit"),
				"weight_uom":d.get("weight_uom"),
				"total_weight":d.get("total_weight"),
				"warehouse":d.get("warehouse"),
				"material_request":d.get("material_request"),
				"material_request_item":d.get("material_request_item"),
				"purchase_order":d.get("parent"),
				# "purchase_order_item":d.get("item_code"),
				"expense_account":d.get("expense_account"),
				"branch":d.get("branch"),
				"cost_center":d.get("cost_center"),


			})
	
	# @frappe.whitelist()
	# def get_item_uom_data(self,filters):
	# 	item = filters.get("item")
	# 	return get_item_uom(item)

	
	def before_submit(self):
		self.validate_extra_delivery_details()

	@frappe.whitelist()
	def validate_extra_delivery_details(self):
		if self.entry_type == "Inward":
			action_msg = frappe._(
				'To allow over receipt / delivery, update "Over Receipt/Delivery Allowance" in Stock Settings or the Item.'
			)
			data = get_extra_delivery_stock_settings(self)["message"]
			
			if data:
				for d in self.items:
					for l in data:
						if d.get("item_code") == l.get("item_code"):
							allowed_extra_percentage = l.get("odr_per")
							allowed_qty = d.get("qty") + d.get("actual_received_qty") + (d.get("qty") * allowed_extra_percentage / 100)

							if allowed_extra_percentage and ((d.accepted_quantity + d.rejected_quantity + d.actual_received_qty) > allowed_qty):
								over_limit_qty = (d.accepted_quantity + d.rejected_quantity + d.actual_received_qty) - allowed_qty
								frappe.throw(
									frappe._(
										"This document is over limit by {0} {1} for item {2}. Are you making another {3} against the same {4}?"
									).format(
										frappe.bold(_("Qty")),
										frappe.bold(over_limit_qty),
										frappe.bold(d.get("item_code")),
										frappe.bold(_("Purchase Receipt")),
										frappe.bold(_("Gate Entry")),
									)
									+ "<br><br>"
									+ action_msg,
									OverAllowanceError,
									title=_("Limit Crossed"),
								)

			if not data:
				for d in self.items:
					if (d.accepted_quantity + d.rejected_quantity + d.actual_received_qty) > d.qty:
						over_limit_qty = (d.accepted_quantity + d.rejected_quantity + d.actual_received_qty) - d.qty
						frappe.throw(
							frappe._(
								"This document is over limit by {0} {1} for item {2}. Are you making another {3} against the same {4}?"
								).format(
									frappe.bold(_("Qty")),
									frappe.bold(over_limit_qty),
									frappe.bold(d.get("item_code")),
									frappe.bold(_("Purchase Receipt")),
									frappe.bold(_("Gate Entry")),
								)
								+ "<br><br>"
								+ action_msg,
								OverAllowanceError,
								title=_("Limit Crossed"),
						)

		
