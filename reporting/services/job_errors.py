from reporting.models.reports import ReportJob


REPORT_FAILURE_MESSAGE = "Report generation failed."
IMPORT_FAILURE_MESSAGE = "Import processing failed."


def public_job_error(job: ReportJob) -> str:
    """Return a stable client-safe failure message for a job."""

    if job.status != ReportJob.Status.FAILED:
        return ""

    payload = job.result_payload or {}
    public_error = payload.get("public_error")

    if isinstance(public_error, str) and public_error.strip():
        return public_error.strip()

    if job.report_type == ReportJob.ReportType.ASSET_IMPORT:
        return IMPORT_FAILURE_MESSAGE

    return REPORT_FAILURE_MESSAGE
