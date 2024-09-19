
import time
import frappe
import warnings
from datetime import datetime
from frappe.model.document import Document

from weighment_client.api import (
    get_allowed_tolerance,
    get_delivery_note_data_for_weighment, 
    get_delivery_note_item_data_for_weighment,
    get_gate_entry_data_from_card_number,
    get_item_data,
    get_weighment_data_from_card_number,
    get_weighment_data_from_gate_entry,
    is_new_weighment_record_for_weighment
)

from frappe.utils.data import (
    get_datetime, 
    get_link_to_form, 
    getdate, 
    now, 
    today
)

from weighment_client.weighment_client_utils import (
    google_voice,
    play_audio,
    read_smartcard,
    read_weigh_bridge
)

class WeighmentScreen(Document):

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    @frappe.whitelist()
    def check_weighbridge_is_empty(self):

        wake_up_weight = frappe.db.get_single_value("Weighment Profile","wake_up_weight")
        if not wake_up_weight:
            frappe.msgprint(
                title="Wakeup Weight Missing for Weigh Bridge",
                msg=f"Please Update Wakeup weight in {get_link_to_form('Weighment Profile','Weighment Profile')}",
            )

        while True:
            if read_weigh_bridge()[0] <= wake_up_weight:
                return True
            else:
                play_audio(audio_profile="Please check platform is blank")
                time.sleep(2)
                print("Wating for decreese weight of waybridge...")


    @frappe.whitelist()
    def wake_up_screen(self):
        wake_up_weight = frappe.db.get_single_value("Weighment Profile","wake_up_weight")
        if not wake_up_weight:
            frappe.msgprint(
                title="Wakeup Weight Missing for Weigh Bridge",
                msg=f"Please Update Wakeup weight in {get_link_to_form('Weighment Profile','Weighment Profile')}",
            )

        while True:
            current_weight = read_weigh_bridge()[0]
            print("current weight:--->",current_weight,wake_up_weight)
            if current_weight >= wake_up_weight:
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
                entry = get_gate_entry_data_from_card_number(card_number=card_number)
                

                if entry.get("is_manual_weighment"):
                    self.is_manual_weighment = entry.get("is_manual_weighment")
                
                if entry.get("is_subcontracting_order"):
                    self.is_subcontracting_order = entry.get("is_subcontracting_order")
                
                if entry.get("enable_weight_adjustment"):
                    self.enable_weight_adjustment = entry.get("enable_weight_adjustment")

                weighment = get_weighment_data_from_card_number(card_number=card_number)
                if entry and "message" in entry:
                    entry = entry["message"]

                    if entry.get("is_completed"):
                        return "weighment_already_done"
                    
                    if entry.get("entry_type") == "Outward" and entry.get("is_in_progress") and not entry.get("is_manual_weighment") and not entry.get("job_work"):

                        if weighment and "message" in weighment:
                            weighment = weighment["message"]

                            if not weighment.get("delivery_note_details") and not weighment.get("is_manual_weighment"):
                                return "trigger_empty_delivery_note_validation"

                if entry.get("name"):
                    return entry.get("name")
                
                else:
                    return "trigger_empty_card_validation"

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
    def update_date_fields_depends_on_weighment(self):
        record = frappe.get_value("Weighment",{"gate_entry_number":self.gate_entry_number,"is_in_progress":1,"is_completed":0},order_by="creation DESC")
        if record:

            doc = frappe.get_cached_doc("Weighment",record)
            self.weighment_date = doc.weighment_date
            self.inward_date = doc.inward_date
            if doc.outward_date:
                self.outward_date = doc.outward_date
            else:
                self.outward_date = getdate(now())

        else:
            self.weighment_date = getdate(today())
            self.inward_date = get_datetime(now())
    
    @frappe.whitelist()
    def update_existing_weighment_data_by_card(self,args):
        data = frappe._dict()
        weighment = get_weighment_data_from_gate_entry(gate_entry=args.entry)

        if weighment and "message" in weighment:
            weighment = weighment["message"]


            self.is_in_progress = weighment.get("is_in_progress")
            self.is_completed = weighment.get("is_completed")
            self.tare_weight = weighment.get("tare_weight")
            self.gross_weight = weighment.get("gross_weight")
            self.reference_record = weighment.get("name")
            self.entry_type = weighment.get("entry_type")
            self.vehicle_number = weighment.get("vehicle_number")
            self.is_manual_weighment = weighment.get("is_manual_weighment")

            if weighment.get("net_weight"):
                self.net_weight = weighment.get("net_weight")
                data.update({"net_weight":weighment.get("net_weight")})

            data.update({
                "is_in_progress":weighment.get("is_in_progress"),
                "is_completed":weighment.get("is_completed"),
                "tare_weight":weighment.get("tare_weight"),
                "gross_weight":weighment.get("gross_weight"),
                "reference_record":weighment.get("name"),
                "is_manual_weighment":weighment.get("is_manual_weighment")
            })

            
            if weighment.get("entry_type") == "Outward" and not weighment.get("is_manual_weighment") and not weighment.get("is_subcontracting_order") and not weighment.get("job_work"):
                allowed_lower_tolerance, allowed_upper_tolerance = self.get_allowed_tolerance_data(item_group = weighment.get("item_group"), branch= weighment.get("branch"))
                if allowed_lower_tolerance:
                    self.allowed_lower_tolerance = allowed_lower_tolerance
                if allowed_upper_tolerance:
                    self.allowed_upper_tolerance = allowed_upper_tolerance

        if data:
            return data
        
    @frappe.whitelist()
    def get_allowed_tolerance_data(self,item_group,branch):
        data = get_allowed_tolerance(item_group=item_group,branch=branch)
        if data and "message" in data:
            data = data["message"]
            return data.get("allowed_lower_tolerance"),data.get("allowed_upper_tolerance")

        return None, None
        
    

    @frappe.whitelist()
    def fetch_purchase_orders_data_by_gate_entry(self,args):
        if args.entry:
            entry = frappe.get_cached_doc("Gate Entry",{"name":args.entry})
            if entry.entry_type == "Inward" and not entry.is_manual_weighment and entry.purchase_orders:
                self.purchase_orders = []
                for po in entry.purchase_orders:
                    self.append("purchase_orders",{
                        "purchase_orders":po.purchase_orders
                    })
    
    @frappe.whitelist()
    def fetch_purchase_order_item_data_by_gate_entry(self,args):
        if args.entry:
            entry = frappe.get_cached_doc("Gate Entry",{"name":args.entry})
            if entry.items and not entry.is_manual_weighment:
                self.items = []
                for d in entry.items:
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
                    "received_quantity":d.get("received_quantity"),
                    "accepted_quantity":d.get("accepted_quantity"),
                    "rejected_quantity":d.get("rejected_quantity"),
                    "actual_received_qty":d.get("actual_received_qty"),
                    "rate":d.get("rate"),
                    "amount":d.get("amount"),
                    "item_tax_template":d.get("item_tax_template"),
                    "gst_treatment":d.get("gst_treatment"),
                    "rate_company_currency":d.get("rate_company_currency"),
                    "amount_company_currency":d.get("amount_company_currency"),
                    "weight_per_unit":d.get("weight_per_unit"),
                    "weight_uom":d.get("weight_uom"),
                    "total_weight":d.get("total_weight"),
                    "warehouse":d.get("warehouse"),
                    "material_request":d.get("material_request"),
                    "purchase_order":d.get("purchase_order"),
                    "material_request_item":d.get("material_request_item"),
                    "purchase_order_item":d.get("purchase_order_item"),
                    "expense_account":d.get("expense_account"),
                    "branch":d.get("branch"),
                    "cost_center":d.get("cost_center"),
			    })
                return True
            
    @frappe.whitelist()
    def fetch_subcontracting_orders_data_by_gate_entry(self,args):
        if args.entry:
            entry = frappe.get_cached_doc("Gate Entry",{"name":args.entry})
            if entry.is_subcontracting_order:
                self.subcontracting_orders = []
                for so in entry.subcontracting_orders:
                    self.append("subcontracting_orders",{
                        "subcontracting_order":so.subcontracting_order
                    })
                    
    @frappe.whitelist()
    def fetch_subcontracting_order_item_data_by_gate_entry(self,args):
        if args.entry:
            entry = frappe.get_cached_doc("Gate Entry",{"name":args.entry})
            if entry.items and entry.is_subcontracting_order:
                self.items = []
                for d in entry.subcontracting_details:
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
                        "subcontracting_order":d.get("subcontracting_order"),
                        "purchase_order_item":d.get("purchase_order_item"),
                        "expense_account":d.get("expense_account"),
                        "branch":d.get("branch"),
                        "cost_center":d.get("cost_center"),
                    })
                return True
    
    @frappe.whitelist()
    def _get_delivery_note_data(self,record):
        data = get_delivery_note_data_for_weighment(weighment=record)

        if data and "message" in data:
            data = data["message"]

            if data:
                self.delivery_notes = []

                for d in data:
                    self.append("delivery_notes",{
                        "delivery_note":d.get("delivery_note")
                    })
                    return True
                
            else:
                return "trigger_empty_delivery_note_validation"
            
    @frappe.whitelist()
    def _get_delivery_note_item_data(self,record):
        _data = get_delivery_note_item_data_for_weighment(weighment=record)

        if _data and "message" in _data:
            data = _data["message"]

            if data:
                self.delivery_note_details = []
                total_weight = 0.0
                for d in data:
                    total_weight += d.get("total_weight")
                    self.append("delivery_note_details",{
                        "delivery_note":d.get("delivery_note"),
                        "item":d.get("item"),
                        "item_name":d.get("item_name"),
                        "qty":d.get("qty"),
                        "uom":d.get("uom"),
                        "total_weight":d.get("total_weight")
                    })

                self.total_weight = total_weight
                self.minimum_permissible_weight = total_weight - self.allowed_lower_tolerance
                self.maximum_permissible_weight = total_weight + self.allowed_upper_tolerance

                print("!!!!!!!!!!!!!!",self.total_weight,self.allowed_lower_tolerance,self.allowed_upper_tolerance,self.minimum_permissible_weight,self.maximum_permissible_weight)
                return True
            
            else:
                return "trigger_empty_delivery_note_validation"
                
    @frappe.whitelist()
    def empty_delivery_note_validatin(self):
        count = 0
        while count < 2:
            play_audio(audio_profile="contact_with_sales_department")
            count +=1
            time.sleep(1)

        return True
    
    @frappe.whitelist()
    def needs_reweighment(self):
        for _ in range(3):
            play_audio(audio_profile="needs_reweight")
            time.sleep(1)
        
        return True

    @frappe.whitelist()
    def validate_purchase_weight(self):
        if self.entry_type == "Inward" and self.items and len(self.items)<=1 and not self.is_manual_weighment and not self.is_subcontracting_order:
            if self.enable_weight_adjustment:

                if self.net_weight < self.items[0].get("accepted_quantity"):
                    for d in self.items:
                        c_factor = frappe.db.get_value("UOM Conversion",{"uom":d.get("uom")},["conversion_factor"])
                        if c_factor:
                            d.accepted_quantity = self.net_weight/c_factor
                            d.received_quantity = self.net_weight/c_factor
                        # d.accepted_quantity = self.net_weight
                        # d.received_quantity = self.net_weight
                
                if self.net_weight > self.items[0].get("accepted_quantity"):
                    extra_weight = self.net_weight - self.items[0].get("accepted_quantity")
                    self.gross_weight -= extra_weight
                    self.net_weight -= extra_weight
                    self.weight_adjusted = 1
            
            else:
                for d in self.items:
                    c_factor = frappe.db.get_value("UOM Conversion",{"uom":d.get("uom")},["conversion_factor"])
                    if c_factor:
                        d.accepted_quantity = self.net_weight/c_factor
                        d.received_quantity = self.net_weight/c_factor
    
    @frappe.whitelist()
    def validate_sales_weight(self):
        if not self.is_manual_weighment and self.entry_type == "Outward" and self.delivery_note_details and self.is_in_progress:
            for d in self.delivery_note_details:
                if d.get("item"):
                    item = get_item_data(item_code=d.get("item"))
                    if item and "message" in item:
                        item = item["message"]
                        if item.get("custom_is_weighment_mandatory") and not (len(self.delivery_note_details) >=2):
                            conversion = frappe.db.get_value("UOM Conversion",{"uom":d.get("uom")},["conversion_factor"])
                            if conversion:
                                d.qty = self.net_weight/conversion
    
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
            if rec.entry_type == "Inward" and self.tare_weight == 0:
                play_audio(audio_profile="Tare Not Done Yet")
                # play_audio(audio_profile="system_error")
                return "trigger_weight_validation"

            if self.gross_weight <= self.tare_weight:
                play_audio(audio_profile="Tare weight cant be less than gross weight")
                return "trigger_weight_validation"
            

            self.net_weight = self.gross_weight - self.tare_weight
            self.validate_purchase_weight()
            self.validate_sales_weight()
            if self.allowed_lower_tolerance > 0:

                if self.net_weight < self.minimum_permissible_weight:
                    play_audio(audio_profile="Delivery Exception")
                    return "trigger_delivery_note_validation"
            
            if self.allowed_upper_tolerance > 0:
                
                if self.net_weight > self.maximum_permissible_weight:
                    play_audio(audio_profile="Delivery Exception")
                    return "trigger_delivery_note_validation"

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


    # @frappe.whitelist()
    # def is_new_weighment_record(self,args):
    #     if args.entry:
    #         condition = 1
    #         weighment = get_weighment_data_from_gate_entry(gate_entry=args.entry)
    #         if weighment and "message" in weighment:
    #             weighment = weighment["message"]
    #             if weighment.get("name"):
    #                 condition = 0
    #             else:
    #                 condition = 1
    #         return condition

    @frappe.whitelist()
    def is_new_weighment_record(self,args):
        if args.entry:
            try:
                data = is_new_weighment_record_for_weighment(
                    gate_entry= args.entry
                )
                if data and "message" in data:
                    data = data["message"]
                    if data == "existing_weighment_record_found":
                        return "existing_record_found"
                    
                    if data == "no_weighment_record_found":
                        return "no_weighment_record_found"
                    
                    if data == "no_gate_entry_found":
                        return "need_reweighment"
            except:
                return "need_reweighment"

    
    
    @frappe.whitelist()
    def create_new_weighment_entry(self):
        try:
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
            # entry.allowed_tolerance = self.allowed_tolerance
            entry.driver_contact = self.driver_contact
            entry.is_in_progress = 1
            entry.location = self.location
            entry.items  = self.items
            entry.purchase_orders = self.purchase_orders
            entry.subcontracting_orders = self.subcontracting_orders
            entry.subcontracting_details = self.subcontracting_details

            
            if self.driver:
                entry.driver = self.driver

            if self.tare_weight:
                entry.tare_weight = self.tare_weight

            if self.gross_weight:
                entry.gross_weight = self.gross_weight

            if self.is_manual_weighment:
                entry.is_manual_weighment = self.is_manual_weighment

            if self.is_subcontracting_order:
                entry.is_subcontracting_order = self.is_subcontracting_order
            
            if self.job_work:
                entry.job_work = self.job_work
                
            entry.save(ignore_permissions=True)
            entry.save("Submit")
            entry.get_first_print()
            
            return "weight_done"
        except:
            frappe.log_error(frappe.get_traceback(),"Gets error while creating weighment against gate entry {}".format(self.gate_entry_number))
            return "needs_reweight"
    
    @frappe.whitelist()
    def update_existing_weighment_details(self):
        if self.gate_entry_number and not ((self.gross_weight == self.tare_weight) or (self.gross_weight <= self.tare_weight)):
            record = frappe.get_value("Weighment", {"gate_entry_number": self.gate_entry_number, "is_in_progress": 1, "is_completed": 0}, order_by="creation DESC")
            if record:
                try:
                    rec = frappe.get_doc("Weighment", record)
                    outward_date_str = datetime.strftime(get_datetime(now()), "%Y-%m-%d %H:%M:%S")
                    rec.outward_date = get_datetime(outward_date_str)
                    
                    if rec.gate_entry_number and rec.entry_type == "Outward" and not rec.tare_weight and not rec.gross_weight:
                        rec.tare_weight = self.tare_weight
                    if rec.gate_entry_number and rec.entry_type == "Outward" and rec.tare_weight and not rec.gross_weight:
                        rec.gross_weight = self.gross_weight
                    if self.weight_adjusted and rec.entry_type == "Inward":
                        rec.gross_weight = self.gross_weight
                    if rec.gate_entry_number and rec.entry_type == "Inward" and not rec.tare_weight and not rec.gross_weight:
                        rec.gross_weight = self.gross_weight
                    if rec.gate_entry_number and rec.entry_type == "Inward" and not rec.tare_weight and rec.gross_weight:
                        rec.tare_weight = self.tare_weight
                    
                    
                    
                    rec.net_weight = rec.gross_weight - rec.tare_weight
                    rec.is_in_progress = 0
                    rec.is_completed = 1
                    rec.allowed_lower_tolerance = self.allowed_lower_tolerance
                    rec.allowed_upper_tolerance = self.allowed_upper_tolerance
                    rec.minimum_permissible_weight = self.minimum_permissible_weight
                    rec.maximum_permissible_weight = self.maximum_permissible_weight
                    rec.total_weight = self.total_weight
                    rec.delivery_note_details = self.delivery_note_details
                    rec.delivery_notes = self.delivery_notes
                    if self.entry_type == "Inward" and rec.items and len(rec.items)<=1:
                        if self.enable_weight_adjustment:
                            if self.net_weight < rec.items[0].get("accepted_quantity"):
                                if rec.items:
                                    for d in rec.items:
                                        c_factor = frappe.db.get_value("UOM Conversion",{"uom":d.get("uom")},["conversion_factor"])
                                        if c_factor:
                                            d.accepted_quantity = self.net_weight/c_factor
                                            d.received_quantity = self.net_weight/c_factor
                    
                        else:
                            # passing whatever net weight into accepted quantity 
                            for d in rec.items:
                                c_factor = frappe.db.get_value("UOM Conversion",{"uom":d.get("uom")},["conversion_factor"])
                                if c_factor:
                                    d.accepted_quantity = self.net_weight/c_factor
                                    d.received_quantity = self.net_weight/c_factor
                    
                    if not self.is_manual_weighment and self.entry_type == "Outward" and rec.delivery_note_details and self.is_in_progress and not self.is_subcontracting_order:
                        for d in rec.delivery_note_details:
                            if d.get("item"):
                                item = get_item_data(item_code=d.get("item"))
                                if item and "message" in item:
                                    item = item["message"]
                                    if item.get("custom_is_weighment_mandatory") and not (len(rec.delivery_note_details) >=2):
                                        conversion = frappe.db.get_value("UOM Conversion",{"uom":d.get("uom")},["conversion_factor"])
                                        d.qty = self.net_weight/conversion
                            
                    rec.save("Submit")
                    rec.get_second_print()
                    return "weight_done"
                except:
                    frappe.log_error(frappe.get_traceback(),"Gets error while updating weight of weighment {}".format(record))
                    return "needs_reweight"


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
