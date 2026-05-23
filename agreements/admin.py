from django.contrib import admin

from agreements.models.agreements import AgreementCoverage, AgreementHistory, AgreementItemHistory, AssetAgreement, AssetAgreementItem

# Register your models here.


class AgreementCoverageInline(admin.TabularInline):

    model = AgreementCoverage

    extra = 0

    readonly_fields = (
        "public_id",
        "scope_type",
        "department",
        "location",
        "room",
        "notes",
    )


class AssetAgreementItemInline(admin.TabularInline):

    model = AssetAgreementItem

    extra = 0

    readonly_fields = (
        "public_id",
        "asset_type",
        "asset_public_id_snapshot",
        "asset_name_snapshot",
        "asset_serial_snapshot",
        "coverage_start",
        "coverage_end",
        "created_at",
    )


class AgreementHistoryInline(admin.TabularInline):

    model = AgreementHistory

    extra = 0

    readonly_fields = (
        "event_type",
        "previous_status",
        "new_status",
        "previous_expiry_date",
        "new_expiry_date",
        "previous_renewal_date",
        "new_renewal_date",
        "notes",
        "created_at",
        "user",
        "user_email",
    )

    can_delete = False

    max_num = 0


# -----------------------------------------------------
# Asset Agreement
# -----------------------------------------------------


@admin.register(AssetAgreement)
class AssetAgreementAdmin(admin.ModelAdmin):

    list_display = (
        "public_id",
        "name",
        "agreement_type",
        "status",
        "vendor",
        "start_date",
        "expiry_date",
        "auto_renew",
        "managing_department",
    )

    list_filter = (
        "agreement_type",
        "status",
        "auto_renew",
        "managing_department",
    )

    search_fields = (
        "public_id",
        "name",
        "vendor",
        "reference_number",
    )

    readonly_fields = (
        "public_id",
    )

    ordering = (
        "-id",
    )

    list_select_related = (
        "managing_department",
    )

    inlines = [
        AgreementCoverageInline,
        AssetAgreementItemInline,
        AgreementHistoryInline,
    ]


# -----------------------------------------------------
# Agreement Coverage
# -----------------------------------------------------


@admin.register(AgreementCoverage)
class AgreementCoverageAdmin(admin.ModelAdmin):

    list_display = (
        "public_id",
        "agreement",
        "scope_type",
        "department",
        "location",
        "room",
    )

    list_filter = (
        "scope_type",
    )

    search_fields = (
        "public_id",
        "agreement__name",
    )

    readonly_fields = (
        "public_id",
    )

    ordering = (
        "-id",
    )

    list_select_related = (
        "agreement",
        "department",
        "location",
        "room",
    )


# -----------------------------------------------------
# Agreement Items
# -----------------------------------------------------


@admin.register(AssetAgreementItem)
class AssetAgreementItemAdmin(admin.ModelAdmin):

    list_display = (
        "public_id",
        "agreement",
        "asset_type",
        "coverage_start",
        "coverage_end",
        "created_at",
    )

    list_filter = (
        "coverage_start",
        "coverage_end",
    )

    search_fields = (
        "public_id",
        "agreement__name",
        "asset_name_snapshot",
        "asset_public_id_snapshot",
    )

    readonly_fields = (
        "public_id",
        "asset_public_id_snapshot",
        "asset_name_snapshot",
        "asset_serial_snapshot",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_select_related = (
        "agreement",
    )


# -----------------------------------------------------
# Agreement History
# -----------------------------------------------------


@admin.register(AgreementHistory)
class AgreementHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "agreement",
        "event_type",
        "previous_status",
        "new_status",
        "created_at",
        "user",
    )

    list_filter = (
        "event_type",
        "created_at",
    )

    search_fields = (
        "agreement__name",
        "user_email",
    )

    readonly_fields = (
        "agreement",
        "event_type",
        "previous_status",
        "new_status",
        "previous_expiry_date",
        "new_expiry_date",
        "previous_renewal_date",
        "new_renewal_date",
        "notes",
        "created_at",
        "user",
        "user_email",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_select_related = (
        "agreement",
        "user",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False


# -----------------------------------------------------
# Agreement Item History
# -----------------------------------------------------


@admin.register(AgreementItemHistory)
class AgreementItemHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "agreement",
        "asset_name",
        "event_type",
        "created_at",
        "user",
    )

    list_filter = (
        "event_type",
        "created_at",
    )

    search_fields = (
        "agreement__name",
        "asset_name",
        "asset_public_id",
    )

    readonly_fields = (
        "agreement",
        "agreement_item",
        "event_type",
        "asset_public_id",
        "asset_name",
        "asset_serial",
        "asset_type",
        "coverage_start",
        "coverage_end",
        "department_name",
        "location_name",
        "room_name",
        "reason",
        "metadata",
        "created_at",
        "user",
        "user_email",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_select_related = (
        "agreement",
        "agreement_item",
        "user",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False