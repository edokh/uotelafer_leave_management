frappe.pages['balance-and-employee'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Balance and Employee Control Panel'),
		single_column: true
	});

	page.set_indicator(__('Loading...'), 'orange');

	// Create custom container for filters to guarantee visibility
	$(page.main).append(`
		<style>
			.excel-table {
				border-collapse: collapse;
				font-size: 12px !important;
			}
			.excel-table th, .excel-table td {
				padding: 0 !important;
				vertical-align: middle;
				height: 24px !important;
				max-height: 24px !important;
				overflow: hidden;
			}
			.excel-table td > div.cell-text {
				padding: 2px 6px !important;
				line-height: 20px !important;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
				height: 24px;
			}
			.excel-table input,
			.excel-table select {
				border: none !important;
				background-color: transparent !important;
				border-radius: 0 !important;
				padding: 0 6px !important;
				height: 24px !important;
				width: 100% !important;
				font-size: 12px !important;
				box-shadow: none !important;
				margin: 0 !important;
				display: block !important;
				outline: none !important;
				-webkit-appearance: none;
				-moz-appearance: none;
				appearance: none;
				line-height: 24px !important;
				vertical-align: middle;
				font-family: inherit;
			}
			.excel-table input:focus, .excel-table input:hover,
			.excel-table select:focus, .excel-table select:hover {
				background-color: var(--control-bg, #f5f5f5) !important;
			}
			.excel-table td:focus-within {
				outline: 2px solid var(--primary, #1b8feb) !important;
				outline-offset: -2px;
				z-index: 2;
				position: relative;
			}
			.excel-table select {
				background-image: url("data:image/svg+xml;utf8,<svg fill='%23666' height='16' viewBox='0 0 24 24' width='16' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/><path d='M0 0h24v24H0z' fill='none'/></svg>") !important;
				background-repeat: no-repeat !important;
				background-position: right 2px center !important;
				background-size: 16px !important;
				padding-right: 18px !important;
				cursor: pointer;
			}
			.excel-table td .btn-save-wrapper {
				padding: 2px;
				display: flex;
				justify-content: center;
				align-items: center;
				height: 24px;
			}
			.excel-table td .btn-save-wrapper button {
				padding: 1px 6px !important;
				font-size: 10px !important;
				height: 20px !important;
				line-height: 18px !important;
			}

			/* Filters design */
			#custom-filters {
				background-color: var(--card-bg, #fff) !important;
				padding: 8px 15px !important;
				border-bottom: 1px solid var(--border-color, #cbd5e0) !important;
				display: flex;
				gap: 15px;
				flex-wrap: wrap;
				align-items: flex-end;
			}
			#custom-filters .filter-wrapper {
				min-width: 180px !important;
				flex: 1;
				max-width: 220px;
			}
			#custom-filters .frappe-control {
				margin-bottom: 0 !important;
			}
			#custom-filters .frappe-control .form-group {
				margin-bottom: 0 !important;
			}
			#custom-filters .frappe-control label {
				font-size: 11px !important;
				font-weight: 600 !important;
				text-transform: uppercase !important;
				letter-spacing: 0.5px !important;
				color: var(--text-muted, #718096) !important;
				margin-bottom: 4px !important;
			}
			#custom-filters .frappe-control input,
			#custom-filters .frappe-control select {
				height: 28px !important;
				font-size: 12px !important;
				border-radius: 4px !important;
				border: 1px solid var(--border-color, #cbd5e0) !important;
				background-color: var(--modal-bg, #f7fafc) !important;
				padding: 4px 8px !important;
				appearance: auto;
				-webkit-appearance: auto;
			}
			#custom-filters .frappe-control input:focus,
			#custom-filters .frappe-control select:focus {
				border-color: var(--primary) !important;
				background-color: var(--card-bg, #fff) !important;
				box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.15) !important;
			}
		</style>
		<div id="custom-filters">
			<div class="filter-wrapper" id="filter-user"></div>
			<div class="filter-wrapper" id="filter-dept"></div>
			<div class="filter-wrapper" id="filter-emp-name"></div>
			<div class="filter-wrapper" id="filter-profile"></div>
			<div class="filter-wrapper" id="filter-type"></div>
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
	let c5 = frappe.ui.form.make_control({
		parent: $(page.main).find('#filter-type'),
		df: { fieldtype: 'Select', fieldname: 'leave_employee_type', label: __('Type'), options: '\nEmployee\nTeaching Staff' },
		render_input: true
	});

	let controls = [c1, c2, c3, c4, c5];
	controls.forEach(c => {
		c.$input.on('change', function() {
			refresh();
		});
	});

	let sort_by = null;
	let sort_asc = false;

	function refresh() {
		filters = {
			user: c1.get_value(),
			leave_department: c2.get_value(),
			leave_employee_name: c3.get_value(),
			profile_full_name: c4.get_value(),
			leave_employee_type: c5.get_value()
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

		// Helper to wrap TH content in a resizable div
		const th_resizer = (text, width=150) => `<div style="resize: horizontal; overflow: hidden; min-width: 50px; width: ${width}px; white-space: nowrap; padding: 4px 8px;">${text}</div>`;

		let table_html = `
			<div class="table-responsive" style="margin: 15px;">
				<table class="table table-bordered table-hover excel-table" style="table-layout: fixed; width: max-content;">
					<thead>
						<tr>
							<th>${th_resizer(__('Username'), 120)}</th>
							<th>${th_resizer(__('First Name'), 120)}</th>
							<th>${th_resizer(__('Middle Name'), 120)}</th>
							<th>${th_resizer(__('Last Name'), 120)}</th>
							<th>${th_resizer(__('Profile Full Name'), 200)}</th>
							<th>${th_resizer(__('Leave Employee Document'), 200)}</th>
							<th>${th_resizer(__('Leave Department'), 180)}</th>
							<th>${th_resizer(__('Type'), 140)}</th>
		`;

		leave_types.forEach(lt => {
			let caret = '';
			if (sort_by === lt) {
				caret = sort_asc ? ' &uarr;' : ' &darr;';
			}
			table_html += `<th><div class="sortable-th" data-leave-type="${lt}" style="cursor: pointer; user-select: none;" title="Click to sort">${th_resizer(lt + caret, 120)}</div></th>`;
		});

		table_html += `
							<th><div style="padding: 4px 8px;">${__('Actions')}</div></th>
						</tr>
					</thead>
					<tbody>
		`;

		users.forEach(u => {
			let dept_val = (u.leave_department || '').replace(/"/g, '&quot;');
			let type_val = u.leave_employee_type || '';

			table_html += `
				<tr data-user="${u.user}">
					<td><div class="cell-text" title="${u.user}">${u.user}</div></td>
					<td><input type="text" data-field="first_name" value="${u.first_name || ''}"></td>
					<td><input type="text" data-field="middle_name" value="${u.middle_name || ''}"></td>
					<td><input type="text" data-field="last_name" value="${u.last_name || ''}"></td>
					<td><div class="cell-text" title="${u.profile_full_name || ''}">${u.profile_full_name || ''}</div></td>
					<td><input type="text" data-field="leave_employee_name" value="${u.leave_employee_name || ''}" placeholder="${__('Leave Employee Name')}"></td>
					<td><input type="text" class="dept-input" data-field="leave_department" value="${dept_val}" list="dept-list" autocomplete="off"></td>
					<td>
						<select data-field="leave_employee_type">
							<option value="" ${type_val === '' ? 'selected' : ''}></option>
							<option value="Employee" ${type_val === 'Employee' ? 'selected' : ''}>${__('Employee')}</option>
							<option value="Teaching Staff" ${type_val === 'Teaching Staff' ? 'selected' : ''}>${__('Teaching Staff')}</option>
						</select>
					</td>
			`;

			leave_types.forEach(lt => {
				let balance = u.balances[lt] || 0.0;
				table_html += `
					<td><input type="number" data-field="balance" data-leave-type="${lt}" value="${balance}" step="any" style="text-align:right;"></td>
				`;
			});

			table_html += `
					<td>
						<div class="btn-save-wrapper">
							<button class="btn btn-primary btn-xs save-row" data-user="${u.user}" style="width: 100%;">
								${__('Save')}
							</button>
						</div>
					</td>
				</tr>
			`;
		});

		table_html += `
					</tbody>
				</table>
			</div>
		`;

		// Build datalist for department autocomplete
		frappe.call({
			method: 'frappe.client.get_list',
			args: { doctype: 'Leave Department', fields: ['name'], limit: 500 },
			callback: function(r) {
				let opts = (r.message || []).map(d => `<option value="${d.name}">`).join('');
				$(page.main).find('#table-container').html(table_html + `<datalist id="dept-list">${opts}</datalist>`);
				bind_events(data);
			}
		});
	}

	function bind_events(data) {
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

		// Bind save button events
		$(page.main).find('.save-row').on('click', function() {
			let btn = $(this);
			let user = btn.attr('data-user');
			let tr = btn.closest('tr');
			
			let first_name = tr.find('[data-field="first_name"]').val();
			let middle_name = tr.find('[data-field="middle_name"]').val();
			let last_name = tr.find('[data-field="last_name"]').val();
			let leave_employee_name = tr.find('[data-field="leave_employee_name"]').val();
			let leave_department = tr.find('[data-field="leave_department"]').val();
			let leave_employee_type = tr.find('[data-field="leave_employee_type"]').val();
			
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
					leave_employee_type: leave_employee_type,
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