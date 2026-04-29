frappe.ui.form.on('Bulk Leave Balance Tool', {
	refresh: function(frm) {

		// Load Employees Button
		frm.add_custom_button('Load Employees', function() {
			frappe.call({
				method: 'uotelafer_leave_management.uotelafer_leave_management.doctype.bulk_leave_balance_tool.bulk_leave_balance_tool.get_all_employees',
				callback: function(r) {
					frm.clear_table('employees');

					r.message.forEach(emp => {
						let row = frm.add_child('employees');
						row.employee = emp.employee;
						// set both fields: `employee_fullname` for our field and `employee_name` for Frappe link formatters
						row.employee_fullname = emp.employee_fullname;
						row.employee_name = emp.employee_fullname;
						// auto-select the row so user can quickly create transactions
						row.selected = 1;
					});

					frm.refresh_field('employees');
				}
			});
		});

		// Create Transactions Button
		frm.add_custom_button('Create Leave Balances', function() {
			frappe.call({
				method: 'uotelafer_leave_management.uotelafer_leave_management.doctype.bulk_leave_balance_tool.bulk_leave_balance_tool.create_leave_balances',
				args: {
					doc: frm.doc
				},
				callback: function(r) {
					if (r && r.message) {
						if (r.message.errors && r.message.errors.length) {
							frappe.msgprint({
								message: r.message.errors.join('\n'),
								title: 'Errors'
							});
						} else {
							frappe.msgprint((r.message.created || 0) + ' Leave Balance Transactions created');
						}
					} else {
						frappe.msgprint('Done successfully');
					}
				}
			});
		});
	}
});