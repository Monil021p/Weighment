// Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Gate Entry", {
	onload: function(frm) {
		// if (!frm.doc.location) {
			// frappe.db.get_value('Weighment Profile', "Weighment Profile", 'location').then(r => {
			// 	if (r.message){
			// 		frm.set_value("location",r.message.location)
			// 	}
			// })
		// }
    },
	
	before_save:function(frm) {
		frm.events.validate_driver_contact(frm)
	},

	refresh:function(frm){
		if (frm.doc.docstatus != 1 && frm.doc.docstatus != 2 && !frm.doc.is_manual_weighment && frm.doc.branch && frm.doc.supplier) {
			if (frm.doc.is_subcontracting_order) {
				frappe.call({
					method: "get_subcontracting_orders",
					doc: frm.doc,
					args:{
						selected_supplier:frm.doc.supplier.split("~")[0]
					},
					callback: r => {
						if (r.message) {
							frm.fields_dict.subcontracting_orders.grid.update_docfield_property("subcontracting_order", "options", r.message);
							frm.refresh_field("subcontracting_orders");
						}
					}
				})
			} else if (!frm.doc.job_work) {
				frappe.call({
					method: "get_purchase_orders",
					doc: frm.doc,
					args:{
						selected_supplier:frm.doc.supplier.split("~")[0]
					},
					callback: r => {
						if (r.message) {

							frm.fields_dict.purchase_orders.grid.update_docfield_property("purchase_orders", "options", r.message);
							frm.refresh_field("purchase_orders");
							frm.refresh_field("purchase_orders");
						}
					}
				})
			} else if (frm.doc.job_work) {
				frappe.call({
					method: "get_stock_entrys",
					doc: frm.doc,
					args:{
						selected_supplier:frm.doc.supplier.split("~")[0]
					},
					callback: r => {
						if (r.message) {
							console.log("*****************",r.message)
							frm.fields_dict.stock_entrys.grid.update_docfield_property("stock_entry", "options", r.message);
							frm.refresh_field("stock_entrys");
						}
					}
				})
			}
		}
		

		if (frm.doc.docstatus != 1 && frm.doc.docstatus != 2) {
			frappe.run_serially([
			
				() => frm.trigger("get_api_data"),
				() => frm.trigger("get_branch_data"),
			]);
		}
		const $button = frm.get_field('fetch_purchase_details').$wrapper.find('button');
		$button.attr('title', 'Get Selected Purcahse Orders Items Data');
		$button.tooltip(); 
		if(!frm.doc.docstatus){
			frm.set_intro("Please put the card on scanner before saving the document") 
		}
		if (frm.doc.docstatus === 1){
			frm.toggle_display("fetch_purchase_details",false)
		} else {
			frm.toggle_display("fetch_purchase_details",true)
		}
		frm.set_df_property('items', 'cannot_add_rows', true);
		frm.set_df_property('subcontracting_order_details', 'cannot_add_rows', true);

		// frm.set_query("uom", "items", function (cdt, cdn) {
		// 	const child = locals[cdt] && locals[cdt][cdn];
		// 	if (child) {
		// 		return {
		// 			query: "get_item_uom_data",
		// 			filters: {
		// 				item: child.item_codedelivery_notes
		// 			}
		// 		};
		// 	}
		// });

		// if (!frm.doc.location) {
		// 	frappe.db.get_value('Weighment Profile', "Weighment Profile", 'location').then(r => {
		// 		if (r.message){
		// 			frm.set_value("location",r.message.location)
		// 		}
		// 	})
		// }
		
		

	},
	
	vehicle:function(frm){
		if (frm.doc.vehicle_owner === "Company Owned") {
			frm.set_value("vehicle_number",frm.doc.vehicle)
			frm.refresh_field("vehicle_number")
		} 
		else {
			frm.set_value("vehicle_number",null)
			frm.refresh_field("vehicle_number")
		}
	},

	fetch_purchase_details:function(frm){
		frappe.call({
			method:"fetch_po_item_details",
			doc:frm.doc,
			freeze: true,
            freeze_message: __("Getting Items Data..."),
			callback:function(r){
				frm.refresh_field("items")
			}
		})
	},
	fetch_subcontracting_details:function(frm){
		frappe.call({
			method:"fetch_so_item_details",
			doc:frm.doc,
			freeze: true,
            freeze_message: __("Getting Subcontracting Order Data..."),
			callback:function(r){
				frm.refresh_field("subcontracting_details")
			}
		})
	},
	
	fetch_stock_entry_details:function(frm) {
		frappe.call({
			method:"fetch_stock_entry_item_data",
			doc:frm.doc,
			freeze: true,
            freeze_message: __("Getting Stock Entry Details Data..."),
			callback:function(r){
				frm.refresh_field("stock_entry_details")
			}
		})
	},

	get_branch_data:function(frm) {
		frappe.call({
			method:"get_branches",
			doc:frm.doc,
			callback:function(r) {
				if (r.message) {
					frm.fields_dict.branch.set_data(r.message);
					frm.refresh_field("branch")
				}
			}
		})	
	},

	branch:function(frm) {
		if (frm.doc.branch) {
			frappe.run_serially([
				() => frappe.call({
					method:"get_company",
					doc:frm.doc,
					callback:function(r) {
						if (r.message) {
							frm.set_value("company",r.message)
							frm.refresh_field("company")
						}
					}
				}),

				() => frappe.call({
					method:"get_branch_abbr",
					doc:frm.doc,
					callback:function(r) {
						if (r.message) {
							frm.set_value("abbr",r.message)
							frm.refresh_field("abbr")
						}
					}
				}),

			])
		} else {
			frm.set_value("company",null)
			frm.set_value("abbr",null)
			frm.refresh_field("company")
			frm.refresh_field("abbr")
		}
		frm.set_value("supplier",null)
		frm.refresh_field("supplier")
	},

	get_api_data:function(frm) {
		frappe.call({
			method:"get_gate_entry_data",
			doc:frm.doc,
			freeze: true,
			freeze_message: __("Getting Data Via Api..."),
			callback:function(r) {
				console.log("log-----------",r.message)
				var vehicle_type = r.message.vehicle_type
				var driver = r.message.driver
				var supplier = r.message.supplier
				var vehicle = r.message.vehicle
				var transporter = r.message.transporter
				var item_group = r.message.item_group
				if (vehicle_type) {
					frm.fields_dict.vehicle_type.set_data(vehicle_type)
					frm.refresh_field("vehicle_type")	
				}
				if (driver) {
					frm.fields_dict.driver.set_data(driver)
					frm.refresh_field("driver")
				}
				if (supplier) {
					frm.fields_dict.supplier.set_data(supplier)
					frm.refresh_field("supplier")
				}
				if (vehicle) {
					frm.fields_dict.vehicle.set_data(vehicle)
					frm.refresh_field("vehicle")
				}
				if (transporter) {
					frm.fields_dict.transporter.set_data(transporter)
					frm.refresh_field("transporter")
				}
				if (item_group) {
					frm.fields_dict.item_group.set_data(item_group)
					frm.refresh_field("item_group")
				}
			}
		})
	},

	driver:function(frm) {
		if (frm.doc.driver) {
			frm.set_value("driver_name",frm.doc.driver.split("~")[1])
			frm.refresh_field("driver_name")
		} else {
			frm.set_value("driver_name",null)
			frm.refresh_field("driver_name")
		}
	},

	supplier:function(frm) {

		if (frm.doc.supplier && !frm.doc.branch) {
			frm.set_value("supplier",null)
			frm.refresh_field("supplier")
			frappe.msgprint("Please Select The Branch First")
		}

		if (frm.doc.supplier) {
			frm.set_value("supplier_name",frm.doc.supplier.split("~")[1])
			frm.refresh_field("supplier_name")
		} else {
			frm.set_value("supplier_name",null)
			frm.refresh_field("supplier_name")
		}
		if (frm.doc.docstatus != 1 && frm.doc.supplier && frm.doc.branch){
			if (frm.doc.is_subcontracting_order) {
				frappe.call({
					method: "get_subcontracting_orders",
					doc: frm.doc,
					args:{
						selected_supplier:frm.doc.supplier.split("~")[0]
					},
					callback: r => {
						if (r.message) {
							frm.fields_dict.subcontracting_orders.grid.update_docfield_property("subcontracting_order", "options", r.message);
							frm.refresh_field("subcontracting_orders");
						}
					}
				})
			} else if (!frm.doc.job_work) {
				frappe.call({
					method: "get_purchase_orders",
					doc: frm.doc,
					args:{
						selected_supplier:frm.doc.supplier.split("~")[0]
					},
					callback: r => {
						if (r.message) {

							frm.fields_dict.purchase_orders.grid.update_docfield_property("purchase_orders", "options", r.message);
							frm.refresh_field("purchase_orders");
							frm.refresh_field("purchase_orders");
						}
					}
				})
			} else if (frm.doc.job_work) {
				frappe.call({
					method: "get_stock_entrys",
					doc: frm.doc,
					args:{
						selected_supplier:frm.doc.supplier.split("~")[0]
					},
					callback: r => {
						if (r.message) {
							console.log("*****************",r.message)
							frm.fields_dict.stock_entrys.grid.update_docfield_property("stock_entry", "options", r.message);
							frm.refresh_field("stock_entrys");
						}
					}
				})
			}
		}
		// if (!frm.doc.supplier) {
		frm.clear_table("purchase_orders")
		frm.refresh_field("purchase_orders")
		frm.clear_table("subcontracting_orders")
		frm.refresh_field("subcontracting_orders")
		frm.clear_table("subcontracting_details")
		frm.refresh_field("subcontracting_details")
		frm.clear_table("items")
		frm.refresh_field("items")
		frm.clear_table("stock_entrys")
		frm.refresh_field("stock_entrys")
		frm.clear_table("stock_entry_details")
		frm.refresh_field("stock_entry_details")
		// }
	},

	transporter:function(frm) {
		if (frm.doc.transporter) {
			frm.set_value("transporter_name",frm.doc.transporter.split("~")[1])
			frm.refresh_field("transporter_name")
		} else {
			frm.set_value("transporter_name",null)
			frm.refresh_field("transporter_name")
		}
	},

	validate_driver_contact:function(frm) {
		const phone_regex = /^\d{10}$/;
		if (!phone_regex.test(frm.doc.driver_contact)) {
			frappe.msgprint(__('Please enter a valid 10 digit phone number'));
			frm.set_value('driver_contact', '');
		}
	},

	is_weighment_required:function(frm){
		if (frm.doc.is_weighment_required === "No" && frm.doc.card_number) {
			frm.set_value("card_number","")
			frm.refresh_field("card_number")
		}
	},
	item_group:function(frm) {
		if (frm.doc.entry_type === "Outward") {
			frm.events.checkWeighmentRequired(frm);
		}
	},

	checkWeighmentRequired:function(frm){
		if (frm.doc.item_group) {
			frappe.call({
				method:"check_weighment_required_details",
				doc:frm.doc,
				freeze:true,
				args:{
					selected_item_group:frm.doc.item_group
				},
				callback: r => {
					console.log("Is Weighment Required:--->",r.message)
					if (r.message) {
						frm.set_value("is_weighment_required",r.message)
						frm.refresh_field("is_weighment_required")
					}
				}
			})
		}
	},

	before_submit:function(frm) {
		if (!frm.doc.vehicle_type) {
			frappe.thorw("Please Select Vehicle Type First")
		}
		if (!frm.doc.driver_name) {
			frappe.thorw("Please Select Driver name First")
		}
		if (!frm.doc.driver_contact) {
			frappe.throw("Please Enter Driver Contact First")
		}
		if (frm.doc.vehicle_owner === "Company Owned" && !frm.doc.vehicle) {
			frappe.thorw("Please Select Vehicle First")
		}
		if (frm.doc.vehicle_owner === "Third Party" && !frm.doc.vehicle_number) {
			frappe.throw("Please Enter Vehicle Number")
		}
		frm.doc.items.forEach(element => {
			if (element.received_quantity <=0) {
				frappe.throw("Received Quantity Can't be zero")
			}
		})
	},

	is_manual_weighment:function(frm) {
		if (frm.doc.is_weighment_required) {
			frm.clear_table("purchase_orders")
			frm.clear_table("items")
			frm.refresh_field("purchase_orders"),
			frm.refresh_field("items")
		}
	},

	job_work:function(frm) {
		if (frm.doc.job_work) {
			frm.set_value("is_manual_weighment",1)
			frm.set_df_property("is_manual_weighment","read_only",true)
			frm.clear_table("purchase_orders")
			frm.clear_table("items")
			frm.refresh_field("purchase_orders"),
			frm.refresh_field("items")
		} else {
			frm.set_value("is_manual_weighment",0)
			frm.set_df_property("is_manual_weighment","read_only",false)
			frm.clear_table("stock_entrys")
			frm.clear_table("stock_entry_details")
			frm.set_value("supplier",null)
			frm.refresh_field("stock_entry")
			frm.refresh_field("supplier")
			frm.refresh_field("stock_entry_details")
		}
		frm.set_value("supplier",null)
		frm.refresh_field("supplier")
	},
	job_work_weighment_required: function (frm) {
		if (frm.doc.job_work_weighment_required === "No") {
			frm.set_value("card_number",null)
			frm.refresh_field("card_number")
		}
	}
})

