// Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.provide("weighment_client.play_audio");

weighment_client.play_audio = function(audio_profile) {
    frappe.call({
        method: "weighment_client.weighment_client_utils.play_audio",
        args: {
            audio_profile: audio_profile
        },
        callback: function(r) {
            if (r.message) {
            }
        }
    });
};

frappe.ui.form.on("Weighment Screen", {

    refresh: function(frm) {
        if (localStorage.getItem('weighment_screen_active') === 'true') {
            let d = new frappe.ui.Dialog({
                title: 'Weighment Screen Active',
                fields: [
                    {
                        label: 'Message',
                        fieldname: 'message',
                        fieldtype: 'HTML',
                        options: '<p>There is already a Weighment Screen tab open. Please close this tab manually.</p>'
                    }
                ],
                primary_action_label: 'Go to Home Page',
                primary_action: function() {
                    window.location.href = '/app';
                }
            });
            d.show();

            return;
        } else {
            localStorage.setItem('weighment_screen_active', 'true');
        }

        frm.add_custom_button(__('Restart'), function() {
            frm.events.restart_weighment_screen(frm);
        });
        frm.disable_save();
        frm.set_df_property("driver", "read_only", 1);
        frm.set_df_property("tare_weight", "read_only", 1);
        frm.set_df_property("gross_weight", "read_only", 1);
        frm.set_df_property("net_weight", "read_only", 1);
        
        // frm.events.wake_up_screen_event(frm)
        frm.events.check_weighbridge_is_empty(frm);
        // frm.events.check_card_connectivity(frm);

        // Listen for tab close or unload to remove the active session flag
        window.addEventListener('beforeunload', function() {
            localStorage.removeItem('weighment_screen_active');
        });
    },

    check_card_connectivity:function(frm){
        frappe.call({
            method:"weighment_client.weighment_client_utils.check_card_connectivity",
            callback:function(r){
                if (r.message) {
                    frm.events.check_weighbridge_is_empty(frm);
                }
            }
        })
    },
    check_weighbridge_is_empty:function(frm){
        console.log("called function ==> check_weighbridge_is_empty")
        
        frappe.call({
            method: "check_weighbridge_is_empty",
            doc: frm.doc,
            
            callback: function (r) {
                console.log("responce from SC00000007283~Vision Associates ==>",r.message)

                if(r.message){
                    frappe.show_alert({message:__("Weight loss Detected"), indicator:'green'});
                    frm.events.wake_up_screen_event(frm);
                }  
            },
        }) 
    },

    wake_up_screen_event:function(frm){
        console.log("called function ==> wake_up_screen_event")
        frappe.call({
            method: "wake_up_screen",
            doc: frm.doc,
            callback: function (r) {
                if(r.message){
                    console.log("Weight Log:------- ",r.message)
                    frappe.show_alert({message:__("Weight Gain Detected"), indicator:'green'});
                    frm.events.check_for_card(frm);
                }  
            },
        }) 
    },

    validate_card_number:function(frm){
        console.log("triggered function ==>, validate_card_number ")
        frappe.call({
            method: "validate_card_number",
            doc: frm.doc,
            callback: function(r) {
                console.log("responce from the validate_card_number ==> ",r.message)
                if (r.message) {
                    frm.events.is_card_removed_already(frm);
                }
            }
        });
    },

    check_for_card: function(frm) {
        console.log("triggered function ==> check_for_card")
        var audioIntervalID = null;
    
        function playAudio(message) {
            console.log(message);
            weighment_client.play_audio("Please put your card on machine");
        }
    
        function stopAudio() {
            clearInterval(audioIntervalID);
        }
    
        playAudio("Waiting for response...");
    
        frappe.call({
            method: "fetch_gate_entry",
            doc: frm.doc,
            callback: function(r) {

                console.log("***************",r.message)
                if (r.message === "weighment already done") {
                    stopAudio();
                    frm.events.validate_card_number(frm);
                    return
                }else if (r.message === "trigger_empty_card_validation"){
                    stopAudio();
                    frm.events.is_card_removed_already(frm);
                    return
                }else if (r.message == "trigger weight loss"){
                    console.log("Weight loss validation triggered")
                    stopAudio();
                    frm.events.is_card_removed_already(frm);
                } else {
                    frm.set_value("gate_entry_number", r.message);
                    frm.refresh_field("gate_entry_number");
                    var message = "Received Card Number: " + r.message;
                    frappe.show_alert({ message: __(message), indicator: 'green' });
                    stopAudio();
                }
            }
        });
    
        audioIntervalID = setInterval(function() {
            playAudio("Still waiting for response...");
        }, 6000);
    
        frm.cscript.on_close = function() {
            clearInterval(audioIntervalID);
            stopAudio();
        };
    },

    gate_entry_number: function(frm) {
        if (frm.doc.gate_entry_number) {
            frappe.db.get_doc("Gate Entry",frm.doc.gate_entry_number).then((entry) => {
                if (entry.driver){
                    var driver = entry.driver.split("~")
                    
                    frm.set_value("driver",driver[0])
                    frm.refresh_field("driver")
                }
                if (entry.transporter){
                    var transporter = entry.transporter.split("~")
                    frm.set_value("transporter",transporter[0])
                    frm.refresh_field("transporter")
                }
                if (entry.supplier){
                    var supplier = entry.supplier.split("~")
                    frm.set_value("supplier",supplier[0])
                    frm.refresh_field("supplier")
                }
                frm.set_value("driver_name",entry.driver_name)
                frm.refresh_field("driver_name")
                frm.set_value("driver_contact",entry.driver_contact)
                frm.refresh_field("driver_contact")
                frm.set_value("entry_type",entry.entry_type)
                frm.refresh_field("entry_type")
                frm.set_value("company",entry.company)
                frm.refresh_field("company")
                frm.set_value("vehicle_type",entry.vehicle_type)
                frm.refresh_field("vehicle_type")
                frm.set_value("branch",entry.branch)
                frm.refresh_field("branch")
                frm.set_value("abbr",entry.abbr)
                frm.refresh_field("abbr")
                frm.set_value("location")
                frm.refresh_field("location")
                frm.set_value("vehicle_number",entry.vehicle_number)
                frm.refresh_field("vehicle_number")
                frm.set_value("enable_weight_adjustment",entry.enable_weight_adjustment)
                frm.refresh_field("enable_weight_adjustment")

                if (entry.entry_type === "Outward") {
                    frm.set_value("item_group",entry.item_group)
                    frm.refresh_field("item_group")
                }
                
                if (entry.allowed_tolerance) {
                    frm.set_value("allowed_tolerance",entry.allowed_tolerance)
                    frm.refresh_field("allowed_tolerance")
                }
                
                frm.set_value("transporter_name",entry.transporter_name)
                frm.refresh_field("transporter_name")
                frappe.run_serially([
                    () => frm.trigger("update_date_fields"),
                    () => frm.trigger("update_purchase_orders_data"),
                    () => frm.trigger("update_purchase_order_item_data"),
                    () => frm.trigger("update_existing_weighment_data"),
                    () => frm.trigger("get_delivery_note_data"),
                    () => frm.trigger("check_for_button")
                ]);
            })

        }

    },
    
    update_date_fields:function(frm){
        frappe.call({
            method:"update_date_fields_depends_on_weighment",
            doc:frm.doc,
            callback:function(r){
                frm.refresh_fields()
            }
        })
    },

    update_purchase_orders_data:function(frm){
        frappe.call({
            method:"fetch_purchase_orders_data_by_gate_entry",
            doc:frm.doc,
            args:{
                entry:frm.doc.gate_entry_number,
            },
            callback:function(r){
                frm.refresh_field("purchase_orders")
                // if (r.message){
                //     r.message.forEach(function (poi) {
                //         var childItem = frm.add_child("purchase_orders");
                //         Object.keys(poi).forEach(function (field) {
                //             childItem[field] = poi[field];
                //         });
                //     });
                //     frm.refresh_field("purchase_orders")
                // }
                
            }
        })
    },

    update_purchase_order_item_data:function(frm){
        frappe.call({
            method:"fetch_purchase_order_item_data_by_gate_entry",
            doc:frm.doc,
            args:{
                entry:frm.doc.gate_entry_number,
            },
            callback:function(r){
                if (r.message){
                    r.message.forEach(function (poi) {
                        var childItem = frm.add_child("items");
                        Object.keys(poi).forEach(function (field) {
                            childItem[field] = poi[field];
                        });
                    });
                    frm.refresh_field("items")
                }
                
            }
        })
    },


    
    update_existing_weighment_data:function(frm){
        frappe.call({
            method:"update_existing_weighment_data_by_card",
            doc:frm.doc,
            args:{
                entry:frm.doc.gate_entry_number,
            },
            callback:function(r){
                if(r.message){
                    if (r.message.reference_record) {
                        frm.set_value("reference_record",r.message.reference_record)
                        frm.refresh_field("reference_record") 
                    }
                    if (r.message.is_in_progress) {
                        frm.set_value("is_in_progress",r.message.is_in_progress)
                        frm.refresh_field("is_in_progress") 
                    }
                    if (r.message.gross_weight) {
                        frm.set_value("gross_weight",r.message.gross_weight)
                        frm.refresh_field("gross_weight")
                    }
                    if (r.message.tare_weight) {
                        frm.set_value("tare_weight",r.message.tare_weight)
                        frm.refresh_field("tare_weight") 
                    }
                    if (r.message.net_weight) {
                        frm.set_value("net_weight",r.message.net_weight)
                        frm.refresh_field("net_weight") 
                    }
                }    
            }
        })
    },

    get_delivery_note_data:function(frm){
        if(frm.doc.reference_record) {
            frappe.call({
                method:"weighment_client.weighment_client_utils.get_updated_data",
                args:{
                    record:frm.doc.reference_record,
                },
                callback:function(r){
                    if (r.message){
                        var total_weight = 0.0
                        r.message.forEach(function (di) {
                            total_weight += di.total_weight
                            var childItem = frm.add_child("delivery_note_details");
                            Object.keys(di).forEach(function (field) {
                                childItem[field] = di[field];
                            });
                        });
                        frm.refresh_field("delivery_note_details")
                        frm.set_value("total_weight",total_weight)
                        frm.set_value("minimum_permissible_weight",(total_weight - frm.doc.allowed_tolerance))
                        frm.set_value("maximum_permissible_weight",(total_weight + frm.doc.allowed_tolerance))
                        frm.refresh_field("total_weight")
                        frm.refresh_field("minimum_permissible_weight")
                        frm.refresh_field("maximum_permissible_weight")
                    }
                }
            })
        }  
    },
    

    validate_weighment_by_delivery_note:function(frm){

    },
    

    check_for_button:function(frm){
        console.log("called function ==> check_for_button")
        var audioIntervalID = null;
    
        function playAudio(message) {
            console.log(message);
            weighment_client.play_audio("Press green button for weight");
        }
    
        function stopAudio() {
            clearInterval(audioIntervalID);
        }

        playAudio("Waiting for response...");
    
        audioIntervalID = setInterval(function() {
            playAudio("Still waiting for response...");
        }, 9000);

        frappe.call({
            // method:"is_button_precessed",
            method:"weighment_client.weighment_client_utils.read_button_switch",
            // doc:frm.doc,
            callback:function(r){    
                console.log("callback from check_for_button ==>",r.message)            
                if (r.message){
                    frappe.show_alert({message:__("Button Press Detected"), indicator:'green'});
                    frappe.call({
                        method:"is_new_weighment_record",
                        doc:frm.doc,
                        args:{
                            entry:frm.doc.gate_entry_number
                        },
                        callback:function(r){                            
                            if (r.message){
                                console.log("creating new entry")
                                frappe.run_serially([
                                    () => frm.trigger("update_weight_details_for_new_entry_record"),
                                    () => frm.trigger("create_new_weighment_entry"),
                                ]);
                                clearInterval(audioIntervalID);
                                stopAudio();
                            }else{
                                console.log("updating existing entry")
                                frappe.run_serially([
                                    () => frm.trigger("update_weight_details_for_existing_entry_record"),
                                    () => frm.trigger("update_existing_weighment_record"),
                                ]);
                                clearInterval(audioIntervalID);
                                stopAudio();

                            }
                        }
                    })
                }
            }
        })
    },


    update_weight_details_for_new_entry_record:function(frm){
        console.log("frm.doc.referece_record:--->",frm.doc.gate_entry_number)

        frappe.call({
            method:"update_weight_details_for_new_entry",
            doc:frm.doc,
            args:{
                entry:frm.doc.gate_entry_number
            },
            callback:function(r){
                frm.refresh_fields()
                console.log("Updated weight field...")
            }
        })
    },

    update_weight_details_for_existing_entry_record:function(frm){
        frappe.call({
            method:"update_weight_details_for_existing_entry",
            doc:frm.doc,
            callback:function(r){
                console.log("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$",r.message)
                if (r.message === "trigger_weight_validation"){
                    // frm.events.is_weighbridge_empty(frm)
                    // frm.events.remove_card_from_machine(frm)
                    frm.events.is_card_removed_already(frm)
                    return

                }
                else if (r.message === "trigger_delivery_note_validation"){
                    console.log("^^^^^^^^triggered delivery note validation")
                    frm.events.is_card_removed_already(frm)
                    return false
                }

                frm.refresh_fields()
            }
        })
    },

    create_new_weighment_entry:function(frm){
        frappe.call({
            method:"create_new_weighment_entry",
            doc:frm.doc,
            callback:function(r){
                if(r.message){
                    frappe.show_alert({message:__("New Record Created"), indicator:'green'});
                    // frm.events.remove_card_from_machine(frm)
                    // frm.events.is_weighbridge_empty(frm)
                    frm.events.is_card_removed_already(frm)
    
                }
            }
        })
    },

    update_existing_weighment_record:function(frm){
        console.log("triggered method ==> update_existing_weighment_record")      
        frappe.call({
            method:"update_existing_weighment_details",
            doc:frm.doc,
            callback:function(r){
                
                if (r.message) {
                    console.log("recived callback from update_existing_weighment_record ==>",r.message)
                    frm.events.is_card_removed_already(frm)
                }          
            }
        })
    },
    
    is_card_removed_already:function(frm){
        console.log("triggered function:---> is_card_removed_already")
        frappe.call({
            method:"weighment_client.weighment_client_utils.is_card_removed_already",
            callback:function(r){
                if (r.message == "card removed") {
                    console.log("responce from is_card_removed_already if condition ==>",r.message)
                    frm.events.is_weighbridge_empty(frm);
                }else if (r.message == "card not removed") {
                    console.log("responce from is_card_removed_already else condition ==>",r.message)
                    frm.events.remove_card_from_machine(frm);
                }
            }
        })
    },
    remove_card_from_machine: function(frm) {
        console.log("triggered function ==>, remove_card_from_machine ")
        var audioIntervalID = null;
    
        function playAudio(message) {
            console.log(message);
            weighment_client.play_audio("Please remove your card");
        }
    
        function stopAudio() {
            clearInterval(audioIntervalID);
        }
        playAudio("Waiting for response...");
    
        audioIntervalID = setInterval(function() {
            playAudio("Still waiting for response...");
        }, 6000);
    
        frappe.call({
            
            method: "weighment_client.weighment_client_utils.check_card_removed",
            callback: function(r) {
                console.log("responce from ==> remove_card_from_machine", r.message);
                if (!r.message) {
                    clearInterval(audioIntervalID);
                    stopAudio();
                    frm.events.is_weighbridge_empty(frm);
                }
            }
        });
    },

    is_weighbridge_empty: function(frm) {
        console.log("triggered function ==>, is_weighbridge_empty")
        var audioIntervalID = null;
    
        function playAudio(message) {
            console.log(message);
            weighment_client.play_audio("Clear platform for next weight");
        }
    
        function stopAudio() {
            clearInterval(audioIntervalID);
        }
    
        playAudio("Waiting for response...");
    
        audioIntervalID = setInterval(function() {
            playAudio("Still waiting for response...");
        }, 6000);
    
        frappe.call({
            method: "clear_plateform_for_next_weighment",
            doc: frm.doc,
            callback: function(r) {
                if (r.message) {
                    console.log("responce from the function is_weighbridge_empty ==>",r.message);
                    frappe.show_alert({ message: __("Weight loss Detected"), indicator: 'green' });
                    clearInterval(audioIntervalID);
                    stopAudio();
                    
                    localStorage.removeItem('weighment_screen_active');
                    frm.reload_doc()
                }
            },
        });
    },
    restart_weighment_screen: function(frm) {
        console.log("Restarting weighment screen...");

        frappe.call({
            method: "restart_weighment_screen",
            doc: frm.doc,
            callback: function(r) {
                if (r.message) {
                    frm.reload_doc();
                    frappe.show_alert({ message: __("Weighment screen restarted"), indicator: 'green' });
                }
            }
        });
    },
    
})

// setInterval(function() {
//     frappe.call({
//         method: "weighment_client.weighment_client_utils.read_weigh_bridge",
//         callback: function(response) {
//             if (response.message && response.message.length > 0) {
//                 var weight = response.message[0];
//                 document.getElementById('currentWeight').textContent = weight;
//             }
//         }
//     });
// }, 1000);


// function updateWeight(frm) {
//     frappe.call({
//         method: "read_weigh_bridge",
//         doc:frm.doc,
//         callback: function(response) {
//             console.get("IIIIIIIIIII",response.message)
//             if (response.message) {
//                 document.getElementById('currentWeight').textContent = response.message;
//             }
//         }
//     });
// }
