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


def on_validate_item(doc, method):
    if doc.is_customer_provided_item:
        if not doc.length_in_inch__cf \
            or not doc.width_in_inch_cf \
            or not doc.height_in_inch_cf:
            frappe.throw("Please set Length, Width, Breadth for Customer Provided Items.")
        doc.volume_in_cubic_feet_cf = doc.length_in_inch__cf * doc.width_in_inch_cf * doc.height_in_inch_cf / 1728


def make_accounting_period(start_date, end_date, company):
    """Creates an accounting period for the selected dates, so no backdated entries"""
    new_doc = frappe.new_doc("Accounting Period")
    new_doc.update({"start_date": start_date, "end_date": end_date, "company": company})
    new_doc.closed_documents = []
    for d in ["Sales Invoice", "Purchase Invoice", "Delivery Note", "Stock Entry"]:
        new_doc.append("closed_documents", {
            "document_type": d,
            "closed": 1
        })
    new_doc.insert(ignore_permissions=True)

def get_item_details():
    item_details = dict()
    for d in frappe.db.sql("""
    select 
        item_code, volume_in_cubic_feet_cf, monthly_storage_charge_cf,
        daily_storage_charge_cf, customer, is_customer_provided_item,
        length_in_inch__cf, width_in_inch_cf, height_in_inch_cf 
    from 
        tabItem""", as_dict=True):
        item_details.setdefault(d.item_code, d)
    return item_details

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

def get_default_price_list(customer, company):
    company = company or get_default_company()
    default_price_list = frappe.db.sql("""
    select 
        COALESCE(cu.default_price_list,cug.default_price_list,sing.value) price_list
    from 
        tabCustomer cu
        inner join `tabCustomer Group` cug on cug.name = cu.customer_group
        cross join tabSingles sing on sing.field = 'selling_price_list'
        and sing.doctype = 'Selling Settings'
    where
        cu.name=%s""", (customer,))
    return default_price_list and default_price_list[0][0] or None


def get_customers_for_billing_cycle(cycle):
        return [d[0] for d in frappe.db.get_all("Customer", filters={"storage_billing_model_cf": cycle}, as_list=1)]


def get_carton_container_receiving_charge(customer, company, receiving_carton_item):
    items = [receiving_carton_item] + [d[0] for d in frappe.db.get_list("Item", {"item_group": "Container"}, as_list=1)]
    out = defaultdict(float)
    for d in items:
        out[d] = get_item_rate(customer, d, {})
    return out

def update_invoiced_cf(doc, method):
    frappe.db.sql("""
    update
        `tabStock Entry` set invoiced_cf = 1
    where
        stock_entry_type in ('Material Receipt', 'Material Issue')
        and invoiced_cf = 0
        and posting_date between %(from_date)s and %(to_date)s
        and customer_cf = %(customer)s
    """, dict(from_date=doc.billing_from_date_cf, to_date=doc.billing_to_date_cf, customer=doc.customer), )

    frappe.db.sql("""
    update
        `tabService Note CT` set invoiced = 1
    where
        docstatus = 1
        and invoiced = 0
        and posting_date between %(from_date)s and %(to_date)s
        and customer = %(customer)s
    """, dict(from_date=doc.billing_from_date_cf, to_date=doc.billing_to_date_cf, customer=doc.customer), )

    frappe.db.sql("""
    update
        `tabSales Order` set invoiced_cf = 1
    where
        docstatus = 1
        and invoiced_cf = 0
        and transaction_date between %(from_date)s and %(to_date)s
        and customer = %(customer)s
    """, dict(from_date=doc.billing_from_date_cf, to_date=doc.billing_to_date_cf, customer=doc.customer), )


@frappe.whitelist()
def uninvoice(from_date, to_date, customer=None):
    '''
    Set invoiced_cf to 0, for use in testing
    to recreate billing
    '''
    filters = dict(from_date=from_date, to_date=to_date, customer=customer)
    where_clause = customer and " and customer_cf = %(customer)s" or ""

    frappe.db.sql("""
    update
        `tabStock Entry` set invoiced_cf = 0
    where
        stock_entry_type in ('Material Receipt', 'Material Issue')
        and invoiced_cf = 1
        and posting_date between %(from_date)s and %(to_date)s
        and customer_cf is not null
        {where_clause}
    """.format(where_clause=where_clause), filters)

    where_clause = customer and " and customer = %(customer)s" or ""
    frappe.db.sql("""
    update
        `tabSales Order` set invoiced_cf = 0
    where
        docstatus = 1
        and invoiced_cf = 1
        and transaction_date between %(from_date)s and %(to_date)s
        {where_clause}
    """.format(where_clause=where_clause), filters)

    frappe.db.sql("""
    update
        `tabService Note CT` set invoiced = 0
    where
        docstatus = 1
        and invoiced = 1
        and posting_date between %(from_date)s and %(to_date)s
        {where_clause}
    """.format(where_clause=where_clause), filters)

    frappe.db.commit()
