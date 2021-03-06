# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.model.document import Document
from frappe.desk.reportview import get_match_cond, get_filters_cond
from frappe.utils import comma_and

class ProgramEnrollment(Document):
	def validate(self):
		self.validate_duplication()
		if not self.student_name:
			self.student_name = frappe.db.get_value("Student", self.student, "title")
		if not self.courses:
			self.extend("courses", self.get_courses())		

	def on_submit(self):
		self.update_student_joining_date()
		if(self.invoice):
			pass
		else:
			self.make_fee_records()

		
	def validate_duplication(self):
		enrollment = frappe.get_all("Program Enrollment", filters={
			"student": self.student,
			"program": self.program,
			"academic_year": self.academic_year,
			"docstatus": ("<", 2),
			"name": ("!=", self.name)
		})
		if enrollment:
			frappe.throw(_("Student is already enrolled."))
	
	def update_student_joining_date(self):
		date = frappe.db.sql("select min(enrollment_date) from `tabProgram Enrollment` where student= %s", self.student)
		frappe.db.set_value("Student", self.student, "joining_date", date)
		
	def make_fee_records(self):
		from erpnext.education.api import get_fee_components
		fee_list = []
		for d in self.fees:
			#fee_components = get_fee_components(d.fee_structure)
			if fee_components:
				fees = frappe.new_doc("Fees")
				fees.update({
					"student": self.student,
					"academic_year": self.academic_year,
					"academic_term": d.academic_term,
					"fee_structure": d.fee_structure,
					"program": self.program,
					"due_date": d.due_date,
					"student_name": self.student_name,
					"program_enrollment": self.name,
					"components": fee_components
				})
				
				fees.save()
				fees.submit()
				fee_list.append(fees.name)
		if fee_list:
			fee_list = ["""<a href="#Form/Fees/%s" target="_blank">%s</a>""" % \
				(fee, fee) for fee in fee_list]
			msgprint(_("Fee Records Created - {0}").format(comma_and(fee_list)))

	def get_courses(self):
		return frappe.db.sql('''select course, course_name from `tabProgram Course` where parent = %s and required = 1''', (self.program), as_dict=1)


@frappe.whitelist()
def get_program_courses(doctype, txt, searchfield, start, page_len, filters):
	if filters.get('program'):
		return frappe.db.sql("""select course, course_name from `tabProgram Course`
			where  parent = %(program)s and course like %(txt)s {match_cond}
			order by
				if(locate(%(_txt)s, course), locate(%(_txt)s, course), 99999),
				idx desc,
				`tabProgram Course`.course asc
			limit {start}, {page_len}""".format(
				match_cond=get_match_cond(doctype),
				start=start,
				page_len=page_len), {
					"txt": "%{0}%".format(txt),
					"_txt": txt.replace('%', ''),
					"program": filters['program']
				})

@frappe.whitelist()
def get_students(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("academic_term"):
		filters["academic_term"] = frappe.defaults.get_defaults().academic_term

	if not filters.get("academic_year"):
		filters["academic_year"] = frappe.defaults.get_defaults().academic_year

	enrolled_students = frappe.get_list("Program Enrollment", filters={
		"academic_term": filters.get('academic_term'),
		"academic_year": filters.get('academic_year')
	}, fields=["student"])

	students = [d.student for d in enrolled_students] if enrolled_students else [""]

	return frappe.db.sql("""select
			name, title from tabStudent
		where 
			name not in (%s)
		and 
			`%s` LIKE %s
		order by 
			idx desc, name
		limit %s, %s"""%(
			", ".join(['%s']*len(students)), searchfield, "%s", "%s", "%s"),
			tuple(students + ["%%%s%%" % txt, start, page_len]
		)
	)

@frappe.whitelist()
def make_inv(customer, customer_name, due_date, courses, fees):
	from frappe import utils
        import json
	count = 0        
	#courses and fees are lists that have the docnames from the front end
	courses = json.loads(courses)
	fees = json.loads(fees)
        udoc = frappe.new_doc("Sales Invoice")
        udoc.naming_series = "ACC-SINV-.YYYY.-"
        udoc.customer = customer
        udoc.customer_name = customer_name
	#Fees
	if(fees):
		for d in fees:
			#fetch fee_structure, it has the amount for the sales invoice, as well as..
			fee_structure = frappe.get_doc("Fee Structure", d)
			for e in fee_structure.components:
				fee_amount = e.amount
				#The fee category. This is have a new field for 
				#"Items" doctype, which will make sure each
				#course correlates to a proper item for identification
				fetched_item = frappe.get_doc("Fee Category", e.fees_category)
				if(fetched_item.item):
					udoc.append('items', {
					'item_code': fetched_item.item,
					'qty': '1',
					'rate': fee_amount,
					'amount': fee_amount,
					})
				count = count + 1
				#Only for checking if the sales invoice will turn out empty
				#In case none of the fee category or the Course doctypes
				#Have any items listed
	#For course
	if(courses):
		for i in range(len(courses)):	
			fdata = frappe.get_doc('Course', courses[i])		
			if(fdata.item):
				count= count + 1			
				udoc.append('items', {
				'item_code': fdata.item,
				'qty': '1',
				})
	udoc.posting_date = frappe.utils.nowdate()
	#Due date  = enrollment date	
	udoc.due_date = due_date
	#saves only if there is at least one potential tx
	if( count>0 ):	
		udoc.save()
		return frappe.get_last_doc("Sales Invoice");	
	else:
		msgprint(_("Invoice couldn't be generated : None of your courses or fee structures have an item group assigned."))
		return			

