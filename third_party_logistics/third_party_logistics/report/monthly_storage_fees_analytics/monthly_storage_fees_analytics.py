# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days
from third_party_logistics.third_party_logistics.billing.utils import get_item_rate, get_item_details
from erpnext.stock.report.stock_balance.stock_balance import execute as get_stock_balance
from operator import itemgetter
from dateutil.relativedelta import relativedelta
import pandas as pd

def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data

def get_columns(filters):
    return [
            dict(label=_("Customer"), fieldname="customer", fieldtype="Link", options="Customer", width=120),
            dict(label=_("Item Group"), fieldname="item_group", fieldtype="Data", width=120),
            dict(label=_("Item"), fieldname="item_name", fieldtype="Link", options="Item", width=120),
            dict(label=_("Inventory as on end Date of Month"), fieldname="qty", fieldtype="Int", width=120),
            dict(label=_("Item Volume"), fieldname="item_volume", fieldtype="Float", width=120),
            dict(label=_("Charge per Cubic Feet"), fieldname="storage_charge_per_cubic_feet", fieldtype="Currency", width=120),
            dict(label=_("Regular Storage Charge"), fieldname="regular_storage_charge", fieldtype="Currency", width=120),
            dict(label=_("LTS Qty"), fieldname="lts_qty", fieldtype="Int", width=120),
            dict(label=_("LTS Rate"), fieldname="lts_storage_rate", fieldtype="Currency", width=120),
            dict(label=_("Long Term Storage Charge"), fieldname="lts_storage_charge", fieldtype="Currency", width=120),
            dict(label=_("Total Charge"), fieldname="total_storage_charge", fieldtype="Currency", width=120),
    ]

def get_data(filters):
    # set from_date to 1 year previous, to calculate LTSF
    filters["from_date"] = getdate(filters["to_date"]) + relativedelta(years=-1)
    storage_charge_items = get_storage_charge_items()
    item_details = get_item_details()
    item_rates = dict()
    customers = get_customers_for_billing_cycle("Monthly")

    _cols, stock_balance = get_stock_balance(filters)

    data = []
    for d in [frappe._dict(x) for x in stock_balance]:
        details = item_details.get(d.item_code)

        # skip non customer items
        customer = filters.get("customer")
        # apply customer filter if set
        if not details.is_customer_provided_item \
        or details.customer not in customers \
        or (customer and not customer == details.get("customer")):
            continue
        customer = details.get("customer")

        # Regular Storage Calculation
        storage_charge_per_cubic_feet = get_item_rate(customer, d.monthly_storage_charge_cf or storage_charge_items.default_monthly_storage_per_cubic_feet, item_rates)
        regular_storage_charge = storage_charge_per_cubic_feet * d.bal_qty * details.volume_in_cubic_feet_cf

        # LTSF Calculation
        lts_storage_rate, lts_storage_charge = 0, 0
        lts_qty = 0 if not d.bal_qty > d.in_qty else (d.bal_qty - d.in_qty)
        lts_storage_rate = get_item_rate(customer, storage_charge_items.default_long_term_storage_fees_for_monthly_cycle, item_rates)
        lts_storage_charge = lts_qty * details.volume_in_cubic_feet_cf * lts_storage_rate

        item = dict(
            customer=details.customer,
            item_group=d.item_group,
            item_name=d.item_name,
            qty=d.bal_qty,
            item_volume=details.volume_in_cubic_feet_cf,
            storage_charge_per_cubic_feet=storage_charge_per_cubic_feet,
            regular_storage_charge=regular_storage_charge,
            lts_qty=lts_qty,
            lts_storage_rate=lts_storage_rate,
            lts_storage_charge=lts_storage_charge,
            total_storage_charge=regular_storage_charge + lts_storage_charge,
            length=details.length_in_inch__cf,
            width=details.width_in_inch_cf,
            height=details.height_in_inch_cf,
            item_code=details.item_code,
        )
        data.append(item)

    data = sorted(data, key=itemgetter('customer', 'item_name'))
    return data

def get_storage_charge_items():
    tpls = frappe.get_single("Third Party Logistics Settings")
    out = dict()
    for d in [
        "default_daily_storage_per_cubic_feet_charge", "default_monthly_storage_per_cubic_feet", "default_long_term_fees_for_daily_cycle", "default_long_term_storage_fees_for_monthly_cycle"]:
        out[d] = tpls.get(d)
    return frappe._dict(out)

def get_conditions(filters):
    where_clause = []
    return where_clause and " and " + " and ".join(where_clause) or ""


def get_customers_for_billing_cycle(cycle):
        return [d[0] for d in frappe.db.get_all("Customer", filters={"storage_billing_model_cf": cycle}, as_list=1)]


def get_invoice_items(filters):
    """
    return invoice items (storage charge item , qty) for billing
    """
    # set from_date to 1 year previous, to calculate LTSF
    filters["from_date"] = getdate(filters["to_date"]) + relativedelta(years=-1)
    storage_charge_items = get_storage_charge_items()
    item_details = get_item_details()
    customers = get_customers_for_billing_cycle("Monthly")
    if not filters.get("customer"):
        frappe.throw('Customer is required for billing monthly storage charges.')

    _cols, stock_balance = get_stock_balance(filters)

    invoice_items = []
    for d in [frappe._dict(x) for x in stock_balance]:
        details = item_details.get(d.item_code)
        # skip non customer items
        customer = filters.get("customer")
        # apply customer filter if set
        if not details.is_customer_provided_item \
        or details.customer not in customers \
        or (customer and not customer == details.get("customer")):
            continue

        # Regular Storage Calculation
        regular_storage_charge_item = d.monthly_storage_charge_cf or storage_charge_items.default_monthly_storage_per_cubic_feet
        regular_storage_qty = d.bal_qty

        # LTSF Calculation
        lts_charge_item = storage_charge_items.default_long_term_storage_fees_for_monthly_cycle
        lts_qty = 0 if not d.bal_qty > d.in_qty else (d.bal_qty - d.in_qty)

        # deduct already billed qty logged in 'Storage Charge Log CT'
        for scl in frappe.db.sql("""
            select
                customer, item, inventory, lts_qty 
            from 
                `tabStorage Charge Log CT`
            where
                customer = %(customer)s and date=%(to_date)s
        """, filters, as_dict=True):
            regular_storage_qty = max(regular_storage_qty - scl.inventory, 0)
            lts_qty = max(lts_qty - scl.lts_qty, 0)

        if regular_storage_qty:
            invoice_items.append({
                "item_code": regular_storage_charge_item,
                "qty": regular_storage_qty
            })
        if lts_qty:
            invoice_items.append({
                "item_code": lts_charge_item,
                "qty": lts_qty
            })

    if invoice_items:
        df = pd.DataFrame(invoice_items)
        g = df.groupby('item_code', as_index=False).agg('sum')
        data = g.to_dict('r')
        return sorted(data, key=itemgetter('item_code'))

    return []
