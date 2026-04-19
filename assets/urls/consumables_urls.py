from django.urls import path, include
from assets.api.viewsets import consumable_viewsets


urlpatterns = [


    # ----------------------------
    # Consumables
    # ----------------------------

    # previously was consumable/batch-* chnaging to cosumable to match urls of other asset types

    path("batch-soft-delete/", consumable_viewsets.BatchConsumableSoftDeleteView.as_view(), name="batch-soft-delete-consumable"),
    path("batch-hard-delete/", consumable_viewsets.BatchConsumableHardDeleteView.as_view(), name="batch-hard-delete-consumable"),

    path("<str:public_id>/restore/", consumable_viewsets.ConsumableRestoreViewSet.as_view(), name="restore-consumable"),
    path("<str:public_id>/soft-delete/", consumable_viewsets.ConsumableSoftDeleteView.as_view(), name="soft-delete-consumable"),

    path("<str:public_id>/", consumable_viewsets.ConsumableModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="consumable-detail"),

    path("consumables-import/", consumable_viewsets.ConsumableBatchImportView.as_view(), name="consumables-batch-import"),
    path("consumables-validate-import/", consumable_viewsets.ConsumableBatchValidateView.as_view(), name="consumables-batch-validate"),

    path("", consumable_viewsets.ConsumableModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="consumables"),

]