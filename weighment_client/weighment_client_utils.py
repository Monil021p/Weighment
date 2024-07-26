import json
import socket
import subprocess
import time
import cv2
import frappe
from frappe.utils import get_path
from frappe.utils.data import flt, get_datetime, get_link_to_form
import requests
import serial
from serial.tools import list_ports
# from smartcard.scard import *
import smartcard
# import smartcard.utils
from smartcard.util import toBytes, toHexString, toASCIIString
from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.CardConnectionObserver import ConsoleCardConnectionObserver
from smartcard.Exceptions import CardRequestTimeoutException
from weighment_client.api import get_child_table_data
from frappe.core.api.file import create_new_folder
from frappe import _

@frappe.whitelist()
def check_card_connectivity():
    try:
        hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
        if hresult != SCARD_S_SUCCESS:
            raise error(
                'Failed to establish context: ' + SCardGetErrorMessage(hresult))
        print('Context established!')

        try:

            hresult, readers = SCardListReaders(hcontext, [])
            if hresult != SCARD_S_SUCCESS:
                # frappe.throw(
                #     title="Failed to list readers:",
                #     msg=f"Failed to list readers: {SCardGetErrorMessage(hresult)}"
                # )
                play_audio(audio_profile="Contact EDP")
                return False
            else:
                return True
        
        finally:
            hresult = SCardReleaseContext(hcontext)
            if hresult != SCARD_S_SUCCESS:
                raise error('Failed to release context: ' +
                            SCardGetErrorMessage(hresult))
            print('Released context.')
    except Exception as e:
        pass
        # play_audio(audio_profile="")


@frappe.whitelist()
def read_smartcard():
    profile = frappe.get_cached_doc("Weighment Profile")
    default_timeout = 10
    if profile.smartcard_timeout:
        default_timeout = profile.smartcard_timeout

    try:
        hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
        if hresult != SCARD_S_SUCCESS:
            raise error(
                'Failed to establish context: ' + SCardGetErrorMessage(hresult))
        print('Context established!')

        try:

            hresult, readers = SCardListReaders(hcontext, [])
            if hresult != SCARD_S_SUCCESS:
                frappe.throw(
                    title="Failed to list readers:",
                    msg=f"Failed to list readers: {SCardGetErrorMessage(hresult)}"
                )
                raise error(
                    'Failed to list readers: ' + SCardGetErrorMessage(hresult))
            print('PCSC Readers:', readers)

            if len(readers) < 1:
                raise error('No smart card readers')
            
            print("readers:--->",readers[0])
            try:
                cardtype = AnyCardType
                cardrequest = CardRequest(timeout=None, cardType=cardtype)
                cardservice = cardrequest.waitforcard()
                
                # wake_up_weight = profile.wake_up_weight
                # if validate_weight == True:
                #     while read_weigh_bridge[0] <= wake_up_weight:
                #         cardservice.connection.disconnect()
                #         time.sleep(2)
                #     return "trigger weight loss"

                observer = ConsoleCardConnectionObserver()
                cardservice.connection.addObserver(observer)
                cardservice.connection.connect()
                apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                response, sw1, sw2 = cardservice.connection.transmit(apdu)

                if sw1 == 0x90 and sw2 == 0x00:
                    data = toHexString(response)
                    if data:
                        return data
                    
                cardservice.connection.disconnect()
                    
            except CardRequestTimeoutException:
                frappe.throw(
                    title="Card Reading Timeout:",
                    msg="The smart card reading operation timed out."
                )

        finally:
            hresult = SCardReleaseContext(hcontext)
            if hresult != SCARD_S_SUCCESS:
                raise error('Failed to release context: ' +
                            SCardGetErrorMessage(hresult))
            print('Released context.')

    except Exception as e:
        print("Exception Error:---->",e)


