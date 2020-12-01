// Copyright (c) 2020, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Third Party Logistics Settings", {
  // refresh: function(frm) { }

  prepare_invoice: function (frm) {
    frappe
      .call({
        method:
          "third_party_logistics.third_party_logistics.billing.billing_controller.make_billing",
        args: { from_date: frm.doc.from_date, to_date: frm.doc.to_date },
      })
      .then(() => {
        frappe.show_alert({ message: "Billing done" });
      });
  },

  un_invoice: function (frm) {
    frappe
      .call({
        method:
          "third_party_logistics.third_party_logistics.billing.billing_controller.uninvoice",
        args: { from_date: frm.doc.from_date, to_date: frm.doc.to_date },
      })
      .then(() => {
        frappe.show_alert({ message: "Uninvoice complete" });
      });
  },
});
