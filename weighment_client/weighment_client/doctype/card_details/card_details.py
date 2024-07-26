# Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document

from frappe.frappeclient import FrappeClient
import requests



class CardDetails(Document):

	def after_insert(self):
		PROFILE = frappe.get_doc("Weighment Profile")
		if PROFILE.is_client:
			URL = PROFILE.get("secondary_server_url")
			API_KEY = PROFILE.get("_api_key")
			API_SECRET = PROFILE.get_password("_api_secret")
		else:  
			URL = PROFILE.get("weighment_server_url")
			API_KEY = PROFILE.get("api_key")
			API_SECRET = PROFILE.get_password("api_secret")
		data = self.as_json()
		headers = {
			"Authorization": f"token {API_KEY}:{API_SECRET}",
			"Content-Type": "application/json"
		}
		try:
			response = requests.post(f"{URL}/api/resource/Card Details", json=json.loads(data), headers=headers)
			# if response.status_code == 200:
				# frappe.msgprint("Record created successfully...")
			# else:
			# 	print("Error:", response.text)
		except Exception as e:
			frappe.error_log(f"Exception occurred: {e}")
			print("Exception:", e)


	def on_update(self):
		PROFILE = frappe.get_doc("Weighment Profile")
		if PROFILE.is_client:
			URL = PROFILE.get("secondary_server_url")
			API_KEY = PROFILE.get("_api_key")
			API_SECRET = PROFILE.get_password("_api_secret")
		else:  
			URL = PROFILE.get("weighment_server_url")
			API_KEY = PROFILE.get("api_key")
			API_SECRET = PROFILE.get_password("api_secret")
		data = self.as_dict()
		to_remove=['creation','modified']
		for d in to_remove:
			if data.get(d):
				data.pop(d)
		payload = json.dumps(data)
		headers = {
			"Authorization": f"token {API_KEY}:{API_SECRET}",
			"Content-Type": "application/json"
		}
		try:
			response = requests.put(f"{URL}/api/resource/Card Details/{self.name}", json=json.loads(payload), headers=headers)
			# if response.status_code == 200:
			# 	frappe.msgprint("Record updated successfully...")
		except Exception as e:
			frappe.error_log(f"Exception occurred: {e}")
			print("Exception:", e)
		# self.rename_document(self.card_number)


	def on_trash(self):
		PROFILE = frappe.get_doc("Weighment Profile")
		if PROFILE.is_client:
			URL = PROFILE.get("secondary_server_url")
			API_KEY = PROFILE.get("_api_key")
			API_SECRET = PROFILE.get_password("_api_secret")
		else:  
			URL = PROFILE.get("weighment_server_url")
			API_KEY = PROFILE.get("api_key")
			API_SECRET = PROFILE.get_password("api_secret")
		headers = {
			"Authorization": f"token {API_KEY}:{API_SECRET}"
		}
		try:
			response = requests.delete(f"{URL}/api/resource/Card Details/{self.name}",headers=headers)
			if response.status_code == 200:
				frappe.msgprint("Record Deleted Sucessfully")
		except Exception as e:
			frappe.error_log(f"Exception occurred: {e}")
			print("Exception:", e)

	def rename_document(self,new_name):
		if self.card_number != self.name:
			self.rename(self.card_number)
		PROFILE = frappe.get_doc("Weighment Profile")
		if PROFILE.is_client:
			URL = PROFILE.get("secondary_server_url")
			API_KEY = PROFILE.get("_api_key")
			API_SECRET = PROFILE.get_password("_api_secret")
		else:  
			URL = PROFILE.get("weighment_server_url")
			API_KEY = PROFILE.get("api_key")
			API_SECRET = PROFILE.get_password("api_secret")
		DOC = FrappeClient(url=URL,api_key=API_KEY,api_secret=API_SECRET)
		card = DOC.get_value("Card Details",fieldname="name",filters={"hex_code":self.hex_code})
		if (card.get("name") and new_name) and  (card.get("name") != new_name):
			url = f"{URL}/api/method/frappe.client.rename_doc"
			headers = {
				"Authorization": f"token {API_KEY}:{API_SECRET}",
				"Content-Type": "application/json"
			}

			params = {
				"doctype": self.doctype,
				"old_name": str(card.get("name")),
				"new_name": str(new_name)
			}
			response = requests.post(url, json=params, headers=headers)
			# if response.status_code == 200:
			# 	frappe.msgprint("Record rename sucessfully")
			# else:
			print("error:--->",response.text)