def get_serial_port():
    port_dict={}
    ports = list(list_ports.comports())
    
    if not ports:
        play_audio(audio_profile="Contact EDP")
        return frappe.throw("Please check for the connectivity of ports")
    for port in ports:
        # print("Port check:---->",port.product)
        # print("port description:---->",port.product)
        if port.description == "USB-Serial Controller D":
            port_dict.update({"w_gross_machine_port":port.device})
        if port.description == "USB-Serial Controller":
            port_dict.update({"bell_switch_port":port.device})
    return port_dict

@staticmethod
def execute_terminal_command(command,password=None):
    try:
        if password:
            command = f"echo '{password}' | sudo -S {command}"
        subprocess.run(command,shell=True,check=True,executable="/bin/bash")
        return True
    except subprocess.CalledProcessError as e:
        if "Module not currently loded" in str(e):
            print(f"Module not currently loaded: {command}")
        else:
            print(f"Command execution failed: {command}")
        return True
    
@staticmethod
def execute_terminal_commands_for_button_or_weighbridge(command, password=None):
    try:
        if password:
            command = f"echo '{password}' | sudo -S {command} "
        subprocess.run(command, shell=True, check=True, executable="/bin/bash")
        return True

    except subprocess.CalledProcessError as e:
        error_message = (
            f"Command Execution Failed: {command} <br>"
            f"Error Message: {e.output.decode() if e.output else 'Unknown error'} <br>"
            f"Please contact <a href='mailto:support@dexciss.com'>support@dexciss.com</a>"
        )
        print(error_message)
        return True

def get_system_password():
    profile = frappe.get_cached_doc("Weighment Profile")
    if not profile.get_password("administrator_password"):
        frappe.throw(
            f"Please set Administrator password in {get_link_to_form('Weighment Profile','Weighment Profile')}"
        )
    password = profile.get_password("administrator_password")
    return password



@frappe.whitelist()
def get_string_order_of_connected_weighbridge():
    profile = frappe.get_doc("Weighment Profile")
    port = profile.get("weighbridge_port")
    weigh_bridge_port = port
    password = get_system_password()
    command_sequence = [
        f"sudo chmod 777 {weigh_bridge_port}"
    ]
    for command in command_sequence:
        if not execute_terminal_commands_for_button_or_weighbridge(command,password):
            return False
        # self.weigh_bridge_command_executed = True

    wb_port = serial.Serial()
    
    wb_port.baudrate = profile.get("baud_rate") if profile.get("baud_rate") else frappe.throw("Please upadate baud rate on {}".format(get_link_to_form('Weighment Profile', 'Weighment Profile')))
    wb_port.bytesize = serial.EIGHTBITS
    wb_port.parity = serial.PARITY_NONE
    wb_port.stopbits = serial.STOPBITS_ONE
    wb_port.port = weigh_bridge_port
    # if wb_port.is_open:
    #     wb_port.close()
    # wb_port.open()
    
    # print("============",wb_port.read(50))
    
    try:
        if wb_port.is_open:
            wb_port.close()
        wb_port.open()
        buff = ""
        chk = False
        wb_port.write(b"S")
        while not chk:
            buff = wb_port.read(50)
            print("buff:------------>",buff)
            alphabet_order = next((char for char in buff.decode() if char.isalpha()), None)

            if alphabet_order:
                wb_port.close()
                chk = True
                
                return alphabet_order
    except Exception as e:
        print("Error:--->",e)
        return False
    
