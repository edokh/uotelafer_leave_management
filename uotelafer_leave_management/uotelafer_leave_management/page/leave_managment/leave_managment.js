frappe.pages['leave-managment'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true
	});

	wrapper.leave_page = new LeaveManagementPage(wrapper);
}

class LeaveManagementPage {
	constructor(wrapper) {
		this.page = wrapper.page;
		this.wrapper = $(wrapper).find('.layout-main-section');
		$(wrapper).find('.page-head').hide();
		this.user_roles = {};
		this.current_tab = 'my_leaves';

		frappe.require('leave_managment.css', () => {
			this.init();
		});
	}

	async init() {
		// Fetch roles
		let r = await frappe.call({ method: "uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_user_roles" });
		this.user_roles = r.message || {};

		this.user_fullname = frappe.session.user_fullname;
		try {
			let u_res = await frappe.db.get_value("Leave Employee", frappe.session.user, "full_name");
			if (u_res && u_res.message && u_res.message.full_name) {
				this.user_fullname = u_res.message.full_name;
			}
		} catch (e) {}

		// Load departments and leave types for forms
		let [dept_res, type_res, emp_res] = await Promise.all([
			frappe.call({ method: "uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_departments" }),
			frappe.call({ method: "uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_leave_types" }),
			frappe.call({ method: "frappe.client.get_list", args: { doctype: "Leave Employee", fields: ["name", "full_name"], limit_page_length: 0 } })
		]);
		this.departments = dept_res.message || [];
		this.leave_types = type_res.message || [];
		this.leave_employees = emp_res.message || [];

		// Determine default tab
		if (this.user_roles.is_follow_up && !this.user_roles.is_employee && !this.user_roles.is_president && !this.user_roles.is_dept_head) {
			this.current_tab = 'follow_up_leaves';
		} else if (this.user_roles.is_president && !this.user_roles.is_employee) {
			this.current_tab = 'president_leaves';
		} else if (this.user_roles.is_dept_head && !this.user_roles.is_employee) {
			this.current_tab = 'department_leaves';
		}

		this.make_ui();
		this.load_data();
	}

