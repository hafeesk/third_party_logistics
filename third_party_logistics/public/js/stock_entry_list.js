frappe.listview_settings["Stock Entry"] = {
  onload: function (me) {
    me.page.add_inner_button("Run Billing", () => {
      frappe
        .call({
          method:
            "third_party_logistics.third_party_logistics.billing.billing_controller.make_billing",
        })
        .then(() => {
          frappe.show_alert({ message: "Billing done" });
        });
    });

    me.page.add_inner_button("Uninvoice", () => {
      frappe
        .call({
          method:
            "third_party_logistics.third_party_logistics.billing.billing_controller.uninvoice_last_month",
        })
        .then(() => {
          frappe.show_alert({ message: "Uninvoice complete" });
        });
    });
  },
};
