// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Enrollment", {
	setup: function(frm) {
		frm.add_fetch('fee_structure', 'total_amount', 'amount');
	},

	onload: function(frm, cdt, cdn){
		frm.set_query("academic_term", "fees", function(){
			return{
				"filters":{
					"academic_year": (frm.doc.academic_year)
				}
			};
		});

		frm.fields_dict['fees'].grid.get_field('fee_structure').get_query = function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {'academic_term': d.academic_term}
			}
		};

		if (frm.doc.program) {
			frm.set_query("course", "courses", function(doc, cdt, cdn) {
				return{
					query: "erpnext.education.doctype.program_enrollment.program_enrollment.get_program_courses",
					filters: {
						'program': frm.doc.program
					}
				}
			});
		}

		frm.set_query("student", function() {
			return{
				query: "erpnext.education.doctype.program_enrollment.program_enrollment.get_students",
				filters: {
					'academic_year': frm.doc.academic_year,
					'academic_term': frm.doc.academic_term
				}
			}
		});
	},

	program: function(frm) {
		frm.events.get_courses(frm);
		if (frm.doc.program) {
			frappe.call({
				method: "erpnext.education.api.get_fee_schedule",
				args: {
					"program": frm.doc.program,
					"student_category": frm.doc.student_category
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("fees" ,r.message);
						frm.events.get_courses(frm);
					}
				}
			});
		}
	},


	student_category: function() {
		frappe.ui.form.trigger("Program Enrollment", "program");
	},

	get_courses: function(frm) {
		frm.set_value("courses",[]);
		frappe.call({
			method: "get_courses",
			doc:frm.doc,
			callback: function(r) {
				if(r.message) {
					frm.set_value("courses", r.message);
				}
			}
		})
	}

});



frappe.ui.form.on("Program Enrollment", {
	sinvoice: function(frm)
	{
		if( cur_frm.doc.sinvoice == 0)
		{
		cur_frm.set_value("invoice" , undefined);
		cur_frm.set_value("_party" , undefined);
		cur_frm.set_df_property("invoice", "hidden", 1);
		cur_frm.set_df_property("invoice", "reqd", 0);
		cur_frm.set_df_property("_party", "hidden", 1);
		cur_frm.set_df_property("_party", "reqd", 0);
		cur_frm.set_df_property("generate", "hidden", 1);
		}

		else{
		cur_frm.set_df_property("invoice", "hidden", 0);
		cur_frm.set_df_property("invoice", "reqd", 1);
		cur_frm.set_df_property("_party", "hidden", 0);
		cur_frm.set_df_property("_party", "reqd", 1);
		}
	}

});


frappe.ui.form.on("Program Enrollment", {
  	invoice: function(frm) {	
	if(cur_frm.doc.invoice != undefined){	
		cur_frm.set_df_property("generate", "hidden", 1);
		}

	else cur_frm.set_df_property("generate", "hidden", 0);
	}
});


frappe.ui.form.on("Program Enrollment", {
  	_party: function(frm) {	
		cur_frm.set_value("invoice" , undefined);
		cur_frm.set_df_property("generate", "hidden", 0);
		}
});


frappe.ui.form.on("Program Enrollment", {
  	
  	generate: function(frm) {

  		if(cur_frm.doc.sinvoice == 0) return;
  		if(cur_frm.doc.courses == undefined || cur_frm.doc.student == undefined || cur_frm.doc._party == undefined)
  			{
  				frappe.msgprint("Form incomplete. Kindly fill the mandatory fields and try again."); return;
  			}
  		var crs = [], fee = [], i = 0;
		cur_frm.doc.courses.forEach(function(rows){ crs[i] = rows.course; i++; });
		i = 0;cur_frm.doc.fees.forEach(function(rows){ fee[i] = rows.fee_structure; i++; });
  		frappe.call({
            method: "erpnext.education.doctype.program_enrollment.program_enrollment.make_inv",
            args:{
                    'customer': frm.doc._party,
                    'customer_name': frm.doc.student_name,
                    'due_date': cur_frm.doc.enrollment_date,
                    'courses': crs,
                    'fees':fee,
                   },
            async: false,
            callback: function(r)
            {
            	cur_frm.set_value("invoice",r.message.name);
            	cur_frm.set_df_property("generate", "hidden", 1); 
            }
        });
	}
});