	make_ui() {
		this.wrapper.empty().append(`
			<div class="leave-management-page">
				<div class="lm-header">
					<h1>إدارة الإجازات <span class="lm-icon">🌴</span></h1>
					<button class="lm-new-btn" id="btn-new-leave">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
						تقديم إجازة جديدة
					</button>
					${this.user_roles.is_employee ? `
					<button class="lm-filter-clear" style="border-color: #2563eb; color: #2563eb;" id="btn-show-balances">
						رصيد إجازاتي
					</button>
					` : ''}
				</div>
				
				<div class="lm-tabs">
					${this.user_roles.is_employee ? `<button class="lm-tab ${this.current_tab === 'my_leaves' ? 'active' : ''}" data-tab="my_leaves">إجازاتي</button>` : ''}
					${this.user_roles.is_dept_head || this.user_roles.is_admin ? `<button class="lm-tab ${this.current_tab === 'department_leaves' ? 'active' : ''}" data-tab="department_leaves">إجازات القسم</button>` : ''}
					${this.user_roles.is_president || this.user_roles.is_admin ? `<button class="lm-tab ${this.current_tab === 'president_leaves' ? 'active' : ''}" data-tab="president_leaves">موافقات رئيس الجامعة</button>` : ''}
					${this.user_roles.is_follow_up || this.user_roles.is_admin ? `<button class="lm-tab ${this.current_tab === 'follow_up_leaves' ? 'active' : ''}" data-tab="follow_up_leaves">متابعة الإجازات</button>` : ''}
				</div>

				<div class="lm-filters">
					<div class="lm-filter-group">
						<label>من تاريخ</label>
						<input type="date" id="filter-from-date">
					</div>
					<div class="lm-filter-group">
						<label>إلى تاريخ</label>
						<input type="date" id="filter-to-date">
					</div>
					<div class="lm-filter-group">
						<label>القسم</label>
						<select id="filter-dep" style="max-width: 160px; text-overflow: ellipsis;">
							<option value="">الكل</option>
							${this.departments.map(d => `<option value="${d.name}">${d.department_name || d.name}</option>`).join('')}
						</select>
					</div>
					<div class="lm-filter-group" id="emp-filter-wrapper">
						<label>الموظف</label>
						<input type="text" id="filter-employee" placeholder="اختر الموظف..." autocomplete="off">
					</div>
					<div class="lm-filter-group">
						<label>نوع الإجازة</label>
						<select id="filter-leave-type">
							<option value="">الكل</option>
							${this.leave_types.map(t => `<option value="${t.name}">${t.leave_type}</option>`).join('')}
						</select>
					</div>
					<div class="lm-filter-group">
						<label>الحالة</label>
						<select id="filter-status">
							<option value="">الكل</option>
							<option value="Pending">قيد الإنتظار</option>
							<option value="Applied">مقدمة للرئيس المباشر</option>
							<option value="Approved By Department">موافق عليها من القسم</option>
							<option value="Approved">مقبولة</option>
							<option value="Rejected">مرفوضة</option>
						</select>
					</div>
					<button class="lm-filter-btn" id="btn-filter">تحديث</button>
					<button class="lm-filter-clear" id="btn-clear-filter">مسح</button>
				</div>

				<div class="lm-stats" id="lm-stats-container">
					<!-- Stats loaded here -->
				</div>

				<div class="lm-table-wrap">
					<table class="lm-table">
						<thead>
							<tr>
								<th>الموظف</th>
								<th>نوع الإجازة</th>
								<th>من تاريخ</th>
								<th>الأيام</th>
								<th>السبب</th>
								<th>المرفقات</th>
								<th>الحالة</th>
								<th>القسم</th>
								<th>الإجراءات</th>
							</tr>
						</thead>
						<tbody id="lm-table-body">
							<!-- Data rows -->
						</tbody>
					</table>
				</div>
			</div>
		`);

		let emp_input = this.wrapper.find('#filter-employee');
		if (this.leave_employees && this.leave_employees.length > 0) {
			let list = this.leave_employees.map(d => d.full_name || d.name);
			new Awesomplete(emp_input[0], {
				list: list,
				minChars: 0,
				maxItems: 15
			});
			emp_input[0].addEventListener("awesomplete-selectcomplete", () => {
				this.load_data();
			});
		}

		this.bind_events();
		
		// Trigger initial tab view logic for filters
		this.update_tab_ui();
	}

	update_tab_ui() {
		let status_val = "";
		
		if (this.current_tab === 'follow_up_leaves') {
			this.wrapper.find('#filter-status').html(`
				<option value="Approved">مقبولة</option>
				<option value="Submitted">مقدمة</option>
				<option value="">الكل (مقبولة ومقدمة)</option>
			`);
			status_val = "Approved";
		} else {
			this.wrapper.find('#filter-status').html(`
				<option value="">الكل</option>
				<option value="Pending">قيد الإنتظار</option>
				<option value="Applied">مقدمة للرئيس المباشر</option>
				<option value="Approved By Department">موافق عليها من القسم</option>
				<option value="Approved">مقبولة</option>
				<option value="Rejected">مرفوضة</option>
			`);
			if (this.current_tab === 'department_leaves') status_val = "Applied";
			else if (this.current_tab === 'president_leaves') status_val = "Approved By Department";
		}

		this.wrapper.find('#filter-status').val(status_val);

		if (this.current_tab === 'my_leaves') {
			this.wrapper.find('#filter-dep').parent().hide();
			this.wrapper.find('#emp-filter-wrapper').hide();
		} else {
			this.wrapper.find('#filter-dep').parent().show();
			this.wrapper.find('#emp-filter-wrapper').show();
		}
	}

