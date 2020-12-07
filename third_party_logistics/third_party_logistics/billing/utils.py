# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, get_first_day, get_last_day, add_days
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from collections import defaultdict
import json
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from erpnext import get_default_company
from erpnext.accounts.party import get_party_details
from erpnext.stock.get_item_details import get_price_list_rate_for

def get_item_rate(customer, item_code, out):
    if out.get((customer, item_code)):
        return out.get((customer, item_code))
    default_price_list = frappe.db.sql("""
        select cu.name,
        COALESCE(cu.default_price_list,cug.default_price_list,sing.value) price_list
        from tabCustomer cu
        inner join `tabCustomer Group` cug on cug.name = cu.customer_group
        cross join tabSingles sing on sing.field = 'selling_price_list'
        and sing.doctype = 'Selling Settings'
        where cu.name=%s""", (customer,), as_dict=True)

    customer_details = get_party_details(party=customer, party_type="Customer")
    customer_details.update({
        "company": get_default_company(),
        "price_list": [d["price_list"] for d in default_price_list if d.name == customer][0],
        "transaction_date": getdate()
    })
    rate = get_price_list_rate_for(customer_details, item_code) or 0.0
    out.setdefault((customer, item_code), rate)
    return rate

def get_customers_for_billing_cycle(cycle):
        return [d[0] for d in frappe.db.get_all("Customer", filters={"storage_billing_model_cf": cycle}, as_list=1)]


def get_carton_container_receiving_charge(customer, company, receiving_carton_item):
    items = [receiving_carton_item] + [d[0] for d in frappe.db.get_list("Item", {"item_group": "Container"}, as_list=1)]
    out = defaultdict(float)
    for d in items:
        out[d] = get_item_rate(customer, d, {})
    return out

@frappe.whitelist()
def uninvoice(from_date, to_date):
    '''
    Set invoiced_cf to 0, for use in testing
    to recreate billing
    '''
    filters = dict(from_date=from_date, to_date=to_date)
    frappe.db.sql("""
    update
        `tabStock Entry` set invoiced_cf = 0
    where
        stock_entry_type = 'Material Receipt'
        and invoiced_cf = 1
        and posting_date between %(from_date)s and %(to_date)s
        and customer_cf is not null
    """, filters)

    frappe.db.sql("""
    update
        `tabSales Order` set invoiced_cf = 0
    where
        docstatus = 1
        and invoiced_cf = 1
        and transaction_date between %(from_date)s and %(to_date)s
    """, filters)
    frappe.db.commit()


def update_invoiced_cf(doc, method):
    frappe.db.sql("""
    update
        `tabStock Entry` set invoiced_cf = 1
    where
        stock_entry_type = 'Material Receipt'
        and invoiced_cf = 0
        and posting_date between %(from_date)s and %(to_date)s
        and customer_cf is not null
    """, dict(from_date=doc.billing_from_date_cf, to_date=doc.billing_to_date_cf), )

    frappe.db.sql("""
    update
        `tabSales Order` set invoiced_cf = 1
    where
        docstatus = 1
        and invoiced_cf = 0
        and transaction_date between %(from_date)s and %(to_date)s
    """, dict(from_date=doc.billing_from_date_cf, to_date=doc.billing_to_date_cf), )
