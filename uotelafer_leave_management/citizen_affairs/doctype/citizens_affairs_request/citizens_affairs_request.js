// Copyright (c) 2026, Computer Center of UoT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Citizens Affairs Request", {
	refresh(frm) {
		// Add Reply button for department heads / admins
		if (!frm.is_new() && frm.doc.status === "Open") {
			frm.add_custom_button(__("الرد على الطلب"), function () {
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
