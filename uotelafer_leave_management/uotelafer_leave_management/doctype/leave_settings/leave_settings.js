// Copyright (c) 2026, Computer Center of UoT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Settings", {
	refresh(frm) {
		frm.set_query("department", "approver_mappings", function(doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			if (row.formation) {
				return {
					filters: {
						formation: row.formation
					}
				};
			}
		});

		frm.set_query("department", "department_visibility", function(doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			if (row.formation) {
				return {
					filters: {
						formation: row.formation
					}
				};
			}
		});
	}
});

frappe.ui.form.on("Leave Approver Mapping", {
	formation: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "department", "");
	}
});

frappe.ui.form.on("Leave Department Visibility", {
	formation: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "department", "");
	}
});