	bind_events() {
		this.wrapper.find('.lm-tab').on('click', (e) => {
			this.wrapper.find('.lm-tab').removeClass('active');
			$(e.currentTarget).addClass('active');
			this.current_tab = $(e.currentTarget).data('tab');
			
			this.update_tab_ui();
			this.load_data();
		});

		this.wrapper.find('#btn-new-leave').on('click', () => {
			this.show_new_leave_dialog();
		});

		this.wrapper.find('#btn-show-balances').on('click', () => {
			this.show_balances_dialog();
		});

		this.wrapper.find('#btn-filter').on('click', () => {
			this.load_data();
		});

		this.wrapper.find('#btn-clear-filter').on('click', () => {
			this.wrapper.find('#filter-from-date').val('');
			this.wrapper.find('#filter-to-date').val('');
			this.wrapper.find('#filter-leave-type').val('');
			this.wrapper.find('#filter-dep').val('');
			this.wrapper.find('#filter-employee').val('');

			this.update_tab_ui();
			this.load_data();
		});
	}

	get_filters() {
		let emp_val = this.wrapper.find('#filter-employee').val();
		let emp_name = '';
		if (emp_val) {
			let matched = this.leave_employees ? this.leave_employees.find(d => (d.full_name || d.name) === emp_val) : null;
			emp_name = matched ? matched.name : emp_val;
		}

		return {
			from_date: this.wrapper.find('#filter-from-date').val(),
			to_date: this.wrapper.find('#filter-to-date').val(),
			leave_type: this.wrapper.find('#filter-leave-type').val(),
			status: this.wrapper.find('#filter-status').val(),
			dep: this.wrapper.find('#filter-dep').val(),
			employee_name: emp_name
		};
	}

	render_skeleton() {
		let html = '';
		for (let i = 0; i < 5; i++) {
			html += `
				<tr class="lm-skeleton-row">
					<td colspan="9">
						<div style="display:flex; gap:16px;">
							<div class="lm-skeleton" style="flex:2"></div>
							<div class="lm-skeleton" style="flex:1"></div>
							<div class="lm-skeleton" style="flex:1"></div>
							<div class="lm-skeleton" style="flex:0.5"></div>
							<div class="lm-skeleton" style="flex:2"></div>
							<div class="lm-skeleton" style="flex:1"></div>
							<div class="lm-skeleton" style="flex:1.5"></div>
							<div class="lm-skeleton" style="flex:1.5"></div>
							<div class="lm-skeleton" style="flex:1"></div>
						</div>
					</td>
				</tr>
			`;
		}
		this.wrapper.find('#lm-table-body').html(html);
	}

	async load_data() {
		this.render_skeleton();

		let method = '';
		if (this.current_tab === 'my_leaves') {
			method = 'uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_employee_leaves';
		} else if (this.current_tab === 'department_leaves') {
			method = 'uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_department_leaves';
		} else if (this.current_tab === 'president_leaves') {
			method = 'uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_president_leaves';
		} else if (this.current_tab === 'follow_up_leaves') {
			method = 'uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_all_leaves';
		}

		let r = await frappe.call({
			method: method,
			args: this.get_filters()
		});

		let data = r.message || [];
		this.render_table(data);
		this.render_stats(data);
	}

	render_stats(data) {
		let total = data.length;
		let pending = data.filter(d => d.workflow_state === 'Pending' || d.workflow_state === 'Applied' || d.workflow_state === 'Approved By Department').length;
		let approved = data.filter(d => d.workflow_state === 'Approved').length;
		let rejected = data.filter(d => d.workflow_state === 'Rejected').length;

		this.wrapper.find('#lm-stats-container').html(`
			<div class="lm-stat-card total">
				<div class="stat-number">${total}</div>
				<div class="stat-label">الإجمالي</div>
			</div>
			<div class="lm-stat-card pending">
				<div class="stat-number">${pending}</div>
				<div class="stat-label">قيد الإنتظار</div>
			</div>
			<div class="lm-stat-card approved">
				<div class="stat-number">${approved}</div>
				<div class="stat-label">مقبولة</div>
			</div>
			<div class="lm-stat-card rejected">
				<div class="stat-number">${rejected}</div>
				<div class="stat-label">مرفوضة</div>
			</div>
		`);
	}

