// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Note CT", {
  refresh: function (frm) {
    frappe.db
      .get_single_value(
        "Third Party Logistics Settings",
        "misc_services_item_group"
      )
      .then((item_group) => {
        frm.set_query("item", "items", function () {
          return {
            filters: [["Item", "item_group", "=", item_group]],
          };
        });
      });
  },
});