// function measureNetworkLatency(callback) {
//     let startTime, endTime;
//     const url = "https://rgtest.dexciss.com"; // Use a reliable endpoint
//     startTime = new Date().getTime();

//     fetch(url, { method: 'HEAD', mode: 'no-cors' })
//         .then(() => {
//             endTime = new Date().getTime();
//             const duration = (endTime - startTime) / 1000; // in seconds
//             callback(duration);
//         })
//         .catch((error) => {
//             console.error('Error measuring network latency:', error);
//         });
// }
frappe.ui.form.on("Stock Entrys", {
    stock_entry: function(frm, cdt, cdn) {
        const child = locals[cdt][cdn];

        var existing_data = [];
        frm.doc.stock_entrys.forEach(element => {
            if (element.stock_entry && element.name !== child.name) {
                existing_data.push(element.stock_entry);
            }
        });

        if (existing_data.includes(child.stock_entry)) {
			frappe.model.set_value(cdt, cdn, "stock_entry", "");
            frappe.throw("This stock entry already exists.");
            
        } 

		frm.clear_table("stock_entry_details")
		frm.refresh_field("stock_entry_details")
    },
	
	accepted_quantity:function(frm,cdt,cdn) {
		const child = locals[cdt][cdn];
		console.log("$$$$$$$$$$$$$$")
		child.received_quantity = child.accepted_quantity + child.rejected_quantity
		refresh_field("received_quantity",cdn,"items")
	}
	
});

