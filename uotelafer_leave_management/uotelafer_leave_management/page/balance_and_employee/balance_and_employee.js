frappe.pages['balance-and-employee'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Balance and Employee Control Panel'),
		single_column: true
	});

	page.set_indicator(__('Loading...'), 'orange');

	// Setup Filters
	page.add_field({
		fieldname: 'user',
		label: __('User'),
		fieldtype: 'Link',
		options: 'User',
		change: function() { refresh(); }
	});
	page.add_field({
		fieldname: 'leave_department',
		label: __('Department'),
		fieldtype: 'Link',
		options: 'Leave Department',
		change: function() { refresh(); }
	});
	page.add_field({
		fieldname: 'leave_employee_name',
		label: __('Leave Employee Name'),
		fieldtype: 'Data',
		change: function() { refresh(); }
	});
	page.add_field({
		fieldname: 'profile_full_name',
		label: __('Profile Name'),
		fieldtype: 'Data',
		change: function() { refresh(); }
	});

	let department_controls = {};

	function refresh() {
		let filters = {
			user: page.fields_dict.user.get_value(),
			leave_department: page.fields_dict.leave_department.get_value(),
			leave_employee_name: page.fields_dict.leave_employee_name.get_value(),
			profile_full_name: page.fields_dict.profile_full_name.get_value()
		};

		page.set_indicator(__('Loading...'), 'orange');
		frappe.call({
			method: 'uotelafer_leave_management.uotelafer_leave_management.page.balance_and_employee.balance_and_employee.get_data',
			args: { filters: filters },
			callback: function(r) {
				if(r.message) {
					render_table(page, r.message);
					page.set_indicator(__('Ready'), 'green');
				}
			}
		});
	}

	refresh();

	function render_table(page, data) {
		let leave_types = data.leave_types;
		let users = data.users;

		department_controls = {};

		let table_html = `
			<div class="table-responsive" style="margin: 15px;">
				<table class="table table-bordered table-hover">
					<thead>
						<tr>
							<th>${__('Username')}</th>
							<th>${__('Full Name (User)')}</th>
							<th>${__('Profile Full Name')}</th>
							<th>${__('Leave Employee Document')}</th>
							<th>${__('Leave Department')}</th>
		`;

		leave_types.forEach(lt => {
			table_html += `<th>${lt}</th>`;
		});

		table_html += `
							<th>${__('Actions')}</th>
						</tr>
					</thead>
					<tbody>
		`;

		users.forEach(u => {
			table_html += `
				<tr data-user="${u.user}">
					<td>${u.user}</td>
					<td>${u.user_full_name}</td>
					<td>${u.profile_full_name || ''}</td>
					<td>
						<input type="text" class="form-control input-sm" 
							data-field="leave_employee_name" 
							value="${u.leave_employee_name || ''}"
							placeholder="${__('Leave Employee Name')}">
					</td>
					<td class="department-cell" data-user="${u.user}"></td>
			`;

			leave_types.forEach(lt => {
				let balance = u.balances[lt] || 0.0;
				table_html += `
					<td>
						<input type="number" class="form-control input-sm text-right" 
							data-field="balance" 
							data-leave-type="${lt}"
							value="${balance}" step="any">
					</td>
				`;
			});

			table_html += `
					<td>
						<button class="btn btn-primary btn-xs save-row" data-user="${u.user}">
							${__('Save')}
						</button>
					</td>
				</tr>
			`;
		});

		table_html += `
					</tbody>
				</table>
			</div>
		`;

		$(page.body).html(table_html);

		// Initialize department link fields
		users.forEach(u => {
			let td = $(page.body).find(`.department-cell[data-user="${u.user}"]`);
			let control = frappe.ui.form.make_control({
				parent: td,
				df: {
					fieldtype: 'Link',
					options: 'Leave Department',
					fieldname: 'leave_department',
					only_input: true
				},
				render_input: true
			});
			control.set_value(u.leave_department);
			department_controls[u.user] = control;
		});

		// Bind save button events
		$(page.body).find('.save-row').on('click', function() {
			let btn = $(this);
			let user = btn.attr('data-user');
			let tr = btn.closest('tr');
			
			let leave_employee_name = tr.find('[data-field="leave_employee_name"]').val();
			let leave_department = department_controls[user] ? department_controls[user].get_value() : '';
			
			let balances = {};
			tr.find('[data-field="balance"]').each(function() {
				let lt = $(this).attr('data-leave-type');
				balances[lt] = $(this).val();
			});

			btn.prop('disabled', true);
			frappe.call({
				method: 'uotelafer_leave_management.uotelafer_leave_management.page.balance_and_employee.balance_and_employee.save_user_row',
				args: {
					user: user,
					leave_employee_name: leave_employee_name,
					leave_department: leave_department,
					balances: balances
				},
				callback: function(r) {
					btn.prop('disabled', false);
					if(!r.exc) {
						frappe.show_alert({
							message: __('Row for {0} saved successfully', [user]),
							indicator: 'green'
						});
					}
				}
			});
		});
	}
}