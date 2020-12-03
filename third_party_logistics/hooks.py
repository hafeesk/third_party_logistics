# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "third_party_logistics"
app_title = "Third Party Logistics"
app_publisher = "GreyCube Technologies"
app_description = "Third Party Logistics"
app_icon = "octicon octicon-home-fill"
app_color = "red"
app_email = "admin@greycube.in"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/third_party_logistics/css/third_party_logistics.css"
app_include_js = "/assets/third_party_logistics/js/third_party_logistics.js"

# include js, css files in header of web template
# web_include_css = "/assets/third_party_logistics/css/third_party_logistics.css"
# web_include_js = "/assets/third_party_logistics/js/third_party_logistics.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Stock Entry": "public/js/stock_entry.js"}
doctype_list_js = {"Stock Entry": "public/js/stock_entry_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "third_party_logistics.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "third_party_logistics.install.before_install"
# after_install = "third_party_logistics.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "third_party_logistics.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "third_party_logistics.third_party_logistics.billing.billing_controller.update_invoiced_cf"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"third_party_logistics.tasks.all"
# 	],
# 	"daily": [
# 		"third_party_logistics.tasks.daily"
# 	],
# 	"hourly": [
# 		"third_party_logistics.tasks.hourly"
# 	],
# 	"weekly": [
# 		"third_party_logistics.tasks.weekly"
# 	]
# 	"monthly": [
# 		"third_party_logistics.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "third_party_logistics.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "third_party_logistics.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "third_party_logistics.task.get_dashboard_data"
# }
