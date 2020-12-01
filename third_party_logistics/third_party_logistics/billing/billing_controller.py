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


def get_filters():
    to_date = add_days(get_first_day(getdate()), -1)
    from_date = get_first_day(to_date)
    return dict(from_date=from_date, to_date=to_date)

def make_storage_charges():
    """
    Calculate Storage Charges based on Storage Model : Daily / Monthly for that customer
    """
    frappe.db.commit()

def make_lt_storage_charges():
    """
    Calculate Long Term Storage Fees , if found
    """
    frappe.db.commit()


def make_receiving_charges(from_date=None, to_date=None):
    """
    Creates one `Sales Invoice` per customer for receiving charges for all Material Receipt in the previous month.
    Scheduled to run on 1st of month 00:15
    """
    filters = get_filters()
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date

    def get_invoice_items(customer, company, items):
        carton_container_charges = get_carton_container_receiving_charge(customer, company, receiving_carton_item)
        out = defaultdict(float)
        for args in items:
            args = frappe._dict(args)
            if args.received_as_cf == "Loose Cartons":
                if carton_container_charges.get(args.container_type_cf, 0) > (carton_container_charges.get(receiving_carton_item, 0) * args.loose_cartons_qty_cf):
                    out[args.container_type_cf] += 1
                else:
                    out[receiving_carton_item] += args.loose_cartons_qty_cf
            elif args.received_as_cf == "Pallet":
                out[receiving_pallet_item] += args.pallet_qty_cf

        return out

    receiving_carton_item = frappe.db.get_value("Third Party Logistics Settings", None, "receiving_carton_item")
    receiving_pallet_item = frappe.db.get_value("Third Party Logistics Settings", None, "receiving_pallet_item")

    invoices = defaultdict(list)
    for d in frappe.db.sql("""
    select
        company, customer_cf customer, received_as_cf, container_type_cf,
        pallet_qty_cf, loose_cartons_qty_cf
    from
        `tabStock Entry` ste
    where
        stock_entry_type = 'Material Receipt'
        and invoiced_cf = 0
        and ste.posting_date between %(from_date)s and %(to_date)s
        and customer_cf is not null
    """, filters, as_dict=True, debug=False):
        invoices[(d["customer"], d["company"])].append(d)

    out = {}
    for key, items in invoices.items():
        out[key] = get_invoice_items(key[0], key[1], items)
    return out


def make_order_fulfillment_charges(from_date=None, to_date=None):
    """
    Calculate Per Order Charges based on No Of Orders (SO) and Item Qty
    Calculate Pick and Pack Charges based on No Of Items ( Total Item Qty in each Order)
    """
    filters = get_filters()
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date

    fulfilment_charge_per_order = frappe.db.get_value("Third Party Logistics Settings", None, "fulfilment_charge_per_order_cf")
    fulfilment_charge_per_order_item_cf = frappe.db.get_value("Third Party Logistics Settings", None, "fulfilment_charge_per_order_item_cf")

    invoices = defaultdict(list)

    per_order_order_item_charges = frappe.db.sql("""
    select
        so.customer, so.company,
        count(distinct so.name) so_count,
        sum(case when it.pick_and_pack_charge_cf is null then soi.qty else 0 end) so_item_qty
    from
        `tabSales Order` so
        inner join `tabSales Order Item` soi on soi.parent = so.name
        inner join tabItem it on it.name = soi.item_code
    where
        so.docstatus = 1
        and so.invoiced_cf = 0
        and so.transaction_date between %(from_date)s and %(to_date)s
    group by
        so.customer, so.company
    """, filters, as_dict=True)

    for d in per_order_order_item_charges:
        invoices[(d['customer'], d['company'])].extend([
            {"item": fulfilment_charge_per_order, "qty": d["so_count"]},
            {"item": fulfilment_charge_per_order_item_cf, "qty": d["so_item_qty"]},
        ])

    per_order_order_item_charges_item_specific = frappe.db.sql("""
    select
        so.customer, so.company,
        it.pick_and_pack_charge_cf item, sum(soi.qty) so_item_qty
    from
        `tabSales Order` so
        inner join `tabSales Order Item` soi on soi.parent = so.name
        inner join tabItem it on it.name = soi.item_code and it.pick_and_pack_charge_cf is not null
    where
        so.docstatus = 1
        and so.invoiced_cf = 0
        and so.transaction_date between %(from_date)s and %(to_date)s
    group by
        so.customer, so.company, it.pick_and_pack_charge_cf
    """, filters, as_dict=True)

    for d in per_order_order_item_charges_item_specific:
        invoices[(d["customer"], d["company"])].append({"item": d["item"], "qty": d["so_item_qty"]})

    out = defaultdict()
    for key, items in invoices.items():
        lines = defaultdict(float)
        for d in items:
            lines[d["item"]] += d["qty"]
        out[key] = lines
    return out

