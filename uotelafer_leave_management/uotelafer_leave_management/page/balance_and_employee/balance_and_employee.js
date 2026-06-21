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
			.filter-toggle-wrapper {
				display: flex;
				flex-direction: column;
				justify-content: flex-end;
			}
			.filter-toggle-label {
				font-size: 11px;
				font-weight: 600;
				text-transform: uppercase;
				letter-spacing: 0.5px;
				color: var(--text-muted, #718096);
				margin-bottom: 4px;
				white-space: nowrap;
			}
			.filter-toggle-pill {
				display: flex;
				align-items: center;
				gap: 7px;
				cursor: pointer;
				user-select: none;
				height: 28px;
			}
			.filter-toggle-pill input[type=checkbox] {
				appearance: none;
				-webkit-appearance: none;
				width: 32px;
				height: 18px;
				border-radius: 9px;
				background: var(--border-color, #cbd5e0);
				transition: background 0.2s;
				position: relative;
				flex-shrink: 0;
				cursor: pointer;
				margin: 0;
				border: none !important;
				box-shadow: none !important;
				outline: none !important;
			}
			.filter-toggle-pill input[type=checkbox]::after {
				content: '';
				position: absolute;
				width: 14px;
				height: 14px;
				border-radius: 50%;
				background: white;
				top: 2px;
				left: 2px;
				transition: left 0.2s;
				box-shadow: 0 1px 3px rgba(0,0,0,0.2);
			}
			.filter-toggle-pill input[type=checkbox]:checked {
				background: var(--primary, #1b8feb);
			}
			.filter-toggle-pill input[type=checkbox]:checked::after {
				left: 16px;
			}
			.filter-toggle-pill span {
				font-size: 12px;
				color: var(--text-color, #333);
				white-space: nowrap;
			}

			/* Tabs Design */
			.tab-btn {
				background: none;
				border: none;
				border-bottom: 3px solid transparent;
				padding: 10px 20px !important;
				font-size: 14px !important;
				font-weight: 600 !important;
				color: var(--text-muted, #64748b) !important;
				cursor: pointer;
				transition: all 0.2s ease;
				margin-bottom: -2px;
				outline: none !important;
			}
			.tab-btn:hover {
				color: var(--text-color, #1e293b) !important;
			}
			.tab-btn.active {
				color: var(--primary, #1b8feb) !important;
				border-bottom-color: var(--primary, #1b8feb) !important;
			}
			.tab-container {
				display: flex;
				gap: 10px;
				margin: 15px 15px 0 15px;
				border-bottom: 2px solid var(--border-color, #e2e8f0);
			}

			/* Log Table Design */
			.log-table {
				width: 100%;
				border-collapse: separate;
				border-spacing: 0;
				margin-top: 10px;
				border: 1px solid var(--border-color, #cbd5e0);
				border-radius: 8px;
				overflow: hidden;
				background-color: var(--card-bg, #fff);
				direction: rtl;
			}
			.log-table th {
				background-color: var(--modal-bg, #f7fafc) !important;
				color: var(--text-color, #1e293b) !important;
				font-weight: 600 !important;
				text-align: right !important;
				padding: 12px 16px !important;
				font-size: 13px !important;
				border-bottom: 2px solid var(--border-color, #e2e8f0);
				height: auto !important;
			}
			.log-table td {
				padding: 12px 16px !important;
				font-size: 13px !important;
				border-bottom: 1px solid var(--border-color, #cbd5e0);
				color: var(--text-color, #334155);
				height: auto !important;
				vertical-align: middle;
				text-align: right !important;
			}
			.log-table tr:last-child td {
				border-bottom: none;
			}
			.log-table tr:hover td {
				background-color: var(--control-bg, #f8fafc);
			}
			.log-badge-user {
				display: inline-flex;
				align-items: center;
				gap: 6px;
				padding: 4px 8px;
				background-color: #f1f5f9;
				color: #475569;
				border-radius: 6px;
				font-weight: 500;
				font-size: 12px;
			}
			.log-badge-email {
				font-size: 11px;
				color: #64748b;
				display: block;
				margin-top: 2px;
			}
			.log-badge-date {
				font-size: 12px;
				color: #64748b;
			}
		</style>
		<div class="tab-container">
			<button class="tab-btn active" id="btn-tab-balances">${__('أرصدة الموظفين')}</button>
			<button class="tab-btn" id="btn-tab-accepted-leaves">${__('سجل الإجازات المقبولة')}</button>
		</div>
		<div id="custom-filters">
			<div class="filter-wrapper" id="filter-user"></div>
			<div class="filter-wrapper" id="filter-dept"></div>
			<div class="filter-wrapper" id="filter-emp-name"></div>
			<div class="filter-wrapper" id="filter-profile"></div>
			<div class="filter-wrapper" id="filter-type"></div>
			<div class="filter-toggle-wrapper">
				<div class="filter-toggle-label">${__('Balance Status')}</div>
				<label class="filter-toggle-pill">
					<input type="checkbox" id="filter-no-balance">
					<span>${__('No balance only')}</span>
				</label>
			</div>
		</div>
		<div id="table-container"></div>
		<div id="accepted-leaves-container" style="display: none; margin: 15px;"></div>
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

	let active_tab = 'balances';

	$(page.main).find('#btn-tab-balances').on('click', function() {
		$(this).addClass('active');
		$(page.main).find('#btn-tab-accepted-leaves').removeClass('active');
		active_tab = 'balances';
		$(page.main).find('#table-container').show();
		$(page.main).find('#accepted-leaves-container').hide();
		
		// Show balances-only filters
		$(page.main).find('#filter-profile').show();
		$(page.main).find('#filter-type').show();
		$(page.main).find('.filter-toggle-wrapper').show();
		
		refresh();
	});

	$(page.main).find('#btn-tab-accepted-leaves').on('click', function() {
		$(this).addClass('active');
		$(page.main).find('#btn-tab-balances').removeClass('active');
		active_tab = 'accepted_leaves';
		$(page.main).find('#table-container').hide();
		$(page.main).find('#accepted-leaves-container').show();
		
		// Hide balances-only filters
		$(page.main).find('#filter-profile').hide();
		$(page.main).find('#filter-type').hide();
		$(page.main).find('.filter-toggle-wrapper').hide();
		
		refresh();
	});

	let controls = [c1, c2, c3, c4, c5];
	controls.forEach(c => {
		c.$input.on('change', function() {
			refresh();
		});
	});

	$(page.main).find('#filter-no-balance').on('change', function() {
		refresh();
	});

	let sort_by = null;
	let sort_asc = false;

	function refresh() {
		filters = {
			user: c1.get_value(),
			leave_department: c2.get_value(),
			leave_employee_name: c3.get_value(),
			profile_full_name: c4.get_value(),
			leave_employee_type: c5.get_value(),
			no_balance: $(page.main).find('#filter-no-balance').is(':checked') ? 1 : 0
		};

		page.set_indicator(__('Loading...'), 'orange');
		if (active_tab === 'balances') {
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
		} else {
			frappe.call({
				method: 'uotelafer_leave_management.uotelafer_leave_management.page.balance_and_employee.balance_and_employee.get_accepted_leaves',
				args: { filters: filters },
				callback: function(r) {
					if(r.message) {
						render_accepted_leaves(r.message);
						page.set_indicator(__('Ready'), 'green');
					}
				}
			});
		}
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

	function render_accepted_leaves(data) {
		let container = $(page.main).find('#accepted-leaves-container');
		container.empty();

		if (data.length === 0) {
			container.html(`
				<div style="text-align: center; padding: 30px; color: var(--text-muted, #718096); font-size: 14px; background-color: var(--card-bg, #fff); border: 1px solid var(--border-color, #cbd5e0); border-radius: 8px;">
					📁 ${__('لا توجد إجازات مقبولة')}
				</div>
			`);
			return;
		}

		let table_html = `
			<div class="table-responsive">
				<table class="log-table">
					<thead>
						<tr>
							<th style="width: 120px; text-align: right;">${__('رقم الإجازة')}</th>
							<th style="text-align: right;">${__('اسم الموظف')}</th>
							<th style="text-align: right;">${__('نوع الإجازة')}</th>
							<th style="width: 120px; text-align: right;">${__('من تاريخ')}</th>
							<th style="width: 120px; text-align: right;">${__('إلى تاريخ')}</th>
							<th style="width: 100px; text-align: right;">${__('المدة')}</th>
							<th style="text-align: right;">${__('تم القبول بواسطة')}</th>
							<th style="width: 180px; text-align: right;">${__('تاريخ القبول')}</th>
						</tr>
					</thead>
					<tbody>
		`;

		data.forEach(row => {
			let duration_str = row.is_time_leave ? `${row.number_of_hours} ${__('ساعات')}` : `${row.days} ${__('أيام')}`;
			let doc_link = `/app/leave/${row.name}`;
			
			let approver_str = '-';
			if (row.approved_by) {
				let name_display = row.approved_by_name || row.approved_by;
				let email_display = row.approved_by_email ? `<span class="log-badge-email">${row.approved_by_email}</span>` : '';
				approver_str = `
					<div>
						<span class="log-badge-user">${name_display}</span>
						${email_display}
					</div>
				`;
			}

			let approved_on_str = row.approved_on ? frappe.datetime.str_to_user(row.approved_on) : '-';

			table_html += `
				<tr>
					<td><a href="${doc_link}" target="_blank" style="font-weight: bold; color: var(--primary, #1b8feb);">${row.name}</a></td>
					<td><b>${row.employee_fullname || row.employee}</b></td>
					<td>
						${row.leave_type}
						${row.is_time_leave ? `<br><span style="font-size: 11px; padding: 2px 6px; background: #e0e7ff; color: #3730a3; border-radius: 4px;">${__('إجازة زمنية')}</span>` : ''}
					</td>
					<td>${row.from_date}</td>
					<td>${row.to_date}</td>
					<td><b>${duration_str}</b></td>
					<td>${approver_str}</td>
					<td><span class="log-badge-date">${approved_on_str}</span></td>
				</tr>
			`;
		});

		table_html += `
					</tbody>
				</table>
			</div>
		`;

		container.html(table_html);
	}
}