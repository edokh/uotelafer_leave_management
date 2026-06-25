# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CitizensAffairsRequest(Document):
	def autoname(self):
		import random
		
		# Generate a 4-digit random number
		while True:
			# using randint ensures we get digits (0-9). zfill pads it to 4 digits (e.g. 0123)
			rand_name = str(random.randint(0, 9999)).zfill(4)
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

		# Get the department head's email
		head_email = dept.department_head  # This is a User link, which is the email
		head_name = dept.department_head_name or dept.department_head

		subject = f"طلب جديد في شؤون المواطنين - {self.full_name}"
		message = f"""
		<div dir="rtl" style="font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; padding: 20px;">
			<h2 style="color: #1e40af;">طلب جديد في شؤون المواطنين</h2>
			<p>السيد/السيدة <b>{head_name}</b>، تحية طيبة</p>
			<p>تم تقديم طلب جديد إلى قسمكم، تفاصيل الطلب:</p>
			<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
				<tr style="background: #f1f5f9;">
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">الاسم الكامل</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.full_name}</td>
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
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">الجهة المعنية</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.target_department}</td>
				</tr>
				<tr style="background: #f1f5f9;">
					<td style="padding: 10px 16px; font-weight: bold; border: 1px solid #e2e8f0;">تفاصيل الطلب</td>
					<td style="padding: 10px 16px; border: 1px solid #e2e8f0;">{self.request_details}</td>
				</tr>
			</table>
			<p>يمكنك الرد على الطلب من خلال صفحة إدارة شؤون المواطنين.</p>
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
def submit_citizen_request(full_name, target_department, request_details, phone_number, email):
	"""Public API for guest users to submit a citizen affairs request."""
	# Validate required fields
	if not all([full_name, target_department, request_details, phone_number, email]):
		frappe.throw(_("جميع الحقول مطلوبة"))

	# Validate department exists
	if not frappe.db.exists("Leave Department", target_department):
		frappe.throw(_("الجهة المعنية غير موجودة"))

	# Validate email format
	import re
	if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
		frappe.throw(_("البريد الإلكتروني غير صحيح"))

	doc = frappe.get_doc({
		"doctype": "Citizens Affairs Request",
		"full_name": full_name,
		"target_department": target_department,
		"request_details": request_details,
		"phone_number": phone_number,
		"email": email,
		"status": "Open"
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
	doc.replied_on = frappe.utils.now()
	doc.status = "Replied"
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	# Send email to the citizen
	subject = f"رد على طلبكم - شؤون المواطنين - {doc.target_department}"
	replied_by_name = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	message = f"""
	<div dir="rtl" style="font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; padding: 20px;">
		<h2 style="color: #059669;">رد على طلبكم</h2>
		<p>السيد/السيدة <b>{doc.full_name}</b>، تحية طيبة</p>
		<p>تم الرد على طلبكم المقدم إلى <b>{doc.target_department}</b>:</p>
		<div style="background: #f0fdf4; border-right: 4px solid #22c55e; padding: 16px; border-radius: 8px; margin: 16px 0;">
			<p style="margin: 0; font-size: 16px; line-height: 1.8;">{reply_text}</p>
		</div>
		<p style="color: #6b7280; font-size: 13px;">تم الرد بواسطة: {replied_by_name}</p>
		<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
		<p style="color: #9ca3af; font-size: 12px;">هذا البريد مرسل تلقائياً من نظام شؤون المواطنين</p>
	</div>
	"""

	try:
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
def get_department_requests(department=None, status=None, from_date=None, to_date=None):
	"""Get requests for a specific department (for department head)."""
	user = frappe.session.user

	# Find the department(s) this user heads
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
			"name", "full_name", "phone_number", "email",
			"target_department", "request_details", "status",
			"creation", "reply_text", "replied_by", "replied_on"
		],
		order_by="creation desc",
		limit_page_length=200
	)

	return requests


@frappe.whitelist()
def get_all_requests(department=None, status=None, from_date=None, to_date=None):
	"""Get all requests across all departments (for admin role)."""
	if not _is_citizen_affairs_admin() and "System Manager" not in frappe.get_roles():
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
			"name", "full_name", "phone_number", "email",
			"target_department", "request_details", "status",
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
	dept_head_role = settings.department_head_role or "Department Head"
	admin_role = settings.citizens_affairs_admin_role or ""

	return {
		"is_dept_head": bool(departments),
		"departments": departments,
		"is_admin": admin_role in roles or "System Manager" in roles,
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
	try:
		settings = frappe.get_single("Leave Settings")
		admin_role = settings.citizens_affairs_admin_role
		if admin_role and admin_role in frappe.get_roles():
			return True
	except Exception:
		pass
	return False
