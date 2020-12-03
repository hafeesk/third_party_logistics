# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days
from third_party_logistics.third_party_logistics.billing.billing_controller import get_item_rate

def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        dict(label=_("Customer"), fieldname="customer", width=200),
        dict(label=_("No Of Orders"), fieldname="no_of_orders", fieldtype="Int", width=160),
        dict(label=_("Total Item Qty in Order"), fieldname="qty", fieldtype="Int", width=160),
    ]

def get_data(filters):
    where_clause = get_conditions(filters)
    data = frappe.db.sql("""
        select so.customer, count(distinct so.name) no_of_orders, sum(soi.qty) qty
    from
        `tabSales Order` so
        inner join `tabSales Order Item` soi on soi.parent = so.name
    where
        so.docstatus = 1
        and so.transaction_date between %(from_date)s and %(to_date)s
        {where_clause} group by so.customer
        order by so.customer""".format(where_clause=where_clause), filters, debug=True)

    return data

def get_conditions(filters):
    where_clause = []
    if filters.get("customer"):
        where_clause = where_clause + ["so.customer = %(customer)s"]

    return where_clause and " and " + " and ".join(where_clause) or ""
