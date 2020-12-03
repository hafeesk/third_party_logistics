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
      default: frappe.get_first_of_month(-2),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("Date"),
      fieldtype: "Date",
      default: frappe.get_last_of_month(-2),
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
    report.page.add_action_icon("fa fa-print", function () {
      if (!report.get_filter_value("customer")) {
        frappe.throw("Please select Customer for report.");
        return;
      }
      let url =
        "/api/method/third_party_logistics.third_party_logistics.billing.billing_controller.get_billing_details";
      const args = {
        filters: report.get_filter_values(),
      };
      open_url_post(url, args);
    });
  },
};
