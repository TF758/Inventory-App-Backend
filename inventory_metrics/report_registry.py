

from data_import.renderers import asset_import_to_workbook_spec
from data_import.services.import_builder import build_asset_import
from inventory_metrics.services.site_reports import build_site_asset_report, build_site_audit_log_report
from inventory_metrics.services.user_summary import build_user_audit_history_report, build_user_summary_report
from inventory_metrics.utils.report_adapters.site_reports import site_asset_to_workbook_spec, site_audit_log_to_workbook_spec
from inventory_metrics.utils.report_adapters.user_summary import user_audit_history_to_workbook_spec, user_summary_to_workbook_spec


"""
Report Registry

Defines all report types supported by the reporting system.

Each report definition describes:

builder
    Function responsible for gathering report data.

renderer
    Function responsible for converting report data into
    an Excel workbook specification.

param_map
    Function that translates stored ReportJob.params into
    arguments expected by the builder function.

Workflow
--------
API request
    ↓
ReportJob created (report_type + params stored)
    ↓
generate_report_task(job_id)
    ↓
registry lookup
    ↓
param_map(params, user) → builder args
    ↓
builder collects data
    ↓
renderer builds workbook spec
    ↓
Excel file written to disk
"""

# ---------------------------------------------------------
# Param mapping helpers
# ---------------------------------------------------------

def user_summary_params(params, user):
    """Map stored job params → user summary builder arguments."""
    return {
        "user_identifier": params["user"],
        "sections": params["sections"],
        "generated_by": user,
    }


def site_asset_params(params, user):
    """Map stored job params → site asset report builder arguments."""
    return {
        "site_type": params["site"]["siteType"],
        "site_id": params["site"]["siteId"],
        "asset_types": params["asset_types"],
        "generated_by": user,
    }


def site_audit_params(params, user):
    """Map stored job params → audit log builder arguments."""
    return {
        "site": params["site"],
        "audit_period_days": params.get("audit_period_days", 30),
        "generated_by": user,
    }

def asset_import_params(params, user):
    return {
        "asset_type": params["asset_type"],
        "stored_file_name": params["stored_file_name"],
        "generated_by": user,
    }

def user_audit_history_params(params, user):

    return {
        "user_identifier": params["user"],
        "start_date": params.get("start_date"),
        "end_date": params.get("end_date"),
        "relative_range": params.get("relative_range"),
        "generated_by": user,
    }

# ---------------------------------------------------------
# Report definitions
# ---------------------------------------------------------

REPORT_DEFINITIONS = {

    "user_summary": {
        "builder": build_user_summary_report,
        "renderer": user_summary_to_workbook_spec,
        "param_map": user_summary_params,
    },

    "site_assets": {
        "builder": build_site_asset_report,
        "renderer": site_asset_to_workbook_spec,
        "param_map": site_asset_params,
    },

    "site_audit_logs": {
        "builder": build_site_audit_log_report,
        "renderer": site_audit_log_to_workbook_spec,
        "param_map": site_audit_params,
    },

    "asset_import": {
    "builder": build_asset_import,
    "renderer": asset_import_to_workbook_spec,
    "param_map": asset_import_params,
    },

 "user_audit_history": {
        "builder": build_user_audit_history_report,
        "renderer": user_audit_history_to_workbook_spec,
        "param_map": user_audit_history_params,
         "streaming": True,
    },   
}