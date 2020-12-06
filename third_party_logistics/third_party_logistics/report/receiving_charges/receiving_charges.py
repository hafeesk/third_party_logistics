# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days
from third_party_logistics.third_party_logistics.billing.utils import get_item_rate


def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        dict(label=_("Stock Entry#"), fieldname="name", fieldtype="Link/Stock Entry", width=160),
        dict(label=_("Customer"), fieldname="customer_cf", width=200),
        dict(label=_("Date"), fieldname="posting_date", width=120),
        dict(label=_("Received as Pallet/LC"), fieldname="received_as_cf", width=140),
        dict(label=_("No of Pallet/LC"), fieldname="pallet_lc_qty", width=120),
        dict(label=_("Rate per Pallet/LC"), fieldname="rate_per_pallet_lc", fieldtype='Currency', width=120),
        dict(label=_("Amount for Pallet/LC"), fieldname="amount_for_pallet_lc", fieldtype='Currency', width=120),
        dict(label=_("Container Type"), fieldname="container_type_cf", width=140),
        dict(label=_("Container Rate"), fieldname="container_rate", fieldtype="Currency", width=140),
        dict(label=_("Receiving Charge for Billing"), fieldname="total_receiving_charge", fieldtype="Currency", width=120),
        dict(label=_("Invoiced"), fieldname="invoiced_cf", fieldtype="Check", width=80),
    ]

def get_data(filters):
    where_clause = get_conditions(filters)

    from third_party_logistics.third_party_logistics.billing.billing_controller import get_carton_container_receiving_charge
    receiving_carton_item = frappe.db.get_value("Third Party Logistics Settings", None, "receiving_carton_item")
    receiving_pallet_item = frappe.db.get_value("Third Party Logistics Settings", None, "receiving_pallet_item")

    data = frappe.db.sql("""
    select
        name, customer_cf, posting_date,  received_as_cf,
        pallet_qty_cf, loose_cartons_qty_cf, container_type_cf,
        coalesce(nullif(pallet_qty_cf,0),loose_cartons_qty_cf) pallet_lc_qty,
        0 total_receiving_charge, invoiced_cf
    from
        `tabStock Entry` ste
    where
        ste.docstatus = 1
        and ste.stock_entry_type = 'Material Receipt'
        and ste.posting_date between %(from_date)s and %(to_date)s
        and ste.customer_cf is not null
        and (pallet_qty_cf+loose_cartons_qty_cf) > 0
        {where_clause}
        order by ste.customer_cf, ste.posting_date, posting_time
    """.format(where_clause=where_clause), filters, as_dict=True)

    if not data:
        return []

    customer_item_rates = dict()

    for d in data:
        if d.received_as_cf == "Loose Cartons":
            d["container_rate"] = get_item_rate(d.customer_cf, d.container_type_cf, customer_item_rates)
            d["rate_per_pallet_lc"] = get_item_rate(d.customer_cf, receiving_carton_item, customer_item_rates)
            d["amount_for_pallet_lc"] = d.loose_cartons_qty_cf * d["rate_per_pallet_lc"]
            d.total_receiving_charge = max(d.amount_for_pallet_lc, d.container_rate)
        else:
            d["rate_per_pallet_lc"] = get_item_rate(d.customer_cf, receiving_pallet_item, customer_item_rates)
            d["amount_for_pallet_lc"] = d.pallet_qty_cf * d["rate_per_pallet_lc"]
            d.total_receiving_charge = d["amount_for_pallet_lc"]
    return data

def get_conditions(filters):
    where_clause = []
    if filters.get("customer"):
        where_clause = where_clause + ["ste.customer_cf = %(customer)s"]

    return where_clause and " and " + " and ".join(where_clause) or ""
