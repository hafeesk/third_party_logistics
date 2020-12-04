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
        dict(label=_("Outbound Stock Entry#"), fieldname="name", fieldtype="Link/Stock Entry", width=160),
        dict(label=_("Customer"), fieldname="customer_cf", width=200),
        dict(label=_("Date"), fieldname="posting_date", width=120),
        dict(label=_("No of Pallets (A)"), fieldname="pallet_outbound_qty_cf", fieldtype='Float', width=100),
        dict(label=_("Qty on Pallet"), fieldname="each_pallet_qty_cf", fieldtype='Data', width=220),
        dict(label=_("Tracking Number"), fieldname="tracking_number_cf", width=120),
        dict(label=_("Total Outbound Pallet Loading Charge(A * Charge) + Outbound Freight * Markup Percent"),
        fieldname="total_outbound_freight_charge", fieldtype='Currency', width=120),
        dict(label=_("Invoiced"), fieldname="invoiced_cf", fieldtype="Check", width=80),
    ]

def get_data(filters):
    where_clause = get_conditions(filters)

    data = frappe.db.sql("""
    select 
        ste.name, ste.customer_cf, ste.company, ste.posting_date,
        ste.tracking_number_cf, 
        ste.each_pallet_qty_cf,
        round(ste.pallet_outbound_qty_cf,2) pallet_outbound_qty_cf,
        0 pallet_loading_charge,
        0 total_pallet_loading_charge,
        outbound_freight_charge_cf,
        cu.outbound_freight_markup_margin_cf,
        (outbound_freight_charge_cf * (1+(.01*cu.outbound_freight_markup_margin_cf))) total_outbound_freight_charge
    from 
        `tabStock Entry` ste
        inner join tabCustomer cu on cu.name = ste.customer_cf
    where 
        ste.stock_entry_type = 'Material Issue'
        and ste.docstatus = 1
        and ste.posting_date between %(from_date)s and %(to_date)s
        {where_clause}
    order by customer_cf, posting_date""".format(where_clause=where_clause), filters, as_dict=True)

    customer_item_rates = dict()
    loading_pallet_item = frappe.db.get_value("Third Party Logistics Settings", None, "loading_pallet_item")

    for d in data:
        d.pallet_loading_charge = get_item_rate(d.customer_cf, loading_pallet_item, customer_item_rates)
        d.total_outbound_freight_charge += d.pallet_loading_charge * d.pallet_outbound_qty_cf

    total = sum([d.total_outbound_freight_charge for d in data])
    data.extend([{"total_outbound_freight_charge": total}])

    return data


def get_conditions(filters):
    where_clause = []
    if filters.get("customer"):
        where_clause = where_clause + ["ste.customer_cf = %(customer)s"]

    return where_clause and " and " + " and ".join(where_clause) or ""
