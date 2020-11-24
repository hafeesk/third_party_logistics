# -*- coding: utf-8 -*-
# Copyright (c) 2020, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, get_first_day, get_last_day, add_days
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions

def make_receiving_charges():
    """
    Creates one `Sales Invoice` per customer for receiving charges for all Material Receipt in the previous month.
    Scheduled to run on 1st of month 00:15
    """
    to_date = add_days(get_first_day(getdate()), -1)
    from_date = get_first_day(to_date)
    filters = dict(from_date=from_date, to_date=to_date)

    def _create_invoice(items):
        invoice = frappe.new_doc('Sales Invoice')
        invoice.set_posting_time = 1
        invoice.posting_date = getdate()
        invoice.customer = items[0]["customer_cf"]
        invoice.company = items[0]["company"]
        invoice.due_date = add_days(getdate(), 30)
        receiving_carton_item = frappe.db.get_value("Third Party Logistics Settings", None, "receiving_carton_item")
        receiving_pallet_item = frappe.db.get_value("Third Party Logistics Settings", None, "receiving_pallet_item")

        for args in items:
            args = frappe._dict(args)
            if args.received_as_cf == "Loose Cartons":
                item = invoice.append("items")
                item.item_code = receiving_carton_item
                item.qty = args.loose_cartons_qty_cf
                item.description = "Carton receiving charges. %s" % args.name

                item = invoice.append("items")
                item.item_code = args.container_type_cf
                item.qty = 1
                item.description = "Container type %s minimum receiving charge. %s" % (args.container_type_cf, args.name)
            elif args.received_as_cf == "Pallet":
                item = invoice.append("items")
                item.item_code = receiving_pallet_item
                item.qty = args.pallet_qty_cf
                item.description = "Pallet receiving charge. %s" % (args.name)

        # Add dimensions in invoice:
        accounting_dimensions = get_accounting_dimensions()
        for dimension in accounting_dimensions:
            if args.get(dimension):
                invoice.update({
                    dimension: args.get(dimension)
                })

        invoice.set_missing_values(for_validate=True)
        invoice.save(ignore_permissions=True)

        # remove carton charge lines if amount less then container type minimum
        lines_to_remove = []
        for idx, d in enumerate(invoice.items):
            if d.item_code == receiving_carton_item:
                if d.amount < invoice.items[idx + 1].amount:
                    lines_to_remove.append(d.name)
                else:
                    lines_to_remove.append(invoice.items[idx + 1].name)
        invoice.items = [d for d in invoice.items if not d.name in lines_to_remove]

        invoice.save(ignore_permissions=True)
        invoice.submit()

    invoices = {}
    for d in frappe.db.sql("""
    select 
        name, company, customer, invoiced_cf, received_as_cf, container_type_cf, 
        pallet_qty_cf, loose_cartons_qty_cf, customer_cf, freight_charges_cf, 
        tracking_number_cf, pallet_outbound_qty_cf, each_pallet_qty_cf, outbound_freight_charge_cf
    from 
        `tabStock Entry` ste
    where 
        stock_entry_type = 'Material Receipt'
        and invoiced_cf = 0
        and ste.posting_date between %(from_date)s and %(to_date)s
    """, filters, as_dict=True):
        invoice = invoices.setdefault((d["customer"], d["company"]), [])
        invoice.append(d)
        frappe.db.set_value("Stock Entry", d.name, "invoiced_cf", 1)

    for _, items in invoices.items():
        _create_invoice(items)

    frappe.db.commit()


@frappe.whitelist()
def test_make_receiving_charges():
    make_receiving_charges()


@frappe.whitelist()
def uninvoice_material_receipt():
    to_date = add_days(get_first_day(getdate()), -1)
    from_date = get_first_day(to_date)
    frappe.db.sql("""
    update `tabStock Entry` set invoiced_cf = 0
    where stock_entry_type = 'Material Receipt'
    and invoiced_cf = 1
    and posting_date between %s and %s
    """, (from_date, to_date))
    frappe.db.commit()
