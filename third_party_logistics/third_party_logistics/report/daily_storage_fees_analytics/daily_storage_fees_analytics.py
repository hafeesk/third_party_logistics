# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days, date_diff
from third_party_logistics.third_party_logistics.billing.billing_controller import get_item_rate
from erpnext.stock.report.stock_balance.stock_balance import execute as get_stock_balance
from operator import itemgetter
from dateutil.relativedelta import relativedelta
import copy
import pandas as pd

def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data

def get_columns(filters):
    return [
            dict(label=_("Customer"), fieldname="customer", fieldtype="Link/Customer", width=120),
            dict(label=_("Item Group"), fieldname="item_group", fieldtype="Data", width=120),
            dict(label=_("Item"), fieldname="item_name", fieldtype="Data", width=120),
            dict(label=_("Inventory as on To Date"), fieldname="qty", fieldtype="Float", width=120),
            dict(label=_("Item Volume"), fieldname="item_volume", fieldtype="Float", width=120),
            dict(label=_("Charge per Cubic Feet"), fieldname="storage_charge_per_cubic_feet", fieldtype="Currency", width=120),
            dict(label=_("Regular Storage Charge"), fieldname="regular_storage_charge", fieldtype="Currency", width=120),
            dict(label=_("LTS Qty"), fieldname="lts_qty", fieldtype="Float", width=120),
            dict(label=_("LTS Rate"), fieldname="lts_storage_rate", fieldtype="Currency", width=120),
            dict(label=_("Long Term Storage Charge"), fieldname="lts_storage_charge", fieldtype="Currency", width=120),
            dict(label=_("Total Charge"), fieldname="total_storage_charge", fieldtype="Currency", width=120),
    ]

def get_data(filters):
    # set from_date to 1 year previous, to calculate LTSF
    storage_charge_items = get_storage_charge_items()
    item_details = get_item_details()
    item_rates = dict()
    customers = get_customers_for_billing_cycle("Daily")
    data = []

    stock_filters = copy.deepcopy(filters)
    for n in range(date_diff(filters["to_date"], filters["from_date"]) + 1):
        curr_date = add_days(filters["from_date"], n)
        stock_filters.update({
            "to_date": curr_date,
            "from_date": getdate(curr_date) + relativedelta(years=-1)
        })
        _cols, stock_balance = get_stock_balance(stock_filters)
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
            storage_charge_per_cubic_feet = get_item_rate(customer, d.daily_storage_charge_cf or storage_charge_items.default_daily_storage_per_cubic_feet_charge, item_rates)
            regular_storage_charge = storage_charge_per_cubic_feet * d.bal_qty * details.volume_in_cubic_feet_cf

            # LTSF Calculation
            lts_storage_rate, lts_storage_charge = 0, 0
            lts_qty = 0 if not d.bal_qty > d.in_qty else (d.bal_qty - d.in_qty)
            if lts_qty:
                lts_storage_rate = get_item_rate(customer, storage_charge_items.default_long_term_storage_fees_for_daily_cycle, item_rates)
                lts_storage_charge = lts_qty * lts_storage_rate

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
            )
            data.append(item)

    group_columns = ["customer", "item_group", "item_name", "item_volume", "storage_charge_per_cubic_feet", "lts_storage_rate"]
    aggregations = {
                "qty": "mean",
                "regular_storage_charge": "sum",
                "lts_qty": "mean",
                "lts_storage_charge": "sum",
                "total_storage_charge": "sum",
    }
    df = pd.DataFrame(data)
    g = df.groupby(group_columns, as_index=False).agg(aggregations)
    data = g.to_dict('r')
    data = sorted(data, key=itemgetter('customer', 'item_name'))
    return data

def get_storage_charge_items():
    tpls = frappe.get_single("Third Party Logistics Settings")
    out = dict()
    for d in [
        "default_daily_storage_per_cubic_feet_charge", "default_monthly_storage_per_cubic_feet", "default_long_term_fees_for_daily_cycle", "default_long_term_storage_fees_for_monthly_cycle"]:
        out[d] = tpls.get(d)
    return frappe._dict(out)


def get_item_details():
    item_details = dict()
    for d in frappe.db.sql("""
    select 
        item_code, volume_in_cubic_feet_cf, monthly_storage_charge_cf,
        daily_storage_charge_cf, customer, is_customer_provided_item
    from 
        tabItem""", as_dict=True):
        item_details.setdefault(d.item_code, d)
    return item_details


def get_conditions(filters):
    where_clause = []
    return where_clause and " and " + " and ".join(where_clause) or ""


def get_customers_for_billing_cycle(cycle):
        return [d[0] for d in frappe.db.get_all("Customer", filters={"storage_billing_model_cf": cycle}, as_list=1)]
