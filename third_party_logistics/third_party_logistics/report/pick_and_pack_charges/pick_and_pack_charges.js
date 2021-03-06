// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Pick and Pack Charges"] = {
  filters: [
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
      // default: "EPIC",
      reqd: 0,
    },
    {
      fieldname: "from_date",
      label: __("Date"),
      fieldtype: "Date",
      default: frappe.get_first_of_month(-1),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("Date"),
      fieldtype: "Date",
      default: frappe.get_last_of_month(-1),
      reqd: 1,
    },
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_default("company"),
      reqd: 1,
      hidden: 1,
    },
  ],

  onload(report) {
    frappe.add_billing_details_link(report);
  },
};
