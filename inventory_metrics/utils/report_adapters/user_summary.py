def user_summary_to_workbook_spec(payload: dict) -> dict:
    if not payload:
        raise ValueError("Empty user summary payload")

    spec = {}

    # --------------------
    # Demographics
    # --------------------
    demographics = payload.get("demographics")
    if demographics:
        rows = [
            [key.replace("_", " ").title(), value]
            for key, value in demographics.items()
        ]
    else:
        rows = [["Message", "No demographic data available."]]

    spec["Demographics"] = {
        "headers": ["Field", "Value"],
        "rows": rows,
    }

    # --------------------
    # Login Stats
    # --------------------
    login_stats = payload.get("loginStats")
    if login_stats:
        spec["Login Stats"] = {
            "headers": list(login_stats.keys()),
            "rows": [list(login_stats.values())],
        }
    else:
        spec["Login Stats"] = {
            "headers": ["Message"],
            "rows": [["No login statistics available."]],
        }

    # --------------------
    # Audit Summary
    # --------------------
    audit_summary = payload.get("auditSummary")
    if audit_summary:
        rows = [
            ["Total Events", audit_summary.get("total", 0)]
        ]

        for event, count in audit_summary.get("events", {}).items():
            rows.append([event, count])
    else:
        rows = [["No audit events found for this user.", ""]]

    spec["Audit Summary"] = {
        "headers": ["Metric", "Count"],
        "rows": rows,
    }

    # --------------------
    # Role Summary
    # --------------------
    role_summary = payload.get("roleSummary")
    if role_summary:
        rows = [
            [
                r.get("role_name"),
                r.get("scope"),
                r.get("assigned_date"),
            ]
            for r in role_summary
        ]
        headers = ["Role", "Scope", "Assigned Date"]
    else:
        headers = ["Message"]
        rows = [["No roles assigned to this user."]]

    spec["Role Summary"] = {
        "headers": headers,
        "rows": rows,
    }

    # --------------------
    # Password Events
    # --------------------
    password_events = payload.get("passwordevents")
    if password_events:
        rows = [
            ["Total password reset events", password_events.get("total_password_reset_events", 0)],
            ["Active reset tokens", password_events.get("active_reset_tokens", 0)],
        ]
    else:
        rows = [["Message", "No password-related events recorded."]]

    spec["Password Events"] = {
        "headers": ["Metric", "Value"],
        "rows": rows,
    }

    return spec