@frappe.whitelist()
def read_button_switch(port=None):
    print("Please press the button --->")
    profile = frappe.get_doc("Weighment Profile")
    port = profile.get("bell_switch_port")
    button_port_number = port
    password = get_system_password()

    command_sequence = [
        f"sudo chmod 777 {button_port_number}"
    ]

    for command in command_sequence:
        if not execute_terminal_commands_for_button_or_weighbridge(command,password):
            return False
        # self.button_command_executed = True

    button_port = serial.Serial()
    button_port.baudrate = profile.get("_baud_rate") if profile.get("_baud_rate") else frappe.throw("Please upadate baud rate ('Bell Switch') on {}".format(get_link_to_form('Weighment Profile', 'Weighment Profile')))
    button_port.timeout = 1
    button_port.bytesize = serial.EIGHTBITS
    button_port.stopbits = serial.STOPBITS_ONE
    button_port.parity = serial.PARITY_NONE
    button_port.port = button_port_number

    try:
        if button_port.is_open:
            button_port.close()
        button_port.open()
        
        x=0
        buff = ""
        while True:
            button_port.write(b"D")
            time.sleep(0.1)
            buff = button_port.read_all().decode('latin-1')
            # buff = button_port.read_all().decode('utf-8')
            if x >=5000:
                return False
            if buff == "D":
                return True
    
    except Exception as e:
        print("Error:--->",e)
        return False

def get_order_string():
    profile = frappe.get_cached_doc("Weighment Profile")
    if not profile.string_order:
        frappe.throw("Please update the String Order in doctype {} by pressing Get String Order Button ".format(get_link_to_form("Weighment Profile","Weighment Profile")))
    return profile.string_order
    

@frappe.whitelist() 
def read_weigh_bridge(port=None):
    # return 5770,10
    # # print("triggered !!!!!!!!")
    profile = frappe.get_doc("Weighment Profile")
    port = profile.get("weighbridge_port")
    order = str(get_order_string())
    weigh_bridge_port = port
    password = get_system_password()
    command_sequence = [
        f"sudo chmod 777 {weigh_bridge_port}"
    ]
    for command in command_sequence:
        if not execute_terminal_commands_for_button_or_weighbridge(command,password):
            return False

    wb_port = serial.Serial()
    wb_port.baudrate = profile.get("baud_rate") if profile.get("baud_rate") else frappe.throw("Please upadate baud rate on {}".format(get_link_to_form('Weighment Profile', 'Weighment Profile')))
    wb_port.bytesize = serial.EIGHTBITS
    wb_port.parity = serial.PARITY_NONE
    wb_port.stopbits = serial.STOPBITS_ONE
    wb_port.port = weigh_bridge_port
    try:
        if wb_port.is_open:
            wb_port.close()
        wb_port.open()
        buff = ""
        chk = False
        wb_port.write(b"S")
        while not chk:
            buff = wb_port.read(50)
            for i in range(1, len(buff) + 1):
                if buff[i - 1] == ord(order) and i > 15:
                    buff = buff[i - 7:i]
                    actual_qtl = ''.join(char for char in buff[:-3:].decode('utf-8') if char.isdigit())
                    actual_kg = ''.join(char for char in buff[-3:-1].decode('utf-8') if char.isdigit())

                    in_kg = flt(actual_qtl + actual_kg)
                    in_quintal = flt(actual_qtl + "." + actual_kg)
                    wb_port.close()
                    chk = True
                    if not in_kg or not in_quintal:
                        return 0,0
                    return in_kg, in_quintal
    except Exception as e:
        print("Error:--->",e)
        return 0,0

@frappe.whitelist()
def play_audio(audio_profile):
    print("????????????????????",audio_profile)
    import os
    import tempfile
    from playsound import playsound

    if not audio_profile:
        frappe.throw("Please check the code you have entered...")
    if frappe.get_value("Audio File Details",{"audio_profile":audio_profile},["is_enabled"]):
        audio = frappe.get_value("Audio File Details",{"audio_profile":audio_profile},["audio_file"])
        if audio:   
            attachment = frappe.get_cached_doc("File",{"file_url":audio})

            temp_file_path = os.path.join(tempfile.gettempdir(),attachment.file_name)
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(attachment.get_content())

            playsound(temp_file_path)
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)


from gtts import gTTS
import os

def google_voice(text):
    tts = gTTS(text=text, lang="hi")
    filename = "voice.mp3"
    tts.save(filename)
    os.system("mpg321 " + filename)
    os.remove(filename)


from smartcard.scard import *
import smartcard.util

