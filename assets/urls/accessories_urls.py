from django.urls import path, include

from assets.api.viewsets import accessory_viewsets


urlpatterns = [

    # ----------------------------
  
    # ----------------------------
    # Accessories
    # ----------------------------

    path("batch-soft-delete/", accessory_viewsets.BatchAccessorySoftDeleteView.as_view(), name="batch-soft-delete-accessory"),
    path("batch-hard-delete/", accessory_viewsets.BatchAccessoryHardDeleteView.as_view(), name="batch-hard-delete-accessory"),

    path("<str:public_id>/restore/", accessory_viewsets.AccessoryRestoreViewSet.as_view(), name="restore-accessory"),
    path("<str:public_id>/soft-delete/", accessory_viewsets.AccessorySoftDeleteView.as_view(), name="soft-delete-accessory"),

    path("<str:public_id>/", accessory_viewsets.AccessoryModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="accessory-detail"),

    path("accessories-validate-import/", accessory_viewsets.AccessoryBatchValidateView.as_view(), name="accessories-validate-import"),
    path("accessories-import/", accessory_viewsets.AccessoryBatchImportView.as_view(), name="accessories-import"),

    path("", accessory_viewsets.AccessoryModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="accessories"),
    
]