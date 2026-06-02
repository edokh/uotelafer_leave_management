frappe.pages['balance-and-employee'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Balance and Employee Control Panel'),
		single_column: true
	});

	page.set_indicator(__('Loading...'), 'orange');

	// Create custom container for filters to guarantee visibility
	$(page.main).append(`
		<div id="custom-filters" style="padding: 15px; display: flex; gap: 15px; flex-wrap: wrap; background-color: var(--control-bg); border-bottom: 1px solid var(--border-color);">
			<div class="filter-wrapper" id="filter-user" style="min-width: 200px;"></div>
			<div class="filter-wrapper" id="filter-dept" style="min-width: 200px;"></div>
			<div class="filter-wrapper" id="filter-emp-name" style="min-width: 200px;"></div>
			<div class="filter-wrapper" id="filter-profile" style="min-width: 200px;"></div>
		</div>
		<div id="table-container"></div>
	`);

	let filters = {};

	let c1 = frappe.ui.form.make_control({
		parent: $(page.main).find('#filter-user'),
		df: { fieldtype: 'Link', options: 'User', fieldname: 'user', label: __('User') },
		render_input: true
	});
	let c2 = frappe.ui.form.make_control({
		parent: $(page.main).find('#filter-dept'),
		df: { fieldtype: 'Link', options: 'Leave Department', fieldname: 'leave_department', label: __('Department') },
		render_input: true
	});
	let c3 = frappe.ui.form.make_control({
		parent: $(page.main).find('#filter-emp-name'),
		df: { fieldtype: 'Data', fieldname: 'leave_employee_name', label: __('Leave Employee Name') },
		render_input: true
	});
	let c4 = frappe.ui.form.make_control({
		parent: $(page.main).find('#filter-profile'),
		df: { fieldtype: 'Data', fieldname: 'profile_full_name', label: __('Profile Name') },
		render_input: true
	});

	let controls = [c1, c2, c3, c4];
	controls.forEach(c => {
		c.$input.on('change', function() {
			refresh();
		});
	});

	let department_controls = {};
	let sort_by = null;
	let sort_asc = false;

	function refresh() {
		filters = {
			user: c1.get_value(),
			leave_department: c2.get_value(),
			leave_employee_name: c3.get_value(),
			profile_full_name: c4.get_value()
		};

		page.set_indicator(__('Loading...'), 'orange');
		frappe.call({
			method: 'uotelafer_leave_management.uotelafer_leave_management.page.balance_and_employee.balance_and_employee.get_data',
			args: { filters: filters },
			callback: function(r) {
				if(r.message) {
					render_table(r.message);
					page.set_indicator(__('Ready'), 'green');
				}
			}
		});
	}

	refresh();

	function render_table(data) {
		let leave_types = data.leave_types;
		let users = data.users;

		if (sort_by) {
			users.sort((a, b) => {
				let val_a = a.balances[sort_by] || 0.0;
				let val_b = b.balances[sort_by] || 0.0;
				if (val_a > val_b) return sort_asc ? 1 : -1;
				if (val_a < val_b) return sort_asc ? -1 : 1;
				return 0;
			});
		}

		department_controls = {};

		// Helper to wrap TH content in a resizable div
		const th_resizer = (text, width=150) => `<div style="resize: horizontal; overflow: hidden; min-width: 50px; width: ${width}px; white-space: nowrap;">${text}</div>`;

		let table_html = `
			<div class="table-responsive" style="margin: 15px;">
				<table class="table table-bordered table-hover" style="table-layout: fixed; width: max-content;">
					<thead>
						<tr>
							<th>${th_resizer(__('Username'), 120)}</th>
							<th>${th_resizer(__('First Name'), 120)}</th>
							<th>${th_resizer(__('Middle Name'), 120)}</th>
							<th>${th_resizer(__('Last Name'), 120)}</th>
							<th>${th_resizer(__('Profile Full Name'), 200)}</th>
							<th>${th_resizer(__('Leave Employee Document'), 200)}</th>
							<th>${th_resizer(__('Leave Department'), 180)}</th>
		`;

		leave_types.forEach(lt => {
			let caret = '';
			if (sort_by === lt) {
				caret = sort_asc ? ' &uarr;' : ' &darr;';
			}
			table_html += `<th><div class="sortable-th" data-leave-type="${lt}" style="cursor: pointer; user-select: none;" title="Click to sort">${th_resizer(lt + caret, 120)}</div></th>`;
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
					<td><div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${u.user}">${u.user}</div></td>
					<td>
						<input type="text" class="form-control input-sm" 
							data-field="first_name" 
							value="${u.first_name || ''}">
					</td>
					<td>
						<input type="text" class="form-control input-sm" 
							data-field="middle_name" 
							value="${u.middle_name || ''}">
					</td>
					<td>
						<input type="text" class="form-control input-sm" 
							data-field="last_name" 
							value="${u.last_name || ''}">
					</td>
					<td><div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${u.profile_full_name || ''}">${u.profile_full_name || ''}</div></td>
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

		$(page.main).find('#table-container').html(table_html);

		// Bind sorting events
		$(page.main).find('.sortable-th').on('click', function() {
			let lt = $(this).attr('data-leave-type');
			if (sort_by === lt) {
				sort_asc = !sort_asc;
			} else {
				sort_by = lt;
				sort_asc = false;
			}
			render_table(data);
		});

		// Initialize department link fields
		users.forEach(u => {
			let td = $(page.main).find(`.department-cell[data-user="${u.user}"]`);
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
		$(page.main).find('.save-row').on('click', function() {
			let btn = $(this);
			let user = btn.attr('data-user');
			let tr = btn.closest('tr');
			
			let first_name = tr.find('[data-field="first_name"]').val();
			let middle_name = tr.find('[data-field="middle_name"]').val();
			let last_name = tr.find('[data-field="last_name"]').val();
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
					first_name: first_name,
					middle_name: middle_name,
					last_name: last_name,
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