@frappe.whitelist()
def check_card_removed():
    srTreeATR = \
        [0x3B, 0x77, 0x94, 0x00, 0x00, 0x82, 0x30, 0x00, 0x13, 0x6C, 0x9F, 0x22]
    srTreeMask = \
        [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]


    def printstate(state):
        reader, eventstate, atr = state
        
        if eventstate & SCARD_STATE_EMPTY:
            print('\tReader empty')
            return True



    try:
        hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
        if hresult != SCARD_S_SUCCESS:
            raise error(
                'Failed to establish context: ' +
                SCardGetErrorMessage(hresult))
        print('Context established!')

        try:
            hresult, readers = SCardListReaders(hcontext, [])
            if hresult != SCARD_S_SUCCESS:
                raise error(
                    'Failed to list readers: ' +
                    SCardGetErrorMessage(hresult))
            print('PCSC Readers:', readers)

            readerstates = []
            for i in range(len(readers)):
                readerstates += [(readers[i], SCARD_STATE_UNAWARE)]

            print('----- Current reader and card states are: -------')
            hresult, newstates = SCardGetStatusChange(hcontext, 0, readerstates)
            for i in newstates:
                printstate(i)

            print('----- Please insert or remove a card ------------')
            hresult, newstates = SCardGetStatusChange(
                                    hcontext,
                                    INFINITE,
                                    newstates)

            print('----- New reader and card states are: -----------')
            for i in newstates:
                printstate(i)

        finally:
            hresult = SCardReleaseContext(hcontext)
            if hresult != SCARD_S_SUCCESS:
                raise error(
                    'Failed to release context: ' +
                    SCardGetErrorMessage(hresult))
            print('Released context.')

        import sys
        if 'win32' == sys.platform:
            print('press Enter to continue')
            sys.stdin.read(1)

    except error as e:
        print(e)


from smartcard.scard import *
import smartcard.util

@frappe.whitelist()
def is_card_removed_already():
    

    try:
        hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
        if hresult != SCARD_S_SUCCESS:
            raise error(
                'Failed to establish context: ' +
                SCardGetErrorMessage(hresult))
        print('Context established!')

        try:
            hresult, readers = SCardListReaders(hcontext, [])
            if hresult != SCARD_S_SUCCESS:
                raise error(
                    'Failed to list readers: ' +
                    SCardGetErrorMessage(hresult))
            print('PCSC Readers:', readers)

            if len(readers) < 1:
                raise error('No smart card readers')

            for zreader in readers:
                print('Trying to perform transaction on card in', zreader)

                try:
                    hresult, hcard, dwActiveProtocol = SCardConnect(
                        hcontext,
                        zreader,
                        SCARD_SHARE_SHARED,
                        SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1)
                    if hresult != SCARD_S_SUCCESS:
                        return "card removed"
                    else:
                        return "card not removed"
                except error as message:
                    print(error, message)

        finally:
            hresult = SCardReleaseContext(hcontext)
            if hresult != SCARD_S_SUCCESS:
                raise error(
                    'failed to release context: ' +
                    SCardGetErrorMessage(hresult))
            print('Released context.')

    except error as e:
        print(e)


