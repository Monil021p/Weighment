# Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from weighment_client.api import cancel_document, delete_document, get_value, insert_document_with_child, submit_document, update_document_after_submit, update_document_with_child
from weighment_client.weighment_client_utils import fetch_ip_address, generate_photo



class Weighment(Document):
    def after_insert(self):
        if not self.url:
            ip = fetch_ip_address()
            self.url = ip
        self.submit()
        self.update_card_details()
        insert_document_with_child(self)
        generate_photo(self)

    def on_trash(self):
        self.reset_card_details()
        delete_document(self)

    def on_update(self):
        update_document_with_child(self)


    # def on_submit(self):
    #     if self.gate_entry_number and self.tare_weight and self.gross_weight:
    #         entry = frappe.get_doc("Gate Entry",self.gate_entry_number)
    #         if self.gross_weight and self.tare_weight:
    #             entry.is_in_progress = 0
    #             entry.is_completed = 1
    #             entry.save("Submit")
    #             # self.is_in_progress = 0
    #             # self.is_completed  = 1
    #             # submit_document(self)
    
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
        update_document_after_submit(self)

    def on_cancel(self):
        self.reset_card_details()
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
                    docname=line.delivery_note,
                    fieldname="docstatus",
                    doctype="Delivery Note"
                )
                if check_docstatus == 1:
                    frappe.throw(f"row {line.idx}: Linked delivery note {line.delivery_note} is already submitted, Please cancel it first")
                else:
                    return True
