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
        frm.disable_save();
        frm.events.check_weighbridge_is_empty(frm);
        // frm.events.check_card_connectivity(frm);
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
                if(r.message){
                    frappe.show_alert({message:__("Weight loss Detected"), indicator:'green'});
                    frm.events.wake_up_screen_event(frm);
                }  
            },
        }) 
    },

    wake_up_screen_event:function(frm){
        frappe.call({
            method: "wake_up_screen",
            doc: frm.doc,
            callback: function (r) {
                if(r.message){
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
                stopAudio();
                if (r.message === "weighment_already_done") {
                    stopAudio();
                    frm.events.validate_card_number(frm);
                    return
                }else if (r.message === "trigger_empty_card_validation"){
                    stopAudio();
                    frm.events.is_card_removed_already(frm);
                    return
                }else if (r.message == "trigger weight loss"){
                    stopAudio();
                    frm.events.is_card_removed_already(frm);
                    return
                }else if (r.message == "trigger_empty_delivery_note_validation") {
                    stopAudio();
                    frm.events.empty_delivery_note(frm);
                    return
                }
                else {

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
    },gate_entry_number: function(frm) {
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

                if (entry.is_manual_weighment) {
                    frm.set_value("is_manual_weighment",entry.is_manual_weighment)
                    frm.refresh_field("is_manual_weighment")
                }

                if (entry.is_subcontracting_order) {
                    frm.set_value("is_subcontracting_order",entry.is_subcontracting_order)
                    frm.refresh_field("is_subcontracting_order")
                }

                if (entry.job_work) {
                    frm.set_value("job_work",entry.job_work)
                    frm.refresh_field("job_work")
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

                if (entry.entry_type === "Outward" && !entry.is_manual_weighment) {
                    frm.set_value("item_group",entry.item_group)
                    frm.refresh_field("item_group")
                }
                
                // if (entry.allowed_tolerance) {
                //     frm.set_value("allowed_tolerance",entry.allowed_tolerance)
                //     frm.refresh_field("allowed_tolerance")
                // }
                
                frm.set_value("transporter_name",entry.transporter_name)
                frm.refresh_field("transporter_name")


                frappe.run_serially([
                    () => frm.trigger("update_date_fields"),
                    () => frm.trigger("update_existing_weighment_data"),
                    () => frm.trigger("get_delivery_note_data"),
                    () => frm.trigger("get_delivery_note_item_data"),
                    
                    () => frm.trigger("update_purchase_orders_data"),
                    () => frm.trigger("update_purchase_order_item_data"),

                    () => frm.trigger("update_subcontracting_orders_data"),
                    () => frm.trigger("update_subcontracting_order_item_data"),

                    () => frm.trigger("check_for_button")
                ]);

                // if (!frm.doc.is_manual_weighment && !frm.doc.is_subcontracting_order) {
                //     frappe.run_serially([
                //         () => frm.trigger("update_date_fields"),
                //         () => frm.trigger("update_existing_weighment_data"),
                //         () => frm.trigger("check_for_button")
                //     ]);
                // } else {
                //     frappe.run_serially([
                //         () => frm.trigger("update_date_fields"),
                //         () => frm.trigger("update_existing_weighment_data"),
                //         () => frm.trigger("get_delivery_note_data"),
                //         () => frm.trigger("get_delivery_note_item_data"),
                        
                //         () => frm.trigger("update_purchase_orders_data"),
                //         () => frm.trigger("update_purchase_order_item_data"),
    
                //         () => frm.trigger("update_subcontracting_orders_data"),
                //         () => frm.trigger("update_subcontracting_order_item_data"),
    
                //         () => frm.trigger("check_for_button")
                //     ]);
                // }
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

    update_subcontracting_orders_data:function(frm){
        frappe.call({
            method:"fetch_subcontracting_orders_data_by_gate_entry",
            doc:frm.doc,
            args:{
                entry:frm.doc.gate_entry_number,
            },
            callback:function(r){
                frm.refresh_field("subcontracting_orders")                
            }
        })
    },

    update_subcontracting_order_item_data:function(frm){
        frappe.call({
            method:"fetch_subcontracting_order_item_data_by_gate_entry",
            doc:frm.doc,
            args:{
                entry:frm.doc.gate_entry_number,
            },
            callback:function(r){
                frm.refresh_field("subcontracting_details") 
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
                frm.refresh_field("items") 
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
                    if (r.message.is_manual_weighment) {
                        frm.set_value("is_manual_weighment",r.message.is_manual_weighment)
                        frm.refresh_field("is_manual_weighment") 
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
                    frm.refresh_field("allowed_lower_tolerance")
                    frm.refresh_field("allowed_upper_tolerance")
                }    
            }
        })
    },
    

    get_delivery_note_item_data:function(frm){
        if(frm.doc.reference_record && frm.doc.entry_type === "Outward" && !frm.doc.is_manual_weighment && !frm.doc.is_subcontracting_order) {
            frappe.call({
                method:"_get_delivery_note_item_data",
                doc:frm.doc,
                args:{
                    record:frm.doc.reference_record,
                },
                callback:function(r){
                    if (r.message && r.message === "trigger_empty_delivery_note_validation") {
                        frm.events.empty_delivery_note(frm)
                        return
                    }
                    else {
                        frm.refresh_field("delivery_note_details")
                        frm.refresh_field("total_weight")
                        frm.refresh_field("minimum_permissible_weight")
                        frm.refresh_field("maximum_permissible_weight")
                    }
                }
            })
        }  
    },

    get_delivery_note_data:function(frm){
        if(frm.doc.reference_record && frm.doc.entry_type === "Outward" && !frm.doc.is_manual_weighment && !frm.doc.is_subcontracting_order) {
            console.log("triggred get_delivery_note_data----------->")
            frappe.call({
                method:"_get_delivery_note_data",
                doc:frm.doc,
                args:{
                    record:frm.doc.reference_record,
                },
                callback:function(r){
                    if (r.message) {
                        if (r.message && r.message === "trigger_empty_delivery_note_validation") {
                            frm.events.empty_delivery_note(frm)
                            return
                        }
                        else {
                            frm.refresh_field("delivery_notes")
                        } 
                    }
                }
            })
        }  
    },

     
    empty_delivery_note:function(frm) {
        frappe.call({
            method:"empty_delivery_note_validatin",
            doc:frm.doc,
            callback:function(r) {
                if (r.message) {
                    frm.events.is_card_removed_already(frm);
                }
            }
        })
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
                            if (r.message && r.message === "no_weighment_record_found"){
                                console.log("creating new entry")
                                frappe.run_serially([
                                    () => frm.trigger("update_weight_details_for_new_entry_record"),
                                    () => frm.trigger("create_new_weighment_entry"),
                                ]);
                                clearInterval(audioIntervalID);
                                stopAudio();

                            } else if (r.message && r.message === "existing_record_found"){
                                console.log("updating existing entry")
                                frappe.run_serially([
                                    () => frm.trigger("update_weight_details_for_existing_entry_record"),
                                    // () => frm.trigger("print_second_slip"),
                                    () => frm.trigger("update_existing_weighment_record"),
                                ]);
                                clearInterval(audioIntervalID);
                                stopAudio();

                            } else if (r.message && "need_reweighment") {
                                clearInterval(audioIntervalID);
                                stopAudio();
                                frm.trigger("needs_reweighment")
                            }
                            else {
                                clearInterval(audioIntervalID);
                                stopAudio();
                                frm.trigger("needs_reweighment")
                            }
                        }
                    })
                }
            }
        })
    },

    needs_reweighment: function(frm) {
        frappe.call({
            method:"needs_reweighment",
            doc:frm.doc,
            callback:function(r) {
                if (r.message) {
                    frm.events.is_card_removed_already(frm);
                }
            }
        })
    },


    // check_for_button:function(frm){
    //     console.log("called function ==> check_for_button")
    //     var audioIntervalID = null;
    
    //     function playAudio(message) {
    //         console.log(message);
    //         weighment_client.play_audio("Press green button for weight");
    //     }
    
    //     function stopAudio() {
    //         clearInterval(audioIntervalID);
    //     }

    //     playAudio("Waiting for response...");
    
    //     audioIntervalID = setInterval(function() {
    //         playAudio("Still waiting for response...");
    //     }, 9000);

    //     frappe.call({
    //         // method:"is_button_precessed",
    //         method:"weighment_client.weighment_client_utils.read_button_switch",
    //         // doc:frm.doc,
    //         callback:function(r){    
    //             console.log("callback from check_for_button ==>",r.message)            
    //             if (r.message){
    //                 frappe.show_alert({message:__("Button Press Detected"), indicator:'green'});
    //                 frappe.call({
    //                     method:"is_new_weighment_record",
    //                     doc:frm.doc,
    //                     args:{
    //                         entry:frm.doc.gate_entry_number
    //                     },
    //                     callback:function(r){                            
    //                         if (r.message){
    //                             console.log("creating new entry")
    //                             frappe.run_serially([
    //                                 () => frm.trigger("update_weight_details_for_new_entry_record"),
    //                                 () => frm.trigger("create_new_weighment_entry"),
    //                             ]);
    //                             clearInterval(audioIntervalID);
    //                             stopAudio();
    //                         }else{
    //                             console.log("updating existing entry")
    //                             frappe.run_serially([
    //                                 () => frm.trigger("update_weight_details_for_existing_entry_record"),
    //                                 // () => frm.trigger("print_second_slip"),
    //                                 () => frm.trigger("update_existing_weighment_record"),
    //                             ]);
    //                             clearInterval(audioIntervalID);
    //                             stopAudio();

    //                         }
    //                     }
    //                 })
    //             }
    //         }
    //     })
    // },


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

    print_first_slip:function(frm) {
        frappe.call({
            method:"print_first_slip",
            doc:frm.doc,
            callback:function(r) {
                if (r.message) {
                    frappe.show_alert({message:__("Print Received"), indicator:'green'});
                }
            }
        })
    },

    print_second_slip:function(frm) {
        frappe.call({
            method:"print_second_slip",
            doc:frm.doc,
            callback:function(r) {
                if (r.message) {
                    frappe.show_alert({message:__("Print Received"), indicator:'green'});
                }
            }
        })
    },

    create_new_weighment_entry:function(frm){
        frappe.call({
            method:"create_new_weighment_entry",
            doc:frm.doc,
            callback:function(r){
                if(r.message && r.message === "weight_done"){
                    frappe.show_alert({message:__("New Record Created"), indicator:'green'});
                    // frm.events.remove_card_from_machine(frm)
                    // frm.events.is_weighbridge_empty(frm)
                    frappe.run_serially([
                        // () => frm.trigger("print_first_slip"),
                        () => frm.trigger("is_card_removed_already"), 
                    ]);    
                } else if (r.message && r.message === "needs_reweight") {
                    frappe.show_alert({message:__("Needs reweight"), indicator:'red'});
                    // frm.events.remove_card_from_machine(frm)
                    // frm.events.is_weighbridge_empty(frm)
                    frappe.run_serially([
                        () => frm.trigger("needs_reweighment"),
                        () => frm.trigger("is_card_removed_already"), 
                    ]);    
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
                
                if (r.message && r.message === "weight_done") {
                    console.log("recived callback from update_existing_weighment_record ==>",r.message)
                    frappe.run_serially([
                        // () => frm.trigger("print_second_slip"),
                        () => frm.trigger("is_card_removed_already"), 
                    ]); 
                } else if (r.message && r.message === "needs_reweight") {
                    frappe.show_alert({message:__("Needs reweight"), indicator:'red'});
                    frappe.run_serially([
                        () => frm.trigger("needs_reweighment"),
                        () => frm.trigger("is_card_removed_already"), 
                    ]);
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
                    // frm.events.remove_card_from_machine_and_check_empty(frm);
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
                    
                    // localStorage.removeItem('weighment_screen_active');
                    frm.reload_doc()
                }
            },
        });
    },
    // remove_card_from_machine_and_check_empty: function(frm) {
    //     console.log("triggered function ==>, remove_card_from_machine_and_check_empty");
    //     var audioIntervalID = null;
        
    //     function playAudio(message) {
    //         console.log(message);
    //         weighment_client.play_audio(message);
    //     }
        
    //     function stopAudio() {
    //         clearInterval(audioIntervalID);
    //     }
    
    //     // Step 1: Play audio to remove the card
    //     playAudio("Please remove your card");
    
    //     audioIntervalID = setInterval(function() {
    //         playAudio("Please remove your card");
    //     }, 6000);
    
    //     // Check if the card has been removed
    //     frappe.call({
    //         method: "weighment_client.weighment_client_utils.check_card_removed",
    //         callback: function(r) {
    //             console.log("response from ==> remove_card_from_machine", r.message);
    //             if (!r.message) {
    //                 clearInterval(audioIntervalID);  // Stop the card removal audio
    //                 stopAudio();
    
    //                 // Step 2: Check if the weighbridge is empty
    //                 check_is_weighbridge_empty(frm);  // Call the weighbridge check
    //             }
    //         }
    //     });
    
    //     // Function to check if the weighbridge is empty
    //     function check_is_weighbridge_empty(frm) {
    //         console.log("triggered function ==>, check_is_weighbridge_empty");
    //         playAudio("Clear platform for next weight");
    
    //         audioIntervalID = setInterval(function() {
    //             playAudio("Clear platform for next weight");
    //         }, 6000);
    
    //         frappe.call({
    //             method: "clear_plateform_for_next_weighment",
    //             doc: frm.doc,
    //             callback: function(r) {
    //                 if (r.message) {
    //                     console.log("response from the function check_is_weighbridge_empty ==>", r.message);
    //                     frappe.show_alert({ message: __("Weight loss Detected"), indicator: 'green' });
    //                     clearInterval(audioIntervalID);  // Stop the weighbridge empty audio
    //                     stopAudio();
                        
    //                     frm.reload_doc();  // Reload the document after completion
    //                 }
    //             },
    //         });
    //     }
    // },
        
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
