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
import importlib
from third_party_logistics.third_party_logistics.billing.utils import get_customers_for_billing_cycle, get_carton_container_receiving_charge
from third_party_logistics.third_party_logistics.report.monthly_storage_fees_analytics.monthly_storage_fees_analytics import get_invoice_items as get_invoice_items_for_monthly_cycle, get_data as get_monthly_storage_fees
from third_party_logistics.third_party_logistics.report.daily_storage_fees_analytics.daily_storage_fees_analytics import get_invoice_items as get_invoice_items_for_daily_cycle, get_data as get_daily_storage_fees
from third_party_logistics.third_party_logistics.report.receiving_charges.receiving_charges import get_data as get_receiving_charges
from third_party_logistics.third_party_logistics.report.pick_and_pack_charges.pick_and_pack_charges import get_data as get_pick_and_pack_charges
from third_party_logistics.third_party_logistics.report.outbound_pallet_loading_charges.outbound_pallet_loading_charges import get_data as get_outbound_pallet_loading_charges
from third_party_logistics.third_party_logistics.report.miscellaneous_services_charges.miscellaneous_services_charges import get_data as get_miscellaneous_services_charges, get_invoice_items as get_invoice_items_for_misc_charges


@frappe.whitelist()
def make_billing(from_date=None, to_date=None):

    filters = get_filters(from_date, to_date)
    from_date = filters["from_date"]
    to_date = filters["to_date"]

    invoices = defaultdict(list)

    # collect all charges. comment item to exclude from billing
    billing_items = []
    billing_items.append(make_receiving_charges(from_date=from_date, to_date=to_date))
    billing_items.append(make_order_fulfillment_charges(from_date=from_date, to_date=to_date))
    billing_items.append(make_outbound_pallet_charges(from_date=from_date, to_date=to_date))
    billing_items.append(make_storage_charges_for_daily_billing(from_date=from_date, to_date=to_date))
    billing_items.append(make_storage_charges_for_monthly_billing(from_date=from_date, to_date=to_date))
    billing_items.append(make_miscellaneous_charges_for_service_notes(from_date=from_date, to_date=to_date))

    # combine charges from all activities to make consolidated invoice per customer
    for charges in billing_items:
        for customer_company, items in charges.items():
            invoices[customer_company].extend(items)

    for customer_company, items in invoices.items():
        invoice = get_invoice_doc(customer_company, from_date, to_date)
        for item_line in items:
            invoice_item = invoice.append("items")
            invoice_item.update(item_line)
        invoice.set_missing_values(for_validate=True)
        invoice.save(ignore_permissions=True)
        filters = dict(from_date=from_date, to_date=to_date, customer=invoice.customer, company=invoice.company)
        fname, fcontent = get_billing_details_pdf(filters)
        save_file(fname, fcontent, "Sales Invoice", invoice.name, is_private=1)

    frappe.db.commit()

def get_filters(from_date, to_date):
    out = dict()
    out["to_date"] = to_date or add_days(get_first_day(getdate()), -1)
    out["from_date"] = from_date or get_first_day(out["to_date"])
    return out

def get_invoice_doc(key, from_date, to_date):
    customer, company = key
    invoice = frappe.new_doc('Sales Invoice')
    invoice.set_posting_time = 1
    invoice.posting_date = getdate()
    invoice.customer = customer
    invoice.company = company
    invoice.due_date = add_days(getdate(), 30)
    invoice.billing_from_date_cf = from_date
    invoice.billing_to_date_cf = to_date
    return invoice

def make_storage_charges_for_monthly_billing(from_date=None, to_date=None):
    """
    Calculate Regular & LTS Storage Charges based on Monthly Billing Cycle customers
    """
    company = get_default_company()
    filters = get_filters(from_date, to_date)

    out = defaultdict(list)
    for customer in get_customers_for_billing_cycle("Monthly"):
        filters.update({"customer": customer, "company": company})
        line_items = get_invoice_items_for_monthly_cycle(filters)
        if line_items:
            out[(customer, company)] = line_items
    return out

def make_storage_charges_for_daily_billing(from_date=None, to_date=None):
    """
    Calculate Regular & LTS Storage Charges based on Monthly Billing Cycle customers
    """
    company = get_default_company()
    filters = get_filters(from_date, to_date)

    out = defaultdict(list)
    for customer in get_customers_for_billing_cycle("Daily"):
        filters.update({"customer": customer, "company": company})
        line_items = get_invoice_items_for_daily_cycle(filters)
        if line_items:
            out[(customer, company)] = line_items
    return out

