frappe.pages['citizens-affairs-mgm'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true
	});

	wrapper.ca_page = new CitizenAffairsMgmPage(wrapper);
}

class CitizenAffairsMgmPage {
	constructor(wrapper) {
		this.page = wrapper.page;
		this.wrapper = $(wrapper).find('.layout-main-section');
		$(wrapper).find('.page-head').hide();
		this.current_tab = 'department_requests';
		this.departments = [];

		frappe.require('citizens_affairs_mgm.css', () => {
			this.init();
		});
	}

	async init() {
		// Get user role info
		let r = await frappe.call({
			method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_user_citizen_role"
		});
		this.role_info = r.message || {};

		// Get departments
		let d = await frappe.call({
			method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_departments_list"
		});
		this.departments = d.message || [];

		// Determine default tab
		if (this.role_info.is_dept_head) {
			this.current_tab = 'department_requests';
		} else if (this.role_info.is_admin) {
			this.current_tab = 'all_requests';
		}

		this.make_ui();
		this.load_data();
	}

	make_ui() {
		this.wrapper.empty().append(`
			<div class="ca-mgm-page">
				<div class="ca-mgm-header">
					<h1>إدارة شؤون المواطنين <span class="ca-icon">🏛️</span></h1>
					<div style="display: flex; gap: 8px; align-items: center;">
						<button class="ca-mgm-copy-link-btn" id="btn-copy-form-link">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
								<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
							</svg>
							نسخ رابط النموذج
						</button>
					</div>
				</div>

				<div class="ca-mgm-tabs">
					${this.role_info.is_dept_head ? `<button class="ca-mgm-tab ${this.current_tab === 'department_requests' ? 'active' : ''}" data-tab="department_requests">طلبات قسمي</button>` : ''}
					${this.role_info.is_admin ? `<button class="ca-mgm-tab ${this.current_tab === 'all_requests' ? 'active' : ''}" data-tab="all_requests">جميع الطلبات</button>` : ''}
				</div>

				<div class="ca-mgm-filters-wrapper">
					<div class="ca-mgm-filters-header-mobile">
						<button class="ca-mgm-filter-toggle" id="btn-toggle-ca-filters">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
							الفلاتر
						</button>
					</div>
					<div class="ca-mgm-filters" id="ca-filters-content">
						<div class="ca-mgm-filter-group">
							<label>من تاريخ</label>
							<input type="date" id="ca-filter-from-date">
						</div>
						<div class="ca-mgm-filter-group">
							<label>إلى تاريخ</label>
							<input type="date" id="ca-filter-to-date">
						</div>
						${this.current_tab === 'all_requests' || this.role_info.is_admin ? `
						<div class="ca-mgm-filter-group" id="ca-dept-filter-wrapper">
							<label>الجهة</label>
							<select id="ca-filter-department" style="max-width: 180px; text-overflow: ellipsis;">
								<option value="">الكل</option>
								${this.departments.map(d => `<option value="${d.name}">${d.department_name || d.name}</option>`).join('')}
							</select>
						</div>
						` : ''}
						<div class="ca-mgm-filter-group">
							<label>الحالة</label>
							<select id="ca-filter-status">
								<option value="All">الكل</option>
								<option value="Open">مفتوح</option>
								<option value="Replied">تم الرد</option>
								<option value="Closed">مغلق</option>
							</select>
						</div>
						<button class="ca-mgm-filter-clear" id="btn-ca-clear-filter">مسح</button>
					</div>
				</div>

				<div class="ca-mgm-stats" id="ca-stats-container"></div>

				<div class="ca-mgm-table-wrap">
					<table class="ca-mgm-table">
						<thead>
							<tr>
								<th>#</th>
								<th>الاسم</th>
								<th>الهاتف</th>
								<th>البريد</th>
								<th>الجهة المعنية</th>
								<th>الحالة</th>
								<th>التاريخ</th>
								<th>الإجراءات</th>
							</tr>
						</thead>
						<tbody id="ca-table-body"></tbody>
					</table>
				</div>
			</div>
		`);

		this.bind_events();
	}

