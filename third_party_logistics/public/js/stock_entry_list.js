frappe.listview_settings["Stock Entry"] = {
  onload: function (me) {
    me.page.add_inner_button("Run Receiving Charges", () => {
      frappe
        .call({
          method:
            "third_party_logistics.third_party_logistics.billing.billing_controller.test_make_receiving_charges",
        })
        .then(() => {
          frappe.show_alert({ message: "Receiving charges created" });
        });
    });

    me.page.add_inner_button("Uninvoice Material Receipt", () => {
      frappe
        .call({
          method:
            "third_party_logistics.third_party_logistics.billing.billing_controller.uninvoice_material_receipt",
        })
        .then(() => {
          frappe.show_alert({ message: "Material Receipt uninvoiced" });
        });
    });
  },
};
