# Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
# For license information, please see license.txt

import json
import warnings
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import get_link_to_form
import requests
from weighment_client.api import (
	check_item_weight_adjustment_on_weighment, 
	get_api_data_for_entry_data, 
	get_child_table_data, 
	get_extra_delivery_stock_settings,
	get_purchase_order_items_data,
	get_stock_entry_item_data,
	get_subcontracting_order_items_data, 
	get_weighment_mandatory_info, 
	insert_document_with_child, 
	delete_document,
	cancel_document,
	get_value,
	get_document_names, 
	update_document_with_child,
	validate_gate_entry_velicle
)

from weighment_client.weighment_client_utils import (
    fetch_ip_address, 
    generate_photo,
    play_audio, 
    read_smartcard
)
class OverAllowanceError(frappe.ValidationError):
	pass

class GateEntry(Document):
	warnings.filterwarnings("ignore", category=DeprecationWarning)

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

		if not get_value(doctype=self.doctype,docname=self.name,fieldname="name"):
			print("test json:----",self.as_json())
			insert_document_with_child(self)


	def on_trash(self):
		if not frappe.db.get_single_value("Weighment Profile","enable_maintanance_mode"):
			frappe.throw("Not allowed to perform this action, Maintanance mode disabled on {}".format(get_link_to_form("Weighment Profile","Weighment Profile")))
		delete_document(self)


	def on_update(self):
		if not self.url:
			ip = fetch_ip_address()
			self.url = ip
		update_document_with_child(self)		


	def on_cancel(self):
		# if not frappe.db.get_single_value("Weighment Profile","enable_maintanance_mode"):
		# 	frappe.throw("Not allowed to perform this action, Maintanance mode disabled on {}".format(get_link_to_form("Weighment Profile","Weighment Profile")))
		if get_value(
			doctype="Gate Entry",
			docname=self.name,
			fieldname="docstatus",
			filters=({"name":self.name})
		) == 1:
			cancel_document(self)
		# if self.card_number:
		# 	card = frappe.get_cached_doc("Card Details",{"card_number":self.card_number})
		# 	card.is_assigned = 0
		# 	card.save()
		

	# def on_submit(self):
	# 	if self.card_number:
			# card = frappe.get_cached_doc("Card Details",{"card_number":self.card_number})
			# card.is_assigned = 1
			# card.save()
		
		# create_submitable_gate_entry(self)
		
		

	@frappe.whitelist()
	def check_weighment_required_details(self,selected_item_group):
		if selected_item_group and "~" in selected_item_group:
			selected_item_group = selected_item_group.split("~")[0]
		
		print("item_group",selected_item_group)
		value = get_value(
			docname=selected_item_group,
			fieldname="custom_is_weighment_required",
			doctype="Item Group",
			filters=({"name":selected_item_group})
		)
		if value == "Yes":
			print("*******************************")
			self.is_weighment_required = "Yes"
		else:
			self.is_weighment_required = "No"

	@frappe.whitelist()
	def get_purchase_orders(self,selected_supplier):
		po = get_document_names(
			doctype="Purchase Order",
			filters={"docstatus":1,"branch":self.branch,"supplier":selected_supplier,"per_received":["<",100]},
		)
		if po and not self.purchase_orders:
			for d in po:
				self.append("purchase_orders",{
					"purchase_orders":d
				})
		return po
	
	@frappe.whitelist()
	def get_subcontracting_orders(self,selected_supplier):
		po = get_document_names(
			doctype="Subcontracting Order",
			filters={"docstatus":1,"branch":self.branch,"supplier":selected_supplier},
		)
		

		return po
	
	@frappe.whitelist()
	def get_stock_entrys(self,selected_supplier):
		se = get_document_names(
			doctype="Stock Entry",
			filters={
				"docstatus":1,
				"company":self.company,
				"supplier":selected_supplier,
				"stock_entry_type":"Send to Subcontractor",
				"custom_job_work_challan":1,
				"add_to_transit":1
				},
		)
		if se and not self.stock_entrys:
			for d in se:
				self.append("stock_entrys",{
					"stock_entry":d
				})
		return se
	

	def before_save(self):
		self.location = frappe.db.get_single_value(doctype="Weighment Profile",fieldname="location")
		self.validate_purchase_entry()
		self.validate_extra_delivery_details()
		generate_photo(self)
		# self.get_allowed_tolerance(selected_item_group=self.item_group)
		if self.entry_type == "Outward" and not self.is_manual_weighment and not self.job_work and not self.is_subcontracting_order:
			self.check_weighment_required_details(selected_item_group=self.item_group)

		if self.job_work:
			if not self.stock_entry_details:
				frappe.throw("Fetch stock entry data first")

			self.is_weighment_required = "Yes" if self.job_work_weighment_required == "Yes" else "No"
			print("weighment required:--->",self.is_weighment_required,self.job_work_weighment_required)
			
		if self.entry_type == "Inward" and self.items and not self.is_manual_weighment and not self.is_subcontracting_order and not self.job_work:
			for d in self.items:
				item = d.get("item_code")
				enable_weight_adjustment = check_item_weight_adjustment_on_weighment(item_code=item)
				if enable_weight_adjustment and "message" in enable_weight_adjustment:
					enable_weight_adjustment = enable_weight_adjustment["message"]
					if enable_weight_adjustment:
						self.enable_weight_adjustment = 1
			if self.enable_weight_adjustment and len(self.items) >= 2:
				frappe.throw(f"Not allow to add more than two items")
		self.update_card_details()
	
	def update_card_details(self):
		if not self.validate_vehicle():
			if not self.card_number and (self.is_weighment_required == "Yes" or (self.is_manual_weighment and not self.job_work)):
				if not self.read_card():
					frappe.throw("No Data Found From This Card")
				if not self.validate_card():
					self.card_number = self.read_card()


	def validate_purchase_entry(self):
		item_groups = {}
		weighable_entry = {}
			
		if self.entry_type == "Inward" and not self.items and not self.is_manual_weighment and not self.is_subcontracting_order and not self.job_work:
			frappe.throw("Fetch Items Data First")
		
		if self.entry_type == "Inward" and not self.subcontracting_details and not self.is_manual_weighment and self.is_subcontracting_order and not self.job_work:
			frappe.throw("Fetch Subcontracting Item Data First")
		
		if self.entry_type == "Inward" and self.items and not self.is_manual_weighment and not self.job_work and not self.is_subcontracting_order:
			a_data = get_weighment_mandatory_info(self)["message"]
			weighment_mandatory_status = None
			ig = None
			for l in a_data:
				for k in self.items:
					if l.get("item_code") == k.get("item_code"):
						current_weighment_status = l.get("custom_is_weighment_mandatory")
						item_group = l.get("ig")
					
						if weighment_mandatory_status is None:
							weighment_mandatory_status = current_weighment_status
						elif weighment_mandatory_status != current_weighment_status:
							frappe.msgprint(
								title="Multiple Found", 
								msg=f"Item {k.get('item_code')} you are trying to add has different weighment statuses."
							)
						if weighable_entry.get(l.get("custom_is_weighment_mandatory")):
							if weighable_entry[l.get("item_code")] and weighable_entry[l.get("item_code")][l.get("custom_is_weighment_mandatory")] != l.get("custom_is_weighment_mandatory"):
								frappe.msgprint(
									title="Multiple Found", 
									msg=f"Item {k.get('item_code')} you are trying to add has different items where some of items are not weighable"
								)
						if ig is None:
							ig = item_group
						elif ig != item_group:
							frappe.msgprint(
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
			is_assigned = get_value(
				docname=card_number,
				doctype="Card Details",
				filters=({"card_number":card_number}),
				fieldname="is_assigned"
			)
			
			if is_assigned == 1:
				frappe.throw("This card is already assigned to other")


	def validate_vehicle(self):
		if self.is_weighment_required == "Yes":
			data = validate_gate_entry_velicle(doc=self)
			if data and "message" in data:
				data = data["message"]
				if data:
					weighment_server_url = frappe.get_single('Weighment Profile').get_value('weighment_server_url')
					
					message = (f"Entered Vehicle Number {self.vehicle_number} is already exist in Gate Entry "
						f"{data} on "
						f"<a href='{weighment_server_url}'>{weighment_server_url}</a> which is not completed yet")
					frappe.throw(message)

	

	@frappe.whitelist()
	def fetch_stock_entry_item_data(self):
		if not self.stock_entrys:
			frappe.throw("Please select stock entry first")

		items = []
		if self.stock_entrys:
			for d in self.stock_entrys:
				data = get_stock_entry_item_data(
					company=self.company,
					supplier=self.supplier.split("~")[0],
					stock_entry=d.stock_entry
				)
				if data and "message" in data:
					items.extend(data["message"])
					

		self.stock_entry_details = []
		if items:
			for j in items:
				self.append("stock_entry_details",{
					"item_code":j.get("item_code"),
					"item_name":j.get("item_name"),
					"qty":j.get("qty"),
					"item_group":j.get("item_group")
				})

	@frappe.whitelist()
	def fetch_po_item_details(self):
		items = []
		if self.purchase_orders:
			for d in self.purchase_orders:
				data = get_purchase_order_items_data(branch=self.branch,supplier=self.supplier.split("~")[0],purchase_order=d.purchase_orders)
				if data and "message" in data:
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
				"delivery_note_item":d.get("delivery_note_item"),
				"purchase_order":d.get("parent"),
				"purchase_order_item":d.get("name"),
				"expense_account":d.get("expense_account"),
				"branch":d.get("branch"),
				"cost_center":d.get("cost_center"),
			})
	

	@frappe.whitelist()
	def fetch_so_item_details(self):
		items = []
		if self.subcontracting_orders:
			for d in self.subcontracting_orders:
				data = get_subcontracting_order_items_data(branch=self.branch,supplier=self.supplier.split("~")[0],subcontracting_order=d.subcontracting_order)
				if data and "message" in data:
					items.extend(data["message"])


		self.subcontracting_details = []
		if items:
			print("items:--------------->",items)
			for d in items:
				self.append("subcontracting_details",{
					"item_code":d.get("item_code"),
					"item_name":d.get("item_name"),
					"qty":d.get("qty"),
					"description":d.get("description"),
					"stock_uom":d.get("stock_uom"),
					"conversion_factor":d.get("conversion_factor"),
					"rate":d.get("rate"),
					"amount":d.get("amount"),
					"warehouse":d.get("warehouse"),
					"material_request":d.get("material_request"),
					"material_request_item":d.get("material_request_item"),
					"subcontracting_order":d.get("parent"),
					"purchase_order_item":d.get("name"),
					"expense_account":d.get("expense_account"),
					"branch":d.get("branch"),
					"cost_center":d.get("cost_center"),
				})

	def before_submit(self):
		self.validate_extra_delivery_details()

	@frappe.whitelist()
	def validate_extra_delivery_details(self):
		if self.entry_type == "Inward" and not self.is_manual_weighment and not self.job_work and not self.is_subcontracting_order:
			action_msg = frappe._(
				'To allow over receipt / delivery, update "Over Receipt/Delivery Allowance" in Stock Settings or the Item.'
			)
			data = get_extra_delivery_stock_settings(self)["message"]
			
			if data:
				for d in self.items:
					for l in data:
						if d.get("item_code") == l.get("item_code"):
							allowed_extra_percentage = l.get("odr_per")
							if allowed_extra_percentage:
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
					accepted_qty = 0
					rejected_qty = 0
					actual_received_qty = 0
					accepted_qty = d.accepted_quantity if d.accepted_quantity else 0
					rejected_qty = d.rejected_quantity if d.rejected_quantity else 0
					actual_received_qty = d.actual_received_qty if d.actual_received_qty else 0
					if (accepted_qty + rejected_qty + actual_received_qty) > d.qty:
						over_limit_qty = (accepted_qty + rejected_qty + actual_received_qty) - d.qty
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

		


def create_submitable_gate_entry(doc):
	try:
		PROFILE = frappe.get_doc("Weighment Profile")
		if PROFILE.is_enabled:
			URL = PROFILE.get("weighment_server_url")
			API_KEY = PROFILE.get("api_key")
			API_SECRET = PROFILE.get_password("api_secret")

			headers = {
			"Authorization": f"token {API_KEY}:{API_SECRET}",
			"Content-Type": "application/json"
			}
			
			data = doc.as_dict()
			fields_to_check = ["driver", "transporter","supplier"]
			for field in fields_to_check:
				if data.get(field) and "~" in data.get(field):
					field_value = data.pop(field)
					actual_value = field_value.split("~")[0]
					data[field] = actual_value
			path = f"{URL}/api/method/weighment_server.api.create_submitable_gate_entry"
			payload = json.dumps({"doc":data})
			response = requests.post(url=path, headers=headers, data=payload)
	except Exception as e:
		print("An error occurred:", str(e))
		frappe.log_error(frappe.get_traceback(), 'Weight Adjustment Data Getting Error')
		return {"error": str(e)}