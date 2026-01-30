def user_summary_to_workbook_spec(payload: dict) -> dict:
    spec = {}

    # --------------------
    # Demographics
    # --------------------
    if "demographics" in payload:
        spec["Demographics"] = {
            "headers": ["Field", "Value"],
            "rows": [
                [key.replace("_", " ").title(), value]
                for key, value in payload["demographics"].items()
            ],
        }

    # --------------------
    # Login Stats
    # --------------------
    if "loginStats" in payload:
        stats = payload["loginStats"]
        spec["Login Stats"] = {
            "headers": list(stats.keys()),
            "rows": [list(stats.values())],
        }

    # --------------------
    # Audit Summary
    # --------------------
    if "auditSummary" in payload:
        summary = payload["auditSummary"]

        rows = [
            ["Total Events", summary.get("total")]
        ]

        for event, count in summary.get("events", {}).items():
            rows.append([event, count])

        spec["Audit Summary"] = {
            "headers": ["Metric", "Count"],
            "rows": rows,
        }

    if "roleSummary" in payload:
        roles = payload["roleSummary"]

        spec["Role Summary"] = {
            "headers": ["Role", "Scope", "Assigned Date"],
            "rows": [
                [
                    r["role_name"],
                    r["scope"],
                    r["assigned_date"],
                ]
                for r in roles
            ],
        }

    if "passwordevents" in payload:
        pe = payload["passwordevents"]

        spec["Password Events"] = {
            "headers": ["Metric", "Value"],
            "rows": [
                ["Total password reset events", pe["total_password_reset_events"]],
                ["Active reset tokens", pe["active_reset_tokens"]],
            ],
        }

    return spec