	bind_events() {
		this.wrapper.find('.ca-mgm-tab').on('click', (e) => {
			this.wrapper.find('.ca-mgm-tab').removeClass('active');
			$(e.currentTarget).addClass('active');
			this.current_tab = $(e.currentTarget).data('tab');

			// Toggle department filter visibility
			let dept_wrapper = this.wrapper.find('#ca-dept-filter-wrapper');
			if (this.current_tab === 'all_requests') {
				dept_wrapper.show();
			} else {
				dept_wrapper.hide();
			}

			this.load_data();
		});

		this.wrapper.find('#btn-copy-form-link').on('click', () => {
			let url = window.location.origin + '/citizen-affairs-request';
			navigator.clipboard.writeText(url).then(() => {
				frappe.show_alert({ message: 'تم نسخ الرابط بنجاح!', indicator: 'green' });
			}).catch(() => {
				// Fallback
				let tmp = document.createElement('textarea');
				tmp.value = url;
				document.body.appendChild(tmp);
				tmp.select();
				document.execCommand('copy');
				document.body.removeChild(tmp);
				frappe.show_alert({ message: 'تم نسخ الرابط بنجاح!', indicator: 'green' });
			});
		});

		this.wrapper.find('#ca-filter-from-date, #ca-filter-to-date, #ca-filter-status, #ca-filter-department').on('change', () => {
			this.load_data();
		});

		this.wrapper.find('#btn-toggle-ca-filters').on('click', () => {
			this.wrapper.find('#ca-filters-content').slideToggle('fast');
		});

		this.wrapper.find('#btn-ca-clear-filter').on('click', () => {
			this.wrapper.find('#ca-filter-from-date').val('');
			this.wrapper.find('#ca-filter-to-date').val('');
			this.wrapper.find('#ca-filter-status').val('All');
			this.wrapper.find('#ca-filter-department').val('');
			this.load_data();
		});
	}

	get_filters() {
		return {
			from_date: this.wrapper.find('#ca-filter-from-date').val(),
			to_date: this.wrapper.find('#ca-filter-to-date').val(),
			status: this.wrapper.find('#ca-filter-status').val(),
			department: this.wrapper.find('#ca-filter-department').val() || ''
		};
	}

	render_skeleton() {
		let html = '';
		for (let i = 0; i < 5; i++) {
			html += `
				<tr>
					<td colspan="8">
						<div style="display:flex; gap:16px;">
							<div class="ca-mgm-skeleton" style="flex:0.3"></div>
							<div class="ca-mgm-skeleton" style="flex:2"></div>
							<div class="ca-mgm-skeleton" style="flex:1"></div>
							<div class="ca-mgm-skeleton" style="flex:1.5"></div>
							<div class="ca-mgm-skeleton" style="flex:1.5"></div>
							<div class="ca-mgm-skeleton" style="flex:1"></div>
							<div class="ca-mgm-skeleton" style="flex:1"></div>
							<div class="ca-mgm-skeleton" style="flex:1"></div>
						</div>
					</td>
				</tr>
			`;
		}
		this.wrapper.find('#ca-table-body').html(html);
	}

