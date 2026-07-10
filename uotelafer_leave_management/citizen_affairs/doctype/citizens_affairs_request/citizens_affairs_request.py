# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import random
import re
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, today


class CitizensAffairsRequest(Document):
	def autoname(self):
		# Generate a prestigious CA request number like CA-2026-#### or 4 digits
		year = today().split("-")[0]
		while True:
			rand_name = f"CA-{year}-" + str(random.randint(1000, 9999))
			if not frappe.db.exists("Citizens Affairs Request", rand_name):
				self.name = rand_name
				break

	def after_insert(self):
		self.notify_department_head()

	def notify_department_head(self):
		"""Send email notification to department head when a new request is submitted."""
		if not self.target_department:
			return

		dept = frappe.get_doc("Leave Department", self.target_department)
		if not dept.department_head:
			return

		head_email = dept.department_head
		head_name = dept.department_head_name or dept.department_head

		subject = f"طلب جديد في شؤون المواطنين - {self.full_name} ({self.name})"
		message = f"""
		<div dir="rtl" style="font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; padding: 20px;">
			<h2 style="color: #1e40af;">طلب جديد في شؤون المواطنين</h2>
			<p>السيد/السيدة <b>{head_name}</b>، تحية طيبة</p>
			<p>تم تقديم طلب جديد إلى قسمكم، تفاصيل الطلب:</p>
			<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
				<tr style="background: #f1f5f9;">
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">رقم الطلب</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;"><b>{self.name}</b></td>
				</tr>
				<tr>
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">الاسم الرباعي</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.full_name}</td>
				</tr>
				<tr style="background: #f1f5f9;">
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">المهنة / العنوان</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.occupation or '-'} — {self.address_area or '-'}</td>
				</tr>
				<tr>
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">رقم الهاتف</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.phone_number}</td>
				</tr>
				<tr style="background: #f1f5f9;">
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">البريد الإلكتروني</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.email}</td>
				</tr>
				<tr>
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">موضوع الطلب</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.request_subject or 'طلب شؤون مواطنين'}</td>
				</tr>
				<tr style="background: #f1f5f9;">
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">تفاصيل الطلب</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0; white-space: pre-wrap;">{self.request_details}</td>
				</tr>
			</table>
			<p>يمكنك مراجعة الطلب أو الرد عليه من خلال صفحة إدارة شؤون المواطنين.</p>
		</div>
		"""

		try:
			frappe.sendmail(
				recipients=[head_email],
				subject=subject,
				message=message,
				now=True
			)
		except Exception:
			frappe.log_error(f"Failed to send citizen affairs notification to {head_email}")


