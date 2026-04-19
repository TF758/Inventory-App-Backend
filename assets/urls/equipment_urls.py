from django.urls import path, include
from assets.api.viewsets import equipment_viewsets


urlpatterns = [
    # ----------------------------
    # Equipment
    # ----------------------------

    # these were previously under equipment/ but moved to match urls of other asset types
    # --- batch routes FIRST ---
    path("batch-unassign/", equipment_viewsets.BatchUnassignEquipmentView.as_view(), name="batch-unassign-equipment"),
    path("batch-assign/", equipment_viewsets.BatchAssignEquipmentView.as_view(), name="batch-assign-equipment"),
    path("batch-condemn/", equipment_viewsets.BatchEquipmentCondemnView.as_view(), name="batch-condemn-equipment"),
    path("batch-status-change/", equipment_viewsets.BatchEquipmentStatusChangeView.as_view(), name="batch-equipment-status-change"),
    path("batch-soft-delete/", equipment_viewsets.BatchEquipmentSoftDeleteView.as_view(), name="batch-equipment-soft-delete"),

    path("equipments-import/", equipment_viewsets.EquipmentBatchImportView.as_view(), name="equipment-batch-import"),

    path("<str:public_id>/status/", equipment_viewsets.EquipmentStatusChangeView.as_view(), name="update-equipment-status"),
    path("<str:public_id>/condemn/", equipment_viewsets.EquipmentCondemnView.as_view(), name="condemn-equipment"),
    path("<str:public_id>/restore/", equipment_viewsets.EquipmentRestoreViewSet.as_view(), name="restore-equipment"),
    path("<str:public_id>/soft-delete/", equipment_viewsets.EquipmentSoftDeleteView.as_view(), name="soft-delete-equipment"),

    path("<str:public_id>/", equipment_viewsets.EquipmentModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="equipment-detail"),

    path("", equipment_viewsets.EquipmentModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="equipments"),
 
]