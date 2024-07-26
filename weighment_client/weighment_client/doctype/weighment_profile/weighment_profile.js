// Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Weighment Profile", {

    validate: function(frm) {
        // Counter for is_primary checkboxes
        let primary_count = 0;

        frm.doc.branch_details.forEach(function(row) {
            if (row.is_primary) {
                primary_count++;
            }
        });

        if (primary_count > 1) {
            frappe.msgprint(__('Only one branch can be marked as primary.'));
            frappe.validated = false; // Prevents form submission
        }
    },
	refresh:function(frm) {
        frappe.call({
			method: "get_locations",
			doc: frm.doc,
			callback: function(r) {
				if (r.message) {
					frm.fields_dict.location.set_data(r.message)
				}
			}
		});

        if (frm.doc.location){
			frappe.call({
				method: "get_branch_data",
				doc: frm.doc,
				args:{
					location:frm.doc.location
				},
				callback: r => {
					if (r.message) {
						frm.fields_dict.branch_details.grid.update_docfield_property("branch", "options", r.message);
        				frm.refresh_field("branch_details");
					}
				}
			})
		}
        

        // frappe.call({
		// 	method: "get_location_names",
		// 	doc: frm.doc,
		// 	callback: function(r) {
		// 		if (r.message) {
		// 			frm.fields_dict.location.set_data(r.message)
		// 		}
		// 	}
		// });

        frappe.call({
			method: "get_weighbridge_uom",
			doc: frm.doc,
			callback: function(r) {
				if (r.message) {
					frm.fields_dict.weighbridge_uom.set_data(r.message)
				}
			}
		});
	},

    location:function(frm) {
        if (frm.doc.location){
			frappe.call({
				method: "get_branch_data",
				doc: frm.doc,
				args:{
					location:frm.doc.location
				},
				callback: r => {
					if (r.message) {
						frm.fields_dict.branch_details.grid.update_docfield_property("branch", "options", r.message);
        				frm.refresh_field("branch_details");
					} else {
                        frappe.msgprint("To update branch data please update location into branch on server")
                    }
				}
			})
		}
    },
    update_audio_profiles:function(frm) {
        let audioProfileField = frappe.meta.get_docfield('Audio File Details', 'audio_profile', frm.docname);
        let options = audioProfileField.options.split('\n');

        let existingOptions = frm.doc.audio_file_details.map(row => row.audio_profile);
        options.forEach(option => {
            if (!existingOptions.includes(option)) {
                let newRow = frm.add_child('audio_file_details');
                newRow.audio_profile = option;
            }
        });
        frm.refresh_field('audio_file_details');
    },

    // branch:function(frm){
    //     if (frm.doc.branch) {
    //         frappe.run_serially([
    //             () => frm.trigger("get_company"),
    //             () => frm.trigger("get_abbr"),
    //             () => frm.trigger("get_location"),
    //         ]);
    //     } else {
    //         frm.set_value("location",null)
    //         frm.refresh_field("location")
    //         frm.set_value("abbr",null)
    //         frm.refresh_field("abbr")
    //         frm.set_value("company",null)
    //         frm.refresh_field("company")
    //     }
    // },

    // get_location:function(frm){
    //     frappe.call({
    //         method: "get_location_name",
    //         doc: frm.doc,
    //         args:{
    //             selected_branch:frm.doc.branch
    //         },
    //         callback: function(r) {
    //             if (r.message) {
    //                 frm.set_value("location",r.message)
    //                 frm.refresh_field("location")
    //             }
    //         }
    //     });
    // },
    // get_company:function(frm){
    //     frappe.call({
    //         method: "get_branch_company",
    //         doc: frm.doc,
    //         args:{
    //             selected_branch:frm.doc.branch
    //         },
    //         callback: function(r) {
    //             if (r.message) {
    //                 frm.set_value("company",r.message)
    //                 frm.refresh_field("company")
    //             }
    //         }
    //     });
    // },
    // get_abbr:function(frm){
    //     frappe.call({
    //         method: "get_branch_abbr",
    //         doc: frm.doc,
    //         args:{
    //             selected_branch:frm.doc.branch
    //         },
    //         callback: function(r) {
    //             if (r.message) {
    //                 frm.set_value("abbr",r.message)
    //                 frm.refresh_field("abbr")
    //             }
    //         }
    //     });
    // },



    read_port:function(frm){
        frappe.call({
            method:"fetch_port_location",
            doc:frm.doc,
            callback(r){
                frappe.msgprint(r.message)
            }
        })
    },
    fetch_ip_address(frm){
        frappe.call({
            method:"fetch_ip_address",
            doc:frm.doc,
            callback(r){
                if(r.message){
                    frm.set_value("system_ip_address",r.message)
                    frm.refresh_field("system_ip_address")
                }
            }
        })
    },
    fetch_admin(frm){
        frappe.call({
            method:"fetch_admin",
            doc:frm.doc,
            callback(r){
                if(r.message){
                    frm.set_value("administrator_user",r.message)
                    frm.refresh_field("administrator_user")
                }
            }
        })
    },
    check_password(frm){
        frappe.call({
            method:"get_pass",
            doc:frm.doc,
            callback(r){
                if(r.message){
                    frappe.msgprint(r.message)
                }
            }
        })
    },

    get_string_order(frm){
        frappe.call({
            method:"weighment_client.weighment_client_utils.get_string_order_of_connected_weighbridge",
            callback:function(r){
                if (r.message){
                    frm.set_value("string_order",r.message)
                    frm.refresh_field("string_order")
                }
            }
        })
    },
    
    fetch_baud_rate:function(frm){
        frappe.call({
            method:"weighment_client.weighment_client_utils.fetch_baud_rate",
            callback:function(r){
                let msg = __("Baud Rate: ");
                msg += ""
                msg += r.message.baud_rate
                msg += "<br>";
                msg += __("String Order: ");
                msg += ""
                msg += r.message.alphabet_order
                frappe.msgprint(msg)
                console.log("baud_rate_found:--->",r.message.baud_rate)
            }
        })
    },

    update_conversion_table:function(frm){
        frappe.call({
            method:"update_conversion_table",
            doc:frm.doc,
            callback:function(r){
                if (r.message) {
                    frm.refresh_field("weighment_uom")
                    frm.refresh_field("uom_conversion")
                }
            }
        })
    },
});
frappe.ui.form.on("Branch Table",{
    branch:function(frm, cdt, cdn) {
        const child = locals[cdt][cdn];
        if (child.branch) {
            frappe.run_serially([
                () => frappe.call({
                    method:"get_branch_company",
                    doc:frm.doc,
                    args:{
                        selected_branch:child.branch
                    },
                    callback:function(r){
    
                        if (r.message) {
                            child.company = r.message
                            refresh_field("company",cdn,"branch_details")
                        }
                    }
                }),
                () => frappe.call({
                    method:"get_branch_abbr",
                    doc:frm.doc,
                    args:{
                        selected_branch:child.branch
                    },
                    callback:function(r){
                        if (r.message) {
                            child.abbr = r.message
                            refresh_field("abbr",cdn,"branch_details")
                        }
                    }
                })
            ]);
        } else {
            child.company = null
            refresh_field("company",cdn,"branch_details")
            child.abbr = null
            refresh_field("abbr",cdn,"branch_details")

        }
    },
})

// frappe.ui.form.on("Camera Details", {
//     enable: function(frm, cdt, cdn) {
//         const child = locals[cdt][cdn];
//         if (child.enable) {
//             // Set the stream field value based on the number of rows already added
//             var streamValue = "stream" + (frm.doc.__children.length + 1);
//             frappe.model.set_value(cdt, cdn, "stream", streamValue);
//         }
//     }
// });