@frappe.whitelist()
def fetch_baud_rate():

    baud_rates_to_check = [
        110, 300, 600, 1200, 2400, 4800,
        9600, 14400, 19200, 28800, 38400,
        57600, 115200, 128000, 256000
    ]

    try:
        profile = frappe.get_doc("Weighment Profile")
        port = profile.get("weighbridge_port")
        if not port:
            print("Weighbridge port not found in profile.")
            return False
        
        weigh_bridge_port = port
        password = get_system_password()
        
        command_sequence = [
            f"sudo chmod 777 {weigh_bridge_port}"
        ]
        
        for command in command_sequence:
            if not execute_terminal_commands_for_button_or_weighbridge(command, password):
                print(f"Failed to execute command: {command}")
                return False

        for baud_rate in baud_rates_to_check:
            try:
                data = {}

                wb_port = serial.Serial(
                    port=weigh_bridge_port,
                    baudrate=baud_rate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )

                if wb_port.is_open:
                    wb_port.close()
                wb_port.open()

                wb_port.write(b"S")
                response = wb_port.read(50)
                print(f"Response at baud rate {baud_rate}: {response}")

                alphabet_order = next((char for char in response.decode(errors='ignore') if char.isalpha()), None)
                if alphabet_order:
                    wb_port.close()
                    data.update({"alphabet_order": alphabet_order, "baud_rate": baud_rate})
                    return data

                wb_port.close()

            except Exception as e:
                print(f"Error at baud rate {baud_rate}: {e}")
                continue

        print("No valid response received at any baud rate.")
        return False

    except Exception as e:
        print(f"Error in fetch_baud_rate function: {e}")
        return False
    
    
@frappe.whitelist()
def fetch_ip_address():
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
def get_updated_data(record):
    data = get_child_table_data(
        docname=record,
        child_table_fieldname="delivery_note_details",
        doctype="Weighment"
    )

    if data:
        child_data = []
        for d in data:
            data_dict = d
            to_remove_ = ["name", "owner", "creation", "modified", "modified_by", "doctype", "parent", "parenttype", "parentfield"]
            for r in to_remove_:
                if data_dict.get(r):
                    data_dict.pop(r)
            
            child_data.append(data_dict)
        return child_data
    
@frappe.whitelist(allow_guest=True)
def generate_photo(doc):
    profile = frappe.get_doc("Weighment Profile")
    camera_urls = frappe._dict()
    if len(profile.camera_details)>0:
        for cam in profile.camera_details:
            if cam.enable:
                camera_urls.update({cam.camera_name:f"rtsp://{cam.camera_user_name}:{cam.get_password('camera_admin_password')}@{cam.camera_ip_address}/{cam.stream}"})
    
    if camera_urls:
        new_width = 640
        new_height = 480
        for camera_name,cam_url in camera_urls.items():
            cap = cv2.VideoCapture(cam_url)
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame,(new_width,new_height))
                image_path = f"/tmp/{frappe.generate_hash(length=10)}.jpg"
                cv2.imwrite(image_path, frame)
                attach_image_to_doctype(doc,image_path,camera_name)
    
def attach_image_to_doctype(doc,image_path,camera_name):
    file_name = f"{doc.name}4.jpeg"
    public_path = get_path("public")
    files_folder_path = os.path.join(public_path, "files")
    if not os.path.exists(files_folder_path):
        create_new_folder(public_path, "files")
    
    file_path = os.path.join(files_folder_path, file_name)
    with open(file_path,"wb") as fp:
        with open(image_path, "rb") as img_fp:
            fp.write(img_fp.read())
    
    record = frappe.new_doc("File")
    record.file_name = file_name
    record.is_private = 0
    record.file_url = '/files/' + file_name
    record.attached_to_doctype = doc.doctype
    record.attached_to_name = doc.name
    record.save(ignore_permissions = True)
    frappe.db.commit()


@frappe.whitelist()
def get_new_card_entries():
    """
    get that records from server which are not exists on local but on server,
    make sure location field on weighment profile are not empty

    """
    profile = frappe.get_doc("Weighment Profile")
    if profile.get("is_enabled"):
    
        existing_records = []
        local_cards = frappe.get_all("Card Details",{"location":profile.get("location")},["name"])
        if local_cards:
            for card in local_cards:
                existing_records.append(card.name)
        
        filters = {"location":profile.location,"name":["not in",existing_records]}
        fields = ["name","abbr","location","branch","card_number","hex_code"]
        
        url = f"{profile.get('weighment_server_url')}/api/resource/Card Details?fields={json.dumps(fields)}&filters={json.dumps(filters)}&limit={None}"
        headers = {
            "Authorization": f"token {profile.get('api_key')}:{profile.get_password('api_secret')}"
        }

        responce = requests.get(url,headers=headers)
        if responce.status_code == 200:
            data = responce.json()
            if data:
                for d in data["data"]:
                    print("data:--->",d)
                    doc = frappe.new_doc("Card Details")
                    doc.update(d)
                    doc.db_insert(d)

