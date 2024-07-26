// Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Weighment", {
	refresh:function(frm) {
        frm.set_df_property("delivery_note_details", "cannot_add_rows", true);
		frm.set_df_property("delivery_note_details", "cannot_delete_rows", true);
        let cond;
        if (frm.doc.entry_type === "Outward") {
            cond = 1
        } else {
            cond = 0
        }

        if (frm.doc.is_completed && frm.doc.entry_type === "Outward") {
            frm.page.set_secondary_action(
                cond ? __("Reset Gross Weight"): __("Reset Tare Weight"),
                function () {
                    if (frm.doc.delivery_note_details) {
                        delivery_notes = frm.doc.delivery_note_details
                        if (delivery_notes.length>0){
                            frappe.call({
                                method:"update_delivery_note_details",
                                doc:frm.doc,
                                callback:function(r){
                                    if (r.message) {
                                        frappe.warn(
                                            __("Are you sure?"),
                                            __('This action will clear your weight details.'),
                                                () => {
                                                    frm.clear_table("delivery_note_details"),
                                                    frm.refresh_field("delivery_note_details")
                                                    if (frm.doc.entry_type === "Inward") {
                                                        frm.set_value("tare_weight",null)
                                                        frm.refresh_field("tare_weight")
                                                        frm.set_value("net_weight",null)
                                                        frm.refresh_field("net_weight")
                                                        frm.set_value("is_completed",false)
                                                        frm.refresh_field("is_completed")
                                                        frm.set_value("is_in_progress",true)
                                                        frm.refresh_field("is_in_progress")
                                                        frm.save("Submit")
                                                    } else if (frm.doc.entry_type === "Outward") {
                                                        frm.set_value("gross_weight",null)
                                                        frm.refresh_field("gross_weight")
                                                        frm.set_value("net_weight",null)
                                                        frm.refresh_field("net_weight")
                                                        frm.set_value("is_completed",false)
                                                        frm.refresh_field("is_completed")
                                                        frm.set_value("is_in_progress",true)
                                                        frm.refresh_field("is_in_progress")
                                                        frm.save("Submit")
                                                    }
                                                },
                                            __("Proceed"),
                                            false
                                        )
                                    }
                                }
                            })
                        }
                    }
                }
            )
        }  
	},
});
