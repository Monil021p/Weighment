# Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
# For license information, please see license.txt


import json
import frappe
from frappe.model.document import Document
from frappe.utils.data import get_datetime, get_link_to_form, getdate,format_date
from frappe.frappeclient import FrappeClient, AuthError, SiteUnreachableError, SiteExpiredError
import requests
from weighment_client.api import (
    cancel_document, 
    delete_document,
    get_document_info, 
    get_value, 
    insert_document_with_child, 
    update_document_after_submit, 
    update_document_with_child
)

from weighment_client.weighment_client_utils import (
    fetch_ip_address, 
    generate_photo
)
from escpos import *
from escpos.printer import Usb


class Weighment(Document):



    @frappe.whitelist()
    def check_delivery_note_status(self):
        if not frappe.db.get_single_value("Weighment Profile","enable_maintanance_mode"):

            frappe.throw(
                title="Illigle Activity",
                msg="Not allow to perform this action, Maintanance mode is disabled"
            )

        try:
            weighment_profile = frappe.get_single("Weighment Profile")

            if weighment_profile.is_enabled:
                
                path = f"{weighment_profile.weighment_server_url}/api/method/weighment_server.api.check_delivery_note_status"
                payload = json.dumps({"weighment":self.name})
                
                headers = {
                    'Content-Type': 'application/json',
                    "Authorization": f"token {weighment_profile.get('api_key')}:{weighment_profile.get_password('api_secret')}"
                }

                response = requests.post(url=path, headers=headers, data=payload)
                data = response.json()

                if data.get("response") == "delivery_note_linked":
                    frappe.throw("unlink linked delivery notes from live server first")
                return True
        except:
            frappe.log_error(frappe.get_traceback(),"getting error while checking delivery note status")

    @frappe.whitelist()
    def check_purchase_receipt_status(self):
        if not frappe.db.get_single_value("Weighment Profile","enable_maintanance_mode"):

            frappe.throw(
                title="Illigle Activity",
                msg="Not allow to perform this action, Maintanance mode is disabled"
            )
        
        try:
            weighment_profile = frappe.get_single("Weighment Profile")

            if weighment_profile.is_enabled:
                
                path = f"{weighment_profile.weighment_server_url}/api/method/weighment_server.api.check_purchase_receipt_status"
                payload = json.dumps({"weighment":self.name})
                
                headers = {
                    'Content-Type': 'application/json',
                    "Authorization": f"token {weighment_profile.get('api_key')}:{weighment_profile.get_password('api_secret')}"
                }

                response = requests.post(url=path, headers=headers, data=payload)
                return response.json()
        except:
            frappe.log_error(frappe.get_traceback(),"getting error while checking purchase receipt status")

    @frappe.whitelist(allow_guest=True)
    def authenticate_user(self,user_id, password):
        try:
            weighment_profile = frappe.get_single("Weighment Profile")
            login = FrappeClient(url=weighment_profile.get("weighment_server_url"),username=user_id,password=password)._login(username=user_id,password=password)
            print("login:--->",login)
            self.add_comment(comment_type="Info",text="Weight data removed by user {0}".format(login.get("full_name")))
            return login
        except AuthError:
            return {"message": "Login Unsuccessful"}
        except SiteUnreachableError:
            return {"message": "Site Unreachable"}
        except SiteExpiredError:
            return {"message": "Site Expired"}
        except Exception as e:
            return {"message": str(e)}
    
    @frappe.whitelist()
    def get_second_print(self):
        profile = frappe.get_single("Weighment Profile")

        if profile.enable_printing:
            vid = int(profile.get("vendor_id"), 16)
            pid = int(profile.get("product_id"), 16)

            allowed_prints = 1

            try:
                if self.entry_type == "Outward" and self.delivery_note_details:
                    item = self.delivery_note_details[0].get("item")
                    if item:
                        if get_value(
                            doctype="Item",
                            docname=item,
                            fieldname="custom_allow_duplicate_print",
                            filters=({"name":item})
                        ) == 1:
                            allowed_prints = 2
                
                if self.entry_type == "Inward" and self.items:
                    item = self.items[0].get("item_code")
                    if get_value(
                            doctype="Item",
                            docname=item,
                            fieldname="custom_allow_duplicate_print",
                            filters=({"name":item})
                        ) == 1:
                            allowed_prints = 2
            except:
                frappe.log_error(frappe.get_traceback(),"get's issue while checking allowed duplicate prints for weighment {}".format(self.name))

            if vid and pid:
                for _ in range(allowed_prints):
                    try:
                        p = Usb(vid, pid)
                        
                        p.open()
                        def center_text(text, width):
                            spaces = (width - len(text)) // 2
                            return ' ' * spaces + text + ' ' * spaces
                        
                        header = center_text(f"{self.company} ({self.branch})", 50)
                        p.text('\x1b\x21\x10' + '\x1b\x45\x01' + header + '\x1b\x45\x00' + '\x1b\x21\x00' + '\n')  # \x1b\x21\x10 for double-height and \x1b\x45\x01 for underline
                        p.text(center_text("Weighment Slip", 50) + '\n')
                        p.text(center_text(f"Weighment Date: {format_date(self.weighment_date)}", 50) + '\n')
                        p.text('-' * 45 + '\n')

                        lines = [
                            f" Entry Type : {self.entry_type}   Branch : {self.branch}",

                        ]
                        if self.supplier_name:
                            lines.extend([
                                f" Party Name : {self.supplier_name}",
                            ])

                        if self.vehicle_type and self.vehicle_number:
                            lines.extend([
                                f" Vehicle Type : {self.vehicle_type}  Vehicle No:\x1b\x45\x01{self.vehicle_number}\x1b\x45\x00",
                            ])

                        if self.vehicle_owner == "Third Party":
                            lines.extend([
                                    f" Transporter : \x1b\x45\x01{self.transporter_name}\x1b\x45\x00",
                                ])
                        
                        if self.entry_type == "Inward":
                            if not self.is_manual_weighment and self.items and (len(self.items) == 1):

                                lines.extend([
                                    f" Item Name : \x1b\x45\x01{self.items[0].get('item_name')}\x1b\x45\x00",
                                ])
                            if not self.is_manual_weighment and self.items and (len(self.items) > 1):

                                lines.extend([
                                    f" Item Name : \x1b\x45\x01Miscellaneous Item\x1b\x45\x00",
                                ])

                            lines.extend([
                                f" Inward Date : {format_date(self.inward_date)}  Gross Weight : \x1b\x45\x01{self.gross_weight} K \x1b\x45\x00",
                                f" Outward Date : {format_date(self.outward_date)}   Tare Weight : \x1b\x45\x01{self.tare_weight} K \x1b\x45\x00",
                            ])
                        
                        if self.entry_type == "Outward":
                            if not self.is_manual_weighment and self.item_group:

                                lines.extend([
                                    f"Item Group : {self.item_group}",
                                ])
                            
                            lines.extend([
                                f"Inward Date : {format_date(self.inward_date)}   Tare Weight : {self.tare_weight} K",
                                f"Outward Date : {format_date(self.outward_date)}  Gross Weight : {self.gross_weight} K",
                                
                            ])

                        
                        

                        for line in lines:
                            p.text(line + '\n')
                        
                        p.text('\x1b\x21\x10\x1b\x45\x01' + f"                           Net Weight : {self.net_weight} K" + '\x1b\x45\x00\x1b\x21\x00' + '\n')  # Double-height and underline

                        p.text('-' * 45 + '\n')

                        p.cut()

                    except Exception as e:
                        frappe.log_error(frappe.get_traceback(),"Second Print Error")
                    
                    finally:
                        p.close()
        return True
    
    @frappe.whitelist()
    def get_first_print(self):
        profile = frappe.get_single("Weighment Profile")
        if profile.enable_printing:
            vid = int(profile.get("vendor_id"), 16)
            pid = int(profile.get("product_id"), 16)
            # vid = f"0x{profile.get('vendor_id')}"
            # pid = f"0x{profile.get('product_id')}"
            if vid and pid:
                try:
                    # Initialize the printer
                    p = Usb(vid, pid)  # Replace with your printer's vendor and product ID
                    p.open()

                    # ESC/POS commands for formatting
                    p.text('\x1b\x45\x01')  # Turn on bold text
                    p.text(" DATE: {}\n".format(frappe.utils.get_datetime(self.inward_date).strftime("%d-%m-%Y")))
                    p.text('\x1b\x45\x00')  # Turn off bold text

                    p.text('\x1b\x45\x01')  # Turn on bold text
                    p.text(" GATE ENTRY: {}\n".format(self.gate_entry_number))
                    p.text('\x1b\x45\x00')  # Turn off bold text

                    p.text('\x1b\x45\x01')  # Turn on bold text
                    p.text(" CARD NUMBER: {}\n\n".format(frappe.db.get_value("Gate Entry", {"name": self.gate_entry_number}, ["card_number"])))
                    p.text('\x1b\x45\x00')  # Turn off bold text

                    # Print VEHICLE NO. with larger text size
                    p.text('\x1b\x21\x10')  # Select double height mode (adjust as needed)
                    p.text(" VEHICLE NO.: {}\n".format(self.vehicle_number))
                    p.text('\x1b\x21\x00')  # Cancel double height mode

                    # Print a line to simulate a border
                    p.text('\n' + '-' * 40 + '\n')

                    p.cut()

                    
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(),"First Print Error")
                finally:
                    p.close()
        return True
    
    def after_insert(self):
        if not self.url:
            ip = fetch_ip_address()
            self.url = ip
        self.submit()
        self.update_card_details()
        insert_document_with_child(self)
        generate_photo(self)

    def on_trash(self):
        if not frappe.db.get_single_value("Weighment Profile","enable_maintanance_mode"):
            frappe.throw("Not allowed to perform this action, Maintanance mode disabled on {}".format(get_link_to_form("Weighment Profile","Weighment Profile")))
        self.reset_card_details()
        delete_document(self)

    def on_update(self):
        update_document_with_child(self)

    
    def before_update_after_submit(self):

        if self.gate_entry_number:
            entry = frappe.get_doc("Gate Entry",self.gate_entry_number)
            if self.gross_weight and self.tare_weight:
                self.is_in_progress = 0
                self.is_completed  = 1
            
            if self.is_in_progress and not entry.is_in_progress:
                entry.is_in_progress = 1
                entry.is_completed = 0
                entry.save("Submit")
            if self.is_completed and not entry.is_completed:
                entry.is_completed = 1
                entry.is_in_progress = 0
                entry.save("Submit")
        # frappe.db.rollback()
        frappe.db.commit()
    
    def on_update_after_submit(self):
        # update_document_after_submit(self)
        
        response = update_document_after_submit(self)
        if not response or (response and  response.status_code != 200):
            self.db_set("update_required",1)
        


    def on_cancel(self):
        self.reset_card_details()
        if get_value(
			doctype="Weighment",
			docname=self.name,
			fieldname="docstatus",
			filters=({"name":self.name})
		) == 1:
            cancel_document(self)

    def update_card_details(self):
        if self.gate_entry_number:
            entry = frappe.get_doc("Gate Entry",self.gate_entry_number)
            entry.is_in_progress = 1
            entry.save("Submit")

    def reset_card_details(self):
        if self.gate_entry_number:
            entry = frappe.get_doc("Gate Entry",self.gate_entry_number)
            if entry.is_in_progress:
                entry.is_in_progress = 0
            if entry.is_completed:
                entry.is_completed = 0
            entry.save("Submit")

    
    @frappe.whitelist()
    def update_delivery_note_details(self):

        if self.delivery_note_details:
            for line in self.delivery_note_details:
                check_docstatus = get_value(
                    docname= line.delivery_note,
                    fieldname= "docstatus",
                    doctype= "Delivery Note"
                )
                if check_docstatus == 1:
                    frappe.throw(f"row {line.idx}: Linked delivery note {line.delivery_note} is already submitted, Please cancel it first")
                else:
                    return True
    
    @frappe.whitelist()
    def reupdate_failed_weighment_data(self):
        if self.is_completed:
            response = update_document_after_submit(self)
            if not response or (response and  response.status_code != 200):
                self.db_set("update_required",1)
            if response and response.status_code == 200:
                self.db_set("update_required",0)

            if not self.update_required:
                return "Updated Sucessfully"
            
            return True
        if self.is_in_progress:
            response = insert_document_with_child(self)
            if not response or (response and  response.status_code != 200):
                self.db_set("update_required",1)
            if response and response.status_code == 200:
                self.db_set("update_required",0)

            if not self.update_required:
                return "Updated Sucessfully"
    