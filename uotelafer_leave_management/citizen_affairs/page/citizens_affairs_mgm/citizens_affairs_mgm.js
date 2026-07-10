// Copyright (c) 2026, Computer Center of UoT and contributors
// For license information, please see license.txt

frappe.pages["citizens-affairs-mgm"].on_page_load = function (wrapper) {
	new CitizensAffairsManagement(wrapper);
};

class CitizensAffairsManagement {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.wrapper.addClass("ca-mgm-page rtl").attr("dir", "rtl");
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("إدارة شؤون المواطنين"),
			single_column: true
		});

		if (this.page && this.page.wrapper) {
			this.page.wrapper.attr("dir", "rtl").addClass("ca-mgm-page");
			this.page.wrapper.find(".page-head").attr("dir", "rtl").css({
				direction: "rtl",
				"text-align": "right"
			});
		}
		if (this.page && this.page.main) {
			this.page.main.attr("dir", "rtl").addClass("ca-mgm-page");
		}

		this.user_role_info = null;
		this.current_tab = "my_department"; // 'my_department' | 'all_requests'
		this.filters = {
			department: "",
			status: "All",
			from_date: "",
			to_date: ""
		};

		this.init();
	}

	async init() {
		await this.check_permissions();
		if (!this.user_role_info) return;

		this.make_ui();
		this.load_data();
	}

	async check_permissions() {
		try {
			const res = await frappe.call({
				method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_user_citizen_role"
			});
			this.user_role_info = res.message;

			if (!this.user_role_info.is_dept_head && !this.user_role_info.is_admin) {
				this.page.main.html(`
					<div class="ca-mgm-empty" dir="rtl">
						<div class="empty-icon">🔒</div>
						<h3>غير مصرح لك بالوصول</h3>
						<p>هذه الصفحة مخصصة لمدراء الكليات والأقسام ومسؤولي شعبة شؤون المواطنين فقط.</p>
					</div>
				`);
				return;
			}

			// If user is admin/CA manager but not a specific dept head, default to all requests
			if (this.user_role_info.is_admin && !this.user_role_info.is_dept_head) {
				this.current_tab = "all_requests";
			}
		} catch (e) {
			console.error(e);
		}
	}

	make_ui() {
		this.page.main.html(`
			<div class="ca-mgm-container" dir="rtl">
				<!-- Tabs (Only for Admins/CA Managers) -->
				${
					this.user_role_info.is_admin
						? `
					<div class="ca-mgm-tabs">
						${
							this.user_role_info.is_dept_head
								? `<button class="ca-mgm-tab ${this.current_tab === 'my_department' ? 'active' : ''}" data-tab="my_department">
									📋 طلبات قسمي
								</button>`
								: ""
						}
						<button class="ca-mgm-tab ${this.current_tab === 'all_requests' ? 'active' : ''}" data-tab="all_requests">
							🌐 جميع طلبات الكليات والأقسام
						</button>
					</div>
				`
						: ""
				}

				<!-- Statistics Cards -->
				<div class="ca-mgm-stats" id="ca-stats-container">
					<div class="ca-mgm-stat-card total">
						<div class="stat-number" id="stat-total">0</div>
						<div class="stat-label">إجمالي الطلبات</div>
					</div>
					<div class="ca-mgm-stat-card open">
						<div class="stat-number" id="stat-open">0</div>
						<div class="stat-label">قيد الانتظار</div>
					</div>
					<div class="ca-mgm-stat-card accepted">
						<div class="stat-number" id="stat-accepted">0</div>
						<div class="stat-label">تم القبول</div>
					</div>
					<div class="ca-mgm-stat-card rejected">
						<div class="stat-number" id="stat-rejected">0</div>
						<div class="stat-label">تم الرفض</div>
					</div>
					<div class="ca-mgm-stat-card replied">
						<div class="stat-number" id="stat-replied">0</div>
						<div class="stat-label">تم الرد</div>
					</div>
				</div>

				<!-- Filter Bar -->
				<div class="ca-mgm-filter-bar">
					<div class="ca-mgm-filter-header">
						<div class="filter-header-title">
							<span class="filter-icon">🔍</span>
							<span>خيارات التصفية والفرز</span>
						</div>
					</div>
					<div class="ca-mgm-filters-grid">
						<div class="ca-mgm-filter-group" id="dept-filter-group" style="display: ${this.current_tab === 'all_requests' ? 'flex' : 'none'};">
							<label for="filter-dept">🏢 الجهة / الكلية:</label>
							<select id="filter-dept" class="ca-filter-control">
								<option value="">جميع الجهات والكليات</option>
							</select>
						</div>
						<div class="ca-mgm-filter-group">
							<label for="filter-status">📌 حالة الطلب:</label>
							<select id="filter-status" class="ca-filter-control">
								<option value="All">جميع الحالات</option>
								<option value="Open">قيد الانتظار (Open)</option>
								<option value="Accepted">مقبول (Accepted)</option>
								<option value="Rejected">مرفوض (Rejected)</option>
								<option value="Replied">تم الرد (Replied)</option>
								<option value="Closed">مغلق (Closed)</option>
							</select>
						</div>
						<div class="ca-mgm-filter-group">
							<label for="filter-from-date">📅 من تاريخ:</label>
							<input type="date" id="filter-from-date" class="ca-filter-control">
						</div>
						<div class="ca-mgm-filter-group">
							<label for="filter-to-date">📅 إلى تاريخ:</label>
							<input type="date" id="filter-to-date" class="ca-filter-control">
						</div>
						<div class="ca-mgm-filter-actions">
							<button class="ca-mgm-btn ca-btn-primary" id="btn-apply-filters">
								<span>⚡ تطبيق الفرز</span>
							</button>
							<button class="ca-mgm-btn ca-btn-outline" id="btn-reset-filters">
								<span>🔄 إعادة ضبط</span>
							</button>
						</div>
					</div>
				</div>

				<!-- Table Container -->
				<div class="ca-mgm-table-wrap" id="ca-table-container">
					<div class="ca-mgm-empty">
						<div class="empty-icon">⏳</div>
						<h3>جاري تحميل الطلبات...</h3>
					</div>
				</div>
			</div>
		`);

		this.bind_events();
		if (this.user_role_info.is_admin) {
			this.load_departments_filter();
		}
	}

	bind_events() {
		const self = this;

		// Tab Switch
		this.wrapper.find(".ca-mgm-tab").on("click", function () {
			self.wrapper.find(".ca-mgm-tab").removeClass("active");
			$(this).addClass("active");
			self.current_tab = $(this).data("tab");

			if (self.current_tab === "all_requests") {
				self.wrapper.find("#dept-filter-group").css("display", "flex");
			} else {
				self.wrapper.find("#dept-filter-group").css("display", "none");
				self.filters.department = "";
			}
			self.load_data();
		});

		// Filters
		this.wrapper.find("#btn-apply-filters").on("click", () => {
			this.filters.department = this.wrapper.find("#filter-dept").val() || "";
			this.filters.status = this.wrapper.find("#filter-status").val() || "All";
			this.filters.from_date = this.wrapper.find("#filter-from-date").val() || "";
			this.filters.to_date = this.wrapper.find("#filter-to-date").val() || "";
			this.load_data();
		});

		this.wrapper.find("#btn-reset-filters").on("click", () => {
			this.wrapper.find("#filter-dept").val("");
			this.wrapper.find("#filter-status").val("All");
			this.wrapper.find("#filter-from-date").val("");
			this.wrapper.find("#filter-to-date").val("");
			this.filters = { department: "", status: "All", from_date: "", to_date: "" };
			this.load_data();
		});
	}

	async load_departments_filter() {
		try {
			const res = await frappe.call({
				method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_departments_list"
			});
			if (res.message) {
				const select = this.wrapper.find("#filter-dept");
				select.empty().append('<option value="">جميع الجهات</option>');
				res.message.forEach((d) => {
					select.append(`<option value="${d.name}">${d.department_name || d.name}</option>`);
				});
			}
		} catch (e) {
			console.error(e);
		}
	}

	async load_data() {
		this.wrapper.find("#ca-table-container").html(`
			<div class="ca-mgm-empty">
				<div class="empty-icon">⏳</div>
				<h3>جاري تحميل الطلبات...</h3>
			</div>
		`);

		const method =
			this.current_tab === "all_requests"
				? "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_all_requests"
				: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.get_department_requests";

		try {
			const res = await frappe.call({
				method: method,
				args: {
					department: this.filters.department,
					status: this.filters.status,
					from_date: this.filters.from_date,
					to_date: this.filters.to_date
				}
			});

			const requests = res.message || [];
			this.update_stats(requests);
			this.render_table(requests);
		} catch (e) {
			console.error(e);
			this.wrapper.find("#ca-table-container").html(`
				<div class="ca-mgm-empty">
					<div class="empty-icon">❌</div>
					<h3>حدث خطأ أثناء جلب البيانات</h3>
				</div>
			`);
		}
	}

	update_stats(requests) {
		const total = requests.length;
		const open = requests.filter((r) => r.status === "Open").length;
		const accepted = requests.filter((r) => r.status === "Accepted").length;
		const rejected = requests.filter((r) => r.status === "Rejected").length;
		const replied = requests.filter((r) => r.status === "Replied").length;

		this.wrapper.find("#stat-total").text(total);
		this.wrapper.find("#stat-open").text(open);
		this.wrapper.find("#stat-accepted").text(accepted);
		this.wrapper.find("#stat-rejected").text(rejected);
		this.wrapper.find("#stat-replied").text(replied);
	}

	render_table(requests) {
		if (!requests.length) {
			this.wrapper.find("#ca-table-container").html(`
				<div class="ca-mgm-empty">
					<div class="empty-icon">📭</div>
					<h3>لا توجد طلبات مطابقة</h3>
					<p>لم يتم العثور على أي طلبات بناءً على الفرز المحدد.</p>
				</div>
			`);
			return;
		}

		let tbody = "";
		requests.forEach((req) => {
			let status_class = "open";
			let status_text = "قيد الانتظار";
			if (req.status === "Accepted") {
				status_class = "accepted";
				status_text = "مقبول ✓";
			} else if (req.status === "Rejected") {
				status_class = "rejected";
				status_text = "مرفوض ✕";
			} else if (req.status === "Replied") {
				status_class = "replied";
				status_text = "تم الرد";
			} else if (req.status === "Closed") {
				status_class = "closed";
				status_text = "مغلق";
			}

			const date_str = frappe.datetime.str_to_user(req.creation.split(" ")[0]);

			tbody += `
				<tr data-name="${req.name}">
					<td>
						<strong style="color: #2563eb;">${req.name}</strong><br>
						<span style="font-size: 12px; color: var(--text-muted);">${date_str}</span>
					</td>
					<td>
						<strong>${frappe.utils.escape_html(req.full_name)}</strong><br>
						<span style="font-size: 12px; color: var(--text-muted);">${frappe.utils.escape_html(req.occupation || '-')} | ${frappe.utils.escape_html(req.address_area || '-')}</span>
					</td>
					<td>
						<span style="font-weight: 600;">${frappe.utils.escape_html(req.target_department)}</span><br>
						<span style="font-size: 12px; color: var(--text-muted);">${frappe.utils.escape_html(req.phone_number)}</span>
					</td>
					<td>
						<strong>${frappe.utils.escape_html(req.request_subject || 'بدون موضوع')}</strong><br>
						<span style="font-size: 12px; color: var(--text-muted);">${frappe.utils.escape_html((req.request_details || '').substring(0, 50))}...</span>
					</td>
					<td>
						<span class="ca-status ${status_class}">
							<span class="status-dot"></span>
							${status_text}
						</span>
					</td>
					<td style="white-space: nowrap;">
						<button class="ca-mgm-action-btn detail btn-show-details" title="عرض التفاصيل">تفاصيل</button>
						<button class="ca-mgm-action-btn print btn-print-form" title="طباعة الاستمارة الرسمية">🖨️</button>
						${
							["Open", "Replied"].includes(req.status)
								? `
							<button class="ca-mgm-action-btn accept btn-accept-req" title="قبول الطلب">✓ القبول</button>
							<button class="ca-mgm-action-btn reject btn-reject-req" title="رفض الطلب">✕ الرفض</button>
							<button class="ca-mgm-action-btn reply btn-reply-req" title="الرد بملاحظة">💬</button>
						`
								: ""
						}
					</td>
				</tr>
			`;
		});

		const html = `
			<table class="ca-mgm-table">
				<thead>
					<tr>
						<th>رقم الطلب والتاريخ</th>
						<th>مقدم الطلب والمهنة</th>
						<th>الجهة المعنية والهاتف</th>
						<th>الموضوع والتفاصيل</th>
						<th>الحالة</th>
						<th>الإجراءات</th>
					</tr>
				</thead>
				<tbody>
					${tbody}
				</tbody>
			</table>
		`;

		this.wrapper.find("#ca-table-container").html(html);
		this.bind_table_events(requests);
	}

	bind_table_events(requests) {
		const self = this;

		this.wrapper.find(".btn-show-details").on("click", function (e) {
			e.stopPropagation();
			const name = $(this).closest("tr").data("name");
			const req = requests.find((r) => r.name === name);
			if (req) self.show_details_dialog(req);
		});

		this.wrapper.find(".btn-print-form").on("click", function (e) {
			e.stopPropagation();
			const name = $(this).closest("tr").data("name");
			const url = frappe.urllib.get_full_url(
				`/printview?doctype=Citizens%20Affairs%20Request&name=${encodeURIComponent(name)}&format=Citizen%20Affairs%20Form`
			);
			window.open(url, "_blank");
		});

		this.wrapper.find(".btn-accept-req").on("click", function (e) {
			e.stopPropagation();
			const name = $(this).closest("tr").data("name");
			const req = requests.find((r) => r.name === name);
			if (req) self.accept_dialog(req);
		});

		this.wrapper.find(".btn-reject-req").on("click", function (e) {
			e.stopPropagation();
			const name = $(this).closest("tr").data("name");
			const req = requests.find((r) => r.name === name);
			if (req) self.reject_dialog(req);
		});

		this.wrapper.find(".btn-reply-req").on("click", function (e) {
			e.stopPropagation();
			const name = $(this).closest("tr").data("name");
			const req = requests.find((r) => r.name === name);
			if (req) self.reply_dialog(req);
		});
	}

	show_details_dialog(req) {
		const self = this;
		const date_str = frappe.datetime.str_to_user(req.creation.split(" ")[0]);

		let ca_section_html = "";
		if (req.status === "Accepted" || req.status === "Rejected") {
			ca_section_html = `
				<div style="background: ${req.status === 'Accepted' ? '#f0fdf4' : '#fef2f2'}; border: 1px solid ${req.status === 'Accepted' ? '#bbf7d0' : '#fecaca'}; border-radius: 12px; padding: 16px; margin-top: 16px;">
					<h4 style="margin: 0 0 10px 0; color: ${req.status === 'Accepted' ? '#166534' : '#991b1b'};">📋 قسم شعبة شؤون المواطنين (${req.decision || (req.status === 'Accepted' ? 'قبول الطلب' : 'رفض الطلب')}):</h4>
					<p style="margin: 4px 0;"><strong>اسم مستلم الطلب:</strong> ${req.receiver_name || '-'}</p>
					<p style="margin: 4px 0;"><strong>تاريخ الاستلام:</strong> ${req.receipt_date || '-'}</p>
					<p style="margin: 4px 0;"><strong>التوصية:</strong> ${req.recommendation || '-'}</p>
					${req.rejection_reasons ? `<p style="margin: 4px 0; color: #dc2626;"><strong>مبررات الرفض:</strong> ${req.rejection_reasons}</p>` : ''}
					<p style="margin: 4px 0;"><strong>مسؤول الشعبة:</strong> ${req.ca_officer_name || '-'} — بتاريخ (${req.ca_officer_date || '-'})</p>
				</div>
			`;
		}

		let reply_html = "";
		if (req.reply_text) {
			reply_html = `
				<div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 16px; margin-top: 16px;">
					<h4 style="margin: 0 0 8px 0; color: #1e40af;">💬 الرد المرسل للمواطن:</h4>
					<p style="margin: 0; white-space: pre-wrap;">${req.reply_text}</p>
					<small style="color: #64748b; display: block; margin-top: 8px;">بواسطة: ${req.replied_by || '-'} في ${frappe.datetime.str_to_user(req.replied_on || '')}</small>
				</div>
			`;
		}

		const d = new frappe.ui.Dialog({
			title: `تفاصيل استمارة شؤون المواطنين (${req.name})`,
			size: "large",
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "details_html",
					options: `
						<div style="font-size: 14px; line-height: 1.8;">
							<div style="display: flex; justify-content: space-between; border-bottom: 2px solid var(--border-color); padding-bottom: 12px; margin-bottom: 16px;">
								<div>
									<h3 style="margin: 0; color: #2563eb;">${req.full_name}</h3>
									<span style="color: var(--text-muted);">${req.occupation || '-'} | ${req.address_area || '-'}</span>
								</div>
								<div style="text-align: left;">
									<strong style="display: block;">${req.name}</strong>
									<span style="color: var(--text-muted);">${date_str}</span>
								</div>
							</div>

							<table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
								<tr>
									<td style="padding: 6px 0; width: 25%;"><strong>الجهة المعنية:</strong></td>
									<td style="padding: 6px 0;">${req.target_department}</td>
									<td style="padding: 6px 0; width: 20%;"><strong>رقم الهاتف:</strong></td>
									<td style="padding: 6px 0;"><a href="tel:${req.phone_number}" style="color: #2563eb; font-weight: bold;">${req.phone_number}</a></td>
								</tr>
								<tr>
									<td style="padding: 6px 0;"><strong>البريد الإلكتروني:</strong></td>
									<td style="padding: 6px 0;"><a href="mailto:${req.email}" style="color: #2563eb;">${req.email}</a></td>
									<td style="padding: 6px 0;"><strong>الحالة الحالية:</strong></td>
									<td style="padding: 6px 0;"><b>${req.status}</b></td>
								</tr>
							</table>

							<div style="background: var(--card-bg); border: 1.5px solid var(--border-color); border-radius: 12px; padding: 16px; margin-bottom: 16px;">
								<h4 style="margin: 0 0 8px 0; color: #2563eb;">م / ${req.request_subject || 'بدون موضوع'}</h4>
								<p style="margin: 0; white-space: pre-wrap; font-size: 15px;">${req.request_details}</p>
							</div>

							${
								req.attachment_1 || req.attachment_2
									? `
								<div style="margin-bottom: 16px;">
									<strong>📎 المرفقات الداعمة:</strong><br>
									${req.attachment_1 ? `<div>• المرفق 1: <a href="${req.attachment_1}" target="_blank" style="color:#2563eb;">${req.attachment_1}</a></div>` : ''}
									${req.attachment_2 ? `<div>• المرفق 2: <a href="${req.attachment_2}" target="_blank" style="color:#2563eb;">${req.attachment_2}</a></div>` : ''}
								</div>
							`
									: ""
							}

							<div style="border-top: 1px dashed var(--border-color); padding-top: 12px; color: var(--text-muted); font-size: 13px;">
								✍️ التعهد: التزم بصحة المعلومات الواردة في الطلب وأتحمل المسؤولية كافة وعليه أوقع.<br>
								<b>توقيع مقدم الطلب:</b> ${req.applicant_signature_name || req.full_name} — <b>بتاريخ:</b> ${req.applicant_submission_date || date_str}
							</div>

							${ca_section_html}
							${reply_html}
						</div>
					`
				}
			],
			primary_action_label: "🖨️ طباعة الاستمارة الرسمية",
			primary_action() {
				const url = frappe.urllib.get_full_url(
					`/printview?doctype=Citizens%20Affairs%20Request&name=${encodeURIComponent(req.name)}&format=Citizen%20Affairs%20Form`
				);
				window.open(url, "_blank");
			}
		});

		// Add Accept / Reject buttons right in the modal footer if open/replied
		if (["Open", "Replied"].includes(req.status)) {
			d.add_custom_action("✓ قبول الطلب", () => {
				d.hide();
				self.accept_dialog(req);
			}, "btn-success");

			d.add_custom_action("✕ رفض الطلب", () => {
				d.hide();
				self.reject_dialog(req);
			}, "btn-danger");
		}

		this.setup_rtl_dialog(d);
		d.show();
	}

	accept_dialog(req) {
		const self = this;
		const d = new frappe.ui.Dialog({
			title: `اعتماد قبول طلب المواطن (${req.name})`,
			fields: [
				{
					fieldtype: "Data",
					fieldname: "receiver_name",
					label: "اسم مستلم الطلب",
					default: frappe.session.user_fullname
				},
				{
					fieldtype: "Date",
					fieldname: "receipt_date",
					label: "تاريخ الاستلام",
					default: frappe.datetime.get_today()
				},
				{
					fieldtype: "Text",
					fieldname: "recommendation",
					label: "التوصية",
					default: "الموافقة على الطلب وفق الضوابط والتعليمات وسياقات العمل."
				},
				{
					fieldtype: "Data",
					fieldname: "ca_officer_name",
					label: "مسؤول شعبة شؤون المواطنين",
					default: frappe.session.user_fullname
				},
				{
					fieldtype: "Text",
					fieldname: "reply_text",
					label: "نص إشعار القبول (الذي سيتم إرساله بالبريد الإلكتروني للمواطن)",
					default: `تم الموافقة وقبول طلبكم رقم (${req.name}) الوارد إلى ${req.target_department} وسيتم اتخاذ الإجراء اللازم.`
				}
			],
			primary_action_label: "تأكيد القبول وإرسال الإشعار",
			primary_action(values) {
				frappe.call({
					method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.accept_citizen_request",
					args: {
						request_name: req.name,
						receiver_name: values.receiver_name,
						receipt_date: values.receipt_date,
						recommendation: values.recommendation,
						ca_officer_name: values.ca_officer_name,
						reply_text: values.reply_text
					},
					freeze: true,
					freeze_message: "جاري حفظ قرار القبول وإرسال الإشعار للمواطن...",
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: "تم قبول الطلب وإرسال الإشعار بنجاح",
								indicator: "green"
							});
							d.hide();
							self.load_data();
						}
					}
				});
			}
		});
		this.setup_rtl_dialog(d);
		d.show();
	}

	reject_dialog(req) {
		const self = this;
		const d = new frappe.ui.Dialog({
			title: `الاعتذار عن قبول الطلب - رفض الطلب (${req.name})`,
			fields: [
				{
					fieldtype: "Text",
					fieldname: "rejection_reasons",
					label: "مبررات وأسباب رفض الطلب (مطلوب)",
					reqd: 1,
					description: "يرجى ذكر المبررات بوضوح ودقة حيث سيتم إرسالها لمقدم الطلب عبر البريد الإلكتروني"
				},
				{
					fieldtype: "Data",
					fieldname: "receiver_name",
					label: "اسم مستلم الطلب",
					default: frappe.session.user_fullname
				},
				{
					fieldtype: "Date",
					fieldname: "receipt_date",
					label: "تاريخ الاستلام",
					default: frappe.datetime.get_today()
				},
				{
					fieldtype: "Text",
					fieldname: "recommendation",
					label: "التوصية",
					default: "نعتذر عن قبول الطلب لعدم استيفاء الضوابط أو الشروط المطلوبة."
				},
				{
					fieldtype: "Data",
					fieldname: "ca_officer_name",
					label: "مسؤول شعبة شؤون المواطنين",
					default: frappe.session.user_fullname
				}
			],
			primary_action_label: "تأكيد الرفض وإرسال المبررات",
			primary_action(values) {
				frappe.call({
					method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.reject_citizen_request",
					args: {
						request_name: req.name,
						rejection_reasons: values.rejection_reasons,
						receiver_name: values.receiver_name,
						receipt_date: values.receipt_date,
						recommendation: values.recommendation,
						ca_officer_name: values.ca_officer_name
					},
					freeze: true,
					freeze_message: "جاري حفظ الرفض وإرسال المبررات للمواطن...",
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: "تم حفظ الرفض وإشعار المواطن بالمبررات",
								indicator: "red"
							});
							d.hide();
							self.load_data();
						}
					}
				});
			}
		});
		this.setup_rtl_dialog(d);
		d.show();
	}

	reply_dialog(req) {
		const self = this;
		const d = new frappe.ui.Dialog({
			title: `إرسال رد أو ملاحظة لمقدم الطلب (${req.name})`,
			fields: [
				{
					fieldtype: "Text",
					fieldname: "reply_text",
					label: "نص الرد",
					reqd: 1,
					default: req.reply_text || ""
				}
			],
			primary_action_label: "إرسال الرد بالبريد الإلكتروني",
			primary_action(values) {
				frappe.call({
					method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.reply_to_request",
					args: {
						request_name: req.name,
						reply_text: values.reply_text
					},
					freeze: true,
					freeze_message: "جاري إرسال الرد...",
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: "تم إرسال الرد بنجاح",
								indicator: "green"
							});
							d.hide();
							self.load_data();
						}
					}
				});
			}
		});
		this.setup_rtl_dialog(d);
		d.show();
	}

	setup_rtl_dialog(d) {
		if (d && d.$wrapper) {
			d.$wrapper.find(".modal-content, .modal-dialog").attr("dir", "rtl").css({
				direction: "rtl",
				"text-align": "right",
				"font-family": "'Cairo', 'Segoe UI', Tahoma, sans-serif"
			});
			d.$wrapper.find(".modal-header .close").css({
				float: "left",
				margin: "-1rem auto -1rem -1rem"
			});
		}
	}
}