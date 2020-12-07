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
        dict(label=_("Customer"), fieldname="customer", fieldtype="Link", options="Customer", width=200),
        dict(label=_("Sales Order#"), fieldname="name", fieldtype="Link", options="Sales Order", width=160),
        dict(label=_("Date"), fieldname="transaction_date", width=120),
        dict(label=_("Per Order Charge (A)"), fieldname="per_order_charge", fieldtype='Currency', width=100),
        dict(label=_("Total Item Qty (B)"), fieldname="total_item_qty", fieldtype='Float', width=120),
        dict(label=_("Per Item Charge"), fieldname="per_item_charge", fieldtype='Currency', width=120),
        dict(label=_("Total Pick & Pack Charge [A+(B*C)]"), fieldname="total_pick_and_pack_charge", fieldtype='Currency', width=120),
        dict(label=_("Invoiced"), fieldname="invoiced_cf", fieldtype="Check", width=80),
    ]

def get_data(filters):
    where_clause = get_conditions(filters)
    data = frappe.db.sql("""
        select
        so.customer, so.company, so.name, so.transaction_date, sum(soi.qty) total_item_qty,
        null item
    from
        `tabSales Order` so
        inner join `tabSales Order Item` soi on soi.parent = so.name
        inner join tabItem it on it.name = soi.item_code
        and it.pick_and_pack_charge_cf is null
    where
        so.docstatus = 1
        and so.invoiced_cf = 0
        and so.transaction_date between %(from_date)s and %(to_date)s
        {where_clause}
    group by so.customer, so.company, so.name, so.transaction_date
union all
    select
        so.customer, so.company, so.name, so.transaction_date, sum(soi.qty) total_item_qty,
        pick_and_pack_charge_cf item
    from
        `tabSales Order` so
        inner join `tabSales Order Item` soi on soi.parent = so.name
        inner join tabItem it on it.name = soi.item_code
        and it.pick_and_pack_charge_cf is not null
    where
        so.docstatus = 1
        and so.invoiced_cf = 0
        and so.transaction_date between %(from_date)s and %(to_date)s
        {where_clause}
    group by so.customer, so.company, so.name, so.transaction_date, it.pick_and_pack_charge_cf
    order by customer, transaction_date""".format(where_clause=where_clause), filters, as_dict=True)

    fulfilment_charge_per_order = frappe.db.get_value("Third Party Logistics Settings", None, "fulfilment_charge_per_order_cf")
    fulfilment_charge_per_order_item = frappe.db.get_value("Third Party Logistics Settings", None, "fulfilment_charge_per_order_item_cf")

    customer_item_rates = dict()
    for d in data:
        if d.item:
            d["per_item_charge"] = get_item_rate(d.customer, d.item, customer_item_rates)
        else:
            d["per_order_charge"] = get_item_rate(d.customer, fulfilment_charge_per_order, customer_item_rates)
            d["per_item_charge"] = get_item_rate(d.customer, fulfilment_charge_per_order_item, customer_item_rates)

        d["total_pick_and_pack_charge"] = (d.per_order_charge or 0) + (d.per_item_charge * d.total_item_qty)

    return data


def get_conditions(filters):
    where_clause = []
    if filters.get("customer"):
        where_clause = where_clause + ["so.customer = %(customer)s"]

    return where_clause and " and " + " and ".join(where_clause) or ""