	async load_data() {
		this.render_skeleton();

		let method = '';
		if (this.current_tab === 'department_requests') {
			method = 'uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_department_requests';
		} else {
			method = 'uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_all_requests';
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
		let open = data.filter(d => d.status === 'Open').length;
		let replied = data.filter(d => d.status === 'Replied').length;
		let closed = data.filter(d => d.status === 'Closed').length;

		this.wrapper.find('#ca-stats-container').html(`
			<div class="ca-mgm-stat-card total">
				<div class="stat-number">${total}</div>
				<div class="stat-label">الإجمالي</div>
			</div>
			<div class="ca-mgm-stat-card open">
				<div class="stat-number">${open}</div>
				<div class="stat-label">مفتوح</div>
			</div>
			<div class="ca-mgm-stat-card replied">
				<div class="stat-number">${replied}</div>
				<div class="stat-label">تم الرد</div>
			</div>
			<div class="ca-mgm-stat-card closed">
				<div class="stat-number">${closed}</div>
				<div class="stat-label">مغلق</div>
			</div>
		`);
	}

	get_status_html(status) {
		let cls = '', label = status;
		if (status === 'Open') { cls = 'open'; label = 'مفتوح'; }
		else if (status === 'Replied') { cls = 'replied'; label = 'تم الرد'; }
		else if (status === 'Closed') { cls = 'closed'; label = 'مغلق'; }
		return `<span class="ca-status ${cls}"><span class="status-dot"></span>${label}</span>`;
	}

	render_table(data) {
		let tbody = this.wrapper.find('#ca-table-body');
		tbody.empty();

		if (data.length === 0) {
			tbody.html(`
				<tr>
					<td colspan="8">
						<div class="ca-mgm-empty">
							<div class="empty-icon">📭</div>
							<p>لا توجد طلبات لعرضها</p>
						</div>
					</td>
				</tr>
			`);
			return;
		}

		data.forEach((row, idx) => {
			let details_text = row.request_details ? (row.request_details.length > 30 ? row.request_details.substring(0, 30) + '...' : row.request_details) : '-';
			let creation_date = row.creation ? frappe.datetime.str_to_user(row.creation.split(' ')[0]) : '-';

			let tr = $(`
				<tr>
					<td><b>${idx + 1}</b></td>
					<td><b>${row.full_name}</b></td>
					<td>${row.phone_number || '-'}</td>
					<td style="direction: ltr; text-align: right;">${row.email || '-'}</td>
					<td>${row.target_department || '-'}</td>
					<td>${this.get_status_html(row.status)}</td>
					<td>${creation_date}</td>
					<td>
						<div style="display: flex; gap: 6px; flex-wrap: nowrap;">
							<button class="ca-mgm-action-btn detail" data-name="${row.name}">تفاصيل</button>
							${row.status === 'Open' ? `<button class="ca-mgm-action-btn reply" data-name="${row.name}">رد</button>` : ''}
							${row.status === 'Replied' ? `<button class="ca-mgm-action-btn close-req" data-name="${row.name}">إغلاق</button>` : ''}
						</div>
					</td>
				</tr>
			`);

			tr.find('.detail').on('click', () => this.show_detail_dialog(row));
			tr.find('.reply').on('click', () => this.show_reply_dialog(row));
			tr.find('.close-req').on('click', () => this.close_request(row));

			tbody.append(tr);
		});
	}

	show_detail_dialog(row) {
		let reply_html = '';
		if (row.reply_text) {
			let replied_by_name = row.replied_by || '-';
			let replied_on = row.replied_on ? frappe.datetime.str_to_user(row.replied_on) : '-';
			reply_html = `
				<div class="ca-mgm-reply-box">
					<div class="reply-label">الرد</div>
					<div class="reply-text">${row.reply_text}</div>
					<div class="reply-meta">بواسطة: ${replied_by_name} — ${replied_on}</div>
				</div>
			`;
		}

		let creation_date = row.creation ? frappe.datetime.str_to_user(row.creation.split(' ')[0]) : '-';

		let dialog = new frappe.ui.Dialog({
			title: `تفاصيل الطلب - ${row.full_name}`,
			size: 'large',
			fields: [
				{
					fieldtype: 'HTML',
					fieldname: 'detail_html',
					options: `
						<div dir="rtl" style="font-family: 'Cairo', sans-serif;">
							<div class="ca-mgm-detail-grid">
								<div class="ca-mgm-detail-item">
									<div class="detail-label">الاسم الكامل</div>
									<div class="detail-value">${row.full_name}</div>
								</div>
								<div class="ca-mgm-detail-item">
									<div class="detail-label">رقم الهاتف</div>
									<div class="detail-value">${row.phone_number || '-'}</div>
								</div>
								<div class="ca-mgm-detail-item">
									<div class="detail-label">البريد الإلكتروني</div>
									<div class="detail-value" style="direction: ltr; text-align: right;">${row.email || '-'}</div>
								</div>
								<div class="ca-mgm-detail-item">
									<div class="detail-label">الجهة المعنية</div>
									<div class="detail-value">${row.target_department || '-'}</div>
								</div>
								<div class="ca-mgm-detail-item">
									<div class="detail-label">الحالة</div>
									<div class="detail-value">${this.get_status_html(row.status)}</div>
								</div>
								<div class="ca-mgm-detail-item">
									<div class="detail-label">التاريخ</div>
									<div class="detail-value">${creation_date}</div>
								</div>
								<div class="ca-mgm-detail-item full-width">
									<div class="detail-label">تفاصيل الطلب</div>
									<div class="detail-value" style="line-height: 1.8; font-weight: 500;">${row.request_details || '-'}</div>
								</div>
							</div>
							${reply_html}
						</div>
					`
				}
			]
		});

		if (row.status === 'Open') {
			dialog.set_primary_action('الرد على الطلب', () => {
				dialog.hide();
				this.show_reply_dialog(row);
			});
		}

		dialog.show();
		dialog.$wrapper.find('.modal-dialog').css('max-width', '700px');
	}

	show_reply_dialog(row) {
		let dialog = new frappe.ui.Dialog({
			title: `الرد على طلب - ${row.full_name}`,
			fields: [
				{
					fieldtype: 'HTML',
					fieldname: 'request_summary',
					options: `
						<div dir="rtl" style="background: var(--bg-light-gray, #f1f5f9); padding: 14px; border-radius: 10px; margin-bottom: 16px; font-family: 'Cairo', sans-serif;">
							<div style="font-size: 13px; color: var(--text-muted); font-weight: 700; margin-bottom: 6px;">ملخص الطلب:</div>
							<div style="font-size: 15px; color: var(--text-color); line-height: 1.7;">${row.request_details || '-'}</div>
							<div style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">
								<b>${row.full_name}</b> — ${row.target_department} — ${row.email}
							</div>
						</div>
					`
				},
				{
					fieldtype: 'Text',
					fieldname: 'reply_text',
					label: 'نص الرد',
					reqd: 1,
					description: 'سيتم إرسال هذا الرد عبر البريد الإلكتروني إلى المواطن'
				}
			],
			primary_action_label: 'إرسال الرد',
			primary_action: (values) => {
				frappe.call({
					method: 'uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.reply_to_request',
					args: {
						request_name: row.name,
						reply_text: values.reply_text
					},
					freeze: true,
					freeze_message: 'جاري إرسال الرد...',
					callback: (r) => {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: 'تم إرسال الرد بنجاح وإخطار المواطن عبر البريد الإلكتروني', indicator: 'green' });
							dialog.hide();
							this.load_data();
						}
					}
				});
			}
		});
		dialog.show();
		dialog.$wrapper.find('.modal-dialog').css('max-width', '600px');
	}

	close_request(row) {
		frappe.confirm('هل أنت متأكد من إغلاق هذا الطلب؟', () => {
			frappe.call({
				method: 'frappe.client.set_value',
				args: {
					doctype: 'Citizens Affairs Request',
					name: row.name,
					fieldname: 'status',
					value: 'Closed'
				},
				callback: (r) => {
					if (!r.exc) {
						frappe.show_alert({ message: 'تم إغلاق الطلب بنجاح', indicator: 'green' });
						this.load_data();
					}
				}
			});
		});
	}
}