// Copyright (c) 2024, Dexciss Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Gate Entry", {
	onload: function(frm) {
        measureNetworkLatency(function(duration) {
            const threshold = 1.0; // Adjust the threshold as needed (in seconds)
            if (duration > threshold) {
                frappe.msgprint(__('Your internet speed seems slow. It took {0} seconds to contact the server.', [duration.toFixed(2)]));
            }
        });
    },
	
	before_save:function(frm) {
		frm.events.validate_driver_contact(frm)
	},

	refresh:function(frm){
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

		// frm.set_query("uom", "items", function (cdt, cdn) {
		// 	const child = locals[cdt] && locals[cdt][cdn];
		// 	if (child) {
		// 		return {
		// 			query: "get_item_uom_data",
		// 			filters: {
		// 				item: child.item_code
		// 			}
		// 		};
		// 	}
		// });
		
		

	},
	// get_po_item_uom_data:function(frm) {
	// 	frappe.call
	// },

	
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
		if (frm.doc.supplier) {
			frm.set_value("supplier_name",frm.doc.supplier.split("~")[1])
			frm.refresh_field("supplier_name")
		} else {
			frm.set_value("supplier_name",null)
			frm.refresh_field("supplier_name")
		}
		if (frm.doc.docstatus != 1 && frm.doc.supplier && frm.doc.branch){
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
					}
				}
			})
		}
		if (!frm.doc.supplier) {
			frm.clear_table("purchase_orders")
			frm.refresh_field("purchase_orders")
			frm.clear_table("items")
			frm.refresh_field("items")
		}
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
})

function measureNetworkLatency(callback) {
    let startTime, endTime;
    const url = "https://rgtest.dexciss.com"; // Use a reliable endpoint
    startTime = new Date().getTime();

    fetch(url, { method: 'HEAD', mode: 'no-cors' })
        .then(() => {
            endTime = new Date().getTime();
            const duration = (endTime - startTime) / 1000; // in seconds
            callback(duration);
        })
        .catch((error) => {
            console.error('Error measuring network latency:', error);
        });
}

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



// class GateEntryController extends frappe.ui.form.Controller {
//     refresh() {
// 		// this.getBranches();
// 		this.getSuppliers();
// 		this.getItemGroups();
// 		this.getVehicleTypes();
// 		this.getVehicle();
// 		this.getTrnasporter();
// 		// this.getPurchaseOrders();
// 		this.getMultiplePurchaseOrders();
// 		this.getDriverData();
		
//     }

// 	branch(){
// 		// this.getComponyName();
// 		this.getMultiplePurchaseOrders()

// 	}

// 	transporter(){
// 		this.getTransporterName();

// 	}

// 	purchase_order(){
		// frappe.run_serially([
		// 	// () => this.frm.trigger("getSupplier"),
		// 	// () => this.frm.trigger("getSupplierName"),
		// 	// () => this.frm.trigger("getPoItems")
		// ]);
// 		// this.getSupplier();
		
// 	}

// 	vehicle_owner(){
// 		this.frm.set_value("driver",null)
// 		this.frm.set_value("driver_name",null)
// 		this.frm.set_value("vehicle",null)
// 		this.frm.refresh_field("driver")
// 		this.frm.refresh_field("driver_name")
// 		this.frm.refresh_field("vehicle")
// 	}

// 	// supplier(){
// 	// 	this.getSupplierName();
// 	// 	this.getPoItems();
// 	// }
// 	item_group(){
// 		this.checkWeighmentRequired();
// 		// this.getAllowedTolerance();
// 	}

// 	driver(){
// 		this.getDriverName();
// 	}
// 	supplier(){
// 		this.getSupplierName()
// 		this.getMultiplePurchaseOrders()
// 	}

// 	// getAllowedTolerance(){
// 	// 	if (this.frm.doc.item_group) {
// 	// 		frappe.call({
// 	// 			method:"get_allowed_tolerance",
// 	// 			doc:this.frm.doc,
// 	// 			args:{
// 	// 				selected_item_group:this.frm.doc.item_group
// 	// 			},
// 	// 			callback: r => {
// 	// 				this.frm.set_value("allowed_tolerance",r.message)
// 	// 				this.frm.refresh_field("allowed_tolerance")
// 	// 			}
// 	// 		})
// 	// 	} else {
// 	// 		this.frm.set_value("allowed_tolerance",0.0)
// 	// 		this.frm.refresh_field("allowed_tolerance")
// 	// 	}
// 	// }

