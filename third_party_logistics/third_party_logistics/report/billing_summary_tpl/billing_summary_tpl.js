// Copyright (c) 2016, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Billing Summary TPL"] = {
  filters: [
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
      reqd: 1,
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
      let url =
        "/api/method/third_party_logistics.third_party_logistics.billing.billing_controller.print_billing_summary";
      const args = {
        filters: report.get_filter_values(),
      };
      open_url_post(url, args);
    });
  },
};
