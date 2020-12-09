frappe.ui.form.on("Stock Entry", {
  stock_entry_type: function (frm) {
    frm.toggle_reqd(
      "customer_cf",
      ["Material Receipt", "Material Issue"].includes(frm.doc.stock_entry_type)
    );
    frm.toggle_reqd(
      "received_as_cf",
      ["Material Receipt"].includes(frm.doc.stock_entry_type)
    );
    frm.toggle_reqd(
      "pallet_outbound_qty_cf",
      ["Material Issue"].includes(frm.doc.stock_entry_type)
    );
  },

  received_as_cf: function (frm) {
    frm.toggle_reqd("pallet_qty_cf", frm.doc.received_as_cf == "Pallet");
    frm.toggle_reqd(
      "loose_cartons_qty_cf",
      frm.doc.received_as_cf == "Loose Cartons"
    );
    frm.toggle_reqd(
      "container_type_cf",
      frm.doc.received_as_cf == "Loose Cartons"
    );
  },

  refresh: function (frm) {
    frappe.db
      .get_single_value(
        "Third Party Logistics Settings",
        "container_item_group"
      )
      .then((item_group) => {
        frm.set_query("container_type_cf", function () {
          return {
            filters: [["Item", "item_group", "=", item_group]],
          };
        });
      });
  },

  validate: function (frm) {
    let messages = [];
    if (frm.doc.stock_entry_type == "Material Issue") {
      if (!frm.doc.customer_cf) {
        messages.push("Please select a 'For Customer' ");
      }
      if (!frm.doc.pallet_outbound_qty_cf) {
        messages.push("Please set the Outbound Pallet Qty");
      }
    }

    if (frm.doc.stock_entry_type == "Material Receipt") {
      if (!frm.doc.customer_cf) {
        messages.push("Please select a 'For Customer' ");
      }
      if (frm.doc.received_as_cf == "Pallet") {
        if (!frm.doc.pallet_qty_cf) {
          messages.push("Please set the Pallet Qty");
        } else if (frm.doc.received_as_cf == "Loose Cartons") {
          if (!frm.doc.loose_cartons_qty_cf) {
            messages.push("Please set the Loose Cartons Qty");
          }
          if (!frm.doc.container_type_cf) {
            messages.push("Please select a Container Type");
          }
        }
      }
    }

    if (messages.length) {
      frappe.msgprint(__(messages.join("\n")));
      frappe.validated = 0;
    }
  },
});