// 	getSuppliers(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method:"get_supplier",
// 				doc:this.frm.doc,
// 				callback: r => {
// 					if (r.message){
// 						// console.log("*********************",r.message)
// 						this.frm.fields_dict.supplier.set_data(r.message);
// 						this.frm.refresh_field("supplier")
// 					}
// 				}
// 			})
// 		}
// 	}

// 	getDriverData(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method:"get_vehical_drivers",
// 				doc:this.frm.doc,
// 				callback: r => {
// 					if (r.message){
// 						this.frm.fields_dict.driver.set_data(r.message);
// 						this.frm.refresh_field("driver")
// 					}
// 				}
// 			})
// 		}
// 	}

// 	getDriverName(){
// 		if(this.frm.doc.driver){
// 			var driver = this.frm.doc.driver.split("~")
// 			frappe.call({
// 				method:"get_driver_name",
// 				doc:this.frm.doc,
// 				args:{
// 					selected_driver:driver[0]
// 				},
// 				freeze: true,
// 				freeze_message: __("Fetching driver name..."),
// 				callback: r => {
// 					if(r.message){
// 						this.frm.set_value("driver_name",r.message)
// 						this.frm.refresh_field("driver_name")
// 					}
// 				}
// 			})
// 		}else{
// 			this.frm.set_value("driver_name",null)
// 			this.frm.refresh_field("driver_name")
// 		}
// 	}

	// checkWeighmentRequired(){
	// 	if (this.frm.doc.item_group) {
	// 		frappe.call({
	// 			method:"check_weighment_required_details",
	// 			doc:this.frm.doc,
	// 			freeze:true,
				
	// 			args:{
	// 				selected_item_group:this.frm.doc.item_group
	// 			},
	// 			callback: r => {
	// 				console.log("Is Weighment Required:--->",r.message)
	// 				if (r.message) {
	// 					this.frm.set_value("is_weighment_required",r.message)
	// 					this.frm.refresh_field("is_weighment_required")
	// 				}
	// 			}
	// 		})
	// 	}
	// }

// 	getPoItems(){
// 		if (this.frm.doc.purchase_order){
// 			frappe.call({
// 				method:"get_po_items",
// 				doc:this.frm.doc,
// 				args:{
// 					selected_po:this.frm.doc.purchase_order
// 				},
// 				callback: r =>{
// 					if (r.message){
// 						const frm = this.frm;
// 						this.frm.clear_table("items")
// 						r.message.forEach(function (poi) {
// 							console.log("poi:---->",poi)
// 							var childItem = frm.add_child("items");
// 							Object.keys(poi).forEach(function (field) {
// 								childItem[field] = poi[field];
// 							});
// 						});
// 						this.frm.refresh_field("items")
// 					}
// 					// this.frm.refresh()
// 				}
// 			})
// 		} else {
// 			this.frm.clear_table("items")
// 			this.frm.refresh_field("items")
// 		}
// 	}

// 	getBranches(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method:"get_branch_data",
// 				doc:this.frm.doc,
// 				callback: r => {
// 					if (r.message){
// 						this.frm.fields_dict.branch.set_data(r.message);
// 						this.frm.refresh_field("branch")
// 					}
// 				}
// 			})
// 		}
// 	}

// 	getItemGroups(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method: "get_item_groups",
// 				// async: false,
// 				doc: this.frm.doc,
// 				callback: r => {
// 					if (r.message) {
// 						this.frm.fields_dict.item_group.set_data(r.message);
// 						this.frm.refresh_field("item_group")
// 					}
// 				}
// 			});
// 		}
//     }

// 	getVehicleTypes(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method: "get_vehicle_types",
// 				// async: false,
// 				doc:this.frm.doc,
// 				callback: r => {
// 					if (r.message) {
// 						this.frm.fields_dict.vehicle_type.set_data(r.message);
// 						this.frm.refresh_field("vehicle_type")
// 					}
// 				}
// 			})
// 		}
// 	}

// 	getVehicle(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method: "get_vehicle",
// 				// async: false,
// 				doc:this.frm.doc,
// 				callback: r => {
// 					if (r.message) {
// 						this.frm.fields_dict.vehicle.set_data(r.message);
// 						this.frm.refresh_field("vehicle")
// 					}
// 				}
// 			})
// 		}
// 	}

// 	getTrnasporter(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method: "get_transporter",
// 				// async: false,
// 				doc:this.frm.doc,
// 				callback: r => {
// 					if (r.message) {
// 						this.frm.fields_dict.transporter.set_data(r.message);
// 						this.frm.refresh_field("transporter")
// 					}
// 				}
// 			})
// 		}
// 	}

