frappe.pages['balance-and-employee'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Balance and Employee Control Panel'),
		single_column: true
	});

	page.set_indicator(__('Loading...'), 'orange');

	frappe.call({
		method: 'uotelafer_leave_management.uotelafer_leave_management.page.balance_and_employee.balance_and_employee.get_data',
		callback: function(r) {
			if(r.message) {
				render_table(page, r.message);
				page.set_indicator(__('Ready'), 'green');
			}
		}
	});

	function render_table(page, data) {
		let leave_types = data.leave_types;
		let users = data.users;

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
						<input type="text" class="form-control input-sm update-field" 
							data-field="leave_employee_name" 
							value="${u.leave_employee_name || ''}"
							placeholder="${__('Leave Employee Name')}">
					</td>
					<td>
						<input type="text" class="form-control input-sm update-field" 
							data-field="leave_department" 
							value="${u.leave_department || ''}"
							placeholder="${__('Department')}">
					</td>
			`;

			leave_types.forEach(lt => {
				let balance = u.balances[lt] || 0.0;
				table_html += `
					<td>
						<input type="number" class="form-control input-sm update-field text-right" 
							data-field="balance" 
							data-leave-type="${lt}"
							value="${balance}" step="any">
					</td>
				`;
			});

			table_html += `</tr>`;
		});

		table_html += `
					</tbody>
				</table>
			</div>
		`;

		$(page.body).html(table_html);

		// Bind change events
		$(page.body).find('.update-field').on('change', function() {
			let $input = $(this);
			let user = $input.closest('tr').attr('data-user');
			let field = $input.attr('data-field');
			let value = $input.val();
			let leave_type = $input.attr('data-leave-type') || null;

			$input.prop('disabled', true);
			frappe.call({
				method: 'uotelafer_leave_management.uotelafer_leave_management.page.balance_and_employee.balance_and_employee.update_user_data',
				args: {
					user: user,
					field: field,
					value: value,
					leave_type: leave_type
				},
				callback: function(r) {
					$input.prop('disabled', false);
					if(!r.exc) {
						frappe.show_alert({
							message: __('Updated successfully'),
							indicator: 'green'
						});
					}
				}
			});
		});
	}
}