frappe.ui.form.on("Purchase Orders", {
    purchase_orders: function(frm, cdt, cdn) {
        const child = locals[cdt][cdn];
        console.log("selected po:--->", child.purchase_orders);

        var existing_data = [];
        frm.doc.purchase_orders.forEach(element => {
            if (element.purchase_orders && element.name !== child.name) {
                existing_data.push(element.purchase_orders);
            }
        });

        if (existing_data.includes(child.purchase_orders)) {
			frappe.model.set_value(cdt, cdn, "purchase_orders", "");
            frappe.throw("This purchase order already exists.");
            
        } 

		frm.clear_table("items")
		frm.refresh_field("items")
    },
	accepted_quantity:function(frm,cdt,cdn) {
		const child = locals[cdt][cdn];
		console.log("$$$$$$$$$$$$$$")
		child.received_quantity = child.accepted_quantity + child.rejected_quantity
		refresh_field("received_quantity",cdn,"items")
	}
	
});

frappe.ui.form.on("Purchase Details", {
	accepted_quantity:function(frm,cdt,cdn) {
		const child = locals[cdt][cdn];
		console.log("$$$$$$$$$$$$$$")
		child.received_quantity = child.accepted_quantity + child.rejected_quantity
		refresh_field("received_quantity",cdn,"items")
		if ((child.accepted_quantity + child.rejected_quantity) > child.qty) {
			// child.accepted_quantity = 0
			// child.received_quantity = 0
			// refresh_field("received_quantity",cdn,"items")
			// refresh_field("accepted_quantity",cdn,"items")
			// frappe.throw("Received Qty can't be greater than the Purchase Order Qty")
		}
		if (child.received_quantity > (child.qty - child.actual_received_qty)) {
			// child.accepted_quantity = 0
			// child.received_quantity = 0
			// refresh_field("received_quantity",cdn,"items")
			// refresh_field("accepted_quantity",cdn,"items")
			// frappe.throw("Received Qty can't be greater than the Purchase Order Qty");
		}
	},
	rejected_quantity:function(frm,cdt,cdn) {
		const child = locals[cdt][cdn];
		child.received_quantity = child.accepted_quantity + child.rejected_quantity
		refresh_field("received_quantity",cdn,"items")
		if ((child.accepted_quantity + child.rejected_quantity) > child.qty) {
			// child.rejected_quantity = 0
			child.received_quantity = child.accepted_quantity + child.rejected_quantity
			// refresh_field("received_quantity",cdn,"items")
			// refresh_field("rejected_quantity",cdn,"items")
			// frappe.throw("Received Qty can't be greater than the Purchase Order Qty")
		}
		if (child.received_quantity > (child.qty - child.actual_received_qty)) {
			// child.accepted_quantity = 0
			// child.received_quantity = 0
			// refresh_field("received_quantity",cdn,"items")
			// refresh_field("accepted_quantity",cdn,"items")
			// frappe.throw("Received Qty can't be greater than the Purchase Order Qty");
		}
	}
	
});