// 	// getSupplier(){
// 	// 	if (this.frm.doc.purchase_order){
// 	// 		frappe.call({
// 	// 			method: "get_supplier",
// 	// 			// async: false,
// 	// 			doc:this.frm.doc,
// 	// 			args:{
// 	// 				selected_po:this.frm.doc.purchase_order
// 	// 			},
// 	// 			freeze:true,
// 	// 			freeze_message: __("Fetching supplier..."),
// 	// 			callback: r => {
// 	// 				if (r.message) {
// 	// 					this.frm.set_value("supplier",r.message);
// 	// 					this.frm.refresh_field("supplier")
// 	// 				}
// 	// 			}
// 	// 		})
// 	// 	}else{
// 	// 		this.frm.set_value("supplier",null)
// 	// 		this.frm.refresh_field("supplier")
// 	// 	}
// 	// }

// 	getPurchaseOrders(){
// 		if (this.frm.doc.docstatus != 1){
// 			frappe.call({
// 				method: "get_purchase_orders",
// 				doc: this.frm.doc,
// 				// async: false,
// 				callback: r => {
// 					if (r.message) {
// 						this.frm.fields_dict.purchase_order.set_data(r.message);
// 						this.frm.refresh_field("purchase_order")
// 					}
// 				}
// 			})
// 		}
// 	}

// 	getMultiplePurchaseOrders(){
		// if (this.frm.doc.docstatus != 1 && this.frm.doc.supplier && this.frm.doc.branch){
		// 	console.log("***********************",this.frm.doc.supplier.split("~")[0])
		// 	frappe.call({
		// 		method: "get_purchase_orders",
		// 		doc: this.frm.doc,
		// 		args:{
		// 			selected_supplier:this.frm.doc.supplier.split("~")[0]
		// 		},
		// 		callback: r => {
		// 			console.log("***********************ww")
		// 			if (r.message) {
		// 				console.log("***********************")
		// 				this.frm.fields_dict.purchase_orders.grid.update_docfield_property("purchase_orders", "options", r.message);
        // 				this.frm.refresh_field("purchase_orders");
		// 			}
		// 		}
		// 	})
		// }
// 	}

// 	getComponyName(){
// 		if(this.frm.doc.branch){
// 			frappe.call({
// 				method:"get_company_name",
// 				doc:this.frm.doc,
// 				args:{
// 					selected_branch:this.frm.doc.branch
// 				},
// 				freeze: true,
// 				freeze_message: __("Fetching company name..."),
// 				callback: r => {
// 					if (r.message){
// 						this.frm.set_value("company",r.message)
// 						this.frm.refresh_field("branch")
// 					}
// 				}
// 			})
// 		}else{
// 			this.frm.set_value("company",null)
// 			this.frm.refresh_field("company")
// 			this.frm.set_value("item_group",null)
// 			this.frm.refresh_field("item_group")
// 		}
// 	}

// 	getSupplierName(){
// 		if (this.frm.doc.supplier){
// 			var supplier = this.frm.doc.supplier.split("~")[0]
// 			frappe.call({
// 				method:"get_supplier_name",
// 				doc:this.frm.doc,
// 				args:{
// 					selected_supplier:supplier
// 				},
// 				freeze: true,
// 				freeze_message: __("Fetching supplier name..."),
// 				callback: response => {
// 					if (response.message) {
// 						this.frm.set_value("supplier_name",response.message)
// 						this.frm.refresh_field("supplier_name")
// 					}
// 				}
// 			})
// 		}else{
// 			this.frm.set_value("supplier_name",null)
// 			this.frm.refresh_field("supplier_name")
// 		}
// 	}

// 	getTransporterName(){
// 		if(this.frm.doc.transporter){
// 			var transporter = this.frm.doc.transporter.split("~")
// 			frappe.call({
// 				method:"get_transporter_name",
// 				doc:this.frm.doc,
// 				args:{
// 					selected_transporter:transporter[0]
// 				},
// 				freeze: true,
// 				freeze_message: __("Fetching transporter name..."),
// 				callback: r => {
// 					if(r.message){
// 						this.frm.set_value("transporter_name",r.message)
// 						this.frm.refresh_field("transporter_name")
// 					}
// 				}
// 			})
// 		}else{
// 			this.frm.set_value("transporter_name",null)
// 			this.frm.refresh_field("transporter_name")
// 		}
// 	}
	
// }

// extend_cscript(cur_frm.cscript, new GateEntryController({ frm: cur_frm }));


