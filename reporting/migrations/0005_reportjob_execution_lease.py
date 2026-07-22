from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0004_alter_reportjob_report_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportjob",
            name="attempt_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="reportjob",
            name="heartbeat_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="reportjob",
            name="task_id",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddIndex(
            model_name="reportjob",
            index=models.Index(
                fields=["status", "heartbeat_at"],
                name="report_job_status_hb_idx",
            ),
        ),
    ]
