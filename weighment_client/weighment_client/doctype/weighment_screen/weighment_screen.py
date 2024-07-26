from datetime import datetime
import json
import time
import frappe
from frappe.frappeclient import FrappeClient
from frappe.model.document import Document
from frappe.utils.data import flt, get_datetime, get_link_to_form, getdate, now, today
import requests
import serial
from smartcard.System import readers
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString
from weighment_client.api import check_item_weight_adjustment_on_weighment, get_child_table_data, get_value
from weighment_client.weighment_client_utils import google_voice, play_audio, read_button_switch, read_smartcard, read_weigh_bridge
import time
from frappe.utils import now_datetime
from playsound import playsound
import threading
background_threads = []
stop_background_processes = False

def background_process():
    global stop_background_processes
    while not stop_background_processes:
        pass
class WeighmentScreen(Document):
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)


    @frappe.whitelist()
    def check_weighbridge_is_empty(self):
        profile = frappe.get_cached_doc("Weighment Profile")
        if not profile.wake_up_weight:
            frappe.msgprint(
                title="Wakeup Weight Missing for Weigh Bridge",
                msg=f"Please Update Wakeup weight in {get_link_to_form('Weighment Profile','Weighment Profile')}",
            )
        wakeup_weight = profile.wake_up_weight
        while True:
            if read_weigh_bridge()[0] <= wakeup_weight:
                return True
            else:
                play_audio(audio_profile="Please check platform is blank")
                time.sleep(2)
                # insert_or_remove_card()
                
                print("Wating for decreese weight of waybridge...")
                # return False


    @frappe.whitelist()
    def wake_up_screen(self):
        profile = frappe.get_cached_doc("Weighment Profile")
        if not profile.wake_up_weight:
            frappe.msgprint(
                title="Wakeup Weight Missing for Weigh Bridge",
                msg=f"Please Update Wakeup weight in {get_link_to_form('Weighment Profile','Weighment Profile')}",
            )

        wakeup_weight = profile.wake_up_weight
        while True:
            current_weight = read_weigh_bridge()[0]
            print("current weight:--->",current_weight,wakeup_weight)
            if current_weight >= wakeup_weight:
                print("Weight gain detected...")
                return True
            else:
                print("Waiting for weight gain...",read_weigh_bridge()[0])
                time.sleep(3)

    @frappe.whitelist()
    def fetch_gate_entry(self):
        data = read_smartcard()
        if data:
            card_number = frappe.db.get_value("Card Details",{"hex_code":data},["card_number"])
            if not card_number:
                return "trigger_empty_card_validation"
            if card_number:
                entry = frappe.db.get_value("Gate Entry",{"card_number":card_number,"docstatus":1},"name",order_by="creation DESC")
                if entry:
                    doc = frappe.get_cached_doc("Gate Entry",entry)
                    if doc.is_completed:
                        return "weighment already done"
                    else:
                        return entry
                else:
                    return "trigger_empty_card_validation"
                
    @frappe.whitelist()
    def validate_card_number(self):
        count = 0
        while count < 2:
            play_audio(audio_profile="Used Token")
            count +=1
            time.sleep(1)

        return True

    
    @frappe.whitelist()
    def fetch_purchase_order_item_data_by_gate_entry(self,args):
        if args.entry:
            entry = frappe.get_cached_doc("Gate Entry",{"name":args.entry})
            if entry.items:
                item_list = []
                for item in entry.items:
                    item_dict = item.as_dict()
                    to_remove_ = ["name", "owner", "creation", "modified", "modified_by", "doctype", "parent", "parenttype", "parentfield"]
                    for r in to_remove_:
                        if item_dict.get(r):
                            item_dict.pop(r)
                    item_list.append(item_dict)
                return item_list
    
    @frappe.whitelist()
    def fetch_purchase_orders_data_by_gate_entry(self,args):
        if args.entry:
            entry = frappe.get_cached_doc("Gate Entry",{"name":args.entry})
            if entry.entry_type == "Inward":
                self.purchase_orders = []
                for po in entry.purchase_orders:
                    self.append("purchase_orders",{
                        "purchase_orders":po.purchase_orders
                    })
    
    @frappe.whitelist()
    def update_purchase_orders_data(self,args):
        if args.entry:
            entry = frappe.get_cached_doc("Gate Entry",{"name":args.entry})
            if entry.purchase_orders:
                item_list = []
                for item in entry.purchase_orders:
                    item_dict = item.as_dict()
                    to_remove_ = ["name", "owner", "creation", "modified", "modified_by", "doctype", "parent", "parenttype", "parentfield"]
                    for r in to_remove_:
                        if item_dict.get(r):
                            item_dict.pop(r)
                    item_list.append(item_dict)
                return item_list
    
    @frappe.whitelist()
    def update_date_fields_depends_on_weighment(self):
        record = frappe.get_value("Weighment",{"gate_entry_number":self.gate_entry_number,"is_in_progress":1,"is_completed":0},order_by="creation DESC")
        if record:

            doc = frappe.get_cached_doc("Weighment",record)
            self.weighment_date = doc.weighment_date
            self.inward_date = doc.inward_date
            if doc.outward_date:
                self.outward_date = doc.outward_date

        else:
            self.weighment_date = getdate(today())
            self.inward_date = get_datetime(now())
    
    @frappe.whitelist()
    def validate_purchase_weight(self):
        if self.entry_type == "Inward" and self.items:
            
            if self.enable_weight_adjustment:
                
                if self.net_weight > self.items[0].get("accepted_quantity"):
                    filtered_weight = self.net_weight - self.items[0].get("accepted_quantity")
                    print("filtered weight:------>",filtered_weight)
                    self.tare_weight = self.tare_weight + filtered_weight
                    self.net_weight = self.net_weight - filtered_weight
                for d in self.items:
                    d.accepted_quantity = self.net_weight
                    d.received_quantity = self.net_weight

                    

            # value = get_value(
            #     doctype="Item",
            #     docname=item,
            #     fieldname="custom_enable_weight_adjustment",
            #     filters = ({"item_code":item})
            # )
            # if value:


    @frappe.whitelist()
    def update_existing_weighment_data_by_card(self,args):
        data = frappe._dict()
        entry = frappe.get_cached_doc("Gate Entry",args.entry)
        weighment = frappe.db.get_value("Weighment",{"gate_entry_number":args.entry,"is_in_progress":1,"is_completed":0},order_by="creation DESC")
        if weighment:
            doc = frappe.get_cached_doc("Weighment",weighment)
            self.is_in_progress = doc.name
            self.is_completed = doc.is_completed
            self.tare_weight = doc.tare_weight
            self.gross_weight = doc.gross_weight
            self.reference_record = doc.name
            data.update({
                "is_in_progress":doc.is_in_progress,
                "is_completed":doc.is_completed,
                "tare_weight":doc.tare_weight,
                "gross_weight":doc.gross_weight,
                "net_weight":doc.net_weight,
                "reference_record":doc.name
            })
            if doc.net_weight:
                data.update({"net_weight":doc.net_weight})
                self.net_weight = doc.net_weight

        if data:
            return data
        
    # @frappe.whitelist()
    # def is_button_precessed(self):
    #     count = 0
    #     while True:
    #         if count != 2:
    #             play_audio(audio_profile="Press green button for weight")
    #             count +=1
    #             time.sleep(2)
    #         else:
    #             break
                
    #     data = read_button_switch()
    #     return data
    
    @frappe.whitelist()
    def update_weight_details_for_new_entry(self,args):
        data = frappe._dict()
        if args.entry:
            entry = frappe.get_doc("Gate Entry",{"name":args.entry})
            print("Entry Type:--->",entry.entry_type)
            if entry.entry_type == "Inward":
                self.gross_weight = read_weigh_bridge()[0]
                time.sleep(5)
                play_audio(audio_profile="Your Gross Weight Is")

                quintal = str(int(self.gross_weight) / 100)
                kilogram = str(int(self.gross_weight) % 100)
                _quintal = (quintal.split("."))
                if "." in quintal:
                    print("@@@@@@@@@@@@@@@@@@Quintal",_quintal,type(_quintal))
                    if _quintal:
                        google_voice(text=_quintal[0])
                        play_audio(audio_profile="Quintal")
                else:
                    google_voice(text=quintal)
                    play_audio(audio_profile="Quintal")

                # print(quintal,kilogram)
                # google_voice(text=quintal)

                # play_audio(audio_profile="Quintal")
                google_voice(text=kilogram)
                play_audio(audio_profile="KG")
                play_audio(audio_profile="Huva")
                
            if entry.entry_type == "Outward":
                self.tare_weight = read_weigh_bridge()[0]
                time.sleep(5)
                play_audio(audio_profile="Your Tare Weight Is")
                # if self.tare_weight < 100:
                quintal = str((int(self.tare_weight) / 100))
                _quintal = (quintal.split("."))
                if "." in quintal:
                    print("@@@@@@@@@@@@@@@@@@Quintal",_quintal,type(_quintal))
                    if _quintal:
                        google_voice(text=_quintal[0])
                        play_audio(audio_profile="Quintal")
                else:
                    google_voice(text=quintal)
                    play_audio(audio_profile="Quintal")
                
                kilogram = str((int(self.tare_weight) % 100))
                
                google_voice(text=kilogram)
                play_audio(audio_profile="KG")
                play_audio(audio_profile="Huva")
    
    @frappe.whitelist()
    def print_first_slip(self):
        pass
    
    @frappe.whitelist()
    def update_weight_details_for_existing_entry(self):
        if self.reference_record:
            rec = frappe.get_cached_doc("Weighment",self.reference_record)
            if rec.entry_type == "Outward" and not rec.tare_weight and not rec.gross_weight:
                self.tare_weight = read_weigh_bridge()[0]
                
            if rec.entry_type == "Outward" and rec.tare_weight and not rec.gross_weight:
                self.gross_weight = read_weigh_bridge()[0]
            if rec.entry_type == "Inward" and not rec.tare_weight and not rec.gross_weight:
                self.gross_weight = read_weigh_bridge()[0]
            if rec.entry_type == "Inward" and not rec.tare_weight and rec.gross_weight:
                self.tare_weight = read_weigh_bridge()[0]
            
            
            time.sleep(3)

            if self.gross_weight <= self.tare_weight:
                play_audio(audio_profile="Tare weight cant be less than gross weight")
                return "trigger_weight_validation"
            
            if self.gross_weight == 0:
                play_audio(audio_profile="Gross Weight Can't Be Zero")
                return "trigger_weight_validation"
            
            
            

            
            self.net_weight = self.gross_weight - self.tare_weight
            self.validate_purchase_weight()
            if rec.allowed_tolerance > 0:

                if self.net_weight < self.minimum_permissible_weight:
                    play_audio(audio_profile="Delivery Exception")
                    return "trigger_delivery_note_validation"
                
                if self.net_weight > self.maximum_permissible_weight:
                    play_audio(audio_profile="Delivery Exception")
                    return "trigger_delivery_note_validation"
            
            
            # play_audio(audio_profile="Your Tare Weight Is")
            # quintal = str(int(self.tare_weight) // 100)
            # kilogram = str(int(self.tare_weight) % 100)

            # print(quintal,kilogram)
            # google_voice(text=quintal)
            # play_audio(audio_profile="Quintal")
            # google_voice(text=kilogram)
            # play_audio(audio_profile="KG")
            # play_audio(audio_profile="Huva")
            if rec.entry_type == "Outward":

                play_audio(audio_profile="Your Gross Weight Is")

                quintal = str(int(self.gross_weight) / 100)
                kilogram = str(int(self.gross_weight) % 100)
                
                if "." in quintal:
                    _quintal = (quintal.split("."))
                    if _quintal:
                        google_voice(text=_quintal[0])
                        play_audio(audio_profile="Quintal")
                else:
                    google_voice(text=quintal)
                    play_audio(audio_profile="Quintal")

                # print(quintal,kilogram)
                # google_voice(text=quintal)
                # play_audio(audio_profile="Quintal")
                google_voice(text=kilogram)
                play_audio(audio_profile="KG")
                play_audio(audio_profile="Huva")

                

                play_audio(audio_profile="Your Net Weight Is")
                quintal = str(int(self.net_weight) / 100)
                kilogram = str(int(self.net_weight) % 100)
                if "." in quintal:
                    _quintal = (quintal.split("."))
                    if _quintal:
                        google_voice(text=_quintal[0])
                        play_audio(audio_profile="Quintal")
                else:
                    google_voice(text=quintal)
                    play_audio(audio_profile="Quintal")


                # print(quintal,kilogram)
                # google_voice(text=quintal)
                # play_audio(audio_profile="Quintal")
                google_voice(text=kilogram)
                play_audio(audio_profile="KG")
                play_audio(audio_profile="Huva")

            if rec.entry_type == "Inward":

                play_audio(audio_profile="Your Tare Weight Is")

                quintal = str(int(self.tare_weight) / 100)
                kilogram = str(int(self.tare_weight) % 100)
                if "." in quintal:
                    _quintal = (quintal.split("."))
                    if _quintal:
                        google_voice(text=_quintal[0])
                        play_audio(audio_profile="Quintal")
                else:
                    google_voice(text=quintal)
                    play_audio(audio_profile="Quintal")

                # print(quintal,kilogram)
                # google_voice(text=quintal)
                # play_audio(audio_profile="Quintal")
                google_voice(text=kilogram)
                play_audio(audio_profile="KG")
                play_audio(audio_profile="Huva")


                play_audio(audio_profile="Your Net Weight Is")
                quintal = str(int(self.net_weight) / 100)
                kilogram = str(int(self.net_weight) % 100)
                if "." in quintal:
                    _quintal = (quintal.split("."))
                    if _quintal:
                        google_voice(text=_quintal[0])
                        play_audio(audio_profile="Quintal")
                else:
                    google_voice(text=quintal)
                    play_audio(audio_profile="Quintal")

                # print(quintal,kilogram)
                # google_voice(text=quintal)
                # play_audio(audio_profile="Quintal")
                google_voice(text=kilogram)
                play_audio(audio_profile="KG")
                play_audio(audio_profile="Huva")

            return True


    @frappe.whitelist()
    def is_new_weighment_record(self,args):
        if args.entry:
            condition = 0
            record = frappe.get_value("Weighment",{"gate_entry_number":args.entry,"is_in_progress":1,"is_completed":0},order_by="creation DESC")
            if record:
                condition = 0
            else:
                condition = 1
            return condition
    
    
    @frappe.whitelist()
    def create_new_weighment_entry(self):
        entry = frappe.new_doc("Weighment")
        entry.gate_entry_number = self.gate_entry_number
        entry.branch = self.branch
        entry.abbr = self.abbr
        entry.company = self.company
        entry.weighment_date = self.weighment_date
        entry.inward_date = self.inward_date
        entry.vehicle_type = self.vehicle_type
        entry.vehicle_number = self.vehicle_number
        entry.vehicle = self.vehicle
        entry.supplier = self.supplier
        entry.supplier_name = self.supplier_name
        entry.entry_type = self.entry_type
        if self.entry_type == "Outward":
            entry.item_group = self.item_group
        entry.driver_name = self.driver_name
        entry.enable_weight_adjustment = self.enable_weight_adjustment
        # entry.purchase_order = self.purchase_order
        entry.allowed_tolerance = self.allowed_tolerance
        entry.driver_contact = self.driver_contact
        entry.is_in_progress = 1
        entry.location = self.location
        entry.items  = self.items
        entry.purchase_orders = self.purchase_orders
        if self.driver:
            entry.driver = self.driver
        if self.tare_weight:
            entry.tare_weight = self.tare_weight
        if self.gross_weight:
            entry.gross_weight = self.gross_weight
        entry.save(ignore_permissions=True)
        entry.save("Submit")
        return True
    
    @frappe.whitelist()
    def update_existing_weighment_details(self):
        if self.gate_entry_number and not ((self.gross_weight == self.tare_weight) or (self.gross_weight <= self.tare_weight)):
            record = frappe.get_value("Weighment", {"gate_entry_number": self.gate_entry_number, "is_in_progress": 1, "is_completed": 0}, order_by="creation DESC")
            if record:
                rec = frappe.get_doc("Weighment", record)
                outward_date_str = datetime.strftime(get_datetime(now()), "%Y-%m-%d %H:%M:%S")
                rec.outward_date = get_datetime(outward_date_str)
                
                if rec.gate_entry_number and rec.entry_type == "Outward" and not rec.tare_weight and not rec.gross_weight:
                    rec.tare_weight = self.tare_weight
                if rec.gate_entry_number and rec.entry_type == "Outward" and rec.tare_weight and not rec.gross_weight:
                    rec.gross_weight = self.gross_weight
                if rec.gate_entry_number and rec.entry_type == "Inward" and not rec.tare_weight and not rec.gross_weight:
                    rec.gross_weight = self.gross_weight
                if rec.gate_entry_number and rec.entry_type == "Inward" and not rec.tare_weight and rec.gross_weight:
                    rec.tare_weight = self.tare_weight
                
                rec.net_weight = rec.gross_weight - rec.tare_weight
                rec.is_in_progress = 0
                rec.is_completed = 1
                rec.minimum_permissible_weight = self.minimum_permissible_weight
                rec.maximum_permissible_weight = self.maximum_permissible_weight
                rec.total_weight = self.total_weight
                rec.delivery_note_details = self.delivery_note_details
                if self.enable_weight_adjustment and rec.entry_type == "Inward" and rec.items:
                    for d in rec.items:
                        d.accepted_quantity = self.net_weight
                        d.received_quantity = self.net_weight
                        
                rec.save("Submit")
                return True

    @frappe.whitelist()
    def clear_plateform_for_next_weighment(self):
        profile = frappe.get_cached_doc("Weighment Profile")
        if not profile.wake_up_weight:
            frappe.msgprint(
                title="Wakeup Weight Missing for Weigh Bridge",
                msg=f"Please Update Wakeup weight in {get_link_to_form('Weighment Profile','Weighment Profile')}",
            )
        wakeup_weight = profile.wake_up_weight
        while True:
            if read_weigh_bridge()[0] <= wakeup_weight:
                return True
            else:
                # play_audio(audio_profile="Please check platform is blank")
                
                # insert_or_remove_card()
                
                print("Wating for decreese weight of waybridge...")
                time.sleep(2)
                # return False

    @frappe.whitelist()
    def restart_weighment_screen(doc):
        import os
        os.system("bench restart")
        return True