@frappe.whitelist()
def get_new_gate_entries():
    
    """
    get that records from server which are not exists on local but on server,
    make sure location field on weighment profile are not empty

    """
    try:
        
        profile = frappe.get_doc("Weighment Profile")
        if profile.get("is_enabled"):

            existing_records = []
            local_gate_entries = frappe.get_all("Gate Entry",{"location":profile.get("location")},["name"])
            if local_gate_entries:
                for entry in local_gate_entries:
                    existing_records.append(entry.name)
            
            
            # meta = frappe.get_meta("Gate Entry")
            fields = ["name","branch","abbr","location","date","card_number","entry_type","vehicle_type","company","time","vehicle_owner","driver","driver_name","driver_contact","item_group","is_weighment_required","allowed_tolerance","vehicle","vehicle_number","transporter","transporter_name","purchase_order","supplier","supplier_name","items","amended_from","docstatus"]
            # field_names = [df.fieldname for df in meta.fields]
            filters = {"location":profile.location,"name":["not in",existing_records]}
            # url = f"{profile.get('weighment_server_url')}/api/resource/Gate Entry?fields={json.dumps(fields)}&filters={json.dumps(filters)}&limit={None}"
            url = f"{profile.get('weighment_server_url')}/api/resource/Gate Entry"
            params = {
                "fields": json.dumps(fields),
                "filters": json.dumps(filters)
            }

            headers = {
                "Authorization": f"token {profile.get('api_key')}:{profile.get_password('api_secret')}"
            }


            responce = requests.get(url,headers=headers,params=params)
            responce.raise_for_status()
            

            if responce.status_code == 200:
                data = responce.json()
                
                if data:
                    for d in data["data"]:

                        
                        if d.get("docstatus") != 2:
                            # _data = d
                            # items = []
                            doc = frappe.new_doc("Gate Entry")
                            doc.name = d.get("name")
                            # if d.get("entry_type") == "Inward":
                            #     _items = get_child_table_data(
                            #         doctype="Gate Entry",
                            #         docname=d.get("name"),
                            #         child_table_fieldname="items"
                            #     )
                            #     for item in _items:
                            #         item_dict = item
                            #         to_remove_ = ["name", "owner", "creation", "modified", "modified_by", "doctype", "parenttype", "parentfield"]
                            #         for r in to_remove_:
                            #             if item_dict.get(r):
                            #                 item_dict.pop(r)
                            #         items.append(item_dict)
                                
                            #     doc.items = items

                            #     print("++++++++++++++++",items)
                            #     doc.items = _items
                            #     # doc.append({"items":_items})
                            
                            # print("+++++++++++++++",_data)
                            # doc.update(_data)

                        
                        
                            doc.update(d)
                            
                            doc.db_insert(d)

    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error in api : {e}")


