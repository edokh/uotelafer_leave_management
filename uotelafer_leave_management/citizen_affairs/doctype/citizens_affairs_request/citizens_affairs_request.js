// Copyright (c) 2026, Computer Center of UoT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Citizens Affairs Request", {
	refresh(frm) {
		// Print Button
		if (!frm.is_new()) {
			frm.add_custom_button(__("🖨️ طباعة الاستمارة"), function () {
				let url = frappe.urllib.get_full_url(
					`/printview?doctype=Citizens%20Affairs%20Request&name=${encodeURIComponent(frm.doc.name)}&format=Citizen%20Affairs%20Form`
				);
				window.open(url, "_blank");
			});
		}

		// Actions only for saved and open/replied requests
		if (!frm.is_new() && ["Open", "Replied"].includes(frm.doc.status)) {
			// Accept Button
			frm.add_custom_button(__("قبول الطلب ✅"), function () {
				let d = new frappe.ui.Dialog({
					title: "قبول طلب شؤون المواطنين",
					fields: [
						{
							fieldtype: "Data",
							fieldname: "receiver_name",
							label: "اسم مستلم الطلب",
							default: frm.doc.receiver_name || frappe.session.user_fullname
						},
						{
							fieldtype: "Date",
							fieldname: "receipt_date",
							label: "تاريخ الاستلام",
							default: frm.doc.receipt_date || frappe.datetime.get_today()
						},
						{
							fieldtype: "Text",
							fieldname: "recommendation",
							label: "التوصية",
							default: frm.doc.recommendation || "الموافقة على الطلب وفق الضوابط والتعليمات."
						},
						{
							fieldtype: "Data",
							fieldname: "ca_officer_name",
							label: "مسؤول شعبة شؤون المواطنين",
							default: frm.doc.ca_officer_name || frappe.session.user_fullname
						},
						{
							fieldtype: "Text",
							fieldname: "reply_text",
							label: "نص إشعار القبول (للمواطن)",
							description: "سيتم إرسال هذا النص عبر البريد الإلكتروني لمقدم الطلب",
							default: `تم قبول طلبكم رقم (${frm.doc.name}) الوارد إلى ${frm.doc.target_department} وسيتم إجراء اللازم.`
						}
					],
					primary_action_label: "اعتماد القبول وإرسال الإشعار",
					primary_action(values) {
						frappe.call({
							method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.accept_citizen_request",
							args: {
								request_name: frm.doc.name,
								receiver_name: values.receiver_name,
								receipt_date: values.receipt_date,
								recommendation: values.recommendation,
								ca_officer_name: values.ca_officer_name,
								reply_text: values.reply_text
							},
							freeze: true,
							freeze_message: "جاري اعتماد القبول وإرسال الإشعار...",
							callback: function (r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: "تم قبول الطلب وإخطار المواطن بنجاح",
										indicator: "green"
									});
									d.hide();
									frm.reload_doc();
								}
							}
						});
					}
				});
				d.show();
			}, __("إجراءات"));

			// Reject Button
			frm.add_custom_button(__("رفض الطلب ❌"), function () {
				let d = new frappe.ui.Dialog({
					title: "الاعتذار عن قبول الطلب (رفض الطلب)",
					fields: [
						{
							fieldtype: "Text",
							fieldname: "rejection_reasons",
							label: "مبررات رفض الطلب",
							reqd: 1,
							description: "يرجى ذكر الأسباب والمبررات بوضوح لإرسالها لمقدم الطلب"
						},
						{
							fieldtype: "Data",
							fieldname: "receiver_name",
							label: "اسم مستلم الطلب",
							default: frm.doc.receiver_name || frappe.session.user_fullname
						},
						{
							fieldtype: "Date",
							fieldname: "receipt_date",
							label: "تاريخ الاستلام",
							default: frm.doc.receipt_date || frappe.datetime.get_today()
						},
						{
							fieldtype: "Text",
							fieldname: "recommendation",
							label: "التوصية",
							default: frm.doc.recommendation || "نعتذر عن قبول الطلب لعدم استيفاء الشروط أو الضوابط."
						},
						{
							fieldtype: "Data",
							fieldname: "ca_officer_name",
							label: "مسؤول شعبة شؤون المواطنين",
							default: frm.doc.ca_officer_name || frappe.session.user_fullname
						}
					],
					primary_action_label: "اعتماد الرفض وإرسال الإشعار",
					primary_action(values) {
						frappe.call({
							method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.reject_citizen_request",
							args: {
								request_name: frm.doc.name,
								rejection_reasons: values.rejection_reasons,
								receiver_name: values.receiver_name,
								receipt_date: values.receipt_date,
								recommendation: values.recommendation,
								ca_officer_name: values.ca_officer_name
							},
							freeze: true,
							freeze_message: "جاري حفظ أسباب الرفض وإرسال الإشعار...",
							callback: function (r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: "تم حفظ الرفض وإخطار المواطن بالمبررات",
										indicator: "red"
									});
									d.hide();
									frm.reload_doc();
								}
							}
						});
					}
				});
				d.show();
			}, __("إجراءات"));

			// Reply Button
			frm.add_custom_button(__("الرد على الطلب 💬"), function () {
				let d = new frappe.ui.Dialog({
					title: "الرد على الطلب",
					fields: [
						{
							fieldtype: "Text",
							fieldname: "reply_text",
							label: "نص الرد",
							reqd: 1
						}
					],
					primary_action_label: "إرسال الرد",
					primary_action(values) {
						frappe.call({
							method: "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.reply_to_request",
							args: {
								request_name: frm.doc.name,
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
									frm.reload_doc();
								}
							}
						});
					}
				});
				d.show();
			}, __("إجراءات"));
		}
	}
});
