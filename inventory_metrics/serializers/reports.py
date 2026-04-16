
from rest_framework import serializers

from reporting.models.reports import ReportJob



class ReportJobSerializer(serializers.ModelSerializer):

    can_download = serializers.SerializerMethodField()
    is_running = serializers.SerializerMethodField()
    is_failed = serializers.SerializerMethodField()

    class Meta:
        model = ReportJob
        fields = [
            "public_id",
            "report_type",
            "status",
            "created_at",
            "finished_at",
            "error",
            "can_download",
            "is_running",
            "is_failed",
        ]
        read_only_fields = fields

    def get_can_download(self, obj):
        request = self.context.get("request")

        if not request:
            return False

        return (
            obj.status == ReportJob.Status.DONE
            and obj.user == request.user
    )

    def get_is_running(self, obj):
        return obj.status in (
            ReportJob.Status.PENDING,
            ReportJob.Status.RUNNING,
        )

    def get_is_failed(self, obj):
        return obj.status == ReportJob.Status.FAILED