@frappe.whitelist()
def get_new_weighment_entries():
    """
    get that records from server which are not exists on local but on server,
    make sure location field on weighment profile are not empty

    """
    try:
        
        profile = frappe.get_doc("Weighment Profile")
        if profile.get("is_enabled"):

            existing_records = []
            local_gate_entries = frappe.get_all("Weighment",{"location":profile.get("location")},["name"])
            if local_gate_entries:
                for entry in local_gate_entries:
                    existing_records.append(entry.name)

            # meta = frappe.get_meta("Weighment")
            # field_names = [df.fieldname for df in meta.fields]
            filters = {"location":profile.location,"name":["not in",existing_records]}
            fields = ["name","branch","gate_entry_number","entry_type","vehicle_type","company","weighment_date","inward_date","outward_date","vehicle_owner","driver","driver_name","driver_contact","item_group","allowed_tolerance","vehicle","vehicle_number","transporter","transporter_name","purchase_order","supplier","supplier_name","items","amended_from","docstatus","delivery_note_details","minimum_permissible_weight","maximum_permissible_weight","total_weight","net_weight","gross_weight","tare_weight"]

            url = f"{profile.get('weighment_server_url')}/api/resource/Weighment"

            params = {
                "fields": json.dumps(fields),
                "filters": json.dumps(filters)
            }

            headers = {
                "Authorization": f"token {profile.get('api_key')}:{profile.get_password('api_secret')}"
            }

            responce = requests.get(url,headers=headers,params=params)
            responce.raise_for_status()
            if responce.status_code ==200:
                data = responce.json()
                if data:
                    for d in data["data"]:
                        if d.get("docstatus") != 2:
                            doc = frappe.new_doc("Weighment")
                            delivery_notes = get_child_table_data(
                                doctype="Weighment",
                                docname=d.get("name"),
                                child_table_fieldname="delivery_note_details"
                            )
                            if delivery_notes:
                                # doc.update({"delivery_note_details":delivery_notes})
                                for k in delivery_notes:
                                    # frappe.db.sql("""update `tabDelivery Note Details` set delivery_note = %s, item = %s, item_name = %s, qty = %s, uom = %s, total_weight = %s where parent = %s""",
                                    #             (k.get("delivery_note"),k.get("item"),k.get("item_name"),k.get("qty"),k.get("uom"),k.get("total_weight"),k.get("parent")))
                                    doc.append("delivery_note_details",{
                                        "delivery_note":k.get("delivery_note"),
                                        "item":k.get("item"),
                                        "item_name":k.get("item_name"),
                                        "qty":k.get("qty"),
                                        "uom":k.get("uom"),
                                        "total_weight":k.get("total_weight"),
                                    })
                            doc.update(d)
                            doc.save(d)

    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error in api : {e}")

    



@frappe.whitelist()
def run_get_updated_data_for_cron():
    get_new_card_entries()
    get_new_gate_entries()
    get_new_weighment_entries()


# """*******************************************************************************************************"""
# def insert_new_record(doc):
# 	PROFILE = frappe.get_doc("Weighment Profile")
# 	URL = PROFILE.get("weighment_server_url")
# 	API_KEY = PROFILE.get("api_key")
# 	API_SECRET = PROFILE.get_password("api_secret")
# 	if PROFILE.get("is_enabled"):
# 		path = f"{URL}/api/method/weighment_server.api.create_new_card_details_record" 
# 		payload = {
# 			"name": doc.name,
# 			"card_number":doc.card_number,
# 			"hex_code": doc.hex_code,
# 			"status": doc.status,
# 			"branch": doc.branch,
# 			"location": doc.location,
# 			"is_assigned": doc.is_assigned,
# 			"is_updated_on_server": doc.is_updated_on_server
# 		}

# 		headers = {
# 			"Authorization": f"token {API_KEY}:{API_SECRET}",
# 			"Content-Type": "application/json"
# 		}
# 		response = requests.post(path, headers=headers, json={"args": payload})
		
# 		if response.status_code == 200:
# 			server_response = response.json()
# 			if server_response.get("isSuccess") == 1:
# 				doc.db_set("is_updated_on_server", True)
# 			else:
# 				frappe.log_error(frappe.get_traceback(), _("Failed to Insert card details On Server"))
# 		else:
# 			frappe.log_error(frappe.get_traceback(), _("Failed to communicate with server while inserting card details on server"))

# """Cron Job For Insert Failed Card Details On Server"""
# def upload_failed_card_details():
# 	details = frappe.get_all("Card Details",{"is_updated_on_server":0},["name"])
# 	for d in details:
# 		record = frappe.get_doc("Card Details",d.name)
# 		insert_new_record(record)

# """*****************************************************************************************************************************************"""