	get_status_html(state) {
		let cls = '';
		let label = state;
		if (state === 'Pending') { cls = 'pending'; label = 'قيد الإنتظار'; }
		else if (state === 'Applied') { cls = 'applied'; label = 'مقدمة للرئيس المباشر'; }
		else if (state === 'Approved By Department') { cls = 'approved-dept'; label = 'موافق عليها من القسم'; }
		else if (state === 'Approved') { cls = 'approved'; label = 'مقبولة'; }
		else if (state === 'Rejected') { cls = 'rejected'; label = 'مرفوضة'; }

		return `<span class="lm-status ${cls}"><span class="status-dot"></span>${label}</span>`;
	}

	render_table(data) {
		let tbody = this.wrapper.find('#lm-table-body');
		tbody.empty();

		if (data.length === 0) {
			tbody.html(`
				<tr>
					<td colspan="9">
						<div class="lm-empty">
							<div class="empty-icon">📁</div>
							<p>لا توجد بيانات لعرضها</p>
						</div>
					</td>
				</tr>
			`);
			return;
		}

		data.forEach(row => {
			let reason_text = row.reason ? (row.reason.length > 30 ? row.reason.substring(0, 30) + '...' : row.reason) : '-';

			let can_approve_dept = this.current_tab === 'department_leaves' && row.workflow_state === 'Applied';
			let can_approve_pres = this.current_tab === 'president_leaves' && row.workflow_state === 'Approved By Department';
			let needs_action = can_approve_dept || can_approve_pres;

			let attachment_btn = row.attachment ? `<button class="lm-action-btn detail" onclick="window.open('${row.attachment}', 'Attachment', 'width=800,height=800'); return false;">عرض</button>` : '-';

			let tr = $(`
				<tr>
					<td><b>${row.employee_fullname || row.employee}</b></td>
					<td>${row.leave_type}</td>
					<td>${row.from_date}</td>
					<td><b>${row.days}</b></td>
					<td style="max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${row.reason || ''}">${reason_text}</td>
					<td>${attachment_btn}</td>
					<td>${this.get_status_html(row.workflow_state)}</td>
					<td>${row.dep || '-'}</td>
					<td>
						<div class="lm-actions">
							<button class="lm-action-btn detail" data-name="${row.name}">إجراء</button>
						</div>
					</td>
				</tr>
			`);

			tr.find('.detail').on('click', () => {
				this.show_details_dialog(row);
			});

			tbody.append(tr);
		});
	}

	show_balances_dialog() {
		let dialog = new frappe.ui.Dialog({
			title: 'رصيد إجازاتي',
			fields: [{ fieldtype: 'HTML', fieldname: 'balances_html' }]
		});

		dialog.show();
		dialog.get_field('balances_html').$wrapper.html('<div style="text-align:center; padding: 20px;">جاري التحميل...</div>');

		frappe.call({
			method: "uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave.get_all_leave_balances",
			args: { employee: frappe.session.user },
			callback: (r) => {
				if (r.message) {
					const balances = r.message;
					let html = '<table class="table table-striped"><thead><tr><th>نوع الإجازة</th><th>الرصيد المتبقي</th></tr></thead><tbody>';
					for (const [leave_type, balance] of Object.entries(balances)) {
						const color = balance >= 0 ? '#28a745' : '#dc3545';
						html += `<tr><td>${leave_type}</td><td><span style="color: ${color}; font-weight: bold;">${balance.toFixed(2)}</span></td></tr>`;
					}
					html += '</tbody></table>';
					dialog.get_field('balances_html').$wrapper.html(html);
				}
			}
		});
	}

