// Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Weighment", {
	refresh:function(frm) {

        frm.set_df_property("delivery_note_details", "cannot_add_rows", true);
		frm.set_df_property("delivery_note_details", "cannot_delete_rows", true);

        frm.trigger("make_custom_button")
	},

    make_custom_button: function(frm) {

        frm.add_custom_button(__("Print"),function(){
            if (frm.doc.is_in_progress) {
                frappe.call({
                    method:"get_first_print",
                    doc:frm.doc,
                    callback:function(r) {
                        frappe.show_alert({ message: __("printing..."), indicator: 'green' });
                    }
                })
            } else if (frm.doc.is_completed) {
                frappe.call({
                    method:"get_second_print",
                    doc:frm.doc,
                    callback:function(r) {
                        frappe.show_alert({ message: __("printing..."), indicator: 'green' });
                    }
                })
            }
        })

        if (frm.doc.update_required) {
            frm.add_custom_button(__("Sync Update"), function () {
                
                frappe.call({
                    method:"reupdate_failed_weighment_data",
                    doc:frm.doc,
                    callback:function(r) {
                        if (r.message && r.message === "Updated Sucessfully") {
                            frappe.show_alert({ message: __("Document Updated Sucessfully"), indicator: 'green' });
                        }
                        frm.reload_doc()
                    }
                })
            })
        }

        let cond = frm.doc.entry_type === "Outward" ? 1 : 0;

        if (frm.doc.is_completed) {
            frappe.db.get_single_value("Weighment Profile", "enable_maintanance_mode").then((value) => {
                if (value) {
                    frm.add_custom_button(
                        cond ? __("Reset Gross Weight") : __("Reset Tare Weight"),
                        function () {
                            if (frm.doc.entry_type === "Outward") {
                                frappe.call({
                                    method: "check_delivery_note_status",
                                    doc: frm.doc,
                                    callback: function(r) {
                                        try {
                                            if (r.message) {
                                                
                                                frappe.confirm(
                                                    __("Are you sure you want to cancel the gross weight?"),
                                                    function() {
                                                        frappe.confirm(
                                                            __("This action will clear your gross weight and net weight details"),
                                                            function() {

                                                                var dialog = new frappe.ui.Dialog({
                                                                    title: 'Authentication Required',
                                                                    fields: [
                                                                        {
                                                                            fieldname: 'user_id',
                                                                            label: 'User ID',
                                                                            fieldtype: 'Data',
                                                                            reqd: true
                                                                        },
                                                                        {
                                                                            fieldname: 'password',
                                                                            label: 'Password',
                                                                            fieldtype: 'Password',
                                                                            reqd: true
                                                                        }
                                                                    ],
                                                                    primary_action_label: 'Authenticate',
                                                                    primary_action: function () {
                                                                        var _data = dialog.get_values();
                                                        
                                                                        if (!_data.user_id || !_data.password) {
                                                                            frappe.msgprint(__('Please enter both User ID and Password'));
                                                                            return;
                                                                        }
                                                        
                                                                        frappe.call({
                                                                            method: "authenticate_user",
                                                                            doc: frm.doc,
                                                                            args: {
                                                                                user_id: _data.user_id,
                                                                                password: _data.password,
                                                                            },
                                                                            callback: function (response) {
                                                                                if (response.message) {
                                                                                    let _data = response.message;
                                                                                    if (_data.message == "Logged In") {
                                                                                        frappe.show_alert({ message: __('Authentication Successful'), indicator: 'green' });
                                                                                        if (frm.doc.delivery_notes) {
                                                                                            var delivery_notes = frm.doc.delivery_notes
                                                                                            if (delivery_notes.length > 0) {
                                                                                                frm.clear_table("delivery_notes"),
                                                                                                frm.refresh_field("delivery_notes")
                                                                                            }
                                                                                        }
                        
                                                                                        if (frm.doc.delivery_note_details) {
                                                                                            var delivery_note_details = frm.doc.delivery_note_details
                                                                                            if (delivery_note_details.length > 0) {
                                                                                                frm.clear_table("delivery_note_details"),
                                                                                                frm.refresh_field("delivery_note_details")
                                                                                            }
                                                                                        }
                                                                                        
                        
                                                                                        frm.set_value("net_weight",null)
                                                                                        frm.set_value("gross_weight",null)
                                                                                        frm.refresh_field("net_weight")
                                                                                        frm.refresh_field("gross_weight")
                                                                                        frm.set_value("is_completed",0)
                                                                                        frm.set_value("is_in_progress",1)
                                                                                        frm.refresh_field("is_in_progress")
                                                                                        frm.refresh_field("is_completed")


                                                                                        // frappe.call({
                                                                                        //     method:"is_delivery_notes_linked",
                                                                                        //     doc:frm.doc,
                                                                                        //     callback:function(r) {

                                                                                        //     }
                                                                                        // })

                                                                                        frm.doc.authenticated = true;
                                                                                        dialog.hide();
                                                                                    } else {
                                                                                        frappe.msgprint(__('Authentication Failed: ' + data.message));
                                                                                        
                                                                                    }
                                                                                } else {
                                                                                    frappe.msgprint(__('Authentication Failed'));
                                                                    
                                                                                }
                                                                            }
                                                                        });
                                                                    },
                                                                    onhide: function () {
                                                                        if (!frm.doc.authenticated) {
                                                                            
                                                                        }
                                                                    }
                                                                });
                                                                
                                                                dialog.show();

                                                            },
                                                            function() {
                                                                console.log("nooo")
                                                            }
                                                        )
                                                        console.log("User confirmed to cancel the second weight.");
                                                    },
                                                    function() {
                                                        console.log("User canceled the action.");
                                                    }
                                                );
                                                
                                            }
                                            
                                        } catch (e) {
                                            console.error("Error handling response:", e);
                                        }
                                    }
                                });

                            } else if (frm.doc.entry_type === "Inward") {
                                frappe.call({
                                    method:"check_purchase_receipt_status",
                                    doc:frm.doc,
                                    callback: function(r) {
                                        try {
                                            if (r.message && "message" in r.message) {
                                                data = r.message.message
                                                if (data.response === "purchase_receipt_submitted") {
                                                    frappe.throw({
                                                        title: __("Not Allowed"),
                                                        message: __("Not allowed to perform this action, Linked purchase receipt {0} is already submitted,Please contact with purchase department", [data.purchase_invoice])
                                                    });
                                                }
                                            } else {
                                                frappe.confirm(
                                                    __("Are you sure you want to cancel the tare weight?"),
                                                    function() {
                                                        frappe.confirm(
                                                            __("This action will clear your tare weight and net weight details"),
                                                            function() {

                                                                var dialog = new frappe.ui.Dialog({
                                                                    title: 'Authentication Required',
                                                                    fields: [
                                                                        {
                                                                            fieldname: 'user_id',
                                                                            label: 'User ID',
                                                                            fieldtype: 'Data',
                                                                            reqd: true
                                                                        },
                                                                        {
                                                                            fieldname: 'password',
                                                                            label: 'Password',
                                                                            fieldtype: 'Password',
                                                                            reqd: true
                                                                        }
                                                                    ],
                                                                    primary_action_label: 'Authenticate',
                                                                    primary_action: function () {
                                                                        var _data = dialog.get_values();
                                                        
                                                                        // Validate if user_id and password are provided
                                                                        if (!_data.user_id || !_data.password) {
                                                                            frappe.msgprint(__('Please enter both User ID and Password'));
                                                                            return;
                                                                        }
                                                        
                                                                        frappe.call({
                                                                            method: "authenticate_user",
                                                                            doc: frm.doc,
                                                                            args: {
                                                                                user_id: _data.user_id,
                                                                                password: _data.password,
                                                                            },
                                                                            callback: function (response) {
                                                                                if (response.message) {
                                                                                    let _data = response.message;
                                                                                    if (_data.message == "Logged In") {
                                                                                        frappe.show_alert({ message: __('Authentication Successful'), indicator: 'green' });
                                                                            
                        
                                                                                        frm.set_value("net_weight",null)
                                                                                        frm.set_value("gross_weight",null)
                                                                                        frm.refresh_field("net_weight")
                                                                                        frm.refresh_field("gross_weight")
                                                                                        frm.set_value("is_completed",0)
                                                                                        frm.set_value("is_in_progress",1)
                                                                                        frm.refresh_field("is_in_progress")
                                                                                        frm.refresh_field("is_completed")
                                                                                        
                                                                                        frm.doc.authenticated = true;
                                                                                        dialog.hide();
                                                                                    } else {
                                                                                        frappe.msgprint(__('Authentication Failed: ' + data.message));
                                                                                        
                                                                                    }
                                                                                } else {
                                                                                    frappe.msgprint(__('Authentication Failed'));

                                                                                }
                                                                            }
                                                                        });
                                                                    },
                                                                    onhide: function () {
                                                                        if (!frm.doc.authenticated) {
                                                                            
                                                                        }
                                                                    }
                                                                });
                                                                
                                                                dialog.show();

                                                            },
                                                            function() {
                                                                console.log("nooo")
                                                            }
                                                        )
                                                        console.log("User confirmed to cancel the second weight.");
                                                    },
                                                    function() {
                                                        console.log("User canceled the action.");
                                                    }
                                                );
                                                
                                            }
                                            
                                        } catch (e) {
                                            console.error("Error handling response:", e);
                                        }
                                        try {
                                            if (r.message && "message" in r.message) {
                                                data = r.message.message
                                                if (data.response === "purchase_receipt_submitted") {
                                                    frappe.throw({
                                                        title: __("Not Allowed"),
                                                        message: __("Not allowed to perform this action, Linked purchase receipt {0} is already submitted,Please contact with purchase department", [data.purchase_invoice])
                                                    });
                                                }
                                            }
                                        } catch (e) {
                                            console.error("Error handling response:", e);
                                        }
                                    }
                                })
                            }

                        }, __("Maintenance")
                    );
                }
            });
        }
    },
});
