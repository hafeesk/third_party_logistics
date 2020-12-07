frappe.get_first_of_month = function (add_months, date) {
  return moment(date || frappe.datetime.get_today())
    .add(add_months || 0, "months")
    .startOf("month")
    .format();
};

frappe.get_last_of_month = function (add_months) {
  return moment()
    .add(add_months || 0, "months")
    .endOf("month")
    .format();
};

frappe.add_billing_details_link = function (report) {
  report.page.clear_icons();
  report.page.add_action_icon("fa fa-print", function () {
    if (!report.get_filter_value("customer")) {
      frappe.throw("Please select Customer for report.");
      return;
    }
    let filters = report.get_filter_values();
    filters.report_name = report.report_name;
    let url =
      "/api/method/third_party_logistics.third_party_logistics.billing.billing_controller.get_billing_details";
    const args = {
      filters: filters,
    };
    open_url_post(url, args);
  });
};