	show_new_leave_dialog() {
		let dialog;
		let update_days = () => {
			if (!dialog) return;
			let from_date = dialog.get_value('from_date');
			let to_date = dialog.get_value('to_date');
			if (from_date && to_date) {
				dialog.get_field('days_display').$wrapper.find('#lm-days-number').text('جاري الحساب...');
				frappe.call({
					method: "uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave.calculate_leave_days",
					args: { from_date: from_date, to_date: to_date },
					callback: (r) => {
						if (r.message !== undefined) {
							dialog.get_field('days_display').$wrapper.find('#lm-days-number').text(r.message);
						}
					}
				});
			}
		};

		dialog = new frappe.ui.Dialog({
			title: 'تقديم إجازة جديدة',
			fields: [
				{ fieldtype: 'Data', fieldname: 'employee_fullname', label: 'الاسم الكامل', reqd: 1, default: this.user_fullname },
				{ fieldtype: 'Link', fieldname: 'leave_type', label: 'نوع الإجازة', options: 'Leave Type', reqd: 1, default: 'اجازة اعتيادية' },
				{ fieldtype: 'Link', fieldname: 'dep', label: 'القسم', options: 'Leave Department', reqd: 1 },
				{ fieldtype: 'Column Break' },
				{ fieldtype: 'Date', fieldname: 'from_date', label: 'من تاريخ', reqd: 1, default: frappe.datetime.add_days(frappe.datetime.nowdate(), 1), onchange: () => update_days() },
				{ fieldtype: 'Date', fieldname: 'to_date', label: 'إلى تاريخ', reqd: 1, default: frappe.datetime.add_days(frappe.datetime.nowdate(), 1), onchange: () => update_days() },
				{ fieldtype: 'Section Break' },
				{ fieldtype: 'HTML', fieldname: 'days_display', options: '<div style="padding: 15px; background: #dbeafe; color: #1e40af; border-radius: 12px; text-align: center; font-size: 18px; font-weight: 800; margin: 10px 0; border: 2px dashed #93c5fd;">عدد أيام الاجازة: <span id="lm-days-number">0</span></div>' },
				{ fieldtype: 'Section Break' },
				{ fieldtype: 'Data', fieldname: 'alternative_employee', label: 'الموظف البديل' },
				{ fieldtype: 'Attach', fieldname: 'attachment', label: 'المرفقات' },
				{ fieldtype: 'Small Text', fieldname: 'reason', label: 'السبب', reqd: 1 }
			],
			primary_action_label: 'إرسال الطلب',
			primary_action: (values) => {
				frappe.call({
					method: 'uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.create_leave',
					args: {
						employee_fullname: values.employee_fullname,
						leave_type: values.leave_type,
						from_date: values.from_date,
						to_date: values.to_date,
						reason: values.reason,
						dep: values.dep,
						alternative_employee: values.alternative_employee,
						attachment: values.attachment
					},
					freeze: true,
					callback: (r) => {
						if (!r.exc) {
							frappe.show_alert({ message: 'تم تقديم الإجازة بنجاح', indicator: 'green' });
							dialog.hide();
							this.load_data();
						}
					}
				});
			}
		});

		dialog.show();
	}

