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
