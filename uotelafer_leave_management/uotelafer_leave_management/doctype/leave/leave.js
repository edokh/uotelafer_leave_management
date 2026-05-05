frappe.ui.form.on("Leave", {
	onload(frm) {
		if (frm.is_new()) {
			if (!frm.doc.date_of_application) {
				frm.set_value("date_of_application", frappe.datetime.nowdate());
			}
			
			let next_day = frappe.datetime.add_days(frappe.datetime.nowdate(), 1);
			if (!frm.doc.from_date) {
				frm.set_value("from_date", next_day);
			}
			if (!frm.doc.to_date) {
				frm.set_value("to_date", next_day);
			}
		}

		// Auto-fill employee from current user
		if (!frm.doc.employee) {
			frm.set_value("employee", frappe.session.user);
		}

		// Show all leave balances when form loads
		show_all_leave_balances(frm);
	},

	dep(frm) {
		// Clear alternative employee when dep changes
		frm.set_value("alternative_employee", "");
	},

	employee(frm) {
		if (frm.doc.employee) {
			frappe.db.get_value("Leave Employee", frm.doc.employee, ["full_name", "leave_department"])
				.then(r => {
					let values = r.message;
					if (values && values.full_name) {
						frm.set_value("employee_fullname", values.full_name);
						if (values.leave_department && !frm.doc.dep) {
							frm.set_value("dep", values.leave_department);
						}
					} else {
						// Fallback to User full_name if Leave Employee doesn't exist yet
						frappe.db.get_value("User", frm.doc.employee, "full_name")
							.then(user_res => {
								if (user_res && user_res.message) {
									frm.set_value("employee_fullname", user_res.message.full_name);
								}
							});
					}
				});
		}
		// Show all leave balances
		show_all_leave_balances(frm);
	},

	from_date(frm) {
		// Calculate days when from_date changes
		if (frm.doc.from_date && frm.doc.to_date) {
			calculate_leave_days(frm);
		}
	},

	to_date(frm) {
		// Calculate days when to_date changes
		if (frm.doc.from_date && frm.doc.to_date) {
			calculate_leave_days(frm);
		}
	},
});


function show_leave_balance(frm) {
	console.log('ayu how are you');

	frappe.call({
		method: "uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave.get_leave_balance",
		args: {
			employee: frm.doc.employee,
			leave_type: frm.doc.leave_type,
			current_leave_name: frm.doc.name
		},
		callback: function (r) {
			if (r.message !== undefined) {
				const balance = r.message;
				const leave_type = frm.doc.leave_type;

				console.log(balance.applications);
				
				// Only show message when there is no balance after selecting dates
				if (balance.total_balance <= 0 || (frm.doc.days && balance.total_balance < frm.doc.days)) {
					frappe.msgprint({
						title: __("Leave Balance"),
						indicator: "red",
						message: __("Available leave balance for {0}: <b>{1}</b> days", [
							leave_type,
							balance.total_balance.toFixed(2)
						])
					});
				}
			}
		}
	});
}

function show_all_leave_balances(frm) {
	if (!frm.doc.employee) {
		return;
	}
	
	frappe.call({
		method: "uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave.get_all_leave_balances",
		args: {
			employee: frm.doc.employee,
			current_leave_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message) {
				const balances = r.message;
				let html = '<table class="table table-striped"><thead><tr><th>' + __("Leave Type") + '</th><th>' + __("Balance") + '</th></tr></thead><tbody>';
				
				for (const [leave_type, balance] of Object.entries(balances)) {
					const color = balance >= 0 ? '#28a745' : '#dc3545';
					html += `<tr><td>${leave_type}</td><td><span style="color: ${color}; font-weight: bold;">${balance.toFixed(2)}</span></td></tr>`;
				}
				
				html += '</tbody></table>';
				
				frm.set_df_property('balance_message', 'options', html);
				frm.refresh_field('balance_message');
			}
		}
	});
}

function calculate_leave_days(frm) {
	// Call backend method to calculate leave days excluding holidays and weekends
	frappe.call({
		method: "uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave.calculate_leave_days",
		args: {
			from_date: frm.doc.from_date,
			to_date: frm.doc.to_date
		},
		callback: function(r) {
			if (r.message !== undefined) {
				frm.set_value("days", r.message);
				console.log("Leave days calculated: " + r.message);
				if (frm.doc.leave_type && frm.doc.employee) {
					show_leave_balance(frm);
				}
			}
		}
	});
}