	async show_details_dialog(row) {
		let can_approve_dept = this.current_tab === 'department_leaves' && row.workflow_state === 'Applied';
		let can_approve_pres = this.current_tab === 'president_leaves' && row.workflow_state === 'Approved By Department';
		let needs_action = can_approve_dept || can_approve_pres;

		let r = await frappe.call({
			method: 'uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.get_leave_comments',
			args: { leave_name: row.name }
		});
		let comments = r.message || [];

		let dialog_html = `
			<div class="lm-detail-grid">
				<div class="lm-detail-item">
					<div class="detail-label">الموظف</div>
					<div class="detail-value">${row.employee_fullname || row.employee}</div>
				</div>
				<div class="lm-detail-item">
					<div class="detail-label">القسم</div>
					<div class="detail-value">${row.dep || '-'}</div>
				</div>
				<div class="lm-detail-item">
					<div class="detail-label">نوع الإجازة</div>
					<div class="detail-value">${row.leave_type}</div>
				</div>
				<div class="lm-detail-item">
					<div class="detail-label">عدد الأيام</div>
					<div class="detail-value" style="color: #2563eb;">${row.days} أيام</div>
				</div>
				<div class="lm-detail-item">
					<div class="detail-label">من تاريخ</div>
					<div class="detail-value">${row.from_date}</div>
				</div>
				<div class="lm-detail-item">
					<div class="detail-label">إلى تاريخ</div>
					<div class="detail-value">${row.to_date}</div>
				</div>
				<div class="lm-detail-item full-width">
					<div class="detail-label">الحالة الحالية</div>
					<div class="detail-value" style="margin-top:5px;">${this.get_status_html(row.workflow_state)}</div>
				</div>
				<div class="lm-detail-item full-width">
					<div class="detail-label">السبب</div>
					<div class="detail-value" style="font-weight: 400;">${row.reason || '-'}</div>
				</div>
				${row.alternative_employee ? `
				<div class="lm-detail-item full-width">
					<div class="detail-label">الموظف البديل</div>
					<div class="detail-value">${row.alternative_employee}</div>
				</div>` : ''}
			</div>

			<div class="lm-comment-section">
				<h4>التعليقات والملاحظات</h4>
				<div class="lm-comments-list">
					${comments.length > 0 ? comments.map(c => `
						<div class="lm-comment-item">
							<div style="display:flex; justify-content:space-between; align-items:center;">
								<span class="comment-author">${c.comment_by}</span>
								<span class="comment-date">${frappe.datetime.global_date_format(c.creation)}</span>
							</div>
							<div class="comment-text">${c.content}</div>
						</div>
					`).join('') : '<div style="color:var(--text-muted); font-size:13px;">لا توجد تعليقات</div>'}
				</div>
				
				${needs_action ? `
					<div class="lm-field">
						<label>إضافة ملاحظة (اختياري)</label>
						<textarea id="action-comment" placeholder="اكتب ملاحظاتك هنا..."></textarea>
					</div>
				` : ''}
			</div>
		`;

		let fields = [
			{ fieldtype: 'HTML', fieldname: 'html_content', options: dialog_html }
		];

		let dialog_options = {
			title: `تفاصيل الإجازة: ${row.name}`,
			fields: fields,
		};

		if (needs_action) {
			dialog_options.primary_action_label = 'موافقة';
			dialog_options.primary_action = () => {
				let comment = dialog.get_field('html_content').$wrapper.find('#action-comment').val();
				this.apply_action(row.name, 'Approve', comment, dialog);
			};

			dialog_options.secondary_action_label = 'رفض';
			dialog_options.secondary_action = () => {
				let comment = dialog.get_field('html_content').$wrapper.find('#action-comment').val();
				this.apply_action(row.name, 'Reject', comment, dialog);
			};
		}

		let dialog = new frappe.ui.Dialog(dialog_options);

		if (needs_action) {
			dialog.get_primary_btn().removeClass('btn-primary').addClass('btn-success');
			dialog.get_secondary_btn().removeClass('btn-default').addClass('btn-danger');
		}

		dialog.show();
	}

	apply_action(leave_name, action, comment, dialog) {
		frappe.call({
			method: 'uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment.apply_workflow_action',
			args: {
				leave_name: leave_name,
				action: action,
				comment: comment
			},
			freeze: true,
			callback: (r) => {
				if (!r.exc) {
					frappe.show_alert({ message: `تم ${action === 'Approve' ? 'الموافقة على' : 'رفض'} الإجازة بنجاح`, indicator: 'green' });
					if (dialog) dialog.hide();
					this.load_data();
				}
			}
		});
	}

	quick_action(leave_name, action) {
		frappe.confirm(
			`هل أنت متأكد من ${action === 'Approve' ? 'الموافقة على' : 'رفض'} هذا الطلب؟`,
			() => {
				this.apply_action(leave_name, action, null, null);
			}
		);
	}
}