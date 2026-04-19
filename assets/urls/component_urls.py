from django.urls import path, include
from assets.api.viewsets import component_viewsets


urlpatterns = [

    # ----------------------------
    # Components
    # ----------------------------

    path("<str:public_id>/", component_viewsets.ComponentModelViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy"
    }), name="component-detail"),

    path("", component_viewsets.ComponentModelViewSet.as_view({
        "get": "list",
        "post": "create"
    }), name="components"),
    
]