# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days
from third_party_logistics.third_party_logistics.billing.utils import get_item_rate
import pandas as pd
from operator import itemgetter

def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        dict(label="Service Note#", fieldname="name", fieldtype="Link", options="Service Note CT", width=160),
        dict(label="Customer#", fieldname="customer", fieldtype="Link", options="Customer", width=160),
        dict(label="Date ", fieldname="posting_date", fieldtype="Date", width=160),
        dict(label="Service", fieldname="item_code", fieldtype="Link", options="Item", width=160),
        dict(label="For Item", fieldname="for_item", fieldtype="Link", options="Item", width=160),
        dict(label="Qty", fieldname="qty", fieldtype="Int", width=160),
        dict(label="Rate", fieldname="rate", fieldtype="Currency", width=160),
        dict(label="Amount", fieldname="amount", fieldtype="Currency", width=160),
        dict(label="Invoiced", fieldname="invoiced", fieldtype="Check", width=160),
    ]

def get_data(filters):
    where_clause = get_conditions(filters)
    data = frappe.db.sql("""
    select 
        sn.name, sn.posting_date, sn.invoiced, sn.customer,
        sni.item item_code, sni.for_item, sni.qty
    from 
        `tabService Note CT` sn
        inner join `tabService Note Item CT` sni on sni.parent = sn.name
    where
        sn.docstatus = 1
        and sn.posting_date between %(from_date)s and %(to_date)s
        {where_clause}
    order by customer, item_code""".format(where_clause=where_clause), filters, as_dict=True)

    item_rates = dict()
    for d in data:
        d["rate"] = get_item_rate(d.customer, d.item_code, item_rates)
        d["amount"] = d["rate"] * d["qty"]
    return data

def get_conditions(filters):
    where_clause = []
    if filters.get("customer"):
        where_clause = where_clause + ["sn.customer = %(customer)s"]

    return where_clause and " and " + " and ".join(where_clause) or ""

def get_invoice_items(filters):
    invoice_items = get_data(filters)
    if not invoice_items:
        return []
    df = pd.DataFrame.from_records(invoice_items)
    df1 = df[['item_code', 'qty']]
    g = df1.groupby('item_code', as_index=False).agg('sum')
    data = g.to_dict('r')
    return sorted(data, key=itemgetter('item_code'))