def make_receiving_charges(from_date=None, to_date=None):
    """
    Creates one `Sales Invoice` per customer for receiving charges for all Material Receipt in the previous month.
    Scheduled to run on 1st of month 00:15
    """
    filters = get_filters(from_date, to_date)

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

        return [{"item_code": item_code, "qty": qty} for item_code, qty in out.items()]

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

def make_outbound_pallet_charges(from_date=None, to_date=None):
    """
    Total Outbound Charge =
    Outbound Freight  charges * Outbound Markup Percent (defined at customer level)  +
    Outbound Pallet Loading Charge * Pallet Qty
    """
    filters = get_filters(from_date, to_date)

    invoice_items = frappe.db.sql("""
    select ste.customer_cf, ste.company, sum(pallet_outbound_qty_cf) pallet_outbound_qty_cf,
    sum(outbound_freight_charge_cf * (1+(.01*cu.outbound_freight_markup_margin_cf))) outbound_freight_charge_cf
    from `tabStock Entry` ste
    inner join tabCustomer cu on cu.name = ste.customer_cf
    where ste.stock_entry_type = 'Material Issue'
    and ste.docstatus = 1 and ste.invoiced_cf = 0
    and ste.posting_date between %(from_date)s and %(to_date)s
    group by ste.customer_cf, ste.company """, filters, as_dict=True, debug=False)

    outbound_freight_charges = frappe.db.get_value("Third Party Logistics Settings", None, "outbound_freight_charges")
    loading_pallet_item = frappe.db.get_value("Third Party Logistics Settings", None, "loading_pallet_item")

    out = defaultdict()
    for d in invoice_items:
        items = out.setdefault((d.customer_cf, d.company), [])
        items.append({"item_code": loading_pallet_item, "qty": d.pallet_outbound_qty_cf})
        if d.outbound_freight_charge_cf:
            items.append({"item_code": outbound_freight_charges, "qty": 1,
            "rate": d.outbound_freight_charge_cf, "amount": d.outbound_freight_charge_cf})

    return out

def make_order_fulfillment_charges(from_date=None, to_date=None):
    """
    Calculate Per Order Charges based on No Of Orders (SO) and Item Qty
    Calculate Pick and Pack Charges based on No Of Items ( Total Item Qty in each Order)
    """
    filters = get_filters(from_date, to_date)

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
        out[key] = [{"item_code": item_code, "qty": qty} for item_code, qty in lines.items()]
    return out

def make_miscellaneous_charges_for_service_notes(from_date, to_date):
    """
    Other Miscellaneous Warehouse Services provided , to be picked from Service Notes
    """
    company = get_default_company()
    filters = get_filters(from_date, to_date)

    out = defaultdict(list)
    for customer in frappe.get_all("Customer"):
        filters.update({"customer": customer.name, "company": company})
        line_items = get_invoice_items_for_misc_charges(filters)
        if line_items:
            out[(customer.name, company)] = line_items
    return out

def get_billing_details_pdf(filters):
    context = dict(filters=filters, base_url=frappe.utils.get_site_url(frappe.local.site))

    context["receiving_charges"] = get_receiving_charges(filters)
    context["pick_and_pack_charges"] = get_pick_and_pack_charges(filters)
    context["outbound_pallet_loading_charges"] = get_outbound_pallet_loading_charges(filters)
    context["monthly_storage_fees"] = get_monthly_storage_fees(filters)
    context["daily_storage_fees"] = get_daily_storage_fees(filters)
    context["miscellaneous_service_charges"] = get_miscellaneous_services_charges(filters)

    template = "third_party_logistics/third_party_logistics/billing/billing_details.html"
    html = frappe.render_template(template, context)
    options = {
        "margin-left": "3mm",
        "margin-right": "3mm",
        "margin-top": "50mm",
        "margin-bottom": "40mm",
        "orientation": "Landscape"
    }
    fname = "{customer}_Billing_Detail_{from_date}_to_{to_date}.pdf".format(**filters)
    return fname, get_pdf(html, options=options)

@frappe.whitelist()
def get_billing_details(filters):
    filters = json.loads(frappe.local.form_dict.filters)
    fname, content = get_billing_details_pdf(filters)
    frappe.local.response.filecontent = content
    frappe.local.response.type = 'download'
    frappe.local.response.filename = fname
