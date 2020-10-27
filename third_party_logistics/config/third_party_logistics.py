#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _


def get_data():
    config = [{'label': _('Transaction'), 'items': [{
        'type': 'doctype',
        'name': 'Sales Order',
        'label': 'Sales Order',
        'description': 'Sales Order'
        },{
        'type': 'doctype',
        'name': 'Delivery Note',
        'label': 'Delivery Note',
        'description': 'Delivery Note'
        },{
        'type': 'doctype',
        'name': 'Stock Entry',
        'label': 'Stock Entry',
        'description': 'Stock Entry'
        },{
        'type': 'doctype',
        'name': 'Service Note CT',
        'label': 'Service Note',
        'description': 'Service Note'
        },{
        'type': 'doctype',
        'name': 'Sales Invoice',
        'label': 'Sales Invoice',
        'description': 'Sales Invoice'
        }]},
        {'label': _('Inventory'), 'items': [{
        'type': 'doctype',
        'name': 'Item',
        'label': 'Item',
        'description': 'Item'
        },{
        'type': 'doctype',
        'name': 'Item Group',
        'label': 'Item Group',
        'description': 'Item Group'
        },{
        'type': 'doctype',
        'name': 'Warehouse',
        'label': 'Warehouse',
        'description': 'Warehouse'
        }]},
        {'label': _('Customer'), 'items': [{
        'type': 'doctype',
        'name': 'Customer',
        'label': 'Customer',
        'description': 'Customer'
        },{
        'type': 'doctype',
        'name': 'Contract',
        'label': 'Contract',
        'description': 'Contract'
        }]},
        {'label': _('Reports'), 'items': [{
        'type': 'report',
        'name': 'Storage Billing Details',
        'label': 'Storage Billing Details',
	    "is_query_report": True,
	    'doctype':'Storage Charge Log CT',
        'description': 'Storage Charge Log CT'
        },{
        'type': 'report',
        'name': 'Stock Balance',
        'label': 'Stock Balance',
	    "is_query_report": True,
	    'doctype':'Stock Entry',
        'description': 'Stock Balance'
        }]},
        {'label': _('Setup'), 'items': [
        {
        'type': 'doctype',
        'name': 'Third Party Logistics Settings',
        'label': 'Third Party Logistics Settings',
        'description': 'Third Party Logistics Settings'
        },{
        'type': 'doctype',
        'name': 'ShipStation Integration Settings',
        'label': 'ShipStation Integration Settings',
        'description': 'ShipStation Integration Settings'
        },
        {
        'type': 'doctype',
        'name': 'Storage Charge Log CT',
        'label': 'Storage Charge Log',
        'description': 'Storage Charge Log'
        }]}]

    return config