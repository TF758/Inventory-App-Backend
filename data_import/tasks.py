
from celery import shared_task
from data_import.services.import_builder import build_asset_import
from inventory_metrics.tasks.reports import generate_report_task
from reporting.models.reports import ReportJob



@shared_task(bind=True)
def run_asset_import_task(self, report_job_id):

    job = ReportJob.objects.select_related("user").get(id=report_job_id)

    params = job.params

    raw_data = build_asset_import(
        asset_type=params["asset_type"],
        stored_file_name=params["stored_file_name"],
        generated_by=job.user,
    )

    # store result for report generation
    job.result_payload = raw_data
    job.save(update_fields=["result_payload"])

    generate_report_task.delay(job.id)