@frappe.whitelist(allow_guest=True)
def submit_citizen_request(
	full_name,
	target_department,
	request_details,
	phone_number,
	email,
	address_area=None,
	occupation=None,
	request_subject=None,
	applicant_pledge=1,
	applicant_signature_name=None,
	attachment_1=None,
	attachment_2=None,
):
	"""Public API for guest users to submit a citizen affairs request."""
	# Validate required fields
	if not all([full_name, target_department, request_details, phone_number, email]):
		frappe.throw(_("جميع الحقول المطلوبة يجب إدخالها"))

	# Validate department exists
	if not frappe.db.exists("Leave Department", target_department):
		frappe.throw(_("الجهة المعنية غير موجودة"))

	# Validate email format
	if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
		frappe.throw(_("البريد الإلكتروني غير صحيح"))

	doc = frappe.get_doc({
		"doctype": "Citizens Affairs Request",
		"full_name": full_name,
		"address_area": address_area or "",
		"occupation": occupation or "",
		"target_department": target_department,
		"request_subject": request_subject or "طلب شؤون مواطنين",
		"request_details": request_details,
		"phone_number": phone_number,
		"email": email,
		"applicant_pledge": 1 if applicant_pledge else 0,
		"applicant_signature_name": applicant_signature_name or full_name,
		"applicant_submission_date": today(),
		"attachment_1": attachment_1 or "",
		"attachment_2": attachment_2 or "",
		"status": "Open",
		"creation_date": today(),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"success": True, "name": doc.name}


@frappe.whitelist()
def reply_to_request(request_name, reply_text):
	"""Reply to a citizen affairs request and send email notification."""
	if not request_name or not reply_text:
		frappe.throw(_("اسم الطلب ونص الرد مطلوبان"))

	doc = frappe.get_doc("Citizens Affairs Request", request_name)

	doc.reply_text = reply_text
	doc.replied_by = frappe.session.user
	doc.replied_on = now()
	if doc.status == "Open":
		doc.status = "Replied"
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	# Send email to the citizen
	subject = f"رد على طلبكم ({doc.name}) - شؤون المواطنين - {doc.target_department}"
	replied_by_name = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	message = f"""
	<div dir="rtl" style="font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; padding: 20px;">
		<h2 style="color: #059669;">رد على طلبكم</h2>
		<p>السيد/السيدة <b>{doc.full_name}</b> المحترم/ة، تحية طيبة</p>
		<p>تم الرد على طلبكم المقدم إلى <b>{doc.target_department}</b>:</p>
		<div style="background: #f0fdf4; border-right: 4px solid #22c55e; padding: 16px; border-radius: 8px; margin: 16px 0;">
			<p style="margin: 0; font-size: 16px; line-height: 1.8; white-space: pre-wrap;">{reply_text}</p>
		</div>
		<p style="color: #6b7280; font-size: 13px;">تم الرد بواسطة: {replied_by_name}</p>
		<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
		<p style="color: #9ca3af; font-size: 12px;">هذا البريد مرسل تلقائياً من نظام شؤون المواطنين - جامعة تلعفر</p>
	</div>
	"""

	try:
		if doc.email:
			frappe.sendmail(
				recipients=[doc.email],
				subject=subject,
				message=message,
				now=True
			)
	except Exception:
		frappe.log_error(f"Failed to send reply notification to {doc.email}")

	return {"success": True}


@frappe.whitelist()
def accept_citizen_request(
	request_name,
	receiver_name=None,
	receipt_date=None,
	recommendation=None,
	ca_officer_name=None,
	reply_text=None,
):
	"""Accept a citizen affairs request, fill CA department section, and send acceptance notification."""
	if not _is_citizen_affairs_admin() and "Department Head" not in frappe.get_roles():
		frappe.throw(_("ليس لديك صلاحية لقبول الطلبات"))

	doc = frappe.get_doc("Citizens Affairs Request", request_name)
	doc.status = "Accepted"
	doc.decision = "قبول الطلب"
	if receiver_name:
		doc.receiver_name = receiver_name
	if receipt_date:
		doc.receipt_date = receipt_date
	else:
		doc.receipt_date = today()
	if recommendation:
		doc.recommendation = recommendation
	if ca_officer_name:
		doc.ca_officer_name = ca_officer_name
	doc.ca_officer_date = today()

	if reply_text:
		doc.reply_text = reply_text
		doc.replied_by = frappe.session.user
		doc.replied_on = now()

	doc.save(ignore_permissions=True)
	frappe.db.commit()

	# Send acceptance email
	subject = f"قبول طلبكم ({doc.name}) - شؤون المواطنين - {doc.target_department}"
	replied_by_name = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	msg_body = reply_text or f"نفيدكم علماً بأنه قد تم قبول طلبكم رقم ({doc.name}) الوارد إلى {doc.target_department}."

	message = f"""
	<div dir="rtl" style="font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; padding: 20px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;">
		<div style="text-align: center; margin-bottom: 20px;">
			<h2 style="color: #15803d; margin: 0;">تم قبول الطلب ✓</h2>
			<p style="color: #64748b; margin-top: 5px;">شعبة شؤون المواطنين - جامعة تلعفر</p>
		</div>
		<p>السيد/السيدة <b>{doc.full_name}</b> المحترم/ة، تحية طيبة وبعد،</p>
		<p>يسرنا إعلامكم بأنه تم <b>قبول طلبكم</b> رقم <b>({doc.name})</b> المقدم إلى <b>{doc.target_department}</b>.</p>
		<div style="background: #f0fdf4; border-right: 4px solid #22c55e; padding: 16px; border-radius: 8px; margin: 16px 0; color: #166534;">
			<p style="margin: 0; font-size: 16px; line-height: 1.8; white-space: pre-wrap;">{msg_body}</p>
		</div>
		<p style="color: #6b7280; font-size: 13px;">تم المعالجة بواسطة: {ca_officer_name or replied_by_name} — بتاريخ {doc.ca_officer_date}</p>
		<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
		<p style="color: #9ca3af; font-size: 12px; text-align: center;">هذا البريد مرسل تلقائياً من نظام إدارة شؤون المواطنين - جامعة تلعفر</p>
	</div>
	"""
	try:
		if doc.email:
			frappe.sendmail(recipients=[doc.email], subject=subject, message=message, now=True)
	except Exception:
		frappe.log_error(f"Failed to send acceptance notification to {doc.email}")

	return {"success": True}


@frappe.whitelist()
def reject_citizen_request(
	request_name,
	rejection_reasons,
	receiver_name=None,
	receipt_date=None,
	recommendation=None,
	ca_officer_name=None,
):
	"""Reject a citizen affairs request, record reasons, and send rejection notification."""
	if not _is_citizen_affairs_admin() and "Department Head" not in frappe.get_roles():
		frappe.throw(_("ليس لديك صلاحية لرفض الطلبات"))

	if not rejection_reasons:
		frappe.throw(_("مبررات رفض الطلب مطلوبة عند الرفض"))

	doc = frappe.get_doc("Citizens Affairs Request", request_name)
	doc.status = "Rejected"
	doc.decision = "رفض الطلب"
	doc.rejection_reasons = rejection_reasons
	if receiver_name:
		doc.receiver_name = receiver_name
	if receipt_date:
		doc.receipt_date = receipt_date
	else:
		doc.receipt_date = today()
	if recommendation:
		doc.recommendation = recommendation
	if ca_officer_name:
		doc.ca_officer_name = ca_officer_name
	doc.ca_officer_date = today()

	doc.save(ignore_permissions=True)
	frappe.db.commit()

	# Send rejection email
	subject = f"تحديث بشأن طلبكم ({doc.name}) - شؤون المواطنين - {doc.target_department}"
	replied_by_name = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	message = f"""
	<div dir="rtl" style="font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; padding: 20px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;">
		<div style="text-align: center; margin-bottom: 20px;">
			<h2 style="color: #b91c1c; margin: 0;">تحديث بشأن طلبكم</h2>
			<p style="color: #64748b; margin-top: 5px;">شعبة شؤون المواطنين - جامعة تلعفر</p>
		</div>
		<p>السيد/السيدة <b>{doc.full_name}</b> المحترم/ة، تحية طيبة وبعد،</p>
		<p>نود إعلامكم بأنه تم مراجعة طلبكم رقم <b>({doc.name})</b> المقدم إلى <b>{doc.target_department}</b>، وقد تم <b>الاعتذار عن قبول الطلب (رفض الطلب)</b> للمبررات التالية:</p>
		<div style="background: #fef2f2; border-right: 4px solid #ef4444; padding: 16px; border-radius: 8px; margin: 16px 0; color: #991b1b;">
			<p style="margin: 0; font-size: 16px; line-height: 1.8; white-space: pre-wrap;">{rejection_reasons}</p>
		</div>
		<p style="color: #6b7280; font-size: 13px;">مسؤول شعبة شؤون المواطنين: {ca_officer_name or replied_by_name} — بتاريخ {doc.ca_officer_date}</p>
		<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
		<p style="color: #9ca3af; font-size: 12px; text-align: center;">هذا البريد مرسل تلقائياً من نظام إدارة شؤون المواطنين - جامعة تلعفر</p>
	</div>
	"""
	try:
		if doc.email:
			frappe.sendmail(recipients=[doc.email], subject=subject, message=message, now=True)
	except Exception:
		frappe.log_error(f"Failed to send rejection notification to {doc.email}")

	return {"success": True}


@frappe.whitelist()
def get_department_requests(department=None, status=None, from_date=None, to_date=None):
	"""Get requests for a specific department (for department head)."""
	user = frappe.session.user

	departments = frappe.get_all(
		"Leave Department",
		filters={"department_head": user},
		pluck="name"
	)

	if not departments and not _is_citizen_affairs_admin():
		frappe.throw(_("ليس لديك صلاحية للوصول إلى هذه الصفحة"))

	filters = {}

	if department:
		filters["target_department"] = department
	elif departments and not _is_citizen_affairs_admin():
		filters["target_department"] = ["in", departments]

	if status and status != "All":
		filters["status"] = status

	if from_date:
		filters["creation"] = [">=", from_date]
	if to_date:
		if "creation" in filters:
			filters["creation"] = ["between", [from_date, to_date]]
		else:
			filters["creation"] = ["<=", to_date]

	requests = frappe.get_all(
		"Citizens Affairs Request",
		filters=filters,
		fields=[
			"name", "full_name", "address_area", "occupation",
			"phone_number", "email", "target_department",
			"request_subject", "request_details", "status", "decision",
			"applicant_pledge", "applicant_signature_name", "applicant_submission_date",
			"attachment_1", "attachment_2",
			"receiver_name", "receiver_signature", "receipt_date",
			"recommendation", "rejection_reasons", "ca_officer_name", "ca_officer_date",
			"creation", "reply_text", "replied_by", "replied_on"
		],
		order_by="creation desc",
		limit_page_length=200
	)

	return requests


@frappe.whitelist()
def get_all_requests(department=None, status=None, from_date=None, to_date=None):
	"""Get all requests across all departments (for admin / citizen affairs manager role)."""
	if not _is_citizen_affairs_admin():
		frappe.throw(_("ليس لديك صلاحية للوصول إلى هذه الصفحة"))

	filters = {}

	if department:
		filters["target_department"] = department

	if status and status != "All":
		filters["status"] = status

	if from_date:
		filters["creation"] = [">=", from_date]
	if to_date:
		if "creation" in filters:
			filters["creation"] = ["between", [from_date, to_date]]
		else:
			filters["creation"] = ["<=", to_date]

	requests = frappe.get_all(
		"Citizens Affairs Request",
		filters=filters,
		fields=[
			"name", "full_name", "address_area", "occupation",
			"phone_number", "email", "target_department",
			"request_subject", "request_details", "status", "decision",
			"applicant_pledge", "applicant_signature_name", "applicant_submission_date",
			"attachment_1", "attachment_2",
			"receiver_name", "receiver_signature", "receipt_date",
			"recommendation", "rejection_reasons", "ca_officer_name", "ca_officer_date",
			"creation", "reply_text", "replied_by", "replied_on"
		],
		order_by="creation desc",
		limit_page_length=500
	)

	return requests


@frappe.whitelist()
def get_user_citizen_role():
	"""Get the user's citizen affairs role info."""
	user = frappe.session.user
	roles = frappe.get_roles(user)

	departments = frappe.get_all(
		"Leave Department",
		filters={"department_head": user},
		pluck="name"
	)

	settings = frappe.get_single("Leave Settings")
	admin_role = settings.citizens_affairs_admin_role or ""

	is_admin = (
		"System Manager" in roles
		or "Citizen Affairs Manager" in roles
		or (admin_role and admin_role in roles)
	)

	return {
		"is_dept_head": bool(departments),
		"departments": departments,
		"is_admin": is_admin,
		"is_system_manager": "System Manager" in roles
	}


@frappe.whitelist()
def get_departments_list():
	"""Get list of all departments."""
	return frappe.get_all(
		"Leave Department",
		fields=["name", "department_name"],
		order_by="department_name asc"
	)


def _is_citizen_affairs_admin():
	"""Check if current user has the citizens affairs admin role."""
	roles = frappe.get_roles()
	if "System Manager" in roles or "Citizen Affairs Manager" in roles:
		return True
	try:
		settings = frappe.get_single("Leave Settings")
		admin_role = settings.citizens_affairs_admin_role
		if admin_role and admin_role in roles:
			return True
	except Exception:
		pass
	return False
