frappe.ui.form.on("Stock Entry", {
  refresh: function (frm) {
    frappe.db
      .get_single_value(
        "Third Party Logistics Settings",
        "container_item_group"
      )
      .then((item_group) => {
        console.log(item_group);
        frm.set_query("container_type_cf", function () {
          return {
            filters: [["Item", "item_group", "=", item_group]],
          };
        });
      });
  },
});