def make_freight_forward_charges_for_bulk_outward_shipment():
    """
        Calculate Freight Forward Charges for Bulk Outbound Shipment - Stock Entry (Material Issued)
    """
    frappe.db.commit()

def make_warehouse_service_charges_for_service_notes():
    """
    Other Miscellaneous Warehouse Services provided , to be picked from Service Notes
    """
    frappe.db.commit()

@frappe.whitelist()
def make_billing(from_date=None, to_date=None):
    def make_invoice(key):
        invoice = frappe.new_doc('Sales Invoice')
        invoice.set_posting_time = 1
        invoice.posting_date = getdate()
        invoice.customer = key[0]
        invoice.company = key[1]
        invoice.due_date = add_days(getdate(), 30)
        invoice.billing_from_date_cf = from_date
        invoice.billing_to_date_cf = to_date

        return invoice

    if not from_date or not to_date:
        filters = get_filters()
        from_date = filters.get("from_date")
        to_date = filters.get("to_date")

    invoices = defaultdict(list)
    # collect all charges
    receiving_charges = make_receiving_charges(from_date=from_date, to_date=to_date)
    order_fulfillment_charges = make_order_fulfillment_charges(from_date=from_date, to_date=to_date)

    for charges in [receiving_charges, order_fulfillment_charges]:
        for key, items_dd in charges.items():
            invoices[key].append(items_dd)

    for key, items in invoices.items():
        invoice = make_invoice(key)
        for dd in items:
            for item, qty in dd.items():
                if qty > 0:
                    invoice_item = invoice.append("items")
                    invoice_item.item_code = item
                    invoice_item.qty = qty
        invoice.set_missing_values(for_validate=True)
        invoice.save(ignore_permissions=True)
        filters = dict(from_date=from_date, to_date=to_date, customer=invoice.customer, company=invoice.company)
        fname, fcontent = get_billing_report(filters)
        save_file(fname, fcontent, "Sales Invoice", invoice.name, is_private=1)

    update_invoiced_cf()

    frappe.db.commit()

def update_invoiced_cf():
    filters = get_filters()
    frappe.db.sql("""
    update 
        `tabStock Entry` set invoiced_cf = 1
    where
        stock_entry_type = 'Material Receipt'
        and invoiced_cf = 0
        and posting_date between %(from_date)s and %(to_date)s
        and customer_cf is not null
    """, filters)

    frappe.db.sql("""
    update 
        `tabSales Order` set invoiced_cf = 1
    where
        docstatus = 1
        and invoiced_cf = 0
        and transaction_date between %(from_date)s and %(to_date)s
    """, filters)


def get_carton_container_receiving_charge(customer, company, receiving_carton_item):
    invoice = frappe.new_doc('Sales Invoice')
    invoice.posting_date = getdate()
    invoice.customer = customer
    invoice.company = company
    invoice.due_date = add_days(getdate(), 30)
    items = [d[0] for d in frappe.db.get_list("Item", {"item_group": "Container"}, as_list=1)]
    items.append(receiving_carton_item)
    for d in items:
        i = invoice.append("items")
        i.item_code = d
        i.qty = 1
    invoice.insert()
    rates = {a: b for a, b in [(d.item_code, d.rate) for d in invoice.items]}
    invoice.delete()
    return rates


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

def get_billing_report(filters):
    from third_party_logistics.third_party_logistics.report.billing_summary_tpl.billing_summary_tpl import get_data
    receiving_charges = get_data(filters)
    context = dict(filters=filters, receiving_charges=receiving_charges)

    template = "third_party_logistics/third_party_logistics/report/billing_summary_tpl/billing_summary_tpl.html"
    html = frappe.render_template(template, context)
    options = {
        "margin-left": "3mm",
        "margin-right": "3mm",
        "margin-top": "50mm",
        "margin-bottom": "40mm",
        "orientation": "Landscape"
    }
    fname = "{customer}_Billing_Summary_{from_date}_to_{to_date}.pdf".format(**filters)
    return fname, get_pdf(html, options=options)

@frappe.whitelist()
def print_billing_summary(filters):
    filters = json.loads(frappe.local.form_dict.filters)
    fname, content = get_billing_report(filters)
    frappe.local.response.filecontent = content
    frappe.local.response.type = 'download'
    frappe.local.response.filename = fname
