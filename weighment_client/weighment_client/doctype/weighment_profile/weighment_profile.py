# Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
import socket
import os

import requests
import serial
from weighment_client.api import get_child_table_data, get_child_table_data_for_single_doctype, get_document_names, get_value
from weighment_client.weighment_client_utils import execute_terminal_commands_for_button_or_weighbridge, get_serial_port, get_system_password
import serial
from serial.tools import list_ports


class WeighmentProfile(Document):
	@frappe.whitelist()
	def fetch_port_location(self):		
		ports = list(list_ports.comports())
		for port in ports:
			return port.device
	
	@frappe.whitelist()
	def get_locations(self):
		if self.is_enabled:
			location = get_document_names(
				doctype = "Location"
			)
			return location
		
	
	@frappe.whitelist()
	def get_branch_data(self,location):
		if self.is_enabled:
			branch = get_document_names(
				doctype="Branch",
				filters={"custom_location":location}
			)
			print("branch:--------->",branch)
			return branch
			
	# @frappe.whitelist()
	# def get_location_name(self,selected_branch):
	# 	location = get_value(
	# 		doctype="Branch",
	# 		docname=selected_branch,
	# 		fieldname="custom_location",
	# 		filters=({"name":selected_branch})
	# 	)
	# 	return location
	
	@frappe.whitelist()
	def get_branch_abbr(self,selected_branch):
		abbr = get_value(
			doctype="Branch",
			docname=selected_branch,
			fieldname="plant_abbr",
			filters=({"name":selected_branch})
		)
		return abbr
	
	@frappe.whitelist()
	def get_branch_company(self,selected_branch):
		
		
		company = get_value(
			doctype="Branch",
			docname=selected_branch,
			fieldname="company",
			filters=({"name":selected_branch})
		)
		print("triggered !!!!!!!!!!!!!!!!!!",company)
		

		return company
	

	
	@frappe.whitelist()
	def get_weighbridge_uom(self):
		if self.is_enabled:
			uom = get_document_names(
				doctype="UOM",
			)
			return uom


	@frappe.whitelist()
	def fetch_ip_address(self):
		try:
			s= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(("8.8.8.8",80))
			ip_address = s.getsockname()[0]
			s.close
			return ip_address
		except Exception as e:
			frappe.throw(
				title="Enexpected Error Found",
				msg= e
			)

	@frappe.whitelist()
	def fetch_admin(self):
		try:
			user = os.getlogin()
			return user
		except Exception as e:
			frappe.throw(
				title="Enexpected Error Found",
				msg=e
			)

	@frappe.whitelist()
	def get_pass(self):
		return self.get_password("administrator_password")
	
	@frappe.whitelist()
	def update_conversion_table(self):
		if self.is_enabled:
			PROFILE = frappe.get_doc("Weighment Profile")
			PROFILE = frappe.get_doc("Weighment Profile")
			URL = PROFILE.get("weighment_server_url")
			API_KEY = PROFILE.get("api_key")
			API_SECRET = PROFILE.get_password("api_secret")

			headers = {
				"Authorization": f"token {self.get('api_key')}:{self.get_password('api_secret')}"
			}

			url = f"{URL}/api/resource/Weighment Client Settings/Weighment Client Settings"
			response = requests.get(url, headers=headers)

			if response.status_code == 200:
				data = response.json()
				self.weighbridge_uom = data["data"]["weighbridge_uom"]

			data = get_child_table_data_for_single_doctype(
				parent_docname="Weighment Client Settings",
				child_table_fieldname="uom_conversion"
			)
			if data:
				self.uom_conversion = []
				for d in data:
					self.append("uom_conversion",{
						"uom":d.get("uom"),
						"conversion_factor":d.get("conversion_factor")
					})
			
			return True

		# return [profile.name for profile in audio_profiles]

	
	# def validate(self):
	# 	if not self.is_client:
	# 		if not self.branch:
	# 			frappe.throw("Branch is required")
	# 		client= frappe.get_doc("User",frappe.session.user)
	# 		c_api_key = client.get("api_key")
	# 		c_api_secret = client.get_password("api_secret")
	# 		is_record_exist = get_value(
	# 			docname=self.platform_location,
	# 			fieldname="name",
	# 			doctype="Weighment Profile",
	# 			filters=({"name":self.platform_location}),
	# 		)
	# 		if not is_record_exist:

	# 			data = self.as_dict()
	# 			client_url = self.fetch_ip_address()
	# 			data.update({"weighment_client_url":client_url})
	# 			to_remove=['creation','modified',"__unsaved","Created By","local_profile_details","audio_file_details","camera_details","weighment_server_url","wake_up_weight","api_key","api_secret"]


	# 			for d in to_remove:
	# 				if data.get(d):
	# 					data.pop(d)
	# 			data.update({
	# 				"name":self.platform_location,
	# 				"wake_up_weight_kg":self.wake_up_weight,
	# 				"api_key":c_api_key,
	# 				"api_secret":c_api_secret
	# 			})

	# 			headers = {
	# 				"Authorization": f"token {self.api_key}:{self.get_password('api_secret')}",
	# 				"Content-Type": "application/json"
	# 			}
	# 			local_profile_details = []
	# 			if self.get("local_profile_details"):
	# 				for a in self.local_profile_details:
	# 					profile_dict = a.as_dict()
	# 					to_remove = ["name", "owner", "creation", "modified", "modified_by", "doctype", "parent", "parenttype", "parentfield"]
	# 					for r in to_remove:
	# 						if profile_dict.get(r):
	# 							profile_dict.pop(r)
	# 					local_profile_details.append(profile_dict)
					
	# 				data.update({"local_profile_details":local_profile_details})
				
	# 			camera_details = []
	# 			if self.get("camera_details"):
	# 				for c in self.camera_details:
	# 					camera_dict=c.as_dict()
	# 					to_remove = ["name", "owner", "creation", "modified", "modified_by", "doctype", "parent", "parenttype", "parentfield"]
	# 					for r in to_remove:
	# 						if camera_dict.get(r):
	# 							camera_dict.pop(r)
						
	# 					camera_details.append(camera_dict)
	# 				data.update({"camera_setting_details":camera_details})

				
				
	# 			payload = json.dumps(data)
	# 			response = requests.post(f"{self.weighment_server_url}/api/resource/Weighment Profile",data=payload,headers=headers)
	# 			if response.status_code == 200:
	# 				frappe.msgprint(
	# 					title="Recored Created",
	# 					indicator="orange",
	# 					alert=True,
	# 					realtime=True,
	# 					msg=" Record Created Sucessfully ... ")
	# 			else:
	# 				print("Error:", response.text)


